#!/bin/bash
# Kubernetes deployment script for Hybrid Search RAG
# Deploys all manifests to AWS EKS cluster

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
CLUSTER_NAME="${CLUSTER_NAME:-hybrid-rag-cluster}"
AWS_REGION="${AWS_REGION:-us-east-1}"
NAMESPACE="hybrid-rag"
K8S_DIR="$(cd "$(dirname "$0")/.." && pwd)/k8s"
ECR_ACCOUNT_ID="${ECR_ACCOUNT_ID:-}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
DRY_RUN="${DRY_RUN:-false}"

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

check_prerequisites() {
    log_step "Checking prerequisites..."

    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl not found. Please install kubectl."
        exit 1
    fi

    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI not found. Please install AWS CLI."
        exit 1
    fi

    # Check helm
    if ! command -v helm &> /dev/null; then
        log_warn "helm not found. Some features may not work."
    fi

    log_info "Prerequisites check passed"
}

configure_kubeconfig() {
    log_step "Configuring kubeconfig for EKS cluster..."

    if ! aws eks update-kubeconfig --name "$CLUSTER_NAME" --region "$AWS_REGION" 2>/dev/null; then
        log_error "Failed to configure kubeconfig. Please check cluster name and region."
        exit 1
    fi

    # Verify connection
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi

    log_info "Successfully connected to cluster: $CLUSTER_NAME"
}

install_prerequisites() {
    log_step "Installing cluster prerequisites..."

    # Install AWS Load Balancer Controller
    if kubectl get deployment -n kube-system aws-load-balancer-controller &> /dev/null; then
        log_info "AWS Load Balancer Controller already installed"
    else
        log_warn "AWS Load Balancer Controller not found. Installing..."

        helm repo add eks https://aws.github.io/eks-charts 2>/dev/null || true
        helm repo update

        # Create IAM service account
        eksctl create iamserviceaccount \
            --cluster="$CLUSTER_NAME" \
            --namespace=kube-system \
            --name=aws-load-balancer-controller \
            --attach-policy-arn=arn:aws:iam::aws:policy/ElasticLoadBalancingFullAccess \
            --override-existing-serviceaccounts \
            --approve

        # Install controller
        helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
            -n kube-system \
            --set clusterName="$CLUSTER_NAME" \
            --set serviceAccount.create=false \
            --set serviceAccount.name=aws-load-balancer-controller

        log_info "AWS Load Balancer Controller installed"
    fi

    # Install External Secrets Operator
    if kubectl get deployment -n external-secrets-system external-secrets &> /dev/null; then
        log_info "External Secrets Operator already installed"
    else
        log_warn "External Secrets Operator not found. Installing..."

        helm repo add external-secrets https://charts.external-secrets.io 2>/dev/null || true
        helm repo update

        helm install external-secrets external-secrets/external-secrets \
            -n external-secrets-system \
            --create-namespace \
            --set installCRDs=true

        log_info "External Secrets Operator installed"
    fi

    # Install Metrics Server
    if kubectl get deployment -n kube-system metrics-server &> /dev/null; then
        log_info "Metrics Server already installed"
    else
        log_warn "Metrics Server not found. Installing..."
        kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
        log_info "Metrics Server installed"
    fi

    # Install EBS CSI Driver
    if kubectl get deployment -n kube-system ebs-csi-controller &> /dev/null; then
        log_info "EBS CSI Driver already installed"
    else
        log_warn "EBS CSI Driver not found. Installing..."

        eksctl create iamserviceaccount \
            --name ebs-csi-controller-sa \
            --namespace kube-system \
            --cluster "$CLUSTER_NAME" \
            --attach-policy-arn arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy \
            --approve \
            --override-existing-serviceaccounts

        kubectl apply -k "github.com/kubernetes-sigs/aws-ebs-csi-driver/deploy/kubernetes/overlays/stable/?ref=release-1.25"

        log_info "EBS CSI Driver installed"
    fi
}

update_image_references() {
    log_step "Updating image references..."

    if [ -z "$ECR_ACCOUNT_ID" ]; then
        ECR_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    fi

    local api_deployment="$K8S_DIR/deployments/api-deployment.yaml"

    if [ -f "$api_deployment" ]; then
        sed -i.bak "s|ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com|${ECR_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com|g" "$api_deployment"
        sed -i.bak "s|:latest|:${IMAGE_TAG}|g" "$api_deployment"
        rm -f "${api_deployment}.bak"
        log_info "Updated image references in API deployment"
    fi
}

