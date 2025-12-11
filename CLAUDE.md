# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Hybrid Search RAG for Academic Research Papers** - A production-ready hybrid search RAG system combining BM25 (lexical) and semantic search with advanced chunking strategies, optimized for academic research papers.

**Status:** Early development phase - project structure not yet created
**Package Manager:** UV (Python 3.12)
**Timeline:** 12-week development (6 weeks MVP + 6 weeks enhancements)

## Technology Stack

### Core Technologies
- **Backend:** FastAPI with asyncio/uvicorn
- **Parser:** Docling (PDF, HTML, DOCX)
- **Chunking:** Chonkie (SemanticChunker, TokenChunker, SDPMChunker)
- **Embeddings:** BGE (BAAI/bge-base-en-v1.5, 768 dimensions)
- **Vector DB:** Qdrant (semantic search)
- **Search:** Elasticsearch (BM25 lexical search)
- **Reranker:** Cohere rerank-english-v3.0
- **LLM:** Anthropic Claude (primary), OpenAI GPT-4 (fallback)

### Infrastructure
- **Cloud:** AWS (US-East-1)
- **Storage:** S3 (documents, logs, artifacts)
- **Caching:** Redis
- **Container:** Docker, Amazon ECR
- **Orchestration:** Kubernetes (Amazon EKS) - Post-MVP
- **Observability:** Loguru (structured JSON logging), OPIK (tracing), Comet ML (experiments)

## Development Commands

### Environment Setup
```bash
# Install UV package manager (if not installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv sync

# Activate virtual environment
source .venv/bin/activate
```

### Local Services (Docker Compose)
```bash
# Start all local services (Qdrant, Elasticsearch, Redis)
docker-compose -f docker/docker-compose.yml up -d

# Stop services
docker-compose -f docker/docker-compose.yml down

# View logs
docker-compose -f docker/docker-compose.yml logs -f
```

### Running the API
```bash
# Development mode with hot reload
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Production mode
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html --cov-report=term

# Run specific test file
pytest tests/unit/test_chunking.py

# Run integration tests only
pytest tests/integration/

# Run with verbose output
pytest -v -s
```

### Code Quality
```bash
# Format code
ruff format .

# Lint code
ruff check .

# Type checking
mypy src/
```

### Load Testing
```bash
# Run Locust load tests
locust -f tests/load/locustfile.py --host=http://localhost:8000
```

## Architecture

### Document Processing Pipeline
```
File Upload → S3 (raw) → Format Detection → Parser Selection →
Text Extraction → Metadata Extraction → Preprocessing →
Quality Validation → S3 (parsed) → Chunking → Dual Indexing
```

### Chunking Strategy
The system implements three chunking approaches via Chonkie:
1. **TokenChunker:** Baseline fixed-token chunking
2. **SemanticChunker:** Primary method for standard documents
3. **SDPMChunker:** Advanced method for long academic papers (>10k tokens)

**Academic-specific chunking:**
- Section-aware: Preserves paper structure (Abstract, Methods, Results, etc.)
- Equation-aware: Keeps LaTeX equations intact with context
- Reference-aware: Maintains citation context
- Abstract handling: Stored as a single complete chunk

### Dual Indexing Architecture
Documents are indexed in parallel:
1. **Qdrant (Vector Store):** Semantic search via BGE embeddings (768-dim)
2. **Elasticsearch:** BM25 lexical search with academic field mappings

### Hybrid Search with Reciprocal Rank Fusion
```python
# Retrieval flow:
Query → Query Processing → Parallel Search (BM25 + Semantic) →
Reciprocal Rank Fusion → Cohere Reranking →
Claude Generation → Citation-backed Answer
```

### RAG Pipeline Flow
```
Query → Retrieval (Hybrid Search) → Reranking (Cohere) →
Context Formation → Prompt Construction →
LLM Generation (Claude/OpenAI) → Response with Citations
```

### API Structure
- `/api/v1/documents/` - Document ingestion endpoints
- `/api/v1/search/` - Search endpoints (lexical, semantic, hybrid)
- `/api/v1/query/` - RAG query endpoints
- `/api/v1/system/` - Health checks, metrics

## Academic Paper Considerations

### Document Characteristics
- **Format:** Primarily PDFs with LaTeX formatting
- **Structure:** Abstract, Introduction, Methods, Results, Discussion, References
- **Content:** Mathematical equations, figures, tables, citations
- **Length:** 8-40 pages typically
- **Metadata:** Authors, affiliations, publication date, journal/conference, DOI, arXiv ID

### Metadata Extraction Requirements
Extract and validate:
- Title, authors, affiliations
- Publication year, venue (journal/conference)
- DOI, arXiv ID
- Abstract and keywords
- Section structure
- Citation count (when available)

