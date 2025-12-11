"""Metadata extraction for academic research papers."""

import re
from typing import Optional

from loguru import logger

from src.indexing.models import PaperMetadata
from src.parsers.base import ParsedDocument


class MetadataExtractor:
    """Extract metadata from academic research papers."""

    def extract_paper_metadata(
        self,
        parsed_doc: ParsedDocument
    ) -> Optional[PaperMetadata]:
        """
        Extract academic paper metadata from parsed document.

        Args:
            parsed_doc: Parsed document

        Returns:
            PaperMetadata if document appears to be an academic paper, None otherwise
        """
        try:
            content = parsed_doc.content
            metadata = parsed_doc.metadata

            # Extract title
            title = self._extract_title(content, metadata)
            if not title:
                logger.warning("Could not extract title - may not be an academic paper")
                return None

            # Extract authors
            authors = self._extract_authors(content, metadata)

            # Extract year
            year = self._extract_year(content, metadata)

            # Extract abstract
            abstract = self._extract_abstract(content)

            # Extract DOI
            doi = self._extract_doi(content)

            # Extract arXiv ID
            arxiv_id = self._extract_arxiv_id(content)

            # Extract sections
            sections = self._extract_section_names(parsed_doc)

            # Extract keywords
            keywords = self._extract_keywords(content)

            # Create paper metadata
            paper_metadata = PaperMetadata(
                title=title,
                authors=authors,
                year=year,
                abstract=abstract,
                doi=doi,
                arxiv_id=arxiv_id,
                sections=sections,
                keywords=keywords,
                page_count=metadata.get("page_count")
            )

            logger.info(f"Extracted metadata for paper: {title[:50]}...")
            return paper_metadata

        except Exception as e:
            logger.error(f"Failed to extract paper metadata: {e}")
            return None

    def _extract_title(self, content: str, metadata: dict) -> Optional[str]:
        """Extract paper title."""
        # Try metadata first
        if "title" in metadata and metadata["title"]:
            return metadata["title"]

        # Try to find title in first few lines
        lines = content.split("\n")[:20]
        for line in lines:
            line = line.strip()
            if len(line) > 20 and len(line) < 200:  # Reasonable title length
                # Filter out common non-title patterns
                if not any(x in line.lower() for x in ["abstract", "introduction", "keywords"]):
                    return line

        return None

    def _extract_authors(self, content: str, metadata: dict) -> list[str]:
        """Extract author names."""
        authors = []

        # Try metadata first
        if "author" in metadata and metadata["author"]:
            author_str = metadata["author"]
            if isinstance(author_str, str):
                authors = [a.strip() for a in author_str.split(",")]
            elif isinstance(author_str, list):
                authors = author_str

        # Try to find authors in content (common patterns)
        if not authors:
            # Look for author line after title
            lines = content.split("\n")[:30]
            for i, line in enumerate(lines):
                # Common author indicators
                if re.search(r"[A-Z][a-z]+\s+[A-Z][a-z]+(\s+and\s+[A-Z][a-z]+\s+[A-Z][a-z]+)*", line):
                    authors = re.findall(r"[A-Z][a-z]+\s+[A-Z][a-z]+", line)
                    break

        return authors[:10]  # Limit to 10 authors

    def _extract_year(self, content: str, metadata: dict) -> Optional[int]:
        """Extract publication year."""
        # Try metadata first
        if "creation_date" in metadata:
            date_str = metadata["creation_date"]
            if date_str:
                year_match = re.search(r"(19|20)\d{2}", str(date_str))
                if year_match:
                    return int(year_match.group())

        # Look for year in content (first 500 chars)
        year_pattern = r"\b(19|20)\d{2}\b"
        matches = re.findall(year_pattern, content[:500])
        if matches:
            # Return the most recent year found
            years = [int(y) for y in matches]
            return max(years)

        return None

    def _extract_abstract(self, content: str) -> Optional[str]:
        """Extract paper abstract."""
        # Look for abstract section
        abstract_pattern = r"(?i)abstract[\s\n:]+(.+?)(?=\n\n|\bintroduction\b|\b1\.?\s+introduction\b)"
        match = re.search(abstract_pattern, content, re.DOTALL)

        if match:
            abstract = match.group(1).strip()
            # Clean up
            abstract = re.sub(r"\s+", " ", abstract)
            return abstract[:1000]  # Limit length

        return None

    def _extract_doi(self, content: str) -> Optional[str]:
        """Extract DOI."""
        doi_pattern = r"10\.\d{4,}/[^\s]+"
        match = re.search(doi_pattern, content)

        if match:
            doi = match.group().strip()
            # Clean up trailing punctuation
            doi = re.sub(r"[.,;]$", "", doi)
            return doi

        return None

    def _extract_arxiv_id(self, content: str) -> Optional[str]:
        """Extract arXiv ID."""
        arxiv_pattern = r"arXiv:(\d{4}\.\d{4,5})"
        match = re.search(arxiv_pattern, content, re.IGNORECASE)

        if match:
            return match.group(1)

        return None

    def _extract_section_names(self, parsed_doc: ParsedDocument) -> list[str]:
        """Extract section names from document."""
        sections = []

        if parsed_doc.sections:
            for section in parsed_doc.sections:
                if "title" in section:
                    sections.append(section["title"])

        return sections

    def _extract_keywords(self, content: str) -> list[str]:
        """Extract keywords from paper."""
        keywords = []

        # Look for keywords section
        keywords_pattern = r"(?i)keywords?[\s\n:]+(.+?)(?=\n\n|\bintroduction\b)"
        match = re.search(keywords_pattern, content)

        if match:
            keyword_str = match.group(1).strip()
            # Split by common delimiters
            keywords = re.split(r"[,;·•]", keyword_str)
            keywords = [k.strip() for k in keywords if k.strip()]
            keywords = keywords[:10]  # Limit to 10 keywords

        return keywords
