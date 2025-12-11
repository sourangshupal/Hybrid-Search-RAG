"""Tests for evaluation metrics."""

import pytest
import numpy as np

from src.evaluation.metrics import (
    EvaluationMetricsCalculator,
    RetrievalMetrics,
    GenerationMetrics,
    evaluate_retrieval_quality,
    evaluate_generation_quality
)


class TestEvaluationMetricsCalculator:
    """Tests for EvaluationMetricsCalculator."""

    def test_calculate_mrr_first_position(self):
        """Test MRR when relevant doc is first."""
        calculator = EvaluationMetricsCalculator()

        retrieved = ["doc1", "doc2", "doc3"]
        relevant = ["doc1"]

        mrr = calculator.calculate_mrr(retrieved, relevant)
        assert mrr == 1.0

    def test_calculate_mrr_second_position(self):
        """Test MRR when relevant doc is second."""
        calculator = EvaluationMetricsCalculator()

        retrieved = ["doc1", "doc2", "doc3"]
        relevant = ["doc2"]

        mrr = calculator.calculate_mrr(retrieved, relevant)
        assert mrr == 0.5

    def test_calculate_mrr_third_position(self):
        """Test MRR when relevant doc is third."""
        calculator = EvaluationMetricsCalculator()

        retrieved = ["doc1", "doc2", "doc3"]
        relevant = ["doc3"]

        mrr = calculator.calculate_mrr(retrieved, relevant)
        assert mrr == pytest.approx(0.333, rel=0.01)

    def test_calculate_mrr_no_relevant(self):
        """Test MRR when no relevant docs retrieved."""
        calculator = EvaluationMetricsCalculator()

        retrieved = ["doc1", "doc2", "doc3"]
        relevant = ["doc4"]

        mrr = calculator.calculate_mrr(retrieved, relevant)
        assert mrr == 0.0

    def test_calculate_recall_at_k_perfect(self):
        """Test Recall@K with perfect retrieval."""
        calculator = EvaluationMetricsCalculator()

        retrieved = ["doc1", "doc2", "doc3", "doc4", "doc5"]
        relevant = ["doc1", "doc2"]

        recall = calculator.calculate_recall_at_k(retrieved, relevant, k=5)
        assert recall == 1.0

    def test_calculate_recall_at_k_partial(self):
        """Test Recall@K with partial retrieval."""
        calculator = EvaluationMetricsCalculator()

        retrieved = ["doc1", "doc2", "doc3", "doc4", "doc5"]
        relevant = ["doc1", "doc2", "doc6", "doc7"]

        recall = calculator.calculate_recall_at_k(retrieved, relevant, k=5)
        assert recall == 0.5  # 2 out of 4 relevant docs retrieved

    def test_calculate_recall_at_k_zero(self):
        """Test Recall@K with no relevant docs."""
        calculator = EvaluationMetricsCalculator()

        retrieved = ["doc1", "doc2", "doc3"]
        relevant = ["doc4", "doc5"]

        recall = calculator.calculate_recall_at_k(retrieved, relevant, k=3)
        assert recall == 0.0

    def test_calculate_precision_at_k_perfect(self):
        """Test Precision@K with perfect precision."""
        calculator = EvaluationMetricsCalculator()

        retrieved = ["doc1", "doc2", "doc3", "doc4", "doc5"]
        relevant = ["doc1", "doc2", "doc3", "doc4", "doc5"]

        precision = calculator.calculate_precision_at_k(retrieved, relevant, k=5)
        assert precision == 1.0

    def test_calculate_precision_at_k_partial(self):
        """Test Precision@K with partial precision."""
        calculator = EvaluationMetricsCalculator()

        retrieved = ["doc1", "doc2", "doc3", "doc4", "doc5"]
        relevant = ["doc1", "doc2"]

        precision = calculator.calculate_precision_at_k(retrieved, relevant, k=5)
        assert precision == 0.4  # 2 out of 5 retrieved docs are relevant

    def test_calculate_precision_at_k_zero(self):
        """Test Precision@K with no relevant docs."""
        calculator = EvaluationMetricsCalculator()

        retrieved = ["doc1", "doc2", "doc3"]
        relevant = ["doc4", "doc5"]

        precision = calculator.calculate_precision_at_k(retrieved, relevant, k=3)
        assert precision == 0.0

    def test_calculate_average_precision_perfect(self):
        """Test Average Precision with perfect ranking."""
        calculator = EvaluationMetricsCalculator()

        retrieved = ["doc1", "doc2", "doc3", "doc4", "doc5"]
        relevant = ["doc1", "doc2", "doc3"]

        ap = calculator.calculate_average_precision(retrieved, relevant)
        # AP = (1/1 + 2/2 + 3/3) / 3 = 3/3 = 1.0
        assert ap == 1.0

    def test_calculate_average_precision_partial(self):
        """Test Average Precision with partial ranking."""
        calculator = EvaluationMetricsCalculator()

        retrieved = ["doc1", "doc2", "doc3", "doc4", "doc5"]
        relevant = ["doc2", "doc4"]

        ap = calculator.calculate_average_precision(retrieved, relevant)
        # AP = (1/2 + 2/4) / 2 = (0.5 + 0.5) / 2 = 0.5
        assert ap == 0.5

    def test_calculate_average_precision_no_relevant(self):
        """Test Average Precision with no relevant docs."""
        calculator = EvaluationMetricsCalculator()

        retrieved = ["doc1", "doc2", "doc3"]
        relevant = ["doc4", "doc5"]

        ap = calculator.calculate_average_precision(retrieved, relevant)
        assert ap == 0.0

    def test_calculate_ndcg_at_k_perfect(self):
        """Test NDCG@K with perfect ranking."""
        calculator = EvaluationMetricsCalculator()

        retrieved = ["doc1", "doc2", "doc3"]
        relevant = ["doc1", "doc2", "doc3"]
        relevance_scores = {"doc1": 3, "doc2": 2, "doc3": 1}

        ndcg = calculator.calculate_ndcg_at_k(retrieved, relevant, relevance_scores, k=3)
        assert ndcg == 1.0

    def test_calculate_ndcg_at_k_imperfect(self):
        """Test NDCG@K with imperfect ranking."""
        calculator = EvaluationMetricsCalculator()

        retrieved = ["doc2", "doc1", "doc3"]  # Wrong order
        relevant = ["doc1", "doc2", "doc3"]
        relevance_scores = {"doc1": 3, "doc2": 2, "doc3": 1}

        ndcg = calculator.calculate_ndcg_at_k(retrieved, relevant, relevance_scores, k=3)
        assert 0.0 < ndcg < 1.0  # Should be less than perfect

    def test_calculate_ndcg_at_k_binary_relevance(self):
        """Test NDCG@K with binary relevance (no scores provided)."""
        calculator = EvaluationMetricsCalculator()

        retrieved = ["doc1", "doc2", "doc3"]
        relevant = ["doc1", "doc2"]

        ndcg = calculator.calculate_ndcg_at_k(retrieved, relevant, k=3)
        assert 0.0 < ndcg <= 1.0

    def test_calculate_retrieval_metrics_batch(self):
        """Test batch retrieval metrics calculation."""
        calculator = EvaluationMetricsCalculator()

        results = [
            {
                "retrieved_docs": ["doc1", "doc2", "doc3"],
                "relevant_docs": ["doc1", "doc2"]
            },
            {
                "retrieved_docs": ["doc4", "doc5", "doc6"],
                "relevant_docs": ["doc4"]
            }
        ]

        metrics = calculator.calculate_retrieval_metrics_batch(results)

        assert isinstance(metrics, RetrievalMetrics)
        assert metrics.num_queries == 2
        assert 0.0 <= metrics.mrr <= 1.0
        assert 0.0 <= metrics.recall_at_10 <= 1.0
        assert 0.0 <= metrics.ndcg_at_10 <= 1.0

    def test_calculate_generation_metrics_batch(self):
        """Test batch generation metrics calculation."""
        calculator = EvaluationMetricsCalculator()

        results = [
            {
                "answer": "This is a test answer with citations [Author 2023].",
                "num_citations": 1,
                "validated": True,
                "generation_time_ms": 2000.0,
                "total_tokens": 500,
                "fallback_used": False
            },
            {
                "answer": "Another answer with multiple citations [Author1 2022] [Author2 2023].",
                "num_citations": 2,
                "validated": True,
                "generation_time_ms": 2500.0,
                "total_tokens": 600,
                "fallback_used": True
            }
        ]

        metrics = calculator.calculate_generation_metrics_batch(results)

        assert isinstance(metrics, GenerationMetrics)
        assert metrics.num_queries == 2
        assert metrics.avg_answer_length > 0
        assert metrics.avg_num_citations > 0
        assert 0.0 <= metrics.validation_pass_rate <= 1.0
        assert 0.0 <= metrics.fallback_rate <= 1.0

    def test_calculate_latency_percentiles(self):
        """Test latency percentile calculation."""
        calculator = EvaluationMetricsCalculator()

        latencies = [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]

        percentiles = calculator.calculate_latency_percentiles(latencies)

        assert "p50" in percentiles
        assert "p90" in percentiles
        assert "p95" in percentiles
        assert "p99" in percentiles
        assert percentiles["p50"] < percentiles["p95"] < percentiles["p99"]

    def test_calculate_latency_percentiles_empty(self):
        """Test latency percentiles with empty list."""
        calculator = EvaluationMetricsCalculator()

        percentiles = calculator.calculate_latency_percentiles([])

        assert all(v == 0.0 for v in percentiles.values())


