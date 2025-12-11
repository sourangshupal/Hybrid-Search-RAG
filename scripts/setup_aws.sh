#!/bin/bash

# Hybrid Search RAG - AWS Infrastructure Setup Script
# This script sets up all required AWS resources for the project

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
AWS_REGION=${AWS_REGION:-"us-east-1"}
ENVIRONMENT=${ENVIRONMENT:-"dev"}
PROJECT_NAME="hybrid-rag"

# Resource names
S3_DOCUMENTS_BUCKET="${PROJECT_NAME}-documents-${ENVIRONMENT}"
S3_LOGS_BUCKET="${PROJECT_NAME}-logs-${ENVIRONMENT}"
S3_ARTIFACTS_BUCKET="${PROJECT_NAME}-artifacts-${ENVIRONMENT}"
ECR_REPO_NAME="${PROJECT_NAME}-api"
SECRETS_NAME="${PROJECT_NAME}-secrets-${ENVIRONMENT}"
LOG_GROUP_API="/aws/ecs/${PROJECT_NAME}-api"
LOG_GROUP_EKS="/aws/eks/${PROJECT_NAME}-cluster"

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

# Check AWS CLI is installed
check_aws_cli() {
    log_info "Checking AWS CLI installation..."
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed. Please install it first."
        exit 1
    fi
    log_info "AWS CLI version: $(aws --version)"
}

# Check AWS credentials
check_aws_credentials() {
    log_info "Checking AWS credentials..."
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured. Please run 'aws configure'"
        exit 1
    fi
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    log_info "Using AWS Account: ${ACCOUNT_ID}"
}

# Create S3 buckets
create_s3_buckets() {
    log_info "Creating S3 buckets..."

    # Documents bucket (with versioning)
    if aws s3 ls "s3://${S3_DOCUMENTS_BUCKET}" 2>&1 | grep -q 'NoSuchBucket'; then
        log_info "Creating documents bucket: ${S3_DOCUMENTS_BUCKET}"
        aws s3 mb "s3://${S3_DOCUMENTS_BUCKET}" --region "${AWS_REGION}"
        aws s3api put-bucket-versioning \
            --bucket "${S3_DOCUMENTS_BUCKET}" \
            --versioning-configuration Status=Enabled

        # Add lifecycle policy for old versions
        cat > /tmp/lifecycle-policy.json <<EOF
{
    "Rules": [
        {
            "ID": "DeleteOldVersions",
            "Prefix": "",
            "Status": "Enabled",
            "NoncurrentVersionExpiration": {
                "NoncurrentDays": 90
            }
        }
    ]
}
EOF
        aws s3api put-bucket-lifecycle-configuration \
            --bucket "${S3_DOCUMENTS_BUCKET}" \
            --lifecycle-configuration file:///tmp/lifecycle-policy.json

        log_info "✓ Documents bucket created with versioning enabled"
    else
        log_warn "Documents bucket already exists: ${S3_DOCUMENTS_BUCKET}"
    fi

    # Logs bucket
    if aws s3 ls "s3://${S3_LOGS_BUCKET}" 2>&1 | grep -q 'NoSuchBucket'; then
        log_info "Creating logs bucket: ${S3_LOGS_BUCKET}"
        aws s3 mb "s3://${S3_LOGS_BUCKET}" --region "${AWS_REGION}"

        # Add lifecycle policy to delete old logs
        cat > /tmp/logs-lifecycle.json <<EOF
{
    "Rules": [
        {
            "ID": "DeleteOldLogs",
            "Prefix": "",
            "Status": "Enabled",
            "Expiration": {
                "Days": 30
            }
        }
    ]
}
EOF
        aws s3api put-bucket-lifecycle-configuration \
            --bucket "${S3_LOGS_BUCKET}" \
            --lifecycle-configuration file:///tmp/logs-lifecycle.json

        log_info "✓ Logs bucket created with 30-day retention"
    else
        log_warn "Logs bucket already exists: ${S3_LOGS_BUCKET}"
    fi

    # Artifacts bucket
    if aws s3 ls "s3://${S3_ARTIFACTS_BUCKET}" 2>&1 | grep -q 'NoSuchBucket'; then
        log_info "Creating artifacts bucket: ${S3_ARTIFACTS_BUCKET}"
        aws s3 mb "s3://${S3_ARTIFACTS_BUCKET}" --region "${AWS_REGION}"
        log_info "✓ Artifacts bucket created"
    else
        log_warn "Artifacts bucket already exists: ${S3_ARTIFACTS_BUCKET}"
    fi

    # Create folder structure in documents bucket
    log_info "Creating folder structure in documents bucket..."
    aws s3api put-object --bucket "${S3_DOCUMENTS_BUCKET}" --key raw/
    aws s3api put-object --bucket "${S3_DOCUMENTS_BUCKET}" --key parsed/
    aws s3api put-object --bucket "${S3_DOCUMENTS_BUCKET}" --key metadata/
}

