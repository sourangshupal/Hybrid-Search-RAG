"""Script to initialize Qdrant and Elasticsearch indices."""

import asyncio
import argparse
from loguru import logger

from src.core.config import Settings
from src.retrieval.qdrant_client import create_qdrant_client_from_config
from src.retrieval.elasticsearch_client import create_elasticsearch_client_from_config


async def create_indices(recreate: bool = False, environment: str = "dev"):
    """
    Create Qdrant collection and Elasticsearch index.

    Args:
        recreate: Whether to recreate indices if they exist
        environment: Environment name (dev, staging, prod)
    """
    logger.info("="*60)
    logger.info("Index Initialization Script")
    logger.info("="*60)
    logger.info(f"Environment: {environment}")
    logger.info(f"Recreate: {recreate}")
    logger.info("")

    # Load configuration
    config = Settings()
    logger.info(f"Loaded configuration from: configs/{environment}.yaml")

    # Initialize clients
    logger.info("\n" + "="*60)
    logger.info("Step 1: Initialize Clients")
    logger.info("="*60)

    qdrant_client = create_qdrant_client_from_config(config)
    logger.info(f"✓ Qdrant client initialized: {qdrant_client.host}:{qdrant_client.port}")

    es_client = create_elasticsearch_client_from_config(config)
    logger.info(f"✓ Elasticsearch client initialized: {es_client.host}:{es_client.port}")

    # Check existing indices
    logger.info("\n" + "="*60)
    logger.info("Step 2: Check Existing Indices")
    logger.info("="*60)

    qdrant_exists = await qdrant_client.collection_exists()
    es_exists = await es_client.index_exists()

    logger.info(f"Qdrant collection '{qdrant_client.collection_name}' exists: {qdrant_exists}")
    logger.info(f"Elasticsearch index '{es_client.index_name}' exists: {es_exists}")

    if (qdrant_exists or es_exists) and not recreate:
        logger.warning("\nIndices already exist. Use --recreate to recreate them.")
        return

    # Create indices
    logger.info("\n" + "="*60)
    logger.info("Step 3: Create Indices")
    logger.info("="*60)

    try:
        # Create Qdrant collection
        logger.info("\nCreating Qdrant collection...")
        qdrant_created = await qdrant_client.create_collection(recreate=recreate)
        if qdrant_created:
            logger.info(f"✓ Created Qdrant collection: {qdrant_client.collection_name}")
        else:
            logger.info(f"✓ Qdrant collection already exists: {qdrant_client.collection_name}")

        # Get collection info
        qdrant_info = await qdrant_client.get_collection_info()
        logger.info(f"  - Vectors: {qdrant_info['vectors_count']}")
        logger.info(f"  - Dimension: {qdrant_info['config']['vector_size']}")
        logger.info(f"  - Distance: {qdrant_info['config']['distance']}")

        # Create Elasticsearch index
        logger.info("\nCreating Elasticsearch index...")
        es_created = await es_client.create_index(recreate=recreate)
        if es_created:
            logger.info(f"✓ Created Elasticsearch index: {es_client.index_name}")
        else:
            logger.info(f"✓ Elasticsearch index already exists: {es_client.index_name}")

        # Get index info
        es_info = await es_client.get_index_info()
        logger.info(f"  - Documents: {es_info['document_count']}")
        logger.info(f"  - Shards: {es_info['number_of_shards']}")

    except Exception as e:
        logger.error(f"\n❌ Failed to create indices: {e}")
        raise

    # Verify indices
    logger.info("\n" + "="*60)
    logger.info("Step 4: Verify Indices")
    logger.info("="*60)

    qdrant_exists = await qdrant_client.collection_exists()
    es_exists = await es_client.index_exists()

    if qdrant_exists and es_exists:
        logger.info("✓ All indices created successfully!")
    else:
        logger.error("❌ Index verification failed")
        logger.error(f"  Qdrant: {qdrant_exists}")
        logger.error(f"  Elasticsearch: {es_exists}")
        raise Exception("Index verification failed")

    # Summary
    logger.info("\n" + "="*60)
    logger.info("Summary")
    logger.info("="*60)
    logger.info(f"✓ Qdrant collection: {qdrant_client.collection_name}")
    logger.info(f"  - Host: {qdrant_client.host}:{qdrant_client.port}")
    logger.info(f"  - Dimension: {qdrant_client.embedding_dim}")
    logger.info(f"  - Distance: {qdrant_client.distance_metric}")
    logger.info("")
    logger.info(f"✓ Elasticsearch index: {es_client.index_name}")
    logger.info(f"  - Host: {es_client.host}:{es_client.port}")
    logger.info(f"  - Mappings: Academic paper fields with boosting")
    logger.info("")
    logger.info("Indices are ready for indexing!")

    # Close clients
    qdrant_client.close()
    es_client.close()


