# Hybrid Search RAG with Advanced Chunking - Project Plan

## 📋 Project Overview

**Project Name:** Hybrid Search RAG for Academic Research Papers  
**Domain:** Academic research paper retrieval and question-answering  
**Development Mode:** Solo development with Claude Code  
**Timeline:** 12 weeks (6 weeks MVP + 6 weeks enhancements)

### Core Objective
Build a production-ready hybrid search RAG system that combines BM25 (lexical) and semantic search with advanced chunking strategies, specifically optimized for academic research papers. The system will enable researchers to query across multiple papers and receive accurate, citation-backed answers.

---

## 🛠 Technology Stack

### Backend & API
- **Python:** 3.12
- **Package Manager:** UV
- **Web Framework:** FastAPI
- **Async Runtime:** asyncio, uvicorn

### Document Processing
- **Parser:** Docling (primary for PDFs, HTML, DOCX)
- **Chunking:** Chonkie (SemanticChunker, TokenChunker, SDPMChunker)
- **Supported Formats:** PDF, CSV, HTML, TXT, JSON, Markdown

### Embeddings & Search
- **Embeddings:** BGE (BAAI/bge-base-en-v1.5, 768 dimensions)
- **Vector Database:** Qdrant (semantic search)
- **Search Engine:** Elasticsearch (BM25 lexical search)
- **Reranker:** Cohere rerank-english-v3.0

### LLM & Generation
- **Primary LLM:** Anthropic Claude (claude-sonnet-4-20250514)
- **Fallback LLM:** OpenAI GPT-4

### Observability & Monitoring
- **Logging:** Loguru (structured JSON logging)
- **Tracing:** OPIK (request tracing, latency tracking)
- **Experiment Tracking:** Comet ML
- **Validation:** Pydantic (data validation)

### Infrastructure
- **Cloud Provider:** AWS (US-East-1)
- **Container Runtime:** Docker
- **Orchestration:** Kubernetes (Amazon EKS) - Post-MVP
- **Storage:** S3 (documents, logs, artifacts)
- **Registry:** Amazon ECR
- **Caching:** Redis

### Development Tools
- **IDE:** VS Code
- **Version Control:** GitHub
- **Testing:** pytest, pytest-asyncio, httpx
- **Load Testing:** Locust
- **Code Quality:** ruff, black, mypy

---

## 📚 Academic Research Paper Specific Considerations

### Document Characteristics
- **Format:** Primarily PDFs with LaTeX formatting
- **Structure:** Abstract, Introduction, Methods, Results, Discussion, References
- **Content:** Mathematical equations, figures, tables, citations
- **Length:** 8-40 pages typically
- **Metadata:** Authors, affiliations, publication date, journal/conference, DOI, arXiv ID

### Specialized Requirements
1. **Citation Preservation:** Maintain reference to original papers
2. **Section Awareness:** Preserve paper structure (abstract, methods, etc.)
3. **Mathematical Content:** Handle LaTeX equations appropriately
4. **Figure/Table Context:** Associate captions and context
5. **Cross-References:** Track paper-to-paper citations
6. **Metadata Enrichment:** Extract author, year, venue, DOI
7. **Domain-Specific Terms:** Handle scientific terminology

### Search Optimization for Research
- **Query Types:**
  - Methodological queries: "What methods were used for X?"
  - Result queries: "What were the findings on Y?"
  - Comparative queries: "Compare approach A vs B"
  - Definition queries: "What is the definition of Z?"
- **Citation Requirements:** All answers must include paper citations
- **Temporal Awareness:** Prioritize recent papers when relevant
- **Authority Scoring:** Consider citation count, venue reputation

---

## 🗂 Project Structure

```
hybrid-rag-research/
├── .github/
│   └── workflows/
│       └── ci-cd.yml
├── src/
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI application
│   │   ├── routes/
│   │   │   ├── documents.py     # Document ingestion endpoints
│   │   │   ├── search.py        # Search endpoints
│   │   │   ├── query.py         # RAG query endpoints
│   │   │   └── system.py        # Health, metrics
│   │   ├── models/
│   │   │   ├── requests.py      # Pydantic request models
│   │   │   └── responses.py     # Pydantic response models
│   │   └── middleware/
│   │       ├── logging.py       # Request logging
│   │       ├── auth.py          # API key authentication
│   │       └── error_handler.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py            # Pydantic settings
│   │   ├── exceptions.py        # Custom exceptions
│   │   └── rag_pipeline.py      # Main RAG orchestrator
│   ├── parsers/
│   │   ├── __init__.py
│   │   ├── base.py              # Base parser interface
│   │   ├── docling_parser.py   # Docling integration
│   │   ├── csv_parser.py
│   │   ├── json_parser.py
│   │   └── markdown_parser.py
│   ├── chunking/
│   │   ├── __init__.py
│   │   ├── chonkie_wrapper.py   # Chonkie integration
│   │   ├── academic_chunker.py  # Custom academic paper chunker
│   │   └── chunk_models.py      # Chunk data models
│   ├── embeddings/
│   │   ├── __init__.py
│   │   └── bge_embedder.py      # BGE embedding service
│   ├── retrieval/
│   │   ├── __init__.py
│   │   ├── qdrant_client.py     # Qdrant operations
│   │   ├── elasticsearch_client.py  # ES operations
│   │   ├── hybrid_search.py     # Hybrid fusion logic
│   │   └── query_processor.py   # Query understanding
│   ├── reranking/
│   │   ├── __init__.py
│   │   └── cohere_reranker.py   # Cohere reranker
│   ├── generation/
│   │   ├── __init__.py
│   │   ├── claude_generator.py  # Anthropic Claude
│   │   ├── openai_generator.py  # OpenAI fallback
│   │   └── prompt_templates.py  # Academic-focused prompts
│   ├── indexing/
│   │   ├── __init__.py
│   │   ├── indexer.py           # Dual indexing orchestrator
│   │   └── metadata_extractor.py
│   └── utils/
│       ├── __init__.py
│       ├── logging_config.py    # Loguru setup
│       ├── metrics.py           # Metrics collection
│       ├── cache.py             # Redis cache wrapper
│       └── s3_client.py         # S3 operations
├── tests/
│   ├── unit/
│   │   ├── test_chunking.py
│   │   ├── test_embeddings.py
│   │   ├── test_search.py
│   │   └── test_reranking.py
│   ├── integration/
│   │   ├── test_rag_pipeline.py
│   │   └── test_api_endpoints.py
│   └── load/
│       └── locustfile.py
├── configs/
│   ├── dev.yaml
│   ├── staging.yaml
│   └── prod.yaml
├── docker/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── docker-compose.prod.yml
├── k8s/
│   ├── namespace.yaml
│   ├── configmaps/
│   ├── secrets/
│   ├── deployments/
│   ├── services/
│   ├── ingress/
│   ├── hpa/
│   └── storage/
├── scripts/
│   ├── setup_aws.sh
│   ├── create_indices.py
│   ├── generate_eval_dataset.py
│   └── run_evaluation.py
├── notebooks/
│   ├── chunking_experiments.ipynb
│   ├── search_evaluation.ipynb
│   └── prompt_engineering.ipynb
├── docs/
│   ├── API.md
│   ├── DEPLOYMENT.md
│   └── EVALUATION.md
├── .env.example
├── .gitignore
├── pyproject.toml
├── uv.lock
└── README.md
```

---

## 🎯 Development Phases

### Phase 1: AWS Account & Infrastructure Foundation (Week 1) ⭐ MVP

#### 1.1 AWS Account Setup
**Tasks:**
- [ ] Create/configure AWS account
- [ ] Set up root account MFA
- [ ] Configure billing alerts ($50, $100, $500)
- [ ] Create monthly budget ($500 limit)
- [ ] Enable Cost Explorer

**Time:** 2 hours

#### 1.2 IAM Configuration
**Tasks:**
- [ ] Create admin IAM user with MFA
- [ ] Create programmatic access user for CLI
- [ ] Create service roles:
  - EKS cluster role (for future)
  - EKS node group role (for future)
  - EC2 instance profile (for dev/staging)
- [ ] Document IAM policies

**Time:** 2 hours

#### 1.3 Core AWS Services
**Tasks:**
- [ ] **VPC Setup:**
  - Create VPC (10.0.0.0/16)
  - Public subnets in 2 AZs (10.0.1.0/24, 10.0.2.0/24)
  - Private subnets in 2 AZs (10.0.11.0/24, 10.0.12.0/24)
  - Internet Gateway
  - NAT Gateway (1 for cost optimization)
  - Route tables
  - Security groups (API, Qdrant, Elasticsearch, Redis)

- [ ] **S3 Buckets:**
  - `hybrid-rag-documents-{env}` (papers, uploads)
  - `hybrid-rag-logs-{env}` (application logs)
  - `hybrid-rag-artifacts-{env}` (models, experiments)
  - Configure lifecycle policies
  - Enable versioning on documents bucket

- [ ] **Secrets Manager:**
  - Anthropic API key
  - OpenAI API key
  - Cohere API key
  - Comet ML API key
  - Database credentials (if needed)

- [ ] **ECR Repository:**
  - Create `hybrid-rag-api` repository
  - Configure image scanning
  - Set lifecycle policy (keep last 10 images)

**Time:** 4 hours

#### 1.4 AWS CLI & SDK Setup
**Tasks:**
- [ ] Install AWS CLI v2
- [ ] Configure profiles (dev, staging, prod)
- [ ] Test S3, Secrets Manager access
- [ ] Install boto3 in project

**Time:** 1 hour

#### 1.5 Monitoring Setup
**Tasks:**
- [ ] Create CloudWatch dashboard
- [ ] Set up log groups:
  - `/aws/ecs/hybrid-rag-api`
  - `/aws/eks/hybrid-rag-cluster` (future)
- [ ] Configure CloudWatch alarms:
  - High API error rate
  - High latency (>5s p95)
  - High cost alerts

**Time:** 2 hours

**Deliverables:**
- AWS account fully configured
- IAM users and roles created
- VPC with proper networking
- S3 buckets created
- Secrets Manager configured
- AWS CLI working locally

---

### Phase 2: Local Development Environment Setup (Week 1) ⭐ MVP

#### 2.1 Project Initialization
**Tasks:**
- [ ] Create GitHub repository: `hybrid-rag-research`
- [ ] Initialize with README, .gitignore, LICENSE
- [ ] Set up branch protection (main branch)
- [ ] Clone repository locally
- [ ] Create project structure (as outlined above)

**Time:** 1 hour

#### 2.2 Python Environment with UV
**Tasks:**
- [ ] Install UV package manager
- [ ] Initialize pyproject.toml with UV
- [ ] Add core dependencies:
  ```toml
  [project]
  name = "hybrid-rag-research"
  version = "0.1.0"
  requires-python = ">=3.12"
  
  dependencies = [
      "fastapi",
      "uvicorn[standard]",
      "pydantic",
      "pydantic-settings",
      "loguru",
      "opik",
      "comet-ml",
      "chonkie",
      "docling",
      "sentence-transformers",
      "qdrant-client",
      "elasticsearch",
      "cohere",
      "anthropic",
      "openai",
      "boto3",
      "redis",
      "python-multipart",
      "httpx",
      "pytest",
      "pytest-asyncio",
      "pytest-cov",
      "ruff",
      "black",
      "mypy",
  ]
  ```
- [ ] Create virtual environment with UV
- [ ] Generate uv.lock file

**Time:** 1 hour

#### 2.3 VS Code Configuration
**Tasks:**
- [ ] Install Python extension
- [ ] Install Docker extension
- [ ] Install Kubernetes extension (for future)
- [ ] Configure settings.json:
  ```json
  {
    "python.defaultInterpreterPath": ".venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.ruffEnabled": true,
    "python.formatting.provider": "black",
    "editor.formatOnSave": true,
    "files.exclude": {
      "**/__pycache__": true,
      "**/.pytest_cache": true
    }
  }
  ```
- [ ] Create .vscode/launch.json for debugging
- [ ] Set up pytest integration

**Time:** 1 hour

