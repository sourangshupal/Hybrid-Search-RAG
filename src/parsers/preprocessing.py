"""Text preprocessing utilities for document processing."""

import re
import unicodedata
from typing import Optional

from loguru import logger


class TextPreprocessor:
    """Utilities for text preprocessing and normalization."""

    @staticmethod
    def normalize_unicode(text: str) -> str:
        """
        Normalize Unicode characters.

        Args:
            text: Input text

        Returns:
            Normalized text
        """
        # Normalize to NFC form (canonical composition)
        text = unicodedata.normalize("NFC", text)
        return text

    @staticmethod
    def normalize_whitespace(text: str) -> str:
        """
        Normalize whitespace in text.

        Args:
            text: Input text

        Returns:
            Text with normalized whitespace
        """
        # Replace multiple spaces with single space
        text = re.sub(r" +", " ", text)

        # Replace multiple newlines with double newline
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Remove trailing/leading whitespace from lines
        lines = [line.strip() for line in text.split("\n")]
        text = "\n".join(lines)

        return text.strip()

    @staticmethod
    def remove_control_characters(text: str) -> str:
        """
        Remove control characters from text.

        Args:
            text: Input text

        Returns:
            Text without control characters
        """
        # Remove control characters except newline and tab
        text = "".join(
            char for char in text
            if unicodedata.category(char) != "Cc" or char in ["\n", "\t"]
        )
        return text

    @staticmethod
    def clean_latex_artifacts(text: str) -> str:
        """
        Clean LaTeX artifacts from text.

        Args:
            text: Input text

        Returns:
            Cleaned text
        """
        # Remove common LaTeX commands
        text = re.sub(r"\\[a-zA-Z]+\{([^}]*)\}", r"\1", text)
        text = re.sub(r"\\[a-zA-Z]+", "", text)

        # Remove LaTeX math mode markers
        text = re.sub(r"\$+", "", text)

        # Remove braces
        text = re.sub(r"[{}]", "", text)

        return text

    @staticmethod
    def preserve_equations(text: str) -> tuple[str, list[str]]:
        """
        Extract and preserve equations from text.

        Args:
            text: Input text

        Returns:
            Tuple of (text with equation placeholders, list of equations)
        """
        equations = []

        # Extract inline equations ($...$)
        def replace_inline(match):
            eq = match.group(1)
            equations.append(eq)
            return f"[EQUATION_{len(equations)-1}]"

        text = re.sub(r"\$([^\$]+)\$", replace_inline, text)

        # Extract display equations ($$...$$)
        def replace_display(match):
            eq = match.group(1)
            equations.append(eq)
            return f"[EQUATION_{len(equations)-1}]"

        text = re.sub(r"\$\$([^\$]+)\$\$", replace_display, text)

        return text, equations

    @staticmethod
    def normalize_citations(text: str) -> str:
        """
        Normalize citation formats.

        Args:
            text: Input text

        Returns:
            Text with normalized citations
        """
        # Normalize common citation patterns
        # [1], [2,3], [Smith et al., 2020]
        text = re.sub(r"\[\s*(\d+(?:\s*,\s*\d+)*)\s*\]", r"[\1]", text)

        return text

    @staticmethod
    def remove_page_numbers(text: str) -> str:
        """
        Remove page numbers from text.

        Args:
            text: Input text

        Returns:
            Text without page numbers
        """
        # Remove standalone numbers at line ends (likely page numbers)
        text = re.sub(r"\n\s*\d+\s*\n", "\n", text)

        return text

    @staticmethod
    def validate_content_quality(text: str, min_length: int = 500) -> bool:
        """
        Validate content quality.

        Args:
            text: Input text
            min_length: Minimum content length in characters

        Returns:
            True if content meets quality criteria
        """
        if not text or len(text.strip()) < min_length:
            logger.warning(f"Content too short: {len(text)} chars")
            return False

        # Check for reasonable word count
        words = text.split()
        if len(words) < 100:
            logger.warning(f"Too few words: {len(words)}")
            return False

        # Check for readable characters
        readable_chars = sum(1 for c in text if c.isalnum() or c.isspace())
        if readable_chars / len(text) < 0.8:
            logger.warning("Too many non-readable characters")
            return False

        return True

    def preprocess_academic_paper(
        self,
        text: str,
        preserve_equations: bool = True,
        remove_latex: bool = False
    ) -> tuple[str, Optional[list[str]]]:
        """
        Preprocess academic paper text.

        Args:
            text: Input text
            preserve_equations: Whether to preserve equations
            remove_latex: Whether to remove LaTeX artifacts

        Returns:
            Tuple of (preprocessed text, equations if preserved)
        """
        equations = None

        # Normalize Unicode
        text = self.normalize_unicode(text)

        # Remove control characters
        text = self.remove_control_characters(text)

        # Preserve equations if requested
        if preserve_equations:
            text, equations = self.preserve_equations(text)

        # Clean LaTeX if requested
        if remove_latex:
            text = self.clean_latex_artifacts(text)

        # Normalize whitespace
        text = self.normalize_whitespace(text)

        # Normalize citations
        text = self.normalize_citations(text)

        # Remove page numbers
        text = self.remove_page_numbers(text)

        return text, equations

    def preprocess_general_text(self, text: str) -> str:
        """
        Preprocess general text.

        Args:
            text: Input text

        Returns:
            Preprocessed text
        """
        # Normalize Unicode
        text = self.normalize_unicode(text)

        # Remove control characters
        text = self.remove_control_characters(text)

        # Normalize whitespace
        text = self.normalize_whitespace(text)

        return text
