"""Evaluation script for RAG system performance."""

import asyncio
import argparse
import json
import time
from typing import List, Dict, Any, Optional
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from src.core.config import Settings
from src.core.rag_pipeline import RAGPipeline, RAGResult
from src.retrieval.hybrid_search import HybridSearchEngine
from src.embeddings.bge_embedder import BGEEmbedder
from src.retrieval.qdrant_client import QdrantClient
from src.retrieval.elasticsearch_client import ElasticsearchClient
from src.generation.claude_generator import ClaudeGenerator
from src.generation.openai_generator import OpenAIGenerator
from src.reranking.cohere_reranker import CohereReranker
from src.utils.tracing import RAGTracer
from src.utils.comet_tracking import CometExperimentTracker


class RAGEvaluator:
    """Evaluator for RAG system performance."""

    def __init__(
        self,
        rag_pipeline: RAGPipeline,
        tracer: Optional[RAGTracer] = None,
        tracker: Optional[CometExperimentTracker] = None
    ):
        """
        Initialize evaluator.

        Args:
            rag_pipeline: RAG pipeline to evaluate
            tracer: Optional OPIK tracer
            tracker: Optional Comet ML tracker
        """
        self.rag_pipeline = rag_pipeline
        self.tracer = tracer
        self.tracker = tracker
        self.results: List[Dict[str, Any]] = []

    async def evaluate_query(
        self,
        query: str,
        expected_answer: Optional[str] = None,
        relevant_doc_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Evaluate a single query.

        Args:
            query: Query to evaluate
            expected_answer: Expected answer (optional)
            relevant_doc_ids: List of relevant document IDs for retrieval evaluation

        Returns:
            Dictionary with evaluation results
        """
        logger.info(f"Evaluating query: {query}")

        start_time = time.time()

        try:
            # Run RAG query
            result = await self.rag_pipeline.query(
                query=query,
                max_results=20,
                use_reranking=True
            )

            # Calculate metrics
            evaluation = {
                "query": query,
                "answer": result.answer,
                "answer_length": len(result.answer),
                "num_citations": len(result.citations),
                "num_sources": len(result.search_results),
                "total_time_ms": result.total_time_ms,
                "search_time_ms": result.search_time_ms,
                "reranking_time_ms": result.reranking_time_ms,
                "generation_time_ms": result.generation_time_ms,
                "model_used": result.model_used,
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
                "total_tokens": result.total_tokens,
                "fallback_used": result.fallback_used,
                "validated": result.validated,
                "success": True
            }

            # Calculate retrieval metrics if relevant docs provided
            if relevant_doc_ids:
                retrieved_ids = [doc["id"] for doc in result.search_results]
                evaluation["retrieval_metrics"] = self._calculate_retrieval_metrics(
                    retrieved_ids,
                    relevant_doc_ids
                )

            # Track in Comet ML
            if self.tracker and self.tracker.experiment:
                self.tracker.log_rag_experiment(
                    query=query,
                    query_type=result.query_type,
                    num_chunks_retrieved=result.num_chunks_retrieved,
                    num_chunks_used=result.num_chunks_used,
                    search_time_ms=result.search_time_ms,
                    reranking_time_ms=result.reranking_time_ms,
                    generation_time_ms=result.generation_time_ms,
                    total_time_ms=result.total_time_ms,
                    model_used=result.model_used,
                    input_tokens=result.input_tokens,
                    output_tokens=result.output_tokens,
                    num_citations=len(result.citations),
                    fallback_used=result.fallback_used,
                    validated=result.validated
                )

            logger.info(f"Query completed in {result.total_time_ms:.2f}ms")

        except Exception as e:
            logger.error(f"Query failed: {e}")
            evaluation = {
                "query": query,
                "success": False,
                "error": str(e),
                "total_time_ms": (time.time() - start_time) * 1000
            }

        self.results.append(evaluation)
        return evaluation

    def _calculate_retrieval_metrics(
        self,
        retrieved_ids: List[str],
        relevant_ids: List[str],
        k_values: List[int] = [5, 10, 20]
    ) -> Dict[str, float]:
        """
        Calculate retrieval metrics.

        Args:
            retrieved_ids: List of retrieved document IDs
            relevant_ids: List of relevant document IDs
            k_values: K values for Recall@K

        Returns:
            Dictionary with retrieval metrics
        """
        metrics = {}

        # Calculate MRR (Mean Reciprocal Rank)
        mrr = 0.0
        for i, doc_id in enumerate(retrieved_ids):
            if doc_id in relevant_ids:
                mrr = 1.0 / (i + 1)
                break
        metrics["mrr"] = mrr

        # Calculate Recall@K
        for k in k_values:
            retrieved_at_k = set(retrieved_ids[:k])
            relevant_set = set(relevant_ids)
            recall = len(retrieved_at_k & relevant_set) / len(relevant_set) if relevant_set else 0.0
            metrics[f"recall_at_{k}"] = recall

        # Calculate Precision@K
        for k in k_values:
            retrieved_at_k = set(retrieved_ids[:k])
            relevant_set = set(relevant_ids)
            precision = len(retrieved_at_k & relevant_set) / k if k > 0 else 0.0
            metrics[f"precision_at_{k}"] = precision

        return metrics

    async def evaluate_dataset(
        self,
        dataset: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Evaluate entire dataset.

        Args:
            dataset: List of evaluation queries with format:
                [{"query": str, "expected_answer": str (optional), "relevant_docs": List[str] (optional)}]

        Returns:
            Dictionary with aggregated results
        """
        logger.info(f"Evaluating dataset with {len(dataset)} queries")

        for item in dataset:
            await self.evaluate_query(
                query=item["query"],
                expected_answer=item.get("expected_answer"),
                relevant_doc_ids=item.get("relevant_docs")
            )

        # Calculate aggregate metrics
        return self.get_aggregate_metrics()

    def get_aggregate_metrics(self) -> Dict[str, Any]:
        """
        Calculate aggregate metrics from all results.

        Returns:
            Dictionary with aggregate metrics
        """
        if not self.results:
            return {}

        successful_results = [r for r in self.results if r.get("success", False)]

        if not successful_results:
            return {
                "total_queries": len(self.results),
                "successful_queries": 0,
                "failed_queries": len(self.results),
                "success_rate": 0.0
            }

        # Calculate averages
        avg_metrics = {
            "total_queries": len(self.results),
            "successful_queries": len(successful_results),
            "failed_queries": len(self.results) - len(successful_results),
            "success_rate": len(successful_results) / len(self.results) * 100,
            "avg_total_time_ms": sum(r["total_time_ms"] for r in successful_results) / len(successful_results),
            "avg_search_time_ms": sum(r.get("search_time_ms", 0) for r in successful_results) / len(successful_results),
            "avg_generation_time_ms": sum(r.get("generation_time_ms", 0) for r in successful_results) / len(successful_results),
            "avg_answer_length": sum(r.get("answer_length", 0) for r in successful_results) / len(successful_results),
            "avg_num_citations": sum(r.get("num_citations", 0) for r in successful_results) / len(successful_results),
            "avg_total_tokens": sum(r.get("total_tokens", 0) for r in successful_results) / len(successful_results),
            "fallback_rate": sum(1 for r in successful_results if r.get("fallback_used", False)) / len(successful_results) * 100,
            "validation_pass_rate": sum(1 for r in successful_results if r.get("validated", False)) / len(successful_results) * 100
        }

        # Calculate retrieval metrics if available
        results_with_retrieval = [r for r in successful_results if "retrieval_metrics" in r]
        if results_with_retrieval:
            avg_metrics["avg_mrr"] = sum(r["retrieval_metrics"]["mrr"] for r in results_with_retrieval) / len(results_with_retrieval)
            avg_metrics["avg_recall_at_5"] = sum(r["retrieval_metrics"]["recall_at_5"] for r in results_with_retrieval) / len(results_with_retrieval)
            avg_metrics["avg_recall_at_10"] = sum(r["retrieval_metrics"]["recall_at_10"] for r in results_with_retrieval) / len(results_with_retrieval)

        # Calculate percentiles
        times = [r["total_time_ms"] for r in successful_results]
        times.sort()
        n = len(times)
        avg_metrics["p50_time_ms"] = times[int(0.5 * n)] if n > 0 else 0
        avg_metrics["p95_time_ms"] = times[int(0.95 * n)] if n > 0 else 0
        avg_metrics["p99_time_ms"] = times[int(0.99 * n)] if n > 0 else 0

        return avg_metrics

    def save_results(self, output_path: str):
        """
        Save evaluation results to file.

        Args:
            output_path: Path to output file
        """
        output = {
            "timestamp": time.time(),
            "aggregate_metrics": self.get_aggregate_metrics(),
            "individual_results": self.results
        }

        with open(output_path, "w") as f:
            json.dump(output, f, indent=2)

        logger.info(f"Results saved to {output_path}")


async def main():
    """Main evaluation function."""
    parser = argparse.ArgumentParser(description="Run RAG system evaluation")
    parser.add_argument(
        "--dataset",
        type=str,
        help="Path to evaluation dataset JSON file"
    )
    parser.add_argument(
        "--query",
        type=str,
        help="Single query to evaluate"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="evaluation_results.json",
        help="Path to output results file"
    )
    parser.add_argument(
        "--enable-comet",
        action="store_true",
        help="Enable Comet ML tracking"
    )
    parser.add_argument(
        "--experiment-name",
        type=str,
        help="Comet ML experiment name"
    )

    args = parser.parse_args()

    # Load settings
    settings = Settings()

    # Initialize components
    logger.info("Initializing RAG components...")

    # Embedder
    embedder = BGEEmbedder(
        model_name="BAAI/bge-base-en-v1.5",
        device="cpu"
    )

    # Clients
    qdrant_client = QdrantClient(
        host=settings.qdrant_host,
        port=settings.qdrant_port
    )

    es_client = ElasticsearchClient(
        host=settings.elasticsearch_host,
        port=settings.elasticsearch_port
    )

    # Reranker
    reranker = None
    if settings.cohere_api_key:
        reranker = CohereReranker(
            api_key=settings.cohere_api_key,
            use_async=True
        )

    # Search engine
    search_engine = HybridSearchEngine(
        embedder=embedder,
        qdrant_client=qdrant_client,
        elasticsearch_client=es_client,
        reranker=reranker
    )

    # Generators
    primary_generator = ClaudeGenerator(
        api_key=settings.anthropic_api_key,
        model="claude-sonnet-4-5-20250929"
    )

    fallback_generator = None
    if settings.openai_api_key:
        fallback_generator = OpenAIGenerator(
            api_key=settings.openai_api_key,
            model="gpt-4o"
        )

    # RAG pipeline
    rag_pipeline = RAGPipeline(
        search_engine=search_engine,
        primary_generator=primary_generator,
        fallback_generator=fallback_generator,
        enable_fallback=True
    )

    # Initialize tracer
    tracer = RAGTracer(enabled=True)

    # Initialize Comet tracker
    tracker = None
    if args.enable_comet and settings.comet_api_key:
        tracker = CometExperimentTracker(
            api_key=settings.comet_api_key,
            project_name="hybrid-search-rag",
            enabled=True
        )
        tracker.start_experiment(
            experiment_name=args.experiment_name or f"evaluation-{int(time.time())}",
            tags=["evaluation"]
        )

    # Create evaluator
    evaluator = RAGEvaluator(
        rag_pipeline=rag_pipeline,
        tracer=tracer,
        tracker=tracker
    )

    # Run evaluation
    if args.query:
        # Single query evaluation
        logger.info("Running single query evaluation")
        result = await evaluator.evaluate_query(args.query)
        print(json.dumps(result, indent=2))

    elif args.dataset:
        # Dataset evaluation
        logger.info(f"Loading dataset from {args.dataset}")
        with open(args.dataset) as f:
            dataset = json.load(f)

        aggregate = await evaluator.evaluate_dataset(dataset)
        print("\nAggregate Metrics:")
        print(json.dumps(aggregate, indent=2))

        # Save results
        evaluator.save_results(args.output)

    else:
        # Demo queries
        logger.info("Running demo evaluation")
        demo_queries = [
            "What are transformers in machine learning?",
            "How does BERT work?",
            "Explain attention mechanism in neural networks",
            "What is the difference between GPT and BERT?",
            "How does backpropagation work?"
        ]

        for query in demo_queries:
            await evaluator.evaluate_query(query)

        aggregate = evaluator.get_aggregate_metrics()
        print("\nAggregate Metrics:")
        print(json.dumps(aggregate, indent=2))

        # Save results
        evaluator.save_results(args.output)

    # End Comet experiment
    if tracker:
        tracker.end_experiment()

    logger.info("Evaluation complete")


if __name__ == "__main__":
    asyncio.run(main())
