# AI-Powered Adaptive Load Balancer

A five-day prototype demonstrating distributed HTTP services, baseline load-balancing algorithms, tabular Q-learning, monitoring and load testing.

## Architecture

- Three FastAPI backend containers (`server-a`, `server-b`, `server-c`)
- FastAPI reverse proxy / load balancer
- Round Robin, Least Connections and Q-learning routing
- Backend metrics: CPU, memory, active requests, request count and latency
- Streamlit dashboard
- Locust load testing

## Run with Docker

Prerequisites: Docker Engine and Docker Compose plugin.

```bash
docker compose up --build
```

Open:
- Load balancer API: http://localhost:8000
- API docs: http://localhost:8000/docs
- Dashboard: http://localhost:8501

Send a test request:

```bash
curl -i "http://localhost:8000/proxy/work?delay=0.05"
```

The response includes `X-Backend-Server` and `X-Load-Balancer-Algorithm` headers.

## Change routing algorithm

```bash
curl -X POST http://localhost:8000/algorithm \
  -H "Content-Type: application/json" \
  -d '{"algorithm":"q_learning"}'
```

Allowed values: `round_robin`, `least_connections`, `q_learning`.

Inspect backend status and aggregate metrics:

```bash
curl http://localhost:8000/servers
curl http://localhost:8000/metrics
```

## Run Locust

```bash
docker compose --profile loadtest up --build
```

Open http://localhost:8089. Set the number of users and spawn rate, then start the test.

For fair comparisons, repeat the same workload for each algorithm and record average/P95 latency, throughput, failures and per-server request distribution.

## Simulate failure

```bash
docker compose stop server-b
```

The load balancer checks health before routing and should exclude the stopped server.

Restart it:

```bash
docker compose start server-b
```

## Q-learning formulation

- State: a compact string with one load bucket per backend (`0` low, `1` medium, `2` high).
- Action: choose a backend index.
- Reward: positive for successful, fast responses; negative for failed, slow or overloaded outcomes.
- Policy: epsilon-greedy exploration/exploitation.
- Update: standard tabular Q-learning temporal-difference update.

The Q-table is persisted in `data/q_table.json`.

## Important experimental caveats

1. This is a prototype, not a production load balancer.
2. CPU and memory readings from containers are host/process-level approximations; use consistent environments and report this limitation.
3. Q-learning is online and initially explores. Do not claim it is better until repeated, controlled experiments support that conclusion.
4. Use the same request profile, duration and machine conditions for every baseline.
5. A request's latency includes network/proxy overhead as well as backend processing.
6. The simple tabular state is intentionally small for the short project deadline. More state variables can cause state-space growth.

## Local run without Docker

Start three terminals:

```bash
SERVER_ID=server-a uvicorn backend.main:app --port 8001
SERVER_ID=server-b uvicorn backend.main:app --port 8002
SERVER_ID=server-c uvicorn backend.main:app --port 8003
```

Then start the load balancer with local backend URLs:

```bash
BACKENDS="server-a=http://127.0.0.1:8001,server-b=http://127.0.0.1:8002,server-c=http://127.0.0.1:8003" uvicorn load_balancer.main:app --port 8000
```

Install dependencies first with `pip install -r requirements.txt`.