#### 2.4 Core Configuration Setup
**Tasks:**
- [ ] Create src/core/config.py with Pydantic Settings:
  ```python
  from pydantic_settings import BaseSettings, SettingsConfigDict
  
  class Settings(BaseSettings):
      # API
      api_title: str = "Hybrid RAG Research API"
      api_version: str = "1.0.0"
      api_host: str = "0.0.0.0"
      api_port: int = 8000
      
      # AWS
      aws_region: str = "us-east-1"
      s3_bucket_documents: str
      s3_bucket_logs: str
      
      # Qdrant
      qdrant_url: str = "http://localhost:6333"
      qdrant_collection: str = "research_papers"
      
      # Elasticsearch
      elasticsearch_url: str = "http://localhost:9200"
      elasticsearch_index: str = "research_papers"
      
      # Redis
      redis_url: str = "redis://localhost:6379"
      
      # LLM
      anthropic_api_key: str
      openai_api_key: str
      cohere_api_key: str
      
      # Embeddings
      embedding_model: str = "BAAI/bge-base-en-v1.5"
      embedding_dimension: int = 768
      
      # Observability
      comet_api_key: str
      comet_project: str = "hybrid-rag-research"
      
      model_config = SettingsConfigDict(
          env_file=".env",
          env_file_encoding="utf-8",
          case_sensitive=False
      )
  ```

- [ ] Create .env.example
- [ ] Create configs/dev.yaml, staging.yaml, prod.yaml

**Time:** 2 hours

#### 2.5 Docker Compose for Local Development
**Tasks:**
- [ ] Create docker/docker-compose.yml:
  ```yaml
  version: '3.8'
  
  services:
    qdrant:
      image: qdrant/qdrant:latest
      container_name: qdrant
      ports:
        - "6333:6333"
      volumes:
        - qdrant_data:/qdrant/storage
      restart: unless-stopped
    
    elasticsearch:
      image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
      container_name: elasticsearch
      environment:
        - discovery.type=single-node
        - xpack.security.enabled=false
        - ES_JAVA_OPTS=-Xms2g -Xmx2g
      ports:
        - "9200:9200"
      volumes:
        - es_data:/usr/share/elasticsearch/data
      restart: unless-stopped
    
    redis:
      image: redis:7-alpine
      container_name: redis
      ports:
        - "6379:6379"
      volumes:
        - redis_data:/data
      restart: unless-stopped
  
  volumes:
    qdrant_data:
    es_data:
    redis_data:
  ```

- [ ] Test docker-compose up
- [ ] Verify all services accessible

**Time:** 2 hours

#### 2.6 Logging Infrastructure with Loguru
**Tasks:**
- [ ] Create src/utils/logging_config.py:
  ```python
  from loguru import logger
  import sys
  
  def setup_logging(log_level: str = "INFO"):
      logger.remove()
      
      # Console logging
      logger.add(
          sys.stdout,
          format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
          level=log_level,
          serialize=False
      )
      
      # File logging with rotation
      logger.add(
          "logs/app_{time}.log",
          rotation="100 MB",
          retention="30 days",
          compression="zip",
          format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}",
          level=log_level,
          serialize=True  # JSON format
      )
      
      return logger
  ```

- [ ] Create logs/ directory
- [ ] Test logging setup

**Time:** 1 hour

**Deliverables:**
- GitHub repository created and configured
- Python 3.12 + UV environment working
- VS Code fully configured
- Docker Compose running Qdrant, Elasticsearch, Redis
- Basic configuration system with Pydantic
- Structured logging with Loguru

---

### Phase 3: Document Processing Pipeline (Week 2) ⭐ MVP

#### 3.1 Docling Integration for Academic Papers
**Tasks:**
- [ ] Install and test Docling
- [ ] Create src/parsers/docling_parser.py:
  - PDF parsing with layout preservation
  - Section detection (Abstract, Introduction, Methods, etc.)
  - Extract equations (LaTeX when possible)
  - Extract figures and tables with captions
  - Extract references/bibliography
  - Handle multi-column layouts

- [ ] Create parser for each format:
  - CSV: src/parsers/csv_parser.py
  - JSON: src/parsers/json_parser.py
  - Markdown: src/parsers/markdown_parser.py
  - TXT: src/parsers/txt_parser.py
  - HTML: src/parsers/html_parser.py

- [ ] Create base parser interface:
  ```python
  from abc import ABC, abstractmethod
  
  class BaseParser(ABC):
      @abstractmethod
      async def parse(self, file_path: str) -> ParsedDocument:
          pass
  ```

**Time:** 8 hours

#### 3.2 Academic Metadata Extraction
**Tasks:**
- [ ] Create src/indexing/metadata_extractor.py
- [ ] Extract paper metadata:
  - Title (from PDF metadata or first page)
  - Authors and affiliations
  - Publication year
  - Journal/Conference name
  - DOI, arXiv ID
  - Abstract
  - Keywords
  - Citation count (if available)
  - Paper length (page count)

- [ ] Implement metadata cleaning and validation
- [ ] Create metadata schema with Pydantic:
  ```python
  class PaperMetadata(BaseModel):
      title: str
      authors: List[str]
      affiliations: List[str] = []
      year: Optional[int] = None
      venue: Optional[str] = None
      doi: Optional[str] = None
      arxiv_id: Optional[str] = None
      abstract: Optional[str] = None
      keywords: List[str] = []
      citation_count: Optional[int] = None
      page_count: Optional[int] = None
      sections: List[str] = []
  ```

**Time:** 4 hours

#### 3.3 Document Preprocessing
**Tasks:**
- [ ] Create preprocessing utilities:
  - Text normalization (Unicode, whitespace)
  - LaTeX equation handling
  - Reference formatting
  - Figure/table caption extraction
  - Section header identification

- [ ] Implement quality checks:
  - Minimum content length (>500 words)
  - Valid metadata (at least title)
  - Readable text (not corrupted PDF)
  - Duplicate detection (by DOI or title)

**Time:** 4 hours

#### 3.4 S3 Integration
**Tasks:**
- [ ] Create src/utils/s3_client.py
- [ ] Implement upload/download functions
- [ ] Handle file streaming for large PDFs
- [ ] Organize S3 structure:
  ```
  s3://hybrid-rag-documents-dev/
  ├── raw/              # Original uploaded files
  │   └── {document_id}.pdf
  ├── parsed/           # Parsed text and metadata
  │   └── {document_id}.json
  └── metadata/         # Extracted metadata
      └── {document_id}_metadata.json
  ```

**Time:** 3 hours

#### 3.5 Document Processing Pipeline
**Tasks:**
- [ ] Create end-to-end pipeline:
  ```python
  File Upload → S3 (raw) → 
  Format Detection → Parser Selection → 
  Text Extraction → Metadata Extraction → 
  Preprocessing → Quality Validation → 
  S3 (parsed) → Ready for Chunking
  ```

- [ ] Add error handling at each stage
- [ ] Implement progress tracking
- [ ] Add retry logic for transient failures

**Time:** 4 hours

**Deliverables:**
- Docling parser working for academic PDFs
- All format parsers implemented
- Metadata extraction for research papers
- S3 integration for document storage
- End-to-end preprocessing pipeline

---

### Phase 4: Advanced Chunking with Chonkie (Week 3) ⭐ MVP

#### 4.1 Chonkie Setup and Integration
**Tasks:**
- [ ] Install Chonkie: `uv add chonkie`
- [ ] Test basic Chonkie chunkers
- [ ] Create src/chunking/chonkie_wrapper.py
- [ ] Implement wrapper for three chunkers:
  - TokenChunker (baseline)
  - SemanticChunker (primary)
  - SDPMChunker (advanced)

**Time:** 3 hours

#### 4.2 Academic Paper Specific Chunker
**Tasks:**
- [ ] Create src/chunking/academic_chunker.py
- [ ] Implement section-aware chunking:
  - Keep sections together when possible
  - Preserve section headers with chunks
  - Handle abstract separately (full text)
  - Special handling for Methods, Results

- [ ] Implement equation-aware chunking:
  - Don't split equations
  - Keep equation context together

- [ ] Implement reference-aware chunking:
  - Keep citations with context
  - Preserve reference list structure

**Time:** 6 hours

#### 4.3 Chunking Strategy by Document Type
**Tasks:**
- [ ] Implement routing logic:
  ```python
  def select_chunker(document_type: str, content_length: int) -> Chunker:
      if document_type == "pdf" and content_length > 10000:
          return SDPMChunker()  # Long academic papers
      elif document_type in ["pdf", "html", "txt"]:
          return SemanticChunker()  # Standard documents
      else:
          return TokenChunker()  # Fallback
  ```

- [ ] Create configuration for each chunker:
  - Token limits (512, 1024, 2048 options)
  - Overlap settings (50, 100, 200 tokens)
  - Similarity thresholds (for semantic chunking)

**Time:** 3 hours

#### 4.4 Chunk Metadata Enrichment
**Tasks:**
- [ ] Create src/chunking/chunk_models.py:
  ```python
  class Chunk(BaseModel):
      chunk_id: str  # UUID
      document_id: str  # Parent document UUID
      content: str  # Chunk text
      chunk_index: int  # Position in document (0-indexed)
      chunker_type: str  # "semantic", "token", "sdpm"
      
      # Token/character counts
      token_count: int
      char_count: int
      
      # Academic paper specific
      section: Optional[str] = None  # Abstract, Methods, etc.
      page_numbers: List[int] = []  # Pages this chunk spans
      contains_equations: bool = False
      contains_figures: bool = False
      contains_tables: bool = False
      
      # Document metadata (denormalized)
      document_title: str
      document_authors: List[str]
      document_year: Optional[int] = None
      document_venue: Optional[str] = None
      
      # Timestamps
      created_at: datetime
      
      # Vector (will be added during embedding)
      embedding: Optional[List[float]] = None
  ```

- [ ] Implement metadata propagation from document to chunks

**Time:** 2 hours

#### 4.5 Chunking Evaluation Framework
**Tasks:**
- [ ] Create notebook: notebooks/chunking_experiments.ipynb
- [ ] Implement chunk quality metrics:
  - Average chunk size
  - Size distribution (histogram)
  - Coherence score (semantic similarity between consecutive chunks)
  - Information density (unique tokens / total tokens)

- [ ] Create visualization:
  - Chunk size distribution plots
  - Side-by-side chunker comparison
  - Sample chunks for manual inspection

- [ ] Log experiments to Comet ML:
  - Chunker parameters
  - Quality metrics
  - Sample outputs

**Time:** 4 hours

#### 4.6 Chunk Inspection UI (Optional but Recommended)
**Tasks:**
- [ ] Create simple HTML page to visualize chunks
- [ ] Display original document with chunk boundaries
- [ ] Show chunk metadata
- [ ] Enable manual quality assessment

**Time:** 3 hours

**Deliverables:**
- Chonkie integrated with 3 chunkers
- Academic-specific chunking logic
- Comprehensive chunk metadata model
- Chunking evaluation framework
- Experiments tracked in Comet ML

---

### Phase 5: Embeddings with BGE (Week 3) ⭐ MVP

#### 5.1 BGE Model Setup
**Tasks:**
- [ ] Install sentence-transformers
- [ ] Create src/embeddings/bge_embedder.py:
  ```python
  from sentence_transformers import SentenceTransformer
  
  class BGEEmbedder:
      def __init__(self, model_name: str = "BAAI/bge-base-en-v1.5"):
          self.model = SentenceTransformer(model_name)
          self.dimension = 768  # bge-base
      
      def embed_text(self, text: str) -> List[float]:
          # Single text embedding
          pass
      
      def embed_batch(self, texts: List[str]) -> List[List[float]]:
          # Batch embedding with progress bar
          pass
      
      def embed_query(self, query: str) -> List[float]:
          # Special query embedding (add instruction if using bge-v1.5)
          pass
  ```

- [ ] Test embedding generation
- [ ] Measure embedding speed (CPU vs GPU if available)

**Time:** 3 hours

#### 5.2 Embedding Optimization
**Tasks:**
- [ ] Implement batching (32-64 texts at a time)
- [ ] Add progress bars for large batches
- [ ] Handle long texts (truncation at 512 tokens)
- [ ] Normalize embeddings (L2 normalization)
- [ ] GPU support with CPU fallback

