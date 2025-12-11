"""Unit tests for embeddings module."""

import time
import numpy as np
import pytest

from src.embeddings.bge_embedder import BGEEmbedder, EmbeddingCache
from src.core.exceptions import EmbeddingError


class TestEmbeddingCache:
    """Tests for embedding cache."""

    def test_cache_initialization(self):
        """Test cache initialization."""
        cache = EmbeddingCache(max_size=100, ttl_seconds=60)
        assert cache.max_size == 100
        assert cache.ttl_seconds == 60
        assert cache.size() == 0

    def test_cache_set_get(self):
        """Test setting and getting cache entries."""
        cache = EmbeddingCache()
        embedding = np.random.randn(768)
        text = "This is a test sentence."

        # Set cache
        cache.set(text, embedding)
        assert cache.size() == 1

        # Get cache
        cached = cache.get(text)
        assert cached is not None
        np.testing.assert_array_equal(cached, embedding)

    def test_cache_miss(self):
        """Test cache miss."""
        cache = EmbeddingCache()
        text = "This is not cached."

        cached = cache.get(text)
        assert cached is None

    def test_cache_expiration(self):
        """Test cache entry expiration."""
        cache = EmbeddingCache(ttl_seconds=1)
        embedding = np.random.randn(768)
        text = "This will expire."

        cache.set(text, embedding)
        assert cache.get(text) is not None

        # Wait for expiration
        time.sleep(1.5)
        assert cache.get(text) is None

    def test_cache_eviction(self):
        """Test cache eviction when full."""
        cache = EmbeddingCache(max_size=10)

        # Fill cache
        for i in range(10):
            cache.set(f"text_{i}", np.random.randn(768))

        assert cache.size() == 10

        # Add one more (should evict oldest)
        cache.set("text_new", np.random.randn(768))
        # Size should be 10 (evicted 1, added 1) or 9 (evicted 10%, added 1)
        assert cache.size() <= 10

    def test_cache_clear(self):
        """Test clearing cache."""
        cache = EmbeddingCache()

        for i in range(5):
            cache.set(f"text_{i}", np.random.randn(768))

        assert cache.size() == 5

        cache.clear()
        assert cache.size() == 0


