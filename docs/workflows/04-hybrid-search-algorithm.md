# Hybrid Search Algorithm

This diagram illustrates the Reciprocal Rank Fusion (RRF) algorithm used to combine semantic and lexical search results.

```mermaid
flowchart TD
    Start([Query Input]) --> EmbedQuery[Embed Query<br/>BGE 768-dim vector]

    EmbedQuery --> ParallelSearch{Parallel<br/>Search}

    subgraph SemanticBranch["🔍 Semantic Search Path"]
        ParallelSearch -->|Vector| VectorSearch[Qdrant Vector Search]
        VectorSearch --> HNSW[HNSW Algorithm<br/>M=16, EF=100]
        HNSW --> CosineSim[Cosine Similarity<br/>sim = A·B / ||A|| ||B||]
        CosineSim --> FilterSem[Metadata Filtering<br/>Optional]
        FilterSem --> SemResults[Semantic Results<br/>Ranked by similarity]
    end

    subgraph LexicalBranch["📝 Lexical Search Path"]
        ParallelSearch -->|Text| FullText[Elasticsearch BM25]
        FullText --> BM25Scoring[BM25 Scoring<br/>TF-IDF variant]
        BM25Scoring --> FieldBoost[Field Boosting:<br/>- title: 2.0<br/>- abstract: 1.5<br/>- body: 1.0]
        FieldBoost --> FilterLex[Metadata Filtering<br/>Optional]
        FilterLex --> LexResults[Lexical Results<br/>Ranked by BM25]
    end

    SemResults --> RRFMerge[Reciprocal Rank Fusion]
    LexResults --> RRFMerge

    subgraph RRFAlgorithm["⚡ RRF Algorithm"]
        RRFMerge --> CalcRRF[Calculate RRF Score<br/>for each document]

        CalcRRF --> Formula["score(d) = Σ 1/(k + rank(d))<br/>k = 60"]

        Formula --> SemScore["semantic_score =<br/>1/(60 + rank_in_semantic)"]
        Formula --> LexScore["lexical_score =<br/>1/(60 + rank_in_lexical)"]

        SemScore --> AlphaWeight
        LexScore --> AlphaWeight

        AlphaWeight["final_score =<br/>α × semantic_score +<br/>(1-α) × lexical_score<br/><br/>α = 0.5 default"]
    end

    AlphaWeight --> Deduplicate[Remove Duplicates<br/>Same chunk_id]
    Deduplicate --> SortByScore[Sort by<br/>final_score DESC]
    SortByScore --> TopK[Select Top-K<br/>K = 10 default]

    TopK --> OptionalRerank{Rerank<br/>Enabled?}

    OptionalRerank -->|Yes| Rerank[Cohere Rerank API]
    OptionalRerank -->|No| FinalResults

    subgraph RerankingPhase["🎯 Reranking Phase"]
        Rerank --> CrossEncoder[Cross-Encoder Model<br/>Query-Document pairs]
        CrossEncoder --> RelScore[Relevance Scores<br/>0.0 - 1.0]
        RelScore --> RerankTop[Top-K Selection<br/>K = 5 typical]
    end

    RerankTop --> FinalResults
    FinalResults([Final Ranked Results])

    %% Add metadata example
    FinalResults --> MetadataBox["Example Result:<br/>────────────────<br/>Document: 'Attention is All You Need'<br/>Chunk ID: chunk_42<br/>Semantic Rank: 3 (score: 0.89)<br/>Lexical Rank: 7 (score: 12.4)<br/>RRF Score: 0.0234<br/>Rerank Score: 0.94<br/>Citations: [Vaswani et al., 2017]"]

    %% Styling
    classDef search fill:#E3F2FD,stroke:#1976D2,stroke-width:2px
    classDef algorithm fill:#FFF9C4,stroke:#F57C00,stroke-width:2px
    classDef result fill:#C8E6C9,stroke:#388E3C,stroke-width:2px

    class VectorSearch,FullText,HNSW,BM25Scoring search
    class CalcRRF,Formula,SemScore,LexScore,AlphaWeight algorithm
    class SemResults,LexResults,FinalResults result
```

## Algorithm Details

### Semantic Search (Qdrant)

**HNSW (Hierarchical Navigable Small World) Parameters**:
- `M = 16`: Number of connections per layer
- `EF_construct = 100`: Construction time parameter
- `EF_search = 64`: Search time parameter

**Cosine Similarity**:
```python
similarity(A, B) = (A · B) / (||A|| × ||B||)
```
Where:
- A = Query embedding (768-dim)
- B = Document embedding (768-dim)
- Range: [-1, 1], typically [0.5, 1.0] for relevant docs

### Lexical Search (Elasticsearch)

**BM25 Scoring Formula**:
```
score(D,Q) = Σ IDF(qi) × (f(qi,D) × (k1 + 1)) / (f(qi,D) + k1 × (1 - b + b × |D|/avgdl))
```
Where:
- `IDF(qi)` = Inverse document frequency of term qi
- `f(qi,D)` = Frequency of term qi in document D
- `k1 = 1.2` = Term frequency saturation parameter
- `b = 0.75` = Length normalization parameter
- `|D|` = Document length
- `avgdl` = Average document length

