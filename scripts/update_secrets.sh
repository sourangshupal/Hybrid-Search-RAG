#!/bin/bash

# Script to update AWS Secrets Manager with API keys
# Usage: ./scripts/update_secrets.sh

set -e

AWS_REGION=${AWS_REGION:-"us-east-1"}
ENVIRONMENT=${ENVIRONMENT:-"dev"}
SECRETS_NAME="hybrid-rag-secrets-${ENVIRONMENT}"

echo "Updating secrets in: ${SECRETS_NAME}"
echo "Region: ${AWS_REGION}"
echo ""

# Prompt for API keys
read -p "Enter Anthropic API key: " ANTHROPIC_KEY
read -p "Enter OpenAI API key: " OPENAI_KEY
read -p "Enter Cohere API key: " COHERE_KEY
read -p "Enter Comet ML API key: " COMET_KEY

# Create JSON payload
SECRET_JSON=$(cat <<EOF
{
    "anthropic_api_key": "${ANTHROPIC_KEY}",
    "openai_api_key": "${OPENAI_KEY}",
    "cohere_api_key": "${COHERE_KEY}",
    "comet_ml_api_key": "${COMET_KEY}"
}
EOF
)

# Update secret
echo "Updating secret..."
aws secretsmanager update-secret \
    --secret-id "${SECRETS_NAME}" \
    --secret-string "${SECRET_JSON}" \
    --region "${AWS_REGION}"

echo "✓ Secrets updated successfully!"
