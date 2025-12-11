# Evaluation Guide

This guide covers the evaluation framework for the Hybrid Search RAG system, including metrics, datasets, and best practices.

## Table of Contents

- [Overview](#overview)
- [Evaluation Metrics](#evaluation-metrics)
- [Synthetic Dataset Generation](#synthetic-dataset-generation)
- [Running Evaluations](#running-evaluations)
- [Interpreting Results](#interpreting-results)
- [Best Practices](#best-practices)

## Overview

The evaluation framework consists of three main components:

1. **Synthetic Dataset Generation**: Create evaluation datasets with diverse queries
2. **Retrieval Evaluation**: Measure search quality with MRR, Recall@K, NDCG
3. **Generation Evaluation**: Assess answer quality, citations, and performance

## Evaluation Metrics

### Retrieval Metrics

#### Mean Reciprocal Rank (MRR)

**Definition**: Average of reciprocal ranks of the first relevant document.

**Formula**:
```
MRR = (1/|Q|) * Σ (1/rank_i)
```

**Range**: 0 to 1 (higher is better)

**Interpretation**:
- MRR = 1.0: All first results are relevant
- MRR = 0.5: First relevant document at rank 2 on average
- MRR = 0.33: First relevant document at rank 3 on average

**Target**: MRR > 0.7 for production

#### Recall@K

**Definition**: Proportion of relevant documents retrieved in top K results.

**Formula**:
```
Recall@K = |relevant ∩ retrieved[:K]| / |relevant|
```

**Range**: 0 to 1 (higher is better)

**Interpretation**:
- Recall@10 = 0.8: 80% of relevant documents in top 10
- Recall@10 = 0.5: 50% of relevant documents in top 10

**Targets**:
- Recall@5 > 0.6
- Recall@10 > 0.8
- Recall@20 > 0.9

#### Precision@K

**Definition**: Proportion of retrieved documents that are relevant in top K.

**Formula**:
```
Precision@K = |relevant ∩ retrieved[:K]| / K
```

**Range**: 0 to 1 (higher is better)

**Interpretation**:
- Precision@10 = 0.8: 8 out of 10 results are relevant
- Precision@10 = 0.5: 5 out of 10 results are relevant

**Targets**:
- Precision@5 > 0.7
- Precision@10 > 0.6

#### Normalized Discounted Cumulative Gain (NDCG@K)

**Definition**: Measures ranking quality with graded relevance scores.

**Formula**:
```
DCG@K = Σ (rel_i / log2(i + 1))
NDCG@K = DCG@K / IDCG@K
```

**Range**: 0 to 1 (higher is better)

**Interpretation**:
- NDCG@10 = 1.0: Perfect ranking
- NDCG@10 = 0.8: Good ranking with minor issues
- NDCG@10 = 0.6: Moderate ranking quality

**Targets**:
- NDCG@10 > 0.75
- NDCG@20 > 0.80

#### Mean Average Precision (MAP)

**Definition**: Average of precision values at each relevant document position.

**Formula**:
```
AP = (1/|relevant|) * Σ (Precision@k * rel_k)
MAP = (1/|Q|) * Σ AP_i
```

**Range**: 0 to 1 (higher is better)

**Target**: MAP > 0.7

### Generation Metrics

#### Answer Length

**Metric**: Average number of characters in generated answers

**Target Range**: 200-800 characters
- Too short (<100): Likely incomplete
- Too long (>1000): May contain unnecessary detail

#### Citation Count

**Metric**: Average number of citations per answer

**Target Range**: 2-5 citations
- Too few (<2): Insufficient support
- Too many (>8): May be over-citing

#### Validation Pass Rate

**Metric**: Percentage of answers passing validation checks

**Validation Checks**:
- Minimum length (50 characters)
- Contains citations
- No error markers
- Coherent structure

**Target**: >95% validation pass rate

#### Generation Latency

**Metrics**: p50, p95, p99 latencies in milliseconds

**Targets**:
- p50 < 2000ms
- p95 < 3500ms
- p99 < 5000ms

#### Token Efficiency

**Metric**: Average tokens per query (input + output)

**Target Range**: 3000-7000 tokens
- Monitor to control costs
- Optimize context selection if consistently high

#### Fallback Rate

**Metric**: Percentage of queries using fallback model (OpenAI)

**Target**: <10% fallback rate
- High rate indicates issues with primary model (Claude)
- Check API key, rate limits, model availability

## Synthetic Dataset Generation

### Generating a Dataset

```bash
# Generate 100 queries with default distribution
python scripts/generate_eval_dataset.py \
  --num-queries 100 \
  --output evaluation_dataset.json

# Generate with ground truth answers
python scripts/generate_eval_dataset.py \
  --num-queries 50 \
  --include-ground-truth \
  --output evaluation_dataset_with_gt.json

# Custom query type distribution
python scripts/generate_eval_dataset.py \
  --num-queries 100 \
  --methodological 0.3 \
  --results 0.2 \
  --comparative 0.2 \
  --definition 0.1 \
  --general 0.2 \
  --output custom_dataset.json

# Custom difficulty distribution
python scripts/generate_eval_dataset.py \
  --num-queries 100 \
  --easy 0.2 \
  --medium 0.5 \
  --hard 0.3 \
  --output difficult_dataset.json
```

### Dataset Structure

```json
{
  "metadata": {
    "num_queries": 100,
    "query_types": {
      "methodological": 25,
      "results": 20,
      "comparative": 20,
      "definition": 15,
      "general": 20
    },
    "difficulty_levels": {
      "easy": 30,
      "medium": 50,
      "hard": 20
    },
    "has_ground_truth": false
  },
  "queries": [
    {
      "id": "query_1",
      "query": "How does BERT work?",
      "query_type": "methodological",
      "topics": ["BERT"],
      "difficulty": "medium",
      "template": "How does {topic} work?",
      "relevant_docs": ["doc_How_does_BERT_work?_0", "doc_How_does_BERT_work?_1", ...],
      "relevance_scores": {
        "doc_How_does_BERT_work?_0": 3,
        "doc_How_does_BERT_work?_1": 3,
        "doc_How_does_BERT_work?_2": 2
      },
      "num_relevant": 5,
      "ground_truth_answer": "BERT (Bidirectional Encoder Representations from Transformers) is..."
    }
  ]
}
```

### Query Types

1. **Methodological** (25%): "How does X work?", "What is the architecture of X?"
2. **Results** (20%): "What results has X achieved?", "What is the performance of X?"
3. **Comparative** (20%): "What is the difference between X and Y?", "Compare X and Y"
4. **Definition** (15%): "What is X?", "Define X"
5. **General** (20%): "Tell me about X", "Provide information on X"

### Difficulty Levels

- **Easy** (30%): Common topics, clear queries
- **Medium** (50%): Standard academic queries
- **Hard** (20%): Complex or ambiguous queries

## Running Evaluations

### Full System Evaluation

```bash
# Evaluate on dataset
python scripts/run_evaluation.py \
  --dataset evaluation_dataset.json \
  --output results.json

# Enable experiment tracking
python scripts/run_evaluation.py \
  --dataset evaluation_dataset.json \
  --enable-comet \
  --experiment-name production-eval-v1 \
  --output results.json

# Single query test
python scripts/run_evaluation.py \
  --query "How does BERT work?" \
  --output single_result.json
```

### Search-Only Evaluation

Use the Jupyter notebook for detailed search analysis:

```bash
# Start Jupyter
jupyter notebook notebooks/search_evaluation.ipynb
```

The notebook provides:
- Comparison of search methods (semantic, lexical, hybrid)
- Latency analysis
- Query type performance analysis
- Visualization of results

### Evaluation Output

```json
{
  "timestamp": 1705320000.0,
  "aggregate_metrics": {
    "total_queries": 100,
    "successful_queries": 98,
    "failed_queries": 2,
    "success_rate": 98.0,
    "avg_total_time_ms": 2450.5,
    "avg_search_time_ms": 175.2,
    "avg_generation_time_ms": 2250.3,
    "avg_answer_length": 542.3,
    "avg_num_citations": 3.2,
    "avg_total_tokens": 5234.1,
    "fallback_rate": 6.1,
    "validation_pass_rate": 96.9,
    "avg_mrr": 0.78,
    "avg_recall_at_5": 0.65,
    "avg_recall_at_10": 0.82,
    "p50_time_ms": 2100.0,
    "p95_time_ms": 3800.0,
    "p99_time_ms": 4500.0
  },
  "individual_results": [...]
}
```

## Interpreting Results

### Good Performance Profile

```
✓ MRR > 0.7
✓ Recall@10 > 0.8
✓ NDCG@10 > 0.75
✓ Validation Pass Rate > 95%
✓ p95 Latency < 3500ms
✓ Fallback Rate < 10%
```

### Performance Issues and Solutions

#### Low MRR (<0.6)

**Problem**: First relevant document is ranked low

**Solutions**:
- Review query expansion strategy
- Adjust fusion weights (favor better performing method)
- Improve embedding model
- Enable reranking if not already active

#### Low Recall@10 (<0.7)

**Problem**: Missing relevant documents in top 10

**Solutions**:
- Increase retrieval limit before reranking
- Review chunking strategy (may be too large/small)
- Check index coverage (are all documents indexed?)
- Adjust BM25 parameters for lexical search

#### Low NDCG@10 (<0.7)

**Problem**: Relevant documents not well-ranked

**Solutions**:
- Enable or improve reranking
- Adjust RRF fusion parameters
- Review scoring normalization
- Consider learning-to-rank approaches

#### High Fallback Rate (>15%)

**Problem**: Frequent failures with primary model

**Causes**:
- API rate limits
- Invalid API key
- Network issues
- Model availability

**Solutions**:
- Check Claude API status
- Verify API key validity
- Implement exponential backoff
- Consider upgrading API tier

#### High p95 Latency (>4000ms)

**Problem**: Slow queries affecting user experience

**Solutions**:
- Enable Redis caching
- Reduce max_chunks for generation
- Implement connection pooling
- Consider async processing for slow queries
- Review reranking performance

#### Low Validation Pass Rate (<90%)

**Problem**: Generated answers failing quality checks

**Causes**:
- Prompts not effective
- Insufficient context
- Model issues

**Solutions**:
- Review and refine prompts
- Increase context chunks
- Add explicit citation instructions
- Review failed examples manually

## Best Practices

### Regular Evaluation

1. **Baseline Evaluation**: Run after major changes
2. **Regression Testing**: Weekly automated evaluation
3. **A/B Testing**: Compare new features against baseline

### Metrics to Monitor

**Priority 1 (Critical)**:
- MRR
- Recall@10
- p95 Latency
- Validation Pass Rate

**Priority 2 (Important)**:
- NDCG@10
- Fallback Rate
- Token Usage
- Cache Hit Rate

**Priority 3 (Nice to Have)**:
- MAP
- Precision@10
- Answer Length
- Citation Count

### Dataset Maintenance

1. **Diversity**: Ensure queries cover all topics and types
2. **Difficulty**: Include easy, medium, and hard queries
3. **Relevance**: Periodically review relevance judgments
4. **Growth**: Add new queries as system evolves
5. **Real Queries**: Supplement synthetic data with real user queries

### Evaluation Frequency

- **Development**: After each significant change
- **Staging**: Daily automated evaluation
- **Production**: Weekly comprehensive evaluation
- **Continuous**: Track live metrics via CloudWatch

### Experiment Tracking

Always track experiments with Comet ML:

```python
from src.utils.comet_tracking import CometExperimentTracker

tracker = CometExperimentTracker(
    api_key=settings.comet_api_key,
    enabled=True
)

tracker.start_experiment(
    experiment_name="eval-2025-01-15",
    tags=["evaluation", "production", "hybrid-search"]
)

# Log evaluation metrics
tracker.log_evaluation_metrics(
    mrr_at_10=0.78,
    recall_at_5=0.65,
    recall_at_10=0.82,
    ndcg=0.75,
    avg_answer_quality=0.85,
    num_queries=100
)

tracker.end_experiment()
```

### Visualization

Use the provided notebook for rich visualizations:
- Metric comparisons across methods
- Latency distributions
- Performance by query type
- Difficulty analysis

Export charts for reports and presentations.

## Troubleshooting

### Evaluation Script Fails

**Error**: `Failed to initialize search engine`

**Solution**: Check that Qdrant and Elasticsearch are running

```bash
docker-compose ps
```

### Low Coverage

**Problem**: Many queries return 0 results

**Solutions**:
- Verify index is populated
- Check query preprocessing
- Review embedding model initialization

### Inconsistent Results

**Problem**: Metrics vary significantly between runs

**Solutions**:
- Increase dataset size (>50 queries minimum)
- Fix random seeds for reproducibility
- Check for API rate limiting
- Review caching behavior

## Next Steps

- [Performance Optimization](OPTIMIZATION.md)
- [Deployment Guide](DEPLOYMENT.md)
- [API Documentation](API.md)

## Contact

For questions about evaluation:
- GitHub Issues: https://github.com/yourusername/hybrid-search-rag/issues
- Email: support@yourcompany.com