### Search Query Types
The system handles four primary query types:
1. **Methodological:** "What methods were used for X?"
2. **Results-based:** "What were the findings on Y?"
3. **Comparative:** "Compare approach A vs B"
4. **Definitional:** "What is the definition of Z?"

### Citation Requirements
- All generated answers MUST include paper citations
- Citations should include: Author(s), Year, Title, Venue
- Link chunks back to source papers via metadata
- Track provenance through the entire pipeline

## S3 Organization Structure
```
s3://hybrid-rag-documents-{env}/
├── raw/              # Original uploaded files
│   └── {document_id}.pdf
├── parsed/           # Parsed text and metadata
│   └── {document_id}.json
└── metadata/         # Extracted metadata
    └── {document_id}_metadata.json
```

## Configuration Management

Uses Pydantic Settings with environment variables:
- Development: `configs/dev.yaml` + `.env`
- Staging: `configs/staging.yaml`
- Production: `configs/prod.yaml`

Key configuration sections:
- API settings (host, port, title, version)
- AWS settings (region, S3 buckets)
- Database URLs (Qdrant, Elasticsearch, Redis)
- LLM API keys (Anthropic, OpenAI, Cohere)
- Embedding model configuration
- Observability settings (Comet ML, OPIK)

## Logging Strategy

Structured logging with Loguru:
- **Console:** Human-readable format with colors
- **File:** JSON format with rotation (100 MB), retention (30 days)
- **CloudWatch:** Streamed for production environments

Log levels:
- DEBUG: Development troubleshooting
- INFO: Key pipeline events
- WARNING: Recoverable issues
- ERROR: Failed operations with context

## Quality Validation

### Document Validation
- Minimum content length: >500 words
- Valid metadata: At least title required
- Readable text: Detect corrupted PDFs
- Duplicate detection: By DOI or title hash

### Chunking Quality
- Chunk size: 512-1024 tokens (configurable)
- Overlap: 50-100 tokens (configurable)
- Section preservation: Keep logical units together
- Equation integrity: No mid-equation splits

## Error Handling Patterns

1. **Transient Failures:** Retry with exponential backoff (3 attempts)
2. **Parse Failures:** Log error, skip document, notify user
3. **API Failures:** Fallback to secondary LLM (OpenAI if Claude fails)
4. **Index Failures:** Queue for retry, alert on repeated failures

## Development Workflow

1. **Local Development:**
   - Use Docker Compose for local services
   - Use `.env` file for secrets
   - Run tests frequently with pytest
   - Use ruff for code formatting/linting

2. **AWS Integration:**
   - All AWS credentials via AWS Secrets Manager
   - S3 for document storage and logs
   - CloudWatch for monitoring

3. **Adding New Parsers:**
   - Inherit from `BaseParser` abstract class
   - Implement async `parse()` method
   - Return `ParsedDocument` model
   - Add format detection logic
   - Write unit tests

4. **Adding New Chunkers:**
   - Integrate with Chonkie or implement custom
   - Update routing logic in `select_chunker()`
   - Validate chunk quality metrics
   - Compare against baseline (TokenChunker)

## AWS Resource Naming Convention
- S3 Buckets: `hybrid-rag-{resource}-{env}` (e.g., `hybrid-rag-documents-dev`)
- ECR Repository: `hybrid-rag-api`
- CloudWatch Log Groups: `/aws/ecs/hybrid-rag-api`, `/aws/eks/hybrid-rag-cluster`
- Security Groups: Named by function (API, Qdrant, Elasticsearch, Redis)

## Project Structure (Target)
```
hybrid-rag-research/
├── src/
│   ├── api/              # FastAPI routes and middleware
│   ├── core/             # Configuration, exceptions, RAG pipeline
│   ├── parsers/          # Document parsers (Docling, CSV, JSON, etc.)
│   ├── chunking/         # Chonkie wrapper, academic chunker
│   ├── embeddings/       # BGE embedder
│   ├── retrieval/        # Qdrant, Elasticsearch, hybrid search
│   ├── reranking/        # Cohere reranker
│   ├── generation/       # Claude/OpenAI generators, prompts
│   ├── indexing/         # Dual indexing, metadata extraction
│   └── utils/            # Logging, metrics, cache, S3 client
├── tests/
│   ├── unit/
│   ├── integration/
│   └── load/
├── configs/              # Environment-specific configs
├── docker/               # Dockerfiles and compose files
├── k8s/                  # Kubernetes manifests (post-MVP)
├── scripts/              # Setup and utility scripts
└── notebooks/            # Jupyter notebooks for experiments
```

## Performance Targets (Post-MVP)
- **Query Latency:** <3s p95 for full RAG pipeline
- **Indexing:** >100 papers/hour
- **Retrieval Accuracy:** >0.8 MRR@10
- **Generation Quality:** >4.0/5.0 human eval
- **Concurrent Users:** >50 simultaneous queries
