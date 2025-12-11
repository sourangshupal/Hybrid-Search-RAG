"""Evaluation metrics for retrieval and generation quality."""

import math
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from dataclasses import dataclass

from loguru import logger


@dataclass
class RetrievalMetrics:
    """Container for retrieval evaluation metrics."""

    mrr: float  # Mean Reciprocal Rank
    map_score: float  # Mean Average Precision
    recall_at_5: float
    recall_at_10: float
    recall_at_20: float
    precision_at_5: float
    precision_at_10: float
    precision_at_20: float
    ndcg_at_10: float  # Normalized Discounted Cumulative Gain
    ndcg_at_20: float
    num_queries: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "mrr": round(self.mrr, 4),
            "map": round(self.map_score, 4),
            "recall@5": round(self.recall_at_5, 4),
            "recall@10": round(self.recall_at_10, 4),
            "recall@20": round(self.recall_at_20, 4),
            "precision@5": round(self.precision_at_5, 4),
            "precision@10": round(self.precision_at_10, 4),
            "precision@20": round(self.precision_at_20, 4),
            "ndcg@10": round(self.ndcg_at_10, 4),
            "ndcg@20": round(self.ndcg_at_20, 4),
            "num_queries": self.num_queries
        }


@dataclass
class GenerationMetrics:
    """Container for generation quality metrics."""

    avg_answer_length: float
    avg_num_citations: int
    validation_pass_rate: float
    avg_generation_time_ms: float
    avg_tokens: float
    fallback_rate: float
    num_queries: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "avg_answer_length": round(self.avg_answer_length, 2),
            "avg_num_citations": self.avg_num_citations,
            "validation_pass_rate": round(self.validation_pass_rate, 4),
            "avg_generation_time_ms": round(self.avg_generation_time_ms, 2),
            "avg_tokens": round(self.avg_tokens, 2),
            "fallback_rate": round(self.fallback_rate, 4),
            "num_queries": self.num_queries
        }


