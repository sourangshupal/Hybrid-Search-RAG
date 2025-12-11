"""Load testing with Locust for Hybrid Search RAG API."""

import json
import random
from locust import HttpUser, task, between, events
from locust.runners import MasterRunner


# Sample queries for load testing
SAMPLE_QUERIES = [
    "What are transformers in machine learning?",
    "How does BERT work?",
    "Explain attention mechanism in neural networks",
    "What is the difference between GPT and BERT?",
    "How does backpropagation work?",
    "What is transfer learning?",
    "Explain convolutional neural networks",
    "What is reinforcement learning?",
    "How does gradient descent work?",
    "What are recurrent neural networks?",
    "Explain self-attention mechanism",
    "What is few-shot learning?",
    "How does prompt engineering work?",
    "What are large language models?",
    "Explain fine-tuning in deep learning",
    "What is knowledge distillation?",
    "How does model compression work?",
    "What are generative adversarial networks?",
    "Explain meta-learning",
    "What is contrastive learning?"
]

# Sample search queries
SEARCH_QUERIES = {
    "semantic": [
        "neural network architectures",
        "deep learning optimization",
        "transformer models",
        "attention mechanisms",
        "natural language processing"
    ],
    "lexical": [
        "machine learning",
        "artificial intelligence",
        "computer vision",
        "reinforcement learning",
        "transfer learning"
    ],
    "hybrid": [
        "BERT and GPT comparison",
        "how transformers work",
        "attention mechanism explained",
        "deep learning basics",
        "neural network training"
    ]
}


