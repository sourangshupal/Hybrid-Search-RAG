"""Rate limiting utilities for API requests."""

import asyncio
import time
from collections import deque
from typing import Optional, Callable, TypeVar, ParamSpec
from dataclasses import dataclass
from functools import wraps

from loguru import logger

P = ParamSpec('P')
T = TypeVar('T')


@dataclass
class RateLimiterConfig:
    """Configuration for rate limiter."""

    max_requests: int  # Maximum requests allowed
    time_window: float  # Time window in seconds
    burst_size: Optional[int] = None  # Allow bursts up to this size


class RateLimiter:
    """
    Token bucket rate limiter for controlling request rates.

    Uses token bucket algorithm with optional burst handling.
    """

    def __init__(
        self,
        name: str,
        max_requests: int,
        time_window: float = 1.0,
        burst_size: Optional[int] = None
    ):
        """
        Initialize rate limiter.

        Args:
            name: Name for this rate limiter
            max_requests: Maximum requests allowed in time window
            time_window: Time window in seconds
            burst_size: Optional burst size (defaults to max_requests)
        """
        self.name = name
        self.max_requests = max_requests
        self.time_window = time_window
        self.burst_size = burst_size or max_requests

        # Token bucket
        self.tokens = float(self.burst_size)
        self.last_update = time.time()

        # Statistics
        self.total_requests = 0
        self.rejected_requests = 0
        self.total_wait_time = 0.0

        # Lock for thread safety
        self._lock = asyncio.Lock()

        logger.info(
            f"Initialized RateLimiter '{name}' "
            f"({max_requests} req/{time_window}s, burst={self.burst_size})"
        )

    async def acquire(self, tokens: float = 1.0, wait: bool = True) -> bool:
        """
        Acquire tokens from the bucket.

        Args:
            tokens: Number of tokens to acquire
            wait: Whether to wait if tokens not available

        Returns:
            True if tokens acquired, False if rejected (when wait=False)

        Raises:
            RateLimitExceededError: If wait=False and tokens not available
        """
        async with self._lock:
            self._refill_tokens()
            self.total_requests += 1

            if self.tokens >= tokens:
                # Tokens available, consume them
                self.tokens -= tokens
                return True

            if not wait:
                # Don't wait, reject request
                self.rejected_requests += 1
                logger.warning(
                    f"Rate limit exceeded for '{self.name}' "
                    f"(tokens={self.tokens:.2f}, needed={tokens})"
                )
                raise RateLimitExceededError(
                    f"Rate limit exceeded for '{self.name}'. "
                    f"Try again later."
                )

        # Wait for tokens to be available
        wait_time = self._calculate_wait_time(tokens)
        logger.debug(
            f"Rate limiting '{self.name}': waiting {wait_time:.2f}s for {tokens} tokens"
        )

        self.total_wait_time += wait_time
        await asyncio.sleep(wait_time)

        # Try again after waiting
        async with self._lock:
            self._refill_tokens()
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            else:
                # Still not enough tokens (shouldn't happen)
                self.rejected_requests += 1
                raise RateLimitExceededError(
                    f"Rate limit exceeded for '{self.name}' after waiting"
                )

    def _refill_tokens(self):
        """Refill tokens based on time elapsed."""
        now = time.time()
        elapsed = now - self.last_update

        # Calculate tokens to add
        # tokens_per_second = max_requests / time_window
        tokens_to_add = (self.max_requests / self.time_window) * elapsed

        # Update tokens (capped at burst_size)
        self.tokens = min(self.burst_size, self.tokens + tokens_to_add)
        self.last_update = now

    def _calculate_wait_time(self, tokens: float) -> float:
        """
        Calculate time to wait for tokens to be available.

        Args:
            tokens: Number of tokens needed

        Returns:
            Wait time in seconds
        """
        tokens_needed = tokens - self.tokens
        if tokens_needed <= 0:
            return 0.0

        # Calculate time needed to accumulate tokens
        tokens_per_second = self.max_requests / self.time_window
        wait_time = tokens_needed / tokens_per_second

        return wait_time

    async def __aenter__(self):
        """Context manager entry."""
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        return False

    def get_stats(self) -> dict:
        """
        Get rate limiter statistics.

        Returns:
            Dictionary with stats
        """
        rejection_rate = (
            self.rejected_requests / self.total_requests * 100
            if self.total_requests > 0 else 0.0
        )
        avg_wait_time = (
            self.total_wait_time / self.total_requests
            if self.total_requests > 0 else 0.0
        )

        return {
            "name": self.name,
            "max_requests": self.max_requests,
            "time_window": self.time_window,
            "burst_size": self.burst_size,
            "current_tokens": round(self.tokens, 2),
            "total_requests": self.total_requests,
            "rejected_requests": self.rejected_requests,
            "rejection_rate": round(rejection_rate, 2),
            "total_wait_time": round(self.total_wait_time, 2),
            "avg_wait_time": round(avg_wait_time, 4)
        }

    def reset(self):
        """Reset rate limiter statistics."""
        self.tokens = float(self.burst_size)
        self.last_update = time.time()
        self.total_requests = 0
        self.rejected_requests = 0
        self.total_wait_time = 0.0
        logger.info(f"Reset rate limiter '{self.name}'")


