"""JSON parser for structured data."""

import json
import uuid
from pathlib import Path
from typing import Union, BinaryIO, Optional

from loguru import logger

from src.parsers.base import BaseParser, ParsedDocument
from src.core.exceptions import ParsingError


class JSONParser(BaseParser):
    """Parser for JSON files."""

    SUPPORTED_FORMATS = [".json", ".jsonl"]

    async def parse(
        self,
        file_path: Union[str, Path, BinaryIO],
        document_id: Optional[str] = None
    ) -> ParsedDocument:
        """
        Parse JSON file.

        Args:
            file_path: Path to JSON file or file-like object
            document_id: Optional document ID

        Returns:
            ParsedDocument with JSON content as formatted text

        Raises:
            ParsingError: If parsing fails
        """
        try:
            # Generate document ID if not provided
            if document_id is None:
                document_id = str(uuid.uuid4())

            # Read JSON content
            if isinstance(file_path, (str, Path)):
                file_path = Path(file_path)
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    filename = file_path.name
                    file_size = file_path.stat().st_size
            else:
                content = file_path.read().decode("utf-8")
                filename = "uploaded.json"
                file_size = len(content)

            # Parse JSON
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                raise ParsingError(f"Invalid JSON: {e}")

            # Convert to human-readable format
            formatted_content = json.dumps(data, indent=2, ensure_ascii=False)

            # Extract metadata
            metadata = {
                "filename": filename,
                "file_size": file_size,
                "parser": "json",
                "data_type": type(data).__name__
            }

            if isinstance(data, list):
                metadata["item_count"] = len(data)
            elif isinstance(data, dict):
                metadata["key_count"] = len(data.keys())
                metadata["keys"] = list(data.keys())[:10]  # First 10 keys

            logger.info(f"Parsed JSON: {metadata.get('data_type')}")

            return ParsedDocument(
                document_id=document_id,
                content=formatted_content,
                metadata=metadata,
                format="json"
            )

        except Exception as e:
            logger.error(f"Failed to parse JSON: {e}")
            raise ParsingError(f"JSON parsing failed: {e}")

    def supports_format(self, file_extension: str) -> bool:
        """Check if format is supported."""
        return file_extension.lower() in self.SUPPORTED_FORMATS

    def get_supported_formats(self) -> list[str]:
        """Get list of supported formats."""
        return self.SUPPORTED_FORMATS
