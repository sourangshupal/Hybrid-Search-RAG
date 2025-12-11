# RAG Query Pipeline Workflow

This diagram shows the complete RAG (Retrieval-Augmented Generation) query processing pipeline.

```mermaid
sequenceDiagram
    actor User
    participant API as FastAPI<br/>Query Endpoint
    participant Cache as Redis Cache
    participant QP as Query<br/>Processor
    participant Emb as BGE<br/>Embedder
    participant Qdrant as Qdrant<br/>Vector DB
    participant ES as Elasticsearch<br/>BM25 Search
    participant RRF as Reciprocal Rank<br/>Fusion
    participant Rerank as Cohere<br/>Reranker
    participant LLM as Claude/GPT-4<br/>Generator
    participant Val as Answer<br/>Validator
    participant Obs as OPIK/CloudWatch<br/>Observability

    User->>API: POST /api/v1/query<br/>{query, top_k, rerank}
    activate API

    API->>Obs: Start trace
    API->>Cache: Check cache<br/>key: hash(query)

    alt Cache Hit
        Cache-->>API: Return cached answer
        API-->>User: Answer + citations<br/>(from cache)
    else Cache Miss
        API->>QP: Process query
        activate QP
        QP->>QP: Normalize text<br/>Extract entities<br/>Detect intent
        QP-->>API: Processed query
        deactivate QP

        API->>Emb: Embed query
        activate Emb
        Emb->>Emb: Tokenize<br/>Encode (768-dim)<br/>L2 normalize
        Emb-->>API: Query embedding
        deactivate Emb

        par Parallel Retrieval
            API->>Qdrant: Semantic search<br/>vector + top_k
            activate Qdrant
            Qdrant->>Qdrant: HNSW search<br/>Cosine similarity<br/>Filter metadata
            Qdrant-->>API: Top-N results<br/>+ scores
            deactivate Qdrant
        and
            API->>ES: Lexical search<br/>query + top_k
            activate ES
            ES->>ES: BM25 scoring<br/>Field boosting<br/>Filter metadata
            ES-->>API: Top-N results<br/>+ scores
            deactivate ES
        end

        API->>RRF: Merge results
        activate RRF
        RRF->>RRF: Reciprocal Rank Fusion<br/>score = Σ(1/(k+rank))<br/>Alpha weighting<br/>Deduplication
        RRF-->>API: Unified top-K results
        deactivate RRF

        alt Reranking Enabled
            API->>Rerank: Rerank top-20
            activate Rerank
            Rerank->>Rerank: Semantic relevance<br/>Cross-encoder scoring
            Rerank-->>API: Reranked top-K<br/>+ confidence scores
            deactivate Rerank
        end

        API->>API: Format context<br/>Concatenate chunks<br/>Add citations<br/>Trim to 8K tokens

        API->>LLM: Generate answer
        activate LLM

        alt Claude Available
            LLM->>LLM: Claude Sonnet 4.5<br/>Temperature: 0.3<br/>Max tokens: 1024
            LLM-->>API: Generated answer
        else Claude Unavailable
            LLM->>LLM: GPT-4 Fallback<br/>Temperature: 0.3<br/>Max tokens: 1024
            LLM-->>API: Generated answer
        end
        deactivate LLM

        API->>Val: Validate answer
        activate Val
        Val->>Val: Check citations<br/>Verify grounding<br/>Detect hallucinations

        alt Answer Valid
            Val-->>API: ✓ Valid
        else Answer Invalid
            Val-->>API: ✗ Invalid<br/>Re-generate
            API->>LLM: Regenerate with guidance
            LLM-->>API: Improved answer
        end
        deactivate Val

        API->>API: Extract citations<br/>Format response

        API->>Cache: Cache answer<br/>TTL: 1 hour
        API->>Obs: Log metrics:<br/>- Latency<br/>- Tokens used<br/>- Confidence

        API-->>User: Answer + citations +<br/>metadata
    end
    deactivate API

    Note over User,Obs: Total latency target: p95 < 3s, p99 < 5s
```

## Pipeline Stages

### 1. Request Reception
- User sends query via REST API
- Optional parameters: `top_k`, `rerank`, `filters`
- Distributed tracing started

### 2. Cache Check
- **Cache Hit**: Return cached answer immediately (< 10ms)
- **Cache Miss**: Proceed with full pipeline
- Cache key: Hash of normalized query + parameters

### 3. Query Processing
- **Normalization**: Lowercase, remove special chars, lemmatization
- **Entity Extraction**: Identify key terms, authors, concepts
- **Intent Detection**: Classify query type (factual, comparative, analytical)

### 4. Query Embedding
- **BGE Embedder**: Generate 768-dimensional vector
- **Normalization**: L2 norm for cosine similarity
- **Batching**: Process multiple queries if available

### 5. Parallel Retrieval
Two searches run simultaneously:

**Semantic Search (Qdrant)**:
- Vector similarity search (HNSW algorithm)
- Cosine similarity metric
- Metadata filtering (optional)
- Top-N candidates

**Lexical Search (Elasticsearch)**:
- BM25 full-text search
- Field boosting (title: 2.0x, abstract: 1.5x)
- Standard analyzer with stop words
- Top-N candidates

### 6. Result Fusion
**Reciprocal Rank Fusion (RRF)**:
```
score(doc) = Σ(1 / (k + rank))
```
Where:
- `k = 60` (constant)
- `rank` = position in result list

**Alpha Weighting**:
```
final_score = α × semantic_score + (1-α) × lexical_score
```
Where `α = 0.5` (configurable)

**Deduplication**: Remove duplicate chunks

### 7. Reranking (Optional)
- **Cohere Rerank API**: Cross-encoder model
- Input: Top-20 candidates
- Output: Top-K reranked results with confidence scores
- Improves precision by 15-25%

### 8. Context Formation
- Concatenate selected chunks
- Insert citation markers [1], [2], [3]
- Trim to fit LLM context window (max 8K tokens)
- Preserve chunk boundaries

### 9. Answer Generation
**Primary: Claude Sonnet 4.5**
- Temperature: 0.3 (factual, low creativity)
- Max tokens: 1024
- System prompt: Academic research assistant

**Fallback: GPT-4**
- Automatic failover on Claude errors
- Same parameters and prompt
- Circuit breaker pattern

### 10. Answer Validation
- **Citation Check**: Verify all claims have citations
- **Grounding Check**: Ensure answer is supported by context
- **Hallucination Detection**: Flag unsupported statements
- **Regeneration**: If invalid, regenerate with additional guidance

### 11. Response Formatting
- Extract citation metadata
- Format answer with markdown
- Add confidence score
- Include metadata (latency, token usage)

### 12. Caching & Logging
- **Cache**: Store in Redis (1 hour TTL)
- **Metrics**: Log to CloudWatch and OPIK
  - End-to-end latency
  - Component latencies
  - Token usage
  - Confidence scores
  - Cache hit rate

## Performance Targets
- **p50 latency**: < 1.5s
- **p95 latency**: < 3s
- **p99 latency**: < 5s
- **Cache hit rate**: 60-70%
- **Accuracy**: > 85% (human evaluation)
