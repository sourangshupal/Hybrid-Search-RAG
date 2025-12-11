"""Query preprocessing and intent extraction for hybrid search."""

import re
from typing import Dict, List, Optional, Any
from enum import Enum

from loguru import logger


class QueryIntent(str, Enum):
    """Types of query intent."""

    METHODOLOGICAL = "methodological"  # How/method questions
    RESULTS = "results"  # What/results questions
    COMPARATIVE = "comparative"  # Compare/contrast questions
    DEFINITION = "definition"  # What is/define questions
    GENERAL = "general"  # General information retrieval


class QueryProcessor:
    """Processor for query preprocessing and intent extraction."""

    # Intent detection patterns
    METHODOLOGICAL_PATTERNS = [
        r"\bhow\b",
        r"\bmethod\b",
        r"\bapproach\b",
        r"\btechnique\b",
        r"\balgorithm\b",
        r"\bimplementation\b",
        r"\bprocedure\b",
    ]

    RESULTS_PATTERNS = [
        r"\bresult\b",
        r"\bperformance\b",
        r"\baccuracy\b",
        r"\boutcome\b",
        r"\bfinding\b",
        r"\bmetric\b",
        r"\bscore\b",
    ]

    COMPARATIVE_PATTERNS = [
        r"\bcompare\b",
        r"\bcomparison\b",
        r"\bdifference\b",
        r"\bvs\b",
        r"\bversus\b",
        r"\bbetter\b",
        r"\bworse\b",
        r"\bbetween\b.*\band\b",
    ]

    DEFINITION_PATTERNS = [
        r"^what is\b",
        r"^define\b",
        r"^definition of\b",
        r"^meaning of\b",
        r"^explain\b",
    ]

    # Stopwords for query expansion (common words to potentially remove)
    STOPWORDS = {
        "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
        "has", "he", "in", "is", "it", "its", "of", "on", "that", "the",
        "to", "was", "will", "with"
    }

    def __init__(
        self,
        expand_query: bool = True,
        extract_filters: bool = True,
        normalize: bool = True
    ):
        """
        Initialize query processor.

        Args:
            expand_query: Whether to expand queries with synonyms
            extract_filters: Whether to extract metadata filters from query
            normalize: Whether to normalize queries
        """
        self.expand_query = expand_query
        self.extract_filters = extract_filters
        self.normalize = normalize

        logger.info("Initialized QueryProcessor")

    def process_query(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process query for hybrid search.

        Args:
            query: Raw query string
            filters: Optional metadata filters

        Returns:
            Dictionary with processed query and metadata
        """
        result = {
            "original_query": query,
            "processed_query": query,
            "intent": QueryIntent.GENERAL,
            "filters": filters or {},
            "expansion_terms": [],
            "boost_fields": []
        }

        # Normalize query
        if self.normalize:
            result["processed_query"] = self._normalize_query(query)

        # Extract intent
        result["intent"] = self._extract_intent(query)

        # Extract filters from query if enabled
        if self.extract_filters:
            extracted_filters = self._extract_filters_from_query(query)
            result["filters"].update(extracted_filters)

        # Determine field boosting based on intent
        result["boost_fields"] = self._get_boost_fields(result["intent"])

        # Expand query if enabled
        if self.expand_query:
            result["expansion_terms"] = self._expand_query(result["processed_query"])

        logger.debug(
            f"Processed query: '{query}' → intent={result['intent']}, "
            f"filters={len(result['filters'])}"
        )

        return result

    def _normalize_query(self, query: str) -> str:
        """
        Normalize query string.

        Args:
            query: Raw query string

        Returns:
            Normalized query
        """
        # Convert to lowercase
        normalized = query.lower()

        # Remove extra whitespace
        normalized = re.sub(r"\s+", " ", normalized)

        # Remove special characters but keep important ones
        normalized = re.sub(r"[^\w\s\-\+\?]", "", normalized)

        # Strip leading/trailing whitespace
        normalized = normalized.strip()

        return normalized

    def _extract_intent(self, query: str) -> QueryIntent:
        """
        Extract query intent from query string.

        Args:
            query: Query string

        Returns:
            Detected query intent
        """
        query_lower = query.lower()

        # Check for definition patterns (highest priority)
        for pattern in self.DEFINITION_PATTERNS:
            if re.search(pattern, query_lower):
                return QueryIntent.DEFINITION

        # Check for comparative patterns
        for pattern in self.COMPARATIVE_PATTERNS:
            if re.search(pattern, query_lower):
                return QueryIntent.COMPARATIVE

        # Check for methodological patterns
        method_count = sum(
            1 for pattern in self.METHODOLOGICAL_PATTERNS
            if re.search(pattern, query_lower)
        )

        # Check for results patterns
        results_count = sum(
            1 for pattern in self.RESULTS_PATTERNS
            if re.search(pattern, query_lower)
        )

        # Return intent with highest match count
        if method_count > results_count and method_count > 0:
            return QueryIntent.METHODOLOGICAL
        elif results_count > 0:
            return QueryIntent.RESULTS

        return QueryIntent.GENERAL

    def _extract_filters_from_query(self, query: str) -> Dict[str, Any]:
        """
        Extract metadata filters from query string.

        Args:
            query: Query string

        Returns:
            Dictionary of extracted filters
        """
        filters = {}

        # Extract year mentions
        year_matches = re.findall(r"\b(19|20)\d{2}\b", query)
        if year_matches:
            years = [int(y) for y in year_matches]
            if len(years) == 1:
                filters["year"] = years[0]
            elif len(years) == 2:
                filters["year"] = {"gte": min(years), "lte": max(years)}

        # Extract author mentions (names in quotes or capitalized)
        author_matches = re.findall(r'"([A-Z][a-z]+ [A-Z][a-z]+)"', query)
        if author_matches:
            filters["authors"] = author_matches

        # Extract venue mentions (conferences/journals)
        venue_patterns = [
            r"\b(NeurIPS|ICML|ICLR|CVPR|ACL|EMNLP|AAAI|IJCAI)\b",
            r"\b(Nature|Science|Cell|PNAS)\b"
        ]
        for pattern in venue_patterns:
            venue_matches = re.findall(pattern, query, re.IGNORECASE)
            if venue_matches:
                filters["venue"] = venue_matches[0]
                break

        return filters

    def _get_boost_fields(self, intent: QueryIntent) -> List[str]:
        """
        Get field boosting based on query intent.

        Args:
            intent: Query intent

        Returns:
            List of fields with boost values
        """
        # Base boosting
        base_fields = [
            "title^3.0",
            "abstract^2.0",
            "section_title^1.5",
            "content^1.0"
        ]

        # Adjust boosting based on intent
        if intent == QueryIntent.METHODOLOGICAL:
            # Boost sections likely to contain methods
            return [
                "section_title^2.0",  # Higher boost for section titles
                "title^2.5",
                "abstract^1.5",
                "content^1.0"
            ]
        elif intent == QueryIntent.RESULTS:
            # Boost sections likely to contain results
            return [
                "abstract^3.0",  # Results often summarized in abstract
                "section_title^2.0",
                "title^2.0",
                "content^1.0"
            ]
        elif intent == QueryIntent.DEFINITION:
            # Boost title and abstract for definitions
            return [
                "title^4.0",  # Highest boost for title
                "abstract^3.0",
                "content^1.0"
            ]
        elif intent == QueryIntent.COMPARATIVE:
            # Balance between abstract and content
            return [
                "abstract^2.5",
                "title^2.0",
                "section_title^1.5",
                "content^1.0"
            ]

        return base_fields

    def _expand_query(self, query: str) -> List[str]:
        """
        Expand query with related terms.

        Args:
            query: Normalized query string

        Returns:
            List of expansion terms
        """
        expansion_terms = []

        # Common ML/AI term expansions
        expansions = {
            "ml": ["machine learning"],
            "dl": ["deep learning"],
            "nn": ["neural network", "neural networks"],
            "cnn": ["convolutional neural network"],
            "rnn": ["recurrent neural network"],
            "lstm": ["long short-term memory"],
            "gpt": ["generative pre-trained transformer"],
            "bert": ["bidirectional encoder representations from transformers"],
            "nlp": ["natural language processing"],
            "cv": ["computer vision"],
            "rl": ["reinforcement learning"],
            "gnn": ["graph neural network"],
            "vit": ["vision transformer"],
            "llm": ["large language model"],
        }

        # Check for acronyms and expand
        words = query.split()
        for word in words:
            word_lower = word.lower()
            if word_lower in expansions:
                expansion_terms.extend(expansions[word_lower])

        return expansion_terms

    def build_enhanced_query(
        self,
        processed_result: Dict[str, Any],
        include_expansions: bool = True
    ) -> str:
        """
        Build enhanced query string with expansions.

        Args:
            processed_result: Result from process_query
            include_expansions: Whether to include expansion terms

        Returns:
            Enhanced query string
        """
        query_parts = [processed_result["processed_query"]]

        if include_expansions and processed_result["expansion_terms"]:
            # Add expansion terms with lower weight
            for term in processed_result["expansion_terms"]:
                query_parts.append(term)

        return " ".join(query_parts)

    def get_search_config(
        self,
        processed_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Get search configuration based on processed query.

        Args:
            processed_result: Result from process_query

        Returns:
            Search configuration dictionary
        """
        return {
            "query": processed_result["processed_query"],
            "enhanced_query": self.build_enhanced_query(processed_result),
            "filters": processed_result["filters"],
            "boost_fields": processed_result["boost_fields"],
            "intent": processed_result["intent"].value
        }

    def __repr__(self) -> str:
        return (
            f"QueryProcessor(expand={self.expand_query}, "
            f"extract_filters={self.extract_filters})"
        )
