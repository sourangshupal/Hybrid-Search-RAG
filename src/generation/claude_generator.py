"""Claude generator for RAG answer generation."""

import time
from typing import Dict, List, Any, Optional, AsyncIterator
import asyncio

from anthropic import AsyncAnthropic
from loguru import logger

from src.generation.prompt_templates import PromptTemplates, QueryType
from src.core.exceptions import GenerationError
from src.core.config import Settings


class ClaudeGenerator:
    """Answer generator using Anthropic Claude."""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-5-20250929",
        max_tokens: int = 4096,
        temperature: float = 0.3,
        timeout: float = 120.0
    ):
        """
        Initialize Claude generator.

        Args:
            api_key: Anthropic API key
            model: Claude model name
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0-1.0)
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.timeout = timeout

        logger.info(f"Initializing ClaudeGenerator (model={model})")

        try:
            self.client = AsyncAnthropic(
                api_key=api_key,
                timeout=timeout
            )
            logger.info("Successfully initialized Claude client")
        except Exception as e:
            logger.error(f"Failed to initialize Claude client: {e}")
            raise GenerationError(f"Failed to initialize Claude client: {e}")

    async def generate(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        query_type: QueryType = QueryType.GENERAL,
        max_chunks: int = 10,
        include_scores: bool = False,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Generate answer using Claude.

        Args:
            query: User's question
            chunks: Retrieved chunks with content and metadata
            query_type: Type of query for prompt selection
            max_chunks: Maximum chunks to include in context
            include_scores: Whether to include relevance scores
            max_retries: Maximum number of retries

        Returns:
            Dictionary with answer, metadata, and citations

        Raises:
            GenerationError: If generation fails
        """
        logger.info(f"Generating answer for query: '{query[:50]}...'")

        for attempt in range(max_retries):
            try:
                start_time = time.time()

                # Create prompt
                prompts = PromptTemplates.create_full_prompt(
                    query=query,
                    chunks=chunks,
                    query_type=query_type,
                    max_chunks=max_chunks,
                    include_scores=include_scores
                )

                # Call Claude API
                response = await self.client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    system=prompts["system"],
                    messages=[
                        {
                            "role": "user",
                            "content": prompts["user"]
                        }
                    ]
                )

                elapsed = time.time() - start_time

                # Extract answer
                answer = response.content[0].text

                # Extract citations
                citations = PromptTemplates.extract_citation_info(chunks)

                # Get token usage
                input_tokens = response.usage.input_tokens
                output_tokens = response.usage.output_tokens

                logger.info(
                    f"Generated answer in {elapsed:.2f}s "
                    f"(in={input_tokens}, out={output_tokens})"
                )

                return {
                    "answer": answer,
                    "citations": citations,
                    "model": self.model,
                    "query_type": query_type.value,
                    "num_chunks": len(chunks[:max_chunks]),
                    "generation_time_ms": elapsed * 1000,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": input_tokens + output_tokens
                }

            except Exception as e:
                logger.warning(
                    f"Generation attempt {attempt + 1}/{max_retries} failed: {e}"
                )
                if attempt == max_retries - 1:
                    logger.error(f"All {max_retries} generation attempts failed")
                    raise GenerationError(f"Failed to generate answer: {e}")

                # Exponential backoff
                await asyncio.sleep(2 ** attempt)

    async def generate_stream(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        query_type: QueryType = QueryType.GENERAL,
        max_chunks: int = 10,
        include_scores: bool = False
    ) -> AsyncIterator[str]:
        """
        Generate answer with streaming.

        Args:
            query: User's question
            chunks: Retrieved chunks
            query_type: Type of query
            max_chunks: Maximum chunks to include
            include_scores: Whether to include scores

        Yields:
            Answer text chunks as they are generated

        Raises:
            GenerationError: If generation fails
        """
        logger.info(f"Streaming answer for query: '{query[:50]}...'")

        try:
            start_time = time.time()

            # Create prompt
            prompts = PromptTemplates.create_full_prompt(
                query=query,
                chunks=chunks,
                query_type=query_type,
                max_chunks=max_chunks,
                include_scores=include_scores
            )

            # Stream response
            async with self.client.messages.stream(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=prompts["system"],
                messages=[
                    {
                        "role": "user",
                        "content": prompts["user"]
                    }
                ]
            ) as stream:
                async for text in stream.text_stream:
                    yield text

            elapsed = time.time() - start_time
            logger.info(f"Completed streaming in {elapsed:.2f}s")

        except Exception as e:
            logger.error(f"Streaming generation failed: {e}")
            raise GenerationError(f"Failed to stream answer: {e}")

    async def generate_with_context_window_management(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        query_type: QueryType = QueryType.GENERAL,
        max_context_tokens: int = 100000,
        include_scores: bool = False
    ) -> Dict[str, Any]:
        """
        Generate answer with automatic context window management.

        Automatically reduces chunks if context exceeds token limit.

        Args:
            query: User's question
            chunks: Retrieved chunks
            query_type: Type of query
            max_context_tokens: Maximum tokens for context
            include_scores: Whether to include scores

        Returns:
            Generation result dictionary
        """
        # Estimate tokens (rough approximation: 1 token ≈ 4 characters)
        def estimate_tokens(text: str) -> int:
            return len(text) // 4

        # Start with all chunks
        max_chunks = len(chunks)

        while max_chunks > 0:
            # Create prompt
            prompts = PromptTemplates.create_full_prompt(
                query=query,
                chunks=chunks,
                query_type=query_type,
                max_chunks=max_chunks,
                include_scores=include_scores
            )

            # Estimate total tokens
            context_tokens = estimate_tokens(prompts["user"])
            system_tokens = estimate_tokens(prompts["system"])
            total_input_tokens = context_tokens + system_tokens

            # Check if within limit
            if total_input_tokens <= max_context_tokens:
                logger.info(
                    f"Using {max_chunks} chunks (~{total_input_tokens} tokens)"
                )
                return await self.generate(
                    query=query,
                    chunks=chunks,
                    query_type=query_type,
                    max_chunks=max_chunks,
                    include_scores=include_scores
                )

            # Reduce chunks by 20%
            max_chunks = int(max_chunks * 0.8)
            logger.warning(
                f"Context too large (~{total_input_tokens} tokens), "
                f"reducing to {max_chunks} chunks"
            )

        # If we get here, even 1 chunk is too large
        raise GenerationError(
            "Cannot fit context within token limit. "
            "Try shorter chunks or smaller max_context_tokens."
        )

    def validate_response(
        self,
        response: Dict[str, Any],
        require_citations: bool = True,
        min_length: int = 50
    ) -> bool:
        """
        Validate generated response.

        Args:
            response: Response dictionary from generate()
            require_citations: Whether to require citations in answer
            min_length: Minimum answer length in characters

        Returns:
            True if valid, False otherwise
        """
        answer = response.get("answer", "")

        # Check minimum length
        if len(answer) < min_length:
            logger.warning(f"Answer too short: {len(answer)} < {min_length}")
            return False

        # Check for citations if required
        if require_citations:
            # Look for citation patterns: [Author Year] or [Source N]
            import re
            citation_pattern = r'\[(?:[A-Z][a-z]+\s+\d{4}|Source\s+\d+)\]'
            citations_found = re.findall(citation_pattern, answer)

            if not citations_found:
                logger.warning("No citations found in answer")
                return False

        # Check for error messages
        error_keywords = [
            "i don't know",
            "i cannot",
            "insufficient information",
            "not enough context"
        ]

        answer_lower = answer.lower()
        if any(keyword in answer_lower for keyword in error_keywords):
            logger.warning("Answer contains uncertainty markers")
            # Not necessarily invalid, but flag it
            return True

        return True

    async def generate_with_validation(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        query_type: QueryType = QueryType.GENERAL,
        max_chunks: int = 10,
        require_citations: bool = True
    ) -> Dict[str, Any]:
        """
        Generate answer with validation.

        Args:
            query: User's question
            chunks: Retrieved chunks
            query_type: Type of query
            max_chunks: Maximum chunks
            require_citations: Whether to require citations

        Returns:
            Validated generation result

        Raises:
            GenerationError: If generation or validation fails
        """
        response = await self.generate(
            query=query,
            chunks=chunks,
            query_type=query_type,
            max_chunks=max_chunks
        )

        # Validate
        is_valid = self.validate_response(response, require_citations=require_citations)

        response["validated"] = is_valid

        if not is_valid:
            logger.warning("Generated response did not pass validation")

        return response

    def get_stats(self) -> Dict[str, Any]:
        """
        Get generator statistics.

        Returns:
            Dictionary with stats
        """
        return {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "timeout": self.timeout
        }

    def __repr__(self) -> str:
        return f"ClaudeGenerator(model={self.model}, max_tokens={self.max_tokens})"


def create_claude_generator_from_config(config: Settings) -> ClaudeGenerator:
    """
    Create Claude generator from config.

    Args:
        config: Application settings

    Returns:
        Initialized Claude generator
    """
    return ClaudeGenerator(
        api_key=config.anthropic_api_key,
        model="claude-sonnet-4-5-20250929",
        max_tokens=4096,
        temperature=0.3,
        timeout=120.0
    )
