# API Reference

Complete API documentation for the Hybrid Search RAG system.

## Base URL

- **Local Development**: `http://localhost:8000`
- **Staging**: `https://api-staging.hybrid-rag.example.com`
- **Production**: `https://api.hybrid-rag.example.com`

## Authentication

Currently, the API does not require authentication for local development. For production deployments, implement authentication via:
- API keys (recommended for service-to-service)
- OAuth 2.0 / JWT (recommended for user-facing apps)
- AWS IAM (for AWS-internal services)

## Common Response Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Request successful |
| 201 | Created | Resource created |
| 400 | Bad Request | Invalid input |
| 404 | Not Found | Resource not found |
| 422 | Unprocessable Entity | Validation error |
| 500 | Internal Server Error | Server error |
| 503 | Service Unavailable | Service temporarily unavailable |

## Endpoints

### System

#### Health Check

Get system health status.

```http
GET /health
```

**Response**:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2025-01-15T10:30:00Z",
  "services": {
    "qdrant": "healthy",
    "elasticsearch": "healthy",
    "redis": "healthy"
  }
}
```

#### Metrics

Get system metrics (Prometheus format).

```http
GET /metrics
```

**Response**: Prometheus-formatted metrics

#### API Information

Get API version and configuration.

```http
GET /api/v1/info
```

**Response**:
```json
{
  "name": "Hybrid Search RAG API",
  "version": "1.0.0",
  "environment": "production",
  "chunking_strategies": ["token", "semantic", "sdpm"],
  "embedding_model": "BAAI/bge-base-en-v1.5",
  "embedding_dimensions": 768
}
```

### Document Management

#### Upload Document

Upload a document for processing.

```http
POST /api/v1/documents/upload
Content-Type: multipart/form-data
```

**Parameters**:
- `file` (required): PDF, DOCX, HTML, TXT, or Markdown file

**Example**:
```bash
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -F "file=@research_paper.pdf"
```

**Response**:
```json
{
  "document_id": "doc_1234567890",
  "filename": "research_paper.pdf",
  "file_size": 2048576,
  "content_type": "application/pdf",
  "uploaded_at": "2025-01-15T10:30:00Z",
  "status": "uploaded"
}
```

#### Ingest Document

Process and index an uploaded document.

```http
POST /api/v1/documents/ingest
Content-Type: application/json
```

**Request Body**:
```json
{
  "document_id": "doc_1234567890",
  "chunking_strategy": "semantic",
  "metadata": {
    "title": "Research Paper Title",
    "authors": ["Author 1", "Author 2"],
    "publication_year": 2024
  }
}
```

**Parameters**:
- `document_id` (required): Document ID from upload
- `chunking_strategy` (optional): "token", "semantic", or "sdpm" (default: "semantic")
- `metadata` (optional): Additional metadata

**Example**:
```bash
curl -X POST "http://localhost:8000/api/v1/documents/ingest" \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "doc_1234567890",
    "chunking_strategy": "semantic"
  }'
```

**Response**:
```json
{
  "document_id": "doc_1234567890",
  "status": "processing",
  "chunking_strategy": "semantic",
  "estimated_chunks": 42,
  "processing_started_at": "2025-01-15T10:31:00Z"
}
```

#### Get Document

Retrieve document metadata and status.

```http
GET /api/v1/documents/{document_id}
```

**Example**:
```bash
curl "http://localhost:8000/api/v1/documents/doc_1234567890"
```

**Response**:
```json
{
  "document_id": "doc_1234567890",
  "filename": "research_paper.pdf",
  "status": "indexed",
  "chunking_strategy": "semantic",
  "num_chunks": 42,
  "uploaded_at": "2025-01-15T10:30:00Z",
  "indexed_at": "2025-01-15T10:32:00Z",
  "metadata": {
    "title": "Research Paper Title",
    "authors": ["Author 1", "Author 2"],
    "publication_year": 2024
  }
}
```

#### Delete Document

Delete a document and its chunks from all indices.

```http
DELETE /api/v1/documents/{document_id}
```

**Example**:
```bash
curl -X DELETE "http://localhost:8000/api/v1/documents/doc_1234567890"
```

**Response**:
```json
{
  "document_id": "doc_1234567890",
  "status": "deleted",
  "deleted_at": "2025-01-15T10:35:00Z"
}
```

### Search

#### Semantic Search

Perform semantic (vector) search only.

```http
POST /api/v1/search/semantic
Content-Type: application/json
```

**Request Body**:
```json
{
  "query": "What are the latest advances in neural architectures?",
  "top_k": 10,
  "filters": {
    "publication_year": {"gte": 2023}
  },
  "score_threshold": 0.7
}
```

**Parameters**:
- `query` (required): Search query
- `top_k` (optional): Number of results (default: 10, max: 100)
- `filters` (optional): Metadata filters
- `score_threshold` (optional): Minimum similarity score (0-1)

**Example**:
```bash
curl -X POST "http://localhost:8000/api/v1/search/semantic" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "neural architecture search",
    "top_k": 5
  }'
