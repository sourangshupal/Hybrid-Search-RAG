"""Unit tests for Cohere reranker."""

import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from typing import List, Dict, Any

from src.reranking.cohere_reranker import CohereReranker
from src.core.exceptions import CohereRerankError


class MockRerankResult:
    """Mock Cohere rerank result."""

    def __init__(self, index: int, relevance_score: float, text: str = None):
        self.index = index
        self.relevance_score = relevance_score
        if text:
            self.document = MagicMock()
            self.document.text = text


class MockRerankResponse:
    """Mock Cohere rerank response."""

    def __init__(self, results: List[MockRerankResult]):
        self.results = results


@pytest.fixture
def mock_cohere_client():
    """Create mock Cohere client."""
    with patch('src.reranking.cohere_reranker.AsyncCohereClient') as mock:
        client = Mock()
        mock.return_value = client
        yield client


@pytest.fixture
def reranker(mock_cohere_client):
    """Create Cohere reranker instance."""
    return CohereReranker(
        api_key="test-api-key",
        model="rerank-english-v3.0",
        top_n=None,
        use_async=True
    )


class TestCohereRerankerInitialization:
    """Tests for reranker initialization."""

    def test_initialization_async(self, mock_cohere_client):
        """Test async client initialization."""
        reranker = CohereReranker(
            api_key="test-key",
            model="rerank-english-v3.0",
            use_async=True
        )

        assert reranker.api_key == "test-key"
        assert reranker.model == "rerank-english-v3.0"
        assert reranker.use_async is True
        assert reranker.top_n is None

    def test_initialization_with_params(self, mock_cohere_client):
        """Test initialization with custom parameters."""
        reranker = CohereReranker(
            api_key="test-key",
            model="rerank-multilingual-v2.0",
            top_n=5,
            max_chunks_per_doc=10,
            use_async=False
        )

        assert reranker.model == "rerank-multilingual-v2.0"
        assert reranker.top_n == 5
        assert reranker.max_chunks_per_doc == 10
        assert reranker.use_async is False

    def test_initialization_failure(self):
        """Test initialization failure handling."""
        with patch('src.reranking.cohere_reranker.AsyncCohereClient') as mock:
            mock.side_effect = Exception("Connection failed")

            with pytest.raises(CohereRerankError):
                CohereReranker(api_key="test-key")


@pytest.mark.asyncio
class TestReranking:
    """Tests for reranking functionality."""

    async def test_rerank_empty_documents(self, reranker):
        """Test reranking with empty documents."""
        result = await reranker.rerank("test query", [])
        assert result == []

    async def test_rerank_basic(self, reranker, mock_cohere_client):
        """Test basic reranking."""
        documents = [
            "Machine learning is a subset of AI",
            "Deep learning uses neural networks",
            "Python is a programming language"
        ]

        # Mock response
        mock_results = [
            MockRerankResult(0, 0.95),
            MockRerankResult(1, 0.85),
            MockRerankResult(2, 0.45)
        ]
        mock_response = MockRerankResponse(mock_results)
        mock_cohere_client.rerank = AsyncMock(return_value=mock_response)

        result = await reranker.rerank(
            query="What is machine learning?",
            documents=documents,
            top_n=3
        )

        assert len(result) == 3
        assert result[0]["index"] == 0
        assert result[0]["relevance_score"] == 0.95
        assert result[1]["index"] == 1
        assert result[1]["relevance_score"] == 0.85
        assert result[2]["index"] == 2
        assert result[2]["relevance_score"] == 0.45

    async def test_rerank_with_documents_returned(self, reranker, mock_cohere_client):
        """Test reranking with documents in response."""
        documents = ["Doc 1", "Doc 2", "Doc 3"]

        # Mock response with document text
        mock_results = [
            MockRerankResult(0, 0.95, "Doc 1"),
            MockRerankResult(1, 0.75, "Doc 2")
        ]
        mock_response = MockRerankResponse(mock_results)
        mock_cohere_client.rerank = AsyncMock(return_value=mock_response)

        result = await reranker.rerank(
            query="test",
            documents=documents,
            top_n=2,
            return_documents=True
        )

        assert len(result) == 2
        assert result[0]["text"] == "Doc 1"
        assert result[1]["text"] == "Doc 2"

    async def test_rerank_top_n_limiting(self, reranker, mock_cohere_client):
        """Test top_n limiting."""
        documents = ["Doc " + str(i) for i in range(10)]

        # Mock response with 3 results
        mock_results = [
            MockRerankResult(i, 0.9 - i * 0.1) for i in range(3)
        ]
        mock_response = MockRerankResponse(mock_results)
        mock_cohere_client.rerank = AsyncMock(return_value=mock_response)

        result = await reranker.rerank(
            query="test",
            documents=documents,
            top_n=3
        )

        assert len(result) == 3
        # Verify API was called with top_n=3
        mock_cohere_client.rerank.assert_called_once()
        call_kwargs = mock_cohere_client.rerank.call_args.kwargs
        assert call_kwargs["top_n"] == 3

    async def test_rerank_with_retry(self, reranker, mock_cohere_client):
        """Test reranking with retry on failure."""
        documents = ["Doc 1", "Doc 2"]

        # First call fails, second succeeds
        mock_results = [MockRerankResult(0, 0.9)]
        mock_response = MockRerankResponse(mock_results)

        mock_cohere_client.rerank = AsyncMock(
            side_effect=[
                Exception("Temporary failure"),
                mock_response
            ]
        )

        result = await reranker.rerank(
            query="test",
            documents=documents,
            max_retries=3
        )

        assert len(result) == 1
        assert mock_cohere_client.rerank.call_count == 2

    async def test_rerank_max_retries_exceeded(self, reranker, mock_cohere_client):
        """Test reranking when max retries exceeded."""
        documents = ["Doc 1", "Doc 2"]

        mock_cohere_client.rerank = AsyncMock(
            side_effect=Exception("Persistent failure")
        )

        with pytest.raises(CohereRerankError):
            await reranker.rerank(
                query="test",
                documents=documents,
                max_retries=2
            )

        assert mock_cohere_client.rerank.call_count == 2