class HybridRAGUser(HttpUser):
    """
    Load test user for Hybrid Search RAG API.

    Simulates realistic user behavior with various endpoints.
    """

    # Wait between 1-5 seconds between tasks
    wait_time = between(1, 5)

    def on_start(self):
        """Called when a user starts."""
        # Check if API is healthy
        with self.client.get("/health", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health check failed: {response.status_code}")

    @task(5)
    def rag_query(self):
        """Test RAG query endpoint (most common operation)."""
        query = random.choice(SAMPLE_QUERIES)

        with self.client.post(
            "/api/v1/query",
            json={
                "query": query,
                "retrieval_top_k": 20,
                "rerank_top_k": 10,
                "include_sources": True
            },
            catch_response=True,
            name="/api/v1/query"
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "answer" in data and "citations" in data:
                        response.success()
                    else:
                        response.failure("Invalid response structure")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"Status code: {response.status_code}")

    @task(3)
    def semantic_search(self):
        """Test semantic search endpoint."""
        query = random.choice(SEARCH_QUERIES["semantic"])

        with self.client.post(
            "/api/v1/search/semantic",
            json={
                "query": query,
                "top_k": 10
            },
            catch_response=True,
            name="/api/v1/search/semantic"
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "results" in data and "total_results" in data:
                        response.success()
                    else:
                        response.failure("Invalid response structure")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"Status code: {response.status_code}")

    @task(2)
    def lexical_search(self):
        """Test lexical search endpoint."""
        query = random.choice(SEARCH_QUERIES["lexical"])

        with self.client.post(
            "/api/v1/search/lexical",
            json={
                "query": query,
                "top_k": 10
            },
            catch_response=True,
            name="/api/v1/search/lexical"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status code: {response.status_code}")

    @task(4)
    def hybrid_search(self):
        """Test hybrid search endpoint."""
        query = random.choice(SEARCH_QUERIES["hybrid"])

        with self.client.post(
            "/api/v1/search/hybrid",
            json={
                "query": query,
                "top_k": 20,
                "rerank": True
            },
            catch_response=True,
            name="/api/v1/search/hybrid"
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "reranked" in data:
                        response.success()
                    else:
                        response.failure("Invalid response structure")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"Status code: {response.status_code}")

    @task(1)
    def health_check(self):
        """Test health check endpoint."""
        with self.client.get(
            "/health",
            catch_response=True,
            name="/health"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status code: {response.status_code}")

    @task(1)
    def metrics_check(self):
        """Test metrics endpoint."""
        with self.client.get(
            "/metrics",
            catch_response=True,
            name="/metrics"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status code: {response.status_code}")

    @task(1)
    def api_info(self):
        """Test API info endpoint."""
        with self.client.get(
            "/api/v1/info",
            catch_response=True,
            name="/api/v1/info"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status code: {response.status_code}")


class QuickRAGUser(HttpUser):
    """
    Fast load test user for quick iterations.

    Only tests core endpoints without waiting.
    """

    wait_time = between(0.1, 0.5)

    @task(10)
    def quick_search(self):
        """Quick semantic search."""
        query = random.choice(SEARCH_QUERIES["semantic"])

        self.client.post(
            "/api/v1/search/semantic",
            json={"query": query, "top_k": 5},
            name="/api/v1/search/semantic (quick)"
        )

    @task(5)
    def quick_rag(self):
        """Quick RAG query."""
        query = random.choice(SAMPLE_QUERIES[:5])  # Use only first 5

        self.client.post(
            "/api/v1/query",
            json={
                "query": query,
                "retrieval_top_k": 10,
                "rerank_top_k": 5,
                "include_sources": False
            },
            name="/api/v1/query (quick)"
        )


class StressTestUser(HttpUser):
    """
    Stress test user with aggressive load.

    No wait time, continuous requests.
    """

    wait_time = between(0, 0.1)

    @task
    def stress_search(self):
        """Stress test search endpoints."""
        endpoint = random.choice([
            "/api/v1/search/semantic",
            "/api/v1/search/lexical",
            "/api/v1/search/hybrid"
        ])

        query = random.choice(SAMPLE_QUERIES)

        self.client.post(
            endpoint,
            json={"query": query, "top_k": 10},
            name=f"{endpoint} (stress)"
        )


# Event hooks for custom reporting
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when test starts."""
    print("\n" + "="*80)
    print("LOAD TEST STARTED")
    print("="*80)
    print(f"Target: {environment.host}")
    print(f"Users: {environment.runner.target_user_count if hasattr(environment.runner, 'target_user_count') else 'N/A'}")
    print("="*80 + "\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when test stops."""
    print("\n" + "="*80)
    print("LOAD TEST COMPLETED")
    print("="*80)

    stats = environment.runner.stats
    print(f"Total requests: {stats.total.num_requests}")
    print(f"Total failures: {stats.total.num_failures}")
    print(f"Failure rate: {stats.total.fail_ratio * 100:.2f}%")
    print(f"Average response time: {stats.total.avg_response_time:.2f}ms")
    print(f"Max response time: {stats.total.max_response_time:.2f}ms")
    print(f"Requests/sec: {stats.total.current_rps:.2f}")

    if stats.total.avg_response_time > 3000:
        print("\n⚠️  WARNING: Average response time exceeds 3s target!")

    print("="*80 + "\n")


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """Called for each request."""
    # Log slow requests
    if response_time > 5000:  # 5 seconds
        print(f"⚠️  Slow request detected: {name} took {response_time:.0f}ms")


# Custom load test shapes (optional)
from locust import LoadTestShape


class StepLoadShape(LoadTestShape):
    """
    Step load test: gradually increase users.

    Stages:
    1. 10 users for 1 minute
    2. 25 users for 2 minutes
    3. 50 users for 2 minutes
    4. 100 users for 3 minutes
    5. 50 users for 1 minute (cooldown)
    """

    stages = [
        {"duration": 60, "users": 10, "spawn_rate": 2},
        {"duration": 180, "users": 25, "spawn_rate": 3},
        {"duration": 300, "users": 50, "spawn_rate": 5},
        {"duration": 480, "users": 100, "spawn_rate": 10},
        {"duration": 540, "users": 50, "spawn_rate": 5},
    ]

    def tick(self):
        """Define load shape."""
        run_time = self.get_run_time()

        for stage in self.stages:
            if run_time < stage["duration"]:
                return (stage["users"], stage["spawn_rate"])

        return None  # Stop test


class SpikeLoadShape(LoadTestShape):
    """
    Spike load test: sudden traffic spikes.

    Pattern:
    - Start with 10 users
    - Spike to 100 users at 1 minute
    - Drop to 20 users
    - Spike to 150 users at 3 minutes
    - End
    """

    stages = [
        {"duration": 60, "users": 10, "spawn_rate": 2},
        {"duration": 90, "users": 100, "spawn_rate": 50},  # Sudden spike
        {"duration": 180, "users": 20, "spawn_rate": 10},
        {"duration": 210, "users": 150, "spawn_rate": 50},  # Another spike
        {"duration": 300, "users": 10, "spawn_rate": 10},
    ]

    def tick(self):
        """Define load shape."""
        run_time = self.get_run_time()

        for stage in self.stages:
            if run_time < stage["duration"]:
                return (stage["users"], stage["spawn_rate"])

        return None


# Usage instructions
"""
Run load tests:

# Basic test (web UI)
locust -f tests/load/locustfile.py --host=http://localhost:8000

# Headless mode
locust -f tests/load/locustfile.py --host=http://localhost:8000 \\
    --users 100 --spawn-rate 10 --run-time 5m --headless

# With specific user class
locust -f tests/load/locustfile.py --host=http://localhost:8000 \\
    --users 50 --spawn-rate 5 HybridRAGUser

# Quick test
locust -f tests/load/locustfile.py --host=http://localhost:8000 \\
    --users 20 --spawn-rate 5 --run-time 2m QuickRAGUser

# Stress test
locust -f tests/load/locustfile.py --host=http://localhost:8000 \\
    --users 200 --spawn-rate 20 --run-time 3m StressTestUser

# Step load shape
locust -f tests/load/locustfile.py --host=http://localhost:8000 \\
    --headless --users 100 --spawn-rate 10 StepLoadShape

# Spike test
locust -f tests/load/locustfile.py --host=http://localhost:8000 \\
    --headless --users 150 --spawn-rate 50 SpikeLoadShape

# Export results
locust -f tests/load/locustfile.py --host=http://localhost:8000 \\
    --users 100 --spawn-rate 10 --run-time 10m --headless \\
    --html report.html --csv results
"""