**Field Boosting**:
```json
{
  "title": 2.0,      // 2x importance
  "abstract": 1.5,   // 1.5x importance
  "body": 1.0        // baseline importance
}
```

### Reciprocal Rank Fusion (RRF)

**RRF Score Calculation**:
```python
def rrf_score(doc, semantic_rank, lexical_rank, k=60):
    """
    Calculate RRF score for a document.

    Args:
        doc: Document identifier
        semantic_rank: Position in semantic results (1-based)
        lexical_rank: Position in lexical results (1-based)
        k: Constant to prevent division by zero (default: 60)

    Returns:
        RRF score (higher is better)
    """
    semantic_score = 1.0 / (k + semantic_rank) if semantic_rank else 0
    lexical_score = 1.0 / (k + lexical_rank) if lexical_rank else 0

    return semantic_score + lexical_score
```

**Alpha Weighting** (Optional Enhancement):
```python
def weighted_rrf_score(doc, semantic_rank, lexical_rank, alpha=0.5, k=60):
    """
    Calculate weighted RRF score.

    Args:
        alpha: Weight for semantic search (0.0 - 1.0)
               0.0 = pure lexical, 1.0 = pure semantic, 0.5 = balanced
    """
    semantic_score = 1.0 / (k + semantic_rank) if semantic_rank else 0
    lexical_score = 1.0 / (k + lexical_rank) if lexical_rank else 0

    return alpha * semantic_score + (1 - alpha) * lexical_score
```

### Example Scenario

**Query**: "transformer architecture attention mechanism"

**Semantic Search Results** (Top 5):
1. "Attention is All You Need" (score: 0.92)
2. "BERT: Pre-training of Deep Bidirectional Transformers" (score: 0.89)
3. "GPT-3: Language Models are Few-Shot Learners" (score: 0.85)
4. "T5: Exploring Transfer Learning" (score: 0.82)
5. "XLNet: Generalized Autoregressive Pretraining" (score: 0.79)

**Lexical Search Results** (Top 5):
1. "Attention Mechanisms in Neural Networks" (BM25: 15.2)
2. "Attention is All You Need" (BM25: 14.8)
3. "Transformer-XL: Attentive Language Models" (BM25: 13.5)
4. "BERT: Pre-training of Deep Bidirectional Transformers" (BM25: 12.9)
5. "Multi-Head Attention in Transformers" (BM25: 11.7)

**RRF Scores** (k=60):

| Document | Sem Rank | Lex Rank | Sem Score | Lex Score | RRF Score | Final Rank |
|----------|----------|----------|-----------|-----------|-----------|------------|
| Attention is All You Need | 1 | 2 | 0.0164 | 0.0161 | 0.0325 | **1** |
| BERT | 2 | 4 | 0.0161 | 0.0156 | 0.0317 | **2** |
| Attention Mechanisms | - | 1 | 0.0000 | 0.0164 | 0.0164 | 3 |
| GPT-3 | 3 | - | 0.0159 | 0.0000 | 0.0159 | 4 |
| Transformer-XL | - | 3 | 0.0000 | 0.0159 | 0.0159 | 5 |

**Observations**:
- "Attention is All You Need" ranks #1 in both searches → Highest RRF score
- BERT ranks high in both (2nd semantic, 4th lexical) → 2nd overall
- Documents appearing in only one search get lower scores

### Reranking (Optional)

After RRF, **Cohere Rerank** can further refine results:

**Input**: Top 20 RRF results
**Output**: Top 5 reranked results

**Cross-Encoder Scoring**:
- Processes query-document pairs jointly
- More accurate than separate embeddings
- Computationally expensive (use for top-K only)
- Output: Relevance score 0.0 - 1.0

**Benefits**:
- 15-25% improvement in NDCG@5
- Better handling of semantic nuances
- Filters out false positives from initial retrieval

### Configuration Parameters

```yaml
hybrid_search:
  # RRF parameters
  rrf_k: 60                    # RRF constant
  alpha: 0.5                   # Semantic/lexical balance (0.0-1.0)

  # Retrieval parameters
  semantic_top_k: 20           # Semantic search candidates
  lexical_top_k: 20            # Lexical search candidates
  final_top_k: 10              # Final results after fusion

  # Reranking
  rerank_enabled: true         # Enable Cohere reranking
  rerank_top_k: 5              # Final reranked results
  rerank_candidates: 20        # Candidates for reranking

  # Elasticsearch BM25
  bm25_k1: 1.2                 # Term frequency saturation
  bm25_b: 0.75                 # Length normalization

  # Field boosting
  title_boost: 2.0
  abstract_boost: 1.5
  body_boost: 1.0

  # Qdrant HNSW
  hnsw_m: 16                   # Connections per layer
  hnsw_ef_construct: 100       # Construction parameter
  hnsw_ef_search: 64           # Search parameter
```
