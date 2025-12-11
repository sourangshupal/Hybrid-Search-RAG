# Docker Deployment Guide

This guide covers Docker containerization and deployment of the Hybrid Search RAG system.

## Table of Contents

- [Quick Start](#quick-start)
- [Building Images](#building-images)
- [Running with Docker Compose](#running-with-docker-compose)
- [Configuration](#configuration)
- [Health Checks](#health-checks)
- [Scaling](#scaling)
- [Troubleshooting](#troubleshooting)

## Quick Start

### Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- 8GB+ RAM available
- API keys (Anthropic, OpenAI, Cohere)

### Start All Services

```bash
# Navigate to docker directory
cd docker

# Create .env file
cp ../.env.example .env
# Edit .env with your API keys

# Start all services
docker-compose -f docker-compose.prod.yml up -d

# Check status
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f api
```

### Access the API

- API: http://localhost:8000
- Docs: http://localhost:8000/docs
- Health: http://localhost:8000/health
- Metrics: http://localhost:8000/metrics

## Building Images

### Build Production Image

```bash
# Build with default settings
docker build -f docker/Dockerfile -t hybrid-rag-api:latest .

# Build with build args
docker build -f docker/Dockerfile \
  --build-arg BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ") \
  --build-arg VCS_REF=$(git rev-parse --short HEAD) \
  --build-arg VERSION=1.0.0 \
  -t hybrid-rag-api:1.0.0 .
```

### Multi-Architecture Build

```bash
# Build for multiple platforms
docker buildx build -f docker/Dockerfile \
  --platform linux/amd64,linux/arm64 \
  -t hybrid-rag-api:latest \
  --push .
```

### Image Size Optimization

The multi-stage Dockerfile optimizes image size:

**Stage 1 (Builder)**: ~1.5GB
- Python 3.12 with build tools
- UV package manager
- All dependencies

**Stage 2 (Runtime)**: ~800MB
- Python 3.12 slim
- Virtual environment only
- No build tools

**Final Image**: ~800MB (optimized)

### Inspect Image

```bash
# View image details
docker inspect hybrid-rag-api:latest

# View layers
docker history hybrid-rag-api:latest

# Check size
docker images hybrid-rag-api
```

## Running with Docker Compose

### Production Stack

```bash
# Start all services
docker-compose -f docker/docker-compose.prod.yml up -d

# Services started:
# - api: Hybrid RAG API (port 8000)
# - qdrant: Vector database (ports 6333, 6334)
# - elasticsearch: Lexical search (ports 9200, 9300)
# - redis: Cache (port 6379)
```

### With Nginx (Optional)

```bash
# Start with Nginx reverse proxy
docker-compose -f docker/docker-compose.prod.yml --profile with-nginx up -d

# Nginx available at:
# - HTTP: http://localhost:80
# - HTTPS: https://localhost:443 (requires SSL setup)
```

### Scaling API Instances

```bash
# Scale to 3 API instances
docker-compose -f docker/docker-compose.prod.yml up -d --scale api=3

# Note: Requires load balancer (Nginx) for distribution
```

### Stop Services

```bash
# Stop all services
docker-compose -f docker/docker-compose.prod.yml stop

# Stop and remove containers
docker-compose -f docker/docker-compose.prod.yml down

# Remove volumes (WARNING: deletes data)
docker-compose -f docker/docker-compose.prod.yml down -v
```

## Configuration

### Environment Variables

Create `.env` file in docker directory:

```bash
# Application
ENVIRONMENT=production
LOG_LEVEL=INFO
VERSION=1.0.0

# API Keys
ANTHROPIC_API_KEY=your_anthropic_key
OPENAI_API_KEY=your_openai_key
COHERE_API_KEY=your_cohere_key
COMET_API_KEY=your_comet_key  # Optional

# AWS (Optional)
AWS_REGION=us-east-1
AWS_S3_BUCKET=your-bucket
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key

# Performance
ENABLE_TRACING=false
ENABLE_COMET_TRACKING=false
```

### Resource Limits

Configure in `docker-compose.prod.yml`:

```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 4G
    reservations:
      cpus: '1.0'
      memory: 2G
```

### Volume Mounts

**Persistent Volumes:**
- `qdrant-data`: Vector database storage
- `elasticsearch-data`: Elasticsearch indices
- `redis-data`: Redis persistence
- `api-logs`: Application logs
- `api-data`: Application data
- `api-models`: Cached models

**Bind Mounts:**
```yaml
volumes:
  - ./configs:/app/configs:ro  # Configuration files
  - ./logs:/app/logs  # Logs directory
```

## Health Checks

### Built-in Health Checks

All services have health checks configured:

```bash
# Check health status
docker-compose -f docker/docker-compose.prod.yml ps

# Healthy output:
# NAME                STATUS
# hybrid-rag-api      Up (healthy)
# qdrant              Up (healthy)
# elasticsearch       Up (healthy)
# redis               Up (healthy)
```

### Manual Health Checks

```bash
# API health
curl http://localhost:8000/health

# Qdrant health
curl http://localhost:6333/healthz

# Elasticsearch health
curl http://localhost:9200/_cluster/health

# Redis health
docker exec redis redis-cli ping
```

### Health Check Configuration

In Dockerfile:
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1
```

Parameters:
- **interval**: 30s (check every 30 seconds)
- **timeout**: 10s (max time for check)
- **start-period**: 40s (grace period on startup)
- **retries**: 3 (failures before unhealthy)

## Logs

### View Logs

```bash
# All services
docker-compose -f docker/docker-compose.prod.yml logs -f

# Specific service
docker-compose -f docker/docker-compose.prod.yml logs -f api

# Last 100 lines
docker-compose -f docker/docker-compose.prod.yml logs --tail=100 api

# Since timestamp
docker-compose -f docker/docker-compose.prod.yml logs --since 2024-01-01T00:00:00Z api
```

### Log Configuration

Logs are written to:
- **Container**: stdout/stderr
- **Volume**: `/app/logs` (mounted to `api-logs` volume)

Access persisted logs:
```bash
# List log files
docker exec hybrid-rag-api ls -lh /app/logs

# View log file
docker exec hybrid-rag-api cat /app/logs/app.log
```

## Pushing to Registry

### Docker Hub

```bash
# Tag image
docker tag hybrid-rag-api:latest yourusername/hybrid-rag-api:latest

# Login
docker login

# Push
docker push yourusername/hybrid-rag-api:latest
```

### Amazon ECR

```bash
# Create repository
aws ecr create-repository --repository-name hybrid-rag-api

# Get login token
aws ecr get-login-password --region us-east-1 | \
    docker login --username AWS --password-stdin \
    <account-id>.dkr.ecr.us-east-1.amazonaws.com

# Tag image
docker tag hybrid-rag-api:latest \
    <account-id>.dkr.ecr.us-east-1.amazonaws.com/hybrid-rag-api:latest

# Push
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/hybrid-rag-api:latest
```

### GitHub Container Registry

```bash
# Login
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Tag
docker tag hybrid-rag-api:latest ghcr.io/username/hybrid-rag-api:latest

# Push
docker push ghcr.io/username/hybrid-rag-api:latest
```

## Scaling

### Horizontal Scaling

#### With Docker Compose

```bash
# Scale API to 4 instances
docker-compose -f docker/docker-compose.prod.yml up -d --scale api=4
```

**Requirements:**
- Load balancer (Nginx) for traffic distribution
- Shared state (Redis, Qdrant, Elasticsearch)
- Stateless API design

#### With Docker Swarm

```bash
# Initialize swarm
docker swarm init

# Deploy stack
docker stack deploy -c docker/docker-compose.prod.yml rag-stack

# Scale service
docker service scale rag-stack_api=4

# Check status
docker service ps rag-stack_api
```

### Vertical Scaling

Increase resources in `docker-compose.prod.yml`:

```yaml
api:
  deploy:
    resources:
      limits:
        cpus: '4.0'      # Increased from 2.0
        memory: 8G       # Increased from 4G
      reservations:
        cpus: '2.0'
        memory: 4G
```

## Monitoring

### Container Stats

```bash
# Real-time stats
docker stats

# Specific container
docker stats hybrid-rag-api

# One-time output
docker stats --no-stream
```

### Inspect Container

```bash
# Container details
docker inspect hybrid-rag-api

# Network info
docker network inspect rag-network

# Volume info
docker volume inspect qdrant-data
```

### Metrics Endpoint

```bash
# Application metrics
curl http://localhost:8000/metrics

# Prometheus format
curl http://localhost:8000/metrics?format=prometheus
```

## Troubleshooting

### Container Won't Start

**Check logs:**
```bash
docker-compose -f docker/docker-compose.prod.yml logs api
```

**Common issues:**
- Missing environment variables
- Port conflicts
- Insufficient resources
- Dependency services not healthy

**Solutions:**
```bash
# Check environment
docker-compose -f docker/docker-compose.prod.yml config

# Check port usage
netstat -tulpn | grep 8000

# Check resources
docker system df
```

### Unhealthy Container

**Check health status:**
```bash
docker inspect hybrid-rag-api --format='{{.State.Health.Status}}'
```

**View health logs:**
```bash
docker inspect hybrid-rag-api --format='{{json .State.Health}}' | jq
```

**Solutions:**
- Increase start-period in health check
- Check application logs
- Verify dependencies are healthy
- Restart container

### Out of Memory

**Symptoms:**
- Container exits with code 137
- OOMKilled in docker inspect

**Solutions:**
```bash
# Increase memory limit
# Edit docker-compose.prod.yml:
deploy:
  resources:
    limits:
      memory: 8G  # Increase from 4G

# Apply changes
docker-compose -f docker/docker-compose.prod.yml up -d
```

### Slow Performance

**Check resource usage:**
```bash
docker stats hybrid-rag-api
```

**Solutions:**
- Increase CPU/memory limits
- Enable Redis caching
- Scale horizontally
- Optimize query patterns

### Volume Permissions

**Issue:** Permission denied errors

**Solution:**
```bash
# Fix ownership
docker exec -u root hybrid-rag-api chown -R appuser:appuser /app/logs

# Or recreate with correct permissions
docker-compose -f docker/docker-compose.prod.yml down -v
docker-compose -f docker/docker-compose.prod.yml up -d
```

## Security Best Practices

### 1. Non-Root User

Dockerfile runs as non-root user (uid: 1000):
```dockerfile
USER appuser
```

### 2. Read-Only Filesystem

Mount configurations as read-only:
```yaml
volumes:
  - ./configs:/app/configs:ro
```

### 3. Secrets Management

**Docker Secrets (Swarm):**
```bash
echo "your_api_key" | docker secret create anthropic_key -
```

```yaml
secrets:
  - anthropic_key

environment:
  - ANTHROPIC_API_KEY_FILE=/run/secrets/anthropic_key
```

**AWS Secrets Manager:**
Use IAM roles and fetch secrets at runtime.

### 4. Network Isolation

Services communicate via private network:
```yaml
networks:
  rag-network:
    driver: bridge
```

### 5. Security Scanning

```bash
# Scan image for vulnerabilities
docker scan hybrid-rag-api:latest

# With Trivy
trivy image hybrid-rag-api:latest
```

## Backup and Recovery

### Backup Volumes

```bash
# Backup Qdrant data
docker run --rm -v qdrant-data:/data -v $(pwd):/backup alpine \
    tar czf /backup/qdrant-backup.tar.gz -C /data .

# Backup Elasticsearch data
docker run --rm -v elasticsearch-data:/data -v $(pwd):/backup alpine \
    tar czf /backup/elasticsearch-backup.tar.gz -C /data .

# Backup Redis data
docker run --rm -v redis-data:/data -v $(pwd):/backup alpine \
    tar czf /backup/redis-backup.tar.gz -C /data .
```

### Restore Volumes

```bash
# Restore Qdrant data
docker run --rm -v qdrant-data:/data -v $(pwd):/backup alpine \
    sh -c "cd /data && tar xzf /backup/qdrant-backup.tar.gz"

# Restart service
docker-compose -f docker/docker-compose.prod.yml restart qdrant
```

## Next Steps

- [Kubernetes Deployment](KUBERNETES.md)
- [CI/CD Pipeline](CICD.md)
- [Performance Optimization](OPTIMIZATION.md)

## Contact

For Docker-related questions:
- GitHub Issues: https://github.com/yourusername/hybrid-search-rag/issues
- Email: devops@yourcompany.com
