# Hybrid Search RAG for Academic Research Papers

A production-ready hybrid search RAG system that combines BM25 (lexical) and semantic search with advanced chunking strategies, specifically optimized for academic research papers.

## Project Status

🚧 **In Development** - Phase 2: Local Development Environment Setup

### Completed Phases
- ✅ Phase 1: AWS Account & Infrastructure Foundation

## Features

- **Hybrid Search**: Combines BM25 lexical search with semantic vector search
- **Advanced Chunking**: Multiple strategies (Token, Semantic, SDPM) optimized for academic papers
- **Academic Paper Support**: Specialized parsing for PDFs with LaTeX, equations, citations
- **Dual Indexing**: Qdrant for vector search + Elasticsearch for BM25
- **LLM Generation**: Claude (primary) with OpenAI fallback
- **Reranking**: Cohere semantic reranking
- **Full Observability**: OPIK tracing, Comet ML experiments, CloudWatch monitoring

## Technology Stack

- **Backend**: FastAPI, Python 3.12
- **Package Manager**: UV
- **Document Processing**: Docling, Chonkie
- **Embeddings**: BGE (BAAI/bge-base-en-v1.5)
- **Vector DB**: Qdrant
- **Search**: Elasticsearch
- **LLMs**: Anthropic Claude, OpenAI GPT-4
- **Reranker**: Cohere
- **Cloud**: AWS (S3, Secrets Manager, ECR, CloudWatch)
- **Observability**: OPIK, Comet ML, Loguru

## Prerequisites

- Python 3.12+
- UV package manager
- Docker and Docker Compose
- AWS Account with configured credentials
- API Keys: Anthropic, OpenAI, Cohere, Comet ML

## Quick Start

### 1. Clone and Setup

```bash
# Clone repository
git clone <repository-url>
cd Hybrid-Search-RAG

# Install dependencies
uv sync

# Activate virtual environment
source .venv/bin/activate
```

### 2. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your API keys and configuration
nano .env
```

### 3. Set Up AWS Infrastructure

```bash
# Run AWS setup script
./scripts/setup_aws.sh

# Update secrets with your API keys
./scripts/update_secrets.sh
```

### 4. Start Local Services

```bash
# Start Qdrant, Elasticsearch, Redis
docker-compose -f docker/docker-compose.yml up -d
```

### 5. Run the API

```bash
# Development mode
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

## Development

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_chunking.py
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

## Project Structure

See [CLAUDE.md](CLAUDE.md) for detailed project structure and architecture documentation.

## Documentation

- [CLAUDE.md](CLAUDE.md) - Development guide for Claude Code
- [PROJECT_PLAN.md](PROJECT_PLAN.md) - Detailed project plan
- `.env.example` - Environment variables template

## AWS Resources

The project uses the following AWS resources (created by `scripts/setup_aws.sh`):

- **S3 Buckets**: Documents, logs, artifacts
- **Secrets Manager**: API keys storage
- **ECR**: Docker image registry
- **CloudWatch**: Logs and monitoring

## License

MIT

## Contributing

This is currently a solo development project. Contributions guidelines will be added in Phase 17.