@pytest.mark.asyncio
class TestSearchResultsReranking:
    """Tests for search results reranking."""

    async def test_rerank_search_results_empty(self, reranker):
        """Test reranking empty search results."""
        result = await reranker.rerank_search_results("test query", [])
        assert result == []

    async def test_rerank_search_results_basic(self, reranker, mock_cohere_client):
        """Test reranking search results."""
        search_results = [
            {
                "id": "doc1",
                "score": 0.8,
                "content": "Machine learning content"
            },
            {
                "id": "doc2",
                "score": 0.7,
                "content": "Deep learning content"
            },
            {
                "id": "doc3",
                "score": 0.6,
                "content": "Python content"
            }
        ]

        # Mock rerank response (reversed order)
        mock_results = [
            MockRerankResult(2, 0.95),  # doc3 now highest
            MockRerankResult(0, 0.85),  # doc1 second
            MockRerankResult(1, 0.75)   # doc2 third
        ]
        mock_response = MockRerankResponse(mock_results)
        mock_cohere_client.rerank = AsyncMock(return_value=mock_response)

        result = await reranker.rerank_search_results(
            query="What is Python?",
            search_results=search_results,
            top_n=3
        )

        assert len(result) == 3
        # Check order changed
        assert result[0]["id"] == "doc3"
        assert result[1]["id"] == "doc1"
        assert result[2]["id"] == "doc2"
        # Check scores updated
        assert result[0]["rerank_score"] == 0.95
        assert result[0]["original_score"] == 0.6
        assert "score" in result[0]

    async def test_rerank_search_results_with_metadata(self, reranker, mock_cohere_client):
        """Test reranking with metadata field."""
        search_results = [
            {
                "id": "doc1",
                "score": 0.8,
                "metadata": {
                    "content": "Content in metadata"
                }
            }
        ]

        mock_results = [MockRerankResult(0, 0.9)]
        mock_response = MockRerankResponse(mock_results)
        mock_cohere_client.rerank = AsyncMock(return_value=mock_response)

        result = await reranker.rerank_search_results(
            query="test",
            search_results=search_results,
            content_field="content"
        )

        assert len(result) == 1
        assert result[0]["id"] == "doc1"

    async def test_rerank_search_results_with_payload(self, reranker, mock_cohere_client):
        """Test reranking with payload field."""
        search_results = [
            {
                "id": "doc1",
                "score": 0.8,
                "payload": {
                    "content": "Content in payload"
                }
            }
        ]

        mock_results = [MockRerankResult(0, 0.9)]
        mock_response = MockRerankResponse(mock_results)
        mock_cohere_client.rerank = AsyncMock(return_value=mock_response)

        result = await reranker.rerank_search_results(
            query="test",
            search_results=search_results,
            content_field="content"
        )

        assert len(result) == 1


