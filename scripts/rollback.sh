#!/bin/bash
# Rollback script for Kubernetes deployment
# Can rollback to previous version or specific revision

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
CLUSTER_NAME="${CLUSTER_NAME:-hybrid-rag-cluster}"
AWS_REGION="${AWS_REGION:-us-east-1}"
NAMESPACE="hybrid-rag"
DEPLOYMENT="hybrid-rag-api"
REVISION="${1:-}"

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

show_usage() {
    cat <<EOF
Usage: $0 [REVISION]

Rollback Kubernetes deployment to previous or specific revision

ARGUMENTS:
    REVISION    Optional revision number to rollback to (default: previous)

EXAMPLES:
    # Rollback to previous version
    $0

    # Rollback to specific revision
    $0 5

    # Rollback with custom cluster
    CLUSTER_NAME=my-cluster AWS_REGION=us-west-2 $0

ENVIRONMENT VARIABLES:
    CLUSTER_NAME    EKS cluster name (default: hybrid-rag-cluster)
    AWS_REGION      AWS region (default: us-east-1)

EOF
}

check_prerequisites() {
    log_step "Checking prerequisites..."

    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl not found"
        exit 1
    fi

    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI not found"
        exit 1
    fi

    log_info "Prerequisites check passed"
}

configure_kubeconfig() {
    log_step "Configuring kubeconfig..."

    if ! aws eks update-kubeconfig --name "$CLUSTER_NAME" --region "$AWS_REGION" 2>/dev/null; then
        log_error "Failed to configure kubeconfig"
        exit 1
    fi

    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to cluster"
        exit 1
    fi

    log_info "Connected to cluster: $CLUSTER_NAME"
}

show_current_status() {
    log_step "Current deployment status..."

    echo ""
    log_info "Current deployment:"
    kubectl get deployment $DEPLOYMENT -n $NAMESPACE -o wide

    echo ""
    log_info "Current pods:"
    kubectl get pods -n $NAMESPACE -l app=$DEPLOYMENT

    echo ""
    log_info "Rollout history:"
    kubectl rollout history deployment/$DEPLOYMENT -n $NAMESPACE
}

confirm_rollback() {
    echo ""
    if [ -n "$REVISION" ]; then
        log_warn "About to rollback to revision: $REVISION"
    else
        log_warn "About to rollback to previous revision"
    fi

    read -p "Continue? (yes/no): " -r
    echo

    if [[ ! $REPLY =~ ^[Yy]es$ ]]; then
        log_info "Rollback cancelled"
        exit 0
    fi
}

perform_rollback() {
    log_step "Performing rollback..."

    # Create backup before rollback
    log_info "Creating backup of current deployment..."
    kubectl get deployment $DEPLOYMENT -n $NAMESPACE -o yaml > "deployment-backup-$(date +%Y%m%d-%H%M%S).yaml"

    # Perform rollback
    if [ -n "$REVISION" ]; then
        log_info "Rolling back to revision $REVISION..."
        kubectl rollout undo deployment/$DEPLOYMENT -n $NAMESPACE --to-revision=$REVISION
    else
        log_info "Rolling back to previous revision..."
        kubectl rollout undo deployment/$DEPLOYMENT -n $NAMESPACE
    fi
}

wait_for_rollback() {
    log_step "Waiting for rollback to complete..."

    if kubectl rollout status deployment/$DEPLOYMENT -n $NAMESPACE --timeout=10m; then
        log_info "Rollback completed successfully"
    else
        log_error "Rollback failed or timed out"
        exit 1
    fi
}

verify_rollback() {
    log_step "Verifying rollback..."

    echo ""
    log_info "Deployment after rollback:"
    kubectl get deployment $DEPLOYMENT -n $NAMESPACE -o wide

    echo ""
    log_info "Pods after rollback:"
    kubectl get pods -n $NAMESPACE -l app=$DEPLOYMENT

    echo ""
    log_info "Checking pod health..."

    # Wait for pods to be ready
    PODS_READY=$(kubectl get pods -n $NAMESPACE -l app=$DEPLOYMENT -o jsonpath='{.items[*].status.conditions[?(@.type=="Ready")].status}' | grep -o True | wc -l)
    PODS_TOTAL=$(kubectl get pods -n $NAMESPACE -l app=$DEPLOYMENT --no-headers | wc -l)

    if [ "$PODS_READY" -eq "$PODS_TOTAL" ]; then
        log_info "All pods are ready: $PODS_READY/$PODS_TOTAL"
    else
        log_warn "Not all pods are ready: $PODS_READY/$PODS_TOTAL"
    fi
}

test_health() {
    log_step "Testing health endpoints..."

    # Get ALB URL
    ALB_URL=$(kubectl get ingress hybrid-rag-ingress -n $NAMESPACE -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null)

    if [ -z "$ALB_URL" ]; then
        log_warn "Could not get ALB URL, skipping health check"
        return
    fi

    # Wait for ALB to update
    log_info "Waiting for ALB to update (30s)..."
    sleep 30

    # Test health endpoint
    log_info "Testing health endpoint..."
    if curl -f -s http://$ALB_URL/health > /dev/null 2>&1; then
        log_info "✅ Health check passed"
    else
        log_warn "⚠️ Health check failed (may need more time)"
    fi
}

show_rollback_summary() {
    echo ""
    echo -e "${GREEN}======================================${NC}"
    echo -e "${GREEN}Rollback Summary${NC}"
    echo -e "${GREEN}======================================${NC}"
    echo ""
    echo "Cluster: $CLUSTER_NAME"
    echo "Namespace: $NAMESPACE"
    echo "Deployment: $DEPLOYMENT"
    if [ -n "$REVISION" ]; then
        echo "Revision: $REVISION"
    else
        echo "Revision: Previous"
    fi
    echo "Timestamp: $(date -u +'%Y-%m-%d %H:%M:%S UTC')"
    echo ""

    # Show current revision
    CURRENT_REVISION=$(kubectl rollout history deployment/$DEPLOYMENT -n $NAMESPACE | tail -1 | awk '{print $1}')
    echo "Current revision: $CURRENT_REVISION"
    echo ""
}

# Main execution
main() {
    if [[ "$1" == "-h" || "$1" == "--help" ]]; then
        show_usage
        exit 0
    fi

    echo -e "${GREEN}======================================${NC}"
    echo -e "${GREEN}Kubernetes Deployment Rollback${NC}"
    echo -e "${GREEN}======================================${NC}"
    echo ""

    check_prerequisites
    configure_kubeconfig
    show_current_status
    confirm_rollback
    perform_rollback
    wait_for_rollback
    verify_rollback
    test_health
    show_rollback_summary

    echo -e "${GREEN}✅ Rollback completed successfully${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Monitor logs: kubectl logs -f deployment/$DEPLOYMENT -n $NAMESPACE"
    echo "  2. Check metrics: kubectl top pods -n $NAMESPACE"
    echo "  3. View history: kubectl rollout history deployment/$DEPLOYMENT -n $NAMESPACE"
    echo ""
}

# Run main
main "$@"
