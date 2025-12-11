"""Redis caching utilities."""

import json
from typing import Any, Optional
from datetime import timedelta

import redis.asyncio as aioredis
from loguru import logger

from src.core.exceptions import CacheError, RedisConnectionError


class RedisCache:
    """Async Redis cache wrapper."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        default_ttl: int = 3600,
        key_prefix: str = "hybrid_rag:"
    ):
        """
        Initialize Redis cache.

        Args:
            host: Redis host
            port: Redis port
            db: Redis database number
            password: Redis password (optional)
            default_ttl: Default TTL in seconds
            key_prefix: Prefix for all cache keys
        """
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.default_ttl = default_ttl
        self.key_prefix = key_prefix
        self.client: Optional[aioredis.Redis] = None

        logger.info(f"Initialized RedisCache ({host}:{port}, db={db})")

    async def connect(self) -> None:
        """
        Connect to Redis.

        Raises:
            RedisConnectionError: If connection fails
        """
        try:
            self.client = await aioredis.from_url(
                f"redis://{self.host}:{self.port}/{self.db}",
                password=self.password,
                encoding="utf-8",
                decode_responses=True
            )

            # Test connection
            await self.client.ping()
            logger.info("Successfully connected to Redis")

        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise RedisConnectionError(f"Failed to connect to Redis: {e}")

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self.client:
            await self.client.close()
            logger.info("Disconnected from Redis")

    def _make_key(self, key: str) -> str:
        """
        Create full cache key with prefix.

        Args:
            key: Base key

        Returns:
            Full key with prefix
        """
        return f"{self.key_prefix}{key}"

    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found

        Raises:
            CacheError: If cache operation fails
        """
        if not self.client:
            logger.warning("Redis client not connected")
            return None

        try:
            full_key = self._make_key(key)
            value = await self.client.get(full_key)

            if value is None:
                logger.debug(f"Cache miss: {key}")
                return None

            # Deserialize JSON
            try:
                deserialized = json.loads(value)
                logger.debug(f"Cache hit: {key}")
                return deserialized
            except json.JSONDecodeError:
                # Return as-is if not JSON
                logger.debug(f"Cache hit (non-JSON): {key}")
                return value

        except Exception as e:
            logger.error(f"Cache get failed for key '{key}': {e}")
            raise CacheError(f"Failed to get from cache: {e}")

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (None = use default)

        Returns:
            True if successful

        Raises:
            CacheError: If cache operation fails
        """
        if not self.client:
            logger.warning("Redis client not connected")
            return False

        try:
            full_key = self._make_key(key)
            ttl = ttl or self.default_ttl

            # Serialize to JSON if not string
            if isinstance(value, (dict, list, tuple)):
                serialized = json.dumps(value)
            else:
                serialized = str(value)

            # Set with TTL
            await self.client.setex(
                full_key,
                timedelta(seconds=ttl),
                serialized
            )

            logger.debug(f"Cached: {key} (TTL={ttl}s)")
            return True

        except Exception as e:
            logger.error(f"Cache set failed for key '{key}': {e}")
            raise CacheError(f"Failed to set in cache: {e}")

    async def delete(self, key: str) -> bool:
        """
        Delete key from cache.

        Args:
            key: Cache key

        Returns:
            True if deleted, False if not found

        Raises:
            CacheError: If cache operation fails
        """
        if not self.client:
            logger.warning("Redis client not connected")
            return False

        try:
            full_key = self._make_key(key)
            result = await self.client.delete(full_key)

            if result:
                logger.debug(f"Deleted from cache: {key}")
                return True
            else:
                logger.debug(f"Cache key not found: {key}")
                return False

        except Exception as e:
            logger.error(f"Cache delete failed for key '{key}': {e}")
            raise CacheError(f"Failed to delete from cache: {e}")

    async def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.

        Args:
            key: Cache key

        Returns:
            True if exists

        Raises:
            CacheError: If cache operation fails
        """
        if not self.client:
            return False

        try:
            full_key = self._make_key(key)
            result = await self.client.exists(full_key)
            return bool(result)

        except Exception as e:
            logger.error(f"Cache exists check failed for key '{key}': {e}")
            raise CacheError(f"Failed to check cache existence: {e}")

    async def clear_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching pattern.

        Args:
            pattern: Key pattern (e.g., "user:*")

        Returns:
            Number of keys deleted

        Raises:
            CacheError: If cache operation fails
        """
        if not self.client:
            return 0

        try:
            full_pattern = self._make_key(pattern)
            keys = await self.client.keys(full_pattern)

            if not keys:
                return 0

            deleted = await self.client.delete(*keys)
            logger.info(f"Cleared {deleted} keys matching pattern: {pattern}")
            return deleted

        except Exception as e:
            logger.error(f"Cache clear pattern failed for '{pattern}': {e}")
            raise CacheError(f"Failed to clear cache pattern: {e}")

    async def get_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats

        Raises:
            CacheError: If operation fails
        """
        if not self.client:
            return {}

        try:
            info = await self.client.info("stats")
            return {
                "total_commands_processed": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "hit_rate": self._calculate_hit_rate(
                    info.get("keyspace_hits", 0),
                    info.get("keyspace_misses", 0)
                )
            }

        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            raise CacheError(f"Failed to get cache stats: {e}")

    @staticmethod
    def _calculate_hit_rate(hits: int, misses: int) -> float:
        """Calculate cache hit rate."""
        total = hits + misses
        if total == 0:
            return 0.0
        return (hits / total) * 100

    def __repr__(self) -> str:
        return f"RedisCache({self.host}:{self.port}, db={self.db})"


# Global cache instance (initialized in main.py)
cache: Optional[RedisCache] = None


def get_cache() -> Optional[RedisCache]:
    """
    Get global cache instance.

    Returns:
        RedisCache instance or None if not initialized
    """
    return cache