**Time:** 2 hours

#### 5.3 Embedding Caching with Redis
**Tasks:**
- [ ] Create src/utils/cache.py:
  ```python
  import redis
  import json
  
  class EmbeddingCache:
      def __init__(self, redis_url: str):
          self.redis = redis.from_url(redis_url)
      
      def get_embedding(self, text: str) -> Optional[List[float]]:
          # Cache key: hash of text
          pass
      
      def set_embedding(self, text: str, embedding: List[float], ttl: int = 86400):
          # Cache embedding for 24 hours
          pass
  ```

- [ ] Integrate cache with embedder
- [ ] Particularly cache query embeddings
- [ ] Monitor cache hit rate

**Time:** 2 hours

#### 5.4 Embedding Benchmarks
**Tasks:**
- [ ] Measure embedding generation time:
  - Single text
  - Batch of 100 texts
  - Batch of 1000 texts
- [ ] Measure memory usage
- [ ] Compare CPU vs GPU (if available)
- [ ] Document results in README

**Time:** 2 hours

**Deliverables:**
- BGE embedder wrapper implemented
- Batch embedding with progress tracking
- Redis caching for embeddings
- Performance benchmarks documented

---

### Phase 6: Dual Indexing - Qdrant & Elasticsearch (Week 4) ⭐ MVP

#### 6.1 Qdrant Setup and Configuration
**Tasks:**
- [ ] Create src/retrieval/qdrant_client.py
- [ ] Create collection with optimal configuration:
  ```python
  from qdrant_client import QdrantClient
  from qdrant_client.models import Distance, VectorParams, OptimizersConfigDiff
  
  client = QdrantClient(url="http://localhost:6333")
  
  client.create_collection(
      collection_name="research_papers",
      vectors_config=VectorParams(
          size=768,  # bge-base dimension
          distance=Distance.COSINE
      ),
      optimizers_config=OptimizersConfigDiff(
          indexing_threshold=20000,  # Start indexing after 20k vectors
      ),
      quantization_config=ScalarQuantization(
          scalar=ScalarQuantizationConfig(
              type=ScalarType.INT8,
              quantile=0.99,
              always_ram=True
          )
      ),
      hnsw_config=HnswConfigDiff(
          m=16,  # Number of edges per node
          ef_construct=100,  # Quality during construction
      )
  )
  ```

- [ ] Configure payload schema:
  ```python
  # Qdrant auto-indexes payloads, but define expected fields
  payload_schema = {
      "document_id": "keyword",
      "chunk_id": "keyword",
      "chunk_index": "integer",
      "document_title": "text",
      "document_authors": "keyword",
      "document_year": "integer",
      "document_venue": "keyword",
      "section": "keyword",
      "created_at": "datetime"
  }
  ```

**Time:** 3 hours

#### 6.2 Qdrant Operations
**Tasks:**
- [ ] Implement core operations:
  - `upsert_chunks()`: Batch insert chunks with embeddings
  - `search()`: Vector similarity search
  - `delete_document()`: Remove all chunks for a document
  - `get_chunk()`: Retrieve specific chunk
  - `count()`: Get total vector count
  - `scroll()`: Paginated retrieval for large result sets

- [ ] Implement filtering:
  ```python
  def search_with_filters(
      query_vector: List[float],
      top_k: int = 10,
      filters: Optional[Dict] = None
  ):
      # Example: filter by year, venue, authors
      filter_conditions = Filter(
          must=[
              FieldCondition(
                  key="document_year",
                  range=RangeCondition(gte=2020)
              )
          ]
      )
  ```

**Time:** 4 hours

#### 6.3 Elasticsearch Setup and Configuration
**Tasks:**
- [ ] Create src/retrieval/elasticsearch_client.py
- [ ] Create index with custom analyzer:
  ```python
  from elasticsearch import Elasticsearch
  
  es = Elasticsearch(["http://localhost:9200"])
  
  index_settings = {
      "settings": {
          "number_of_shards": 2,
          "number_of_replicas": 1,
          "analysis": {
              "analyzer": {
                  "academic_english": {
                      "type": "english",
                      "stopwords": "_english_"
                  },
                  "exact_match": {
                      "type": "keyword"
                  }
              }
          }
      },
      "mappings": {
          "properties": {
              "content": {
                  "type": "text",
                  "analyzer": "academic_english",
                  "fields": {
                      "keyword": {
                          "type": "keyword",
                          "ignore_above": 256
                      }
                  }
              },
              "document_id": {"type": "keyword"},
              "chunk_id": {"type": "keyword"},
              "chunk_index": {"type": "integer"},
              "document_title": {
                  "type": "text",
                  "analyzer": "academic_english",
                  "fields": {"keyword": {"type": "keyword"}}
              },
              "document_authors": {"type": "keyword"},
              "document_year": {"type": "integer"},
              "document_venue": {
                  "type": "text",
                  "fields": {"keyword": {"type": "keyword"}}
              },
              "section": {"type": "keyword"},
              "created_at": {"type": "date"}
          }
      }
  }
  
  es.indices.create(index="research_papers", body=index_settings)
  ```

**Time:** 3 hours

#### 6.4 Elasticsearch Operations
**Tasks:**
- [ ] Implement core operations:
  - `index_chunks()`: Batch index chunks
  - `search()`: BM25 search
  - `delete_document()`: Remove all chunks for a document
  - `get_chunk()`: Retrieve specific chunk
  - `count()`: Get document count

- [ ] Implement BM25 search with boosting:
  ```python
  def bm25_search(
      query: str,
      top_k: int = 10,
      filters: Optional[Dict] = None
  ):
      body = {
          "query": {
              "bool": {
                  "must": [
                      {
                          "multi_match": {
                              "query": query,
                              "fields": [
                                  "content^2",  # Boost content
                                  "document_title^3",  # Boost title more
                                  "section^1.5"  # Boost section
                              ],
                              "type": "best_fields"
                          }
                      }
                  ],
                  "filter": []  # Add filters here
              }
          },
          "size": top_k
      }
  ```

**Time:** 4 hours

#### 6.5 Dual Indexing Pipeline
**Tasks:**
- [ ] Create src/indexing/indexer.py:
  ```python
  class DualIndexer:
      def __init__(self, qdrant_client, es_client, embedder):
          self.qdrant = qdrant_client
          self.es = es_client
          self.embedder = embedder
      
      async def index_document(self, document: ParsedDocument, chunks: List[Chunk]):
          # 1. Generate embeddings for all chunks
          embeddings = await self.embedder.embed_batch([c.content for c in chunks])
          
          # 2. Index to Qdrant (with embeddings)
          await self.qdrant.upsert_chunks(chunks, embeddings)
          
          # 3. Index to Elasticsearch (without embeddings)
          await self.es.index_chunks(chunks)
          
          logger.info(f"Indexed {len(chunks)} chunks for document {document.id}")
  ```

- [ ] Implement transaction-like behavior:
  - If Qdrant succeeds but ES fails → rollback Qdrant
  - If ES succeeds but Qdrant fails → rollback ES
  - Log all failures for manual reconciliation

- [ ] Add batch processing:
  - Process multiple documents in parallel
  - Progress tracking with tqdm
  - Error collection and reporting

**Time:** 4 hours

#### 6.6 Index Health Monitoring
**Tasks:**
- [ ] Create health check functions:
  - Check Qdrant collection exists and count
  - Check ES index exists and count
  - Compare counts (should match)
  - Check index freshness (last updated time)

- [ ] Create reconciliation script:
  - Find documents in Qdrant but not in ES
  - Find documents in ES but not in Qdrant
  - Re-index inconsistent documents

**Time:** 3 hours

**Deliverables:**
- Qdrant collection created and configured
- Elasticsearch index created and configured
- Dual indexing pipeline working
- Index health monitoring
- Reconciliation capabilities

---

### Phase 7: Hybrid Search Implementation (Week 4) ⭐ MVP

#### 7.1 Semantic Search (Qdrant)
**Tasks:**
- [ ] Implement semantic search in src/retrieval/qdrant_client.py:
  ```python
  async def semantic_search(
      query: str,
      top_k: int = 50,
      filters: Optional[Dict] = None,
      score_threshold: float = 0.5
  ) -> List[SearchResult]:
      # 1. Embed query
      query_vector = await self.embedder.embed_query(query)
      
      # 2. Search Qdrant
      results = self.client.search(
          collection_name="research_papers",
          query_vector=query_vector,
          limit=top_k,
          query_filter=filters,
          score_threshold=score_threshold,
          with_payload=True
      )
      
      # 3. Format results
      return [SearchResult.from_qdrant(r) for r in results]
  ```

- [ ] Test semantic search with various queries
- [ ] Tune score_threshold parameter

**Time:** 3 hours

#### 7.2 Lexical Search (Elasticsearch)
**Tasks:**
- [ ] Implement BM25 search in src/retrieval/elasticsearch_client.py:
  ```python
  async def lexical_search(
      query: str,
      top_k: int = 50,
      filters: Optional[Dict] = None,
      min_score: float = 0.0
  ) -> List[SearchResult]:
      # Build ES query
      body = self._build_bm25_query(query, filters)
      
      # Execute search
      response = await self.es.search(
          index="research_papers",
          body=body,
          size=top_k,
          min_score=min_score
      )
      
      # Format results
      return [SearchResult.from_elasticsearch(hit) for hit in response['hits']['hits']]
  ```

- [ ] Test BM25 search
- [ ] Experiment with field boosting

**Time:** 3 hours

#### 7.3 Hybrid Search Fusion
**Tasks:**
- [ ] Create src/retrieval/hybrid_search.py
- [ ] Implement Reciprocal Rank Fusion (RRF):
  ```python
  def reciprocal_rank_fusion(
      semantic_results: List[SearchResult],
      lexical_results: List[SearchResult],
      k: int = 60
  ) -> List[SearchResult]:
      """
      RRF formula: score(d) = sum(1 / (k + rank_i))
      where rank_i is the rank of document d in result list i
      """
      scores = defaultdict(float)
      results_map = {}
      
      # Process semantic results
      for rank, result in enumerate(semantic_results, start=1):
          scores[result.chunk_id] += 1 / (k + rank)
          results_map[result.chunk_id] = result
      
      # Process lexical results
      for rank, result in enumerate(lexical_results, start=1):
          scores[result.chunk_id] += 1 / (k + rank)
          if result.chunk_id not in results_map:
              results_map[result.chunk_id] = result
      
      # Sort by RRF score
      sorted_results = sorted(
          results_map.values(),
          key=lambda r: scores[r.chunk_id],
          reverse=True
      )
      
      # Update scores
      for result in sorted_results:
          result.hybrid_score = scores[result.chunk_id]
      
      return sorted_results
  ```

- [ ] Implement weighted fusion (alternative):
  ```python
  def weighted_fusion(
      semantic_results: List[SearchResult],
      lexical_results: List[SearchResult],
      alpha: float = 0.5
  ) -> List[SearchResult]:
      """
      Weighted score: alpha * semantic + (1-alpha) * lexical
      """
      # Normalize scores to [0, 1]
      semantic_normalized = normalize_scores(semantic_results)
      lexical_normalized = normalize_scores(lexical_results)
      
      # Combine scores
      # ... implementation
  ```

**Time:** 4 hours

#### 7.4 Query Processing
**Tasks:**
- [ ] Create src/retrieval/query_processor.py:
  ```python
  class QueryProcessor:
      def preprocess_query(self, query: str) -> str:
          # Clean query
          # Expand abbreviations common in research
          # Handle special characters
          pass
      
      def detect_query_type(self, query: str) -> str:
          # "definition", "method", "result", "comparison"
          # Use simple heuristics or small classifier
          pass
      
      def extract_keywords(self, query: str) -> List[str]:
          # Extract important terms for filtering
          pass
  ```

- [ ] Implement query expansion (optional):
  - Add synonyms
  - Add domain-specific terms

**Time:** 3 hours

