
import time


class AdaptiveController:
    """
    Observes workload metrics and recommends a routing algorithm.

    It does not route requests or modify the Q-learning agent.
    """

    ALGORITHMS = {
        "round_robin",
        "least_connections",
        "q_learning",
    }

    def __init__(
        self,
        evaluation_interval=2,
        required_confirmations=3,
        cooldown_seconds=10,
        min_q_learning_updates=30,
    ):
        self.evaluation_interval = evaluation_interval
        self.required_confirmations = required_confirmations
        self.cooldown_seconds = cooldown_seconds
        self.min_q_learning_updates = min_q_learning_updates

        self.pending_algorithm = None
        self.confirmation_count = 0
        self.last_switch_at = 0.0

    def classify_workload(self, recent_requests, backend_metrics, now):
        # Consider requests from the last 10 seconds.
        window = [
            request
            for request in recent_requests
            if now - request["timestamp"] <= 10
        ]

        request_rate = len(window) / 10.0

        latencies = [
            request["latency_ms"]
            for request in window
        ]

        average_latency = (
            sum(latencies) / len(latencies)
            if latencies else 0.0
        )

        error_rate = (
            sum(not request["success"] for request in window)
            / len(window)
            if window else 0.0
        )

        max_cpu = max(
            (float(m.get("cpu_percent", 0)) for m in backend_metrics),
            default=0.0,
        )

        max_active = max(
            (int(m.get("active_requests", 0)) for m in backend_metrics),
            default=0,
        )

        # High workload conditions.
        if (
            request_rate >= 8
            or average_latency >= 250
            or error_rate >= 0.10
            or max_cpu >= 75
            or max_active >= 8
        ):
            workload = "high"

        # Medium workload conditions.
        elif (
            request_rate >= 3
            or average_latency >= 120
            or error_rate >= 0.03
            or max_cpu >= 50
            or max_active >= 3
        ):
            workload = "medium"

        else:
            workload = "low"

        statistics = {
            "request_rate": round(request_rate, 2),
            "average_latency_ms": round(average_latency, 2),
            "error_rate": round(error_rate, 3),
            "max_cpu_percent": round(max_cpu, 2),
            "max_active_requests": max_active,
        }

        return workload, statistics

    def evaluate(
        self,
        current_algorithm,
        recent_requests,
        backend_metrics,
        q_learning_updates,
        healthy_count,
        now=None,
    ):
        now = time.monotonic() if now is None else now

        if healthy_count == 0:
            self.pending_algorithm = None
            self.confirmation_count = 0

            return {
                "workload": "unknown",
                "candidate": current_algorithm,
                "should_switch": False,
                "reason": "No healthy backend servers",
                "statistics": {},
            }

        workload, statistics = self.classify_workload(
            recent_requests,
            backend_metrics,
            now=time.time()
        )

        if workload == "low":
            candidate = "round_robin"
            reason = "Low workload: use fair round-robin distribution"

        elif workload == "medium":
            candidate = "least_connections"
            reason = "Moderate workload: prefer servers with fewer active requests"

        else:
            if q_learning_updates >= self.min_q_learning_updates:
                candidate = "q_learning"
                reason = "High workload: use the sufficiently trained Q-learning agent"
            else:
                candidate = "least_connections"
                reason = (
                    "High workload, but Q-learning has insufficient training; "
                    "using least connections as a fallback"
                )

        if candidate == current_algorithm:
            self.pending_algorithm = None
            self.confirmation_count = 0

            return {
                "workload": workload,
                "candidate": candidate,
                "should_switch": False,
                "reason": reason,
                "statistics": statistics,
            }

        if candidate == self.pending_algorithm:
            self.confirmation_count += 1
        else:
            self.pending_algorithm = candidate
            self.confirmation_count = 1

        cooldown_complete = (
            now - self.last_switch_at >= self.cooldown_seconds
        )

        should_switch = (
            self.confirmation_count >= self.required_confirmations
            and cooldown_complete
        )

        return {
            "workload": workload,
            "candidate": candidate,
            "should_switch": should_switch,
            "reason": reason,
            "confirmations": self.confirmation_count,
            "statistics": statistics,
        }

    def mark_switched(self, now=None):
        self.last_switch_at = (
            time.monotonic() if now is None else now
        )
        self.pending_algorithm = None
        self.confirmation_count = 0
