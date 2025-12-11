"""Plain text parser for TXT files."""

import uuid
from pathlib import Path
from typing import Union, BinaryIO, Optional

from loguru import logger

from src.parsers.base import BaseParser, ParsedDocument
from src.core.exceptions import ParsingError


class TXTParser(BaseParser):
    """Parser for plain text files."""

    SUPPORTED_FORMATS = [".txt"]

    async def parse(
        self,
        file_path: Union[str, Path, BinaryIO],
        document_id: Optional[str] = None
    ) -> ParsedDocument:
        """
        Parse plain text file.

        Args:
            file_path: Path to text file or file-like object
            document_id: Optional document ID

        Returns:
            ParsedDocument with text content

        Raises:
            ParsingError: If parsing fails
        """
        try:
            # Generate document ID if not provided
            if document_id is None:
                document_id = str(uuid.uuid4())

            # Read text content
            if isinstance(file_path, (str, Path)):
                file_path = Path(file_path)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                except UnicodeDecodeError:
                    # Try with latin-1 encoding
                    with open(file_path, "r", encoding="latin-1") as f:
                        content = f.read()

                filename = file_path.name
                file_size = file_path.stat().st_size
            else:
                try:
                    content = file_path.read().decode("utf-8")
                except UnicodeDecodeError:
                    content = file_path.read().decode("latin-1")

                filename = "uploaded.txt"
                file_size = len(content)

            # Basic content analysis
            lines = content.split("\n")
            paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]

            metadata = {
                "filename": filename,
                "file_size": file_size,
                "parser": "txt",
                "line_count": len(lines),
                "paragraph_count": len(paragraphs),
                "character_count": len(content),
                "word_count": len(content.split())
            }

            logger.info(f"Parsed TXT: {len(lines)} lines, {len(paragraphs)} paragraphs")

            return ParsedDocument(
                document_id=document_id,
                content=content,
                metadata=metadata,
                format="txt"
            )

        except Exception as e:
            logger.error(f"Failed to parse TXT: {e}")
            raise ParsingError(f"TXT parsing failed: {e}")

    def supports_format(self, file_extension: str) -> bool:
        """Check if format is supported."""
        return file_extension.lower() in self.SUPPORTED_FORMATS

    def get_supported_formats(self) -> list[str]:
        """Get list of supported formats."""
        return self.SUPPORTED_FORMATS
