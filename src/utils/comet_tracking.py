"""Comet ML experiment tracking integration."""

from typing import Optional, Dict, Any, List
from datetime import datetime
import json

from loguru import logger

try:
    from comet_ml import Experiment, ExistingExperiment
    COMET_AVAILABLE = True
except ImportError:
    COMET_AVAILABLE = False
    logger.warning("Comet ML not installed. Experiment tracking will be disabled. Install with: pip install comet-ml")


class CometExperimentTracker:
    """Tracker for RAG experiments using Comet ML."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        project_name: str = "hybrid-search-rag",
        workspace: Optional[str] = None,
        enabled: bool = True
    ):
        """
        Initialize Comet experiment tracker.

        Args:
            api_key: Comet ML API key
            project_name: Project name
            workspace: Workspace name
            enabled: Whether tracking is enabled
        """
        self.api_key = api_key
        self.project_name = project_name
        self.workspace = workspace
        self.enabled = enabled and COMET_AVAILABLE and api_key is not None
        self.experiment: Optional[Experiment] = None

        if not COMET_AVAILABLE and enabled:
            logger.warning("Comet ML not available. Experiment tracking disabled.")
        elif not api_key and enabled:
            logger.warning("Comet ML API key not provided. Experiment tracking disabled.")

    def start_experiment(
        self,
        experiment_name: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Optional[Experiment]:
        """
        Start a new experiment.

        Args:
            experiment_name: Name for the experiment
            tags: Tags to associate with experiment

        Returns:
            Experiment instance if successful, None otherwise
        """
        if not self.enabled:
            return None

        try:
            self.experiment = Experiment(
                api_key=self.api_key,
                project_name=self.project_name,
                workspace=self.workspace
            )

            if experiment_name:
                self.experiment.set_name(experiment_name)

            if tags:
                self.experiment.add_tags(tags)

            # Log system info
            self.experiment.log_other("start_time", datetime.utcnow().isoformat())

            logger.info(f"Started Comet experiment: {experiment_name or 'unnamed'}")
            return self.experiment

        except Exception as e:
            logger.error(f"Failed to start Comet experiment: {e}")
            self.enabled = False
            return None

    def log_chunking_experiment(
        self,
        chunker_type: str,
        chunk_size: int,
        chunk_overlap: int,
        num_chunks: int,
        avg_chunk_length: float,
        document_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Log chunking experiment results.

        Args:
            chunker_type: Type of chunker used (semantic, token, sdpm)
            chunk_size: Target chunk size
            chunk_overlap: Chunk overlap size
            num_chunks: Number of chunks created
            avg_chunk_length: Average chunk length
            document_id: ID of chunked document
            metadata: Additional metadata
        """
        if not self.enabled or not self.experiment:
            return

        try:
            # Log parameters
            self.experiment.log_parameters({
                "chunker_type": chunker_type,
                "chunk_size": chunk_size,
                "chunk_overlap": chunk_overlap
            })

            # Log metrics
            self.experiment.log_metrics({
                "num_chunks": num_chunks,
                "avg_chunk_length": avg_chunk_length
            })

            # Log metadata
            if metadata:
                self.experiment.log_other("chunking_metadata", json.dumps(metadata))

            logger.debug(f"Logged chunking experiment for document {document_id}")

        except Exception as e:
            logger.warning(f"Failed to log chunking experiment: {e}")

    def log_embedding_experiment(
        self,
        model_name: str,
        embedding_dim: int,
        batch_size: int,
        num_embeddings: int,
        avg_time_per_embedding_ms: float,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Log embedding generation experiment.

        Args:
            model_name: Name of embedding model
            embedding_dim: Embedding dimension
            batch_size: Batch size used
            num_embeddings: Number of embeddings generated
            avg_time_per_embedding_ms: Average time per embedding in ms
            metadata: Additional metadata
        """
        if not self.enabled or not self.experiment:
            return

        try:
            # Log parameters
            self.experiment.log_parameters({
                "embedding_model": model_name,
                "embedding_dim": embedding_dim,
                "batch_size": batch_size
            })

            # Log metrics
            self.experiment.log_metrics({
                "num_embeddings": num_embeddings,
                "avg_time_per_embedding_ms": avg_time_per_embedding_ms,
                "throughput_embeddings_per_sec": 1000.0 / avg_time_per_embedding_ms if avg_time_per_embedding_ms > 0 else 0
            })

            if metadata:
                self.experiment.log_other("embedding_metadata", json.dumps(metadata))

            logger.debug("Logged embedding experiment")

        except Exception as e:
            logger.warning(f"Failed to log embedding experiment: {e}")

    def log_search_experiment(
        self,
        search_type: str,
        query: str,
        num_results: int,
        search_time_ms: float,
        fusion_method: Optional[str] = None,
        reranked: bool = False,
        reranking_time_ms: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Log search experiment.

        Args:
            search_type: Type of search (semantic, lexical, hybrid)
            query: Search query
            num_results: Number of results returned
            search_time_ms: Search duration in milliseconds
            fusion_method: Fusion method used (if hybrid)
            reranked: Whether results were reranked
            reranking_time_ms: Reranking duration in milliseconds
            metadata: Additional metadata
        """
        if not self.enabled or not self.experiment:
            return

        try:
            # Log parameters
            params = {
                "search_type": search_type,
                "query_length": len(query)
            }
            if fusion_method:
                params["fusion_method"] = fusion_method

            self.experiment.log_parameters(params)

            # Log metrics
            metrics = {
                "num_results": num_results,
                "search_time_ms": search_time_ms
            }
            if reranked and reranking_time_ms is not None:
                metrics["reranking_time_ms"] = reranking_time_ms
                metrics["total_time_ms"] = search_time_ms + reranking_time_ms

            self.experiment.log_metrics(metrics)

            # Log query as text
            self.experiment.log_text(query, metadata={"type": "search_query"})

            if metadata:
                self.experiment.log_other("search_metadata", json.dumps(metadata))

            logger.debug(f"Logged search experiment: {search_type}")

        except Exception as e:
            logger.warning(f"Failed to log search experiment: {e}")

    def log_generation_experiment(
        self,
        model: str,
        query: str,
        num_context_chunks: int,
        input_tokens: int,
        output_tokens: int,
        generation_time_ms: float,
        answer_length: int,
        num_citations: int,
        fallback_used: bool = False,
        validated: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Log LLM generation experiment.

        Args:
            model: LLM model used
            query: User query
            num_context_chunks: Number of context chunks provided
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            generation_time_ms: Generation duration in milliseconds
            answer_length: Length of generated answer
            num_citations: Number of citations in answer
            fallback_used: Whether fallback model was used
            validated: Whether answer passed validation
            metadata: Additional metadata
        """
        if not self.enabled or not self.experiment:
            return

        try:
            # Log parameters
            self.experiment.log_parameters({
                "model": model,
                "num_context_chunks": num_context_chunks,
                "fallback_used": fallback_used
            })

            # Log metrics
            self.experiment.log_metrics({
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "generation_time_ms": generation_time_ms,
                "answer_length": answer_length,
                "num_citations": num_citations,
                "tokens_per_second": (output_tokens / generation_time_ms * 1000) if generation_time_ms > 0 else 0,
                "validated": 1 if validated else 0
            })

            # Log query as text
            self.experiment.log_text(query, metadata={"type": "user_query"})

            if metadata:
                self.experiment.log_other("generation_metadata", json.dumps(metadata))

            logger.debug(f"Logged generation experiment: {model}")

        except Exception as e:
            logger.warning(f"Failed to log generation experiment: {e}")

    def log_rag_experiment(
        self,
        query: str,
        query_type: str,
        num_chunks_retrieved: int,
        num_chunks_used: int,
        search_time_ms: float,
        reranking_time_ms: float,
        generation_time_ms: float,
        total_time_ms: float,
        model_used: str,
        input_tokens: int,
        output_tokens: int,
        num_citations: int,
        fallback_used: bool,
        validated: bool,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Log end-to-end RAG experiment.

        Args:
            query: User query
            query_type: Type of query (methodological, results, etc.)
            num_chunks_retrieved: Number of chunks retrieved
            num_chunks_used: Number of chunks used in generation
            search_time_ms: Search duration in milliseconds
            reranking_time_ms: Reranking duration in milliseconds
            generation_time_ms: Generation duration in milliseconds
            total_time_ms: Total query duration in milliseconds
            model_used: LLM model used
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            num_citations: Number of citations in answer
            fallback_used: Whether fallback was used
            validated: Whether answer passed validation
            metadata: Additional metadata
        """
        if not self.enabled or not self.experiment:
            return

        try:
            # Log parameters
            self.experiment.log_parameters({
                "query_type": query_type,
                "model_used": model_used,
                "num_chunks_retrieved": num_chunks_retrieved,
                "num_chunks_used": num_chunks_used
            })

            # Log metrics
            self.experiment.log_metrics({
                "search_time_ms": search_time_ms,
                "reranking_time_ms": reranking_time_ms,
                "generation_time_ms": generation_time_ms,
                "total_time_ms": total_time_ms,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "num_citations": num_citations,
                "fallback_used": 1 if fallback_used else 0,
                "validated": 1 if validated else 0,
                "retrieval_percentage": (search_time_ms + reranking_time_ms) / total_time_ms * 100 if total_time_ms > 0 else 0,
                "generation_percentage": generation_time_ms / total_time_ms * 100 if total_time_ms > 0 else 0
            })

            # Log query as text
            self.experiment.log_text(query, metadata={"type": "rag_query"})

            if metadata:
                self.experiment.log_other("rag_metadata", json.dumps(metadata))

            logger.debug("Logged RAG experiment")

        except Exception as e:
            logger.warning(f"Failed to log RAG experiment: {e}")

    def log_evaluation_metrics(
        self,
        mrr_at_10: float,
        recall_at_5: float,
        recall_at_10: float,
        ndcg: float,
        avg_answer_quality: float,
        num_queries: int,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Log evaluation metrics.

        Args:
            mrr_at_10: Mean Reciprocal Rank at 10
            recall_at_5: Recall at 5
            recall_at_10: Recall at 10
            ndcg: Normalized Discounted Cumulative Gain
            avg_answer_quality: Average answer quality score
            num_queries: Number of queries evaluated
            metadata: Additional metadata
        """
        if not self.enabled or not self.experiment:
            return

        try:
            # Log evaluation metrics
            self.experiment.log_metrics({
                "mrr_at_10": mrr_at_10,
                "recall_at_5": recall_at_5,
                "recall_at_10": recall_at_10,
                "ndcg": ndcg,
                "avg_answer_quality": avg_answer_quality,
                "num_queries": num_queries
            })

            if metadata:
                self.experiment.log_other("evaluation_metadata", json.dumps(metadata))

            logger.info(f"Logged evaluation metrics: MRR@10={mrr_at_10:.3f}, NDCG={ndcg:.3f}")

        except Exception as e:
            logger.warning(f"Failed to log evaluation metrics: {e}")

    def end_experiment(self):
        """End the current experiment."""
        if not self.enabled or not self.experiment:
            return

        try:
            self.experiment.log_other("end_time", datetime.utcnow().isoformat())
            self.experiment.end()
            logger.info("Ended Comet experiment")
            self.experiment = None

        except Exception as e:
            logger.error(f"Failed to end Comet experiment: {e}")


# Global tracker instance
_tracker: Optional[CometExperimentTracker] = None


def get_tracker() -> Optional[CometExperimentTracker]:
    """
    Get global tracker instance.

    Returns:
        CometExperimentTracker: Global tracker instance or None
    """
    global _tracker
    if _tracker is None:
        # Initialize with disabled state by default
        _tracker = CometExperimentTracker(enabled=False)
    return _tracker


def set_tracker(tracker: CometExperimentTracker):
    """
    Set global tracker instance.

    Args:
        tracker: Tracker instance to set
    """
    global _tracker
    _tracker = tracker


def initialize_tracker(
    api_key: Optional[str] = None,
    project_name: str = "hybrid-search-rag",
    workspace: Optional[str] = None,
    enabled: bool = True
):
    """
    Initialize global tracker.

    Args:
        api_key: Comet ML API key
        project_name: Project name
        workspace: Workspace name
        enabled: Whether tracking is enabled
    """
    tracker = CometExperimentTracker(
        api_key=api_key,
        project_name=project_name,
        workspace=workspace,
        enabled=enabled
    )
    set_tracker(tracker)
    return tracker
