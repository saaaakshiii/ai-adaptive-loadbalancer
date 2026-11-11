import os

def load_backends():
    raw = os.getenv(
        "BACKENDS",
        "server-a=http://127.0.0.1:8001,server-b=http://127.0.0.1:8002,server-c=http://127.0.0.1:8003",
    )
    result = []
    for item in raw.split(","):
        name, url = item.strip().split("=", 1)
        result.append({"name": name, "url": url.rstrip("/")})
    return result

BACKENDS = load_backends()
Q_TABLE_PATH = os.getenv("Q_TABLE_PATH", "data/q_table.json")
