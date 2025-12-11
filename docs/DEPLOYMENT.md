```markdown
# Deployment Guide

This guide covers deploying the Hybrid Search RAG system to production environments.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Environment Configuration](#environment-configuration)
- [Local Development](#local-development)
- [Observability Setup](#observability-setup)
- [Docker Deployment](#docker-deployment)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Services

1. **Qdrant** - Vector database
   - Version: 1.7.0+
   - Port: 6333

2. **Elasticsearch** - Lexical search
   - Version: 8.11.0+
   - Port: 9200

3. **Redis** - Caching layer
   - Version: 7.0+
   - Port: 6379

4. **AWS Account** (for cloud deployment)
   - S3 buckets configured
   - Secrets Manager access
   - ECR repository
   - CloudWatch access

### API Keys Required

1. **Anthropic Claude API** - Primary LLM
2. **OpenAI API** - Fallback LLM
3. **Cohere API** - Reranking
4. **Comet ML API** (optional) - Experiment tracking

## Environment Configuration

### 1. Create `.env` file

```bash
# Copy from template
cp .env.example .env

# Edit with your values
vim .env
```

### 2. Required Environment Variables

```bash
# API Keys
ANTHROPIC_API_KEY=your_anthropic_key
OPENAI_API_KEY=your_openai_key
COHERE_API_KEY=your_cohere_key
COMET_API_KEY=your_comet_key  # Optional

# Database URLs
QDRANT_HOST=localhost
QDRANT_PORT=6333
ELASTICSEARCH_HOST=localhost
ELASTICSEARCH_PORT=9200
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=  # Optional

# AWS Configuration
AWS_REGION=us-east-1
AWS_S3_BUCKET=hybrid-rag-documents-dev
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret

# Application Settings
ENVIRONMENT=development  # development, staging, production
LOG_LEVEL=INFO
ENABLE_TRACING=true
ENABLE_COMET_TRACKING=false
```

## Local Development

### 1. Start Services with Docker Compose

```bash
cd docker
docker-compose up -d

# Verify services are running
docker-compose ps
```

### 2. Install Dependencies

```bash
# Using UV package manager
uv sync

# Activate virtual environment
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate  # Windows
```

### 3. Create Search Indices

```bash
python scripts/create_indices.py
```

### 4. Run API Server

```bash
# Development mode with hot reload
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Production mode
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 5. Access API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health Check: http://localhost:8000/health
- Metrics: http://localhost:8000/metrics

## Observability Setup

### OPIK Tracing

OPIK provides distributed tracing for RAG pipeline operations.

#### Installation

```bash
pip install opik
```

#### Configuration

```python
from src.utils.tracing import RAGTracer

# Initialize tracer
tracer = RAGTracer(
    project_name="hybrid-search-rag",
    enabled=True
)

# Use in RAG pipeline
async with tracer.trace_rag_query(
    query="Your query",
    max_results=20,
    use_reranking=True
) as ctx:
    result = await rag_pipeline.query(...)
```

#### Traced Operations

- **Retrieval**: Semantic, lexical, and hybrid search
- **Reranking**: Cohere reranking operations
- **Generation**: LLM generation with Claude/OpenAI
- **Embeddings**: BGE embedding generation
- **Full RAG Query**: End-to-end query execution

#### Viewing Traces

Traces are logged with structured metadata and can be viewed in the OPIK dashboard.

### Comet ML Experiment Tracking

Comet ML tracks experiments and model performance.

#### Installation

```bash
pip install comet-ml
```

#### Configuration

```python
from src.utils.comet_tracking import CometExperimentTracker

# Initialize tracker
tracker = CometExperimentTracker(
    api_key="your_comet_api_key",
    project_name="hybrid-search-rag",
    workspace="your_workspace",
    enabled=True
)

# Start experiment
tracker.start_experiment(
    experiment_name="rag-evaluation-v1",
    tags=["production", "claude-sonnet-4.5"]
)

# Log RAG experiment
tracker.log_rag_experiment(
    query="query",
    query_type="methodological",
    num_chunks_retrieved=20,
    num_chunks_used=10,
    search_time_ms=150.0,
    reranking_time_ms=75.0,
    generation_time_ms=2000.0,
    total_time_ms=2225.0,
    model_used="claude-sonnet-4-5-20250929",
    input_tokens=5000,
    output_tokens=500,
    num_citations=3,
    fallback_used=False,
    validated=True
)

# End experiment
tracker.end_experiment()
```

