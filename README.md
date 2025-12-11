# Hybrid Search RAG for Academic Research Papers

[![CI](https://github.com/yourusername/hybrid-search-rag/actions/workflows/ci.yml/badge.svg)](https://github.com/yourusername/hybrid-search-rag/actions/workflows/ci.yml)
[![CD](https://github.com/yourusername/hybrid-search-rag/actions/workflows/cd.yml/badge.svg)](https://github.com/yourusername/hybrid-search-rag/actions/workflows/cd.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)

A production-ready hybrid search RAG (Retrieval-Augmented Generation) system that combines BM25 lexical search with semantic vector search, specifically optimized for academic research papers. Features advanced chunking strategies, dual indexing, semantic reranking, and LLM-powered answer generation.

## 🚀 Features

### Core Capabilities

- **Hybrid Search**: Reciprocal Rank Fusion (RRF) combining BM25 and semantic search
- **Advanced Chunking**: Multiple strategies (Token, Semantic, SDPM) optimized for academic papers
- **Academic Paper Support**: Specialized parsing for PDFs with LaTeX equations, citations, and references
- **Dual Indexing**: Qdrant (vector) + Elasticsearch (lexical) for comprehensive search
- **Semantic Reranking**: Cohere-powered reranking for improved relevance
- **LLM Generation**: Claude Sonnet 4.5 (primary) with GPT-4 fallback
- **Full Observability**: OPIK tracing, Comet ML experiments, CloudWatch monitoring

### Production Features

- **Auto-scaling**: Kubernetes HPA (3-10 replicas based on load)
- **High Availability**: Multi-pod deployments with health checks
- **CI/CD Pipeline**: Automated testing, building, and deployment
- **Security**: AWS Secrets Manager, IRSA, TLS termination
- **Performance**: Redis caching, circuit breakers, rate limiting
- **Monitoring**: Comprehensive metrics, logging, and alerting

## 📋 Table of Contents

- [Architecture](#architecture)
- [Technology Stack](#technology-stack)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Deployment](#deployment)
- [API Documentation](#api-documentation)
- [Development](#development)
- [Project Structure](#project-structure)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [License](#license)

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       User Request                           │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                  FastAPI Application                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Document   │  │    Search    │  │   RAG Query  │      │
│  │   Ingestion  │  │   Endpoints  │  │   Endpoint   │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
└─────────┼──────────────────┼──────────────────┼─────────────┘
          ↓                  ↓                  ↓
┌─────────────────┐  ┌──────────────────────────────────────┐
│    Parsing      │  │        Hybrid Retrieval              │
│  ┌──────────┐   │  │  ┌────────────┐  ┌───────────────┐  │
│  │ Docling  │   │  │  │   Qdrant   │  │ Elasticsearch │  │
│  └────┬─────┘   │  │  │  (Vectors) │  │    (BM25)     │  │
│       ↓         │  │  └─────┬──────┘  └──────┬────────┘  │
│  ┌──────────┐   │  │        │                │           │
│  │ Chonkie  │   │  │        └────────┬───────┘           │
│  │Chunking  │   │  │                 ↓                    │
│  └────┬─────┘   │  │          ┌────────────┐             │
│       ↓         │  │          │    RRF     │             │
│  ┌──────────┐   │  │          │  Fusion    │             │
│  │   BGE    │   │  │          └─────┬──────┘             │
│  │Embedding │   │  │                ↓                    │
│  └──────────┘   │  │          ┌────────────┐             │
└─────────────────┘  │          │   Cohere   │             │
                     │          │  Reranking │             │
                     │          └─────┬──────┘             │
                     └────────────────┼────────────────────┘
                                      ↓
                     ┌────────────────────────────────────┐
                     │       LLM Generation               │
                     │  ┌───────────┐  ┌──────────────┐  │
                     │  │  Claude   │  │    GPT-4     │  │
                     │  │ (Primary) │  │  (Fallback)  │  │
                     │  └───────────┘  └──────────────┘  │
                     └────────────────┬───────────────────┘
                                      ↓
                     ┌────────────────────────────────────┐
                     │     Generated Answer with          │
                     │         Citations                  │
                     └────────────────────────────────────┘
```

## 🛠️ Technology Stack

### Backend & API
- **Framework**: FastAPI (async)
- **Language**: Python 3.12
- **Package Manager**: UV (ultra-fast Python package installer)
- **ASGI Server**: Uvicorn with multiple workers

### Document Processing
- **Parser**: Docling (PDF, DOCX, HTML with LaTeX support)
- **Chunker**: Chonkie (Token, Semantic, SDPM strategies)
- **Embeddings**: BGE (BAAI/bge-base-en-v1.5, 768 dimensions)

### Search & Retrieval
- **Vector Database**: Qdrant v1.7.4
- **Lexical Search**: Elasticsearch 8.11.3
- **Cache**: Redis 7 (LRU, 2GB max)
- **Reranker**: Cohere Rerank API

### LLM & Generation
- **Primary**: Anthropic Claude Sonnet 4.5
- **Fallback**: OpenAI GPT-4
- **Strategy**: Automatic failover with circuit breakers

### Infrastructure & DevOps
- **Cloud**: AWS (S3, ECR, EKS, Secrets Manager, CloudWatch)
- **Container**: Docker (multi-stage builds)
- **Orchestration**: Kubernetes (EKS)
- **Load Balancer**: AWS ALB with SSL
- **CI/CD**: GitHub Actions

### Observability
- **Tracing**: OPIK
- **Experiments**: Comet ML
- **Logging**: Loguru with structured JSON
- **Metrics**: CloudWatch, Prometheus-compatible

## 📦 Prerequisites

### Required
- **Python**: 3.12 or higher
- **UV**: Package manager ([install guide](https://github.com/astral-sh/uv))
- **Docker**: 20.10+ and Docker Compose 2.0+
- **Git**: Version control

### Optional (for deployment)
- **AWS CLI**: v2.x for cloud deployment
- **kubectl**: v1.28+ for Kubernetes
- **eksctl**: For EKS cluster management
- **Terraform**: For infrastructure as code (optional)

### API Keys
- **Anthropic**: Claude API key
- **OpenAI**: GPT-4 API key
- **Cohere**: Rerank API key
- **Comet ML**: Experiment tracking (optional)

## 🚀 Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/hybrid-search-rag.git
cd hybrid-search-rag
```

### 2. Install Dependencies

```bash
# Install UV (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv sync

# Activate virtual environment
source .venv/bin/activate
```

### 3. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit with your API keys
nano .env
```

Required environment variables:
```bash
# LLM API Keys
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
COHERE_API_KEY=...

# Service Endpoints (for local development)
QDRANT_HOST=localhost
QDRANT_PORT=6333
ELASTICSEARCH_HOST=localhost
ELASTICSEARCH_PORT=9200
REDIS_HOST=localhost
REDIS_PORT=6379

# Optional: Observability
COMET_API_KEY=...
ENABLE_TRACING=false
ENABLE_COMET_TRACKING=false
```

### 4. Start Local Services

```bash
# Start Qdrant, Elasticsearch, Redis with Docker Compose
docker-compose -f docker/docker-compose.yml up -d

# Verify services are running
docker ps
```

### 5. Run the Application

```bash
# Development mode with auto-reload
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Or with multiple workers (production)
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 6. Access the API

- **API Base**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health
- **Metrics**: http://localhost:8000/metrics

### 7. Quick Test

```bash
# Upload a document
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@path/to/paper.pdf"

# Perform RAG query
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the main findings of this research?",
    "top_k": 5
  }'
```

## 🚢 Deployment

### Docker Deployment

```bash
# Build Docker image
./scripts/build_docker.sh

# Run with Docker Compose (production stack)
cd docker
docker-compose -f docker-compose.prod.yml up -d

# Access via Nginx (if using --profile with-nginx)
curl http://localhost/health
```

See [DOCKER.md](docs/DOCKER.md) for detailed Docker deployment guide.

### Kubernetes Deployment

```bash
# Deploy to EKS
./scripts/deploy_k8s.sh --cluster hybrid-rag-cluster --region us-east-1

# Check deployment status
kubectl get pods -n hybrid-rag

# Access via load balancer
kubectl get ingress -n hybrid-rag
```

See [KUBERNETES.md](docs/KUBERNETES.md) for complete Kubernetes guide.

### CI/CD Pipeline

The project includes GitHub Actions workflows for automated deployment:

- **CI**: Runs on every PR (tests, linting, security scans)
- **CD**: Deploys to staging (main) and production (tags)
- **Rollback**: Manual rollback workflow

See [CICD.md](docs/CICD.md) for CI/CD setup and usage.

## 📚 API Documentation

### Core Endpoints

#### Document Management

**Upload Document**
```http
POST /api/v1/documents/upload
Content-Type: multipart/form-data

file: <PDF/DOCX file>
```

**Ingest Document**
```http
POST /api/v1/documents/ingest
Content-Type: application/json

{
  "document_id": "string",
  "chunking_strategy": "semantic"  // token, semantic, sdpm
}
```

#### Search

**Hybrid Search**
```http
POST /api/v1/search/hybrid
Content-Type: application/json

{
  "query": "string",
  "top_k": 10,
  "alpha": 0.5  // 0=lexical only, 1=semantic only
}
```

**Semantic Search**
```http
POST /api/v1/search/semantic
Content-Type: application/json

{
  "query": "string",
  "top_k": 10,
  "filters": {}
}
```

#### RAG Query

**Ask a Question**
```http
POST /api/v1/query
Content-Type: application/json

{
  "query": "What are the key contributions?",
  "top_k": 5,
  "rerank": true,
  "include_citations": true
}
```

See [API.md](docs/API.md) for complete API reference.

## 💻 Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html --cov-report=term-missing

# Run specific test categories
pytest tests/unit/              # Unit tests only
pytest tests/integration/       # Integration tests
pytest tests/load/              # Load tests with Locust

# Run specific test file
pytest tests/unit/test_embeddings.py -v

# Run with debugging
pytest tests/unit/ -v -s --pdb
```

### Code Quality

```bash
# Format code with Ruff
ruff format src/ tests/

# Lint code
ruff check src/ tests/

# Auto-fix linting issues
ruff check src/ tests/ --fix

# Type checking with MyPy
mypy src/ --ignore-missing-imports

# Check imports with isort
isort --check-only src/ tests/
```

### Load Testing

```bash
# Run load tests with Locust
cd tests/load
locust -f locustfile.py --host=http://localhost:8000

# Headless mode
locust -f locustfile.py --host=http://localhost:8000 \
  --users 50 --spawn-rate 5 --run-time 10m --headless
```

### Pre-commit Hooks

```bash
# Install pre-commit hooks (optional)
pip install pre-commit
pre-commit install

# Run manually
pre-commit run --all-files
```

## 📁 Project Structure

```
hybrid-search-rag/
├── .github/                    # GitHub Actions workflows
│   ├── workflows/
│   │   ├── ci.yml             # Continuous Integration
│   │   ├── cd.yml             # Continuous Deployment
│   │   ├── rollback.yml       # Deployment rollback
│   │   └── manual-deploy.yml  # Manual deployment
│   └── SETUP.md               # GitHub Actions setup guide
├── src/                       # Source code
│   ├── api/                   # FastAPI application
│   │   ├── main.py           # API entry point
│   │   ├── routes/           # API routes
│   │   ├── models/           # Pydantic models
│   │   └── middleware/       # Custom middleware
│   ├── core/                  # Core business logic
│   │   ├── config.py         # Configuration
│   │   ├── rag_pipeline.py   # Main RAG pipeline
│   │   └── exceptions.py     # Custom exceptions
│   ├── parsers/               # Document parsers
│   │   ├── docling_parser.py # PDF/DOCX parser
│   │   └── ...
│   ├── chunking/              # Chunking strategies
│   │   ├── chonkie_wrapper.py
│   │   └── academic_chunker.py
│   ├── embeddings/            # Embedding generation
│   │   └── bge_embedder.py
│   ├── retrieval/             # Search and retrieval
│   │   ├── hybrid_search.py
│   │   ├── qdrant_client.py
│   │   └── elasticsearch_client.py
│   ├── reranking/             # Semantic reranking
│   │   └── cohere_reranker.py
│   ├── generation/            # LLM generation
│   │   ├── claude_generator.py
│   │   └── openai_generator.py
│   ├── indexing/              # Indexing logic
│   │   ├── indexer.py
│   │   └── metadata_extractor.py
│   └── utils/                 # Utilities
│       ├── logging_config.py
│       ├── s3_client.py
│       ├── cache.py
│       ├── circuit_breaker.py
│       └── rate_limiter.py
├── tests/                     # Test suite
│   ├── unit/                 # Unit tests
│   ├── integration/          # Integration tests
│   └── load/                 # Load tests
├── docker/                    # Docker configuration
│   ├── Dockerfile            # Multi-stage build
│   ├── docker-compose.yml    # Local development
│   ├── docker-compose.prod.yml  # Production stack
│   └── nginx.conf            # Nginx configuration
├── k8s/                       # Kubernetes manifests
│   ├── namespace.yaml
│   ├── deployments/
│   ├── services/
│   ├── ingress/
│   └── hpa/
├── scripts/                   # Utility scripts
│   ├── setup_aws.sh          # AWS infrastructure setup
│   ├── build_docker.sh       # Docker build script
│   ├── deploy_k8s.sh         # Kubernetes deployment
│   └── rollback.sh           # Deployment rollback
├── docs/                      # Documentation
│   ├── API.md                # API reference
│   ├── DOCKER.md             # Docker guide
│   ├── KUBERNETES.md         # Kubernetes guide
│   ├── CICD.md               # CI/CD guide
│   └── OPTIMIZATION.md       # Performance guide
├── configs/                   # Configuration files
│   ├── dev.yaml
│   ├── staging.yaml
│   └── prod.yaml
├── pyproject.toml            # Project dependencies (UV)
├── .env.example              # Environment template
├── README.md                 # This file
├── CONTRIBUTING.md           # Contribution guidelines
└── LICENSE                   # MIT License
```

## 📖 Documentation

- **[API.md](docs/API.md)**: Complete API reference with examples
- **[DOCKER.md](docs/DOCKER.md)**: Docker deployment guide
- **[KUBERNETES.md](docs/KUBERNETES.md)**: Kubernetes deployment on AWS EKS
- **[CICD.md](docs/CICD.md)**: CI/CD pipeline setup and usage
- **[OPTIMIZATION.md](docs/OPTIMIZATION.md)**: Performance optimization guide
- **[CONTRIBUTING.md](CONTRIBUTING.md)**: How to contribute

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Quick Contribution Steps

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`pytest`)
5. Run linting (`ruff check . --fix`)
6. Commit (`git commit -m 'Add amazing feature'`)
7. Push (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Docling**: PDF parsing with academic paper support
- **Chonkie**: Advanced chunking strategies
- **BGE**: High-quality embeddings
- **Qdrant**: Fast vector search
- **Anthropic**: Claude LLM
- **Cohere**: Semantic reranking

## 📧 Contact

- **Issues**: https://github.com/yourusername/hybrid-search-rag/issues
- **Discussions**: https://github.com/yourusername/hybrid-search-rag/discussions
- **Email**: your.email@example.com

## 🌟 Star History

If you find this project useful, please consider giving it a star ⭐

---

**Built with ❤️ for the research community**
