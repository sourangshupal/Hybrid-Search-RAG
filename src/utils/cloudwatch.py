"""AWS CloudWatch integration for logging and monitoring."""

import json
from typing import Optional, Dict, Any, List
from datetime import datetime
import os

from loguru import logger

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    logger.warning("boto3 not installed. CloudWatch integration will be disabled. Install with: pip install boto3")


class CloudWatchLogger:
    """Logger for sending structured logs to AWS CloudWatch."""

    def __init__(
        self,
        log_group_name: str = "/aws/hybrid-search-rag",
        log_stream_name: Optional[str] = None,
        region: str = "us-east-1",
        enabled: bool = True
    ):
        """
        Initialize CloudWatch logger.

        Args:
            log_group_name: CloudWatch log group name
            log_stream_name: CloudWatch log stream name (auto-generated if None)
            region: AWS region
            enabled: Whether CloudWatch logging is enabled
        """
        self.log_group_name = log_group_name
        self.log_stream_name = log_stream_name or f"api-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
        self.region = region
        self.enabled = enabled and BOTO3_AVAILABLE
        self.client = None
        self.sequence_token = None

        if self.enabled:
            try:
                self.client = boto3.client('logs', region_name=region)
                self._ensure_log_group_exists()
                self._ensure_log_stream_exists()
                logger.info(f"CloudWatch logger initialized: {log_group_name}/{self.log_stream_name}")
            except NoCredentialsError:
                logger.warning("AWS credentials not found. CloudWatch logging disabled.")
                self.enabled = False
            except Exception as e:
                logger.warning(f"Failed to initialize CloudWatch: {e}. Logging disabled.")
                self.enabled = False

    def _ensure_log_group_exists(self):
        """Ensure log group exists, create if it doesn't."""
        if not self.client:
            return

        try:
            self.client.create_log_group(logGroupName=self.log_group_name)
            logger.info(f"Created CloudWatch log group: {self.log_group_name}")
        except self.client.exceptions.ResourceAlreadyExistsException:
            pass  # Log group already exists
        except Exception as e:
            logger.error(f"Failed to create log group: {e}")
            raise

    def _ensure_log_stream_exists(self):
        """Ensure log stream exists, create if it doesn't."""
        if not self.client:
            return

        try:
            self.client.create_log_stream(
                logGroupName=self.log_group_name,
                logStreamName=self.log_stream_name
            )
            logger.info(f"Created CloudWatch log stream: {self.log_stream_name}")
        except self.client.exceptions.ResourceAlreadyExistsException:
            pass  # Log stream already exists
        except Exception as e:
            logger.error(f"Failed to create log stream: {e}")
            raise

    def log_event(
        self,
        message: str,
        level: str = "INFO",
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Log a single event to CloudWatch.

        Args:
            message: Log message
            level: Log level (INFO, WARNING, ERROR, DEBUG)
            metadata: Additional metadata to include
        """
        if not self.enabled or not self.client:
            return

        try:
            log_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "level": level,
                "message": message
            }

            if metadata:
                log_entry["metadata"] = metadata

            event = {
                'timestamp': int(datetime.utcnow().timestamp() * 1000),
                'message': json.dumps(log_entry)
            }

            kwargs = {
                'logGroupName': self.log_group_name,
                'logStreamName': self.log_stream_name,
                'logEvents': [event]
            }

            if self.sequence_token:
                kwargs['sequenceToken'] = self.sequence_token

            response = self.client.put_log_events(**kwargs)
            self.sequence_token = response.get('nextSequenceToken')

        except Exception as e:
            logger.warning(f"Failed to log event to CloudWatch: {e}")

    def log_api_request(
        self,
        request_id: str,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None
    ):
        """
        Log API request to CloudWatch.

        Args:
            request_id: Unique request ID
            method: HTTP method
            path: Request path
            status_code: Response status code
            duration_ms: Request duration in milliseconds
            user_agent: User agent string
            ip_address: Client IP address
        """
        metadata = {
            "request_id": request_id,
            "method": method,
            "path": path,
            "status_code": status_code,
            "duration_ms": duration_ms
        }

        if user_agent:
            metadata["user_agent"] = user_agent
        if ip_address:
            metadata["ip_address"] = ip_address

        self.log_event(
            f"API Request: {method} {path} - {status_code} ({duration_ms:.2f}ms)",
            level="INFO",
            metadata=metadata
        )

    def log_search_query(
        self,
        query: str,
        search_type: str,
        num_results: int,
        search_time_ms: float,
        reranked: bool = False
    ):
        """
        Log search query to CloudWatch.

        Args:
            query: Search query
            search_type: Type of search (semantic, lexical, hybrid)
            num_results: Number of results returned
            search_time_ms: Search duration in milliseconds
            reranked: Whether results were reranked
        """
        metadata = {
            "query": query,
            "search_type": search_type,
            "num_results": num_results,
            "search_time_ms": search_time_ms,
            "reranked": reranked
        }

        self.log_event(
            f"Search Query: {search_type} - {num_results} results in {search_time_ms:.2f}ms",
            level="INFO",
            metadata=metadata
        )

    def log_rag_query(
        self,
        query: str,
        model_used: str,
        total_time_ms: float,
        num_chunks_retrieved: int,
        num_chunks_used: int,
        input_tokens: int,
        output_tokens: int,
        fallback_used: bool,
        validated: bool
    ):
        """
        Log RAG query to CloudWatch.

        Args:
            query: User query
            model_used: LLM model used
            total_time_ms: Total query duration in milliseconds
            num_chunks_retrieved: Number of chunks retrieved
            num_chunks_used: Number of chunks used
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            fallback_used: Whether fallback was used
            validated: Whether response passed validation
        """
        metadata = {
            "query": query,
            "model_used": model_used,
            "total_time_ms": total_time_ms,
            "num_chunks_retrieved": num_chunks_retrieved,
            "num_chunks_used": num_chunks_used,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "fallback_used": fallback_used,
            "validated": validated
        }

        self.log_event(
            f"RAG Query: {model_used} - {total_time_ms:.2f}ms, {input_tokens + output_tokens} tokens",
            level="INFO",
            metadata=metadata
        )

    def log_error(
        self,
        error_type: str,
        error_message: str,
        stack_trace: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Log error to CloudWatch.

        Args:
            error_type: Type/class of error
            error_message: Error message
            stack_trace: Stack trace
            metadata: Additional metadata
        """
        error_metadata = {
            "error_type": error_type,
            "error_message": error_message
        }

        if stack_trace:
            error_metadata["stack_trace"] = stack_trace

        if metadata:
            error_metadata.update(metadata)

        self.log_event(
            f"Error: {error_type} - {error_message}",
            level="ERROR",
            metadata=error_metadata
        )


class CloudWatchMetrics:
    """Publisher for custom metrics to AWS CloudWatch."""

    def __init__(
        self,
        namespace: str = "HybridSearchRAG",
        region: str = "us-east-1",
        enabled: bool = True
    ):
        """
        Initialize CloudWatch metrics publisher.

        Args:
            namespace: CloudWatch metrics namespace
            region: AWS region
            enabled: Whether metrics publishing is enabled
        """
        self.namespace = namespace
        self.region = region
        self.enabled = enabled and BOTO3_AVAILABLE
        self.client = None

        if self.enabled:
            try:
                self.client = boto3.client('cloudwatch', region_name=region)
                logger.info(f"CloudWatch metrics initialized: {namespace}")
            except NoCredentialsError:
                logger.warning("AWS credentials not found. CloudWatch metrics disabled.")
                self.enabled = False
            except Exception as e:
                logger.warning(f"Failed to initialize CloudWatch metrics: {e}. Metrics disabled.")
                self.enabled = False

    def put_metric(
        self,
        metric_name: str,
        value: float,
        unit: str = "None",
        dimensions: Optional[List[Dict[str, str]]] = None
    ):
        """
        Put a single metric to CloudWatch.

        Args:
            metric_name: Name of the metric
            value: Metric value
            unit: Metric unit (Seconds, Milliseconds, Count, etc.)
            dimensions: Metric dimensions
        """
        if not self.enabled or not self.client:
            return

        try:
            metric_data = {
                'MetricName': metric_name,
                'Value': value,
                'Unit': unit,
                'Timestamp': datetime.utcnow()
            }

            if dimensions:
                metric_data['Dimensions'] = dimensions

            self.client.put_metric_data(
                Namespace=self.namespace,
                MetricData=[metric_data]
            )

        except Exception as e:
            logger.warning(f"Failed to put metric to CloudWatch: {e}")

    def put_search_latency(self, latency_ms: float, search_type: str):
        """
        Put search latency metric.

        Args:
            latency_ms: Search latency in milliseconds
            search_type: Type of search (semantic, lexical, hybrid)
        """
        self.put_metric(
            metric_name="SearchLatency",
            value=latency_ms,
            unit="Milliseconds",
            dimensions=[{"Name": "SearchType", "Value": search_type}]
        )

    def put_rag_latency(self, latency_ms: float, model: str):
        """
        Put RAG query latency metric.

        Args:
            latency_ms: Query latency in milliseconds
            model: LLM model used
        """
        self.put_metric(
            metric_name="RAGLatency",
            value=latency_ms,
            unit="Milliseconds",
            dimensions=[{"Name": "Model", "Value": model}]
        )

    def put_token_usage(self, tokens: int, model: str, token_type: str):
        """
        Put token usage metric.

        Args:
            tokens: Number of tokens
            model: LLM model
            token_type: Type of tokens (input, output, total)
        """
        self.put_metric(
            metric_name="TokenUsage",
            value=tokens,
            unit="Count",
            dimensions=[
                {"Name": "Model", "Value": model},
                {"Name": "TokenType", "Value": token_type}
            ]
        )

    def put_cache_hit(self, hit: bool):
        """
        Put cache hit/miss metric.

        Args:
            hit: Whether cache was hit
        """
        self.put_metric(
            metric_name="CacheHitRate",
            value=1.0 if hit else 0.0,
            unit="None"
        )

    def put_error_count(self, error_type: str):
        """
        Put error count metric.

        Args:
            error_type: Type of error
        """
        self.put_metric(
            metric_name="ErrorCount",
            value=1.0,
            unit="Count",
            dimensions=[{"Name": "ErrorType", "Value": error_type}]
        )


# Global instances
_cloudwatch_logger: Optional[CloudWatchLogger] = None
_cloudwatch_metrics: Optional[CloudWatchMetrics] = None


def get_cloudwatch_logger() -> Optional[CloudWatchLogger]:
    """
    Get global CloudWatch logger instance.

    Returns:
        CloudWatchLogger: Global logger instance or None
    """
    global _cloudwatch_logger
    if _cloudwatch_logger is None:
        # Initialize with disabled state by default
        _cloudwatch_logger = CloudWatchLogger(enabled=False)
    return _cloudwatch_logger


def get_cloudwatch_metrics() -> Optional[CloudWatchMetrics]:
    """
    Get global CloudWatch metrics instance.

    Returns:
        CloudWatchMetrics: Global metrics instance or None
    """
    global _cloudwatch_metrics
    if _cloudwatch_metrics is None:
        # Initialize with disabled state by default
        _cloudwatch_metrics = CloudWatchMetrics(enabled=False)
    return _cloudwatch_metrics


def initialize_cloudwatch(
    log_group_name: str = "/aws/hybrid-search-rag",
    log_stream_name: Optional[str] = None,
    metrics_namespace: str = "HybridSearchRAG",
    region: str = "us-east-1",
    enabled: bool = True
):
    """
    Initialize CloudWatch logging and metrics.

    Args:
        log_group_name: CloudWatch log group name
        log_stream_name: CloudWatch log stream name
        metrics_namespace: CloudWatch metrics namespace
        region: AWS region
        enabled: Whether CloudWatch is enabled
    """
    global _cloudwatch_logger, _cloudwatch_metrics

    _cloudwatch_logger = CloudWatchLogger(
        log_group_name=log_group_name,
        log_stream_name=log_stream_name,
        region=region,
        enabled=enabled
    )

    _cloudwatch_metrics = CloudWatchMetrics(
        namespace=metrics_namespace,
        region=region,
        enabled=enabled
    )

    return _cloudwatch_logger, _cloudwatch_metrics
