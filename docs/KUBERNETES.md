# Kubernetes Deployment Guide

Complete guide for deploying Hybrid Search RAG on AWS EKS.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [EKS Cluster Setup](#eks-cluster-setup)
- [Deploy to Kubernetes](#deploy-to-kubernetes)
- [Configuration](#configuration)
- [Scaling](#scaling)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)
- [Maintenance](#maintenance)

## Overview

The Hybrid Search RAG system is deployed on AWS EKS with:

- **API Service**: 3-10 replicas (auto-scaling)
- **Qdrant**: Vector database (StatefulSet)
- **Elasticsearch**: Lexical search (StatefulSet)
- **Redis**: Cache layer (StatefulSet)
- **AWS Load Balancer**: ALB for internet-facing traffic
- **Auto-scaling**: HPA based on CPU/memory
- **Secrets**: AWS Secrets Manager via External Secrets Operator
- **Storage**: EBS volumes (gp3) and EFS for shared storage

### Architecture

```
Internet
    ↓
Application Load Balancer (ALB)
    ↓
Kubernetes Ingress
    ↓
API Service (ClusterIP)
    ↓
API Pods (3-10 replicas)
    ├→ Qdrant (StatefulSet)
    ├→ Elasticsearch (StatefulSet)
    └→ Redis (StatefulSet)
```

## Prerequisites

### Local Tools

```bash
# AWS CLI
aws --version  # v2.x or higher

# kubectl
kubectl version --client  # v1.28+

# eksctl (for cluster creation)
eksctl version  # 0.150.0+

# helm (for operators)
helm version  # v3.12.0+
```

### AWS Resources

1. **EKS Cluster**: v1.28 or higher
2. **VPC**: With public and private subnets
3. **IAM Roles**:
   - EKS cluster role
   - Node group role
   - ALB controller role
   - External Secrets role
4. **Secrets Manager**: API keys stored
5. **ECR Repository**: Docker image pushed
6. **S3 Buckets**: For logs and data

### Installed Operators

- AWS Load Balancer Controller
- External Secrets Operator
- Metrics Server
- EBS CSI Driver
- EFS CSI Driver (optional)

## EKS Cluster Setup

### Option 1: Create New Cluster with eksctl

```bash
# Create cluster configuration
cat > eks-cluster.yaml <<EOF
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: hybrid-rag-cluster
  region: us-east-1
  version: "1.28"

vpc:
  cidr: 10.0.0.0/16
  nat:
    gateway: Single

managedNodeGroups:
  - name: api-nodes
    instanceType: m5.2xlarge
    minSize: 3
    maxSize: 10
    desiredCapacity: 3
    volumeSize: 100
    volumeType: gp3
    labels:
      role: api
    tags:
      k8s.io/cluster-autoscaler/enabled: "true"
      k8s.io/cluster-autoscaler/hybrid-rag-cluster: "owned"
    iam:
      withAddonPolicies:
        autoScaler: true
        ebs: true
        efs: true
        albIngress: true
        cloudWatch: true

  - name: database-nodes
    instanceType: r5.2xlarge
    minSize: 3
    maxSize: 6
    desiredCapacity: 3
    volumeSize: 200
    volumeType: gp3
    labels:
      role: database
    taints:
      - key: database
        value: "true"
        effect: NoSchedule

cloudWatch:
  clusterLogging:
    enableTypes:
      - api
      - audit
      - authenticator
      - controllerManager
      - scheduler
    logRetentionInDays: 7

addons:
  - name: vpc-cni
  - name: coredns
  - name: kube-proxy
  - name: aws-ebs-csi-driver
    version: latest
EOF

# Create cluster (takes 15-20 minutes)
eksctl create cluster -f eks-cluster.yaml

# Verify cluster
kubectl get nodes
```

### Option 2: Use Existing Cluster

```bash
# Configure kubectl
aws eks update-kubeconfig --name <cluster-name> --region us-east-1

# Verify connection
kubectl cluster-info
kubectl get nodes
```

### Tag Subnets for ALB

```bash
# Tag public subnets (for internet-facing ALB)
aws ec2 create-tags \
  --resources subnet-xxxxx subnet-yyyyy \
  --tags Key=kubernetes.io/role/elb,Value=1

# Tag private subnets (for internal ALB)
aws ec2 create-tags \
  --resources subnet-aaaaa subnet-bbbbb \
  --tags Key=kubernetes.io/role/internal-elb,Value=1
```

## Deploy to Kubernetes

### Step 1: Install Prerequisites

```bash
# 1. AWS Load Balancer Controller
eksctl create iamserviceaccount \
  --cluster=hybrid-rag-cluster \
  --namespace=kube-system \
  --name=aws-load-balancer-controller \
  --attach-policy-arn=arn:aws:iam::aws:policy/ElasticLoadBalancingFullAccess \
  --approve

helm repo add eks https://aws.github.io/eks-charts
helm repo update

helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=hybrid-rag-cluster \
  --set serviceAccount.create=false \
  --set serviceAccount.name=aws-load-balancer-controller

# 2. External Secrets Operator
helm repo add external-secrets https://charts.external-secrets.io
helm repo update

helm install external-secrets external-secrets/external-secrets \
  -n external-secrets-system \
  --create-namespace \
  --set installCRDs=true

# 3. Metrics Server
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# 4. EBS CSI Driver
eksctl create iamserviceaccount \
  --name ebs-csi-controller-sa \
  --namespace kube-system \
  --cluster hybrid-rag-cluster \
  --attach-policy-arn arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy \
  --approve

kubectl apply -k "github.com/kubernetes-sigs/aws-ebs-csi-driver/deploy/kubernetes/overlays/stable/?ref=release-1.25"
```

### Step 2: Configure Secrets

```bash
# Store API keys in AWS Secrets Manager
aws secretsmanager create-secret \
  --name hybrid-rag/api-keys \
  --description "API keys for Hybrid RAG" \
  --secret-string '{
    "anthropic_api_key": "sk-ant-...",
    "openai_api_key": "sk-...",
    "cohere_api_key": "...",
    "comet_api_key": "..."
  }' \
  --region us-east-1

# Create IAM policy for External Secrets
cat > external-secrets-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ],
      "Resource": "arn:aws:secretsmanager:us-east-1:*:secret:hybrid-rag/*"
    }
  ]
}
EOF

aws iam create-policy \
  --policy-name HybridRAGSecretsPolicy \
  --policy-document file://external-secrets-policy.json

# Create IAM role for service account
eksctl create iamserviceaccount \
  --name hybrid-rag-api-sa \
  --namespace hybrid-rag \
  --cluster hybrid-rag-cluster \
  --attach-policy-arn arn:aws:iam::ACCOUNT_ID:policy/HybridRAGSecretsPolicy \
  --approve
```

### Step 3: Update Configuration

```bash
# Update k8s/deployments/api-deployment.yaml
# Replace ACCOUNT_ID with your AWS account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
sed -i "s/ACCOUNT_ID/$ACCOUNT_ID/g" k8s/deployments/api-deployment.yaml

# Update k8s/ingress/api-ingress.yaml
# Replace with your ACM certificate ARN
CERT_ARN="arn:aws:acm:us-east-1:ACCOUNT_ID:certificate/CERTIFICATE_ID"
sed -i "s|arn:aws:acm:us-east-1:ACCOUNT_ID:certificate/CERTIFICATE_ID|$CERT_ARN|g" k8s/ingress/api-ingress.yaml

# Update domain name
sed -i 's/api.hybrid-rag.example.com/your-domain.com/g' k8s/ingress/api-ingress.yaml

# Update EFS filesystem ID in storage/pvc.yaml (if using EFS)
EFS_ID=$(aws efs describe-file-systems --query "FileSystems[?Name=='hybrid-rag-efs'].FileSystemId" --output text)
sed -i "s/fs-XXXXXXXXX/$EFS_ID/g" k8s/storage/pvc.yaml
```

### Step 4: Deploy Using Script

```bash
# Automated deployment
./scripts/deploy_k8s.sh

# Or manually apply manifests
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/storage/pvc.yaml
kubectl apply -f k8s/configmaps/app-config.yaml
kubectl apply -f k8s/secrets/external-secret.yaml

# Wait for secrets to sync
sleep 30

# Deploy services
kubectl apply -f k8s/services/
kubectl apply -f k8s/deployments/redis-deployment.yaml
kubectl apply -f k8s/deployments/qdrant-deployment.yaml
kubectl apply -f k8s/deployments/elasticsearch-deployment.yaml

# Wait for databases
kubectl wait --for=condition=ready pod -l app=redis -n hybrid-rag --timeout=300s
kubectl wait --for=condition=ready pod -l app=qdrant -n hybrid-rag --timeout=300s
kubectl wait --for=condition=ready pod -l app=elasticsearch -n hybrid-rag --timeout=600s

# Deploy API
kubectl apply -f k8s/deployments/api-deployment.yaml
kubectl apply -f k8s/hpa/api-hpa.yaml
kubectl apply -f k8s/ingress/api-ingress.yaml
```

### Step 5: Verify Deployment

```bash
# Check all resources
kubectl get all -n hybrid-rag

# Check pods
kubectl get pods -n hybrid-rag

# Check services
kubectl get svc -n hybrid-rag

# Check ingress
kubectl get ingress -n hybrid-rag

# Get ALB URL
ALB_URL=$(kubectl get ingress hybrid-rag-ingress -n hybrid-rag -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
echo "API URL: http://$ALB_URL"

# Test health endpoint
curl http://$ALB_URL/health

# View logs
kubectl logs -f deployment/hybrid-rag-api -n hybrid-rag
```

## Configuration

### Environment Variables

Edit `k8s/configmaps/app-config.yaml`:

```yaml
data:
  ENVIRONMENT: "production"
  LOG_LEVEL: "INFO"
  AWS_REGION: "us-east-1"
  AWS_S3_BUCKET: "your-bucket"
  ENABLE_TRACING: "true"
```

Apply changes:
```bash
kubectl apply -f k8s/configmaps/app-config.yaml
kubectl rollout restart deployment/hybrid-rag-api -n hybrid-rag
```

### Resource Limits

Edit `k8s/deployments/api-deployment.yaml`:

```yaml
resources:
  requests:
    cpu: "2000m"     # Increase from 1000m
    memory: "4Gi"    # Increase from 2Gi
  limits:
    cpu: "4000m"     # Increase from 2000m
    memory: "8Gi"    # Increase from 4Gi
```

Apply changes:
```bash
kubectl apply -f k8s/deployments/api-deployment.yaml
```

### Storage Expansion

```bash
# Expand PVC (supported by gp3 storage class)
kubectl patch pvc qdrant-storage -n hybrid-rag -p '{"spec":{"resources":{"requests":{"storage":"100Gi"}}}}'

# Verify expansion
kubectl get pvc -n hybrid-rag
```

## Scaling

### Manual Scaling

```bash
# Scale API pods
kubectl scale deployment hybrid-rag-api -n hybrid-rag --replicas=5

# Verify scaling
kubectl get pods -n hybrid-rag -l app=hybrid-rag-api
```

### Auto-Scaling (HPA)

```bash
# View HPA status
kubectl get hpa -n hybrid-rag

# Describe HPA
kubectl describe hpa hybrid-rag-api-hpa -n hybrid-rag

# Edit HPA limits
kubectl edit hpa hybrid-rag-api-hpa -n hybrid-rag
# Change minReplicas and maxReplicas
```

### Cluster Auto-Scaling

```bash
# Install Cluster Autoscaler
kubectl apply -f https://raw.githubusercontent.com/kubernetes/autoscaler/master/cluster-autoscaler/cloudprovider/aws/examples/cluster-autoscaler-autodiscover.yaml

# Configure for your cluster
kubectl -n kube-system \
  annotate deployment.apps/cluster-autoscaler \
  cluster-autoscaler.kubernetes.io/safe-to-evict="false"

kubectl -n kube-system \
  set image deployment.apps/cluster-autoscaler \
  cluster-autoscaler=registry.k8s.io/autoscaling/cluster-autoscaler:v1.28.0

# Verify
kubectl logs -f deployment/cluster-autoscaler -n kube-system
```

## Monitoring

### Logs

```bash
# View API logs
kubectl logs -f deployment/hybrid-rag-api -n hybrid-rag

# View specific pod logs
kubectl logs <pod-name> -n hybrid-rag

# View previous container logs
kubectl logs <pod-name> -n hybrid-rag --previous

# Stream logs for all API pods
kubectl logs -f -l app=hybrid-rag-api -n hybrid-rag --all-containers=true
```

### Metrics

```bash
# Pod metrics
kubectl top pods -n hybrid-rag

# Node metrics
kubectl top nodes

# HPA metrics
kubectl get hpa -n hybrid-rag --watch
```

### Events

```bash
# View events
kubectl get events -n hybrid-rag --sort-by='.lastTimestamp'

# Watch events
kubectl get events -n hybrid-rag --watch
```

### CloudWatch Integration

```bash
# Install Fluent Bit for log forwarding
kubectl apply -f https://raw.githubusercontent.com/aws-samples/amazon-cloudwatch-container-insights/latest/k8s-deployment-manifest-templates/deployment-mode/daemonset/container-insights-monitoring/fluent-bit/fluent-bit.yaml

# View logs in CloudWatch
aws logs tail /aws/eks/hybrid-rag-cluster/application --follow
```

## Troubleshooting

### Pod Not Starting

```bash
# Check pod status
kubectl describe pod <pod-name> -n hybrid-rag

# Common issues:
# 1. Image pull errors
kubectl get events -n hybrid-rag | grep "Failed to pull image"

# Fix: Update image reference or ECR permissions
kubectl edit deployment hybrid-rag-api -n hybrid-rag

# 2. Secret not found
kubectl get secrets -n hybrid-rag

# Fix: Verify External Secrets
kubectl describe externalsecret hybrid-rag-api-keys -n hybrid-rag

# 3. Insufficient resources
kubectl describe nodes

# Fix: Scale cluster or reduce requests
```

### Load Balancer Not Created

```bash
# Check ingress status
kubectl describe ingress hybrid-rag-ingress -n hybrid-rag

# Check ALB controller logs
kubectl logs -f deployment/aws-load-balancer-controller -n kube-system

# Common issues:
# 1. Subnets not tagged
# Verify subnet tags (see "Tag Subnets" section)

# 2. IAM permissions
# Verify service account has correct role
kubectl describe sa aws-load-balancer-controller -n kube-system
```

### Database Connection Issues

```bash
# Check database pods
kubectl get pods -n hybrid-rag -l component=vector-database

# Test connectivity from API pod
kubectl exec -it <api-pod-name> -n hybrid-rag -- sh
# Inside pod:
nc -zv qdrant-service 6333
nc -zv elasticsearch-service 9200
nc -zv redis-service 6379

# Check service endpoints
kubectl get endpoints -n hybrid-rag
```

### High Latency

```bash
# Check pod resources
kubectl top pods -n hybrid-rag

# Check if pods are being throttled
kubectl describe pod <pod-name> -n hybrid-rag | grep -A 5 "Limits"

# Increase resources
kubectl edit deployment hybrid-rag-api -n hybrid-rag

# Check HPA status
kubectl describe hpa hybrid-rag-api-hpa -n hybrid-rag

# Check if more replicas are needed
kubectl get hpa -n hybrid-rag --watch
```

### Secret Sync Failures

```bash
# Check External Secrets status
kubectl describe externalsecret -n hybrid-rag

# Check SecretStore
kubectl describe secretstore -n hybrid-rag

# Verify IAM permissions
aws sts assume-role --role-arn <service-account-role-arn> --role-session-name test

# Manual secret creation (fallback)
kubectl create secret generic api-keys -n hybrid-rag \
  --from-literal=ANTHROPIC_API_KEY=sk-ant-... \
  --from-literal=OPENAI_API_KEY=sk-... \
  --from-literal=COHERE_API_KEY=...
```

## Maintenance

### Rolling Updates

```bash
# Update image tag
kubectl set image deployment/hybrid-rag-api hybrid-rag-api=ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/hybrid-rag-api:v1.2.0 -n hybrid-rag

# Monitor rollout
kubectl rollout status deployment/hybrid-rag-api -n hybrid-rag

# Rollback if needed
kubectl rollout undo deployment/hybrid-rag-api -n hybrid-rag

# View rollout history
kubectl rollout history deployment/hybrid-rag-api -n hybrid-rag
```

### Backup

```bash
# Backup Qdrant data
kubectl exec qdrant-0 -n hybrid-rag -- tar czf /tmp/qdrant-backup.tar.gz /qdrant/storage
kubectl cp hybrid-rag/qdrant-0:/tmp/qdrant-backup.tar.gz ./qdrant-backup.tar.gz

# Backup Elasticsearch indices
kubectl exec elasticsearch-0 -n hybrid-rag -- \
  curl -X POST "localhost:9200/_snapshot/my_backup/snapshot_1?wait_for_completion=true"

# Backup to S3
aws s3 cp qdrant-backup.tar.gz s3://hybrid-rag-backups/$(date +%Y%m%d)/
```

### Cleanup

```bash
# Delete all resources
kubectl delete namespace hybrid-rag

# Delete cluster (if needed)
eksctl delete cluster --name hybrid-rag-cluster --region us-east-1

# Delete associated resources
aws elbv2 describe-load-balancers --query "LoadBalancers[?starts_with(LoadBalancerName, 'k8s-hybridra')].LoadBalancerArn" | xargs -I {} aws elbv2 delete-load-balancer --load-balancer-arn {}

# Delete EBS volumes
aws ec2 describe-volumes --filters "Name=tag:kubernetes.io/cluster/hybrid-rag-cluster,Values=owned" --query "Volumes[].VolumeId" | xargs -I {} aws ec2 delete-volume --volume-id {}
```

## Best Practices

1. **Always use namespaces** for resource isolation
2. **Enable resource quotas** to prevent resource exhaustion
3. **Use Pod Disruption Budgets** for high availability
4. **Enable audit logging** for compliance
5. **Regular backups** of stateful data
6. **Monitor costs** with AWS Cost Explorer
7. **Use Spot instances** for cost optimization (non-production)
8. **Implement network policies** for security
9. **Regular security scans** with tools like kube-bench
10. **Use GitOps** for declarative deployments (ArgoCD, Flux)

## Cost Optimization

```bash
# Use Spot instances for non-critical workloads
# Add to node group configuration:
spot: true
instancesDistribution:
  maxPrice: 0.5
  onDemandBaseCapacity: 2
  onDemandPercentageAboveBaseCapacity: 30

# Use Fargate for specific workloads
eksctl create fargateprofile \
  --cluster hybrid-rag-cluster \
  --name api-fargate \
  --namespace hybrid-rag \
  --labels app=hybrid-rag-api

# Enable cluster autoscaler
# Scale down unused nodes automatically
```

## Security Hardening

```bash
# Enable Pod Security Standards
kubectl label namespace hybrid-rag pod-security.kubernetes.io/enforce=restricted

# Network Policies
kubectl apply -f - <<EOF
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-network-policy
  namespace: hybrid-rag
spec:
  podSelector:
    matchLabels:
      app: hybrid-rag-api
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              name: hybrid-rag
      ports:
        - protocol: TCP
          port: 8000
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              name: hybrid-rag
EOF

# Enable IRSA (IAM Roles for Service Accounts)
# Already configured in deployment script

# Scan images
trivy image ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/hybrid-rag-api:latest
```

## Contact

For Kubernetes deployment questions:
- GitHub Issues: https://github.com/yourusername/hybrid-search-rag/issues
- Email: devops@yourcompany.com
