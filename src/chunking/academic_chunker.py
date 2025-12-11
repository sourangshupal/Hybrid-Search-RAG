"""Academic paper specific chunking strategies."""

import re
from typing import Optional

from loguru import logger

from src.chunking.chunk_models import (
    Chunk,
    ChunkingResult,
    ChunkingConfig,
    ChunkingStrategy
)
from src.chunking.chonkie_wrapper import ChonkieWrapper
from src.parsers.base import ParsedDocument
from src.core.exceptions import ChunkingError


class AcademicChunker:
    """Chunker optimized for academic research papers."""

    def __init__(self, config: Optional[ChunkingConfig] = None):
        """
        Initialize academic chunker.

        Args:
            config: Chunking configuration
        """
        self.config = config or ChunkingConfig(strategy=ChunkingStrategy.ACADEMIC)
        self.base_chunker = ChonkieWrapper(config)
        logger.info("Initialized AcademicChunker")

    async def chunk_paper(
        self,
        parsed_doc: ParsedDocument,
        preserve_sections: bool = True,
        preserve_equations: bool = True,
        preserve_abstract: bool = True
    ) -> ChunkingResult:
        """
        Chunk academic paper with structure preservation.

        Args:
            parsed_doc: Parsed document
            preserve_sections: Keep section boundaries
            preserve_equations: Don't split equations
            preserve_abstract: Keep abstract as single chunk

        Returns:
            ChunkingResult with academically-aware chunks

        Raises:
            ChunkingError: If chunking fails
        """
        try:
            logger.info(f"Chunking academic paper: {parsed_doc.document_id}")

            chunks = []
            chunk_index = 0

            # Handle abstract separately if requested
            if preserve_abstract and parsed_doc.sections:
                abstract_chunk = self._create_abstract_chunk(
                    parsed_doc,
                    chunk_index
                )
                if abstract_chunk:
                    chunks.append(abstract_chunk)
                    chunk_index += 1

            # Process sections if available
            if preserve_sections and parsed_doc.sections:
                section_chunks = await self._chunk_by_sections(
                    parsed_doc,
                    chunk_index
                )
                chunks.extend(section_chunks)
                chunk_index += len(section_chunks)

            # If no sections or not preserving them, use base chunking
            if not chunks:
                # Prepare content
                content = self._prepare_content(
                    parsed_doc.content,
                    preserve_equations
                )

                # Use semantic chunking for long papers, token for shorter
                word_count = len(parsed_doc.content.split())
                strategy = (
                    ChunkingStrategy.SDPM if word_count > 10000
                    else ChunkingStrategy.SEMANTIC
                )

                result = await self.base_chunker.chunk_text(
                    content,
                    parsed_doc.document_id,
                    strategy=strategy,
                    document_metadata=parsed_doc.metadata
                )
                chunks = result.chunks

            # Post-process chunks
            chunks = self._post_process_chunks(chunks, preserve_equations)

            # Link chunks
            chunks = self._link_chunks(chunks)

            # Calculate statistics
            chunk_sizes = [c.token_count for c in chunks]
            avg_size = sum(chunk_sizes) / len(chunks) if chunks else 0
            min_size = min(chunk_sizes) if chunks else 0
            max_size = max(chunk_sizes) if chunks else 0

            result = ChunkingResult(
                document_id=parsed_doc.document_id,
                chunks=chunks,
                total_chunks=len(chunks),
                chunking_strategy=ChunkingStrategy.ACADEMIC,
                avg_chunk_size=avg_size,
                min_chunk_size=min_size,
                max_chunk_size=max_size,
                chunk_size=self.config.chunk_size,
                chunk_overlap=self.config.chunk_overlap
            )

            logger.info(f"Created {len(chunks)} academic chunks")
            return result

        except Exception as e:
            logger.error(f"Academic chunking failed: {e}")
            raise ChunkingError(f"Failed to chunk academic paper: {e}")

    def _create_abstract_chunk(
        self,
        parsed_doc: ParsedDocument,
        chunk_index: int
    ) -> Optional[Chunk]:
        """Create a single chunk for the abstract."""
        # Find abstract section
        for section in parsed_doc.sections:
            if "abstract" in section.get("title", "").lower():
                content = section.get("content", "")
                if content:
                    return Chunk(
                        chunk_id=f"{parsed_doc.document_id}_chunk_{chunk_index}",
                        document_id=parsed_doc.document_id,
                        content=content,
                        chunk_index=chunk_index,
                        chunking_strategy=ChunkingStrategy.ACADEMIC,
                        token_count=len(content.split()),  # Approximate
                        char_count=len(content),
                        section_title="Abstract",
                        section_level=1,
                        document_metadata=parsed_doc.metadata
                    )
        return None

    async def _chunk_by_sections(
        self,
        parsed_doc: ParsedDocument,
        start_index: int
    ) -> list[Chunk]:
        """Chunk document by sections."""
        chunks = []
        chunk_index = start_index

        for section in parsed_doc.sections:
            section_title = section.get("title", "")
            section_content = section.get("content", "")
            section_level = section.get("level", 1)

            if not section_content or "abstract" in section_title.lower():
                continue

            # If section is short enough, keep as single chunk
            word_count = len(section_content.split())
            if word_count < self.config.chunk_size:
                chunk = Chunk(
                    chunk_id=f"{parsed_doc.document_id}_chunk_{chunk_index}",
                    document_id=parsed_doc.document_id,
                    content=f"## {section_title}\n\n{section_content}",
                    chunk_index=chunk_index,
                    chunking_strategy=ChunkingStrategy.ACADEMIC,
                    token_count=word_count,
                    char_count=len(section_content),
                    section_title=section_title,
                    section_level=section_level,
                    document_metadata=parsed_doc.metadata
                )
                chunks.append(chunk)
                chunk_index += 1
            else:
                # Section is too long, sub-chunk it
                section_result = await self.base_chunker.chunk_text(
                    section_content,
                    parsed_doc.document_id,
                    strategy=ChunkingStrategy.SEMANTIC,
                    document_metadata=parsed_doc.metadata
                )

                # Add section context to sub-chunks
                for sub_chunk in section_result.chunks:
                    sub_chunk.chunk_index = chunk_index
                    sub_chunk.chunk_id = f"{parsed_doc.document_id}_chunk_{chunk_index}"
                    sub_chunk.section_title = section_title
                    sub_chunk.section_level = section_level
                    sub_chunk.chunking_strategy = ChunkingStrategy.ACADEMIC
                    chunks.append(sub_chunk)
                    chunk_index += 1

        return chunks

    def _prepare_content(
        self,
        content: str,
        preserve_equations: bool
    ) -> str:
        """Prepare content for chunking."""
        if preserve_equations:
            # Mark equations to prevent splitting
            content = re.sub(
                r"(\$[^\$]+\$)",
                r"[EQUATION_START]\1[EQUATION_END]",
                content
            )
            content = re.sub(
                r"(\$\$[^\$]+\$\$)",
                r"[EQUATION_START]\1[EQUATION_END]",
                content
            )

        return content

    def _post_process_chunks(
        self,
        chunks: list[Chunk],
        preserve_equations: bool
    ) -> list[Chunk]:
        """Post-process chunks for academic content."""
        for chunk in chunks:
            # Check for equations
            chunk.has_equations = bool(
                re.search(r"\$[^\$]+\$|\$\$[^\$]+\$\$", chunk.content)
            )

            # Check for citations
            chunk.has_citations = bool(
                re.search(r"\[\d+\]|\([^\)]*\d{4}[^\)]*\)", chunk.content)
            )

            # Check for complete sentences
            chunk.has_complete_sentences = (
                chunk.content.strip().endswith((".", "!", "?"))
            )

            # Clean equation markers if present
            if preserve_equations:
                chunk.content = chunk.content.replace("[EQUATION_START]", "")
                chunk.content = chunk.content.replace("[EQUATION_END]", "")

        return chunks

    def _link_chunks(self, chunks: list[Chunk]) -> list[Chunk]:
        """Link chunks together."""
        for i, chunk in enumerate(chunks):
            if i > 0:
                chunk.previous_chunk_id = chunks[i - 1].chunk_id
            if i < len(chunks) - 1:
                chunk.next_chunk_id = chunks[i + 1].chunk_id

        return chunks
