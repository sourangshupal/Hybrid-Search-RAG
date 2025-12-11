# Architecture Documentation

Comprehensive architecture overview of the Hybrid Search RAG system.

## Table of Contents

- [System Overview](#system-overview)
- [Component Architecture](#component-architecture)
- [Data Flow](#data-flow)
- [Technology Stack](#technology-stack)
- [Deployment Architecture](#deployment-architecture)
- [Scaling Strategy](#scaling-strategy)
- [Security Architecture](#security-architecture)

## System Overview

The Hybrid Search RAG system is designed as a production-ready, scalable platform for academic paper search and question answering. It combines lexical (BM25) and semantic (vector) search with LLM-powered generation.

### High-Level Architecture

```
┌───────────────────────────────────────────────────────────────┐
│                         Users / Clients                        │
└──────────────────┬────────────────────────────────────────────┘
                   │
                   ↓
┌──────────────────────────────────────────────────────────────┐
│                    Load Balancer (AWS ALB)                    │
│                  - SSL Termination                            │
│                  - Health Checks                              │
│                  - Rate Limiting                              │
└──────────────────┬───────────────────────────────────────────┘
                   │
                   ↓
┌──────────────────────────────────────────────────────────────┐
│              API Layer (FastAPI + Uvicorn)                    │
│                                                               │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  Document   │  │    Search    │  │  RAG Query   │       │
│  │ Management  │  │  Endpoints   │  │  Endpoint    │       │
│  └─────────────┘  └──────────────┘  └──────────────┘       │
└──────────────────┬───────────────────────────────────────────┘
                   │
       ┌───────────┼───────────┐
       │           │           │
       ↓           ↓           ↓
┌─────────┐ ┌──────────┐ ┌──────────┐
│  Redis  │ │  Qdrant  │ │  Elastic │
│  Cache  │ │  Vector  │ │  Search  │
└─────────┘ └──────────┘ └──────────┘
       │           │           │
       └───────────┼───────────┘
                   │
                   ↓
┌──────────────────────────────────────────────────────────────┐
│                    Processing Layer                           │
│                                                               │
│  ┌────────┐  ┌──────────┐  ┌───────────┐  ┌──────────┐    │
│  │Parsing │→ │Chunking  │→ │Embedding  │→ │Indexing  │    │
│  │(Docling)│  │(Chonkie) │  │(BGE)      │  │(Dual)    │    │
│  └────────┘  └──────────┘  └───────────┘  └──────────┘    │
└──────────────────────────────────────────────────────────────┘
                   │
                   ↓
┌──────────────────────────────────────────────────────────────┐
│                  LLM Generation Layer                         │
│                                                               │
│  ┌────────────────┐          ┌──────────────┐              │
│  │  Claude API    │  ←───→   │  Cohere      │              │
│  │  (Primary)     │          │  Reranking   │              │
│  └────────────────┘          └──────────────┘              │
│                                                               │
│  ┌────────────────┐                                         │
│  │  OpenAI API    │                                         │
│  │  (Fallback)    │                                         │
│  └────────────────┘                                         │
└──────────────────────────────────────────────────────────────┘
```

## Component Architecture

### 1. API Layer

**Framework**: FastAPI (async)

**Components**:
- **Document Routes**: Upload, ingest, retrieve, delete
- **Search Routes**: Semantic, lexical, hybrid
- **Query Routes**: RAG query, history
- **System Routes**: Health, metrics, info

**Key Features**:
- Async/await throughout
- Pydantic validation
- OpenAPI documentation
- Error handling middleware
- Logging middleware
- CORS support

### 2. Document Processing Pipeline

```
Document → Parser → Chunker → Embedder → Indexer
```

**Parser (Docling)**:
- Supports: PDF, DOCX, HTML, TXT, Markdown
- Extracts: Text, equations (LaTeX), tables, figures
- Metadata: Title, authors, references, sections

**Chunker (Chonkie)**:
- **Token Chunker**: Fixed-size chunks with overlap
- **Semantic Chunker**: Meaning-based boundaries
- **SDPM Chunker**: Sentence-based for long papers
- **Academic Chunker**: Section-aware, preserves structure

**Embedder (BGE)**:
- Model: BAAI/bge-base-en-v1.5
- Dimensions: 768
- Batch processing (32 per batch)
- GPU acceleration (FP16)
- In-memory cache with TTL

**Indexer**:
- **Dual Indexing**: Qdrant (vector) + Elasticsearch (BM25)
- **Parallel**: Both indices updated simultaneously
- **Metadata**: Enriched with document info
- **Retry Logic**: Handles failures gracefully

### 3. Search & Retrieval

**Hybrid Search Algorithm**:

```python
1. Parallel Execution:
   - Semantic Search (Qdrant) → vectors
   - Lexical Search (Elasticsearch) → scores

2. Reciprocal Rank Fusion (RRF):
   score = Σ(1 / (k + rank))
   where k = 60 (constant)

3. Alpha Weighting:
   final_score = alpha * semantic + (1-alpha) * lexical
   where alpha ∈ [0, 1]

4. Deduplication:
   Remove duplicate chunks

5. Reranking (Optional):
   Cohere Rerank API
```

**Vector Search (Qdrant)**:
- **Similarity**: Cosine
- **Index Type**: HNSW
- **M**: 16 (connections per layer)
- **EF Construct**: 100

**Lexical Search (Elasticsearch)**:
- **Algorithm**: BM25
- **Field Boosting**: title (2.0), abstract (1.5)
- **Analyzer**: Standard with stop words

### 4. RAG Pipeline

```
Query → Retrieval → Reranking → Context Formation → LLM → Answer
```

**Retrieval**:
- Top-k chunks (default: 5)
- Hybrid search with alpha=0.5
- Metadata filtering support

**Reranking**:
- Cohere Rerank API
- Top-20 candidates → Top-5 results
- Relevance scores normalized

**Context Formation**:
- Chunk concatenation
- Citation markers insertion
- Context window management (8K tokens max)

**LLM Generation**:
- **Primary**: Claude Sonnet 4.5
- **Fallback**: GPT-4
- **Circuit Breaker**: Auto-failover on errors
- **Streaming**: Supported for real-time responses

### 5. Caching Strategy

**Multi-Level Caching**:

1. **Redis (L1 Cache)**:
   - Query results (1 hour TTL)
   - Document metadata (24 hours TTL)
   - Search results (30 minutes TTL)

2. **In-Memory (L2 Cache)**:
   - Embeddings (common queries)
   - Model weights
   - Configuration

3. **CDN (L3 Cache)**:
   - Static assets
   - Documentation

### 6. Observability

**Tracing (OPIK)**:
- RAG pipeline stages
- Retrieval latency
- Generation time
- Token usage

**Experiments (Comet ML)**:
- Chunking strategies
- Embedding models
- Search parameters
- A/B tests

**Logging (Loguru)**:
- Structured JSON logs
- Log levels by environment
- Sensitive data masking

**Metrics (CloudWatch)**:
- Request latency (p50, p95, p99)
- Error rates
- Cache hit rates
- Token usage

## Data Flow

### Document Ingestion Flow

```
1. Upload
   POST /api/v1/documents/upload
   → Save to S3
   → Return document_id

2. Ingest
   POST /api/v1/documents/ingest
   → Parse document (Docling)
   → Extract metadata
   → Chunk content (Chonkie)
   → Generate embeddings (BGE)
   → Index in Qdrant
   → Index in Elasticsearch
   → Return status

3. Status
   GET /api/v1/documents/{id}
   → Fetch from Redis cache
   → Or query databases
   → Return metadata
```

### Query Flow

```
1. Receive Query
   POST /api/v1/query
   → Validate input
   → Check cache (Redis)

2. Retrieval (if not cached)
   → Embed query (BGE)
   → Parallel search:
     - Qdrant (semantic)
     - Elasticsearch (lexical)
   → Reciprocal Rank Fusion
   → Rerank (Cohere)
   → Top-k selection

3. Generation
   → Format context
   → Call Claude API
   → If fails → Call OpenAI
   → Parse response
   → Extract citations

4. Response
   → Cache result
   → Log metrics
   → Return answer
```

## Technology Stack

### Core Technologies

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| API Framework | FastAPI | latest | REST API |
| Runtime | Python | 3.12+ | Core language |
| Package Manager | UV | latest | Dependency management |
| ASGI Server | Uvicorn | latest | Production server |
| Parser | Docling | latest | Document parsing |
| Chunker | Chonkie | latest | Advanced chunking |
| Embeddings | BGE | base-v1.5 | Vector embeddings |
| Vector DB | Qdrant | v1.7.4 | Semantic search |
| Search Engine | Elasticsearch | 8.11.3 | Lexical search |
| Cache | Redis | 7-alpine | Fast caching |
| LLM (Primary) | Claude | Sonnet 4.5 | Generation |
| LLM (Fallback) | GPT-4 | latest | Backup generation |
| Reranker | Cohere | latest | Result reranking |

### Infrastructure

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Container | Docker | Containerization |
| Orchestration | Kubernetes (EKS) | Container orchestration |
| Cloud | AWS | Infrastructure |
| Load Balancer | AWS ALB | Traffic distribution |
| Storage | AWS S3 | Object storage |
| Secrets | AWS Secrets Manager | API key management |
| Registry | Amazon ECR | Docker images |
| Monitoring | CloudWatch | Metrics and logs |
| CI/CD | GitHub Actions | Automation |

## Deployment Architecture

### Kubernetes Deployment

```
┌─────────────────────────────────────────────────────────────┐
│                    AWS EKS Cluster                           │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Namespace: hybrid-rag                              │   │
│  │                                                      │   │
│  │  ┌───────────────────────────────────────┐         │   │
│  │  │  Deployment: hybrid-rag-api           │         │   │
│  │  │  Replicas: 3-10 (HPA)                 │         │   │
│  │  │  Resources: 1-2 CPU, 2-4GB RAM        │         │   │
│  │  └───────────────────────────────────────┘         │   │
│  │                                                      │   │
│  │  ┌───────────────────────────────────────┐         │   │
│  │  │  StatefulSet: qdrant                  │         │   │
│  │  │  Replicas: 1                          │         │   │
│  │  │  Storage: 50Gi gp3                    │         │   │
│  │  └───────────────────────────────────────┘         │   │
│  │                                                      │   │
│  │  ┌───────────────────────────────────────┐         │   │
│  │  │  StatefulSet: elasticsearch           │         │   │
│  │  │  Replicas: 1                          │         │   │
│  │  │  Storage: 100Gi gp3                   │         │   │
│  │  └───────────────────────────────────────┘         │   │
│  │                                                      │   │
│  │  ┌───────────────────────────────────────┐         │   │
│  │  │  StatefulSet: redis                   │         │   │
│  │  │  Replicas: 1                          │         │   │
│  │  │  Storage: 20Gi gp3                    │         │   │
│  │  └───────────────────────────────────────┘         │   │
│  │                                                      │   │
│  │  ┌───────────────────────────────────────┐         │   │
│  │  │  HorizontalPodAutoscaler              │         │   │
│  │  │  Min: 3, Max: 10                      │         │   │
│  │  │  CPU Target: 70%                      │         │   │
│  │  │  Memory Target: 80%                   │         │   │
│  │  └───────────────────────────────────────┘         │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                 AWS Application Load Balancer                │
│  - SSL/TLS Termination                                      │
│  - Health Checks                                            │
│  - Cross-AZ Load Balancing                                  │
└─────────────────────────────────────────────────────────────┘
```

### High Availability

- **Multi-AZ Deployment**: Pods spread across availability zones
- **Auto-Scaling**: HPA scales based on CPU/memory
- **Health Checks**: Liveness, readiness, startup probes
- **Rolling Updates**: Zero-downtime deployments
- **Automatic Failover**: Pod restarts on failure

## Scaling Strategy

### Horizontal Scaling

**API Pods**:
- Min: 3 replicas
- Max: 10 replicas
- Triggers:
  - CPU > 70%
  - Memory > 80%
- Scale-up: Fast (30s stabilization)
- Scale-down: Slow (5min stabilization)

**Databases** (Future):
- Qdrant: Cluster mode
- Elasticsearch: Multi-node cluster
- Redis: Redis Cluster

### Vertical Scaling

Adjust resource limits based on load:

```yaml
resources:
  requests:
    cpu: "2000m"
    memory: "4Gi"
  limits:
    cpu: "4000m"
    memory: "8Gi"
```

### Performance Optimization

1. **Caching**: Redis for hot data
2. **Batch Processing**: Embeddings in batches
3. **Connection Pooling**: HTTP and database
4. **Circuit Breakers**: Prevent cascading failures
5. **Rate Limiting**: Protect from overload

## Security Architecture

### Authentication & Authorization

**Current**: None (local development)

**Production** (Recommended):
- API Keys: Service-to-service auth
- OAuth 2.0/JWT: User authentication
- RBAC: Role-based access control

### Data Security

**In Transit**:
- TLS 1.2+ for all external connections
- mTLS for internal service communication

**At Rest**:
- EBS encryption (AWS KMS)
- S3 encryption (SSE-S3 or SSE-KMS)
- Secrets in AWS Secrets Manager

### Network Security

- **VPC**: Private subnets for databases
- **Security Groups**: Least privilege
- **WAF**: Optional AWS WAF for ALB
- **DDoS Protection**: AWS Shield

### Application Security

- **Input Validation**: Pydantic models
- **Rate Limiting**: Per-endpoint limits
- **CORS**: Configurable origins
- **Error Handling**: No sensitive data in responses
- **Logging**: Sensitive data masking

## Design Principles

### Scalability

- Stateless API (scales horizontally)
- Async/await (high concurrency)
- Caching (reduces load)
- Auto-scaling (elastic capacity)

### Reliability

- Circuit breakers (fault tolerance)
- Retries with exponential backoff
- Health checks (self-healing)
- Graceful degradation

### Maintainability

- Clean code architecture
- Comprehensive tests
- Type hints throughout
- Documentation

### Observability

- Structured logging
- Distributed tracing
- Metrics collection
- Alerting

## Future Enhancements

- **Multi-tenancy**: Isolated namespaces per tenant
- **Advanced RAG**: Agentic RAG, iterative retrieval
- **Model Fine-tuning**: Domain-specific embeddings
- **Streaming**: Real-time answer generation
- **Multi-modal**: Image and table support

## Contact

For architecture questions:
- GitHub Issues: https://github.com/yourusername/hybrid-search-rag/issues
- Email: architecture@example.com