class EvaluationMetricsCalculator:
    """Calculator for evaluation metrics."""

    @staticmethod
    def calculate_mrr(
        retrieved_docs: List[str],
        relevant_docs: List[str]
    ) -> float:
        """
        Calculate Mean Reciprocal Rank.

        Args:
            retrieved_docs: List of retrieved document IDs (ordered by rank)
            relevant_docs: List of relevant document IDs

        Returns:
            MRR score (0 to 1)
        """
        relevant_set = set(relevant_docs)

        for rank, doc_id in enumerate(retrieved_docs, start=1):
            if doc_id in relevant_set:
                return 1.0 / rank

        return 0.0

    @staticmethod
    def calculate_recall_at_k(
        retrieved_docs: List[str],
        relevant_docs: List[str],
        k: int
    ) -> float:
        """
        Calculate Recall@K.

        Args:
            retrieved_docs: List of retrieved document IDs
            relevant_docs: List of relevant document IDs
            k: Cutoff rank

        Returns:
            Recall@K score (0 to 1)
        """
        if not relevant_docs:
            return 0.0

        retrieved_at_k = set(retrieved_docs[:k])
        relevant_set = set(relevant_docs)

        num_relevant_retrieved = len(retrieved_at_k & relevant_set)
        return num_relevant_retrieved / len(relevant_set)

    @staticmethod
    def calculate_precision_at_k(
        retrieved_docs: List[str],
        relevant_docs: List[str],
        k: int
    ) -> float:
        """
        Calculate Precision@K.

        Args:
            retrieved_docs: List of retrieved document IDs
            relevant_docs: List of relevant document IDs
            k: Cutoff rank

        Returns:
            Precision@K score (0 to 1)
        """
        if k == 0:
            return 0.0

        retrieved_at_k = set(retrieved_docs[:k])
        relevant_set = set(relevant_docs)

        num_relevant_retrieved = len(retrieved_at_k & relevant_set)
        return num_relevant_retrieved / k

    @staticmethod
    def calculate_average_precision(
        retrieved_docs: List[str],
        relevant_docs: List[str]
    ) -> float:
        """
        Calculate Average Precision.

        Args:
            retrieved_docs: List of retrieved document IDs
            relevant_docs: List of relevant document IDs

        Returns:
            Average Precision score (0 to 1)
        """
        if not relevant_docs:
            return 0.0

        relevant_set = set(relevant_docs)
        num_relevant = 0
        sum_precisions = 0.0

        for rank, doc_id in enumerate(retrieved_docs, start=1):
            if doc_id in relevant_set:
                num_relevant += 1
                precision_at_rank = num_relevant / rank
                sum_precisions += precision_at_rank

        if num_relevant == 0:
            return 0.0

        return sum_precisions / len(relevant_set)

    @staticmethod
    def calculate_ndcg_at_k(
        retrieved_docs: List[str],
        relevant_docs: List[str],
        relevance_scores: Optional[Dict[str, int]] = None,
        k: int = 10
    ) -> float:
        """
        Calculate Normalized Discounted Cumulative Gain at K.

        Args:
            retrieved_docs: List of retrieved document IDs (ordered by rank)
            relevant_docs: List of relevant document IDs
            relevance_scores: Optional dict mapping doc_id to relevance score (1-3)
            k: Cutoff rank

        Returns:
            NDCG@K score (0 to 1)
        """
        if not relevant_docs:
            return 0.0

        # Default relevance scores (binary)
        if relevance_scores is None:
            relevance_scores = {doc_id: 1 for doc_id in relevant_docs}

        # Calculate DCG
        dcg = 0.0
        for rank, doc_id in enumerate(retrieved_docs[:k], start=1):
            relevance = relevance_scores.get(doc_id, 0)
            # DCG formula: rel_i / log2(i + 1)
            dcg += relevance / math.log2(rank + 1)

        # Calculate IDCG (ideal DCG)
        # Sort relevant docs by relevance score (descending)
        sorted_relevant = sorted(
            relevant_docs,
            key=lambda doc_id: relevance_scores.get(doc_id, 0),
            reverse=True
        )

        idcg = 0.0
        for rank, doc_id in enumerate(sorted_relevant[:k], start=1):
            relevance = relevance_scores.get(doc_id, 0)
            idcg += relevance / math.log2(rank + 1)

        # NDCG = DCG / IDCG
        if idcg == 0:
            return 0.0

        return dcg / idcg

    @staticmethod
    def calculate_retrieval_metrics_batch(
        results: List[Dict[str, Any]]
    ) -> RetrievalMetrics:
        """
        Calculate retrieval metrics for batch of queries.

        Args:
            results: List of result dictionaries with keys:
                - retrieved_docs: List[str]
                - relevant_docs: List[str]
                - relevance_scores: Optional[Dict[str, int]]

        Returns:
            RetrievalMetrics object with aggregated metrics
        """
        calculator = EvaluationMetricsCalculator()

        mrr_scores = []
        map_scores = []
        recall_5_scores = []
        recall_10_scores = []
        recall_20_scores = []
        precision_5_scores = []
        precision_10_scores = []
        precision_20_scores = []
        ndcg_10_scores = []
        ndcg_20_scores = []

        for result in results:
            retrieved = result.get("retrieved_docs", [])
            relevant = result.get("relevant_docs", [])
            relevance_scores = result.get("relevance_scores")

            if not retrieved or not relevant:
                continue

            # MRR
            mrr_scores.append(calculator.calculate_mrr(retrieved, relevant))

            # MAP
            map_scores.append(calculator.calculate_average_precision(retrieved, relevant))

            # Recall@K
            recall_5_scores.append(calculator.calculate_recall_at_k(retrieved, relevant, 5))
            recall_10_scores.append(calculator.calculate_recall_at_k(retrieved, relevant, 10))
            recall_20_scores.append(calculator.calculate_recall_at_k(retrieved, relevant, 20))

            # Precision@K
            precision_5_scores.append(calculator.calculate_precision_at_k(retrieved, relevant, 5))
            precision_10_scores.append(calculator.calculate_precision_at_k(retrieved, relevant, 10))
            precision_20_scores.append(calculator.calculate_precision_at_k(retrieved, relevant, 20))

            # NDCG@K
            ndcg_10_scores.append(calculator.calculate_ndcg_at_k(retrieved, relevant, relevance_scores, 10))
            ndcg_20_scores.append(calculator.calculate_ndcg_at_k(retrieved, relevant, relevance_scores, 20))

        # Calculate averages
        return RetrievalMetrics(
            mrr=np.mean(mrr_scores) if mrr_scores else 0.0,
            map_score=np.mean(map_scores) if map_scores else 0.0,
            recall_at_5=np.mean(recall_5_scores) if recall_5_scores else 0.0,
            recall_at_10=np.mean(recall_10_scores) if recall_10_scores else 0.0,
            recall_at_20=np.mean(recall_20_scores) if recall_20_scores else 0.0,
            precision_at_5=np.mean(precision_5_scores) if precision_5_scores else 0.0,
            precision_at_10=np.mean(precision_10_scores) if precision_10_scores else 0.0,
            precision_at_20=np.mean(precision_20_scores) if precision_20_scores else 0.0,
            ndcg_at_10=np.mean(ndcg_10_scores) if ndcg_10_scores else 0.0,
            ndcg_at_20=np.mean(ndcg_20_scores) if ndcg_20_scores else 0.0,
            num_queries=len(results)
        )

    @staticmethod
    def calculate_generation_metrics_batch(
        results: List[Dict[str, Any]]
    ) -> GenerationMetrics:
        """
        Calculate generation metrics for batch of queries.

        Args:
            results: List of result dictionaries with keys:
                - answer: str
                - num_citations: int
                - validated: bool
                - generation_time_ms: float
                - total_tokens: int
                - fallback_used: bool

        Returns:
            GenerationMetrics object with aggregated metrics
        """
        answer_lengths = []
        num_citations_list = []
        validated_list = []
        generation_times = []
        tokens_list = []
        fallback_list = []

        for result in results:
            if "answer" in result:
                answer_lengths.append(len(result["answer"]))

            if "num_citations" in result:
                num_citations_list.append(result["num_citations"])

            if "validated" in result:
                validated_list.append(1 if result["validated"] else 0)

            if "generation_time_ms" in result:
                generation_times.append(result["generation_time_ms"])

            if "total_tokens" in result:
                tokens_list.append(result["total_tokens"])

            if "fallback_used" in result:
                fallback_list.append(1 if result["fallback_used"] else 0)

        return GenerationMetrics(
            avg_answer_length=np.mean(answer_lengths) if answer_lengths else 0.0,
            avg_num_citations=int(np.mean(num_citations_list)) if num_citations_list else 0,
            validation_pass_rate=np.mean(validated_list) if validated_list else 0.0,
            avg_generation_time_ms=np.mean(generation_times) if generation_times else 0.0,
            avg_tokens=np.mean(tokens_list) if tokens_list else 0.0,
            fallback_rate=np.mean(fallback_list) if fallback_list else 0.0,
            num_queries=len(results)
        )

    @staticmethod
    def calculate_latency_percentiles(
        latencies: List[float],
        percentiles: List[int] = [50, 90, 95, 99]
    ) -> Dict[str, float]:
        """
        Calculate latency percentiles.

        Args:
            latencies: List of latency values in milliseconds
            percentiles: List of percentiles to calculate

        Returns:
            Dictionary mapping percentile to value
        """
        if not latencies:
            return {f"p{p}": 0.0 for p in percentiles}

        result = {}
        for p in percentiles:
            value = np.percentile(latencies, p)
            result[f"p{p}"] = round(value, 2)

        return result


