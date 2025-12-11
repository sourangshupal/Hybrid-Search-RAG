"""OPIK tracing integration for RAG pipeline observability."""

import time
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any, List
from functools import wraps
import asyncio

from loguru import logger

try:
    import opik
    from opik import track
    OPIK_AVAILABLE = True
except ImportError:
    OPIK_AVAILABLE = False
    logger.warning("OPIK not installed. Tracing will be disabled. Install with: pip install opik")


class TracingContext:
    """Context manager for tracing operations."""

    def __init__(self, operation_name: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Initialize tracing context.

        Args:
            operation_name: Name of the operation being traced
            metadata: Additional metadata to log
        """
        self.operation_name = operation_name
        self.metadata = metadata or {}
        self.start_time = None
        self.end_time = None
        self.duration_ms = None
        self.result = None
        self.error = None

    def __enter__(self):
        """Start tracing."""
        self.start_time = time.time()
        logger.debug(f"[TRACE] Starting {self.operation_name}", extra=self.metadata)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """End tracing."""
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000

        if exc_type is not None:
            self.error = str(exc_val)
            logger.error(
                f"[TRACE] {self.operation_name} failed after {self.duration_ms:.2f}ms: {self.error}",
                extra=self.metadata
            )
        else:
            logger.debug(
                f"[TRACE] {self.operation_name} completed in {self.duration_ms:.2f}ms",
                extra=self.metadata
            )

        return False  # Don't suppress exceptions

    async def __aenter__(self):
        """Async context manager entry."""
        self.start_time = time.time()
        logger.debug(f"[TRACE] Starting {self.operation_name}", extra=self.metadata)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000

        if exc_type is not None:
            self.error = str(exc_val)
            logger.error(
                f"[TRACE] {self.operation_name} failed after {self.duration_ms:.2f}ms: {self.error}",
                extra=self.metadata
            )
        else:
            logger.debug(
                f"[TRACE] {self.operation_name} completed in {self.duration_ms:.2f}ms",
                extra=self.metadata
            )

        return False


class RAGTracer:
    """Tracer for RAG pipeline operations."""

    def __init__(self, project_name: str = "hybrid-search-rag", enabled: bool = True):
        """
        Initialize RAG tracer.

        Args:
            project_name: OPIK project name
            enabled: Whether tracing is enabled
        """
        self.project_name = project_name
        self.enabled = enabled and OPIK_AVAILABLE

        if self.enabled:
            try:
                opik.configure(project_name=project_name)
                logger.info(f"OPIK tracing initialized for project: {project_name}")
            except Exception as e:
                logger.warning(f"Failed to initialize OPIK: {e}. Tracing will be disabled.")
                self.enabled = False

    @asynccontextmanager
    async def trace_retrieval(
        self,
        query: str,
        limit: int,
        semantic_only: bool = False,
        lexical_only: bool = False
    ):
        """
        Trace document retrieval operation.

        Args:
            query: Search query
            limit: Number of results to retrieve
            semantic_only: Whether using semantic search only
            lexical_only: Whether using lexical search only

        Yields:
            TracingContext: Context for retrieval operation
        """
        search_type = "semantic" if semantic_only else ("lexical" if lexical_only else "hybrid")

        metadata = {
            "query": query,
            "limit": limit,
            "search_type": search_type
        }

        async with TracingContext("retrieval", metadata) as ctx:
            if self.enabled:
                ctx.metadata["opik_enabled"] = True
            yield ctx

    @asynccontextmanager
    async def trace_reranking(
        self,
        query: str,
        num_documents: int,
        top_n: Optional[int] = None
    ):
        """
        Trace reranking operation.

        Args:
            query: Search query
            num_documents: Number of documents to rerank
            top_n: Number of top results to return

        Yields:
            TracingContext: Context for reranking operation
        """
        metadata = {
            "query": query,
            "num_documents": num_documents,
            "top_n": top_n or num_documents
        }

        async with TracingContext("reranking", metadata) as ctx:
            if self.enabled:
                ctx.metadata["opik_enabled"] = True
            yield ctx

    @asynccontextmanager
    async def trace_generation(
        self,
        query: str,
        num_chunks: int,
        query_type: str,
        model: str
    ):
        """
        Trace answer generation operation.

        Args:
            query: User query
            num_chunks: Number of context chunks
            query_type: Type of query (e.g., methodological, results)
            model: LLM model being used

        Yields:
            TracingContext: Context for generation operation
        """
        metadata = {
            "query": query,
            "num_chunks": num_chunks,
            "query_type": query_type,
            "model": model
        }

        async with TracingContext("generation", metadata) as ctx:
            if self.enabled:
                ctx.metadata["opik_enabled"] = True
            yield ctx

    @asynccontextmanager
    async def trace_rag_query(
        self,
        query: str,
        max_results: int,
        use_reranking: bool
    ):
        """
        Trace full RAG query operation.

        Args:
            query: User query
            max_results: Maximum number of results to retrieve
            use_reranking: Whether reranking is enabled

        Yields:
            TracingContext: Context for RAG query operation
        """
        metadata = {
            "query": query,
            "max_results": max_results,
            "use_reranking": use_reranking
        }

        async with TracingContext("rag_query", metadata) as ctx:
            if self.enabled:
                ctx.metadata["opik_enabled"] = True
            yield ctx

    @asynccontextmanager
    async def trace_embedding(
        self,
        text_length: int,
        batch_size: int = 1
    ):
        """
        Trace embedding generation operation.

        Args:
            text_length: Length of text being embedded
            batch_size: Number of texts in batch

        Yields:
            TracingContext: Context for embedding operation
        """
        metadata = {
            "text_length": text_length,
            "batch_size": batch_size
        }

        async with TracingContext("embedding", metadata) as ctx:
            if self.enabled:
                ctx.metadata["opik_enabled"] = True
            yield ctx

    def log_retrieval_metrics(
        self,
        query: str,
        num_results: int,
        search_time_ms: float,
        fusion_method: Optional[str] = None,
        semantic_count: int = 0,
        lexical_count: int = 0
    ):
        """
        Log retrieval metrics.

        Args:
            query: Search query
            num_results: Number of results retrieved
            search_time_ms: Search duration in milliseconds
            fusion_method: Fusion method used (e.g., RRF)
            semantic_count: Number of semantic results
            lexical_count: Number of lexical results
        """
        if not self.enabled:
            return

        try:
            logger.info(
                "Retrieval metrics",
                extra={
                    "query": query,
                    "num_results": num_results,
                    "search_time_ms": search_time_ms,
                    "fusion_method": fusion_method,
                    "semantic_count": semantic_count,
                    "lexical_count": lexical_count
                }
            )
        except Exception as e:
            logger.warning(f"Failed to log retrieval metrics: {e}")

    def log_generation_metrics(
        self,
        query: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        generation_time_ms: float,
        fallback_used: bool = False
    ):
        """
        Log generation metrics.

        Args:
            query: User query
            model: LLM model used
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            generation_time_ms: Generation duration in milliseconds
            fallback_used: Whether fallback model was used
        """
        if not self.enabled:
            return

        try:
            logger.info(
                "Generation metrics",
                extra={
                    "query": query,
                    "model": model,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": input_tokens + output_tokens,
                    "generation_time_ms": generation_time_ms,
                    "fallback_used": fallback_used
                }
            )
        except Exception as e:
            logger.warning(f"Failed to log generation metrics: {e}")

    def log_rag_metrics(
        self,
        query: str,
        total_time_ms: float,
        num_chunks_retrieved: int,
        num_chunks_used: int,
        model_used: str,
        fallback_used: bool,
        validated: bool
    ):
        """
        Log end-to-end RAG metrics.

        Args:
            query: User query
            total_time_ms: Total query duration in milliseconds
            num_chunks_retrieved: Number of chunks retrieved
            num_chunks_used: Number of chunks used in generation
            model_used: LLM model used
            fallback_used: Whether fallback was used
            validated: Whether response passed validation
        """
        if not self.enabled:
            return

        try:
            logger.info(
                "RAG query metrics",
                extra={
                    "query": query,
                    "total_time_ms": total_time_ms,
                    "num_chunks_retrieved": num_chunks_retrieved,
                    "num_chunks_used": num_chunks_used,
                    "model_used": model_used,
                    "fallback_used": fallback_used,
                    "validated": validated
                }
            )
        except Exception as e:
            logger.warning(f"Failed to log RAG metrics: {e}")


# Global tracer instance
_tracer: Optional[RAGTracer] = None


def get_tracer() -> RAGTracer:
    """
    Get global tracer instance.

    Returns:
        RAGTracer: Global tracer instance
    """
    global _tracer
    if _tracer is None:
        _tracer = RAGTracer()
    return _tracer


def set_tracer(tracer: RAGTracer):
    """
    Set global tracer instance.

    Args:
        tracer: Tracer instance to set
    """
    global _tracer
    _tracer = tracer