```

**Response**:
```json
{
  "query": "neural architecture search",
  "results": [
    {
      "chunk_id": "chunk_001",
      "document_id": "doc_1234567890",
      "text": "Neural Architecture Search (NAS) has emerged as...",
      "score": 0.92,
      "metadata": {
        "page": 3,
        "section": "Introduction",
        "document_title": "Research Paper Title"
      }
    }
  ],
  "total_results": 5,
  "search_time_ms": 145
}
```

#### Lexical Search

Perform lexical (BM25) search only.

```http
POST /api/v1/search/lexical
Content-Type: application/json
```

**Request Body**:
```json
{
  "query": "transformer attention mechanism",
  "top_k": 10,
  "boost_fields": {
    "title": 2.0,
    "abstract": 1.5
  }
}
```

**Parameters**:
- `query` (required): Search query
- `top_k` (optional): Number of results (default: 10, max: 100)
- `boost_fields` (optional): Field-specific boosting

**Example**:
```bash
curl -X POST "http://localhost:8000/api/v1/search/lexical" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "transformer attention",
    "top_k": 5
  }'
```

**Response**: Same format as semantic search

#### Hybrid Search

Perform hybrid search combining lexical and semantic.

```http
POST /api/v1/search/hybrid
Content-Type: application/json
```

**Request Body**:
```json
{
  "query": "self-attention mechanisms in transformers",
  "top_k": 10,
  "alpha": 0.5,
  "rerank": true,
  "rerank_top_k": 20
}
```

**Parameters**:
- `query` (required): Search query
- `top_k` (optional): Final number of results (default: 10)
- `alpha` (optional): Semantic weight (0=lexical only, 1=semantic only, default: 0.5)
- `rerank` (optional): Use Cohere reranking (default: false)
- `rerank_top_k` (optional): Candidates for reranking (default: 20)

**Example**:
```bash
curl -X POST "http://localhost:8000/api/v1/search/hybrid" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "attention mechanisms",
    "top_k": 5,
    "alpha": 0.5,
    "rerank": true
  }'
```

**Response**:
```json
{
  "query": "attention mechanisms",
  "results": [
    {
      "chunk_id": "chunk_003",
      "document_id": "doc_1234567890",
      "text": "The attention mechanism allows the model to focus on...",
      "score": 0.89,
      "fusion_score": {
        "lexical": 12.3,
        "semantic": 0.87,
        "combined": 0.89
      },
      "rerank_score": 0.91,
      "metadata": {
        "page": 5,
        "section": "Methods"
      }
    }
  ],
  "total_results": 5,
  "search_time_ms": 287,
  "rerank_time_ms": 142
}
```

### RAG Query

#### Ask Question

Perform RAG query with LLM-generated answer.

```http
POST /api/v1/query
Content-Type: application/json
```

**Request Body**:
```json
{
  "query": "What are the key contributions of this paper?",
  "top_k": 5,
  "rerank": true,
  "include_citations": true,
  "llm_model": "claude",
  "temperature": 0.7,
  "max_tokens": 1024
}
```

**Parameters**:
- `query` (required): Question to ask
- `top_k` (optional): Number of chunks to retrieve (default: 5)
- `rerank` (optional): Use Cohere reranking (default: true)
- `include_citations` (optional): Include chunk citations (default: true)
- `llm_model` (optional): "claude" or "gpt4" (default: "claude")
- `temperature` (optional): LLM temperature (0-1, default: 0.7)
- `max_tokens` (optional): Max response tokens (default: 1024)

**Example**:
```bash
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the main findings?",
    "top_k": 5,
    "include_citations": true
  }'
