"""Integration tests for RAG pipeline."""

import pytest
import numpy as np
from unittest.mock import AsyncMock, Mock, patch, MagicMock

from src.core.rag_pipeline import RAGPipeline, RAGResult
from src.retrieval.hybrid_search import HybridSearchEngine, SearchResult, HybridSearchResult
from src.generation.claude_generator import ClaudeGenerator
from src.generation.openai_generator import OpenAIGenerator
from src.generation.prompt_templates import QueryType
from src.embeddings.bge_embedder import BGEEmbedder
from src.retrieval.qdrant_client import QdrantClient
from src.retrieval.elasticsearch_client import ElasticsearchClient


@pytest.fixture
def mock_claude_response():
    """Create mock Claude API response."""
    response = Mock()
    response.content = [Mock()]
    response.content[0].text = """Based on the provided papers, BERT [Devlin 2019] uses a transformer architecture with bidirectional attention mechanisms. The model is pre-trained on masked language modeling and next sentence prediction tasks.

The key innovation is the bidirectional context [Source 1], which allows the model to understand relationships between words more effectively than previous unidirectional models."""

    response.usage = Mock()
    response.usage.input_tokens = 1500
    response.usage.output_tokens = 250

    return response


@pytest.fixture
def mock_openai_response():
    """Create mock OpenAI API response."""
    response = Mock()
    response.choices = [Mock()]
    response.choices[0].message = Mock()
    response.choices[0].message.content = """GPT-3 [Brown 2020] is a large language model with 175 billion parameters. It demonstrates impressive few-shot learning capabilities across various NLP tasks."""

    response.usage = Mock()
    response.usage.prompt_tokens = 1600
    response.usage.completion_tokens = 200
    response.usage.total_tokens = 1800

    return response


@pytest.fixture
async def mock_hybrid_search_engine():
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
            elasticsearch_client=es_client
        )

        yield engine


@pytest.fixture
def mock_claude_generator(mock_claude_response):
    """Create mock Claude generator."""
    generator = Mock(spec=ClaudeGenerator)
    generator.model = "claude-sonnet-4-5-20250929"

    # Mock generate method
    async def mock_generate(*args, **kwargs):
        return {
            "answer": mock_claude_response.content[0].text,
            "citations": [
                {
                    "authors": "Devlin et al.",
                    "year": "2019",
                    "title": "BERT: Pre-training of Deep Bidirectional Transformers",
                    "venue": "NAACL",
                    "doi": "",
                    "arxiv_id": ""
                }
            ],
            "model": "claude-sonnet-4-5-20250929",
            "query_type": "methodological",
            "num_chunks": 5,
            "generation_time_ms": 1500.0,
            "input_tokens": 1500,
            "output_tokens": 250,
            "total_tokens": 1750
        }

    generator.generate_with_validation = AsyncMock(side_effect=mock_generate)
    generator.generate_stream = AsyncMock()
    generator.get_stats = Mock(return_value={
        "model": "claude-sonnet-4-5-20250929",
        "max_tokens": 4096,
        "temperature": 0.3
    })

    return generator


@pytest.fixture
def mock_openai_generator(mock_openai_response):
    """Create mock OpenAI generator."""
    generator = Mock(spec=OpenAIGenerator)
    generator.model = "gpt-4o"

    # Mock generate method
    async def mock_generate(*args, **kwargs):
        return {
            "answer": mock_openai_response.choices[0].message.content,
            "citations": [
                {
                    "authors": "Brown et al.",
                    "year": "2020",
                    "title": "Language Models are Few-Shot Learners",
                    "venue": "NeurIPS",
                    "doi": "",
                    "arxiv_id": "2005.14165"
                }
            ],
            "model": "gpt-4o",
            "query_type": "general",
            "num_chunks": 5,
            "generation_time_ms": 1200.0,
            "input_tokens": 1600,
            "output_tokens": 200,
            "total_tokens": 1800
        }

    generator.generate_with_validation = AsyncMock(side_effect=mock_generate)
    generator.generate_stream = AsyncMock()
    generator.get_stats = Mock(return_value={
        "model": "gpt-4o",
        "max_tokens": 4096,
        "temperature": 0.3
    })

    return generator