class TestRetrievalMetrics:
    """Tests for RetrievalMetrics dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        metrics = RetrievalMetrics(
            mrr=0.75,
            map_score=0.70,
            recall_at_5=0.60,
            recall_at_10=0.80,
            recall_at_20=0.90,
            precision_at_5=0.70,
            precision_at_10=0.65,
            precision_at_20=0.55,
            ndcg_at_10=0.75,
            ndcg_at_20=0.80,
            num_queries=100
        )

        result = metrics.to_dict()

        assert isinstance(result, dict)
        assert result["mrr"] == 0.75
        assert result["recall@10"] == 0.8
        assert result["ndcg@10"] == 0.75
        assert result["num_queries"] == 100


class TestGenerationMetrics:
    """Tests for GenerationMetrics dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        metrics = GenerationMetrics(
            avg_answer_length=500.5,
            avg_num_citations=3,
            validation_pass_rate=0.95,
            avg_generation_time_ms=2250.5,
            avg_tokens=5500.0,
            fallback_rate=0.05,
            num_queries=100
        )

        result = metrics.to_dict()

        assert isinstance(result, dict)
        assert result["avg_answer_length"] == 500.5
        assert result["avg_num_citations"] == 3
        assert result["validation_pass_rate"] == 0.95
        assert result["num_queries"] == 100


