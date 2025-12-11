"""BGE embeddings using sentence-transformers."""

import asyncio
import hashlib
import time
from typing import Optional, Union, List, Dict, Any
from pathlib import Path

import numpy as np
import torch
from sentence_transformers import SentenceTransformer
from loguru import logger

from src.core.exceptions import EmbeddingError
from src.core.config import Settings


class EmbeddingCache:
    """In-memory cache for embeddings."""

    def __init__(self, max_size: int = 10000, ttl_seconds: int = 3600):
        """
        Initialize embedding cache.

        Args:
            max_size: Maximum number of cached embeddings
            ttl_seconds: Time-to-live for cache entries in seconds
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, tuple[np.ndarray, float]] = {}
        logger.info(f"Initialized EmbeddingCache (max_size={max_size}, ttl={ttl_seconds}s)")

    def _hash_text(self, text: str) -> str:
        """Generate hash key for text."""
        return hashlib.sha256(text.encode()).hexdigest()

    def get(self, text: str) -> Optional[np.ndarray]:
        """
        Get embedding from cache.

        Args:
            text: Text to retrieve embedding for

        Returns:
            Cached embedding or None if not found/expired
        """
        key = self._hash_text(text)
        if key in self._cache:
            embedding, timestamp = self._cache[key]
            # Check if entry has expired
            if time.time() - timestamp < self.ttl_seconds:
                logger.debug(f"Cache hit for text (hash: {key[:8]}...)")
                return embedding
            else:
                # Remove expired entry
                del self._cache[key]
                logger.debug(f"Cache entry expired (hash: {key[:8]}...)")
        return None

    def set(self, text: str, embedding: np.ndarray) -> None:
        """
        Store embedding in cache.

        Args:
            text: Text key
            embedding: Embedding to cache
        """
        # Evict oldest entries if cache is full
        if len(self._cache) >= self.max_size:
            # Remove oldest 10% of entries
            to_remove = int(self.max_size * 0.1)
            sorted_items = sorted(self._cache.items(), key=lambda x: x[1][1])
            for key, _ in sorted_items[:to_remove]:
                del self._cache[key]
            logger.debug(f"Evicted {to_remove} old cache entries")

        key = self._hash_text(text)
        self._cache[key] = (embedding, time.time())
        logger.debug(f"Cached embedding (hash: {key[:8]}...)")

    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
        logger.info("Cleared embedding cache")

    def size(self) -> int:
        """Get current cache size."""
        return len(self._cache)


class BGEEmbedder:
    """BGE embeddings generator using sentence-transformers."""

    # Query instruction for retrieval tasks
    QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "

    def __init__(
        self,
        model_name: str = "BAAI/bge-base-en-v1.5",
        device: Optional[str] = None,
        batch_size: int = 32,
        max_length: int = 512,
        normalize: bool = True,
        use_cache: bool = True,
        cache_max_size: int = 10000,
        cache_ttl: int = 3600,
        use_fp16: bool = True
    ):
        """
        Initialize BGE embedder.

        Args:
            model_name: Name of the BGE model
            device: Device to use ('cuda', 'cpu', or None for auto-detect)
            batch_size: Batch size for encoding
            max_length: Maximum sequence length
            normalize: Whether to L2 normalize embeddings
            use_cache: Whether to cache embeddings
            cache_max_size: Maximum cache size
            cache_ttl: Cache TTL in seconds
            use_fp16: Use FP16 for faster computation
        """
        self.model_name = model_name
        self.batch_size = batch_size
        self.max_length = max_length
        self.normalize = normalize
        self.use_cache = use_cache
        self.use_fp16 = use_fp16

        # Detect device
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        logger.info(f"Initializing BGEEmbedder with model: {model_name}")
        logger.info(f"Device: {self.device} (GPU available: {torch.cuda.is_available()})")

        # Initialize cache
        self.cache = EmbeddingCache(max_size=cache_max_size, ttl_seconds=cache_ttl) if use_cache else None

        # Load model
        try:
            self.model = SentenceTransformer(model_name, device=self.device)
            self.model.max_seq_length = max_length

            # Enable FP16 if using GPU
            if self.use_fp16 and self.device == "cuda":
                self.model.half()
                logger.info("Enabled FP16 mode for faster computation")

            # Get embedding dimension
            self.embedding_dim = self.model.get_sentence_embedding_dimension()
            logger.info(f"Model loaded successfully (embedding_dim={self.embedding_dim})")

        except Exception as e:
            logger.error(f"Failed to load BGE model: {e}")
            raise EmbeddingError(f"Failed to initialize BGE model: {e}")

    def embed_text(
        self,
        texts: Union[str, List[str]],
        is_query: bool = False,
        show_progress: bool = False,
        max_retries: int = 3
    ) -> np.ndarray:
        """
        Generate embeddings for text(s) synchronously.

        Args:
            texts: Single text or list of texts
            is_query: Whether texts are queries (adds instruction prefix)
            show_progress: Show progress bar for batch processing
            max_retries: Number of retries on failure

        Returns:
            Embeddings as numpy array (shape: [n_texts, embedding_dim])

        Raises:
            EmbeddingError: If embedding generation fails
        """
        # Normalize input
        if isinstance(texts, str):
            texts = [texts]
            single_text = True
        else:
            single_text = False

        # Check cache for single text
        if single_text and self.use_cache and not is_query:
            cached = self.cache.get(texts[0])
            if cached is not None:
                return cached

        # Add query instruction if needed
        if is_query:
            texts = [self.QUERY_INSTRUCTION + text for text in texts]
            logger.debug(f"Added query instruction to {len(texts)} queries")

        # Generate embeddings with retry logic
        for attempt in range(max_retries):
            try:
                start_time = time.time()

                embeddings = self.model.encode(
                    texts,
                    batch_size=self.batch_size,
                    normalize_embeddings=self.normalize,
                    show_progress_bar=show_progress,
                    convert_to_numpy=True
                )

                elapsed = time.time() - start_time
                logger.info(
                    f"Generated {len(texts)} embeddings in {elapsed:.2f}s "
                    f"({len(texts)/elapsed:.1f} texts/sec)"
                )

                # Cache single text embeddings
                if single_text and self.use_cache and not is_query:
                    self.cache.set(texts[0], embeddings)

                return embeddings

            except Exception as e:
                logger.warning(f"Embedding generation failed (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    logger.error(f"All {max_retries} embedding attempts failed")
                    raise EmbeddingError(f"Failed to generate embeddings: {e}")
                # Wait before retry
                time.sleep(2 ** attempt)  # Exponential backoff

    async def embed_text_async(
        self,
        texts: Union[str, List[str]],
        is_query: bool = False,
        show_progress: bool = False,
        max_retries: int = 3
    ) -> np.ndarray:
        """
        Generate embeddings for text(s) asynchronously.

        Args:
            texts: Single text or list of texts
            is_query: Whether texts are queries (adds instruction prefix)
            show_progress: Show progress bar for batch processing
            max_retries: Number of retries on failure

        Returns:
            Embeddings as numpy array (shape: [n_texts, embedding_dim])

        Raises:
            EmbeddingError: If embedding generation fails
        """
        # Run synchronous embedding in thread pool
        return await asyncio.to_thread(
            self.embed_text,
            texts=texts,
            is_query=is_query,
            show_progress=show_progress,
            max_retries=max_retries
        )

    def embed_queries(
        self,
        queries: Union[str, List[str]],
        show_progress: bool = False,
        max_retries: int = 3
    ) -> np.ndarray:
        """
        Generate embeddings for queries with instruction prefix.

        Args:
            queries: Query or list of queries
            show_progress: Show progress bar
            max_retries: Number of retries on failure

        Returns:
            Query embeddings
        """
        return self.embed_text(
            texts=queries,
            is_query=True,
            show_progress=show_progress,
            max_retries=max_retries
        )

    async def embed_queries_async(
        self,
        queries: Union[str, List[str]],
        show_progress: bool = False,
        max_retries: int = 3
    ) -> np.ndarray:
        """
        Generate embeddings for queries asynchronously with instruction prefix.

        Args:
            queries: Query or list of queries
            show_progress: Show progress bar
            max_retries: Number of retries on failure

        Returns:
            Query embeddings
        """
        return await self.embed_text_async(
            texts=queries,
            is_query=True,
            show_progress=show_progress,
            max_retries=max_retries
        )

    def embed_documents(
        self,
        documents: Union[str, List[str]],
        show_progress: bool = False,
        max_retries: int = 3
    ) -> np.ndarray:
        """
        Generate embeddings for documents (no instruction prefix).

        Args:
            documents: Document or list of documents
            show_progress: Show progress bar
            max_retries: Number of retries on failure

        Returns:
            Document embeddings
        """
        return self.embed_text(
            texts=documents,
            is_query=False,
            show_progress=show_progress,
            max_retries=max_retries
        )

    async def embed_documents_async(
        self,
        documents: Union[str, List[str]],
        show_progress: bool = False,
        max_retries: int = 3
    ) -> np.ndarray:
        """
        Generate embeddings for documents asynchronously (no instruction prefix).

        Args:
            documents: Document or list of documents
            show_progress: Show progress bar
            max_retries: Number of retries on failure

        Returns:
            Document embeddings
        """
        return await self.embed_text_async(
            texts=documents,
            is_query=False,
            show_progress=show_progress,
            max_retries=max_retries
        )

    def compute_similarity(
        self,
        embeddings1: np.ndarray,
        embeddings2: np.ndarray
    ) -> np.ndarray:
        """
        Compute cosine similarity between embeddings.

        For L2 normalized embeddings, this is simply the dot product.

        Args:
            embeddings1: First set of embeddings (shape: [n, dim])
            embeddings2: Second set of embeddings (shape: [m, dim])

        Returns:
            Similarity matrix (shape: [n, m])
        """
        # For L2 normalized vectors, cosine similarity = dot product
        return embeddings1 @ embeddings2.T

    def get_embedding_dimension(self) -> int:
        """Get embedding dimension."""
        return self.embedding_dim

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        if not self.use_cache:
            return {"enabled": False}

        return {
            "enabled": True,
            "size": self.cache.size(),
            "max_size": self.cache.max_size,
            "ttl_seconds": self.cache.ttl_seconds
        }

    def clear_cache(self) -> None:
        """Clear embedding cache."""
        if self.use_cache:
            self.cache.clear()

    def __repr__(self) -> str:
        return (
            f"BGEEmbedder(model={self.model_name}, device={self.device}, "
            f"dim={self.embedding_dim}, normalize={self.normalize})"
        )


def create_embedder_from_config(config: Settings) -> BGEEmbedder:
    """
    Create BGE embedder from config.

    Args:
        config: Application settings

    Returns:
        Initialized BGE embedder
    """
    return BGEEmbedder(
        model_name=config.embedding_model,
        device=None,  # Auto-detect
        batch_size=config.embedding_batch_size,
        max_length=config.embedding_max_length,
        normalize=True,
        use_cache=True,
        cache_max_size=10000,
        cache_ttl=3600,
        use_fp16=True
    )
