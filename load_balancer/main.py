import os
import time
from collections import deque
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel

from load_balancer.config import BACKENDS, Q_TABLE_PATH
from load_balancer.health_checker import collect_backend_metrics
from load_balancer.algorithms.round_robin import RoundRobin
from load_balancer.algorithms.least_connections import LeastConnections
from load_balancer.algorithms.q_learning import QLearningAgent

round_robin = RoundRobin()
least_connections = LeastConnections()
agent = QLearningAgent(table_path=Q_TABLE_PATH)
algorithm = "round_robin"
request_count = 0
error_count = 0
recent_requests = deque(maxlen=500)
client: httpx.AsyncClient | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global client
    client = httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=2.0))
    yield
    agent.save()
    await client.aclose()

app = FastAPI(title="AI Adaptive Load Balancer", lifespan=lifespan)

class AlgorithmUpdate(BaseModel):
    algorithm: str

async def current_metrics():
    results = await collect_backend_metrics(client, BACKENDS)
    healthy = [i for i, (ok, _) in enumerate(results) if ok]
    metrics = [m for _, m in results]
    return healthy, metrics

@app.get("/")
async def home():
    return {
        "project": "AI-Powered Adaptive Load Balancer",
        "algorithm": algorithm,
        "backends": len(BACKENDS),
        "proxy_endpoint": "/proxy/work?delay=0.05",
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/servers")
async def servers():
    healthy, metrics = await current_metrics()
    return {
        "servers": [
            {"name": b["name"], "url": b["url"], "healthy": i in healthy,
             "metrics": metrics[i]}
            for i, b in enumerate(BACKENDS)
        ]
    }

@app.get("/algorithm")
async def get_algorithm():
    return {"algorithm": algorithm, "available": ["round_robin", "least_connections", "q_learning"]}

@app.post("/algorithm")
async def set_algorithm(body: AlgorithmUpdate):
    global algorithm
    allowed = {"round_robin", "least_connections", "q_learning"}
    if body.algorithm not in allowed:
        raise HTTPException(400, f"Choose one of: {', '.join(sorted(allowed))}")
    algorithm = body.algorithm
    return {"algorithm": algorithm}

@app.get("/metrics")
async def get_metrics():
    healthy, backend_metrics = await current_metrics()
    latencies = [x["latency_ms"] for x in recent_requests]
    avg = sum(latencies) / len(latencies) if latencies else 0.0
    sorted_lat = sorted(latencies)
    p95 = sorted_lat[min(int(0.95 * len(sorted_lat)), len(sorted_lat)-1)] if sorted_lat else 0.0
    counts = {b["name"]: 0 for b in BACKENDS}
    for item in recent_requests:
        counts[item["server"]] += 1
    return {
        "algorithm": algorithm,
        "total_requests": request_count,
        "error_count": error_count,
        "healthy_servers": len(healthy),
        "server_request_distribution": counts,
        "average_latency_ms": round(avg, 2),
        "p95_latency_ms": round(p95, 2),
        "q_learning_updates": agent.updates,
        "epsilon": round(agent.epsilon, 4),
        "backends": [
            {"name": b["name"], "healthy": i in healthy, **backend_metrics[i]}
            for i, b in enumerate(BACKENDS)
        ],
        "recent_requests": list(recent_requests)[-100:],
    }

@app.api_route("/proxy/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_request(path: str, request: Request):
    global request_count, error_count
    healthy, before_metrics = await current_metrics()
    if not healthy:
        raise HTTPException(503, "No healthy backend servers")

    if algorithm == "round_robin":
        selected = round_robin.choose(healthy, before_metrics)
        state = None
    elif algorithm == "least_connections":
        selected = least_connections.choose(healthy, before_metrics)
        state = None
    else:
        state = agent.state_from_metrics(before_metrics)
        selected = agent.choose_action(state, healthy, len(BACKENDS))

    if selected is None:
        raise HTTPException(503, "No backend available")

    backend = BACKENDS[selected]
    started = time.perf_counter()
    status_code = 502
    success = False
    body = await request.body()
    target_url = f"{backend['url']}/{path}"
    if request.url.query:
        target_url += f"?{request.url.query}"

    headers = {
        k: v for k, v in request.headers.items()
        if k.lower() not in {"host", "content-length", "connection"}
    }

    try:
        upstream = await client.request(
            request.method, target_url, content=body, headers=headers
        )
        status_code = upstream.status_code
        success = 200 <= status_code < 400
        response_headers = {
            k: v for k, v in upstream.headers.items()
            if k.lower() in {"content-type", "cache-control"}
        }
        response = Response(
            content=upstream.content,
            status_code=status_code,
            headers=response_headers
        )
    except httpx.HTTPError:
        response = Response(
            content=b'{"detail":"Backend request failed"}',
            status_code=502,
            media_type="application/json"
        )

    latency_ms = (time.perf_counter() - started) * 1000
    request_count += 1
    if not success:
        error_count += 1

    recent_requests.append({
        "timestamp": time.time(),
        "server": backend["name"],
        "latency_ms": round(latency_ms, 2),
        "status_code": status_code,
        "success": success
    })

    if algorithm == "q_learning":
        next_healthy, after_metrics = await current_metrics()
        next_state = agent.state_from_metrics(after_metrics)
        cpu = float(before_metrics[selected].get("cpu_percent", 0))
        overload_penalty = max(0.0, cpu - 80.0) / 20.0
        # Reward successful, fast responses; penalize failures and overload.
        reward = (2.0 if success else -5.0) - min(latency_ms / 500.0, 4.0) - overload_penalty
        agent.update(
            state, selected, reward, next_state,
            next_healthy, len(BACKENDS)
        )

    response.headers["X-Backend-Server"] = backend["name"]
    response.headers["X-Load-Balancer-Algorithm"] = algorithm
    return response