#### 7.5 Search Result Model
**Tasks:**
- [ ] Create comprehensive result model:
  ```python
  class SearchResult(BaseModel):
      chunk_id: str
      document_id: str
      content: str
      
      # Scores
      semantic_score: Optional[float] = None
      lexical_score: Optional[float] = None
      hybrid_score: Optional[float] = None
      
      # Metadata
      document_title: str
      document_authors: List[str]
      document_year: Optional[int] = None
      document_venue: Optional[str] = None
      section: Optional[str] = None
      
      # Ranking
      rank: Optional[int] = None
  ```

**Time:** 1 hour

#### 7.6 Search Evaluation
**Tasks:**
- [ ] Create search evaluation notebook
- [ ] Compare search methods:
  - Semantic only
  - Lexical only
  - Hybrid (RRF)
  - Hybrid (weighted)

- [ ] Visualize results:
  - Score distributions
  - Result overlap (Venn diagrams)
  - Top-k accuracy

- [ ] Log experiments to Comet ML

**Time:** 4 hours

**Deliverables:**
- Semantic search working (Qdrant)
- Lexical search working (Elasticsearch)
- Hybrid fusion (RRF and weighted)
- Query preprocessing
- Search evaluation framework

---

### Phase 8: Reranking with Cohere (Week 5) ⭐ MVP

#### 8.1 Cohere Reranker Setup
**Tasks:**
- [ ] Install Cohere SDK: `uv add cohere`
- [ ] Get Cohere API key from secrets
- [ ] Create src/reranking/cohere_reranker.py:
  ```python
  import cohere
  from typing import List
  
  class CohereReranker:
      def __init__(self, api_key: str, model: str = "rerank-english-v3.0"):
          self.client = cohere.Client(api_key)
          self.model = model
      
      async def rerank(
          self,
          query: str,
          documents: List[str],
          top_n: int = 10,
          max_chunks_per_doc: int = 1
      ) -> List[RerankResult]:
          """
          Rerank documents using Cohere's reranker
          """
          response = self.client.rerank(
              model=self.model,
              query=query,
              documents=documents,
              top_n=top_n,
              max_chunks_per_doc=max_chunks_per_doc,
              return_documents=True
          )
          
          return [
              RerankResult(
                  index=result.index,
                  relevance_score=result.relevance_score,
                  document=result.document.text if result.document else None
              )
              for result in response.results
          ]
  ```

**Time:** 2 hours

#### 8.2 Reranking Pipeline Integration
**Tasks:**
- [ ] Integrate reranker into search flow:
  ```python
  async def hybrid_search_with_reranking(
      query: str,
      top_k_retrieval: int = 50,
      top_k_final: int = 10,
      use_reranker: bool = True
  ) -> List[SearchResult]:
      # 1. Hybrid search (broad recall)
      hybrid_results = await hybrid_search(query, top_k=top_k_retrieval)
      
      # 2. Rerank if enabled
      if use_reranker:
          documents = [r.content for r in hybrid_results]
          reranked = await reranker.rerank(query, documents, top_n=top_k_final)
          
          # 3. Map reranked results back to original
          final_results = []
          for rerank_result in reranked:
              original = hybrid_results[rerank_result.index]
              original.rerank_score = rerank_result.relevance_score
              original.rank = len(final_results) + 1
              final_results.append(original)
          
          return final_results
      else:
          return hybrid_results[:top_k_final]
  ```

**Time:** 3 hours

#### 8.3 Reranker Error Handling
**Tasks:**
- [ ] Implement retry logic with exponential backoff:
  ```python
  from tenacity import retry, stop_after_attempt, wait_exponential
  
  @retry(
      stop=stop_after_attempt(3),
      wait=wait_exponential(multiplier=1, min=2, max=10)
  )
  async def rerank_with_retry(self, query, documents, top_n):
      # Call Cohere API
      pass
  ```

- [ ] Implement fallback strategy:
  - If API fails → use hybrid scores
  - Log failures to monitoring

- [ ] Handle rate limits:
  - Track API usage
  - Implement request queuing if needed

**Time:** 2 hours

#### 8.4 Reranking Caching
**Tasks:**
- [ ] Cache reranking results in Redis:
  ```python
  cache_key = f"rerank:{hash(query)}:{hash(tuple(doc_ids))}"
  
  # Check cache first
  cached = await redis.get(cache_key)
  if cached:
      return json.loads(cached)
  
  # Call API
  results = await reranker.rerank(...)
  
  # Cache results (1 hour TTL)
  await redis.setex(cache_key, 3600, json.dumps(results))
  ```

**Time:** 2 hours

#### 8.5 Reranking Evaluation
**Tasks:**
- [ ] Create reranking evaluation notebook
- [ ] Compare with and without reranking:
  - NDCG improvement
  - MRR improvement
  - Top-1, Top-3, Top-5 accuracy

- [ ] Measure impact on:
  - Retrieval quality
  - Latency
  - API cost

- [ ] A/B test different top_k_retrieval values (30, 50, 100)
- [ ] Log experiments to Comet ML

**Time:** 4 hours

#### 8.6 Cost Monitoring
**Tasks:**
- [ ] Track Cohere API usage:
  - Number of rerank calls
  - Number of documents reranked
  - Estimated cost per query

- [ ] Set up alerts for high usage
- [ ] Document cost analysis in README

**Time:** 1 hour

**Deliverables:**
- Cohere reranker integrated
- Two-stage retrieval pipeline (recall → rerank)
- Error handling and fallbacks
- Result caching
- Reranking evaluation with metrics
- Cost monitoring

---

### Phase 9: RAG Pipeline with LLM (Week 5) ⭐ MVP

#### 9.1 Claude Integration (Anthropic)
**Tasks:**
- [ ] Install Anthropic SDK: `uv add anthropic`
- [ ] Create src/generation/claude_generator.py:
  ```python
  import anthropic
  
  class ClaudeGenerator:
      def __init__(self, api_key: str):
          self.client = anthropic.Anthropic(api_key=api_key)
          self.model = "claude-sonnet-4-20250514"
      
      async def generate(
          self,
          query: str,
          context: List[SearchResult],
          stream: bool = False
      ) -> GenerationResult:
          """
          Generate answer based on retrieved context
          """
          # Build prompt
          prompt = self._build_prompt(query, context)
          
          # Call Claude
          if stream:
              return await self._generate_stream(prompt)
          else:
              return await self._generate(prompt)
      
      def _build_prompt(self, query: str, context: List[SearchResult]) -> str:
          # Format context with sources
          context_text = "\n\n".join([
              f"[Source {i+1}] {result.document_title} ({result.document_year})\n"
              f"Section: {result.section}\n"
              f"Content: {result.content}"
              for i, result in enumerate(context)
          ])
          
          prompt = f"""You are a helpful research assistant. Answer the user's question based on the provided academic paper excerpts.

Rules:
1. Only use information from the provided sources
2. Cite sources using [Source N] format
3. If the sources don't contain enough information, say so
4. Be precise and academic in tone
5. Mention relevant papers, authors, and years

Context from research papers:
{context_text}

Question: {query}

Answer:"""
          return prompt
  ```

**Time:** 4 hours

#### 9.2 OpenAI Integration (Fallback)
**Tasks:**
- [ ] Install OpenAI SDK: `uv add openai`
- [ ] Create src/generation/openai_generator.py (similar structure to Claude)
- [ ] Implement same interface as Claude generator

**Time:** 2 hours

#### 9.3 Academic-Focused Prompt Engineering
**Tasks:**
- [ ] Create src/generation/prompt_templates.py:
  ```python
  SYSTEM_PROMPT = """You are an expert research assistant specialized in academic literature. Your role is to provide accurate, well-cited answers based on research papers.

Core principles:
- Accuracy: Only state information present in sources
- Citations: Always cite sources using [Source N] format
- Academic tone: Professional and precise language
- Completeness: Address all aspects of the question
- Transparency: Acknowledge limitations in sources"""

  def build_context_prompt(results: List[SearchResult]) -> str:
      # Format context with rich metadata
      pass
  
  def build_comparative_prompt(query: str, results: List[SearchResult]) -> str:
      # Special prompt for comparing papers
      pass
  
  def build_definition_prompt(query: str, results: List[SearchResult]) -> str:
      # Special prompt for definitions
      pass
  ```

- [ ] Create prompts for different query types:
  - Factual questions
  - Methodological questions
  - Comparative questions
  - Definition questions

**Time:** 3 hours

#### 9.4 Context Construction
**Tasks:**
- [ ] Implement intelligent context assembly:
  ```python
  class ContextBuilder:
      def build_context(
          self,
          query: str,
          results: List[SearchResult],
          max_tokens: int = 6000
      ) -> str:
          """
          Assemble context from search results
          """
          # 1. Deduplicate results from same document
          deduped = self._deduplicate(results)
          
          # 2. Sort by relevance score
          sorted_results = sorted(deduped, key=lambda r: r.rerank_score, reverse=True)
          
          # 3. Fit into token budget
          context_chunks = []
          token_count = 0
          
          for result in sorted_results:
              chunk_tokens = self._estimate_tokens(result.content)
              if token_count + chunk_tokens <= max_tokens:
                  context_chunks.append(result)
                  token_count += chunk_tokens
              else:
                  break
          
          # 4. Format with metadata
          return self._format_context(context_chunks)
  ```

- [ ] Implement token counting (approximate)
- [ ] Handle context window overflow

**Time:** 3 hours

#### 9.5 Streaming Response
**Tasks:**
- [ ] Implement streaming for Claude:
  ```python
  async def _generate_stream(self, prompt: str):
      async with self.client.messages.stream(
          model=self.model,
          max_tokens=2048,
          messages=[{"role": "user", "content": prompt}]
      ) as stream:
          async for text in stream.text_stream:
              yield text
  ```

- [ ] Create FastAPI streaming endpoint (next phase)

**Time:** 2 hours

#### 9.6 Answer Quality Checks
**Tasks:**
- [ ] Implement post-generation checks:
  ```python
  class AnswerValidator:
      def validate_answer(self, answer: str, context: List[SearchResult]) -> ValidationResult:
          checks = {
              "has_citations": self._check_citations(answer),
              "sufficient_length": len(answer) > 100,
              "not_refusal": not self._is_refusal(answer),
              "proper_format": self._check_format(answer)
          }
          
          return ValidationResult(
              is_valid=all(checks.values()),
              checks=checks
          )
      
      def _check_citations(self, answer: str) -> bool:
          # Check for [Source N] patterns
          return bool(re.search(r'\[Source \d+\]', answer))
      
      def _is_refusal(self, answer: str) -> bool:
          # Check for common refusal phrases
          refusal_phrases = [
              "I don't have enough information",
              "The sources don't contain",
              "I cannot answer"
          ]
          return any(phrase.lower() in answer.lower() for phrase in refusal_phrases)
  ```

**Time:** 2 hours

#### 9.7 Full RAG Pipeline
**Tasks:**
- [ ] Create src/core/rag_pipeline.py:
  ```python
  class RAGPipeline:
      def __init__(
          self,
          retriever,
          reranker,
          generator,
          context_builder,
          validator
      ):
          self.retriever = retriever
          self.reranker = reranker
          self.generator = generator
          self.context_builder = context_builder
          self.validator = validator
      
      async def query(self, query: str, top_k: int = 10) -> RAGResponse:
          # 1. Retrieve documents
          search_results = await self.retriever.hybrid_search(query, top_k=50)
          
          # 2. Rerank
          reranked_results = await self.reranker.rerank(query, search_results, top_n=top_k)
          
          # 3. Build context
          context = self.context_builder.build_context(query, reranked_results)
          
          # 4. Generate answer
          answer = await self.generator.generate(query, reranked_results)
          
          # 5. Validate answer
          validation = self.validator.validate_answer(answer, reranked_results)
          
          # 6. Return response
          return RAGResponse(
              query=query,
              answer=answer,
              sources=reranked_results,
              validation=validation,
              metadata={
                  "num_sources": len(reranked_results),
                  "context_tokens": self._estimate_tokens(context)
              }
          )
  ```

**Time:** 3 hours

**Deliverables:**
- Claude LLM integration
- OpenAI fallback
- Academic-focused prompt templates
- Context building logic
- Streaming support
- Answer validation
- Complete RAG pipeline

---

### Phase 10: FastAPI Application (Week 6) ⭐ MVP

