"""Generate synthetic evaluation dataset for RAG system."""

import asyncio
import argparse
import json
import random
from typing import List, Dict, Any, Optional
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from src.core.config import Settings
from src.generation.claude_generator import ClaudeGenerator
from src.generation.prompt_templates import QueryType


class SyntheticDatasetGenerator:
    """Generator for synthetic evaluation datasets."""

    # Sample topics for academic queries
    TOPICS = [
        "transformers", "attention mechanism", "BERT", "GPT", "neural networks",
        "deep learning", "machine learning", "natural language processing",
        "computer vision", "reinforcement learning", "transfer learning",
        "few-shot learning", "zero-shot learning", "prompt engineering",
        "large language models", "pre-training", "fine-tuning", "embeddings",
        "recurrent neural networks", "convolutional neural networks",
        "generative adversarial networks", "diffusion models", "graph neural networks",
        "meta-learning", "self-supervised learning", "contrastive learning",
        "knowledge distillation", "model compression", "neural architecture search",
        "optimization algorithms", "gradient descent", "backpropagation"
    ]

    # Query templates by type
    QUERY_TEMPLATES = {
        QueryType.METHODOLOGICAL: [
            "How does {topic} work?",
            "What is the architecture of {topic}?",
            "Explain the methodology behind {topic}.",
            "What are the key components of {topic}?",
            "Describe the training process for {topic}.",
            "What algorithm does {topic} use?",
            "How is {topic} implemented?",
            "What are the technical details of {topic}?"
        ],
        QueryType.RESULTS: [
            "What results has {topic} achieved?",
            "What is the performance of {topic}?",
            "What benchmarks has {topic} been evaluated on?",
            "What are the experimental results for {topic}?",
            "How well does {topic} perform compared to baselines?",
            "What metrics are used to evaluate {topic}?",
            "What datasets has {topic} been tested on?",
            "What improvements does {topic} provide?"
        ],
        QueryType.COMPARATIVE: [
            "What is the difference between {topic1} and {topic2}?",
            "How does {topic1} compare to {topic2}?",
            "Which is better: {topic1} or {topic2}?",
            "What are the advantages of {topic1} over {topic2}?",
            "Compare and contrast {topic1} and {topic2}.",
            "How do {topic1} and {topic2} differ in performance?",
            "What are the trade-offs between {topic1} and {topic2}?",
            "When should I use {topic1} versus {topic2}?"
        ],
        QueryType.DEFINITION: [
            "What is {topic}?",
            "Define {topic}.",
            "What does {topic} mean?",
            "Explain {topic} in simple terms.",
            "What is the concept of {topic}?",
            "Provide an overview of {topic}.",
            "What is meant by {topic}?",
            "Give a brief explanation of {topic}."
        ],
        QueryType.GENERAL: [
            "Tell me about {topic}.",
            "What can you explain about {topic}?",
            "I'm interested in learning about {topic}.",
            "Provide information on {topic}.",
            "What should I know about {topic}?",
            "Discuss {topic}.",
            "Give me an overview of {topic}.",
            "What are the key aspects of {topic}?"
        ]
    }

    def __init__(self, generator: Optional[ClaudeGenerator] = None):
        """
        Initialize dataset generator.

        Args:
            generator: Optional LLM generator for creating ground truth
        """
        self.generator = generator

    def generate_query(
        self,
        query_type: QueryType,
        difficulty: str = "medium"
    ) -> Dict[str, Any]:
        """
        Generate a single synthetic query.

        Args:
            query_type: Type of query to generate
            difficulty: Difficulty level (easy, medium, hard)

        Returns:
            Dictionary with query information
        """
        # Select template
        templates = self.QUERY_TEMPLATES[query_type]
        template = random.choice(templates)

        # Fill template
        if "{topic1}" in template and "{topic2}" in template:
            # Comparative query
            topic1, topic2 = random.sample(self.TOPICS, 2)
            query = template.format(topic1=topic1, topic2=topic2)
            topics = [topic1, topic2]
        else:
            # Single topic query
            topic = random.choice(self.TOPICS)
            query = template.format(topic=topic)
            topics = [topic]

        return {
            "query": query,
            "query_type": query_type.value,
            "topics": topics,
            "difficulty": difficulty,
            "template": template
        }

    async def generate_ground_truth(
        self,
        query: str,
        context: Optional[str] = None
    ) -> Optional[str]:
        """
        Generate ground truth answer using LLM.

        Args:
            query: Query to answer
            context: Optional context for answer generation

        Returns:
            Ground truth answer or None if generator not available
        """
        if not self.generator:
            return None

        try:
            # Create prompt
            if context:
                prompt = f"""Given the following context, answer the question.

Context: {context}

Question: {query}

Provide a comprehensive, accurate answer with citations where appropriate."""
            else:
                prompt = f"""Answer the following academic question comprehensively and accurately. Include citations in the format [Author Year] where appropriate.

Question: {query}"""

            # Generate answer
            result = await self.generator.generate(
                query=query,
                chunks=[],  # No chunks for ground truth generation
                query_type=QueryType.GENERAL,
                max_chunks=0
            )

            return result["answer"]

        except Exception as e:
            logger.error(f"Failed to generate ground truth for query '{query}': {e}")
            return None

    def generate_relevance_judgments(
        self,
        query: str,
        topics: List[str],
        num_relevant: int = 5
    ) -> Dict[str, Any]:
        """
        Generate synthetic relevance judgments for retrieval evaluation.

        Args:
            query: The query
            topics: Query topics
            num_relevant: Number of relevant documents to generate

        Returns:
            Dictionary with relevance judgments
        """
        # Generate relevant document IDs
        # In a real system, these would be actual document IDs from the index
        relevant_docs = [f"doc_{query.replace(' ', '_')[:30]}_{i}" for i in range(num_relevant)]

        # Assign relevance scores
        relevance_scores = {}
        for i, doc_id in enumerate(relevant_docs):
            # Higher score for earlier documents (more relevant)
            relevance_scores[doc_id] = 3 - min(i // 2, 2)  # Scores: 3, 3, 2, 2, 1

        return {
            "relevant_docs": relevant_docs,
            "relevance_scores": relevance_scores,
            "num_relevant": len(relevant_docs)
        }

    async def generate_dataset(
        self,
        num_queries: int = 100,
        distribution: Optional[Dict[str, float]] = None,
        difficulty_distribution: Optional[Dict[str, float]] = None,
        include_ground_truth: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Generate complete evaluation dataset.

        Args:
            num_queries: Number of queries to generate
            distribution: Distribution of query types (defaults to uniform)
            difficulty_distribution: Distribution of difficulties (defaults to uniform)
            include_ground_truth: Whether to generate ground truth answers

        Returns:
            List of query dictionaries
        """
        logger.info(f"Generating evaluation dataset with {num_queries} queries")

        # Default distributions
        if distribution is None:
            distribution = {
                QueryType.METHODOLOGICAL: 0.25,
                QueryType.RESULTS: 0.20,
                QueryType.COMPARATIVE: 0.20,
                QueryType.DEFINITION: 0.15,
                QueryType.GENERAL: 0.20
            }

        if difficulty_distribution is None:
            difficulty_distribution = {
                "easy": 0.3,
                "medium": 0.5,
                "hard": 0.2
            }

        dataset = []

        for i in range(num_queries):
            # Select query type based on distribution
            query_type = random.choices(
                list(distribution.keys()),
                weights=list(distribution.values()),
                k=1
            )[0]

            # Select difficulty based on distribution
            difficulty = random.choices(
                list(difficulty_distribution.keys()),
                weights=list(difficulty_distribution.values()),
                k=1
            )[0]

            # Generate query
            query_data = self.generate_query(query_type, difficulty)
            query_data["id"] = f"query_{i+1}"

            # Generate relevance judgments
            relevance_data = self.generate_relevance_judgments(
                query_data["query"],
                query_data["topics"]
            )
            query_data.update(relevance_data)

            # Generate ground truth if requested
            if include_ground_truth and self.generator:
                ground_truth = await self.generate_ground_truth(query_data["query"])
                if ground_truth:
                    query_data["ground_truth_answer"] = ground_truth

            dataset.append(query_data)

            if (i + 1) % 10 == 0:
                logger.info(f"Generated {i + 1}/{num_queries} queries")

        logger.info(f"Dataset generation complete: {len(dataset)} queries")
        return dataset

    def save_dataset(
        self,
        dataset: List[Dict[str, Any]],
        output_path: str
    ):
        """
        Save dataset to JSON file.

        Args:
            dataset: Dataset to save
            output_path: Output file path
        """
        # Add metadata
        output = {
            "metadata": {
                "num_queries": len(dataset),
                "query_types": self._count_query_types(dataset),
                "difficulty_levels": self._count_difficulties(dataset),
                "has_ground_truth": any("ground_truth_answer" in q for q in dataset)
            },
            "queries": dataset
        }

        with open(output_path, "w") as f:
            json.dump(output, f, indent=2)

        logger.info(f"Dataset saved to {output_path}")

    def _count_query_types(self, dataset: List[Dict[str, Any]]) -> Dict[str, int]:
        """Count queries by type."""
        counts = {}
        for query in dataset:
            query_type = query["query_type"]
            counts[query_type] = counts.get(query_type, 0) + 1
        return counts

    def _count_difficulties(self, dataset: List[Dict[str, Any]]) -> Dict[str, int]:
        """Count queries by difficulty."""
        counts = {}
        for query in dataset:
            difficulty = query["difficulty"]
            counts[difficulty] = counts.get(difficulty, 0) + 1
        return counts

    def generate_statistics(self, dataset: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate statistics for dataset.

        Args:
            dataset: Dataset to analyze

        Returns:
            Dictionary with statistics
        """
        stats = {
            "total_queries": len(dataset),
            "query_types": self._count_query_types(dataset),
            "difficulty_levels": self._count_difficulties(dataset),
            "avg_query_length": sum(len(q["query"]) for q in dataset) / len(dataset) if dataset else 0,
            "avg_topics_per_query": sum(len(q["topics"]) for q in dataset) / len(dataset) if dataset else 0,
            "avg_relevant_docs": sum(q["num_relevant"] for q in dataset) / len(dataset) if dataset else 0,
            "has_ground_truth": sum(1 for q in dataset if "ground_truth_answer" in q)
        }

        return stats


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Generate synthetic evaluation dataset")
    parser.add_argument(
        "--num-queries",
        type=int,
        default=100,
        help="Number of queries to generate"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="evaluation_dataset.json",
        help="Output file path"
    )
    parser.add_argument(
        "--include-ground-truth",
        action="store_true",
        help="Generate ground truth answers using LLM"
    )
    parser.add_argument(
        "--methodological",
        type=float,
        default=0.25,
        help="Proportion of methodological queries"
    )
    parser.add_argument(
        "--results",
        type=float,
        default=0.20,
        help="Proportion of results queries"
    )
    parser.add_argument(
        "--comparative",
        type=float,
        default=0.20,
        help="Proportion of comparative queries"
    )
    parser.add_argument(
        "--definition",
        type=float,
        default=0.15,
        help="Proportion of definition queries"
    )
    parser.add_argument(
        "--general",
        type=float,
        default=0.20,
        help="Proportion of general queries"
    )
    parser.add_argument(
        "--easy",
        type=float,
        default=0.3,
        help="Proportion of easy queries"
    )
    parser.add_argument(
        "--medium",
        type=float,
        default=0.5,
        help="Proportion of medium queries"
    )
    parser.add_argument(
        "--hard",
        type=float,
        default=0.2,
        help="Proportion of hard queries"
    )

    args = parser.parse_args()

    # Initialize generator if ground truth requested
    generator = None
    if args.include_ground_truth:
        settings = Settings()
        if not settings.anthropic_api_key:
            logger.error("Anthropic API key required for ground truth generation")
            return

        generator = ClaudeGenerator(
            api_key=settings.anthropic_api_key,
            model="claude-sonnet-4-5-20250929"
        )
        logger.info("Initialized Claude generator for ground truth generation")

    # Create dataset generator
    dataset_generator = SyntheticDatasetGenerator(generator=generator)

    # Build distributions
    distribution = {
        QueryType.METHODOLOGICAL: args.methodological,
        QueryType.RESULTS: args.results,
        QueryType.COMPARATIVE: args.comparative,
        QueryType.DEFINITION: args.definition,
        QueryType.GENERAL: args.general
    }

    difficulty_distribution = {
        "easy": args.easy,
        "medium": args.medium,
        "hard": args.hard
    }

    # Normalize distributions
    total = sum(distribution.values())
    distribution = {k: v/total for k, v in distribution.items()}

    total_diff = sum(difficulty_distribution.values())
    difficulty_distribution = {k: v/total_diff for k, v in difficulty_distribution.items()}

    # Generate dataset
    dataset = await dataset_generator.generate_dataset(
        num_queries=args.num_queries,
        distribution=distribution,
        difficulty_distribution=difficulty_distribution,
        include_ground_truth=args.include_ground_truth
    )

    # Save dataset
    dataset_generator.save_dataset(dataset, args.output)

    # Print statistics
    stats = dataset_generator.generate_statistics(dataset)
    print("\nDataset Statistics:")
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
