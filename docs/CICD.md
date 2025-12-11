# CI/CD Pipeline Documentation

Complete guide for the automated CI/CD pipeline using GitHub Actions.

## Table of Contents

- [Overview](#overview)
- [Workflows](#workflows)
- [Setup](#setup)
- [Usage](#usage)
- [Deployment Process](#deployment-process)
- [Rollback Procedures](#rollback-procedures)
- [Troubleshooting](#troubleshooting)

## Overview

The CI/CD pipeline automates testing, building, and deployment of the Hybrid Search RAG system using GitHub Actions.

### Pipeline Architecture

```
Pull Request → CI Workflow → Tests + Build → Review
    ↓
Merge to main → CD Workflow → Build + Push to ECR → Deploy to Staging
    ↓
Create Tag (v*.*.*) → Deploy to Production → Smoke Tests
```

### Key Features

- **Automated Testing**: Unit, integration, and security tests
- **Code Quality**: Linting, formatting, and type checking
- **Docker Builds**: Multi-stage builds with caching
- **Security Scanning**: Trivy, Bandit, and Safety checks
- **Staged Deployments**: Staging → Production
- **Automated Rollbacks**: On deployment failures
- **Smoke Tests**: Post-deployment verification
- **Manual Controls**: Workflow dispatch for manual operations

## Workflows

### 1. CI Workflow (`.github/workflows/ci.yml`)

**Trigger**: Pull requests and pushes to main/develop

**Jobs**:
1. **Code Quality** (10 min)
   - Ruff linting
   - Ruff formatting
   - MyPy type checking
   - isort import checking

2. **Security Scan** (15 min)
   - Bandit security linter
   - Safety dependency scanner
   - Upload security reports

3. **Unit Tests** (20 min)
   - Run pytest with coverage
   - Upload to Codecov
   - Generate test reports

4. **Integration Tests** (30 min)
   - Spin up services (Qdrant, ES, Redis)
   - Run integration tests
   - Verify service connectivity

5. **Build Docker** (30 min)
   - Multi-stage Docker build
   - Trivy security scan
   - Upload SARIF to GitHub Security

6. **PR Comment** (PR only)
   - Post test results to PR
   - Summary of checks

7. **Build Summary**
   - Aggregate all results
   - Fail if critical jobs fail

### 2. CD Workflow (`.github/workflows/cd.yml`)

**Triggers**:
- Push to main
- Git tags (v*.*.*)
- Manual workflow dispatch

**Jobs**:
1. **Build and Push** (30 min)
   - Build Docker image
   - Push to Amazon ECR
   - Tag as latest and version
   - Scan with Trivy

2. **Deploy to Staging** (15 min)
   - Update EKS deployment
   - Wait for rollout
   - Run smoke tests
   - Rollback on failure

3. **Deploy to Production** (20 min)
   - Requires tag or manual trigger
   - Needs staging success
   - Create deployment backup
   - Update deployment
   - Run comprehensive tests
   - Rollback on failure

4. **Post-Deployment Monitoring** (10 min)
   - Monitor for 5 minutes
   - Check pod health
   - Check error logs
   - Create deployment summary

### 3. Rollback Workflow (`.github/workflows/rollback.yml`)

**Trigger**: Manual workflow dispatch

**Parameters**:
- `environment`: staging or production
- `revision`: Specific revision (optional)

**Steps**:
- Validate environment
- Get current deployment info
- Perform rollback
- Wait for completion
- Verify rollback
- Run health checks
- Create summary

### 4. Manual Deploy Workflow (`.github/workflows/manual-deploy.yml`)

**Trigger**: Manual workflow dispatch

**Parameters**:
- `environment`: staging or production
- `image-tag`: Docker image tag
- `skip-tests`: Skip smoke tests (optional)

**Steps**:
- Validate image exists in ECR
- Create deployment backup
- Update deployment
- Run smoke tests (if not skipped)
- Rollback on failure

## Setup

### 1. GitHub Secrets

Configure the following secrets in GitHub Settings → Secrets → Actions:

```bash
# AWS Credentials
AWS_ACCESS_KEY_ID         # AWS access key
AWS_SECRET_ACCESS_KEY     # AWS secret key

# API Keys (for integration tests)
ANTHROPIC_API_KEY         # Anthropic Claude API key
OPENAI_API_KEY            # OpenAI API key
COHERE_API_KEY            # Cohere API key
```

### 2. GitHub Environments

Create two environments with protection rules:

#### Staging Environment
- **Name**: `staging`
- **URL**: https://api-staging.hybrid-rag.example.com
- **Protection**: None (auto-deploy)
- **Secrets**: None required (uses repo secrets)

#### Production Environment
- **Name**: `production`
- **URL**: https://api.hybrid-rag.example.com
- **Protection Rules**:
  - ✅ Required reviewers: 1-2 team members
  - ✅ Wait timer: 0 minutes (or 5 for extra safety)
  - ✅ Allowed branches: Only tags matching `v*.*.*`
- **Secrets**: None required (uses repo secrets)

### 3. Branch Protection Rules

Configure for `main` branch:

```yaml
Settings → Branches → Branch protection rules → main

Protection rules:
✅ Require a pull request before merging
  ✅ Require approvals (1)
  ✅ Dismiss stale reviews
✅ Require status checks to pass
  ✅ Code Quality
  ✅ Security Scan
  ✅ Unit Tests
  ✅ Build Docker
✅ Require conversation resolution before merging
✅ Do not allow bypassing the above settings
```

### 4. AWS Infrastructure

Ensure the following AWS resources exist:

- **ECR Repository**: `hybrid-rag-api`
- **EKS Clusters**:
  - Staging: `hybrid-rag-staging`
  - Production: `hybrid-rag-cluster`
- **IAM Permissions**: GitHub Actions user needs:
  - ECR: Push/pull images
  - EKS: Describe clusters, update kubeconfig
  - Kubernetes: Update deployments via kubectl

### 5. Kubernetes Setup

Verify these are deployed:
- API deployment: `hybrid-rag-api` in namespace `hybrid-rag`
- Ingress: `hybrid-rag-ingress`
- All supporting services (Qdrant, ES, Redis)

## Usage

### Running CI on Pull Requests

1. **Create a branch**:
   ```bash
   git checkout -b feature/my-feature
   ```

2. **Make changes and commit**:
   ```bash
   git add .
   git commit -m "Add new feature"
   git push origin feature/my-feature
   ```

3. **Create Pull Request**:
   - Go to GitHub
   - Create PR from your branch to `main`
   - CI workflow runs automatically

4. **Review CI Results**:
   - Check the "Checks" tab
   - View test results in PR comment
   - Fix any failures

5. **Merge PR**:
   - Get approvals
   - Ensure all checks pass
   - Merge to main
   - CD workflow triggers automatically

### Deploying to Staging

**Automatic** (on merge to main):
1. Merge PR to main
2. CD workflow builds and pushes to ECR
3. Automatically deploys to staging
4. Runs smoke tests
5. Check deployment status

**Manual**:
1. Go to Actions → Manual Deployment
2. Click "Run workflow"
3. Select `staging`
4. Enter image tag (e.g., `v1.2.3`)
5. Run workflow

### Deploying to Production

**Via Git Tag** (Recommended):
1. Ensure staging is stable
2. Create and push tag:
   ```bash
   git tag -a v1.2.3 -m "Release version 1.2.3"
   git push origin v1.2.3
   ```
3. CD workflow triggers
4. Deploys to staging first
5. Requires manual approval for production
6. Approve in GitHub Actions
7. Deploys to production
8. Runs smoke tests and monitoring

**Manual Deployment**:
1. Go to Actions → Manual Deployment
2. Click "Run workflow"
3. Select `production`
4. Enter image tag
5. Requires approval
6. Approve deployment
7. Monitor progress

### Rolling Back

#### Via GitHub Actions

1. **Go to Actions → Rollback Deployment**
2. **Click "Run workflow"**
3. **Configure**:
   - Environment: `staging` or `production`
   - Revision: Leave empty for previous, or specify number
4. **Requires approval** (for production)
5. **Review and approve**
6. **Monitor rollback**

#### Via Command Line

```bash
# Rollback to previous version
./scripts/rollback.sh

# Rollback to specific revision
./scripts/rollback.sh 5

# Rollback on different cluster
CLUSTER_NAME=hybrid-rag-staging ./scripts/rollback.sh

# View rollout history
kubectl rollout history deployment/hybrid-rag-api -n hybrid-rag

# Check current status
kubectl get deployment hybrid-rag-api -n hybrid-rag -o wide
```

## Deployment Process

### Staging Deployment Flow

```
1. Merge to main
   ↓
2. Build Docker image
   ↓
3. Push to ECR (tags: version + latest)
   ↓
4. Update staging deployment
   ↓
5. Wait for rollout (5 min timeout)
   ↓
6. Run smoke tests (health endpoint)
   ↓
7. Success → Continue
   Failure → Auto-rollback
```

### Production Deployment Flow

```
1. Create git tag (v*.*.*)
   ↓
2. Build Docker image
   ↓
3. Deploy to staging (validation)
   ↓
4. Staging success → Request production approval
   ↓
5. Manual approval required
   ↓
6. Create deployment backup
   ↓
7. Update production deployment
   ↓
8. Wait for rollout (10 min timeout)
   ↓
9. Run smoke tests (health + API)
   ↓
10. Run integration tests
   ↓
11. 5-minute monitoring period
   ↓
12. Success → Create deployment tag
    Failure → Auto-rollback
```

## Rollback Procedures

### When to Rollback

- Health checks failing
- Increased error rates
- Performance degradation
- Failed smoke tests
- Unexpected behavior

### Automatic Rollback

Happens automatically on:
- Rollout timeout (5-10 minutes)
- Smoke test failures
- Health check failures

### Manual Rollback

#### Method 1: GitHub Actions (Recommended)

1. Navigate to Actions → Rollback Deployment
2. Run workflow:
   - Environment: `production`
   - Revision: (empty for previous)
3. Approve if required
4. Monitor rollback

#### Method 2: Command Line

```bash
# Quick rollback to previous
./scripts/rollback.sh

# Rollback to specific revision
# First, check history
kubectl rollout history deployment/hybrid-rag-api -n hybrid-rag

# Then rollback
./scripts/rollback.sh 7
```

#### Method 3: kubectl

```bash
# Connect to cluster
aws eks update-kubeconfig --name hybrid-rag-cluster --region us-east-1

# View history
kubectl rollout history deployment/hybrid-rag-api -n hybrid-rag

# Rollback to previous
kubectl rollout undo deployment/hybrid-rag-api -n hybrid-rag

# Rollback to specific revision
kubectl rollout undo deployment/hybrid-rag-api -n hybrid-rag --to-revision=7

# Monitor rollback
kubectl rollout status deployment/hybrid-rag-api -n hybrid-rag
```

### Post-Rollback Verification

```bash
# Check deployment status
kubectl get deployment hybrid-rag-api -n hybrid-rag

# Check pods
kubectl get pods -n hybrid-rag -l app=hybrid-rag-api

# Check logs
kubectl logs -f deployment/hybrid-rag-api -n hybrid-rag

# Test health endpoint
curl https://api.hybrid-rag.example.com/health
```

## Troubleshooting

### CI Failures

#### Tests Failing

```bash
# Run tests locally
source .venv/bin/activate
pytest tests/unit/ -v

# Check specific test
pytest tests/unit/test_embeddings.py -v

# Run with debugging
pytest tests/unit/ -v -s --pdb
```

#### Linting Errors

```bash
# Run Ruff locally
ruff check src/ tests/

# Auto-fix
ruff check src/ tests/ --fix

# Format code
ruff format src/ tests/
```

#### Type Checking Errors

```bash
# Run MyPy
mypy src/ --ignore-missing-imports

# Check specific file
mypy src/api/main.py
```

### CD Failures

#### Image Build Fails

Check:
- Dockerfile syntax
- Build context
- Available disk space
- Network connectivity

```bash
# Test build locally
docker build -f docker/Dockerfile -t test:latest .

# Build with no cache
docker build --no-cache -f docker/Dockerfile -t test:latest .
```

#### Push to ECR Fails

Check:
- AWS credentials
- ECR repository exists
- Permissions

```bash
# Test ECR login
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

# Verify repository
aws ecr describe-repositories --repository-names hybrid-rag-api
```

#### Deployment Timeout

Check:
- Pod events: `kubectl describe pod <pod-name> -n hybrid-rag`
- Resource availability: `kubectl get nodes`
- Image pull: `kubectl get events -n hybrid-rag`

```bash
# Check pod status
kubectl get pods -n hybrid-rag -l app=hybrid-rag-api

# View events
kubectl get events -n hybrid-rag --sort-by='.lastTimestamp'

# Check logs
kubectl logs <pod-name> -n hybrid-rag --previous
```

#### Smoke Tests Fail

Check:
- ALB health
- Service endpoints
- Application logs

```bash
# Get ALB URL
ALB_URL=$(kubectl get ingress hybrid-rag-ingress -n hybrid-rag -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

# Test manually
curl -v http://$ALB_URL/health

# Check ALB target health
aws elbv2 describe-target-health --target-group-arn <target-group-arn>
```

### Rollback Issues

#### Rollback Fails

```bash
# Check rollout status
kubectl rollout status deployment/hybrid-rag-api -n hybrid-rag

# View rollout history
kubectl rollout history deployment/hybrid-rag-api -n hybrid-rag

# Describe deployment
kubectl describe deployment hybrid-rag-api -n hybrid-rag

# Manual intervention
kubectl edit deployment hybrid-rag-api -n hybrid-rag
```

#### Previous Version Not Available

```bash
# Check available revisions
kubectl rollout history deployment/hybrid-rag-api -n hybrid-rag

# If no history, deploy specific image
kubectl set image deployment/hybrid-rag-api \
  api=ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/hybrid-rag-api:v1.0.0 \
  -n hybrid-rag
```

## Best Practices

### 1. Testing

- Run tests locally before pushing
- Write tests for new features
- Maintain >80% code coverage
- Test integration points

### 2. Versioning

- Use semantic versioning (v1.2.3)
- Tag releases properly
- Keep changelog updated
- Document breaking changes

### 3. Deployments

- Always deploy to staging first
- Monitor staging for at least 1 hour
- Deploy during low-traffic periods
- Have rollback plan ready
- Communicate with team

### 4. Monitoring

- Watch logs during deployment
- Monitor metrics for anomalies
- Set up alerts
- Review post-deployment reports

### 5. Security

- Scan images before deployment
- Keep dependencies updated
- Review security reports
- Rotate credentials regularly

## Workflow Reference

### Workflow Files

| File | Purpose | Trigger |
|------|---------|---------|
| `ci.yml` | Continuous Integration | PR, Push to main/develop |
| `cd.yml` | Continuous Deployment | Push to main, Tags |
| `rollback.yml` | Rollback deployments | Manual |
| `manual-deploy.yml` | Manual deployments | Manual |

### Common Commands

```bash
# View workflow runs
gh run list --workflow=ci.yml

# View specific run
gh run view <run-id>

# Rerun failed jobs
gh run rerun <run-id> --failed

# Cancel running workflow
gh run cancel <run-id>

# View logs
gh run view <run-id> --log

# Trigger manual workflow
gh workflow run manual-deploy.yml \
  -f environment=staging \
  -f image-tag=v1.2.3
```

## Contact

For CI/CD pipeline questions:
- GitHub Issues: https://github.com/yourusername/hybrid-search-rag/issues
- Email: devops@yourcompany.com
