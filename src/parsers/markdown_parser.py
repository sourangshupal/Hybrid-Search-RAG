"""Markdown parser for markdown documents."""

import re
import uuid
from pathlib import Path
from typing import Union, BinaryIO, Optional

from loguru import logger

from src.parsers.base import BaseParser, ParsedDocument
from src.core.exceptions import ParsingError


class MarkdownParser(BaseParser):
    """Parser for Markdown files."""

    SUPPORTED_FORMATS = [".md", ".markdown"]

    async def parse(
        self,
        file_path: Union[str, Path, BinaryIO],
        document_id: Optional[str] = None
    ) -> ParsedDocument:
        """
        Parse Markdown file.

        Args:
            file_path: Path to Markdown file or file-like object
            document_id: Optional document ID

        Returns:
            ParsedDocument with Markdown content

        Raises:
            ParsingError: If parsing fails
        """
        try:
            # Generate document ID if not provided
            if document_id is None:
                document_id = str(uuid.uuid4())

            # Read Markdown content
            if isinstance(file_path, (str, Path)):
                file_path = Path(file_path)
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    filename = file_path.name
                    file_size = file_path.stat().st_size
            else:
                content = file_path.read().decode("utf-8")
                filename = "uploaded.md"
                file_size = len(content)

            # Extract sections based on headers
            sections = self._extract_sections(content)

            # Extract code blocks
            code_blocks = re.findall(r"```[\s\S]*?```", content)

            # Extract links
            links = re.findall(r"\[([^\]]+)\]\(([^\)]+)\)", content)

            metadata = {
                "filename": filename,
                "file_size": file_size,
                "parser": "markdown",
                "section_count": len(sections),
                "code_block_count": len(code_blocks),
                "link_count": len(links)
            }

            logger.info(f"Parsed Markdown: {len(sections)} sections, {len(code_blocks)} code blocks")

            return ParsedDocument(
                document_id=document_id,
                content=content,
                metadata=metadata,
                format="markdown",
                sections=sections
            )

        except Exception as e:
            logger.error(f"Failed to parse Markdown: {e}")
            raise ParsingError(f"Markdown parsing failed: {e}")

    def _extract_sections(self, content: str) -> list[dict]:
        """Extract sections based on markdown headers."""
        sections = []
        lines = content.split("\n")
        current_section = None
        section_content = []

        for idx, line in enumerate(lines):
            # Check for headers (# Header)
            header_match = re.match(r"^(#{1,6})\s+(.+)$", line)

            if header_match:
                # Save previous section
                if current_section:
                    current_section["content"] = "\n".join(section_content)
                    sections.append(current_section)

                # Start new section
                level = len(header_match.group(1))
                title = header_match.group(2).strip()
                current_section = {
                    "section_id": f"section_{len(sections)}",
                    "title": title,
                    "level": level,
                    "position": idx,
                    "content": ""
                }
                section_content = []
            elif current_section:
                section_content.append(line)

        # Save last section
        if current_section:
            current_section["content"] = "\n".join(section_content)
            sections.append(current_section)

        return sections

    def supports_format(self, file_extension: str) -> bool:
        """Check if format is supported."""
        return file_extension.lower() in self.SUPPORTED_FORMATS

    def get_supported_formats(self) -> list[str]:
        """Get list of supported formats."""
        return self.SUPPORTED_FORMATS
