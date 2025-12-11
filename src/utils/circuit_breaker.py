"""Circuit breaker pattern for external service calls."""

import asyncio
import time
from enum import Enum
from typing import Callable, Any, Optional, TypeVar, ParamSpec
from dataclasses import dataclass, field
from functools import wraps

from loguru import logger

P = ParamSpec('P')
T = TypeVar('T')


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, rejecting requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""

    failure_threshold: int = 5  # Failures before opening
    success_threshold: int = 2  # Successes in half-open before closing
    timeout_seconds: float = 60.0  # Time to wait before half-open
    half_open_timeout: float = 30.0  # Time to wait in half-open
    expected_exception: type = Exception  # Exception type to catch


@dataclass
class CircuitBreakerStats:
    """Statistics for circuit breaker."""

    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[float] = None
    opened_at: Optional[float] = None
    total_calls: int = 0
    total_failures: int = 0
    total_successes: int = 0


class CircuitBreaker:
    """
    Circuit breaker for protecting against cascading failures.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, requests are rejected
    - HALF_OPEN: Testing if service recovered, limited requests allowed
    """

    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None
    ):
        """
        Initialize circuit breaker.

        Args:
            name: Name for this circuit breaker
            config: Configuration options
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.stats = CircuitBreakerStats()
        self._lock = asyncio.Lock()

        logger.info(
            f"Initialized CircuitBreaker '{name}' "
            f"(failure_threshold={self.config.failure_threshold}, "
            f"timeout={self.config.timeout_seconds}s)"
        )

    async def call(
        self,
        func: Callable[P, T],
        *args: P.args,
        **kwargs: P.kwargs
    ) -> T:
        """
        Execute function with circuit breaker protection.

        Args:
            func: Function to call
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerOpenError: If circuit is open
            Exception: Original exception from function
        """
        async with self._lock:
            self._check_state()

            if self.stats.state == CircuitState.OPEN:
                logger.warning(f"Circuit '{self.name}' is OPEN, rejecting request")
                raise CircuitBreakerOpenError(
                    f"Circuit breaker '{self.name}' is OPEN. "
                    f"Too many failures ({self.stats.total_failures}). "
                    f"Try again after {self.config.timeout_seconds}s."
                )

        # Execute function
        try:
            self.stats.total_calls += 1

            # Call function (handle both sync and async)
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            # Record success
            await self._on_success()
            return result

        except self.config.expected_exception as e:
            # Record failure
            await self._on_failure()
            raise

    def _check_state(self):
        """Check and update circuit state based on time."""
        current_time = time.time()

        if self.stats.state == CircuitState.OPEN:
            # Check if timeout has passed
            if (self.stats.opened_at and
                current_time - self.stats.opened_at >= self.config.timeout_seconds):
                logger.info(f"Circuit '{self.name}' transitioning to HALF_OPEN")
                self.stats.state = CircuitState.HALF_OPEN
                self.stats.success_count = 0
                self.stats.failure_count = 0

    async def _on_success(self):
        """Handle successful call."""
        async with self._lock:
            self.stats.total_successes += 1
            self.stats.success_count += 1

            if self.stats.state == CircuitState.HALF_OPEN:
                # Check if enough successes to close circuit
                if self.stats.success_count >= self.config.success_threshold:
                    logger.info(
                        f"Circuit '{self.name}' transitioning to CLOSED "
                        f"after {self.stats.success_count} successes"
                    )
                    self.stats.state = CircuitState.CLOSED
                    self.stats.failure_count = 0
                    self.stats.success_count = 0

    async def _on_failure(self):
        """Handle failed call."""
        async with self._lock:
            self.stats.total_failures += 1
            self.stats.failure_count += 1
            self.stats.last_failure_time = time.time()

            if self.stats.state == CircuitState.HALF_OPEN:
                # Immediately open on failure in half-open
                logger.warning(
                    f"Circuit '{self.name}' transitioning to OPEN "
                    f"(failure in HALF_OPEN state)"
                )
                self.stats.state = CircuitState.OPEN
                self.stats.opened_at = time.time()

            elif self.stats.state == CircuitState.CLOSED:
                # Check if failure threshold exceeded
                if self.stats.failure_count >= self.config.failure_threshold:
                    logger.warning(
                        f"Circuit '{self.name}' transitioning to OPEN "
                        f"after {self.stats.failure_count} failures"
                    )
                    self.stats.state = CircuitState.OPEN
                    self.stats.opened_at = time.time()

    def get_stats(self) -> dict:
        """
        Get circuit breaker statistics.

        Returns:
            Dictionary with stats
        """
        return {
            "name": self.name,
            "state": self.stats.state.value,
            "total_calls": self.stats.total_calls,
            "total_successes": self.stats.total_successes,
            "total_failures": self.stats.total_failures,
            "success_rate": (
                self.stats.total_successes / self.stats.total_calls * 100
                if self.stats.total_calls > 0 else 0.0
            ),
            "failure_count": self.stats.failure_count,
            "success_count": self.stats.success_count,
            "last_failure_time": self.stats.last_failure_time
        }

    def reset(self):
        """Reset circuit breaker to closed state."""
        self.stats = CircuitBreakerStats()
        logger.info(f"Reset circuit breaker '{self.name}'")


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass


def circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    success_threshold: int = 2,
    timeout_seconds: float = 60.0
):
    """
    Decorator for applying circuit breaker to functions.

    Args:
        name: Circuit breaker name
        failure_threshold: Failures before opening
        success_threshold: Successes in half-open before closing
        timeout_seconds: Time to wait before half-open

    Example:
        @circuit_breaker("external_api", failure_threshold=3)
        async def call_api():
            return await client.get("/endpoint")
    """
    config = CircuitBreakerConfig(
        failure_threshold=failure_threshold,
        success_threshold=success_threshold,
        timeout_seconds=timeout_seconds
    )
    breaker = CircuitBreaker(name, config)

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            return await breaker.call(func, *args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            # For sync functions, wrap in async
            async def _async_call():
                return await breaker.call(func, *args, **kwargs)

            return asyncio.run(_async_call())

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


class CircuitBreakerManager:
    """Manager for multiple circuit breakers."""

    def __init__(self):
        """Initialize circuit breaker manager."""
        self._breakers: dict[str, CircuitBreaker] = {}

    def get_or_create(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None
    ) -> CircuitBreaker:
        """
        Get existing or create new circuit breaker.

        Args:
            name: Circuit breaker name
            config: Configuration for new breaker

        Returns:
            CircuitBreaker instance
        """
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(name, config)
        return self._breakers[name]

    def get(self, name: str) -> Optional[CircuitBreaker]:
        """
        Get circuit breaker by name.

        Args:
            name: Circuit breaker name

        Returns:
            CircuitBreaker or None if not found
        """
        return self._breakers.get(name)

    def get_all_stats(self) -> dict[str, dict]:
        """
        Get statistics for all circuit breakers.

        Returns:
            Dictionary mapping breaker names to stats
        """
        return {
            name: breaker.get_stats()
            for name, breaker in self._breakers.items()
        }

    def reset_all(self):
        """Reset all circuit breakers."""
        for breaker in self._breakers.values():
            breaker.reset()
        logger.info("Reset all circuit breakers")


# Global circuit breaker manager
_manager = CircuitBreakerManager()


def get_circuit_breaker_manager() -> CircuitBreakerManager:
    """
    Get global circuit breaker manager.

    Returns:
        CircuitBreakerManager instance
    """
    return _manager