#### 10.1 FastAPI Application Structure
**Tasks:**
- [ ] Create src/api/main.py:
  ```python
  from fastapi import FastAPI
  from fastapi.middleware.cors import CORSMiddleware
  
  app = FastAPI(
      title="Hybrid RAG Research API",
      description="RAG system for academic research papers",
      version="1.0.0"
  )
  
  # CORS
  app.add_middleware(
      CORSMiddleware,
      allow_origins=["*"],  # Configure properly for production
      allow_credentials=True,
      allow_methods=["*"],
      allow_headers=["*"],
  )
  
  # Include routers
  from src.api.routes import documents, search, query, system
  app.include_router(documents.router, prefix="/api/v1/documents", tags=["documents"])
  app.include_router(search.router, prefix="/api/v1/search", tags=["search"])
  app.include_router(query.router, prefix="/api/v1/query", tags=["query"])
  app.include_router(system.router, prefix="/api/v1", tags=["system"])
  
  @app.on_event("startup")
  async def startup():
      # Initialize services
      pass
  
  @app.on_event("shutdown")
  async def shutdown():
      # Cleanup
      pass
  ```

**Time:** 2 hours

#### 10.2 Document Management Endpoints
**Tasks:**
- [ ] Create src/api/routes/documents.py:
  ```python
  from fastapi import APIRouter, UploadFile, File, BackgroundTasks
  
  router = APIRouter()
  
  @router.post("/ingest")
  async def ingest_document(
      file: UploadFile = File(...),
      metadata: Optional[Dict] = None,
      chunker_type: str = "semantic",
      background_tasks: BackgroundTasks = None
  ):
      """
      Upload and index a document
      """
      # 1. Save to S3
      # 2. Queue for processing (background task)
      # 3. Return job ID
      pass
  
  @router.get("/{document_id}")
  async def get_document(document_id: str):
      """
      Retrieve document metadata and chunks
      """
      pass
  
  @router.delete("/{document_id}")
  async def delete_document(document_id: str):
      """
      Delete document from all indices
      """
      pass
  
  @router.get("")
  async def list_documents(
      skip: int = 0,
      limit: int = 20,
      filter_year: Optional[int] = None,
      filter_venue: Optional[str] = None
  ):
      """
      List documents with pagination and filtering
      """
      pass
  
  @router.get("/{document_id}/status")
  async def get_ingestion_status(document_id: str):
      """
      Check ingestion job status
      """
      pass
  ```

**Time:** 4 hours

#### 10.3 Search Endpoints
**Tasks:**
- [ ] Create src/api/routes/search.py:
  ```python
  from fastapi import APIRouter
  from src.api.models.requests import SearchRequest
  from src.api.models.responses import SearchResponse
  
  router = APIRouter()
  
  @router.post("", response_model=SearchResponse)
  async def search(request: SearchRequest):
      """
      Hybrid search without LLM generation
      """
      # 1. Parse query
      # 2. Hybrid search
      # 3. Optional reranking
      # 4. Return results
      pass
  ```

**Time:** 2 hours

#### 10.4 RAG Query Endpoints
**Tasks:**
- [ ] Create src/api/routes/query.py:
  ```python
  from fastapi import APIRouter
  from fastapi.responses import StreamingResponse
  from src.api.models.requests import QueryRequest
  from src.api.models.responses import QueryResponse
  
  router = APIRouter()
  
  @router.post("", response_model=QueryResponse)
  async def query(request: QueryRequest):
      """
      Full RAG query with answer generation
      """
      # 1. Run RAG pipeline
      # 2. Return answer with sources
      pass
  
  @router.post("/stream")
  async def query_stream(request: QueryRequest):
      """
      Streaming RAG response
      """
      async def generate():
          async for chunk in rag_pipeline.query_stream(request.query):
              yield f"data: {chunk}\n\n"
      
      return StreamingResponse(generate(), media_type="text/event-stream")
  ```

**Time:** 3 hours

#### 10.5 System Endpoints
**Tasks:**
- [ ] Create src/api/routes/system.py:
  ```python
  from fastapi import APIRouter
  
  router = APIRouter()
  
  @router.get("/health")
  async def health_check():
      """
      Health check endpoint
      """
      return {
          "status": "healthy",
          "services": {
              "qdrant": await check_qdrant(),
              "elasticsearch": await check_elasticsearch(),
              "redis": await check_redis()
          }
      }
  
  @router.get("/metrics")
  async def get_metrics():
      """
      System metrics
      """
      return {
          "total_documents": await get_document_count(),
          "total_chunks": await get_chunk_count(),
          "cache_hit_rate": await get_cache_stats(),
          "avg_query_latency": await get_latency_stats()
      }
  ```

**Time:** 2 hours

#### 10.6 Pydantic Request/Response Models
**Tasks:**
- [ ] Create src/api/models/requests.py:
  ```python
  from pydantic import BaseModel, Field
  
  class SearchRequest(BaseModel):
      query: str = Field(..., min_length=1)
      top_k: int = Field(10, ge=1, le=100)
      search_type: str = Field("hybrid", pattern="^(semantic|lexical|hybrid)$")
      use_reranker: bool = True
      filters: Optional[Dict[str, Any]] = None
  
  class QueryRequest(BaseModel):
      query: str = Field(..., min_length=1)
      top_k: int = Field(10, ge=1, le=100)
      use_reranker: bool = True
      stream: bool = False
      filters: Optional[Dict[str, Any]] = None
  ```

- [ ] Create src/api/models/responses.py:
  ```python
  from pydantic import BaseModel
  
  class Source(BaseModel):
      document_id: str
      document_title: str
      document_authors: List[str]
      document_year: Optional[int]
      section: Optional[str]
      content: str
      relevance_score: float
  
  class QueryResponse(BaseModel):
      query: str
      answer: str
      sources: List[Source]
      confidence: float
      latency_ms: float
      metadata: Dict[str, Any]
  ```

**Time:** 2 hours

#### 10.7 Middleware & Error Handling
**Tasks:**
- [ ] Create src/api/middleware/logging.py:
  ```python
  import time
  from fastapi import Request
  from loguru import logger
  
  @app.middleware("http")
  async def log_requests(request: Request, call_next):
      # Generate correlation ID
      correlation_id = str(uuid.uuid4())
      request.state.correlation_id = correlation_id
      
      # Log request
      logger.info(
          f"Request started",
          correlation_id=correlation_id,
          method=request.method,
          path=request.url.path
      )
      
      # Process request
      start_time = time.time()
      response = await call_next(request)
      latency = time.time() - start_time
      
      # Log response
      logger.info(
          f"Request completed",
          correlation_id=correlation_id,
          status_code=response.status_code,
          latency_ms=latency * 1000
      )
      
      return response
  ```

- [ ] Create src/api/middleware/error_handler.py:
  ```python
  from fastapi import Request
  from fastapi.responses import JSONResponse
  
  @app.exception_handler(Exception)
  async def global_exception_handler(request: Request, exc: Exception):
      logger.error(
          f"Unhandled exception",
          correlation_id=request.state.correlation_id,
          error=str(exc),
          exc_info=True
      )
      
      return JSONResponse(
          status_code=500,
          content={
              "error": "Internal server error",
              "correlation_id": request.state.correlation_id
          }
      )
  ```

**Time:** 2 hours

#### 10.8 Authentication
**Tasks:**
- [ ] Create src/api/middleware/auth.py:
  ```python
  from fastapi import Security, HTTPException
  from fastapi.security import APIKeyHeader
  
  api_key_header = APIKeyHeader(name="X-API-Key")
  
  async def verify_api_key(api_key: str = Security(api_key_header)):
      if api_key not in VALID_API_KEYS:  # Load from config/database
          raise HTTPException(
              status_code=401,
              detail="Invalid API key"
          )
      return api_key
  ```

- [ ] Add authentication to endpoints:
  ```python
  @router.post("")
  async def query(
      request: QueryRequest,
      api_key: str = Depends(verify_api_key)
  ):
      # ...
  ```

**Time:** 2 hours

#### 10.9 Rate Limiting
**Tasks:**
- [ ] Install slowapi: `uv add slowapi`
- [ ] Add rate limiting:
  ```python
  from slowapi import Limiter, _rate_limit_exceeded_handler
  from slowapi.util import get_remote_address
  
  limiter = Limiter(key_func=get_remote_address)
  app.state.limiter = limiter
  app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
  
  @router.post("")
  @limiter.limit("10/minute")
  async def query(request: Request, query_request: QueryRequest):
      # ...
  ```

**Time:** 2 hours

#### 10.10 API Documentation
**Tasks:**
- [ ] Enhance OpenAPI docs with examples:
  ```python
  @router.post(
      "",
      summary="Query the RAG system",
      description="Submit a question and receive an AI-generated answer based on indexed research papers",
      response_description="Answer with cited sources"
  )
  async def query(...):
      # ...
  ```

- [ ] Add request/response examples
- [ ] Document authentication
- [ ] Create API usage guide in docs/API.md

**Time:** 2 hours

**Deliverables:**
- FastAPI application with all core endpoints
- Document ingestion with background processing
- Search and query endpoints
- Health and metrics endpoints
- Request/response validation
- Authentication and rate limiting
- Comprehensive error handling
- OpenAPI documentation

---

### Phase 11: Observability with OPIK & Comet ML (Week 6) ⭐ MVP

#### 11.1 OPIK Integration
**Tasks:**
- [ ] Install OPIK: `uv add opik`
- [ ] Configure OPIK client:
  ```python
  from opik import Opik, track
  
  opik_client = Opik(
      api_key=settings.opik_api_key,
      project_name="hybrid-rag-research"
  )
  ```

- [ ] Add tracing to RAG pipeline:
  ```python
  @track
  async def rag_pipeline_query(query: str):
      with opik_client.trace("embedding"):
          query_vector = await embed_query(query)
      
      with opik_client.trace("hybrid_search"):
          search_results = await hybrid_search(query, query_vector)
      
      with opik_client.trace("reranking"):
          reranked_results = await rerank(search_results)
      
      with opik_client.trace("generation"):
          answer = await generate_answer(query, reranked_results)
      
      return answer
  ```

- [ ] Track custom metrics:
  - Number of chunks retrieved
  - Retrieval scores
  - Reranking scores
  - Token usage
  - API costs

**Time:** 4 hours

#### 11.2 Enhanced Logging with Loguru
**Tasks:**
- [ ] Structure all logs consistently:
  ```python
  logger.info(
      "Search completed",
      correlation_id=correlation_id,
      query=query,
      num_results=len(results),
      latency_ms=latency,
      search_type="hybrid",
      used_reranker=True
  )
  ```

- [ ] Log all component interactions:
  - Parser operations
  - Embedding generation
  - Index operations
  - Search operations
  - Reranking
  - LLM calls

- [ ] Log errors with full context:
  ```python
  logger.error(
      "Reranking failed",
      correlation_id=correlation_id,
      query=query,
      num_candidates=len(candidates),
      error=str(e),
      exc_info=True
  )
  ```

**Time:** 2 hours

#### 11.3 Metrics Collection
**Tasks:**
- [ ] Create src/utils/metrics.py:
  ```python
  class MetricsCollector:
      def __init__(self, redis_client):
          self.redis = redis_client
      
      async def record_query(self, latency: float, success: bool):
          # Increment counters
          await self.redis.incr("metrics:total_queries")
          if success:
              await self.redis.incr("metrics:successful_queries")
          
          # Record latency (sliding window)
          await self.redis.zadd("metrics:latencies", {str(time.time()): latency})
      
      async def record_search_quality(self, num_results: int, avg_score: float):
          # Track search quality metrics
          pass
      
      async def get_stats(self) -> Dict:
          # Aggregate metrics
          pass
  ```

- [ ] Track key metrics:
  - Request count (total, by endpoint)
  - Success/failure rate
  - Latency percentiles (p50, p95, p99)
  - Cache hit rate
  - Token usage
  - API costs (estimated)

**Time:** 3 hours

#### 11.4 Comet ML Experiment Tracking
**Tasks:**
- [ ] Initialize Comet ML:
  ```python
  from comet_ml import Experiment
  
  experiment = Experiment(
      api_key=settings.comet_api_key,
      project_name="hybrid-rag-research",
      workspace=settings.comet_workspace
  )
  ```