# Create Secrets Manager secret
create_secrets_manager() {
    log_info "Creating AWS Secrets Manager secret..."

    # Check if secret exists
    if aws secretsmanager describe-secret --secret-id "${SECRETS_NAME}" --region "${AWS_REGION}" 2>&1 | grep -q 'ResourceNotFoundException'; then
        log_info "Creating secret: ${SECRETS_NAME}"

        # Create secret with placeholder values
        cat > /tmp/secrets.json <<EOF
{
    "anthropic_api_key": "REPLACE_WITH_YOUR_ANTHROPIC_API_KEY",
    "openai_api_key": "REPLACE_WITH_YOUR_OPENAI_API_KEY",
    "cohere_api_key": "REPLACE_WITH_YOUR_COHERE_API_KEY",
    "comet_ml_api_key": "REPLACE_WITH_YOUR_COMET_ML_API_KEY"
}
EOF

        aws secretsmanager create-secret \
            --name "${SECRETS_NAME}" \
            --description "API keys for Hybrid RAG ${ENVIRONMENT} environment" \
            --secret-string file:///tmp/secrets.json \
            --region "${AWS_REGION}"

        log_info "✓ Secrets Manager secret created"
        log_warn "⚠️  IMPORTANT: Update the secret values with your actual API keys using:"
        log_warn "    aws secretsmanager update-secret --secret-id ${SECRETS_NAME} --secret-string '{...}'"
    else
        log_warn "Secret already exists: ${SECRETS_NAME}"
    fi
}

# Create ECR repository
create_ecr_repository() {
    log_info "Creating ECR repository..."

    if aws ecr describe-repositories --repository-names "${ECR_REPO_NAME}" --region "${AWS_REGION}" 2>&1 | grep -q 'RepositoryNotFoundException'; then
        log_info "Creating ECR repository: ${ECR_REPO_NAME}"

        aws ecr create-repository \
            --repository-name "${ECR_REPO_NAME}" \
            --image-scanning-configuration scanOnPush=true \
            --region "${AWS_REGION}"

        # Set lifecycle policy to keep only last 10 images
        cat > /tmp/ecr-lifecycle.json <<EOF
{
    "rules": [
        {
            "rulePriority": 1,
            "description": "Keep last 10 images",
            "selection": {
                "tagStatus": "any",
                "countType": "imageCountMoreThan",
                "countNumber": 10
            },
            "action": {
                "type": "expire"
            }
        }
    ]
}
EOF

        aws ecr put-lifecycle-policy \
            --repository-name "${ECR_REPO_NAME}" \
            --lifecycle-policy-text file:///tmp/ecr-lifecycle.json \
            --region "${AWS_REGION}"

        ECR_URI=$(aws ecr describe-repositories --repository-names "${ECR_REPO_NAME}" --region "${AWS_REGION}" --query 'repositories[0].repositoryUri' --output text)
        log_info "✓ ECR repository created: ${ECR_URI}"
    else
        log_warn "ECR repository already exists: ${ECR_REPO_NAME}"
    fi
}

