from urllib.request import urlopen
from collections import Counter
from statistics import mean
from time import perf_counter

latencies = []
distribution = Counter()

for i in range(60):
    start = perf_counter()

    with urlopen("http://localhost:8000/proxy/work", timeout=10) as response:
        server = response.headers.get("X-Backend-Server", "unknown")
        response.read()

    latencies.append((perf_counter() - start) * 1000)
    distribution[server] += 1

ordered = sorted(latencies)

print("\nQ-LEARNING RESULTS")
print("Requests:", len(latencies))
print("Distribution:", dict(distribution))
print("Average latency:", round(mean(latencies), 2), "ms")
print("P95 latency:", round(ordered[int(0.95 * len(ordered)) - 1], 2), "ms")