class TestBGEEmbedder:
    """Tests for BGE embedder."""

    @pytest.fixture
    def embedder(self):
        """Create embedder fixture."""
        return BGEEmbedder(
            model_name="BAAI/bge-small-en-v1.5",  # Use small model for faster tests
            batch_size=4,
            max_length=128,
            use_cache=True,
            use_fp16=False  # Disable FP16 for testing
        )

    def test_embedder_initialization(self, embedder):
        """Test embedder initialization."""
        assert embedder.model is not None
        assert embedder.embedding_dim > 0
        assert embedder.device in ["cuda", "cpu"]
        assert embedder.normalize is True

    def test_single_text_embedding(self, embedder):
        """Test embedding a single text."""
        text = "This is a test sentence."
        embedding = embedder.embed_text(text)

        assert isinstance(embedding, np.ndarray)
        assert embedding.shape == (1, embedder.embedding_dim)
        assert not np.isnan(embedding).any()

        # Check normalization
        if embedder.normalize:
            norm = np.linalg.norm(embedding[0])
            assert abs(norm - 1.0) < 1e-5

    def test_batch_embedding(self, embedder):
        """Test embedding multiple texts."""
        texts = [
            "First sentence.",
            "Second sentence.",
            "Third sentence."
        ]
        embeddings = embedder.embed_text(texts)

        assert embeddings.shape == (len(texts), embedder.embedding_dim)
        assert not np.isnan(embeddings).any()

        # Check all embeddings are normalized
        if embedder.normalize:
            for embedding in embeddings:
                norm = np.linalg.norm(embedding)
                assert abs(norm - 1.0) < 1e-5

    def test_query_embedding(self, embedder):
        """Test query embedding with instruction."""
        query = "What is the capital of France?"
        embedding = embedder.embed_queries(query)

        assert embedding.shape == (1, embedder.embedding_dim)
        assert not np.isnan(embedding).any()

    def test_document_embedding(self, embedder):
        """Test document embedding without instruction."""
        document = "Paris is the capital of France."
        embedding = embedder.embed_documents(document)

        assert embedding.shape == (1, embedder.embedding_dim)
        assert not np.isnan(embedding).any()

    def test_query_vs_document_embedding(self, embedder):
        """Test that query and document embeddings differ due to instruction."""
        text = "What is machine learning?"

        query_embedding = embedder.embed_queries(text)
        doc_embedding = embedder.embed_documents(text)

        # Embeddings should be different (query has instruction prefix)
        assert not np.allclose(query_embedding, doc_embedding)

    @pytest.mark.asyncio
    async def test_async_embedding(self, embedder):
        """Test async embedding generation."""
        texts = ["First sentence.", "Second sentence."]
        embeddings = await embedder.embed_text_async(texts)

        assert embeddings.shape == (len(texts), embedder.embedding_dim)
        assert not np.isnan(embeddings).any()

    @pytest.mark.asyncio
    async def test_async_query_embedding(self, embedder):
        """Test async query embedding."""
        query = "What is AI?"
        embedding = await embedder.embed_queries_async(query)

        assert embedding.shape == (1, embedder.embedding_dim)
        assert not np.isnan(embedding).any()

    @pytest.mark.asyncio
    async def test_async_document_embedding(self, embedder):
        """Test async document embedding."""
        document = "AI is artificial intelligence."
        embedding = await embedder.embed_documents_async(document)

        assert embedding.shape == (1, embedder.embedding_dim)
        assert not np.isnan(embedding).any()

    def test_similarity_computation(self, embedder):
        """Test similarity computation."""
        texts1 = ["Machine learning is a subset of AI."]
        texts2 = ["AI includes machine learning.", "The weather is nice today."]

        embeddings1 = embedder.embed_text(texts1)
        embeddings2 = embedder.embed_text(texts2)

        similarity = embedder.compute_similarity(embeddings1, embeddings2)

        assert similarity.shape == (1, 2)
        # First similarity should be higher (related content)
        assert similarity[0, 0] > similarity[0, 1]

    def test_cache_functionality(self, embedder):
        """Test embedding cache."""
        text = "This will be cached."

        # First call - not cached
        embedding1 = embedder.embed_text(text)
        cache_stats = embedder.get_cache_stats()
        assert cache_stats["enabled"] is True
        assert cache_stats["size"] == 1

        # Second call - should hit cache
        embedding2 = embedder.embed_text(text)
        np.testing.assert_array_equal(embedding1, embedding2)

    def test_cache_clear(self, embedder):
        """Test clearing cache."""
        texts = ["First", "Second", "Third"]

        for text in texts:
            embedder.embed_text(text)

        stats = embedder.get_cache_stats()
        assert stats["size"] == len(texts)

        embedder.clear_cache()
        stats = embedder.get_cache_stats()
        assert stats["size"] == 0

    def test_empty_text(self, embedder):
        """Test handling of empty text."""
        # Empty string should still produce an embedding
        embedding = embedder.embed_text("")
        assert embedding.shape == (1, embedder.embedding_dim)

    def test_long_text_truncation(self, embedder):
        """Test that long text is truncated to max_length."""
        # Create very long text
        long_text = " ".join(["word"] * 1000)

        embedding = embedder.embed_text(long_text)
        assert embedding.shape == (1, embedder.embedding_dim)
        assert not np.isnan(embedding).any()

    def test_special_characters(self, embedder):
        """Test handling of special characters."""
        texts = [
            "Text with emoji 😊",
            "Math symbols: ∑∫∂",
            "Special chars: @#$%^&*()"
        ]

        embeddings = embedder.embed_text(texts)
        assert embeddings.shape == (len(texts), embedder.embedding_dim)
        assert not np.isnan(embeddings).any()

    def test_multilingual_text(self, embedder):
        """Test with non-English text (may not be optimal but shouldn't crash)."""
        texts = [
            "Hello world",
            "Bonjour le monde",
            "Hola mundo"
        ]

        embeddings = embedder.embed_text(texts)
        assert embeddings.shape == (len(texts), embedder.embedding_dim)
        assert not np.isnan(embeddings).any()

    def test_embedding_consistency(self, embedder):
        """Test that same text produces same embedding."""
        text = "Consistency check."

        embedding1 = embedder.embed_text(text)
        embedder.clear_cache()  # Clear cache to force recomputation
        embedding2 = embedder.embed_text(text)

        # Should be very close (might have tiny numerical differences)
        np.testing.assert_allclose(embedding1, embedding2, rtol=1e-4)

    def test_batch_vs_single_consistency(self, embedder):
        """Test that batch and single embedding produce same results."""
        texts = ["First text", "Second text"]

        # Batch embedding
        batch_embeddings = embedder.embed_text(texts)

        # Individual embeddings
        embedder.clear_cache()
        individual_embeddings = np.vstack([
            embedder.embed_text(text) for text in texts
        ])

        # Should be very close
        np.testing.assert_allclose(batch_embeddings, individual_embeddings, rtol=1e-4)

    def test_get_embedding_dimension(self, embedder):
        """Test getting embedding dimension."""
        dim = embedder.get_embedding_dimension()
        assert dim == embedder.embedding_dim
        assert dim > 0

    def test_repr(self, embedder):
        """Test string representation."""
        repr_str = repr(embedder)
        assert "BGEEmbedder" in repr_str
        assert embedder.model_name in repr_str
        assert str(embedder.embedding_dim) in repr_str


@pytest.mark.asyncio
class TestBGEEmbedderAsync:
    """Async tests for BGE embedder."""

    @pytest.fixture
    async def embedder(self):
        """Create embedder fixture."""
        return BGEEmbedder(
            model_name="BAAI/bge-small-en-v1.5",
            batch_size=4,
            max_length=128,
            use_fp16=False
        )

    async def test_concurrent_async_embedding(self, embedder):
        """Test concurrent async embedding calls."""
        import asyncio

        texts_list = [
            ["First batch text 1", "First batch text 2"],
            ["Second batch text 1", "Second batch text 2"],
            ["Third batch text 1", "Third batch text 2"]
        ]

        # Run concurrently
        tasks = [embedder.embed_text_async(texts) for texts in texts_list]
        results = await asyncio.gather(*tasks)

        # Verify all results
        for i, embeddings in enumerate(results):
            assert embeddings.shape == (len(texts_list[i]), embedder.embedding_dim)
            assert not np.isnan(embeddings).any()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
