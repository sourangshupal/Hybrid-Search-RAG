"""Integration tests for API endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch
import numpy as np

from src.api.main import app, initialize_dependencies
from src.retrieval.hybrid_search import HybridSearchEngine, HybridSearchResult, SearchResult
from src.core.rag_pipeline import RAGPipeline, RAGResult
from src.embeddings.bge_embedder import BGEEmbedder
from src.retrieval.qdrant_client import QdrantClient
from src.retrieval.elasticsearch_client import ElasticsearchClient
from src.generation.claude_generator import ClaudeGenerator


@pytest.fixture
def mock_search_engine():
    """Create mock search engine."""
    with patch('src.retrieval.qdrant_client.QdrantClientLib'), \
         patch('src.retrieval.elasticsearch_client.Elasticsearch') as mock_es:

        mock_es.return_value.ping.return_value = True

        # Mock embedder
        embedder = Mock(spec=BGEEmbedder)
        embedder.embed_queries_async = AsyncMock(
            return_value=np.random.randn(1, 768)
        )

        # Create clients
        qdrant_client = QdrantClient(host="localhost", port=6333)
        es_client = ElasticsearchClient(host="localhost", port=9200)

        # Create engine
        engine = HybridSearchEngine(
            embedder=embedder,
            qdrant_client=qdrant_client,
            elasticsearch_client=es_client
        )

        # Mock search method
        async def mock_search(*args, **kwargs):
            return HybridSearchResult(
                query=kwargs.get("query", "test"),
                results=[
                    SearchResult(
                        id="doc1",
                        score=0.9,
                        content="Test content about transformers",
                        metadata={"title": "Test Paper", "authors": "Author", "year": 2023},
                        source="hybrid",
                        rank=1,
                        explanation="Retrieved via hybrid search"
                    )
                ],
                total_results=1,
                semantic_count=1,
                lexical_count=0,
                fusion_method="rrf",
                execution_time_ms=100.0,
                reranked=True,
                reranking_time_ms=50.0
            )

        engine.search = mock_search

        return engine


@pytest.fixture
def mock_rag_pipeline(mock_search_engine):
    """Create mock RAG pipeline."""
    # Mock generator
    generator = Mock(spec=ClaudeGenerator)
    generator.model = "claude-sonnet-4-5-20250929"

    # Create pipeline
    pipeline = RAGPipeline(
        search_engine=mock_search_engine,
        primary_generator=generator
    )

    # Mock query method
    async def mock_query(*args, **kwargs):
        return RAGResult(
            query=kwargs.get("query", "test"),
            answer="This is a test answer with citations [Author 2023].",
            citations=[{
                "authors": "Author",
                "year": "2023",
                "title": "Test Paper",
                "venue": "",
                "doi": "",
                "arxiv_id": ""
            }],
            search_results=[{
                "id": "doc1",
                "title": "Test Paper",
                "authors": "Author",
                "year": 2023,
                "score": 0.9
            }],
            model_used="claude-sonnet-4-5-20250929",
            query_type="general",
            num_chunks_retrieved=1,
            num_chunks_used=1,
            search_time_ms=100.0,
            reranking_time_ms=50.0,
            generation_time_ms=1500.0,
            total_time_ms=1650.0,
            input_tokens=1000,
            output_tokens=200,
            total_tokens=1200,
            validated=True,
            fallback_used=False
        )

    pipeline.query = mock_query

    return pipeline


@pytest.fixture
def client(mock_search_engine, mock_rag_pipeline):
    """Create test client with mocked dependencies."""
    # Initialize dependencies
    initialize_dependencies(
        search_engine=mock_search_engine,
        rag_pipeline=mock_rag_pipeline
    )

    # Create test client
    return TestClient(app)


class TestSystemEndpoints:
    """Tests for system endpoints."""

    def test_root(self, client):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "service" in data
        assert "components" in data

    def test_metrics(self, client):
        """Test metrics endpoint."""
        response = client.get("/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "requests" in data
        assert "uptime_seconds" in data

    def test_api_info(self, client):
        """Test API info endpoint."""
        response = client.get("/api/v1/info")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Hybrid Search RAG API"
        assert "version" in data
        assert "endpoints" in data


class TestSearchEndpoints:
    """Tests for search endpoints."""

    def test_semantic_search(self, client):
        """Test semantic search endpoint."""
        request_data = {
            "query": "What are transformers?",
            "top_k": 5
        }

        response = client.post("/api/v1/search/semantic", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "What are transformers?"
        assert "results" in data
        assert "total_results" in data
        assert "search_time_ms" in data

    def test_lexical_search(self, client):
        """Test lexical search endpoint."""
        request_data = {
            "query": "machine learning",
            "top_k": 10
        }

        response = client.post("/api/v1/search/lexical", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "machine learning"

    def test_hybrid_search(self, client):
        """Test hybrid search endpoint."""
        request_data = {
            "query": "neural networks",
            "top_k": 10,
            "rerank": True
        }

        response = client.post("/api/v1/search/hybrid", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "neural networks"
        assert "reranked" in data

    def test_search_validation_error(self, client):
        """Test search with invalid request."""
        request_data = {
            "query": "",  # Empty query should fail
            "top_k": 5
        }

        response = client.post("/api/v1/search/semantic", json=request_data)
        assert response.status_code == 422  # Validation error


class TestRAGEndpoints:
    """Tests for RAG query endpoints."""

    def test_rag_query(self, client):
        """Test RAG query endpoint."""
        request_data = {
            "query": "How does BERT work?",
            "retrieval_top_k": 20,
            "rerank_top_k": 10,
            "include_sources": True
        }

        response = client.post("/api/v1/query", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "How does BERT work?"
        assert "answer" in data
        assert "citations" in data
        assert "sources" in data
        assert "model_used" in data
        assert "total_time_ms" in data
        assert "tokens_used" in data

    def test_rag_query_validation(self, client):
        """Test RAG query with invalid request."""
        request_data = {
            "query": "",  # Empty query
            "retrieval_top_k": 20
        }

        response = client.post("/api/v1/query", json=request_data)
        assert response.status_code == 422


class TestDocumentEndpoints:
    """Tests for document management endpoints."""

    def test_upload_document(self, client):
        """Test document upload endpoint."""
        # Note: This is a placeholder endpoint
        files = {"file": ("test.pdf", b"fake pdf content", "application/pdf")}

        response = client.post("/api/v1/documents/upload", files=files)
        assert response.status_code == 201
        data = response.json()
        assert "message" in data
        assert "filename" in data

    def test_get_document(self, client):
        """Test get document endpoint."""
        response = client.get("/api/v1/documents/test123")
        assert response.status_code == 200
        data = response.json()
        assert data["document_id"] == "test123"

    def test_delete_document(self, client):
        """Test delete document endpoint."""
        response = client.delete("/api/v1/documents/test123")
        assert response.status_code == 200
        data = response.json()
        assert data["document_id"] == "test123"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
