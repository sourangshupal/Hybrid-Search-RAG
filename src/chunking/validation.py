"""Chunk quality validation utilities."""

import re
from typing import Optional

from loguru import logger

from src.chunking.chunk_models import Chunk, ChunkingResult


class ChunkValidator:
    """Validator for chunk quality."""

    def __init__(
        self,
        min_chunk_size: int = 100,
        max_chunk_size: int = 2048,
        require_complete_sentences: bool = False
    ):
        """
        Initialize chunk validator.

        Args:
            min_chunk_size: Minimum chunk size in tokens
            max_chunk_size: Maximum chunk size in tokens
            require_complete_sentences: Whether chunks must end with complete sentences
        """
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.require_complete_sentences = require_complete_sentences

    def validate_chunk(self, chunk: Chunk) -> tuple[bool, Optional[str]]:
        """
        Validate a single chunk.

        Args:
            chunk: Chunk to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check size constraints
        if chunk.token_count < self.min_chunk_size:
            return False, f"Chunk too small: {chunk.token_count} < {self.min_chunk_size}"

        if chunk.token_count > self.max_chunk_size:
            return False, f"Chunk too large: {chunk.token_count} > {self.max_chunk_size}"

        # Check for empty content
        if not chunk.content.strip():
            return False, "Chunk content is empty"

        # Check for complete sentences if required
        if self.require_complete_sentences and not chunk.has_complete_sentences:
            if not self._has_complete_sentence(chunk.content):
                logger.warning(f"Chunk {chunk.chunk_id} doesn't end with complete sentence")

        # Check for broken equations
        if chunk.has_equations:
            if not self._validate_equations(chunk.content):
                return False, "Chunk contains broken equations"

        # Check for reasonable character/token ratio
        if chunk.token_count > 0:
            char_token_ratio = chunk.char_count / chunk.token_count
            if char_token_ratio < 2 or char_token_ratio > 10:
                logger.warning(
                    f"Unusual char/token ratio for chunk {chunk.chunk_id}: {char_token_ratio:.2f}"
                )

        return True, None

    def validate_chunking_result(
        self,
        result: ChunkingResult
    ) -> tuple[bool, list[str]]:
        """
        Validate entire chunking result.

        Args:
            result: Chunking result to validate

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Validate each chunk
        for chunk in result.chunks:
            is_valid, error = self.validate_chunk(chunk)
            if not is_valid:
                errors.append(f"Chunk {chunk.chunk_index}: {error}")

        # Check for chunk overlap consistency
        if result.chunk_overlap > 0:
            overlap_errors = self._validate_overlaps(result.chunks, result.chunk_overlap)
            errors.extend(overlap_errors)

        # Check chunk ordering
        for i, chunk in enumerate(result.chunks):
            if chunk.chunk_index != i:
                errors.append(
                    f"Chunk index mismatch: expected {i}, got {chunk.chunk_index}"
                )

        # Check chunk linking
        link_errors = self._validate_links(result.chunks)
        errors.extend(link_errors)

        # Check statistics
        if result.total_chunks != len(result.chunks):
            errors.append(
                f"Total chunks mismatch: {result.total_chunks} != {len(result.chunks)}"
            )

        is_valid = len(errors) == 0
        if not is_valid:
            logger.warning(f"Chunking validation found {len(errors)} errors")

        return is_valid, errors

    def _has_complete_sentence(self, text: str) -> bool:
        """Check if text ends with a complete sentence."""
        text = text.strip()
        return bool(text) and text[-1] in ".!?"

    def _validate_equations(self, content: str) -> bool:
        """Validate equations are not broken."""
        # Check for unmatched dollar signs (LaTeX math mode)
        dollar_count = content.count("$")
        if dollar_count % 2 != 0:
            return False

        # Check for balanced braces
        open_braces = content.count("{")
        close_braces = content.count("}")
        if abs(open_braces - close_braces) > 2:  # Allow small mismatch
            return False

        return True

    def _validate_overlaps(
        self,
        chunks: list[Chunk],
        expected_overlap: int
    ) -> list[str]:
        """Validate chunk overlaps."""
        errors = []

        for i in range(len(chunks) - 1):
            curr_chunk = chunks[i]
            next_chunk = chunks[i + 1]

            # Check if chunks have position information
            if curr_chunk.end_char is not None and next_chunk.start_char is not None:
                # Calculate actual overlap
                if curr_chunk.end_char <= next_chunk.start_char:
                    # No overlap - this might be intentional for section-based chunking
                    continue

                overlap = curr_chunk.end_char - next_chunk.start_char

                # Allow some flexibility
                if abs(overlap - expected_overlap) > expected_overlap * 0.5:
                    logger.debug(
                        f"Overlap deviation: expected ~{expected_overlap}, got {overlap}"
                    )

        return errors

    def _validate_links(self, chunks: list[Chunk]) -> list[str]:
        """Validate chunk linking."""
        errors = []

        for i, chunk in enumerate(chunks):
            # Check previous link
            if i > 0:
                expected_prev = chunks[i - 1].chunk_id
                if chunk.previous_chunk_id != expected_prev:
                    errors.append(
                        f"Chunk {i} previous link incorrect: "
                        f"{chunk.previous_chunk_id} != {expected_prev}"
                    )

            # Check next link
            if i < len(chunks) - 1:
                expected_next = chunks[i + 1].chunk_id
                if chunk.next_chunk_id != expected_next:
                    errors.append(
                        f"Chunk {i} next link incorrect: "
                        f"{chunk.next_chunk_id} != {expected_next}"
                    )

        return errors

    def get_quality_score(self, chunk: Chunk) -> float:
        """
        Calculate quality score for chunk (0-1).

        Args:
            chunk: Chunk to score

        Returns:
            Quality score between 0 and 1
        """
        score = 1.0

        # Penalize for size extremes
        if chunk.token_count < self.min_chunk_size:
            score -= 0.3
        elif chunk.token_count > self.max_chunk_size:
            score -= 0.2

        # Reward complete sentences
        if chunk.has_complete_sentences:
            score += 0.1

        # Reward preserved structure
        if chunk.section_title:
            score += 0.1

        # Penalize broken equations
        if chunk.has_equations and not self._validate_equations(chunk.content):
            score -= 0.3

        return max(0.0, min(1.0, score))
