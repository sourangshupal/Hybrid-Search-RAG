"""Parser factory for selecting appropriate parser based on file type."""

from pathlib import Path
from typing import Union

from loguru import logger

from src.parsers.base import BaseParser
from src.parsers.docling_parser import DoclingParser
from src.parsers.csv_parser import CSVParser
from src.parsers.json_parser import JSONParser
from src.parsers.markdown_parser import MarkdownParser
from src.parsers.txt_parser import TXTParser
from src.core.exceptions import ParsingError


class ParserFactory:
    """Factory for creating appropriate parser based on file format."""

    def __init__(self):
        """Initialize parser factory with available parsers."""
        self.parsers: list[BaseParser] = [
            DoclingParser(),
            CSVParser(),
            JSONParser(),
            MarkdownParser(),
            TXTParser()
        ]

        logger.info(f"Parser factory initialized with {len(self.parsers)} parsers")

    def get_parser(self, file_path: Union[str, Path]) -> BaseParser:
        """
        Get appropriate parser for file.

        Args:
            file_path: Path to file

        Returns:
            Parser instance

        Raises:
            ParsingError: If no parser supports the file format
        """
        file_path = Path(file_path)
        extension = file_path.suffix.lower()

        # Find parser that supports this format
        for parser in self.parsers:
            if parser.supports_format(extension):
                logger.info(f"Selected {parser.__class__.__name__} for {extension}")
                return parser

        raise ParsingError(
            f"No parser available for format: {extension}",
            details={"supported_formats": self.get_supported_formats()}
        )

    def get_supported_formats(self) -> list[str]:
        """
        Get all supported file formats.

        Returns:
            List of supported file extensions
        """
        formats = set()
        for parser in self.parsers:
            formats.update(parser.get_supported_formats())

        return sorted(list(formats))

    def supports_format(self, file_extension: str) -> bool:
        """
        Check if format is supported.

        Args:
            file_extension: File extension to check

        Returns:
            True if format is supported
        """
        return file_extension.lower() in self.get_supported_formats()
