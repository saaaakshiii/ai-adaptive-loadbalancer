import time
import psutil

class ServerMetrics:
    def __init__(self):
        self.active_requests = 0
        self.total_requests = 0
        self.failed_requests = 0
        self.latencies_ms = []
        self.started_at = time.time()

    def snapshot(self, server_id: str):
        recent = self.latencies_ms[-100:]
        avg_latency = sum(recent) / len(recent) if recent else 0.0
        return {
            "server_id": server_id,
            "cpu_percent": psutil.cpu_percent(interval=None),
            "memory_percent": psutil.virtual_memory().percent,
            "active_requests": self.active_requests,
            "total_requests": self.total_requests,
            "failed_requests": self.failed_requests,
            "average_latency_ms": round(avg_latency, 2),
            "uptime_seconds": round(time.time() - self.started_at, 1),
        }

metrics = ServerMetrics()