# Create CloudWatch log groups
create_cloudwatch_logs() {
    log_info "Creating CloudWatch log groups..."

    # API log group
    if ! aws logs describe-log-groups --log-group-name-prefix "${LOG_GROUP_API}" --region "${AWS_REGION}" 2>&1 | grep -q "${LOG_GROUP_API}"; then
        log_info "Creating log group: ${LOG_GROUP_API}"
        aws logs create-log-group --log-group-name "${LOG_GROUP_API}" --region "${AWS_REGION}"
        aws logs put-retention-policy --log-group-name "${LOG_GROUP_API}" --retention-in-days 30 --region "${AWS_REGION}"
        log_info "✓ API log group created (30-day retention)"
    else
        log_warn "Log group already exists: ${LOG_GROUP_API}"
    fi

    # EKS log group (for future use)
    if ! aws logs describe-log-groups --log-group-name-prefix "${LOG_GROUP_EKS}" --region "${AWS_REGION}" 2>&1 | grep -q "${LOG_GROUP_EKS}"; then
        log_info "Creating log group: ${LOG_GROUP_EKS}"
        aws logs create-log-group --log-group-name "${LOG_GROUP_EKS}" --region "${AWS_REGION}"
        aws logs put-retention-policy --log-group-name "${LOG_GROUP_EKS}" --retention-in-days 30 --region "${AWS_REGION}"
        log_info "✓ EKS log group created (30-day retention)"
    else
        log_warn "Log group already exists: ${LOG_GROUP_EKS}"
    fi
}

# Create CloudWatch alarms
create_cloudwatch_alarms() {
    log_info "Creating CloudWatch alarms..."

    # High cost alert
    log_info "Creating billing alarm for $50 threshold..."
    aws cloudwatch put-metric-alarm \
        --alarm-name "${PROJECT_NAME}-high-cost-${ENVIRONMENT}" \
        --alarm-description "Alert when estimated charges exceed $50" \
        --metric-name EstimatedCharges \
        --namespace AWS/Billing \
        --statistic Maximum \
        --period 21600 \
        --evaluation-periods 1 \
        --threshold 50 \
        --comparison-operator GreaterThanThreshold \
        --region us-east-1 2>/dev/null || log_warn "Billing alarm might require SNS topic"

    log_info "✓ CloudWatch alarms configured"
}

# Print summary
print_summary() {
    log_info "=========================================="
    log_info "AWS Infrastructure Setup Complete!"
    log_info "=========================================="
    echo ""
    log_info "S3 Buckets:"
    echo "  - Documents: s3://${S3_DOCUMENTS_BUCKET}"
    echo "  - Logs: s3://${S3_LOGS_BUCKET}"
    echo "  - Artifacts: s3://${S3_ARTIFACTS_BUCKET}"
    echo ""
    log_info "Secrets Manager:"
    echo "  - Secret: ${SECRETS_NAME}"
    echo ""
    log_info "ECR Repository:"
    ECR_URI=$(aws ecr describe-repositories --repository-names "${ECR_REPO_NAME}" --region "${AWS_REGION}" --query 'repositories[0].repositoryUri' --output text 2>/dev/null || echo "Not found")
    echo "  - Repository: ${ECR_URI}"
    echo ""
    log_info "CloudWatch:"
    echo "  - API Logs: ${LOG_GROUP_API}"
    echo "  - EKS Logs: ${LOG_GROUP_EKS}"
    echo ""
    log_warn "Next Steps:"
    echo "  1. Update Secrets Manager with your actual API keys"
    echo "  2. Run 'aws configure' to set AWS_REGION=${AWS_REGION} if not already set"
    echo "  3. Update .env file with S3 bucket names"
}

# Main execution
main() {
    log_info "Starting AWS infrastructure setup for ${PROJECT_NAME}-${ENVIRONMENT}..."
    log_info "Region: ${AWS_REGION}"
    echo ""

    check_aws_cli
    check_aws_credentials
    echo ""

    create_s3_buckets
    echo ""

    create_secrets_manager
    echo ""

    create_ecr_repository
    echo ""

    create_cloudwatch_logs
    echo ""

    create_cloudwatch_alarms
    echo ""

    print_summary
}

# Run main function
main
