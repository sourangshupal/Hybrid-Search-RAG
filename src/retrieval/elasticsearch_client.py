"""Elasticsearch client for lexical search (BM25)."""

from typing import List, Dict, Any, Optional
from datetime import datetime

from elasticsearch import Elasticsearch, helpers
from elasticsearch.exceptions import NotFoundError, RequestError
from loguru import logger

from src.core.exceptions import SearchEngineError
from src.core.config import Settings


class ElasticsearchClient:
    """Client for Elasticsearch lexical search operations."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 9200,
        index_name: str = "research_papers",
        username: Optional[str] = None,
        password: Optional[str] = None,
        use_ssl: bool = False
    ):
        """
        Initialize Elasticsearch client.

        Args:
            host: Elasticsearch server host
            port: Elasticsearch server port
            index_name: Name of the index
            username: Optional username for authentication
            password: Optional password for authentication
            use_ssl: Whether to use SSL
        """
        self.host = host
        self.port = port
        self.index_name = index_name

        logger.info(f"Initializing ElasticsearchClient (host={host}:{port}, index={index_name})")

        try:
            # Build connection URL
            scheme = "https" if use_ssl else "http"
            hosts = [f"{scheme}://{host}:{port}"]

            # Initialize client
            if username and password:
                self.client = Elasticsearch(
                    hosts=hosts,
                    basic_auth=(username, password),
                    verify_certs=use_ssl,
                    request_timeout=30
                )
            else:
                self.client = Elasticsearch(
                    hosts=hosts,
                    verify_certs=False,
                    request_timeout=30
                )

            # Test connection
            if self.client.ping():
                logger.info("Successfully connected to Elasticsearch")
            else:
                raise SearchEngineError("Failed to ping Elasticsearch")

        except Exception as e:
            logger.error(f"Failed to connect to Elasticsearch: {e}")
            raise SearchEngineError(f"Failed to connect to Elasticsearch: {e}")

    async def create_index(
        self,
        recreate: bool = False,
        number_of_shards: int = 1,
        number_of_replicas: int = 0
    ) -> bool:
        """
        Create or recreate index with academic paper mappings.

        Args:
            recreate: Whether to recreate index if it exists
            number_of_shards: Number of shards
            number_of_replicas: Number of replicas

        Returns:
            True if index was created

        Raises:
            SearchEngineError: If index creation fails
        """
        try:
            # Check if index exists
            exists = self.client.indices.exists(index=self.index_name)

            if exists:
                if recreate:
                    logger.warning(f"Deleting existing index: {self.index_name}")
                    self.client.indices.delete(index=self.index_name)
                else:
                    logger.info(f"Index {self.index_name} already exists")
                    return False

            # Define mappings for academic papers
            mappings = {
                "properties": {
                    # Document identification
                    "document_id": {"type": "keyword"},
                    "chunk_id": {"type": "keyword"},
                    "chunk_index": {"type": "integer"},

                    # Content fields with boosting
                    "content": {
                        "type": "text",
                        "analyzer": "english",
                        "fields": {
                            "keyword": {"type": "keyword"},
                            "shingles": {
                                "type": "text",
                                "analyzer": "shingle_analyzer"
                            }
                        }
                    },
                    "title": {
                        "type": "text",
                        "analyzer": "english",
                        "boost": 3.0,  # Higher weight for title
                        "fields": {
                            "keyword": {"type": "keyword"}
                        }
                    },
                    "abstract": {
                        "type": "text",
                        "analyzer": "english",
                        "boost": 2.0,  # Higher weight for abstract
                    },

                    # Section information
                    "section_title": {
                        "type": "text",
                        "analyzer": "english",
                        "boost": 1.5
                    },
                    "section_level": {"type": "integer"},

                    # Chunking metadata
                    "chunking_strategy": {"type": "keyword"},
                    "token_count": {"type": "integer"},
                    "has_equations": {"type": "boolean"},
                    "has_citations": {"type": "boolean"},

                    # Academic metadata
                    "authors": {
                        "type": "text",
                        "fields": {
                            "keyword": {"type": "keyword"}
                        }
                    },
                    "year": {"type": "integer"},
                    "venue": {
                        "type": "text",
                        "fields": {
                            "keyword": {"type": "keyword"}
                        }
                    },
                    "doi": {"type": "keyword"},
                    "arxiv_id": {"type": "keyword"},
                    "keywords": {"type": "keyword"},

                    # References and links
                    "references": {"type": "text"},
                    "previous_chunk_id": {"type": "keyword"},
                    "next_chunk_id": {"type": "keyword"},

                    # Timestamps
                    "indexed_at": {"type": "date"}
                }
            }

            # Define custom analyzers
            settings = {
                "number_of_shards": number_of_shards,
                "number_of_replicas": number_of_replicas,
                "analysis": {
                    "analyzer": {
                        "shingle_analyzer": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": ["lowercase", "shingle_filter"]
                        }
                    },
                    "filter": {
                        "shingle_filter": {
                            "type": "shingle",
                            "min_shingle_size": 2,
                            "max_shingle_size": 3
                        }
                    }
                }
            }

            # Create index
            self.client.indices.create(
                index=self.index_name,
                mappings=mappings,
                settings=settings
            )

            logger.info(f"Created index {self.index_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to create index: {e}")
            raise SearchEngineError(f"Failed to create index: {e}")

    async def index_documents(
        self,
        documents: List[Dict[str, Any]],
        batch_size: int = 500
    ) -> int:
        """
        Index documents in bulk.

        Args:
            documents: List of document dictionaries
            batch_size: Batch size for bulk indexing

        Returns:
            Number of documents indexed

        Raises:
            SearchEngineError: If indexing fails
        """
        try:
            # Add timestamp and prepare for bulk indexing
            actions = []
            for doc in documents:
                doc["indexed_at"] = datetime.utcnow().isoformat()

                action = {
                    "_index": self.index_name,
                    "_id": doc.get("chunk_id"),
                    "_source": doc
                }
                actions.append(action)

            # Bulk index
            success, failed = helpers.bulk(
                self.client,
                actions,
                chunk_size=batch_size,
                raise_on_error=False,
                stats_only=False
            )

            if failed:
                logger.warning(f"Failed to index {len(failed)} documents")
                for item in failed[:5]:  # Log first 5 failures
                    logger.warning(f"Failed item: {item}")

            logger.info(f"Indexed {success} documents successfully")
            return success

        except Exception as e:
            logger.error(f"Bulk indexing failed: {e}")
            raise SearchEngineError(f"Bulk indexing failed: {e}")

    async def search(
        self,
        query: str,
        limit: int = 10,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None,
        fields: Optional[List[str]] = None,
        min_score: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Search documents using BM25.

        Args:
            query: Search query
            limit: Maximum number of results
            offset: Number of results to skip
            filters: Metadata filters
            fields: Fields to search (default: content, title, abstract, section_title)
            min_score: Minimum relevance score

        Returns:
            List of search results with scores

        Raises:
            SearchEngineError: If search fails
        """
        try:
            # Default search fields with boosting
            if fields is None:
                fields = [
                    "title^3.0",           # Highest boost for title
                    "abstract^2.0",        # High boost for abstract
                    "section_title^1.5",   # Medium boost for section titles
                    "content^1.0"          # Base boost for content
                ]

            # Build query
            must_queries = [
                {
                    "multi_match": {
                        "query": query,
                        "fields": fields,
                        "type": "best_fields",
                        "fuzziness": "AUTO",
                        "prefix_length": 2
                    }
                }
            ]

            # Add filter conditions
            filter_conditions = []
            if filters:
                filter_conditions = self._build_filters(filters)

            # Construct full query
            search_query = {
                "bool": {
                    "must": must_queries,
                    "filter": filter_conditions
                }
            }

            # Execute search
            response = self.client.search(
                index=self.index_name,
                query=search_query,
                from_=offset,
                size=limit,
                min_score=min_score
            )

            # Format results
            results = []
            for hit in response["hits"]["hits"]:
                results.append({
                    "id": hit["_id"],
                    "score": hit["_score"],
                    "payload": hit["_source"]
                })

            logger.debug(f"Found {len(results)} results (query: '{query[:50]}...')")
            return results

        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise SearchEngineError(f"Search failed: {e}")

    def _build_filters(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Build Elasticsearch filter conditions from dictionary.

        Args:
            filters: Dictionary of field: value pairs

        Returns:
            List of Elasticsearch filter conditions
        """
        conditions = []

        for field, value in filters.items():
            if isinstance(value, list):
                # OR condition for list values
                conditions.append({
                    "terms": {field: value}
                })
            elif isinstance(value, dict):
                # Range conditions
                if "gte" in value or "lte" in value:
                    range_condition = {}
                    if "gte" in value:
                        range_condition["gte"] = value["gte"]
                    if "lte" in value:
                        range_condition["lte"] = value["lte"]
                    conditions.append({
                        "range": {field: range_condition}
                    })
            else:
                # Exact match
                conditions.append({
                    "term": {field: value}
                })

        return conditions

    async def delete_documents(self, ids: List[str]) -> int:
        """
        Delete documents by IDs.

        Args:
            ids: List of document IDs to delete

        Returns:
            Number of documents deleted

        Raises:
            SearchEngineError: If deletion fails
        """
        try:
            actions = [
                {
                    "_op_type": "delete",
                    "_index": self.index_name,
                    "_id": doc_id
                }
                for doc_id in ids
            ]

            success, failed = helpers.bulk(
                self.client,
                actions,
                raise_on_error=False,
                stats_only=True
            )

            logger.info(f"Deleted {success} documents")
            return success

        except Exception as e:
            logger.error(f"Failed to delete documents: {e}")
            raise SearchEngineError(f"Failed to delete documents: {e}")

    async def delete_by_query(self, filters: Dict[str, Any]) -> int:
        """
        Delete documents matching filters.

        Args:
            filters: Metadata filters

        Returns:
            Number of documents deleted

        Raises:
            SearchEngineError: If deletion fails
        """
        try:
            filter_conditions = self._build_filters(filters)
            query = {
                "bool": {
                    "filter": filter_conditions
                }
            }

            response = self.client.delete_by_query(
                index=self.index_name,
                query=query
            )

            deleted = response.get("deleted", 0)
            logger.info(f"Deleted {deleted} documents matching filters")
            return deleted

        except Exception as e:
            logger.error(f"Failed to delete by query: {e}")
            raise SearchEngineError(f"Failed to delete by query: {e}")

    async def get_index_info(self) -> Dict[str, Any]:
        """
        Get index information and statistics.

        Returns:
            Dictionary with index info

        Raises:
            SearchEngineError: If retrieval fails
        """
        try:
            stats = self.client.indices.stats(index=self.index_name)
            index_stats = stats["indices"][self.index_name]

            count_response = self.client.count(index=self.index_name)

            return {
                "name": self.index_name,
                "document_count": count_response["count"],
                "size_in_bytes": index_stats["total"]["store"]["size_in_bytes"],
                "number_of_shards": index_stats["total"]["shard_stats"]["total_count"],
            }

        except Exception as e:
            logger.error(f"Failed to get index info: {e}")
            raise SearchEngineError(f"Failed to get index info: {e}")

    async def index_exists(self) -> bool:
        """
        Check if index exists.

        Returns:
            True if index exists
        """
        try:
            return self.client.indices.exists(index=self.index_name)
        except Exception as e:
            logger.error(f"Failed to check index existence: {e}")
            return False

    async def count_documents(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count documents in index.

        Args:
            filters: Optional metadata filters

        Returns:
            Number of documents

        Raises:
            SearchEngineError: If count fails
        """
        try:
            if filters:
                filter_conditions = self._build_filters(filters)
                query = {
                    "bool": {
                        "filter": filter_conditions
                    }
                }
                response = self.client.count(index=self.index_name, query=query)
            else:
                response = self.client.count(index=self.index_name)

            return response["count"]

        except Exception as e:
            logger.error(f"Failed to count documents: {e}")
            raise SearchEngineError(f"Failed to count documents: {e}")

    async def refresh_index(self):
        """Refresh index to make recent changes searchable."""
        try:
            self.client.indices.refresh(index=self.index_name)
            logger.debug(f"Refreshed index {self.index_name}")
        except Exception as e:
            logger.warning(f"Failed to refresh index: {e}")

    def close(self):
        """Close client connection."""
        try:
            self.client.close()
            logger.info("Closed Elasticsearch client")
        except Exception as e:
            logger.warning(f"Error closing Elasticsearch client: {e}")

    def __repr__(self) -> str:
        return (
            f"ElasticsearchClient(host={self.host}:{self.port}, "
            f"index={self.index_name})"
        )


def create_elasticsearch_client_from_config(config: Settings) -> ElasticsearchClient:
    """
    Create Elasticsearch client from config.

    Args:
        config: Application settings

    Returns:
        Initialized Elasticsearch client
    """
    return ElasticsearchClient(
        host=config.elasticsearch_host,
        port=config.elasticsearch_port,
        index_name=config.elasticsearch_index,
        username=None,
        password=None,
        use_ssl=False
    )
