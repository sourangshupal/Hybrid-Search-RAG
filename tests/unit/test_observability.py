"""Tests for observability components."""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import json

from src.utils.tracing import RAGTracer, TracingContext, get_tracer, set_tracer
from src.utils.comet_tracking import CometExperimentTracker, get_tracker, set_tracker
from src.utils.cloudwatch import CloudWatchLogger, CloudWatchMetrics


class TestTracingContext:
    """Tests for TracingContext."""

    def test_sync_context_success(self):
        """Test synchronous context manager success."""
        ctx = TracingContext("test_operation", {"key": "value"})

        with ctx:
            assert ctx.start_time is not None

        assert ctx.end_time is not None
        assert ctx.duration_ms is not None
        assert ctx.duration_ms > 0
        assert ctx.error is None

    def test_sync_context_error(self):
        """Test synchronous context manager with error."""
        ctx = TracingContext("test_operation")

        with pytest.raises(ValueError):
            with ctx:
                raise ValueError("Test error")

        assert ctx.error == "Test error"

    @pytest.mark.asyncio
    async def test_async_context_success(self):
        """Test asynchronous context manager success."""
        ctx = TracingContext("test_operation")

        async with ctx:
            assert ctx.start_time is not None

        assert ctx.end_time is not None
        assert ctx.duration_ms > 0

    @pytest.mark.asyncio
    async def test_async_context_error(self):
        """Test asynchronous context manager with error."""
        ctx = TracingContext("test_operation")

        with pytest.raises(ValueError):
            async with ctx:
                raise ValueError("Async test error")

        assert ctx.error == "Async test error"


class TestRAGTracer:
    """Tests for RAGTracer."""

    def test_init_disabled(self):
        """Test tracer initialization when disabled."""
        tracer = RAGTracer(enabled=False)
        assert not tracer.enabled

    @patch('src.utils.tracing.OPIK_AVAILABLE', False)
    def test_init_opik_not_available(self):
        """Test tracer initialization when OPIK not available."""
        tracer = RAGTracer(enabled=True)
        assert not tracer.enabled

    @pytest.mark.asyncio
    async def test_trace_retrieval(self):
        """Test retrieval tracing."""
        tracer = RAGTracer(enabled=False)  # Disable OPIK for testing

        async with tracer.trace_retrieval(
            query="test query",
            limit=10,
            semantic_only=True
        ) as ctx:
            assert ctx.operation_name == "retrieval"
            assert ctx.metadata["query"] == "test query"
            assert ctx.metadata["limit"] == 10
            assert ctx.metadata["search_type"] == "semantic"

    @pytest.mark.asyncio
    async def test_trace_reranking(self):
        """Test reranking tracing."""
        tracer = RAGTracer(enabled=False)

        async with tracer.trace_reranking(
            query="test query",
            num_documents=20,
            top_n=10
        ) as ctx:
            assert ctx.operation_name == "reranking"
            assert ctx.metadata["num_documents"] == 20
            assert ctx.metadata["top_n"] == 10

    @pytest.mark.asyncio
    async def test_trace_generation(self):
        """Test generation tracing."""
        tracer = RAGTracer(enabled=False)

        async with tracer.trace_generation(
            query="test query",
            num_chunks=10,
            query_type="general",
            model="claude-sonnet-4-5-20250929"
        ) as ctx:
            assert ctx.operation_name == "generation"
            assert ctx.metadata["model"] == "claude-sonnet-4-5-20250929"

    @pytest.mark.asyncio
    async def test_trace_rag_query(self):
        """Test RAG query tracing."""
        tracer = RAGTracer(enabled=False)

        async with tracer.trace_rag_query(
            query="test query",
            max_results=20,
            use_reranking=True
        ) as ctx:
            assert ctx.operation_name == "rag_query"
            assert ctx.metadata["use_reranking"] is True

    def test_log_retrieval_metrics(self):
        """Test logging retrieval metrics."""
        tracer = RAGTracer(enabled=False)

        # Should not raise error even when disabled
        tracer.log_retrieval_metrics(
            query="test",
            num_results=10,
            search_time_ms=150.0,
            fusion_method="rrf"
        )

    def test_log_generation_metrics(self):
        """Test logging generation metrics."""
        tracer = RAGTracer(enabled=False)

        tracer.log_generation_metrics(
            query="test",
            model="claude-sonnet-4-5-20250929",
            input_tokens=1000,
            output_tokens=200,
            generation_time_ms=2000.0
        )

    def test_get_set_tracer(self):
        """Test global tracer get/set."""
        tracer = RAGTracer(enabled=False)
        set_tracer(tracer)
        assert get_tracer() == tracer


