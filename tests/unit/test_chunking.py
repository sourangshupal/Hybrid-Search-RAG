"""Unit tests for chunking module."""

import pytest

from src.chunking.chunk_models import (
    Chunk,
    ChunkingConfig,
    ChunkingStrategy,
    ChunkingResult
)
from src.chunking.validation import ChunkValidator


class TestChunkModels:
    """Tests for chunk models."""

    def test_chunk_creation(self):
        """Test creating a chunk."""
        chunk = Chunk(
            chunk_id="test_chunk_0",
            document_id="test_doc",
            content="This is a test chunk.",
            chunk_index=0,
            chunking_strategy=ChunkingStrategy.TOKEN,
            token_count=5,
            char_count=21
        )

        assert chunk.chunk_id == "test_chunk_0"
        assert chunk.document_id == "test_doc"
        assert chunk.token_count == 5
        assert chunk.chunking_strategy == ChunkingStrategy.TOKEN

    def test_chunk_validation_positive_token_count(self):
        """Test that token count must be positive."""
        with pytest.raises(ValueError, match="Token count must be positive"):
            Chunk(
                chunk_id="test_chunk_0",
                document_id="test_doc",
                content="Test",
                chunk_index=0,
                chunking_strategy=ChunkingStrategy.TOKEN,
                token_count=0,  # Invalid
                char_count=4
            )

    def test_chunking_config_defaults(self):
        """Test chunking config defaults."""
        config = ChunkingConfig()

        assert config.strategy == ChunkingStrategy.SEMANTIC
        assert config.chunk_size == 512
        assert config.chunk_overlap == 50
        assert config.preserve_sections is True

    def test_chunking_config_overlap_validation(self):
        """Test that overlap must be less than chunk size."""
        with pytest.raises(ValueError, match="chunk_overlap must be less than chunk_size"):
            ChunkingConfig(
                chunk_size=100,
                chunk_overlap=100  # Invalid: equal to chunk_size
            )


class TestChunkValidator:
    """Tests for chunk validator."""

    def test_valid_chunk(self):
        """Test validating a valid chunk."""
        validator = ChunkValidator(min_chunk_size=50, max_chunk_size=1000)

        chunk = Chunk(
            chunk_id="test_chunk_0",
            document_id="test_doc",
            content="This is a valid test chunk with enough content.",
            chunk_index=0,
            chunking_strategy=ChunkingStrategy.SEMANTIC,
            token_count=100,
            char_count=47,
            has_complete_sentences=True
        )

        is_valid, error = validator.validate_chunk(chunk)
        assert is_valid is True
        assert error is None

    def test_chunk_too_small(self):
        """Test chunk that is too small."""
        validator = ChunkValidator(min_chunk_size=100)

        chunk = Chunk(
            chunk_id="test_chunk_0",
            document_id="test_doc",
            content="Short.",
            chunk_index=0,
            chunking_strategy=ChunkingStrategy.TOKEN,
            token_count=10,  # Below minimum
            char_count=6
        )

        is_valid, error = validator.validate_chunk(chunk)
        assert is_valid is False
        assert "too small" in error.lower()

    def test_chunk_too_large(self):
        """Test chunk that is too large."""
        validator = ChunkValidator(max_chunk_size=500)

        chunk = Chunk(
            chunk_id="test_chunk_0",
            document_id="test_doc",
            content="Very long content...",
            chunk_index=0,
            chunking_strategy=ChunkingStrategy.TOKEN,
            token_count=1000,  # Above maximum
            char_count=500
        )

        is_valid, error = validator.validate_chunk(chunk)
        assert is_valid is False
        assert "too large" in error.lower()

    def test_empty_chunk_content(self):
        """Test chunk with empty content."""
        validator = ChunkValidator()

        chunk = Chunk(
            chunk_id="test_chunk_0",
            document_id="test_doc",
            content="   ",  # Empty after strip
            chunk_index=0,
            chunking_strategy=ChunkingStrategy.TOKEN,
            token_count=100,
            char_count=3
        )

        is_valid, error = validator.validate_chunk(chunk)
        assert is_valid is False
        assert "empty" in error.lower()

    def test_quality_score(self):
        """Test quality score calculation."""
        validator = ChunkValidator(min_chunk_size=100, max_chunk_size=1000)

        chunk = Chunk(
            chunk_id="test_chunk_0",
            document_id="test_doc",
            content="This is a good quality chunk with complete sentences.",
            chunk_index=0,
            chunking_strategy=ChunkingStrategy.SEMANTIC,
            token_count=500,
            char_count=54,
            has_complete_sentences=True,
            section_title="Introduction"
        )

        score = validator.get_quality_score(chunk)
        assert 0.0 <= score <= 1.0
        assert score > 0.9  # Should have high quality


@pytest.mark.asyncio
class TestChonkieWrapper:
    """Tests for Chonkie wrapper."""

    async def test_token_chunking(self):
        """Test token-based chunking."""
        from src.chunking.chonkie_wrapper import ChonkieWrapper

        config = ChunkingConfig(
            strategy=ChunkingStrategy.TOKEN,
            chunk_size=50,
            chunk_overlap=10
        )
        wrapper = ChonkieWrapper(config)

        text = " ".join(["word"] * 200)  # 200 words
        result = await wrapper.chunk_text(
            text,
            document_id="test_doc",
            strategy=ChunkingStrategy.TOKEN
        )

        assert isinstance(result, ChunkingResult)
        assert result.total_chunks > 0
        assert result.chunking_strategy == ChunkingStrategy.TOKEN
        assert len(result.chunks) == result.total_chunks


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
