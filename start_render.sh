
#!/usr/bin/env bash
set -e

HOST="127.0.0.1"
LB_PORT="${PORT:-10000}"

echo "Starting backend server A..."
SERVER_ID=server-a uvicorn backend.main:app --host "$HOST" --port 8001 &
PID_A=$!

echo "Starting backend server B..."
SERVER_ID=server-b uvicorn backend.main:app --host "$HOST" --port 8002 &
PID_B=$!

echo "Starting backend server C..."
SERVER_ID=server-c uvicorn backend.main:app --host "$HOST" --port 8003 &
PID_C=$!

LB_PID=""

cleanup() {
    echo "Stopping application processes..."

    if [ -n "$LB_PID" ]; then
        kill "$LB_PID" 2>/dev/null || true
    fi

    kill "$PID_A" "$PID_B" "$PID_C" 2>/dev/null || true
}

trap cleanup EXIT INT TERM

echo "Waiting for backend health checks..."

for port in 8001 8002 8003; do
    ready=false

    for attempt in $(seq 1 30); do
        if python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:${port}/health', timeout=2)" 2>/dev/null; then
            ready=true
            break
        fi

        sleep 1
    done

    if [ "$ready" != true ]; then
        echo "Backend on port $port failed to become healthy."
        exit 1
    fi

    echo "Backend on port $port is healthy."
done

echo "Starting adaptive load balancer on port $LB_PORT..."

uvicorn load_balancer.main:app --host 0.0.0.0 --port "$LB_PORT" &
LB_PID=$!

wait "$LB_PID"
