"""Wrapper for Chonkie chunking library."""

import uuid
from typing import Optional

from chonkie import TokenChunker, SemanticChunker, SDPMChunker
from loguru import logger

from src.chunking.chunk_models import (
    Chunk,
    ChunkingResult,
    ChunkingConfig,
    ChunkingStrategy
)
from src.core.exceptions import ChunkingError


class ChonkieWrapper:
    """Wrapper for Chonkie chunking strategies."""

    def __init__(self, config: Optional[ChunkingConfig] = None):
        """
        Initialize Chonkie wrapper.

        Args:
            config: Chunking configuration
        """
        self.config = config or ChunkingConfig()
        logger.info(f"Initialized ChonkieWrapper with strategy: {self.config.strategy}")

    async def chunk_text(
        self,
        text: str,
        document_id: str,
        strategy: Optional[ChunkingStrategy] = None,
        document_metadata: Optional[dict] = None
    ) -> ChunkingResult:
        """
        Chunk text using specified strategy.

        Args:
            text: Text to chunk
            document_id: Document identifier
            strategy: Chunking strategy (overrides config)
            document_metadata: Metadata to attach to chunks

        Returns:
            ChunkingResult with chunks

        Raises:
            ChunkingError: If chunking fails
        """
        try:
            strategy = strategy or self.config.strategy
            metadata = document_metadata or {}

            logger.info(f"Chunking document {document_id} with {strategy.value} strategy")

            # Select and apply chunking strategy
            if strategy == ChunkingStrategy.TOKEN:
                chunks = await self._chunk_with_token(text, document_id, metadata)
            elif strategy == ChunkingStrategy.SEMANTIC:
                chunks = await self._chunk_with_semantic(text, document_id, metadata)
            elif strategy == ChunkingStrategy.SDPM:
                chunks = await self._chunk_with_sdpm(text, document_id, metadata)
            else:
                raise ChunkingError(f"Unsupported chunking strategy: {strategy}")

            # Calculate statistics
            chunk_sizes = [c.token_count for c in chunks]
            avg_size = sum(chunk_sizes) / len(chunks) if chunks else 0
            min_size = min(chunk_sizes) if chunks else 0
            max_size = max(chunk_sizes) if chunks else 0

            result = ChunkingResult(
                document_id=document_id,
                chunks=chunks,
                total_chunks=len(chunks),
                chunking_strategy=strategy,
                avg_chunk_size=avg_size,
                min_chunk_size=min_size,
                max_chunk_size=max_size,
                chunk_size=self.config.chunk_size,
                chunk_overlap=self.config.chunk_overlap
            )

            logger.info(f"Created {len(chunks)} chunks (avg: {avg_size:.0f} tokens)")
            return result

        except Exception as e:
            logger.error(f"Chunking failed: {e}")
            raise ChunkingError(f"Failed to chunk document: {e}")

    async def _chunk_with_token(
        self,
        text: str,
        document_id: str,
        metadata: dict
    ) -> list[Chunk]:
        """Chunk text with TokenChunker (fixed-size)."""
        try:
            chunker = TokenChunker(
                chunk_size=self.config.chunk_size,
                chunk_overlap=self.config.chunk_overlap
            )

            # Chunk the text
            raw_chunks = chunker.chunk(text)

            # Convert to Chunk objects
            chunks = []
            for idx, raw_chunk in enumerate(raw_chunks):
                chunk = Chunk(
                    chunk_id=f"{document_id}_chunk_{idx}",
                    document_id=document_id,
                    content=raw_chunk.text,
                    chunk_index=idx,
                    chunking_strategy=ChunkingStrategy.TOKEN,
                    token_count=raw_chunk.token_count,
                    char_count=len(raw_chunk.text),
                    start_char=raw_chunk.start_index,
                    end_char=raw_chunk.end_index,
                    document_metadata=metadata,
                    previous_chunk_id=f"{document_id}_chunk_{idx-1}" if idx > 0 else None,
                    next_chunk_id=f"{document_id}_chunk_{idx+1}" if idx < len(raw_chunks) - 1 else None
                )
                chunks.append(chunk)

            return chunks

        except Exception as e:
            raise ChunkingError(f"TokenChunker failed: {e}")

    async def _chunk_with_semantic(
        self,
        text: str,
        document_id: str,
        metadata: dict
    ) -> list[Chunk]:
        """Chunk text with SemanticChunker (meaning-based)."""
        try:
            chunker = SemanticChunker(
                chunk_size=self.config.chunk_size,
                chunk_overlap=self.config.chunk_overlap,
                similarity_threshold=self.config.similarity_threshold or 0.5
            )

            # Chunk the text
            raw_chunks = chunker.chunk(text)

            # Convert to Chunk objects
            chunks = []
            for idx, raw_chunk in enumerate(raw_chunks):
                chunk = Chunk(
                    chunk_id=f"{document_id}_chunk_{idx}",
                    document_id=document_id,
                    content=raw_chunk.text,
                    chunk_index=idx,
                    chunking_strategy=ChunkingStrategy.SEMANTIC,
                    token_count=raw_chunk.token_count,
                    char_count=len(raw_chunk.text),
                    start_char=raw_chunk.start_index,
                    end_char=raw_chunk.end_index,
                    document_metadata=metadata,
                    previous_chunk_id=f"{document_id}_chunk_{idx-1}" if idx > 0 else None,
                    next_chunk_id=f"{document_id}_chunk_{idx+1}" if idx < len(raw_chunks) - 1 else None
                )
                chunks.append(chunk)

            return chunks

        except Exception as e:
            raise ChunkingError(f"SemanticChunker failed: {e}")

    async def _chunk_with_sdpm(
        self,
        text: str,
        document_id: str,
        metadata: dict
    ) -> list[Chunk]:
        """Chunk text with SDPMChunker (for long documents)."""
        try:
            chunker = SDPMChunker(
                chunk_size=self.config.chunk_size,
                chunk_overlap=self.config.chunk_overlap
            )

            # Chunk the text
            raw_chunks = chunker.chunk(text)

            # Convert to Chunk objects
            chunks = []
            for idx, raw_chunk in enumerate(raw_chunks):
                chunk = Chunk(
                    chunk_id=f"{document_id}_chunk_{idx}",
                    document_id=document_id,
                    content=raw_chunk.text,
                    chunk_index=idx,
                    chunking_strategy=ChunkingStrategy.SDPM,
                    token_count=raw_chunk.token_count,
                    char_count=len(raw_chunk.text),
                    start_char=raw_chunk.start_index,
                    end_char=raw_chunk.end_index,
                    document_metadata=metadata,
                    previous_chunk_id=f"{document_id}_chunk_{idx-1}" if idx > 0 else None,
                    next_chunk_id=f"{document_id}_chunk_{idx+1}" if idx < len(raw_chunks) - 1 else None
                )
                chunks.append(chunk)

            return chunks

        except Exception as e:
            raise ChunkingError(f"SDPMChunker failed: {e}")