- [ ] Log experiments:
  ```python
  # Log configuration
  experiment.log_parameters({
      "embedding_model": "bge-base-en-v1.5",
      "chunker_type": "semantic",
      "chunk_size": 512,
      "top_k": 10,
      "reranker": "cohere-v3"
  })
  
  # Log metrics
  experiment.log_metrics({
      "mrr": 0.75,
      "ndcg_10": 0.68,
      "answer_faithfulness": 0.82
  })
  
  # Log artifacts
  experiment.log_asset("eval_results.json")
  ```

- [ ] Create experiment tracking for:
  - Chunking strategy comparisons
  - Embedding model comparisons
  - Search parameter tuning
  - Reranking evaluation
  - End-to-end RAG quality

**Time:** 3 hours

#### 11.5 Dashboard Creation
**Tasks:**
- [ ] Create monitoring dashboard (simple HTML or Streamlit):
  - Real-time request count
  - Average latency
  - Error rate
  - Cache statistics
  - Top queries
  - System health

- [ ] Or use existing tools:
  - OPIK dashboard (built-in)
  - Comet ML dashboard (built-in)
  - CloudWatch dashboard (AWS)

**Time:** 4 hours (if building custom) or 1 hour (if using existing)

**Deliverables:**
- OPIK tracing throughout RAG pipeline
- Comprehensive structured logging
- Metrics collection system
- Comet ML experiment tracking
- Monitoring dashboard

---

## 🔄 Post-MVP Phases (Weeks 7-12)

### Phase 12: Synthetic Evaluation Dataset (Week 7)

#### 12.1 QA Generation with LLM
**Tasks:**
- [ ] Create scripts/generate_eval_dataset.py
- [ ] For each indexed document:
  - Generate 3-5 questions per paper
  - Generate expected answers
  - Label difficulty (easy, medium, hard)
  - Tag question type (factual, methodological, comparative)

- [ ] Use Claude/GPT-4 for generation:
  ```python
  prompt = f"""Based on this research paper excerpt, generate 3 questions that test understanding:

Paper: {paper_title}
Section: {section}
Content: {chunk_content}

Generate:
1. One factual question (who, what, when, where)
2. One methodological question (how was X done?)
3. One analytical question (why, implications)

Format:
Q: [question]
A: [expected answer]
Type: [factual/methodological/analytical]
Difficulty: [easy/medium/hard]
"""
  ```

- [ ] Manual review and refinement of generated questions
- [ ] Target: 100-200 high-quality QA pairs

**Time:** 8 hours

#### 12.2 Evaluation Framework
**Tasks:**
- [ ] Create scripts/run_evaluation.py
- [ ] Implement evaluation metrics:
  - **Retrieval:** MRR, NDCG@K, Recall@K, Precision@K
  - **Generation:** Faithfulness, Relevance, RAGAS metrics

- [ ] Run evaluation pipeline:
  ```python
  async def evaluate_system(eval_dataset: List[QA]):
      results = []
      
      for qa in eval_dataset:
          # Run RAG
          response = await rag_pipeline.query(qa.question)
          
          # Evaluate retrieval
          retrieval_metrics = evaluate_retrieval(
              retrieved=response.sources,
              ground_truth=qa.relevant_chunks
          )
          
          # Evaluate generation
          generation_metrics = evaluate_generation(
              generated=response.answer,
              expected=qa.expected_answer,
              context=response.sources
          )
          
          results.append({
              "question": qa.question,
              "retrieval": retrieval_metrics,
              "generation": generation_metrics
          })
      
      return aggregate_results(results)
  ```

**Time:** 8 hours

#### 12.3 RAGAS Integration
**Tasks:**
- [ ] Install RAGAS: `uv add ragas`
- [ ] Implement RAGAS metrics:
  - Context Relevancy
  - Answer Faithfulness
  - Answer Relevancy
  - Context Recall
  - Context Precision

- [ ] Run RAGAS evaluation:
  ```python
  from ragas import evaluate
  from ragas.metrics import faithfulness, answer_relevancy, context_recall
  
  result = evaluate(
      dataset=eval_dataset,
      metrics=[faithfulness, answer_relevancy, context_recall]
  )
  ```

**Time:** 4 hours

#### 12.4 Continuous Evaluation
**Tasks:**
- [ ] Set up automated evaluation:
  - Run on every major change
  - Track metric trends over time
  - Alert on regression

- [ ] Create evaluation notebook: notebooks/evaluation_dashboard.ipynb
- [ ] Visualize results:
  - Metric trends
  - Per-question-type performance
  - Failure analysis

**Time:** 4 hours

**Deliverables:**
- 100-200 synthetic QA pairs
- Comprehensive evaluation framework
- RAGAS integration
- Automated evaluation pipeline
- Evaluation dashboard

---

### Phase 13: Performance Optimization (Week 8)

#### 13.1 Query Caching
**Tasks:**
- [ ] Implement full query result caching:
  ```python
  cache_key = f"query:{hash(query)}:{top_k}:{filters}"
  
  cached_result = await redis.get(cache_key)
  if cached_result:
      return json.loads(cached_result)
  
  result = await rag_pipeline.query(query)
  
  await redis.setex(cache_key, 3600, json.dumps(result))
  ```

- [ ] Cache invalidation strategy:
  - Time-based (TTL)
  - Event-based (when new documents indexed)

**Time:** 3 hours

#### 13.2 Embedding Caching
**Tasks:**
- [ ] Cache embeddings for:
  - All indexed chunks (permanent)
  - Frequent queries (time-based)

- [ ] Implement warm-up cache:
  - Pre-compute embeddings for common queries
  - Background refresh

**Time:** 2 hours

#### 13.3 Database Optimization
**Tasks:**
- [ ] Qdrant optimization:
  - Tune HNSW parameters
  - Experiment with quantization (int8, binary)
  - Optimize payload indexing

- [ ] Elasticsearch optimization:
  - Tune shard/replica configuration
  - Optimize analyzers
  - Index refresh interval tuning

**Time:** 4 hours

#### 13.4 Code Profiling
**Tasks:**
- [ ] Profile application with py-spy:
  ```bash
  py-spy record -o profile.svg -- python -m uvicorn src.api.main:app
  ```

- [ ] Identify bottlenecks:
  - Slow functions
  - Memory leaks
  - Blocking I/O

- [ ] Optimize hot paths

**Time:** 4 hours

#### 13.5 Load Testing
**Tasks:**
- [ ] Create tests/load/locustfile.py:
  ```python
  from locust import HttpUser, task, between
  
  class RAGUser(HttpUser):
      wait_time = between(1, 3)
      
      @task(3)
      def search(self):
          self.client.post("/api/v1/search", json={
              "query": random.choice(QUERIES),
              "top_k": 10
          })
      
      @task(1)
      def query(self):
          self.client.post("/api/v1/query", json={
              "query": random.choice(QUERIES),
              "top_k": 10
          })
  ```

- [ ] Run load tests:
  - 10 concurrent users
  - 100 concurrent users
  - 500 concurrent users

- [ ] Measure and document:
  - Throughput (requests/sec)
  - Latency (p50, p95, p99)
  - Error rate
  - Resource utilization

**Time:** 4 hours

#### 13.6 Connection Pooling
**Tasks:**
- [ ] Implement connection pools for:
  - Qdrant client
  - Elasticsearch client
  - Redis client
  - HTTP clients (httpx)

**Time:** 2 hours

**Deliverables:**
- Full query caching implemented
- Database performance optimized
- Application profiled and optimized
- Load testing results documented
- Performance benchmarks

---

### Phase 14: Docker Containerization (Week 9)

#### 14.1 Production Dockerfile
**Tasks:**
- [ ] Create docker/Dockerfile:
  ```dockerfile
  # Multi-stage build
  FROM python:3.12-slim as builder
  
  # Install UV
  RUN pip install uv
  
  WORKDIR /app
  
  # Copy dependency files
  COPY pyproject.toml uv.lock ./
  
  # Install dependencies
  RUN uv sync --frozen --no-dev
  
  # Final stage
  FROM python:3.12-slim
  
  WORKDIR /app
  
  # Copy installed dependencies from builder
  COPY --from=builder /app/.venv /app/.venv
  
  # Copy application code
  COPY src/ ./src/
  COPY configs/ ./configs/
  
  # Create non-root user
  RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
  USER appuser
  
  EXPOSE 8000
  
  CMD ["/app/.venv/bin/uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
  ```

- [ ] Optimize image size:
  - Multi-stage build
  - Minimal base image
  - Layer caching
  - .dockerignore

**Time:** 3 hours

#### 14.2 Production Docker Compose
**Tasks:**
- [ ] Create docker/docker-compose.prod.yml:
  ```yaml
  version: '3.8'
  
  services:
    api:
      build:
        context: ..
        dockerfile: docker/Dockerfile
      image: hybrid-rag-api:latest
      container_name: rag-api
      ports:
        - "8000:8000"
      environment:
        - QDRANT_URL=http://qdrant:6333
        - ELASTICSEARCH_URL=http://elasticsearch:9200
        - REDIS_URL=redis://redis:6379
      env_file:
        - ../.env
      depends_on:
        - qdrant
        - elasticsearch
        - redis
      restart: unless-stopped
      healthcheck:
        test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
        interval: 30s
        timeout: 10s
        retries: 3
    
    qdrant:
      image: qdrant/qdrant:latest
      ports:
        - "6333:6333"
      volumes:
        - qdrant_data:/qdrant/storage
      restart: unless-stopped
    
    elasticsearch:
      image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
      environment:
        - discovery.type=single-node
        - xpack.security.enabled=false
        - ES_JAVA_OPTS=-Xms4g -Xmx4g
      ports:
        - "9200:9200"
      volumes:
        - es_data:/usr/share/elasticsearch/data
      restart: unless-stopped
    
    redis:
      image: redis:7-alpine
      ports:
        - "6379:6379"
      volumes:
        - redis_data:/data
      restart: unless-stopped
  
  volumes:
    qdrant_data:
    es_data:
    redis_data:
  ```

**Time:** 2 hours

#### 14.3 Docker Testing
**Tasks:**
- [ ] Build image: `docker build -t hybrid-rag-api:latest -f docker/Dockerfile .`
- [ ] Test locally with docker-compose
- [ ] Verify all services working
- [ ] Test health checks
- [ ] Document image size and build time

**Time:** 2 hours

#### 14.4 ECR Push
**Tasks:**
- [ ] Authenticate to ECR:
  ```bash
  aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com
  ```

- [ ] Tag image:
  ```bash
  docker tag hybrid-rag-api:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/hybrid-rag-api:latest
  docker tag hybrid-rag-api:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/hybrid-rag-api:v1.0.0
  ```

- [ ] Push to ECR:
  ```bash
  docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/hybrid-rag-api:latest
  docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/hybrid-rag-api:v1.0.0
  ```

**Time:** 1 hour

**Deliverables:**
- Production Dockerfile optimized
- Docker Compose for production
- Image pushed to ECR
- Documentation for Docker deployment

---

### Phase 15: Kubernetes on AWS EKS (Week 10-11)

#### 15.1 EKS Cluster Creation
**Tasks:**
- [ ] Create EKS cluster using eksctl:
  ```bash
  eksctl create cluster \
    --name hybrid-rag-cluster \
    --region us-east-1 \
    --nodegroup-name standard-workers \
    --node-type t3.xlarge \
    --nodes 3 \
    --nodes-min 2 \
    --nodes-max 5 \
    --managed \
    --alb-ingress-access \
    --full-ecr-access
  ```

- [ ] Wait for cluster creation (20-30 minutes)
- [ ] Configure kubectl:
  ```bash
  aws eks update-kubeconfig --name hybrid-rag-cluster --region us-east-1
  ```

- [ ] Verify cluster:
  ```bash
  kubectl get nodes
  kubectl get namespaces
  ```

**Time:** 2 hours (including waiting)

#### 15.2 Kubernetes Manifests
**Tasks:**
- [ ] Create k8s/namespace.yaml:
  ```yaml
  apiVersion: v1
  kind: Namespace
  metadata:
    name: hybrid-rag
  ```

