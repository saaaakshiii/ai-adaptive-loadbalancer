
from urllib.request import urlopen
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter
from statistics import mean
from time import perf_counter
from math import ceil
import json

URL = "http://localhost:8000/proxy/work"
TOTAL_REQUESTS = 1800
MAX_WORKERS = 20


def get_algorithm():
    with urlopen("http://localhost:8000/algorithm") as response:
        return json.loads(response.read())["algorithm"]


def send_request():
    start = perf_counter()

    try:
        with urlopen(URL, timeout=10) as response:
            server = response.headers.get("X-Backend-Server", "unknown")
            algorithm = response.headers.get(
                "X-Load-Balancer-Algorithm", "unknown"
            )
            response.read()
            latency = (perf_counter() - start) * 1000

            return server, algorithm, latency, False

    except Exception:
        latency = (perf_counter() - start) * 1000
        return "failed", "unknown", latency, True

def main():
    algorithm = get_algorithm()

    latencies = []
    distribution = Counter()
    algorithm_distribution = Counter()
    errors = 0

    print(f"\n{algorithm.upper()} RESULTS")
    print(f"Sending {TOTAL_REQUESTS} requests with {MAX_WORKERS} workers...")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [
            executor.submit(send_request)
            for _ in range(TOTAL_REQUESTS)
        ]

        for future in as_completed(futures):
            server, used_algorithm, latency, failed = future.result()

            latencies.append(latency)
            distribution[server] += 1
            algorithm_distribution[used_algorithm] += 1

            if failed:
                errors += 1

    ordered = sorted(latencies)
    p95 = ordered[ceil(0.95 * len(ordered)) - 1] if ordered else 0

    print("\nBENCHMARK RESULTS")
    print("Algorithm:", algorithm)
    print("Requests:", TOTAL_REQUESTS)
    print("Concurrency:", MAX_WORKERS)
    print("Distribution:", dict(distribution))
    print("Algorithm distribution:", dict(algorithm_distribution))
    print("Average latency:", round(mean(latencies), 2), "ms")
    print("P95 latency:", round(p95, 2), "ms")
    print("Errors:", errors)


if __name__ == "__main__":
    main()
