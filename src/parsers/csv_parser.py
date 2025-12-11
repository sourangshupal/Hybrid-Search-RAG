"""CSV parser for tabular data."""

import csv
import uuid
from io import StringIO
from pathlib import Path
from typing import Union, BinaryIO, Optional

from loguru import logger

from src.parsers.base import BaseParser, ParsedDocument
from src.core.exceptions import ParsingError


class CSVParser(BaseParser):
    """Parser for CSV files."""

    SUPPORTED_FORMATS = [".csv"]

    async def parse(
        self,
        file_path: Union[str, Path, BinaryIO],
        document_id: Optional[str] = None
    ) -> ParsedDocument:
        """
        Parse CSV file.

        Args:
            file_path: Path to CSV file or file-like object
            document_id: Optional document ID

        Returns:
            ParsedDocument with CSV content as text

        Raises:
            ParsingError: If parsing fails
        """
        try:
            # Generate document ID if not provided
            if document_id is None:
                document_id = str(uuid.uuid4())

            # Read CSV content
            if isinstance(file_path, (str, Path)):
                file_path = Path(file_path)
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    filename = file_path.name
                    file_size = file_path.stat().st_size
            else:
                content = file_path.read().decode("utf-8")
                filename = "uploaded.csv"
                file_size = len(content)

            # Parse CSV to extract structure
            csv_reader = csv.DictReader(StringIO(content))
            rows = list(csv_reader)

            # Convert to markdown table for better readability
            if rows:
                headers = list(rows[0].keys())
                markdown_content = "| " + " | ".join(headers) + " |\n"
                markdown_content += "| " + " | ".join(["---"] * len(headers)) + " |\n"

                for row in rows:
                    markdown_content += "| " + " | ".join(str(row.get(h, "")) for h in headers) + " |\n"
            else:
                markdown_content = content

            metadata = {
                "filename": filename,
                "file_size": file_size,
                "parser": "csv",
                "row_count": len(rows),
                "column_count": len(rows[0]) if rows else 0,
                "columns": list(rows[0].keys()) if rows else []
            }

            # Create table representation
            tables = [{
                "table_id": "main_table",
                "content": rows,
                "row_count": len(rows),
                "column_count": len(rows[0]) if rows else 0
            }] if rows else []

            logger.info(f"Parsed CSV: {len(rows)} rows, {len(rows[0]) if rows else 0} columns")

            return ParsedDocument(
                document_id=document_id,
                content=markdown_content,
                metadata=metadata,
                format="csv",
                tables=tables
            )

        except Exception as e:
            logger.error(f"Failed to parse CSV: {e}")
            raise ParsingError(f"CSV parsing failed: {e}")

    def supports_format(self, file_extension: str) -> bool:
        """Check if format is supported."""
        return file_extension.lower() in self.SUPPORTED_FORMATS

    def get_supported_formats(self) -> list[str]:
        """Get list of supported formats."""
        return self.SUPPORTED_FORMATS
