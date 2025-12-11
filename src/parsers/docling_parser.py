"""Docling-based parser for PDF, DOCX, and HTML documents."""

import uuid
from pathlib import Path
from typing import Union, BinaryIO, Optional

from docling.document_converter import DocumentConverter
from loguru import logger

from src.parsers.base import BaseParser, ParsedDocument
from src.core.exceptions import ParsingError
from src.indexing.models import Section, Table, Figure


class DoclingParser(BaseParser):
    """Parser using Docling for PDF, DOCX, and HTML documents."""

    SUPPORTED_FORMATS = [".pdf", ".docx", ".html", ".htm"]

    def __init__(self):
        """Initialize Docling parser."""
        try:
            self.converter = DocumentConverter()
            logger.info("Docling parser initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Docling parser: {e}")
            raise ParsingError(f"Docling initialization failed: {e}")

    async def parse(
        self,
        file_path: Union[str, Path, BinaryIO],
        document_id: Optional[str] = None
    ) -> ParsedDocument:
        """
        Parse document using Docling.

        Args:
            file_path: Path to document file or file-like object
            document_id: Optional document ID

        Returns:
            ParsedDocument with extracted content and metadata

        Raises:
            ParsingError: If parsing fails
        """
        try:
            # Convert file_path to Path object
            if isinstance(file_path, (str, Path)):
                file_path = Path(file_path)
                if not file_path.exists():
                    raise ParsingError(f"File not found: {file_path}")
            else:
                raise ParsingError("Docling parser requires file path, not file object")

            # Generate document ID if not provided
            if document_id is None:
                document_id = str(uuid.uuid4())

            # Convert document
            logger.info(f"Parsing document: {file_path}")
            result = self.converter.convert(str(file_path))

            # Extract content
            content = result.document.export_to_markdown()

            # Extract metadata
            metadata = self._extract_metadata(result, file_path)

            # Extract sections
            sections = self._extract_sections(result)

            # Extract tables
            tables = self._extract_tables(result)

            # Extract figures
            figures = self._extract_figures(result)

            # Extract equations
            equations = self._extract_equations(result)

            # Extract references
            references = self._extract_references(result)

            logger.info(f"Successfully parsed document {document_id}: {len(content)} chars")

            return ParsedDocument(
                document_id=document_id,
                content=content,
                metadata=metadata,
                format=file_path.suffix[1:],  # Remove leading dot
                sections=sections,
                tables=tables,
                figures=figures,
                equations=equations,
                references=references
            )

        except Exception as e:
            logger.error(f"Failed to parse document with Docling: {e}")
            raise ParsingError(
                f"Docling parsing failed: {e}",
                details={"file_path": str(file_path)}
            )

    def _extract_metadata(self, result, file_path: Path) -> dict:
        """Extract metadata from parsed document."""
        metadata = {
            "filename": file_path.name,
            "file_size": file_path.stat().st_size if file_path.exists() else 0,
            "parser": "docling"
        }

        # Try to extract document metadata if available
        if hasattr(result.document, "metadata"):
            doc_metadata = result.document.metadata
            if doc_metadata:
                metadata.update({
                    "title": getattr(doc_metadata, "title", None),
                    "author": getattr(doc_metadata, "author", None),
                    "creation_date": getattr(doc_metadata, "creation_date", None),
                    "modification_date": getattr(doc_metadata, "modification_date", None),
                    "page_count": getattr(doc_metadata, "page_count", None),
                })

        return metadata

    def _extract_sections(self, result) -> list[dict]:
        """Extract document sections with hierarchy."""
        sections = []

        try:
            # Iterate through document structure
            for idx, item in enumerate(result.document.children):
                if hasattr(item, "label") and "heading" in item.label.lower():
                    section = {
                        "section_id": f"section_{idx}",
                        "title": item.text if hasattr(item, "text") else "",
                        "level": int(item.label.split("_")[-1]) if "_" in item.label else 1,
                        "content": "",
                        "position": idx
                    }
                    sections.append(section)
        except Exception as e:
            logger.warning(f"Could not extract sections: {e}")

        return sections

    def _extract_tables(self, result) -> list[dict]:
        """Extract tables from document."""
        tables = []

        try:
            for idx, item in enumerate(result.document.children):
                if hasattr(item, "label") and "table" in item.label.lower():
                    table = {
                        "table_id": f"table_{idx}",
                        "caption": getattr(item, "caption", None),
                        "position": idx,
                        "content": str(item)
                    }
                    tables.append(table)
        except Exception as e:
            logger.warning(f"Could not extract tables: {e}")

        return tables

    def _extract_figures(self, result) -> list[dict]:
        """Extract figures/images from document."""
        figures = []

        try:
            for idx, item in enumerate(result.document.children):
                if hasattr(item, "label") and "figure" in item.label.lower():
                    figure = {
                        "figure_id": f"figure_{idx}",
                        "caption": getattr(item, "caption", None),
                        "position": idx
                    }
                    figures.append(figure)
        except Exception as e:
            logger.warning(f"Could not extract figures: {e}")

        return figures

    def _extract_equations(self, result) -> list[str]:
        """Extract mathematical equations."""
        equations = []

        try:
            for item in result.document.children:
                if hasattr(item, "label") and "formula" in item.label.lower():
                    if hasattr(item, "text"):
                        equations.append(item.text)
        except Exception as e:
            logger.warning(f"Could not extract equations: {e}")

        return equations

    def _extract_references(self, result) -> list[str]:
        """Extract references/bibliography."""
        references = []

        try:
            # Look for references section
            in_references = False
            for item in result.document.children:
                if hasattr(item, "text"):
                    text_lower = item.text.lower()
                    if "references" in text_lower or "bibliography" in text_lower:
                        in_references = True
                        continue

                    if in_references and hasattr(item, "label"):
                        if "heading" in item.label.lower():
                            break  # End of references section
                        references.append(item.text)
        except Exception as e:
            logger.warning(f"Could not extract references: {e}")

        return references

    def supports_format(self, file_extension: str) -> bool:
        """Check if format is supported."""
        return file_extension.lower() in self.SUPPORTED_FORMATS

    def get_supported_formats(self) -> list[str]:
        """Get list of supported formats."""
        return self.SUPPORTED_FORMATS