class TestCometExperimentTracker:
    """Tests for CometExperimentTracker."""

    def test_init_disabled(self):
        """Test tracker initialization when disabled."""
        tracker = CometExperimentTracker(enabled=False)
        assert not tracker.enabled

    def test_init_no_api_key(self):
        """Test tracker initialization without API key."""
        tracker = CometExperimentTracker(api_key=None, enabled=True)
        assert not tracker.enabled

    @patch('src.utils.comet_tracking.COMET_AVAILABLE', False)
    def test_init_comet_not_available(self):
        """Test tracker initialization when Comet not available."""
        tracker = CometExperimentTracker(api_key="test", enabled=True)
        assert not tracker.enabled

    def test_start_experiment_disabled(self):
        """Test starting experiment when disabled."""
        tracker = CometExperimentTracker(enabled=False)
        result = tracker.start_experiment("test")
        assert result is None

    def test_log_chunking_experiment_disabled(self):
        """Test logging chunking experiment when disabled."""
        tracker = CometExperimentTracker(enabled=False)

        # Should not raise error
        tracker.log_chunking_experiment(
            chunker_type="semantic",
            chunk_size=512,
            chunk_overlap=50,
            num_chunks=100,
            avg_chunk_length=450.0,
            document_id="doc123"
        )

    def test_log_embedding_experiment_disabled(self):
        """Test logging embedding experiment when disabled."""
        tracker = CometExperimentTracker(enabled=False)

        tracker.log_embedding_experiment(
            model_name="bge-base",
            embedding_dim=768,
            batch_size=32,
            num_embeddings=1000,
            avg_time_per_embedding_ms=10.0
        )

    def test_log_search_experiment_disabled(self):
        """Test logging search experiment when disabled."""
        tracker = CometExperimentTracker(enabled=False)

        tracker.log_search_experiment(
            search_type="hybrid",
            query="test query",
            num_results=10,
            search_time_ms=150.0,
            reranked=True,
            reranking_time_ms=75.0
        )

    def test_log_generation_experiment_disabled(self):
        """Test logging generation experiment when disabled."""
        tracker = CometExperimentTracker(enabled=False)

        tracker.log_generation_experiment(
            model="claude-sonnet-4-5-20250929",
            query="test",
            num_context_chunks=10,
            input_tokens=1000,
            output_tokens=200,
            generation_time_ms=2000.0,
            answer_length=500,
            num_citations=3
        )

    def test_log_rag_experiment_disabled(self):
        """Test logging RAG experiment when disabled."""
        tracker = CometExperimentTracker(enabled=False)

        tracker.log_rag_experiment(
            query="test",
            query_type="general",
            num_chunks_retrieved=20,
            num_chunks_used=10,
            search_time_ms=150.0,
            reranking_time_ms=75.0,
            generation_time_ms=2000.0,
            total_time_ms=2225.0,
            model_used="claude-sonnet-4-5-20250929",
            input_tokens=1000,
            output_tokens=200,
            num_citations=3,
            fallback_used=False,
            validated=True
        )

    def test_log_evaluation_metrics_disabled(self):
        """Test logging evaluation metrics when disabled."""
        tracker = CometExperimentTracker(enabled=False)

        tracker.log_evaluation_metrics(
            mrr_at_10=0.75,
            recall_at_5=0.6,
            recall_at_10=0.8,
            ndcg=0.85,
            avg_answer_quality=0.9,
            num_queries=100
        )

    def test_end_experiment_disabled(self):
        """Test ending experiment when disabled."""
        tracker = CometExperimentTracker(enabled=False)
        tracker.end_experiment()  # Should not raise error

    def test_get_set_tracker(self):
        """Test global tracker get/set."""
        tracker = CometExperimentTracker(enabled=False)
        set_tracker(tracker)
        assert get_tracker() == tracker


