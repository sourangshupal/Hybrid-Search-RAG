"""Prompt templates for RAG generation with LLMs."""

from typing import Dict, List, Any, Optional
from enum import Enum


class QueryType(str, Enum):
    """Types of research queries."""

    METHODOLOGICAL = "methodological"
    RESULTS = "results"
    COMPARATIVE = "comparative"
    DEFINITION = "definition"
    GENERAL = "general"


class PromptTemplates:
    """Templates for academic research RAG prompts."""

    # System prompts for different query types
    SYSTEM_PROMPTS = {
        QueryType.METHODOLOGICAL: """You are an expert research assistant specializing in explaining methodologies and techniques from academic papers.

Your role:
- Explain methods, algorithms, and approaches clearly and accurately
- Focus on implementation details and technical specifics
- Reference the original papers and authors
- Include relevant equations or pseudocode when helpful
- Clarify assumptions and limitations

Always cite sources using [Author Year] format.""",

        QueryType.RESULTS: """You are an expert research assistant specializing in analyzing experimental results and findings from academic papers.

Your role:
- Summarize key results and performance metrics accurately
- Compare results across different papers when relevant
- Explain the significance and implications of findings
- Note experimental settings and conditions
- Highlight strengths and limitations of evaluations

Always cite sources using [Author Year] format.""",

        QueryType.COMPARATIVE: """You are an expert research assistant specializing in comparative analysis of research papers and approaches.

Your role:
- Compare and contrast different methods, models, or techniques
- Highlight key differences and similarities
- Discuss trade-offs and relative advantages
- Synthesize insights from multiple papers
- Provide balanced, objective comparisons

Always cite sources using [Author Year] format.""",

        QueryType.DEFINITION: """You are an expert research assistant specializing in explaining concepts and definitions from academic research.

Your role:
- Provide clear, accurate definitions of technical terms
- Explain concepts in context of the broader field
- Include examples and use cases when helpful
- Reference seminal papers and key contributions
- Build from basic to advanced understanding

Always cite sources using [Author Year] format.""",

        QueryType.GENERAL: """You are an expert research assistant helping users understand academic research papers.

Your role:
- Provide accurate, well-sourced answers to research questions
- Synthesize information from multiple papers
- Explain complex concepts clearly
- Maintain academic rigor and precision
- Acknowledge uncertainty when appropriate

Always cite sources using [Author Year] format."""
    }

    # Base prompt template for RAG
    BASE_RAG_TEMPLATE = """Based on the provided research paper excerpts, please answer the following question.

Question: {query}

Context from research papers:
{context}

Instructions:
- Answer the question using only information from the provided context
- Cite specific papers using [Author Year] format
- If the context doesn't contain enough information to fully answer the question, acknowledge this
- Be precise and accurate in your response
- Include relevant details like metrics, methods, or findings
- Structure your answer clearly

Answer:"""

    # Template for methodological queries
    METHODOLOGICAL_TEMPLATE = """Based on the provided research paper excerpts, please explain the methodology for the following question.

Question: {query}

Research Paper Context:
{context}

Instructions:
- Focus on technical details and implementation specifics
- Explain the approach step-by-step if applicable
- Include algorithmic details, architectures, or procedures
- Cite papers using [Author Year] format for each method mentioned
- Note any assumptions or prerequisites
- Mention datasets, hyperparameters, or experimental setup if relevant

Explanation:"""

    # Template for results queries
    RESULTS_TEMPLATE = """Based on the provided research paper excerpts, please summarize the results for the following question.

Question: {query}

Research Paper Context:
{context}

Instructions:
- Report specific metrics, scores, or performance numbers
- Include experimental conditions and settings
- Compare results across papers if multiple are relevant
- Note any limitations or caveats mentioned by authors
- Cite papers using [Author Year] format
- Be quantitatively precise (include exact numbers when available)

Summary:"""

    # Template for comparative queries
    COMPARATIVE_TEMPLATE = """Based on the provided research paper excerpts, please compare and contrast the approaches for the following question.

Question: {query}

Research Paper Context:
{context}

Instructions:
- Identify key similarities and differences
- Compare methodologies, results, or approaches
- Discuss relative strengths and weaknesses
- Use a structured format (e.g., bullet points or table if helpful)
- Cite papers using [Author Year] format
- Provide objective, balanced analysis

Comparison:"""

    # Template for definition queries
    DEFINITION_TEMPLATE = """Based on the provided research paper excerpts, please explain the concept or provide a definition for the following question.

Question: {query}

Research Paper Context:
{context}

Instructions:
- Provide a clear, accurate definition
- Explain the concept in context
- Include examples or applications if helpful
- Build from intuition to technical details
- Cite papers using [Author Year] format, especially seminal works
- Clarify any common misconceptions

Explanation:"""

    # Template for streaming responses
    STREAMING_SYSTEM_PROMPT = """You are a research assistant providing answers based on academic papers. Stream your response naturally while maintaining accuracy and proper citations."""

    @classmethod
    def get_system_prompt(cls, query_type: QueryType = QueryType.GENERAL) -> str:
        """
        Get system prompt for query type.

        Args:
            query_type: Type of query

        Returns:
            System prompt string
        """
        return cls.SYSTEM_PROMPTS.get(query_type, cls.SYSTEM_PROMPTS[QueryType.GENERAL])

    @classmethod
    def get_user_prompt(
        cls,
        query: str,
        context: str,
        query_type: QueryType = QueryType.GENERAL
    ) -> str:
        """
        Get user prompt for query.

        Args:
            query: User's question
            context: Retrieved context from papers
            query_type: Type of query

        Returns:
            Formatted user prompt
        """
        templates = {
            QueryType.METHODOLOGICAL: cls.METHODOLOGICAL_TEMPLATE,
            QueryType.RESULTS: cls.RESULTS_TEMPLATE,
            QueryType.COMPARATIVE: cls.COMPARATIVE_TEMPLATE,
            QueryType.DEFINITION: cls.DEFINITION_TEMPLATE,
            QueryType.GENERAL: cls.BASE_RAG_TEMPLATE
        }

        template = templates.get(query_type, cls.BASE_RAG_TEMPLATE)
        return template.format(query=query, context=context)

    @classmethod
    def format_context(
        cls,
        chunks: List[Dict[str, Any]],
        include_metadata: bool = True,
        max_chunks: Optional[int] = None
    ) -> str:
        """
        Format retrieved chunks into context string.

        Args:
            chunks: List of retrieved chunks with content and metadata
            include_metadata: Whether to include metadata (title, authors, year)
            max_chunks: Maximum number of chunks to include

        Returns:
            Formatted context string
        """
        if max_chunks:
            chunks = chunks[:max_chunks]

        context_parts = []

        for i, chunk in enumerate(chunks, 1):
            # Extract metadata
            metadata = chunk.get("metadata", {})
            content = chunk.get("content", "")

            # Build context entry
            if include_metadata:
                title = metadata.get("title", "Unknown")
                authors = metadata.get("authors", "Unknown")
                year = metadata.get("year", "N/A")

                # Format: [Source 1] Title (Authors, Year)
                header = f"[Source {i}] {title}"
                if authors != "Unknown" or year != "N/A":
                    header += f" ({authors}, {year})"

                context_parts.append(f"{header}\n{content}")
            else:
                context_parts.append(f"[Source {i}]\n{content}")

        return "\n\n---\n\n".join(context_parts)

    @classmethod
    def format_context_with_scores(
        cls,
        chunks: List[Dict[str, Any]],
        show_scores: bool = True,
        max_chunks: Optional[int] = None
    ) -> str:
        """
        Format context with relevance scores.

        Args:
            chunks: List of chunks with scores
            show_scores: Whether to show relevance scores
            max_chunks: Maximum chunks to include

        Returns:
            Formatted context with scores
        """
        if max_chunks:
            chunks = chunks[:max_chunks]

        context_parts = []

        for i, chunk in enumerate(chunks, 1):
            metadata = chunk.get("metadata", {})
            content = chunk.get("content", "")
            score = chunk.get("score", 0.0)

            title = metadata.get("title", "Unknown")
            authors = metadata.get("authors", "Unknown")
            year = metadata.get("year", "N/A")

            # Format header with optional score
            header = f"[Source {i}] {title}"
            if authors != "Unknown" or year != "N/A":
                header += f" ({authors}, {year})"
            if show_scores:
                header += f" [Relevance: {score:.3f}]"

            context_parts.append(f"{header}\n{content}")

        return "\n\n---\n\n".join(context_parts)

    @classmethod
    def extract_citation_info(cls, chunks: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """
        Extract citation information from chunks.

        Args:
            chunks: List of chunks with metadata

        Returns:
            List of citation dictionaries
        """
        citations = []
        seen = set()

        for chunk in chunks:
            metadata = chunk.get("metadata", {})

            # Create citation key
            authors = metadata.get("authors", "Unknown")
            year = metadata.get("year", "N/A")
            title = metadata.get("title", "Unknown")

            citation_key = f"{authors}_{year}_{title}"

            if citation_key not in seen:
                seen.add(citation_key)
                citations.append({
                    "authors": authors,
                    "year": str(year),
                    "title": title,
                    "venue": metadata.get("venue", ""),
                    "doi": metadata.get("doi", ""),
                    "arxiv_id": metadata.get("arxiv_id", "")
                })

        return citations

    @classmethod
    def format_citations(cls, citations: List[Dict[str, str]]) -> str:
        """
        Format citations in academic style.

        Args:
            citations: List of citation dictionaries

        Returns:
            Formatted citations string
        """
        if not citations:
            return ""

        formatted = ["References:"]

        for i, cit in enumerate(citations, 1):
            authors = cit.get("authors", "Unknown")
            year = cit.get("year", "N/A")
            title = cit.get("title", "Unknown")
            venue = cit.get("venue", "")
            doi = cit.get("doi", "")
            arxiv_id = cit.get("arxiv_id", "")

            # Format: [1] Authors (Year). Title. Venue. DOI/ArXiv
            citation_str = f"[{i}] {authors} ({year}). {title}."

            if venue:
                citation_str += f" {venue}."

            if doi:
                citation_str += f" DOI: {doi}"
            elif arxiv_id:
                citation_str += f" arXiv: {arxiv_id}"

            formatted.append(citation_str)

        return "\n".join(formatted)

    @classmethod
    def create_full_prompt(
        cls,
        query: str,
        chunks: List[Dict[str, Any]],
        query_type: QueryType = QueryType.GENERAL,
        max_chunks: Optional[int] = 10,
        include_scores: bool = False
    ) -> Dict[str, str]:
        """
        Create full prompt with system and user messages.

        Args:
            query: User's question
            chunks: Retrieved chunks
            query_type: Type of query
            max_chunks: Maximum chunks to include
            include_scores: Whether to include relevance scores

        Returns:
            Dictionary with 'system' and 'user' prompts
        """
        # Format context
        if include_scores:
            context = cls.format_context_with_scores(chunks, show_scores=True, max_chunks=max_chunks)
        else:
            context = cls.format_context(chunks, include_metadata=True, max_chunks=max_chunks)

        # Get prompts
        system_prompt = cls.get_system_prompt(query_type)
        user_prompt = cls.get_user_prompt(query, context, query_type)

        return {
            "system": system_prompt,
            "user": user_prompt
        }


def create_simple_prompt(query: str, context: str) -> str:
    """
    Create a simple RAG prompt.

    Args:
        query: User's question
        context: Context string

    Returns:
        Simple prompt
    """
    return f"""Answer the following question based on the provided context.

Question: {query}

Context:
{context}

Answer:"""