- [ ] Create k8s/configmaps/app-config.yaml:
  ```yaml
  apiVersion: v1
  kind: ConfigMap
  metadata:
    name: app-config
    namespace: hybrid-rag
  data:
    QDRANT_URL: "http://qdrant-service:6333"
    ELASTICSEARCH_URL: "http://elasticsearch-service:9200"
    REDIS_URL: "redis://redis-service:6379"
    LOG_LEVEL: "INFO"
  ```

- [ ] Create k8s/secrets/api-secrets.yaml:
  ```yaml
  apiVersion: v1
  kind: Secret
  metadata:
    name: api-secrets
    namespace: hybrid-rag
  type: Opaque
  stringData:
    ANTHROPIC_API_KEY: "your-key"
    OPENAI_API_KEY: "your-key"
    COHERE_API_KEY: "your-key"
    COMET_API_KEY: "your-key"
  ```
  Note: Use AWS Secrets Manager integration in production

**Time:** 2 hours

#### 15.3 Storage Manifests
**Tasks:**
- [ ] Create k8s/storage/qdrant-pvc.yaml:
  ```yaml
  apiVersion: v1
  kind: PersistentVolumeClaim
  metadata:
    name: qdrant-pvc
    namespace: hybrid-rag
  spec:
    accessModes:
      - ReadWriteOnce
    resources:
      requests:
        storage: 50Gi
    storageClassName: gp3
  ```

- [ ] Create k8s/storage/elasticsearch-pvc.yaml (similar)

**Time:** 1 hour

#### 15.4 Deployment Manifests
**Tasks:**
- [ ] Create k8s/deployments/api-deployment.yaml:
  ```yaml
  apiVersion: apps/v1
  kind: Deployment
  metadata:
    name: rag-api
    namespace: hybrid-rag
  spec:
    replicas: 3
    selector:
      matchLabels:
        app: rag-api
    template:
      metadata:
        labels:
          app: rag-api
      spec:
        containers:
        - name: api
          image: <account-id>.dkr.ecr.us-east-1.amazonaws.com/hybrid-rag-api:latest
          ports:
          - containerPort: 8000
          env:
          - name: QDRANT_URL
            valueFrom:
              configMapKeyRef:
                name: app-config
                key: QDRANT_URL
          - name: ANTHROPIC_API_KEY
            valueFrom:
              secretKeyRef:
                name: api-secrets
                key: ANTHROPIC_API_KEY
          resources:
            requests:
              memory: "2Gi"
              cpu: "1000m"
            limits:
              memory: "4Gi"
              cpu: "2000m"
          livenessProbe:
            httpGet:
              path: /api/v1/health
              port: 8000
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /api/v1/health
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 5
  ```

- [ ] Create k8s/deployments/qdrant-statefulset.yaml
- [ ] Create k8s/deployments/elasticsearch-statefulset.yaml
- [ ] Create k8s/deployments/redis-deployment.yaml

**Time:** 4 hours

#### 15.5 Service Manifests
**Tasks:**
- [ ] Create k8s/services/api-service.yaml:
  ```yaml
  apiVersion: v1
  kind: Service
  metadata:
    name: rag-api-service
    namespace: hybrid-rag
  spec:
    selector:
      app: rag-api
    ports:
    - protocol: TCP
      port: 80
      targetPort: 8000
    type: LoadBalancer
  ```

- [ ] Create internal services for Qdrant, ES, Redis

**Time:** 2 hours

#### 15.6 HPA Configuration
**Tasks:**
- [ ] Create k8s/hpa/api-hpa.yaml:
  ```yaml
  apiVersion: autoscaling/v2
  kind: HorizontalPodAutoscaler
  metadata:
    name: rag-api-hpa
    namespace: hybrid-rag
  spec:
    scaleTargetRef:
      apiVersion: apps/v1
      kind: Deployment
      name: rag-api
    minReplicas: 2
    maxReplicas: 10
    metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
  ```

**Time:** 1 hour

#### 15.7 Ingress Configuration
**Tasks:**
- [ ] Install AWS Load Balancer Controller:
  ```bash
  kubectl apply -k "github.com/aws/eks-charts/stable/aws-load-balancer-controller//crds?ref=master"
  
  helm repo add eks https://aws.github.io/eks-charts
  helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
    -n kube-system \
    --set clusterName=hybrid-rag-cluster
  ```

- [ ] Create k8s/ingress/ingress.yaml:
  ```yaml
  apiVersion: networking.k8s.io/v1
  kind: Ingress
  metadata:
    name: rag-api-ingress
    namespace: hybrid-rag
    annotations:
      kubernetes.io/ingress.class: alb
      alb.ingress.kubernetes.io/scheme: internet-facing
      alb.ingress.kubernetes.io/target-type: ip
      alb.ingress.kubernetes.io/healthcheck-path: /api/v1/health
  spec:
    rules:
    - http:
        paths:
        - path: /
          pathType: Prefix
          backend:
            service:
              name: rag-api-service
              port:
                number: 80
  ```

**Time:** 2 hours

#### 15.8 Deploy to EKS
**Tasks:**
- [ ] Apply all manifests:
  ```bash
  kubectl apply -f k8s/namespace.yaml
  kubectl apply -f k8s/configmaps/
  kubectl apply -f k8s/secrets/
  kubectl apply -f k8s/storage/
  kubectl apply -f k8s/deployments/
  kubectl apply -f k8s/services/
  kubectl apply -f k8s/hpa/
  kubectl apply -f k8s/ingress/
  ```

- [ ] Verify deployments:
  ```bash
  kubectl get pods -n hybrid-rag
  kubectl get services -n hybrid-rag
  kubectl get ingress -n hybrid-rag
  ```

- [ ] Test API endpoint:
  ```bash
  INGRESS_URL=$(kubectl get ingress -n hybrid-rag -o jsonpath='{.items[0].status.loadBalancer.ingress[0].hostname}')
  curl http://$INGRESS_URL/api/v1/health
  ```

**Time:** 2 hours

#### 15.9 Monitoring Setup
**Tasks:**
- [ ] Install Prometheus:
  ```bash
  helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
  helm install prometheus prometheus-community/kube-prometheus-stack -n monitoring --create-namespace
  ```

- [ ] Install Grafana dashboards
- [ ] Configure CloudWatch Container Insights

**Time:** 3 hours

**Deliverables:**
- EKS cluster running
- All services deployed to Kubernetes
- Autoscaling configured
- Load balancer with public endpoint
- Monitoring and observability

---

### Phase 16: CI/CD Pipeline (Week 12)

#### 16.1 GitHub Actions Workflow
**Tasks:**
- [ ] Create .github/workflows/ci-cd.yml:
  ```yaml
  name: CI/CD Pipeline
  
  on:
    push:
      branches: [main, develop]
    pull_request:
      branches: [main]
  
  jobs:
    test:
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v3
        
        - name: Set up Python 3.12
          uses: actions/setup-python@v4
          with:
            python-version: '3.12'
        
        - name: Install UV
          run: pip install uv
        
        - name: Install dependencies
          run: uv sync
        
        - name: Run linting
          run: |
            uv run ruff check .
            uv run black --check .
        
        - name: Run tests
          run: uv run pytest --cov=src tests/
        
        - name: Upload coverage
          uses: codecov/codecov-action@v3
    
    build:
      needs: test
      runs-on: ubuntu-latest
      if: github.ref == 'refs/heads/main'
      steps:
        - uses: actions/checkout@v3
        
        - name: Configure AWS credentials
          uses: aws-actions/configure-aws-credentials@v2
          with:
            aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
            aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
            aws-region: us-east-1
        
        - name: Login to Amazon ECR
          id: login-ecr
          uses: aws-actions/amazon-ecr-login@v1
        
        - name: Build and push Docker image
          env:
            ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
            IMAGE_TAG: ${{ github.sha }}
          run: |
            docker build -t $ECR_REGISTRY/hybrid-rag-api:$IMAGE_TAG -f docker/Dockerfile .
            docker tag $ECR_REGISTRY/hybrid-rag-api:$IMAGE_TAG $ECR_REGISTRY/hybrid-rag-api:latest
            docker push $ECR_REGISTRY/hybrid-rag-api:$IMAGE_TAG
            docker push $ECR_REGISTRY/hybrid-rag-api:latest
    
    deploy:
      needs: build
      runs-on: ubuntu-latest
      if: github.ref == 'refs/heads/main'
      steps:
        - uses: actions/checkout@v3
        
        - name: Configure AWS credentials
          uses: aws-actions/configure-aws-credentials@v2
          with:
            aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
            aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
            aws-region: us-east-1
        
        - name: Update kubeconfig
          run: aws eks update-kubeconfig --name hybrid-rag-cluster --region us-east-1
        
        - name: Deploy to EKS
          env:
            ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
            IMAGE_TAG: ${{ github.sha }}
          run: |
            kubectl set image deployment/rag-api api=$ECR_REGISTRY/hybrid-rag-api:$IMAGE_TAG -n hybrid-rag
            kubectl rollout status deployment/rag-api -n hybrid-rag
        
        - name: Verify deployment
          run: |
            kubectl get pods -n hybrid-rag
            kubectl get services -n hybrid-rag
  ```

**Time:** 4 hours

#### 16.2 GitHub Secrets Setup
**Tasks:**
- [ ] Add secrets to GitHub repository:
  - AWS_ACCESS_KEY_ID
  - AWS_SECRET_ACCESS_KEY
  - ANTHROPIC_API_KEY
  - OPENAI_API_KEY
  - COHERE_API_KEY
  - COMET_API_KEY

**Time:** 1 hour

#### 16.3 Branch Protection
**Tasks:**
- [ ] Configure branch protection for main:
  - Require pull request reviews
  - Require status checks to pass
  - Require branches to be up to date
  - Require linear history

**Time:** 1 hour

#### 16.4 Testing CI/CD
**Tasks:**
- [ ] Create test PR to trigger workflow
- [ ] Verify tests run
- [ ] Verify Docker build
- [ ] Verify deployment (on main branch)
- [ ] Document CI/CD process

**Time:** 2 hours

**Deliverables:**
- GitHub Actions CI/CD pipeline
- Automated testing, building, and deployment
- Branch protection configured
- Documentation for CI/CD

---

### Phase 17: Documentation & Polish (Week 12)

#### 17.1 README Documentation
**Tasks:**
- [ ] Create comprehensive README.md:
  - Project overview
  - Features
  - Architecture diagram
  - Quick start guide
  - API examples
  - Configuration options
  - Deployment instructions
  - Contributing guidelines

**Time:** 3 hours

#### 17.2 API Documentation
**Tasks:**
- [ ] Create docs/API.md:
  - Authentication
  - Endpoints reference
  - Request/response examples
  - Error codes
  - Rate limiting
  - Best practices

**Time:** 2 hours

#### 17.3 Deployment Guide
**Tasks:**
- [ ] Create docs/DEPLOYMENT.md:
  - Local development setup
  - Docker deployment
  - Kubernetes deployment
  - AWS configuration
  - Monitoring setup
  - Troubleshooting

**Time:** 2 hours

#### 17.4 Evaluation Guide
**Tasks:**
- [ ] Create docs/EVALUATION.md:
  - How to create evaluation dataset
  - Running evaluations
  - Interpreting metrics
  - Improvement strategies

**Time:** 2 hours

#### 17.5 Architecture Documentation
**Tasks:**
- [ ] Create architecture diagrams:
  - System overview
  - Data flow
  - Deployment architecture
  - Monitoring architecture

- [ ] Use tools like draw.io or Mermaid

**Time:** 3 hours

**Deliverables:**
- Comprehensive README
- API documentation
- Deployment guide
- Evaluation guide
- Architecture diagrams

---

## 📊 Success Metrics & Evaluation

### System Performance Targets

| Metric | Target | Critical Threshold |
|--------|--------|-------------------|
| Search Latency (p95) | < 500ms | < 1s |
| Full RAG Query (p95) | < 3s | < 5s |
| API Availability | > 99% | > 95% |
| Error Rate | < 1% | < 5% |

### Retrieval Quality Targets