class TestCloudWatchLogger:
    """Tests for CloudWatchLogger."""

    def test_init_disabled(self):
        """Test logger initialization when disabled."""
        logger = CloudWatchLogger(enabled=False)
        assert not logger.enabled
        assert logger.client is None

    @patch('src.utils.cloudwatch.BOTO3_AVAILABLE', False)
    def test_init_boto3_not_available(self):
        """Test logger initialization when boto3 not available."""
        logger = CloudWatchLogger(enabled=True)
        assert not logger.enabled

    @patch('src.utils.cloudwatch.boto3')
    def test_init_no_credentials(self, mock_boto3):
        """Test logger initialization without AWS credentials."""
        from botocore.exceptions import NoCredentialsError

        mock_boto3.client.side_effect = NoCredentialsError()

        logger = CloudWatchLogger(enabled=True)
        assert not logger.enabled

    def test_log_event_disabled(self):
        """Test logging event when disabled."""
        logger = CloudWatchLogger(enabled=False)

        # Should not raise error
        logger.log_event(
            message="Test message",
            level="INFO",
            metadata={"key": "value"}
        )

    def test_log_api_request_disabled(self):
        """Test logging API request when disabled."""
        logger = CloudWatchLogger(enabled=False)

        logger.log_api_request(
            request_id="req-123",
            method="POST",
            path="/api/v1/query",
            status_code=200,
            duration_ms=2500.0
        )

    def test_log_search_query_disabled(self):
        """Test logging search query when disabled."""
        logger = CloudWatchLogger(enabled=False)

        logger.log_search_query(
            query="test query",
            search_type="hybrid",
            num_results=10,
            search_time_ms=150.0,
            reranked=True
        )

    def test_log_rag_query_disabled(self):
        """Test logging RAG query when disabled."""
        logger = CloudWatchLogger(enabled=False)

        logger.log_rag_query(
            query="test",
            model_used="claude-sonnet-4-5-20250929",
            total_time_ms=2500.0,
            num_chunks_retrieved=20,
            num_chunks_used=10,
            input_tokens=1000,
            output_tokens=200,
            fallback_used=False,
            validated=True
        )

    def test_log_error_disabled(self):
        """Test logging error when disabled."""
        logger = CloudWatchLogger(enabled=False)

        logger.log_error(
            error_type="ValueError",
            error_message="Test error",
            stack_trace="Stack trace here"
        )


class TestCloudWatchMetrics:
    """Tests for CloudWatchMetrics."""

    def test_init_disabled(self):
        """Test metrics initialization when disabled."""
        metrics = CloudWatchMetrics(enabled=False)
        assert not metrics.enabled
        assert metrics.client is None

    @patch('src.utils.cloudwatch.BOTO3_AVAILABLE', False)
    def test_init_boto3_not_available(self):
        """Test metrics initialization when boto3 not available."""
        metrics = CloudWatchMetrics(enabled=True)
        assert not metrics.enabled

    def test_put_metric_disabled(self):
        """Test putting metric when disabled."""
        metrics = CloudWatchMetrics(enabled=False)

        # Should not raise error
        metrics.put_metric(
            metric_name="TestMetric",
            value=100.0,
            unit="Count"
        )

    def test_put_search_latency_disabled(self):
        """Test putting search latency when disabled."""
        metrics = CloudWatchMetrics(enabled=False)

        metrics.put_search_latency(
            latency_ms=150.0,
            search_type="hybrid"
        )

    def test_put_rag_latency_disabled(self):
        """Test putting RAG latency when disabled."""
        metrics = CloudWatchMetrics(enabled=False)

        metrics.put_rag_latency(
            latency_ms=2500.0,
            model="claude-sonnet-4-5-20250929"
        )

    def test_put_token_usage_disabled(self):
        """Test putting token usage when disabled."""
        metrics = CloudWatchMetrics(enabled=False)

        metrics.put_token_usage(
            tokens=1000,
            model="claude-sonnet-4-5-20250929",
            token_type="input"
        )

    def test_put_cache_hit_disabled(self):
        """Test putting cache hit when disabled."""
        metrics = CloudWatchMetrics(enabled=False)

        metrics.put_cache_hit(hit=True)
        metrics.put_cache_hit(hit=False)

    def test_put_error_count_disabled(self):
        """Test putting error count when disabled."""
        metrics = CloudWatchMetrics(enabled=False)

        metrics.put_error_count(error_type="ValueError")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
