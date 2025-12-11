"""Chunking strategy router and selector."""

from typing import Optional

from loguru import logger

from src.chunking.chunk_models import (
    ChunkingResult,
    ChunkingConfig,
    ChunkingStrategy
)
from src.chunking.chonkie_wrapper import ChonkieWrapper
from src.chunking.academic_chunker import AcademicChunker
from src.parsers.base import ParsedDocument
from src.indexing.models import DocumentFormat


class ChunkingStrategyRouter:
    """Router for selecting appropriate chunking strategy."""

    def __init__(self, default_config: Optional[ChunkingConfig] = None):
        """
        Initialize chunking router.

        Args:
            default_config: Default chunking configuration
        """
        self.default_config = default_config or ChunkingConfig()
        self.base_chunker = ChonkieWrapper(self.default_config)
        self.academic_chunker = AcademicChunker(self.default_config)

        logger.info("Initialized ChunkingStrategyRouter")

    async def chunk_document(
        self,
        parsed_doc: ParsedDocument,
        strategy: Optional[ChunkingStrategy] = None,
        config: Optional[ChunkingConfig] = None
    ) -> ChunkingResult:
        """
        Chunk document using appropriate strategy.

        Args:
            parsed_doc: Parsed document
            strategy: Override automatic strategy selection
            config: Override default configuration

        Returns:
            ChunkingResult with chunks
        """
        # Use provided config or default
        chunk_config = config or self.default_config

        # Select strategy if not provided
        if strategy is None:
            strategy = self.select_strategy(parsed_doc)

        logger.info(f"Using {strategy.value} strategy for {parsed_doc.document_id}")

        # Route to appropriate chunker
        if strategy == ChunkingStrategy.ACADEMIC:
            return await self.academic_chunker.chunk_paper(
                parsed_doc,
                preserve_sections=chunk_config.preserve_sections,
                preserve_equations=chunk_config.preserve_equations
            )
        else:
            # Use base chunker for token, semantic, or SDPM
            return await self.base_chunker.chunk_text(
                parsed_doc.content,
                parsed_doc.document_id,
                strategy=strategy,
                document_metadata=parsed_doc.metadata
            )

    def select_strategy(self, parsed_doc: ParsedDocument) -> ChunkingStrategy:
        """
        Automatically select best chunking strategy for document.

        Args:
            parsed_doc: Parsed document

        Returns:
            Recommended chunking strategy
        """
        content_length = len(parsed_doc.content)
        word_count = len(parsed_doc.content.split())
        doc_format = parsed_doc.format.lower()

        # Check if academic paper
        is_academic = self._is_academic_paper(parsed_doc)

        # Selection logic
        if is_academic:
            logger.debug("Detected academic paper → using ACADEMIC strategy")
            return ChunkingStrategy.ACADEMIC

        elif doc_format in ["pdf", "docx", "html"] and word_count > 10000:
            logger.debug("Long structured document → using SDPM strategy")
            return ChunkingStrategy.SDPM

        elif doc_format in ["pdf", "docx", "html", "txt", "markdown"]:
            logger.debug("Standard document → using SEMANTIC strategy")
            return ChunkingStrategy.SEMANTIC

        else:
            logger.debug("Simple document → using TOKEN strategy")
            return ChunkingStrategy.TOKEN

    def _is_academic_paper(self, parsed_doc: ParsedDocument) -> bool:
        """
        Determine if document is an academic paper.

        Args:
            parsed_doc: Parsed document

        Returns:
            True if appears to be academic paper
        """
        indicators = 0

        # Check for academic sections
        if parsed_doc.sections:
            section_titles = [
                s.get("title", "").lower()
                for s in parsed_doc.sections
                if isinstance(s, dict)
            ]
            academic_sections = [
                "abstract", "introduction", "methods", "methodology",
                "results", "discussion", "conclusion", "references"
            ]
            if any(sec in " ".join(section_titles) for sec in academic_sections):
                indicators += 2

        # Check for equations
        if parsed_doc.equations and len(parsed_doc.equations) > 0:
            indicators += 1

        # Check for references
        if parsed_doc.references and len(parsed_doc.references) > 5:
            indicators += 1

        # Check metadata for academic indicators
        metadata = parsed_doc.metadata
        if any(key in metadata for key in ["doi", "arxiv_id", "authors", "venue"]):
            indicators += 1

        # Check for tables and figures (common in papers)
        if parsed_doc.tables and len(parsed_doc.tables) > 0:
            indicators += 1
        if parsed_doc.figures and len(parsed_doc.figures) > 0:
            indicators += 1

        # Threshold: >= 3 indicators = academic paper
        is_academic = indicators >= 3

        logger.debug(f"Academic paper indicators: {indicators}/7 → {is_academic}")
        return is_academic

    def get_recommended_config(
        self,
        parsed_doc: ParsedDocument
    ) -> ChunkingConfig:
        """
        Get recommended chunking configuration for document.

        Args:
            parsed_doc: Parsed document

        Returns:
            Recommended chunking configuration
        """
        word_count = len(parsed_doc.content.split())
        is_academic = self._is_academic_paper(parsed_doc)

        # Base configuration
        config = ChunkingConfig()

        # Adjust based on document characteristics
        if is_academic:
            config.strategy = ChunkingStrategy.ACADEMIC
            config.preserve_sections = True
            config.preserve_equations = True
            config.preserve_citations = True
            config.chunk_size = 512
            config.chunk_overlap = 50

        elif word_count > 20000:
            # Very long document
            config.strategy = ChunkingStrategy.SDPM
            config.chunk_size = 1024
            config.chunk_overlap = 100

        elif word_count > 10000:
            # Long document
            config.strategy = ChunkingStrategy.SDPM
            config.chunk_size = 768
            config.chunk_overlap = 75

        elif word_count > 2000:
            # Medium document
            config.strategy = ChunkingStrategy.SEMANTIC
            config.chunk_size = 512
            config.chunk_overlap = 50

        else:
            # Short document
            config.strategy = ChunkingStrategy.TOKEN
            config.chunk_size = 256
            config.chunk_overlap = 25

        logger.debug(f"Recommended config: {config.strategy.value}, size={config.chunk_size}")
        return config
