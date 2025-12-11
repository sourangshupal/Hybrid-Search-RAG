# System Architecture Overview

This diagram shows the high-level architecture of the Hybrid Search RAG system using a C4-style flowchart.

```mermaid
flowchart TB
    subgraph Users["👥 Users / Clients"]
        WebApp["Web Application"]
        API_Client["API Clients"]
        CLI["CLI Tools"]
    end

    subgraph AWS["☁️ AWS Cloud Infrastructure"]
        subgraph LoadBalancer["AWS Application Load Balancer"]
            ALB["ALB<br/>- SSL Termination<br/>- Health Checks<br/>- Rate Limiting"]
        end

        subgraph Kubernetes["🎯 EKS Kubernetes Cluster"]
            subgraph APILayer["API Layer (FastAPI)"]
                DocAPI["Document API<br/>/documents/*"]
                SearchAPI["Search API<br/>/search/*"]
                QueryAPI["RAG Query API<br/>/query"]
                SystemAPI["System API<br/>/health, /metrics"]
            end

            subgraph DataStores["📊 Data Storage Layer"]
                Redis["Redis Cache<br/>- Query cache<br/>- Session data"]
                Qdrant["Qdrant Vector DB<br/>- 768-dim vectors<br/>- Semantic search"]
                Elastic["Elasticsearch<br/>- BM25 search<br/>- Full-text index"]
            end

            subgraph Processing["⚙️ Processing Layer"]
                Parser["Document Parser<br/>(Docling)"]
                Chunker["Chunker<br/>(Chonkie)"]
                Embedder["Embedder<br/>(BGE)"]
                Indexer["Dual Indexer"]
            end
        end

        subgraph Storage["💾 AWS S3"]
            DocBucket["Documents Bucket"]
            LogBucket["Logs Bucket"]
            ArtifactBucket["Artifacts Bucket"]
        end

        subgraph Secrets["🔐 AWS Secrets Manager"]
            APIKeys["API Keys<br/>- Anthropic<br/>- OpenAI<br/>- Cohere"]
        end
    end

    subgraph External["🌐 External Services"]
        Claude["Anthropic Claude<br/>Sonnet 4.5"]
        GPT["OpenAI GPT-4<br/>(Fallback)"]
        Cohere["Cohere Rerank API"]
    end

    subgraph Observability["📈 Observability"]
        CloudWatch["AWS CloudWatch"]
        OPIK["OPIK Tracing"]
        CometML["Comet ML"]
    end

    %% User flows
    Users --> ALB
    ALB --> APILayer

    %% API to data stores
    DocAPI --> Redis
    DocAPI --> Storage
    DocAPI --> Processing
    SearchAPI --> Redis
    SearchAPI --> Qdrant
    SearchAPI --> Elastic
    QueryAPI --> Redis
    QueryAPI --> Qdrant
    QueryAPI --> Elastic

    %% Processing pipeline
    Parser --> Chunker
    Chunker --> Embedder
    Embedder --> Indexer
    Indexer --> Qdrant
    Indexer --> Elastic
    Parser --> DocBucket

    %% External services
    QueryAPI --> Claude
    QueryAPI --> GPT
    QueryAPI --> Cohere
    APILayer --> APIKeys

    %% Observability
    APILayer --> CloudWatch
    APILayer --> OPIK
    APILayer --> CometML

    %% Styling
    classDef primary fill:#4A90E2,stroke:#2E5C8A,stroke-width:2px,color:#fff
    classDef storage fill:#50C878,stroke:#2E7D4E,stroke-width:2px,color:#fff
    classDef external fill:#FF6B6B,stroke:#C94A4A,stroke-width:2px,color:#fff
    classDef observability fill:#FFD93D,stroke:#CCB030,stroke-width:2px,color:#333

    class DocAPI,SearchAPI,QueryAPI,SystemAPI primary
    class Redis,Qdrant,Elastic,DocBucket,LogBucket,ArtifactBucket storage
    class Claude,GPT,Cohere external
    class CloudWatch,OPIK,CometML observability
```

## Key Components

### API Layer
- **FastAPI Framework**: Async REST API with automatic OpenAPI documentation
- **Document Management**: Upload, ingest, retrieve, delete operations
- **Search Endpoints**: Semantic, lexical, and hybrid search
- **RAG Query**: Main question-answering endpoint
- **System Health**: Monitoring and metrics endpoints

### Data Storage
- **Redis**: L1 cache for queries, sessions, and frequently accessed data
- **Qdrant**: Vector database for semantic search (HNSW index, cosine similarity)
- **Elasticsearch**: Full-text search with BM25 algorithm

### Processing Pipeline
- **Docling Parser**: Extracts text, equations, tables, figures from PDFs/DOCX
- **Chonkie Chunker**: Multiple strategies (Token, Semantic, SDPM, Academic)
- **BGE Embedder**: Generates 768-dimensional embeddings
- **Dual Indexer**: Indexes to both Qdrant and Elasticsearch in parallel

### External Services
- **Claude Sonnet 4.5**: Primary LLM for answer generation
- **GPT-4**: Fallback LLM when Claude is unavailable
- **Cohere Rerank**: Semantic reranking of search results

### Observability
- **CloudWatch**: Metrics, logs, and alarms
- **OPIK**: Distributed tracing for RAG pipeline
- **Comet ML**: Experiment tracking and A/B testing
