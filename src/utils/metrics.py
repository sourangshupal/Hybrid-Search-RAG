"""Metrics collection utilities."""

import time
from typing import Dict, Any, Optional
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime

from loguru import logger


@dataclass
class MetricsCollector:
    """Collects application metrics."""

    # Request counters
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0

    # Endpoint counters
    endpoint_counts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))

    # Search metrics
    search_queries: int = 0
    avg_search_time_ms: float = 0.0
    search_times: list = field(default_factory=list)

    # RAG metrics
    rag_queries: int = 0
    avg_rag_time_ms: float = 0.0
    rag_times: list = field(default_factory=list)
    claude_usage: int = 0
    openai_usage: int = 0
    fallback_usage: int = 0

    # Token usage
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0

    # Start time
    start_time: float = field(default_factory=time.time)

    def record_request(self, endpoint: str, success: bool = True) -> None:
        """
        Record API request.

        Args:
            endpoint: API endpoint path
            success: Whether request succeeded
        """
        self.total_requests += 1

        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1

        self.endpoint_counts[endpoint] += 1

    def record_search(self, duration_ms: float) -> None:
        """
        Record search query.

        Args:
            duration_ms: Search duration in milliseconds
        """
        self.search_queries += 1
        self.search_times.append(duration_ms)

        # Update average
        self.avg_search_time_ms = sum(self.search_times) / len(self.search_times)

    def record_rag_query(
        self,
        duration_ms: float,
        model_used: str,
        fallback_used: bool = False,
        input_tokens: int = 0,
        output_tokens: int = 0
    ) -> None:
        """
        Record RAG query.

        Args:
            duration_ms: Query duration in milliseconds
            model_used: LLM model used
            fallback_used: Whether fallback was used
            input_tokens: Input tokens consumed
            output_tokens: Output tokens generated
        """
        self.rag_queries += 1
        self.rag_times.append(duration_ms)

        # Update average
        self.avg_rag_time_ms = sum(self.rag_times) / len(self.rag_times)

        # Track model usage
        if "claude" in model_used.lower():
            self.claude_usage += 1
        elif "gpt" in model_used.lower():
            self.openai_usage += 1

        if fallback_used:
            self.fallback_usage += 1

        # Track tokens
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_tokens += (input_tokens + output_tokens)

    def get_uptime(self) -> float:
        """
        Get uptime in seconds.

        Returns:
            Uptime in seconds
        """
        return time.time() - self.start_time

    def get_percentiles(
        self,
        values: list,
        percentiles: list = [50, 95, 99]
    ) -> Dict[str, float]:
        """
        Calculate percentiles for list of values.

        Args:
            values: List of numeric values
            percentiles: Percentiles to calculate

        Returns:
            Dictionary with percentile values
        """
        if not values:
            return {f"p{p}": 0.0 for p in percentiles}

        sorted_values = sorted(values)
        n = len(sorted_values)

        results = {}
        for p in percentiles:
            index = int((p / 100) * n)
            index = min(index, n - 1)
            results[f"p{p}"] = sorted_values[index]

        return results

    def get_summary(self) -> Dict[str, Any]:
        """
        Get metrics summary.

        Returns:
            Dictionary with all metrics
        """
        uptime = self.get_uptime()

        # Calculate percentiles
        search_percentiles = self.get_percentiles(self.search_times)
        rag_percentiles = self.get_percentiles(self.rag_times)

        return {
            "uptime_seconds": uptime,
            "uptime_formatted": self._format_uptime(uptime),
            "requests": {
                "total": self.total_requests,
                "successful": self.successful_requests,
                "failed": self.failed_requests,
                "success_rate": self._calculate_success_rate(),
                "by_endpoint": dict(self.endpoint_counts)
            },
            "search": {
                "total_queries": self.search_queries,
                "avg_time_ms": round(self.avg_search_time_ms, 2),
                **{k: round(v, 2) for k, v in search_percentiles.items()}
            },
            "rag": {
                "total_queries": self.rag_queries,
                "avg_time_ms": round(self.avg_rag_time_ms, 2),
                "claude_usage": self.claude_usage,
                "openai_usage": self.openai_usage,
                "fallback_usage": self.fallback_usage,
                "fallback_rate": self._calculate_fallback_rate(),
                **{k: round(v, 2) for k, v in rag_percentiles.items()}
            },
            "tokens": {
                "total_input": self.total_input_tokens,
                "total_output": self.total_output_tokens,
                "total": self.total_tokens,
                "avg_per_query": self._calculate_avg_tokens_per_query()
            }
        }

    def _calculate_success_rate(self) -> float:
        """Calculate request success rate."""
        if self.total_requests == 0:
            return 0.0
        return round((self.successful_requests / self.total_requests) * 100, 2)

    def _calculate_fallback_rate(self) -> float:
        """Calculate LLM fallback rate."""
        if self.rag_queries == 0:
            return 0.0
        return round((self.fallback_usage / self.rag_queries) * 100, 2)

    def _calculate_avg_tokens_per_query(self) -> int:
        """Calculate average tokens per query."""
        if self.rag_queries == 0:
            return 0
        return round(self.total_tokens / self.rag_queries)

    @staticmethod
    def _format_uptime(seconds: float) -> str:
        """Format uptime as human-readable string."""
        days, remainder = divmod(int(seconds), 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)

        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        parts.append(f"{seconds}s")

        return " ".join(parts)

    def reset(self) -> None:
        """Reset all metrics."""
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.endpoint_counts.clear()
        self.search_queries = 0
        self.avg_search_time_ms = 0.0
        self.search_times.clear()
        self.rag_queries = 0
        self.avg_rag_time_ms = 0.0
        self.rag_times.clear()
        self.claude_usage = 0
        self.openai_usage = 0
        self.fallback_usage = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_tokens = 0
        self.start_time = time.time()

        logger.info("Metrics reset")


# Global metrics instance
metrics = MetricsCollector()


def get_metrics() -> MetricsCollector:
    """
    Get global metrics instance.

    Returns:
        MetricsCollector instance
    """
    return metrics