| Metric | Target | Acceptable |
|--------|--------|-----------|
| MRR | > 0.7 | > 0.6 |
| NDCG@10 | > 0.6 | > 0.5 |
| Recall@10 | > 0.8 | > 0.7 |
| Precision@10 | > 0.6 | > 0.5 |

### Generation Quality Targets

| Metric | Target | Acceptable |
|--------|--------|-----------|
| Answer Faithfulness | > 0.8 | > 0.7 |
| Answer Relevance | > 0.85 | > 0.75 |
| Citation Accuracy | > 90% | > 80% |
| User Satisfaction | > 4.0/5.0 | > 3.5/5.0 |

### Cost Efficiency Targets

| Resource | Monthly Budget | Alert Threshold |
|----------|---------------|----------------|
| AWS Infrastructure | $300 | $250 |
| LLM API Costs | $150 | $125 |
| Cohere API | $50 | $40 |
| Total | $500 | $415 |

---

## 🚧 Potential Challenges & Mitigation Strategies

### Challenge 1: Academic PDF Parsing Complexity
**Risk:** PDFs with complex layouts, equations, tables may not parse correctly

**Mitigation:**
- Use Docling's advanced layout analysis
- Implement fallback to simpler parsers
- Manual review and correction workflow for important papers
- Document known parsing limitations

### Challenge 2: Chunking Quality for Technical Content
**Risk:** Poor chunks for equations, algorithms, complex figures

**Mitigation:**
- Use section-aware chunking
- Don't split equations or code blocks
- Keep figure captions with context
- A/B test different chunkers
- Manual quality spot-checks

### Challenge 3: Retrieval Quality for Domain-Specific Queries
**Risk:** Semantic search may miss domain-specific terminology

**Mitigation:**
- Hybrid search combines BM25 (exact term matching) with semantic
- Domain-specific fine-tuning of embeddings (future)
- Query expansion with domain terms
- Reranking to improve precision

### Challenge 4: Citation Accuracy in Generated Answers
**Risk:** LLM may generate plausible but incorrect citations

**Mitigation:**
- Explicit prompt instructions for citations
- Post-processing to verify citations exist
- Answer validation checks
- Human-in-the-loop for high-stakes queries

### Challenge 5: API Cost Management
**Risk:** LLM and reranker API costs may exceed budget

**Mitigation:**
- Aggressive caching of results
- Rate limiting per user
- Prompt optimization to reduce tokens
- Monitor costs daily with alerts
- Consider self-hosted models for heavy usage

### Challenge 6: EKS Complexity for Solo Development
**Risk:** Kubernetes complexity may slow development

**Mitigation:**
- Start with Docker Compose (MVP)
- Use managed services (EKS, managed node groups)
- Leverage eksctl for cluster management
- Good documentation and runbooks
- Consider ECS as simpler alternative

### Challenge 7: Evaluation Dataset Quality
**Risk:** Synthetic dataset may not reflect real usage

**Mitigation:**
- Manual review of generated questions
- Diverse question types and difficulties
- Continuous evaluation with real queries
- Collect user feedback
- Iterative dataset improvement

### Challenge 8: Document Ingestion Bottleneck
**Risk:** Parsing and indexing large papers may be slow

**Mitigation:**
- Background task processing
- Batch processing with progress tracking
- Parallel processing (multiple workers)
- Status endpoints for tracking progress
- Incremental indexing

---

## 🎯 MVP vs Post-MVP Feature Prioritization

### MVP Features (Weeks 1-6) - Must Have ⭐
- ✅ Document parsing (Docling) for PDFs, CSV, HTML, TXT, JSON, Markdown
- ✅ Advanced chunking with Chonkie (3 strategies)
- ✅ BGE embeddings (bge-base-en-v1.5)
- ✅ Qdrant vector search + Elasticsearch BM25
- ✅ Hybrid search with RRF
- ✅ Cohere reranking
- ✅ Claude LLM for answer generation
- ✅ FastAPI with core endpoints (ingest, search, query)
- ✅ Structured logging with Loguru
- ✅ OPIK observability
- ✅ Basic Comet ML experiment tracking
- ✅ Docker Compose for local dev
- ✅ AWS S3 integration

### Post-MVP Features (Weeks 7-12) - Nice to Have 🔄
- 🔄 Comprehensive evaluation framework (100+ QA pairs)
- 🔄 RAGAS integration
- 🔄 Performance optimization (caching, profiling)
- 🔄 Load testing
- 🔄 Production Docker images
- 🔄 EKS deployment
- 🔄 CI/CD pipeline
- 🔄 Advanced monitoring dashboards
- 🔄 Comprehensive documentation

### Future Enhancements - Can Wait 💡
- 💡 Fine-tuned embeddings for research domain
- 💡 Graph-based retrieval (paper citations network)
- 💡 Multi-modal support (images, tables from papers)
- 💡 Conversational RAG (multi-turn dialogues)
- 💡 User feedback loop for continuous improvement
- 💡 Semantic caching with vector similarity
- 💡 Query suggestions and autocomplete
- 💡 Paper recommendation system
- 💡 Collaborative features (shared collections)

---

## 📅 Detailed Week-by-Week Schedule

### Week 1: Foundation
- **Days 1-2:** AWS setup, IAM, VPC, S3, Secrets Manager
- **Days 3-4:** Local dev environment, Python/UV, VS Code, Docker Compose
- **Day 5:** Logging setup, basic configuration

### Week 2: Document Processing
- **Days 1-3:** Docling integration, multi-format parsers
- **Days 4-5:** Metadata extraction, S3 integration, preprocessing pipeline

### Week 3: Chunking & Embeddings
- **Days 1-3:** Chonkie integration, academic-specific chunking
- **Days 4-5:** BGE embeddings, caching, benchmarking

### Week 4: Search Infrastructure
- **Days 1-2:** Qdrant setup and indexing
- **Days 2-3:** Elasticsearch setup and indexing
- **Days 4-5:** Hybrid search, query processing

### Week 5: Reranking & RAG
- **Days 1-2:** Cohere reranker integration
- **Days 3-5:** LLM integration, RAG pipeline, prompts

### Week 6: API & Observability
- **Days 1-3:** FastAPI endpoints, authentication, rate limiting
- **Days 4-5:** OPIK integration, metrics, basic experiments

### Week 7: Evaluation
- **Days 1-3:** Generate synthetic QA dataset
- **Days 4-5:** Evaluation framework, RAGAS, metrics

### Week 8: Optimization
- **Days 1-2:** Caching implementation
- **Days 3-4:** Performance profiling and optimization
- **Day 5:** Load testing

### Week 9: Containerization
- **Days 1-2:** Production Dockerfile
- **Days 3-4:** Docker Compose production, ECR push
- **Day 5:** Testing and documentation

### Week 10-11: Kubernetes
- **Week 10 Days 1-2:** EKS cluster creation
- **Week 10 Days 3-5:** Kubernetes manifests (deployments, services, storage)
- **Week 11 Days 1-2:** HPA, ingress, monitoring
- **Week 11 Days 3-5:** Deploy and test on EKS

### Week 12: CI/CD & Documentation
- **Days 1-2:** GitHub Actions CI/CD pipeline
- **Days 3-5:** Comprehensive documentation (README, API, deployment, evaluation)

---

## 🔧 Development Tools & Resources

### Essential Tools
- **IDE:** VS Code with Python, Docker, Kubernetes extensions
- **Terminal:** iTerm2 (Mac) or Windows Terminal
- **API Testing:** Postman, HTTPie, or curl
- **Database GUI:** 
  - Qdrant: Built-in dashboard (http://localhost:6333/dashboard)
  - Elasticsearch: Kibana or Elasticvue
  - Redis: RedisInsight
- **Kubernetes:** k9s (terminal UI), Lens (GUI)
- **Monitoring:** Grafana, CloudWatch dashboard
- **Profiling:** py-spy, memory_profiler

### Documentation Resources
- **Chonkie:** https://docs.chonkie.ai/
- **Docling:** https://github.com/DS4SD/docling
- **BGE:** https://huggingface.co/BAAI/bge-base-en-v1.5
- **Qdrant:** https://qdrant.tech/documentation/
- **Elasticsearch:** https://www.elastic.co/guide/
- **Cohere:** https://docs.cohere.com/docs/rerank-2
- **Anthropic:** https://docs.anthropic.com/
- **OPIK:** https://www.comet.com/site/products/opik/
- **Comet ML:** https://www.comet.com/docs/
- **FastAPI:** https://fastapi.tiangolo.com/
- **AWS EKS:** https://docs.aws.amazon.com/eks/

### Learning Resources
- **RAG Best Practices:** LangChain documentation, LlamaIndex guides
- **Vector Databases:** Qdrant tutorials, Pinecone guides
- **Kubernetes:** Kubernetes.io tutorials, eksctl documentation
- **Academic Paper Processing:** arXiv, GROBID, ScienceParse

---

## 📝 Project Checklist

### Setup Phase ✅
- [ ] AWS account configured
- [ ] GitHub repository created
- [ ] Local development environment ready
- [ ] Docker Compose running
- [ ] Configuration system set up

### Document Processing ✅
- [ ] Docling parser working
- [ ] All format parsers implemented
- [ ] Metadata extraction complete
- [ ] S3 integration working
- [ ] Preprocessing pipeline tested

### Chunking & Embeddings ✅
- [ ] Chonkie integrated
- [ ] Academic chunker implemented
- [ ] BGE embeddings working
- [ ] Chunk evaluation framework complete
- [ ] Experiments tracked in Comet ML

### Search Infrastructure ✅
- [ ] Qdrant indexed
- [ ] Elasticsearch indexed
- [ ] Hybrid search working
- [ ] Reranker integrated
- [ ] Search evaluation complete

### RAG Pipeline ✅
- [ ] Claude LLM integrated
- [ ] Prompts engineered
- [ ] Context building optimized
- [ ] Answer validation working
- [ ] Full pipeline tested

### API Development ✅
- [ ] All endpoints implemented
- [ ] Authentication working
- [ ] Rate limiting configured
- [ ] Error handling robust
- [ ] API documentation complete

### Observability ✅
- [ ] OPIK tracing active
- [ ] Structured logging implemented
- [ ] Metrics collection working
- [ ] Comet ML tracking active
- [ ] Dashboards created

### Evaluation ✅
- [ ] Synthetic dataset created (100+ QA)
- [ ] Evaluation framework working
- [ ] RAGAS integrated
- [ ] Metrics tracked over time
- [ ] Continuous evaluation automated

### Production Ready ✅
- [ ] Performance optimized
- [ ] Load tested
- [ ] Docker images built
- [ ] EKS deployed
- [ ] CI/CD pipeline working
- [ ] Documentation complete
- [ ] Monitoring and alerting configured

---

## 🎯 Success Criteria

The project will be considered successful when:

1. **Functionality:**
   - Can ingest PDFs, CSV, HTML, TXT, JSON, Markdown documents
   - Hybrid search returns relevant results
   - RAG system generates accurate, cited answers
   - All API endpoints working reliably

2. **Performance:**
   - Search latency < 500ms (p95)
   - RAG query latency < 3s (p95)
   - Can handle 100+ concurrent users
   - API availability > 99%

3. **Quality:**
   - MRR > 0.7 on evaluation dataset
   - Answer faithfulness > 0.8
   - Citation accuracy > 90%

4. **Production Readiness:**
   - Deployed to AWS EKS
   - CI/CD pipeline functional
   - Monitoring and alerting active
   - Comprehensive documentation

5. **Cost Efficiency:**
   - Total monthly cost < $500
   - Cost per query < $0.06

---

## 🚀 Getting Started

Once this plan is approved, we'll begin with:

1. **Week 1, Day 1:** AWS account setup and IAM configuration
2. Set up GitHub repository structure
3. Initialize local development environment
4. Get Docker Compose running with Qdrant, Elasticsearch, Redis

**Ready to start? Let's build an amazing hybrid RAG system for academic research! 🎓🔬📚**

---

## 📞 Support & Questions

For questions or clarifications during development:
- Review this project plan
- Check relevant documentation links
- Use Claude Code for implementation assistance
- Document decisions and lessons learned

**Let's build something great! 🚀**