apply_manifests() {
    log_step "Applying Kubernetes manifests..."

    local apply_cmd="kubectl apply"
    if [ "$DRY_RUN" = "true" ]; then
        apply_cmd="kubectl apply --dry-run=client"
        log_warn "DRY RUN mode - no changes will be applied"
    fi

    # Create namespace
    log_info "Creating namespace..."
    $apply_cmd -f "$K8S_DIR/namespace.yaml"

    # Apply storage
    log_info "Creating PersistentVolumeClaims..."
    $apply_cmd -f "$K8S_DIR/storage/pvc.yaml"

    # Apply ConfigMaps
    log_info "Creating ConfigMaps..."
    $apply_cmd -f "$K8S_DIR/configmaps/app-config.yaml"

    # Apply Secrets
    log_info "Creating Secrets (External Secrets)..."
    $apply_cmd -f "$K8S_DIR/secrets/external-secret.yaml"

    # Wait for External Secrets to sync
    if [ "$DRY_RUN" != "true" ]; then
        log_info "Waiting for secrets to sync (30s)..."
        sleep 30
    fi

    # Apply Services
    log_info "Creating Services..."
    $apply_cmd -f "$K8S_DIR/services/qdrant-service.yaml"
    $apply_cmd -f "$K8S_DIR/services/elasticsearch-service.yaml"
    $apply_cmd -f "$K8S_DIR/services/redis-service.yaml"
    $apply_cmd -f "$K8S_DIR/services/api-service.yaml"

    # Apply Deployments/StatefulSets
    log_info "Creating StatefulSets and Deployments..."
    $apply_cmd -f "$K8S_DIR/deployments/redis-deployment.yaml"
    $apply_cmd -f "$K8S_DIR/deployments/qdrant-deployment.yaml"
    $apply_cmd -f "$K8S_DIR/deployments/elasticsearch-deployment.yaml"

    # Wait for databases to be ready
    if [ "$DRY_RUN" != "true" ]; then
        log_info "Waiting for databases to be ready..."
        kubectl wait --for=condition=ready pod -l app=redis -n "$NAMESPACE" --timeout=300s
        kubectl wait --for=condition=ready pod -l app=qdrant -n "$NAMESPACE" --timeout=300s
        kubectl wait --for=condition=ready pod -l app=elasticsearch -n "$NAMESPACE" --timeout=600s
    fi

    # Deploy API
    $apply_cmd -f "$K8S_DIR/deployments/api-deployment.yaml"

    # Apply HPA
    log_info "Creating HorizontalPodAutoscaler..."
    $apply_cmd -f "$K8S_DIR/hpa/api-hpa.yaml"

    # Apply Ingress
    log_info "Creating Ingress..."
    $apply_cmd -f "$K8S_DIR/ingress/api-ingress.yaml"

    log_info "All manifests applied successfully"
}

verify_deployment() {
    log_step "Verifying deployment..."

    if [ "$DRY_RUN" = "true" ]; then
        log_warn "Skipping verification (DRY RUN mode)"
        return
    fi

    # Wait for API deployment
    log_info "Waiting for API pods to be ready..."
    if kubectl wait --for=condition=ready pod -l app=hybrid-rag-api -n "$NAMESPACE" --timeout=300s; then
        log_info "API pods are ready"
    else
        log_error "API pods failed to become ready"
        kubectl get pods -n "$NAMESPACE"
        exit 1
    fi

    # Check all resources
    echo ""
    log_info "Resource Status:"
    echo ""
    kubectl get all -n "$NAMESPACE"

    echo ""
    log_info "PersistentVolumeClaims:"
    kubectl get pvc -n "$NAMESPACE"

    echo ""
    log_info "Ingress:"
    kubectl get ingress -n "$NAMESPACE"

    # Get Load Balancer URL
    echo ""
    log_info "Load Balancer URL:"
    ALB_URL=$(kubectl get ingress hybrid-rag-ingress -n "$NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null)
    if [ -n "$ALB_URL" ]; then
        echo -e "${GREEN}$ALB_URL${NC}"
    else
        log_warn "Load Balancer URL not yet available (may take a few minutes)"
    fi
}

show_usage() {
    cat <<EOF
Usage: $0 [OPTIONS]

Deploy Hybrid Search RAG to AWS EKS

OPTIONS:
    -c, --cluster NAME      EKS cluster name (default: hybrid-rag-cluster)
    -r, --region REGION     AWS region (default: us-east-1)
    -a, --account ID        AWS account ID (auto-detected if not provided)
    -t, --tag TAG           Docker image tag (default: latest)
    -d, --dry-run           Perform dry run (no changes applied)
    -h, --help              Show this help message

EXAMPLES:
    # Deploy to default cluster
    $0

    # Deploy to specific cluster
    $0 --cluster my-cluster --region us-west-2

    # Dry run
    $0 --dry-run

    # Deploy specific image tag
    $0 --tag v1.2.3

ENVIRONMENT VARIABLES:
    CLUSTER_NAME            EKS cluster name
    AWS_REGION              AWS region
    ECR_ACCOUNT_ID          AWS account ID
    IMAGE_TAG               Docker image tag
    DRY_RUN                 Set to 'true' for dry run

EOF
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -c|--cluster)
            CLUSTER_NAME="$2"
            shift 2
            ;;
        -r|--region)
            AWS_REGION="$2"
            shift 2
            ;;
        -a|--account)
            ECR_ACCOUNT_ID="$2"
            shift 2
            ;;
        -t|--tag)
            IMAGE_TAG="$2"
            shift 2
            ;;
        -d|--dry-run)
            DRY_RUN="true"
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Main execution
main() {
    echo -e "${GREEN}======================================${NC}"
    echo -e "${GREEN}Hybrid Search RAG - Kubernetes Deployment${NC}"
    echo -e "${GREEN}======================================${NC}"
    echo ""
    echo -e "Cluster: ${YELLOW}$CLUSTER_NAME${NC}"
    echo -e "Region: ${YELLOW}$AWS_REGION${NC}"
    echo -e "Namespace: ${YELLOW}$NAMESPACE${NC}"
    echo -e "Image Tag: ${YELLOW}$IMAGE_TAG${NC}"
    echo -e "Dry Run: ${YELLOW}$DRY_RUN${NC}"
    echo ""

    check_prerequisites
    configure_kubeconfig
    install_prerequisites
    update_image_references
    apply_manifests
    verify_deployment

    echo ""
    echo -e "${GREEN}======================================${NC}"
    echo -e "${GREEN}Deployment Complete!${NC}"
    echo -e "${GREEN}======================================${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Verify all pods are running: kubectl get pods -n $NAMESPACE"
    echo "  2. Check logs: kubectl logs -f deployment/hybrid-rag-api -n $NAMESPACE"
    echo "  3. Test API health: curl http://\$ALB_URL/health"
    echo "  4. Access API docs: http://\$ALB_URL/docs"
    echo ""
}

# Run main function
main
