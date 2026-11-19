import asyncio
import os
import time
from fastapi import FastAPI, HTTPException, Query
from backend.metrics import metrics
    
app = FastAPI(title="Backend Server")
SERVER_ID = os.getenv("SERVER_ID", "server-local")
DEFAULT_WORK_DELAYS = {
    "server-a": 0.30,
    "server-b": 0.10,
    "server-c": 0.05,
}

DEFAULT_WORK_DELAY = float(
    os.getenv(
        "WORK_DELAY_SECONDS",
        DEFAULT_WORK_DELAYS.get(SERVER_ID, 0.05)
    )
)
@app.get("/")
async def home():
    return {"message": "Backend is running", "server_id": SERVER_ID}

@app.get("/health")
async def health():
    return {"status": "healthy", "server_id": SERVER_ID}

@app.get("/metrics")
async def get_metrics():
    return metrics.snapshot(SERVER_ID)

@app.get("/work")
async def work(
    delay: float | None = Query(default=None, ge=0, le=5),
    fail: bool = False
):
    actual_delay = (
        DEFAULT_WORK_DELAY if delay is None else delay
    )

    metrics.active_requests += 1
    metrics.total_requests += 1
    started = time.perf_counter()

    try:
        await asyncio.sleep(actual_delay)

        if fail:
            metrics.failed_requests += 1
            raise HTTPException(
                status_code=500,
                detail="Simulated failure"
            )

        return {
            "server_id": SERVER_ID,
            "message": "Work completed",
            "simulated_processing_delay_ms": round(
                actual_delay * 1000, 2
            ),
        }

    finally:
        metrics.latencies_ms.append(
            (time.perf_counter() - started) * 1000
        )
        metrics.latencies_ms = metrics.latencies_ms[-500:]
        metrics.active_requests = max(
            0, metrics.active_requests - 1
        )