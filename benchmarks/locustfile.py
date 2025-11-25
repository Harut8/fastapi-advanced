"""
Locust load testing scenarios for comparing msgspec vs Pydantic performance.

This file defines realistic API usage patterns to benchmark the performance
difference between msgspec and pure Pydantic serialization.

Usage:
    # Test msgspec app (port 8000)
    locust -f benchmarks/locustfile.py --host=http://localhost:8000

    # Test Pydantic app (port 8001)
    locust -f benchmarks/locustfile.py --host=http://localhost:8001

    # Headless mode with specific load
    locust -f benchmarks/locustfile.py --host=http://localhost:8000 \
           --users 100 --spawn-rate 10 --run-time 60s --headless
"""
import random
from typing import Any, Dict

from locust import HttpUser, between, task


class APIUser(HttpUser):
    """
    Simulates realistic API user behavior with mixed workload.

    Weight distribution:
    - 50%: Read operations (GET single user, GET list)
    - 30%: Create operations (POST)
    - 15%: Update operations (PUT)
    - 5%: Delete operations (DELETE)
    """

    wait_time = between(0.5, 2.0)  # Wait 0.5-2 seconds between requests
    user_ids: list[int] = []

    def on_start(self) -> None:
        """Initialize test data when a simulated user starts."""
        # Seed some users if database is empty
        response = self.client.post("/users/seed", params={"count": 50})
        if response.status_code == 200:
            # Populate user_ids for subsequent operations
            self.user_ids = list(range(1, 51))

    @task(20)
    def get_health(self) -> None:
        """Health check endpoint (lightweight operation)."""
        self.client.get("/", name="GET /health")

    @task(30)
    def get_user(self) -> None:
        """Retrieve a single user by ID."""
        if self.user_ids:
            user_id = random.choice(self.user_ids)
            self.client.get(f"/users/{user_id}", name="GET /users/:id")

    @task(50)
    def list_users(self) -> None:
        """
        List users with pagination (most common operation).

        This tests serialization of large response payloads (100 users).
        """
        page = random.randint(1, 5)
        self.client.get(
            "/users",
            params={"page": page, "page_size": 100},
            name="GET /users (paginated)",
        )

    @task(30)
    def create_user(self) -> None:
        """
        Create a new user (tests request validation + response serialization).
        """
        user_num = random.randint(1000, 9999)
        payload = {
            "username": f"user_{user_num}",
            "email": f"user{user_num}@example.com",
            "fullName": f"Test User {user_num}",
            "isActive": True,
        }
        response = self.client.post("/users", json=payload, name="POST /users")
        if response.status_code == 201:
            try:
                data = response.json()
                if "data" in data and "id" in data["data"]:
                    self.user_ids.append(data["data"]["id"])
            except Exception:
                pass

    @task(15)
    def update_user(self) -> None:
        """Update an existing user."""
        if self.user_ids:
            user_id = random.choice(self.user_ids)
            payload = {
                "fullName": f"Updated User {user_id}",
                "isActive": random.choice([True, False]),
            }
            self.client.put(f"/users/{user_id}", json=payload, name="PUT /users/:id")

    @task(5)
    def delete_user(self) -> None:
        """Delete a user (least common operation)."""
        if len(self.user_ids) > 10:  # Keep at least 10 users
            user_id = self.user_ids.pop(random.randint(0, len(self.user_ids) - 1))
            self.client.delete(f"/users/{user_id}", name="DELETE /users/:id")


class ReadHeavyUser(HttpUser):
    """
    Read-heavy workload pattern (90% reads, 10% writes).

    Use this for testing scenarios where the API is primarily read-focused,
    such as public-facing APIs or content delivery.
    """

    wait_time = between(0.1, 0.5)

    @task(50)
    def list_users(self) -> None:
        """List users - primary operation."""
        page = random.randint(1, 10)
        self.client.get(
            "/users",
            params={"page": page, "page_size": 100},
            name="GET /users (paginated)",
        )

    @task(40)
    def get_user(self) -> None:
        """Get single user."""
        user_id = random.randint(1, 100)
        self.client.get(f"/users/{user_id}", name="GET /users/:id")

    @task(10)
    def create_user(self) -> None:
        """Occasional write operation."""
        user_num = random.randint(1000, 9999)
        payload = {
            "username": f"user_{user_num}",
            "email": f"user{user_num}@example.com",
            "fullName": f"Test User {user_num}",
            "isActive": True,
        }
        self.client.post("/users", json=payload, name="POST /users")


class WriteHeavyUser(HttpUser):
    """
    Write-heavy workload pattern (70% writes, 30% reads).

    Use this for testing scenarios where the API handles frequent updates,
    such as real-time data ingestion or high-frequency trading systems.
    """

    wait_time = between(0.1, 0.5)
    user_ids: list[int] = []

    def on_start(self) -> None:
        """Initialize with some users."""
        response = self.client.post("/users/seed", params={"count": 20})
        if response.status_code == 200:
            self.user_ids = list(range(1, 21))

    @task(40)
    def create_user(self) -> None:
        """Frequent user creation."""
        user_num = random.randint(1000, 9999)
        payload = {
            "username": f"user_{user_num}",
            "email": f"user{user_num}@example.com",
            "fullName": f"Test User {user_num}",
            "isActive": True,
        }
        response = self.client.post("/users", json=payload, name="POST /users")
        if response.status_code == 201:
            try:
                data = response.json()
                if "data" in data and "id" in data["data"]:
                    self.user_ids.append(data["data"]["id"])
            except Exception:
                pass

    @task(30)
    def update_user(self) -> None:
        """Frequent updates."""
        if self.user_ids:
            user_id = random.choice(self.user_ids)
            payload = {
                "fullName": f"Updated User {user_id}",
                "isActive": random.choice([True, False]),
            }
            self.client.put(f"/users/{user_id}", json=payload, name="PUT /users/:id")

    @task(20)
    def list_users(self) -> None:
        """Occasional reads."""
        self.client.get(
            "/users",
            params={"page": 1, "page_size": 100},
            name="GET /users (paginated)",
        )

    @task(10)
    def get_user(self) -> None:
        """Single user retrieval."""
        if self.user_ids:
            user_id = random.choice(self.user_ids)
            self.client.get(f"/users/{user_id}", name="GET /users/:id")