#### Tracked Metrics

- **Chunking**: Chunker type, chunk sizes, document processing
- **Embeddings**: Model, dimensions, throughput
- **Search**: Query types, latencies, result counts
- **Generation**: Model usage, tokens, fallback rates
- **RAG Pipeline**: End-to-end metrics, validation rates
- **Evaluation**: MRR@10, Recall@K, NDCG, answer quality

### AWS CloudWatch Integration

CloudWatch provides centralized logging and metrics in AWS.

#### Configuration

```python
from src.utils.cloudwatch import initialize_cloudwatch

# Initialize CloudWatch
logger, metrics = initialize_cloudwatch(
    log_group_name="/aws/hybrid-search-rag",
    log_stream_name="api-production",
    metrics_namespace="HybridSearchRAG",
    region="us-east-1",
    enabled=True
)

# Log events
logger.log_api_request(
    request_id="req-123",
    method="POST",
    path="/api/v1/query",
    status_code=200,
    duration_ms=2500.0
)

# Put metrics
metrics.put_rag_latency(
    latency_ms=2500.0,
    model="claude-sonnet-4-5-20250929"
)
```

#### CloudWatch Dashboards

Create custom dashboards to visualize:

1. **API Metrics**
   - Request rates
   - Error rates
   - Latency percentiles (p50, p95, p99)

2. **Search Metrics**
   - Search query rates by type
   - Search latencies
   - Cache hit rates

3. **RAG Metrics**
   - RAG query rates
   - Model usage distribution
   - Token consumption
   - Fallback rates

4. **System Metrics**
   - CPU and memory usage
   - Service health checks
   - Error counts by type

#### Setting Up CloudWatch Alarms

```bash
# Example: High error rate alarm
aws cloudwatch put-metric-alarm \
  --alarm-name high-error-rate \
  --alarm-description "Alert when error rate exceeds 5%" \
  --metric-name ErrorCount \
  --namespace HybridSearchRAG \
  --statistic Average \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 5.0 \
  --comparison-operator GreaterThanThreshold

# Example: High latency alarm
aws cloudwatch put-metric-alarm \
  --alarm-name high-rag-latency \
  --alarm-description "Alert when p95 latency exceeds 5 seconds" \
  --metric-name RAGLatency \
  --namespace HybridSearchRAG \
  --statistic ExtendedStatistics \
  --extended-statistic p95 \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 5000.0 \
  --comparison-operator GreaterThanThreshold
```

### Structured Logging

All components use Loguru for structured logging.

#### Log Levels

- **DEBUG**: Detailed tracing information
- **INFO**: General informational messages
- **WARNING**: Warning messages (non-critical)
- **ERROR**: Error messages
- **CRITICAL**: Critical failures

#### Log Format

```json
{
  "timestamp": "2025-01-15T10:30:45.123Z",
  "level": "INFO",
  "message": "RAG query completed",
  "request_id": "req-abc123",
  "query": "How does BERT work?",
  "total_time_ms": 2500.5,
  "model_used": "claude-sonnet-4-5-20250929",
  "tokens": 5500
}
```

#### Custom Logging

```python
from loguru import logger

# Log with context
logger.info(
    "Search query executed",
    extra={
        "query": query,
        "search_type": "hybrid",
        "num_results": 20,
        "search_time_ms": 150.5
    }
)
```

### Performance Monitoring

#### Key Metrics to Monitor

1. **Latency Metrics**
   - p50 (median): Target < 1.5s
   - p95: Target < 3.0s
   - p99: Target < 5.0s

2. **Throughput Metrics**
   - Requests per second
   - Tokens per second
   - Cache hit rate

3. **Quality Metrics**
   - Validation pass rate
   - Fallback usage rate
   - Average citations per answer

4. **Cost Metrics**
   - Total tokens consumed
   - Token cost by model
   - Cache savings

#### Viewing Metrics