class RateLimitExceededError(Exception):
    """Raised when rate limit is exceeded."""
    pass


def rate_limit(
    name: str,
    max_requests: int,
    time_window: float = 1.0,
    burst_size: Optional[int] = None,
    wait: bool = True
):
    """
    Decorator for rate limiting functions.

    Args:
        name: Rate limiter name
        max_requests: Maximum requests in time window
        time_window: Time window in seconds
        burst_size: Optional burst size
        wait: Whether to wait when rate limit hit

    Example:
        @rate_limit("openai_api", max_requests=10, time_window=60)
        async def call_openai():
            return await client.completions.create(...)
    """
    limiter = RateLimiter(name, max_requests, time_window, burst_size)

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            await limiter.acquire(wait=wait)
            return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            async def _async_call():
                await limiter.acquire(wait=wait)
                return func(*args, **kwargs)

            return asyncio.run(_async_call())

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


class SlidingWindowRateLimiter:
    """
    Sliding window rate limiter using timestamp queue.

    More accurate than token bucket but uses more memory.
    """

    def __init__(
        self,
        name: str,
        max_requests: int,
        time_window: float = 1.0
    ):
        """
        Initialize sliding window rate limiter.

        Args:
            name: Name for this rate limiter
            max_requests: Maximum requests in time window
            time_window: Time window in seconds
        """
        self.name = name
        self.max_requests = max_requests
        self.time_window = time_window

        # Queue of request timestamps
        self.requests: deque = deque()

        # Statistics
        self.total_requests = 0
        self.rejected_requests = 0

        # Lock for thread safety
        self._lock = asyncio.Lock()

        logger.info(
            f"Initialized SlidingWindowRateLimiter '{name}' "
            f"({max_requests} req/{time_window}s)"
        )

    async def acquire(self, wait: bool = True) -> bool:
        """
        Acquire permission to make request.

        Args:
            wait: Whether to wait if rate limit hit

        Returns:
            True if acquired, False if rejected

        Raises:
            RateLimitExceededError: If wait=False and limit hit
        """
        async with self._lock:
            now = time.time()
            self.total_requests += 1

            # Remove expired timestamps
            cutoff = now - self.time_window
            while self.requests and self.requests[0] < cutoff:
                self.requests.popleft()

            # Check if under limit
            if len(self.requests) < self.max_requests:
                self.requests.append(now)
                return True

            if not wait:
                self.rejected_requests += 1
                raise RateLimitExceededError(
                    f"Rate limit exceeded for '{self.name}'"
                )

        # Calculate wait time
        wait_time = self.requests[0] + self.time_window - now + 0.001  # Add small buffer

        logger.debug(
            f"Rate limiting '{self.name}': waiting {wait_time:.2f}s"
        )
        await asyncio.sleep(wait_time)

        # Try again
        return await self.acquire(wait=False)

    def get_stats(self) -> dict:
        """Get rate limiter statistics."""
        rejection_rate = (
            self.rejected_requests / self.total_requests * 100
            if self.total_requests > 0 else 0.0
        )

        return {
            "name": self.name,
            "max_requests": self.max_requests,
            "time_window": self.time_window,
            "current_requests": len(self.requests),
            "total_requests": self.total_requests,
            "rejected_requests": self.rejected_requests,
            "rejection_rate": round(rejection_rate, 2)
        }


class RateLimiterManager:
    """Manager for multiple rate limiters."""

    def __init__(self):
        """Initialize rate limiter manager."""
        self._limiters: dict[str, RateLimiter] = {}

    def get_or_create(
        self,
        name: str,
        max_requests: int,
        time_window: float = 1.0,
        burst_size: Optional[int] = None
    ) -> RateLimiter:
        """
        Get existing or create new rate limiter.

        Args:
            name: Rate limiter name
            max_requests: Maximum requests in time window
            time_window: Time window in seconds
            burst_size: Optional burst size

        Returns:
            RateLimiter instance
        """
        if name not in self._limiters:
            self._limiters[name] = RateLimiter(
                name, max_requests, time_window, burst_size
            )
        return self._limiters[name]

    def get(self, name: str) -> Optional[RateLimiter]:
        """
        Get rate limiter by name.

        Args:
            name: Rate limiter name

        Returns:
            RateLimiter or None if not found
        """
        return self._limiters.get(name)

    def get_all_stats(self) -> dict[str, dict]:
        """
        Get statistics for all rate limiters.

        Returns:
            Dictionary mapping limiter names to stats
        """
        return {
            name: limiter.get_stats()
            for name, limiter in self._limiters.items()
        }

    def reset_all(self):
        """Reset all rate limiters."""
        for limiter in self._limiters.values():
            limiter.reset()
        logger.info("Reset all rate limiters")


# Global rate limiter manager
_manager = RateLimiterManager()


def get_rate_limiter_manager() -> RateLimiterManager:
    """
    Get global rate limiter manager.

    Returns:
        RateLimiterManager instance
    """
    return _manager
