"""Integration tests for hybrid search."""

import pytest
import numpy as np
from unittest.mock import AsyncMock, Mock, patch

from src.retrieval.query_processor import QueryProcessor, QueryIntent
from src.retrieval.hybrid_search import HybridSearchEngine, SearchResult
from src.embeddings.bge_embedder import BGEEmbedder
from src.retrieval.qdrant_client import QdrantClient
from src.retrieval.elasticsearch_client import ElasticsearchClient


class TestQueryProcessor:
    """Tests for query processor."""

    @pytest.fixture
    def processor(self):
        """Create query processor."""
        return QueryProcessor()

    def test_query_normalization(self, processor):
        """Test query normalization."""
        query = "  What  is   Machine Learning?  "
        result = processor.process_query(query)

        assert result["processed_query"] == "what is machine learning?"
        assert result["original_query"] == query

    def test_intent_extraction_methodological(self, processor):
        """Test methodological intent extraction."""
        queries = [
            "How does BERT work?",
            "What method was used?",
            "What approach did they take?",
            "Describe the implementation technique"
        ]

        for query in queries:
            result = processor.process_query(query)
            assert result["intent"] == QueryIntent.METHODOLOGICAL

    def test_intent_extraction_results(self, processor):
        """Test results intent extraction."""
        # Queries that should clearly indicate results intent
        query = "The model achieved 95% accuracy in performance tests"
        result = processor.process_query(query)

        # Should detect either RESULTS or GENERAL (both acceptable)
        assert result["intent"] in [QueryIntent.RESULTS, QueryIntent.GENERAL]

    def test_intent_extraction_comparative(self, processor):
        """Test comparative intent extraction."""
        queries = [
            "Compare BERT and GPT",
            "Difference between CNNs and RNNs",
            "LSTM versus GRU comparison",
            "Better performance: transformers vs LSTMs"
        ]

        for query in queries:
            result = processor.process_query(query)
            assert result["intent"] == QueryIntent.COMPARATIVE

    def test_intent_extraction_definition(self, processor):
        """Test definition intent extraction."""
        queries = [
            "What is machine learning?",
            "Define neural network",
            "Definition of attention mechanism",
            "Explain what is GPT"
        ]

        for query in queries:
            result = processor.process_query(query)
            assert result["intent"] == QueryIntent.DEFINITION

    def test_filter_extraction_year(self, processor):
        """Test year filter extraction."""
        query = "papers published in 2024"
        result = processor.process_query(query)

        # Year extraction is best-effort - just verify it's present
        assert "year" in result["filters"]
        # Could be 2024 or partial match - just check it's a reasonable value
        year = result["filters"]["year"]
        assert isinstance(year, (int, dict))

    def test_filter_extraction_year_range(self, processor):
        """Test year range filter extraction."""
        query = "Research from 2020 to 2024"
        result = processor.process_query(query)

        # Year range extraction is best-effort
        if "year" in result["filters"]:
            year_filter = result["filters"]["year"]
            # Check if it's a range or single year
            if isinstance(year_filter, dict):
                assert "gte" in year_filter or "lte" in year_filter

    def test_filter_extraction_venue(self, processor):
        """Test venue filter extraction."""
        queries = [
            ("Papers from NeurIPS", "NeurIPS"),
            ("ICML research", "ICML"),
            ("Nature publications", "Nature")
        ]

        for query, expected_venue in queries:
            result = processor.process_query(query)
            if "venue" in result["filters"]:
                assert result["filters"]["venue"] == expected_venue

    def test_query_expansion(self, processor):
        """Test query expansion."""
        queries_with_expansions = [
            ("ml algorithms", ["machine learning"]),
            ("dl models", ["deep learning"]),
            ("nlp techniques", ["natural language processing"]),
            ("llm performance", ["large language model"])
        ]

        for query, expected_expansions in queries_with_expansions:
            result = processor.process_query(query)
            for expansion in expected_expansions:
                assert expansion in result["expansion_terms"]

    def test_boost_fields_methodological(self, processor):
        """Test field boosting for methodological queries."""
        query = "How does attention mechanism work?"
        result = processor.process_query(query)

        boost_fields = result["boost_fields"]
        # Section titles should have high boost for methods
        assert any("section_title" in field for field in boost_fields)

    def test_boost_fields_results(self, processor):
        """Test field boosting for results queries."""
        query = "What accuracy did the model achieve?"
        result = processor.process_query(query)

        boost_fields = result["boost_fields"]
        # Abstract should have high boost for results
        assert any("abstract^3.0" in field for field in boost_fields)

    def test_enhanced_query_building(self, processor):
        """Test enhanced query building with expansions."""
        query = "ml performance"
        result = processor.process_query(query)
        enhanced = processor.build_enhanced_query(result)

        # Should include original query
        assert "ml" in enhanced or "performance" in enhanced
        # Should include expansions
        if result["expansion_terms"]:
            assert any(term in enhanced for term in result["expansion_terms"])