def evaluate_retrieval_quality(
    search_results: List[Dict[str, Any]],
    ground_truth: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Evaluate retrieval quality against ground truth.

    Args:
        search_results: List of search result dicts with 'query' and 'results' keys
        ground_truth: List of ground truth dicts with 'query' and 'relevant_docs' keys

    Returns:
        Dictionary with evaluation metrics
    """
    calculator = EvaluationMetricsCalculator()

    # Match results with ground truth
    matched_results = []
    for search_result in search_results:
        query = search_result.get("query")

        # Find matching ground truth
        gt = next((g for g in ground_truth if g.get("query") == query), None)
        if not gt:
            logger.warning(f"No ground truth found for query: {query}")
            continue

        # Extract retrieved doc IDs
        retrieved_docs = [r.get("id") for r in search_result.get("results", [])]

        matched_results.append({
            "query": query,
            "retrieved_docs": retrieved_docs,
            "relevant_docs": gt.get("relevant_docs", []),
            "relevance_scores": gt.get("relevance_scores")
        })

    # Calculate metrics
    metrics = calculator.calculate_retrieval_metrics_batch(matched_results)

    return {
        "retrieval_metrics": metrics.to_dict(),
        "num_evaluated": len(matched_results)
    }


def evaluate_generation_quality(
    generation_results: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Evaluate generation quality.

    Args:
        generation_results: List of generation result dicts

    Returns:
        Dictionary with evaluation metrics
    """
    calculator = EvaluationMetricsCalculator()

    # Calculate metrics
    metrics = calculator.calculate_generation_metrics_batch(generation_results)

    # Calculate latency percentiles
    generation_times = [r.get("generation_time_ms", 0) for r in generation_results]
    latency_percentiles = calculator.calculate_latency_percentiles(generation_times)

    return {
        "generation_metrics": metrics.to_dict(),
        "latency_percentiles": latency_percentiles,
        "num_evaluated": len(generation_results)
    }