```bash
# API metrics endpoint
curl http://localhost:8000/metrics

# Example response
{
  "uptime_seconds": 3600,
  "requests": {
    "total": 1000,
    "successful": 980,
    "failed": 20,
    "success_rate": 98.0
  },
  "search": {
    "total_queries": 500,
    "avg_time_ms": 145.5,
    "p50": 120.0,
    "p95": 250.0,
    "p99": 400.0
  },
  "rag": {
    "total_queries": 300,
    "avg_time_ms": 2250.0,
    "claude_usage": 280,
    "openai_usage": 20,
    "fallback_rate": 6.67,
    "p50": 2000.0,
    "p95": 3500.0,
    "p99": 4800.0
  },
  "tokens": {
    "total_input": 1500000,
    "total_output": 150000,
    "total": 1650000,
    "avg_per_query": 5500
  }
}
```

## Docker Deployment

### Build Docker Image

```bash
# Build image
docker build -f docker/Dockerfile -t hybrid-rag-api:latest .

# Tag for ECR
docker tag hybrid-rag-api:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/hybrid-rag-api:latest

# Push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/hybrid-rag-api:latest
```

### Run with Docker Compose

```bash
cd docker
docker-compose -f docker-compose.prod.yml up -d
```

## Kubernetes Deployment

Detailed in Phase 15 of the implementation plan.

## Monitoring

### Health Checks

```bash
# API health
curl http://localhost:8000/health

# Response
{
  "status": "healthy",
  "timestamp": "2025-01-15T10:30:00Z",
  "version": "1.0.0",
  "components": {
    "api": "healthy",
    "redis": "healthy",
    "qdrant": "healthy",
    "elasticsearch": "healthy"
  }
}
```

### Metrics Dashboard

Access real-time metrics at: http://localhost:8000/metrics

## Troubleshooting

### Common Issues

#### 1. OPIK Connection Failed

**Error**: `Failed to initialize OPIK: Connection refused`

**Solution**:
- Ensure OPIK is installed: `pip install opik`
- Check OPIK server is running
- Verify network connectivity
- Set `ENABLE_TRACING=false` to disable if not needed

#### 2. CloudWatch Permissions

**Error**: `Failed to log event to CloudWatch: AccessDenied`

**Solution**:
- Verify AWS credentials are configured
- Check IAM permissions include:
  - `logs:CreateLogGroup`
  - `logs:CreateLogStream`
  - `logs:PutLogEvents`
  - `cloudwatch:PutMetricData`

#### 3. Comet ML Tracking Failed

**Error**: `Failed to start Comet experiment: Invalid API key`

**Solution**:
- Verify `COMET_API_KEY` is set correctly
- Check workspace and project names exist
- Set `ENABLE_COMET_TRACKING=false` to disable if not needed

#### 4. High Latency

**Issue**: p95 latency > 5 seconds

**Solutions**:
- Check Redis cache is working (cache hit rate)
- Reduce `max_chunks` in generation
- Enable connection pooling for Qdrant/Elasticsearch
- Consider horizontal scaling

#### 5. High Fallback Rate

**Issue**: OpenAI fallback rate > 20%

**Solutions**:
- Check Anthropic API key is valid
- Verify rate limits not exceeded
- Check Claude API health status
- Review error logs for specific failures

### Logs

```bash
# View API logs
docker logs -f hybrid-rag-api

# View specific component logs
docker logs -f qdrant
docker logs -f elasticsearch
docker logs -f redis

# Search logs for errors
docker logs hybrid-rag-api 2>&1 | grep ERROR

# View CloudWatch logs
aws logs tail /aws/hybrid-search-rag --follow
```

### Performance Optimization

1. **Enable Redis Caching**
   - Semantic search: 1 hour TTL
   - Hybrid search: 30 min TTL
   - RAG queries: 2 hour TTL

2. **Connection Pooling**
   - Qdrant: Max 10 connections
   - Elasticsearch: Max 10 connections
   - Redis: Max 10 connections

3. **Batch Processing**
   - Embeddings: Batch size 32
   - Reranking: Batch up to 100 documents

4. **Circuit Breakers**
   - Enable for all external services
   - Failure threshold: 5
   - Timeout: 60s
   - Half-open timeout: 30s

## Contact & Support

For issues and questions:
- GitHub Issues: https://github.com/yourusername/hybrid-search-rag/issues
- Email: support@yourcompany.com

## Next Steps

- [Phase 12: Evaluation](../docs/EVALUATION.md)
- [Phase 13: Performance Optimization](../docs/OPTIMIZATION.md)
- [Phase 14-15: Kubernetes Deployment](../docs/KUBERNETES.md)
```
