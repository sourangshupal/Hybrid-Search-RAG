# GitHub Actions Setup Guide

Quick setup guide for CI/CD pipeline.

## Prerequisites

- GitHub repository with admin access
- AWS account with EKS clusters
- Docker images in ECR

## Step-by-Step Setup

### 1. Configure GitHub Secrets

Go to: **Settings → Secrets and variables → Actions → New repository secret**

Add these secrets:

```bash
AWS_ACCESS_KEY_ID          # Your AWS access key
AWS_SECRET_ACCESS_KEY      # Your AWS secret key
ANTHROPIC_API_KEY          # For integration tests
OPENAI_API_KEY             # For integration tests
COHERE_API_KEY             # For integration tests
```

### 2. Create Environments

Go to: **Settings → Environments → New environment**

#### Create "staging" environment:
- Name: `staging`
- Deployment URL: `https://api-staging.hybrid-rag.example.com`
- Protection rules: None

#### Create "production" environment:
- Name: `production`
- Deployment URL: `https://api.hybrid-rag.example.com`
- Protection rules:
  - ✅ Required reviewers: Add team members (1-2)
  - ✅ Deployment branches: Selected branches only → Add `v*.*.*` pattern

### 3. Configure Branch Protection

Go to: **Settings → Branches → Add branch protection rule**

Branch name pattern: `main`

Enable:
- ✅ Require a pull request before merging
  - ✅ Require approvals: 1
  - ✅ Dismiss stale pull request approvals when new commits are pushed
- ✅ Require status checks to pass before merging
  - ✅ Require branches to be up to date before merging
  - Add status checks:
    - `Code Quality`
    - `Security Scan`
    - `Unit Tests`
    - `Build Docker Image`
- ✅ Require conversation resolution before merging
- ✅ Do not allow bypassing the above settings

### 4. Update Workflow Variables

Edit workflow files to match your setup:

#### `.github/workflows/cd.yml`:
```yaml
env:
  AWS_REGION: us-east-1                          # Your AWS region
  ECR_REPOSITORY: hybrid-rag-api                 # Your ECR repo
  EKS_CLUSTER_STAGING: hybrid-rag-staging        # Your staging cluster
  EKS_CLUSTER_PRODUCTION: hybrid-rag-cluster     # Your production cluster
```

#### `.github/workflows/rollback.yml`:
```yaml
env:
  AWS_REGION: us-east-1                          # Your AWS region
  EKS_CLUSTER_STAGING: hybrid-rag-staging        # Your staging cluster
  EKS_CLUSTER_PRODUCTION: hybrid-rag-cluster     # Your production cluster
```

### 5. Verify AWS Setup

Ensure these exist:

```bash
# ECR repository
aws ecr describe-repositories --repository-names hybrid-rag-api

# EKS clusters
aws eks describe-cluster --name hybrid-rag-staging
aws eks describe-cluster --name hybrid-rag-cluster

# Kubernetes deployments
kubectl get deployment hybrid-rag-api -n hybrid-rag
```

### 6. Test CI Workflow

1. Create a test branch:
   ```bash
   git checkout -b test/ci-setup
   echo "# Test" >> README.md
   git commit -am "Test CI"
   git push origin test/ci-setup
   ```

2. Create pull request
3. Verify CI runs successfully
4. Close PR without merging

### 7. Test CD Workflow

1. Merge a change to main
2. Verify staging deployment
3. Check Actions tab for workflow status

### 8. Test Production Deployment

1. Create a test tag:
   ```bash
   git tag -a v0.0.1-test -m "Test production deployment"
   git push origin v0.0.1-test
   ```

2. Monitor deployment in Actions
3. Approve production deployment
4. Verify deployment
5. Delete test tag:
   ```bash
   git tag -d v0.0.1-test
   git push origin :refs/tags/v0.0.1-test
   ```

## Verification Checklist

- [ ] GitHub secrets configured
- [ ] Environments created (staging, production)
- [ ] Branch protection rules set
- [ ] Workflow variables updated
- [ ] AWS resources verified
- [ ] CI workflow tested
- [ ] CD staging deployment tested
- [ ] Production deployment tested
- [ ] Rollback workflow tested

## Troubleshooting

### Secrets Not Working

Check:
- Secret names match exactly (case-sensitive)
- Secrets are set at repository level, not environment
- No extra spaces in secret values

### Workflow Not Triggering

Check:
- Workflow files are in `.github/workflows/`
- YAML syntax is valid
- Branch/tag patterns match
- Repository has Actions enabled

### Deployment Fails

Check:
- AWS credentials are valid
- IAM permissions are correct
- EKS cluster is accessible
- Kubernetes resources exist

## Next Steps

1. Set up Codecov for coverage reports
2. Configure Slack/Discord notifications
3. Add custom deployment gates
4. Set up monitoring dashboards
5. Configure cost alerts

## Support

- Documentation: [CICD.md](../docs/CICD.md)
- Issues: https://github.com/yourusername/hybrid-search-rag/issues