async def delete_indices(environment: str = "dev"):
    """
    Delete Qdrant collection and Elasticsearch index.

    Args:
        environment: Environment name (dev, staging, prod)
    """
    logger.info("="*60)
    logger.info("Index Deletion Script")
    logger.info("="*60)
    logger.warning("⚠️  This will DELETE all data!")

    # Confirm deletion
    confirmation = input("Type 'DELETE' to confirm: ")
    if confirmation != "DELETE":
        logger.info("Deletion cancelled.")
        return

    # Load configuration
    config = Settings()

    # Initialize clients
    qdrant_client = create_qdrant_client_from_config(config)
    es_client = create_elasticsearch_client_from_config(config)

    try:
        # Delete Qdrant collection
        if await qdrant_client.collection_exists():
            logger.info(f"Deleting Qdrant collection: {qdrant_client.collection_name}")
            qdrant_client.client.delete_collection(qdrant_client.collection_name)
            logger.info("✓ Qdrant collection deleted")
        else:
            logger.info("Qdrant collection does not exist")

        # Delete Elasticsearch index
        if await es_client.index_exists():
            logger.info(f"Deleting Elasticsearch index: {es_client.index_name}")
            es_client.client.indices.delete(index=es_client.index_name)
            logger.info("✓ Elasticsearch index deleted")
        else:
            logger.info("Elasticsearch index does not exist")

        logger.info("\n✓ All indices deleted successfully")

    except Exception as e:
        logger.error(f"❌ Failed to delete indices: {e}")
        raise

    finally:
        qdrant_client.close()
        es_client.close()


async def show_stats(environment: str = "dev"):
    """
    Show statistics for both indices.

    Args:
        environment: Environment name (dev, staging, prod)
    """
    logger.info("="*60)
    logger.info("Index Statistics")
    logger.info("="*60)

    # Load configuration
    config = Settings()

    # Initialize clients
    qdrant_client = create_qdrant_client_from_config(config)
    es_client = create_elasticsearch_client_from_config(config)

    try:
        # Qdrant stats
        if await qdrant_client.collection_exists():
            logger.info("\nQdrant Collection:")
            info = await qdrant_client.get_collection_info()
            logger.info(f"  Name: {info['name']}")
            logger.info(f"  Vectors: {info['vectors_count']}")
            logger.info(f"  Points: {info['points_count']}")
            logger.info(f"  Segments: {info['segments_count']}")
            logger.info(f"  Status: {info['status']}")
            logger.info(f"  Distance: {info['config']['distance']}")
        else:
            logger.warning("\nQdrant collection does not exist")

        # Elasticsearch stats
        if await es_client.index_exists():
            logger.info("\nElasticsearch Index:")
            info = await es_client.get_index_info()
            logger.info(f"  Name: {info['name']}")
            logger.info(f"  Documents: {info['document_count']}")
            logger.info(f"  Size: {info['size_in_bytes'] / 1024 / 1024:.2f} MB")
            logger.info(f"  Shards: {info['number_of_shards']}")
        else:
            logger.warning("\nElasticsearch index does not exist")

    except Exception as e:
        logger.error(f"❌ Failed to get stats: {e}")
        raise

    finally:
        qdrant_client.close()
        es_client.close()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Manage Qdrant and Elasticsearch indices")
    parser.add_argument(
        "action",
        choices=["create", "delete", "stats"],
        help="Action to perform"
    )
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Recreate indices if they exist (only for create action)"
    )
    parser.add_argument(
        "--env",
        default="dev",
        choices=["dev", "staging", "prod"],
        help="Environment (default: dev)"
    )

    args = parser.parse_args()

    if args.action == "create":
        asyncio.run(create_indices(recreate=args.recreate, environment=args.env))
    elif args.action == "delete":
        asyncio.run(delete_indices(environment=args.env))
    elif args.action == "stats":
        asyncio.run(show_stats(environment=args.env))


if __name__ == "__main__":
    main()