@pytest.mark.asyncio
class TestRAGPipelineBasic:
    """Tests for basic RAG pipeline functionality."""

    async def test_initialization(
        self,
        mock_hybrid_search_engine,
        mock_claude_generator,
        mock_openai_generator
    ):
        """Test RAG pipeline initialization."""
        pipeline = RAGPipeline(
            search_engine=mock_hybrid_search_engine,
            primary_generator=mock_claude_generator,
            fallback_generator=mock_openai_generator,
            enable_fallback=True
        )

        assert pipeline.search_engine == mock_hybrid_search_engine
        assert pipeline.primary_generator == mock_claude_generator
        assert pipeline.fallback_generator == mock_openai_generator
        assert pipeline.enable_fallback is True

    async def test_query_with_results(
        self,
        mock_hybrid_search_engine,
        mock_claude_generator,
        mock_openai_generator
    ):
        """Test RAG query with search results."""
        # Mock search results
        mock_hybrid_search_engine.search = AsyncMock(
            return_value=HybridSearchResult(
                query="What is BERT?",
                results=[
                    SearchResult(
                        id="doc1",
                        score=0.95,
                        content="BERT uses bidirectional transformers...",
                        metadata={
                            "title": "BERT Paper",
                            "authors": "Devlin et al.",
                            "year": 2019
                        },
                        source="hybrid",
                        rank=1
                    ),
                    SearchResult(
                        id="doc2",
                        score=0.85,
                        content="Transformer architecture with attention...",
                        metadata={
                            "title": "Attention is All You Need",
                            "authors": "Vaswani et al.",
                            "year": 2017
                        },
                        source="hybrid",
                        rank=2
                    )
                ],
                total_results=2,
                semantic_count=1,
                lexical_count=1,
                fusion_method="rrf",
                execution_time_ms=150.0,
                reranked=True,
                reranking_time_ms=50.0
            )
        )

        pipeline = RAGPipeline(
            search_engine=mock_hybrid_search_engine,
            primary_generator=mock_claude_generator
        )

        result = await pipeline.query("What is BERT?")

        assert isinstance(result, RAGResult)
        assert result.query == "What is BERT?"
        assert len(result.answer) > 0
        assert result.num_chunks_retrieved == 2
        assert result.model_used == "claude-sonnet-4-5-20250929"
        assert result.fallback_used is False

    async def test_query_no_results(
        self,
        mock_hybrid_search_engine,
        mock_claude_generator
    ):
        """Test RAG query with no search results."""
        # Mock empty search results
        mock_hybrid_search_engine.search = AsyncMock(
            return_value=HybridSearchResult(
                query="Nonexistent topic",
                results=[],
                total_results=0,
                semantic_count=0,
                lexical_count=0,
                fusion_method="rrf",
                execution_time_ms=100.0
            )
        )

        pipeline = RAGPipeline(
            search_engine=mock_hybrid_search_engine,
            primary_generator=mock_claude_generator
        )

        result = await pipeline.query("Nonexistent topic")

        assert result.num_chunks_retrieved == 0
        assert "couldn't find" in result.answer.lower()
        assert result.validated is False

    async def test_query_type_detection(
        self,
        mock_hybrid_search_engine,
        mock_claude_generator
    ):
        """Test automatic query type detection."""
        # Mock search results
        mock_hybrid_search_engine.search = AsyncMock(
            return_value=HybridSearchResult(
                query="How does BERT work?",
                results=[
                    SearchResult(
                        id="doc1",
                        score=0.9,
                        content="BERT methodology...",
                        metadata={"title": "BERT", "authors": "Devlin", "year": 2019},
                        source="hybrid",
                        rank=1
                    )
                ],
                total_results=1,
                semantic_count=1,
                lexical_count=0,
                fusion_method="semantic_only",
                execution_time_ms=100.0
            )
        )

        pipeline = RAGPipeline(
            search_engine=mock_hybrid_search_engine,
            primary_generator=mock_claude_generator
        )

        result = await pipeline.query("How does BERT work?")

        # Should detect methodological query type
        assert result.query_type in ["methodological", "general"]


@pytest.mark.asyncio
class TestRAGPipelineFallback:
    """Tests for fallback mechanism."""

    async def test_fallback_on_primary_failure(
        self,
        mock_hybrid_search_engine,
        mock_claude_generator,
        mock_openai_generator
    ):
        """Test fallback to OpenAI when Claude fails."""
        # Mock search results
        mock_hybrid_search_engine.search = AsyncMock(
            return_value=HybridSearchResult(
                query="Test query",
                results=[
                    SearchResult(
                        id="doc1",
                        score=0.9,
                        content="Test content",
                        metadata={"title": "Test", "authors": "Author", "year": 2020},
                        source="hybrid",
                        rank=1
                    )
                ],
                total_results=1,
                semantic_count=1,
                lexical_count=0,
                fusion_method="semantic_only",
                execution_time_ms=100.0
            )
        )

        # Make Claude fail
        from src.core.exceptions import GenerationError
        mock_claude_generator.generate_with_validation = AsyncMock(
            side_effect=GenerationError("Claude API failed")
        )

        pipeline = RAGPipeline(
            search_engine=mock_hybrid_search_engine,
            primary_generator=mock_claude_generator,
            fallback_generator=mock_openai_generator,
            enable_fallback=True
        )

        result = await pipeline.query("Test query")

        assert result.fallback_used is True
        assert result.model_used == "gpt-4o"
        assert len(result.answer) > 0

    async def test_no_fallback_when_disabled(
        self,
        mock_hybrid_search_engine,
        mock_claude_generator,
        mock_openai_generator
    ):
        """Test that fallback doesn't activate when disabled."""
        # Mock search results
        mock_hybrid_search_engine.search = AsyncMock(
            return_value=HybridSearchResult(
                query="Test query",
                results=[
                    SearchResult(
                        id="doc1",
                        score=0.9,
                        content="Test content",
                        metadata={"title": "Test", "authors": "Author", "year": 2020},
                        source="hybrid",
                        rank=1
                    )
                ],
                total_results=1,
                semantic_count=1,
                lexical_count=0,
                fusion_method="semantic_only",
                execution_time_ms=100.0
            )
        )

        # Make Claude fail
        from src.core.exceptions import GenerationError, RAGPipelineError
        mock_claude_generator.generate_with_validation = AsyncMock(
            side_effect=GenerationError("Claude API failed")
        )

        pipeline = RAGPipeline(
            search_engine=mock_hybrid_search_engine,
            primary_generator=mock_claude_generator,
            fallback_generator=mock_openai_generator,
            enable_fallback=False
        )

        with pytest.raises(RAGPipelineError):
            await pipeline.query("Test query")


