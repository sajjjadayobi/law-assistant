"""Load testing script for Law Agent using Locust.

Usage:
    locust -f tests/load/locustfile.py --host=http://localhost:8000 --users=10 --spawn-rate=1

This script simulates realistic user behavior patterns for the Law Agent.
"""

import random
import time

from locust import HttpUser, between, events, task

# Sample test queries in Persian
SAMPLE_QUERIES = [
    "قوانین مربوط به بیمه اجتماعی چیست؟",
    "حقوق کارگری چه مراتبی دارد؟",
    "مالیات درآمد چطور محاسبه می‌شود؟",
    "فرایند ثبت نام شرکت به چه صورت است؟",
    "جرائم سایبری و مجازات های آن",
    "دادرسی مدنی و مراحل شکایت",
    "قوانین مرتبط با نوشتن وصیت‌نامه",
    "حقوق مستأجر و موجِّر در حق‌الاجاره",
    "قانون حمایت مصرف‌کنندگان",
    "فرایند طلاق و نفقه در قانون خانواده",
    "مسئولیت مدنی و بیمه شخص ثالث",
    "حقوق شهروندی و تابعیت",
]

FOLLOW_UP_QUERIES = [
    "توضیح بیشتر در مورد این قانون",
    "این قانون چه تاریخی تصویب شد؟",
    "مستثنیات این قانون چیست؟",
    "جزای تخلف از این قانون چیست؟",
    "نحوه اعتراض به تصمیم طبق این قانون",
]


class LawAgentUser(HttpUser):
    """Simulates a user interacting with Law Agent."""

    wait_time = between(2, 5)  # Wait 2-5 seconds between requests

    def on_start(self):
        """Called when a locust user is spawned."""
        self.conversation_id = None
        self.message_count = 0
        self.session_start_time = time.time()

    @task(3)
    def new_conversation_simple_query(self):
        """Start new conversation with simple query (3x weight)."""
        query = random.choice(SAMPLE_QUERIES)
        self.send_query(query, is_new=True)
        self.conversation_id = None

    @task(1)
    def multi_turn_conversation(self):
        """Multi-turn conversation with follow-ups (1x weight)."""
        # Start new conversation
        query = random.choice(SAMPLE_QUERIES)
        self.send_query(query, is_new=True)

        # Follow up with 1-2 related questions
        for _ in range(random.randint(1, 2)):
            follow_up = random.choice(FOLLOW_UP_QUERIES)
            time.sleep(random.uniform(1, 3))  # Simulate user reading response
            self.send_query(follow_up, is_new=False)

    def send_query(self, query: str, is_new: bool = False):
        """Send a query to the agent.

        Args:
            query: Query text
            is_new: Whether this starts a new conversation
        """
        headers = {
            "Content-Type": "application/json",
        }

        payload = {
            "message": query,
            "conversation_id": self.conversation_id if not is_new else None,
        }

        with self.client.post(
            "/api/chat",
            json=payload,
            headers=headers,
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    self.conversation_id = data.get("conversation_id")
                    self.message_count += 1
                    response.success()
                except Exception as e:
                    response.failure(f"Failed to parse response: {str(e)}")
            elif response.status_code == 500:
                response.failure(f"Server error: {response.text}")
            else:
                response.failure(f"Unexpected status: {response.status_code}")

    @task
    def get_health_check(self):
        """Occasional health checks (1x weight)."""
        with self.client.get("/health", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health check failed: {response.status_code}")

    @task
    def get_conversation_history(self):
        """Get conversation history if available."""
        if self.conversation_id:
            with self.client.get(
                f"/api/conversations/{self.conversation_id}",
                catch_response=True,
            ) as response:
                if response.status_code == 200:
                    response.success()
                else:
                    response.failure(f"Failed to get history: {response.status_code}")

    def on_stop(self):
        """Called when a locust user stops."""
        session_duration = time.time() - self.session_start_time
        print(f"User session ended: {self.message_count} messages in {session_duration:.1f}s")


# Event handlers for tracking aggregate statistics
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when load test starts."""
    print("\n" + "=" * 80)
    print("LOAD TEST STARTED")
    print("=" * 80)
    print(f"Target: {environment.host}")
    print(f"Users: {environment.runner.target_user_count}")
    print(f"Spawn rate: {environment.runner.spawn_rate} users/sec")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when load test stops."""
    print("\n" + "=" * 80)
    print("LOAD TEST COMPLETE")
    print("=" * 80)

    # Print summary statistics
    stats = environment.stats
    print("\nRequest Statistics:")
    for method in ["GET", "POST"]:
        method_stats = stats.entries.get((method, "/api/chat")) or stats.entries.get(
            (method, "/health")
        )
        if method_stats:
            print(f"\n{method} Requests:")
            print(f"  Total: {method_stats.num_requests}")
            print(f"  Failed: {method_stats.num_failures}")
            print(f"  Avg Response Time: {method_stats.avg_response_time:.0f}ms")
            print(f"  Min Response Time: {method_stats.min_response_time:.0f}ms")
            print(f"  Max Response Time: {method_stats.max_response_time:.0f}ms")
            print(f"  50th percentile: {method_stats.get_response_time_percentile(0.5):.0f}ms")
            print(f"  95th percentile: {method_stats.get_response_time_percentile(0.95):.0f}ms")
            print(f"  99th percentile: {method_stats.get_response_time_percentile(0.99):.0f}ms")


# Configuration for different load test scenarios
TEST_SCENARIOS = {
    "light": {
        "description": "Light load - 10 users",
        "users": 10,
        "spawn_rate": 1,
        "duration": 300,  # 5 minutes
    },
    "medium": {
        "description": "Medium load - 50 users",
        "users": 50,
        "spawn_rate": 5,
        "duration": 600,  # 10 minutes
    },
    "heavy": {
        "description": "Heavy load - 100 users",
        "users": 100,
        "spawn_rate": 10,
        "duration": 900,  # 15 minutes
    },
    "stress": {
        "description": "Stress test - 200 users",
        "users": 200,
        "spawn_rate": 20,
        "duration": 1200,  # 20 minutes
    },
}