class TestEvaluationFunctions:
    """Tests for top-level evaluation functions."""

    def test_evaluate_retrieval_quality(self):
        """Test retrieval quality evaluation."""
        search_results = [
            {
                "query": "test query 1",
                "results": [
                    {"id": "doc1"},
                    {"id": "doc2"},
                    {"id": "doc3"}
                ]
            },
            {
                "query": "test query 2",
                "results": [
                    {"id": "doc4"},
                    {"id": "doc5"}
                ]
            }
        ]

        ground_truth = [
            {
                "query": "test query 1",
                "relevant_docs": ["doc1", "doc2"]
            },
            {
                "query": "test query 2",
                "relevant_docs": ["doc4"]
            }
        ]

        result = evaluate_retrieval_quality(search_results, ground_truth)

        assert "retrieval_metrics" in result
        assert "num_evaluated" in result
        assert result["num_evaluated"] == 2

    def test_evaluate_generation_quality(self):
        """Test generation quality evaluation."""
        generation_results = [
            {
                "answer": "Test answer 1",
                "num_citations": 2,
                "validated": True,
                "generation_time_ms": 2000.0,
                "total_tokens": 500,
                "fallback_used": False
            },
            {
                "answer": "Test answer 2",
                "num_citations": 3,
                "validated": True,
                "generation_time_ms": 2500.0,
                "total_tokens": 600,
                "fallback_used": False
            }
        ]

        result = evaluate_generation_quality(generation_results)

        assert "generation_metrics" in result
        assert "latency_percentiles" in result
        assert "num_evaluated" in result
        assert result["num_evaluated"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