@pytest.mark.asyncio
class TestRAGPipelineStreaming:
    """Tests for streaming functionality."""

    async def test_streaming_query(
        self,
        mock_hybrid_search_engine,
        mock_claude_generator
    ):
        """Test streaming RAG query."""
        # Mock search results
        mock_hybrid_search_engine.search = AsyncMock(
            return_value=HybridSearchResult(
                query="What is BERT?",
                results=[
                    SearchResult(
                        id="doc1",
                        score=0.9,
                        content="BERT content",
                        metadata={"title": "BERT", "authors": "Devlin", "year": 2019},
                        source="hybrid",
                        rank=1
                    )
                ],
                total_results=1,
                semantic_count=1,
                lexical_count=0,
                fusion_method="semantic_only",
                execution_time_ms=100.0
            )
        )

        # Mock streaming response
        async def mock_stream(*args, **kwargs):
            chunks = ["BERT ", "is a ", "transformer ", "model."]
            for chunk in chunks:
                yield chunk

        mock_claude_generator.generate_stream = mock_stream

        pipeline = RAGPipeline(
            search_engine=mock_hybrid_search_engine,
            primary_generator=mock_claude_generator
        )

        # Collect streamed chunks
        chunks = []
        async for chunk in pipeline.query_stream("What is BERT?"):
            chunks.append(chunk)

        assert len(chunks) > 0
        assert "".join(chunks) == "BERT is a transformer model."


@pytest.mark.asyncio
class TestRAGPipelineValidation:
    """Tests for response validation."""

    async def test_validated_response(
        self,
        mock_hybrid_search_engine,
        mock_claude_generator
    ):
        """Test response with validation."""
        # Mock search results
        mock_hybrid_search_engine.search = AsyncMock(
            return_value=HybridSearchResult(
                query="Test query",
                results=[
                    SearchResult(
                        id="doc1",
                        score=0.9,
                        content="Test content",
                        metadata={"title": "Test", "authors": "Author", "year": 2020},
                        source="hybrid",
                        rank=1
                    )
                ],
                total_results=1,
                semantic_count=1,
                lexical_count=0,
                fusion_method="semantic_only",
                execution_time_ms=100.0
            )
        )

        # Mock validated response
        async def mock_generate_validated(*args, **kwargs):
            return {
                "answer": "Test answer with [Source 1] citation.",
                "citations": [{"authors": "Author", "year": "2020", "title": "Test"}],
                "model": "claude-sonnet-4-5-20250929",
                "query_type": "general",
                "num_chunks": 1,
                "generation_time_ms": 1000.0,
                "input_tokens": 1000,
                "output_tokens": 100,
                "total_tokens": 1100,
                "validated": True
            }

        mock_claude_generator.generate_with_validation = AsyncMock(
            side_effect=mock_generate_validated
        )

        pipeline = RAGPipeline(
            search_engine=mock_hybrid_search_engine,
            primary_generator=mock_claude_generator,
            require_citations=True
        )

        result = await pipeline.query("Test query", validate_response=True)

        assert result.validated is True


@pytest.mark.asyncio
class TestRAGPipelineUtilities:
    """Tests for utility methods."""

    async def test_get_stats(
        self,
        mock_hybrid_search_engine,
        mock_claude_generator,
        mock_openai_generator
    ):
        """Test getting pipeline statistics."""
        pipeline = RAGPipeline(
            search_engine=mock_hybrid_search_engine,
            primary_generator=mock_claude_generator,
            fallback_generator=mock_openai_generator
        )

        stats = pipeline.get_stats()

        assert "primary_generator" in stats
        assert "fallback_generator" in stats
        assert "fallback_enabled" in stats
        assert stats["primary_generator"]["model"] == "claude-sonnet-4-5-20250929"

    async def test_repr(
        self,
        mock_hybrid_search_engine,
        mock_claude_generator
    ):
        """Test string representation."""
        pipeline = RAGPipeline(
            search_engine=mock_hybrid_search_engine,
            primary_generator=mock_claude_generator
        )

        repr_str = repr(pipeline)
        assert "RAGPipeline" in repr_str
        assert "claude-sonnet-4-5-20250929" in repr_str


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