```

**Response**:
```json
{
  "query": "What are the main findings?",
  "answer": "The main findings of this research are: 1) The proposed architecture achieves state-of-the-art performance... [1][2] 2) The attention mechanism shows improved interpretability... [3]",
  "citations": [
    {
      "citation_id": "[1]",
      "chunk_id": "chunk_003",
      "document_id": "doc_1234567890",
      "text": "We achieve state-of-the-art performance on...",
      "score": 0.91
    },
    {
      "citation_id": "[2]",
      "chunk_id": "chunk_007",
      "document_id": "doc_1234567890",
      "text": "Our model outperforms previous baselines by...",
      "score": 0.88
    }
  ],
  "metadata": {
    "llm_model": "claude-sonnet-4.5",
    "retrieval_time_ms": 287,
    "generation_time_ms": 2145,
    "total_time_ms": 2432,
    "tokens_used": 856
  }
}
```

#### Get Query History

Retrieve query history for a session.

```http
GET /api/v1/query/history?session_id={session_id}&limit=10
```

**Parameters**:
- `session_id` (optional): Session identifier
- `limit` (optional): Max results (default: 10, max: 100)

**Example**:
```bash
curl "http://localhost:8000/api/v1/query/history?limit=5"
```

**Response**:
```json
{
  "queries": [
    {
      "query_id": "query_001",
      "query": "What are the main findings?",
      "timestamp": "2025-01-15T10:40:00Z",
      "llm_model": "claude-sonnet-4.5",
      "tokens_used": 856
    }
  ],
  "total": 5
}
```

## Error Responses

All errors follow this format:

```json
{
  "detail": "Error message",
  "error_code": "ERROR_CODE",
  "timestamp": "2025-01-15T10:45:00Z",
  "path": "/api/v1/query",
  "request_id": "req_abcdef123456"
}
```

### Common Error Codes

| Code | Description |
|------|-------------|
| `DOCUMENT_NOT_FOUND` | Document ID doesn't exist |
| `INVALID_CHUNKING_STRATEGY` | Invalid chunking strategy |
| `VALIDATION_ERROR` | Input validation failed |
| `RATE_LIMIT_EXCEEDED` | Too many requests |
| `SERVICE_UNAVAILABLE` | External service unavailable |
| `LLM_ERROR` | LLM generation failed |
| `SEARCH_ERROR` | Search operation failed |

### Example Error

```json
{
  "detail": "Document not found",
  "error_code": "DOCUMENT_NOT_FOUND",
  "timestamp": "2025-01-15T10:45:00Z",
  "path": "/api/v1/documents/doc_invalid",
  "request_id": "req_abcdef123456"
}
```

## Rate Limits

- **General API**: 100 requests/second
- **RAG Query**: 10 requests/second
- **Document Upload**: 20 requests/minute

Rate limit headers:
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1642251600
```

## Pagination

For endpoints that support pagination:

**Request**:
```http
GET /api/v1/documents?page=2&page_size=20
```

**Parameters**:
- `page` (optional): Page number (default: 1)
- `page_size` (optional): Items per page (default: 10, max: 100)

**Response**:
```json
{
  "items": [...],
  "pagination": {
    "page": 2,
    "page_size": 20,
    "total_items": 150,
    "total_pages": 8,
    "has_next": true,
    "has_prev": true
  }
}
```

## Webhooks

Configure webhooks for document processing events:

```http
POST /api/v1/webhooks
Content-Type: application/json
```

**Request**:
```json
{
  "url": "https://your-app.com/webhook",
  "events": ["document.indexed", "document.failed"],
  "secret": "your_webhook_secret"
}
```

**Webhook Payload**:
```json
{
  "event": "document.indexed",
  "document_id": "doc_1234567890",
  "timestamp": "2025-01-15T10:50:00Z",
  "data": {
    "num_chunks": 42,
    "chunking_strategy": "semantic"
  }
}
```

## SDK Examples

### Python

```python
import httpx

# Initialize client
client = httpx.Client(base_url="http://localhost:8000")

# Upload document
with open("paper.pdf", "rb") as f:
    response = client.post(
        "/api/v1/documents/upload",
        files={"file": f}
    )
doc_id = response.json()["document_id"]

# Ingest document
client.post("/api/v1/documents/ingest", json={
    "document_id": doc_id,
    "chunking_strategy": "semantic"
})

# RAG query
response = client.post("/api/v1/query", json={
    "query": "What are the main findings?",
    "top_k": 5
})
print(response.json()["answer"])
```

### JavaScript

```javascript
const baseURL = 'http://localhost:8000';

// Upload document
const formData = new FormData();
formData.append('file', fileInput.files[0]);

const uploadResp = await fetch(`${baseURL}/api/v1/documents/upload`, {
  method: 'POST',
  body: formData
});
const { document_id } = await uploadResp.json();

// Ingest document
await fetch(`${baseURL}/api/v1/documents/ingest`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    document_id,
    chunking_strategy: 'semantic'
  })
});

// RAG query
const queryResp = await fetch(`${baseURL}/api/v1/query`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    query: 'What are the main findings?',
    top_k: 5
  })
});
const { answer } = await queryResp.json();
console.log(answer);
```

### cURL

```bash
# Upload
DOC_ID=$(curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -F "file=@paper.pdf" | jq -r '.document_id')

# Ingest
curl -X POST "http://localhost:8000/api/v1/documents/ingest" \
  -H "Content-Type: application/json" \
  -d "{\"document_id\": \"$DOC_ID\", \"chunking_strategy\": \"semantic\"}"

# Query
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the main findings?", "top_k": 5}' | jq '.answer'
```

## Interactive Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Support

- **Issues**: https://github.com/yourusername/hybrid-search-rag/issues
- **Discussions**: https://github.com/yourusername/hybrid-search-rag/discussions
- **Email**: api-support@example.com