@pytest.mark.asyncio
class TestScoreNormalization:
    """Tests for score normalization."""

    def test_normalize_scores_basic(self, reranker):
        """Test basic score normalization."""
        results = [
            {"id": "doc1", "rerank_score": 0.9},
            {"id": "doc2", "rerank_score": 0.5},
            {"id": "doc3", "rerank_score": 0.3}
        ]

        normalized = reranker._normalize_scores(results)

        # Max score (0.9) should normalize to 1.0
        assert normalized[0]["rerank_score_normalized"] == 1.0
        assert normalized[0]["score"] == 1.0

        # Min score (0.3) should normalize to 0.0
        assert normalized[2]["rerank_score_normalized"] == 0.0
        assert normalized[2]["score"] == 0.0

        # Middle score should be in between
        assert 0.0 < normalized[1]["rerank_score_normalized"] < 1.0

    def test_normalize_scores_all_same(self, reranker):
        """Test normalization when all scores are the same."""
        results = [
            {"id": "doc1", "rerank_score": 0.5},
            {"id": "doc2", "rerank_score": 0.5},
            {"id": "doc3", "rerank_score": 0.5}
        ]

        normalized = reranker._normalize_scores(results)

        # All should normalize to 1.0
        for result in normalized:
            assert result["rerank_score_normalized"] == 1.0
            assert result["score"] == 1.0

    def test_normalize_scores_empty(self, reranker):
        """Test normalization with empty results."""
        results = []
        normalized = reranker._normalize_scores(results)
        assert normalized == []

    async def test_rerank_without_normalization(self, reranker, mock_cohere_client):
        """Test reranking without score normalization."""
        search_results = [
            {"id": "doc1", "score": 0.8, "content": "Content 1"},
            {"id": "doc2", "score": 0.7, "content": "Content 2"}
        ]

        mock_results = [
            MockRerankResult(0, 0.9),
            MockRerankResult(1, 0.7)
        ]
        mock_response = MockRerankResponse(mock_results)
        mock_cohere_client.rerank = AsyncMock(return_value=mock_response)

        result = await reranker.rerank_search_results(
            query="test",
            search_results=search_results,
            normalize_scores=False
        )

        # Scores should not be normalized
        assert "rerank_score_normalized" not in result[0]
        assert result[0]["rerank_score"] == 0.9
        assert result[1]["rerank_score"] == 0.7


@pytest.mark.asyncio
class TestFallbackMechanism:
    """Tests for fallback mechanism."""

    async def test_rerank_with_fallback_success(self, reranker, mock_cohere_client):
        """Test fallback when reranking succeeds."""
        search_results = [
            {"id": "doc1", "score": 0.8, "content": "Content 1"}
        ]

        mock_results = [MockRerankResult(0, 0.95)]
        mock_response = MockRerankResponse(mock_results)
        mock_cohere_client.rerank = AsyncMock(return_value=mock_response)

        result = await reranker.rerank_with_fallback(
            query="test",
            search_results=search_results
        )

        assert len(result) == 1
        assert result[0]["rerank_score"] == 0.95

    async def test_rerank_with_fallback_failure(self, reranker, mock_cohere_client):
        """Test fallback when reranking fails."""
        search_results = [
            {"id": "doc1", "score": 0.8, "content": "Content 1"},
            {"id": "doc2", "score": 0.7, "content": "Content 2"}
        ]

        mock_cohere_client.rerank = AsyncMock(
            side_effect=Exception("API failure")
        )

        result = await reranker.rerank_with_fallback(
            query="test",
            search_results=search_results,
            fallback_to_original=True
        )

        # Should return original results
        assert result == search_results

    async def test_rerank_with_fallback_disabled(self, reranker, mock_cohere_client):
        """Test fallback disabled raises error."""
        search_results = [
            {"id": "doc1", "score": 0.8, "content": "Content 1"}
        ]

        mock_cohere_client.rerank = AsyncMock(
            side_effect=Exception("API failure")
        )

        with pytest.raises(Exception):
            await reranker.rerank_with_fallback(
                query="test",
                search_results=search_results,
                fallback_to_original=False
            )


class TestUtilities:
    """Tests for utility methods."""

    def test_get_stats(self, reranker):
        """Test getting reranker statistics."""
        stats = reranker.get_stats()

        assert "model" in stats
        assert stats["model"] == "rerank-english-v3.0"
        assert "top_n" in stats
        assert "max_chunks_per_doc" in stats
        assert "use_async" in stats
        assert stats["use_async"] is True

    def test_repr(self, reranker):
        """Test string representation."""
        repr_str = repr(reranker)
        assert "CohereReranker" in repr_str
        assert "rerank-english-v3.0" in repr_str


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