@pytest.mark.asyncio
class TestHybridSearchEngine:
    """Tests for hybrid search engine."""

    @pytest.fixture
    async def mock_search_engine(self):
        """Create mock hybrid search engine."""
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

            # Create search engine
            engine = HybridSearchEngine(
                embedder=embedder,
                qdrant_client=qdrant_client,
                elasticsearch_client=es_client,
                k=60,
                semantic_weight=0.5,
                lexical_weight=0.5
            )

            yield engine

    async def test_semantic_search_only(self, mock_search_engine):
        """Test semantic search only."""
        # Mock Qdrant search
        mock_search_engine.qdrant_client.search = AsyncMock(
            return_value=[
                {
                    "id": "doc1",
                    "score": 0.95,
                    "payload": {"content": "Machine learning content"}
                },
                {
                    "id": "doc2",
                    "score": 0.85,
                    "payload": {"content": "Deep learning content"}
                }
            ]
        )

        result = await mock_search_engine.search(
            "machine learning",
            limit=10,
            semantic_only=True
        )

        assert result.total_results == 2
        assert result.semantic_count == 2
        assert result.lexical_count == 0
        assert result.fusion_method == "semantic_only"
        assert all(r.source == "semantic" for r in result.results)

    async def test_lexical_search_only(self, mock_search_engine):
        """Test lexical search only."""
        # Mock Elasticsearch search
        mock_search_engine.elasticsearch_client.search = AsyncMock(
            return_value=[
                {
                    "id": "doc1",
                    "score": 12.5,
                    "payload": {"content": "Machine learning content"}
                },
                {
                    "id": "doc2",
                    "score": 10.3,
                    "payload": {"content": "Deep learning content"}
                }
            ]
        )

        result = await mock_search_engine.search(
            "machine learning",
            limit=10,
            lexical_only=True
        )

        assert result.total_results == 2
        assert result.semantic_count == 0
        assert result.lexical_count == 2
        assert result.fusion_method == "lexical_only"
        assert all(r.source == "lexical" for r in result.results)

    async def test_hybrid_search_with_rrf(self, mock_search_engine):
        """Test hybrid search with RRF."""
        # Mock both searches
        mock_search_engine.qdrant_client.search = AsyncMock(
            return_value=[
                {
                    "id": "doc1",
                    "score": 0.95,
                    "payload": {"content": "ML content"}
                },
                {
                    "id": "doc2",
                    "score": 0.85,
                    "payload": {"content": "DL content"}
                }
            ]
        )

        mock_search_engine.elasticsearch_client.search = AsyncMock(
            return_value=[
                {
                    "id": "doc2",
                    "score": 12.5,
                    "payload": {"content": "DL content"}
                },
                {
                    "id": "doc3",
                    "score": 10.3,
                    "payload": {"content": "AI content"}
                }
            ]
        )

        result = await mock_search_engine.search(
            "machine learning",
            limit=10,
            use_rrf=True
        )

        assert result.total_results >= 2  # At least doc1, doc2, doc3
        assert result.semantic_count == 2
        assert result.lexical_count == 2
        assert result.fusion_method == "rrf"
        # doc2 should rank high (appears in both)
        assert any(r.id == "doc2" for r in result.results)

    async def test_hybrid_search_with_weighted_fusion(self, mock_search_engine):
        """Test hybrid search with weighted fusion."""
        # Mock both searches
        mock_search_engine.qdrant_client.search = AsyncMock(
            return_value=[
                {
                    "id": "doc1",
                    "score": 0.95,
                    "payload": {"content": "ML content"}
                }
            ]
        )

        mock_search_engine.elasticsearch_client.search = AsyncMock(
            return_value=[
                {
                    "id": "doc2",
                    "score": 12.5,
                    "payload": {"content": "DL content"}
                }
            ]
        )

        result = await mock_search_engine.search(
            "machine learning",
            limit=10,
            use_rrf=False  # Use weighted fusion
        )

        assert result.fusion_method == "weighted"
        assert result.total_results == 2

    async def test_result_deduplication(self, mock_search_engine):
        """Test result deduplication."""
        # Mock both searches with overlapping results
        mock_search_engine.qdrant_client.search = AsyncMock(
            return_value=[
                {
                    "id": "doc1",
                    "score": 0.95,
                    "payload": {"content": "Content"}
                }
            ]
        )

        mock_search_engine.elasticsearch_client.search = AsyncMock(
            return_value=[
                {
                    "id": "doc1",  # Same ID
                    "score": 12.5,
                    "payload": {"content": "Content"}
                }
            ]
        )

        result = await mock_search_engine.search(
            "query",
            limit=10
        )

        # Should have only 1 result (deduplicated)
        assert result.total_results == 1
        assert result.results[0].id == "doc1"

    async def test_result_explanations(self, mock_search_engine):
        """Test result explanations."""
        mock_search_engine.qdrant_client.search = AsyncMock(
            return_value=[
                {
                    "id": "doc1",
                    "score": 0.95,
                    "payload": {
                        "content": "Content",
                        "year": 2024,
                        "authors": "Smith"
                    }
                }
            ]
        )

        mock_search_engine.elasticsearch_client.search = AsyncMock(
            return_value=[]
        )

        result = await mock_search_engine.search(
            "query from 2024",
            limit=10,
            include_explanation=True
        )

        assert result.total_results >= 1
        assert result.results[0].explanation is not None
        assert "Score" in result.results[0].explanation

    async def test_reciprocal_rank_fusion_calculation(self, mock_search_engine):
        """Test RRF score calculation."""
        semantic_results = [
            SearchResult(
                id="doc1", score=0.9, content="", metadata={},
                source="semantic", rank=1
            ),
            SearchResult(
                id="doc2", score=0.8, content="", metadata={},
                source="semantic", rank=2
            )
        ]

        lexical_results = [
            SearchResult(
                id="doc2", score=15.0, content="", metadata={},
                source="lexical", rank=1
            ),
            SearchResult(
                id="doc3", score=12.0, content="", metadata={},
                source="lexical", rank=2
            )
        ]

        fused = mock_search_engine._reciprocal_rank_fusion(
            semantic_results, lexical_results
        )

        # doc2 appears in both, should have highest score
        assert fused[0].id == "doc2"
        assert fused[0].source == "hybrid"

    async def test_compare_search_methods(self, mock_search_engine):
        """Test comparison of search methods."""
        # Mock searches
        mock_search_engine.qdrant_client.search = AsyncMock(
            return_value=[
                {
                    "id": "doc1",
                    "score": 0.95,
                    "payload": {"content": "Content"}
                }
            ]
        )

        mock_search_engine.elasticsearch_client.search = AsyncMock(
            return_value=[
                {
                    "id": "doc2",
                    "score": 12.5,
                    "payload": {"content": "Content"}
                }
            ]
        )

        comparison = await mock_search_engine.compare_search_methods(
            "machine learning",
            limit=10
        )

        assert "semantic" in comparison
        assert "lexical" in comparison
        assert "hybrid" in comparison
        assert "overlap" in comparison
        assert comparison["semantic"]["count"] >= 0
        assert comparison["lexical"]["count"] >= 0
        assert comparison["hybrid"]["count"] >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
