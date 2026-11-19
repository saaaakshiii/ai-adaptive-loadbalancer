
import time
import unittest

from load_balancer.adaptive_controller import AdaptiveController


class TestAdaptiveController(unittest.TestCase):

    def setUp(self):
        self.controller = AdaptiveController()
        self.backends = [
            {"cpu_percent": 10, "active_requests": 0},
            {"cpu_percent": 15, "active_requests": 0},
            {"cpu_percent": 20, "active_requests": 0},
        ]

    def evaluate(self, backends=None, requests=None, updates=50,
                 current="round_robin", now=100):
        return self.controller.evaluate(
            current_algorithm=current,
            recent_requests=requests or [],
            backend_metrics=backends or self.backends,
            q_learning_updates=updates,
            healthy_count=3,
            now=now,
        )

    def test_low_workload(self):
        result = self.evaluate()
        self.assertEqual(result["workload"], "low")
        self.assertEqual(result["candidate"], "round_robin")
        self.assertFalse(result["should_switch"])

    def test_medium_workload(self):
        backends = [
            {"cpu_percent": 10, "active_requests": 3},
            {"cpu_percent": 15, "active_requests": 0},
            {"cpu_percent": 20, "active_requests": 0},
        ]

        result = self.evaluate(backends=backends)

        self.assertEqual(result["workload"], "medium")
        self.assertEqual(result["candidate"], "least_connections")

    def test_high_workload_with_trained_agent(self):
        requests = [
            {
                "timestamp": time.time() - 1,
                "latency_ms": 300,
                "success": True,
            }
            for _ in range(100)
        ]

        result = self.evaluate(
            requests=requests,
            updates=50,
        )

        self.assertEqual(result["workload"], "high")
        self.assertEqual(result["candidate"], "q_learning")

    def test_high_workload_without_training(self):
        requests = [
            {
                "timestamp": time.time() - 1,
                "latency_ms": 300,
                "success": True,
            }
            for _ in range(100)
        ]

        result = self.evaluate(
            requests=requests,
            updates=5,
        )

        self.assertEqual(result["candidate"], "least_connections")

    def test_three_confirmations_required(self):
        requests = [
            {
                "timestamp": time.time() - 1,
                "latency_ms": 300,
                "success": True,
            }
            for _ in range(100)
        ]

        first = self.evaluate(
            requests=requests, current="round_robin", now=20
        )
        second = self.evaluate(
            requests=requests, current="round_robin", now=22
        )
        third = self.evaluate(
            requests=requests, current="round_robin", now=24
        )

        self.assertFalse(first["should_switch"])
        self.assertFalse(second["should_switch"])
        self.assertTrue(third["should_switch"])


if __name__ == "__main__":
    unittest.main()
