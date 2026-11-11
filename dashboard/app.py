import os
import time
import requests
import pandas as pd
import streamlit as st

LB_URL = os.getenv("LB_URL", "http://localhost:8000")

st.set_page_config(page_title="Adaptive Load Balancer", layout="wide")
st.title("AI-Powered Adaptive Load Balancer")
st.caption("Distributed backend monitoring and routing experiments")

with st.sidebar:
    st.header("Routing control")
    selected = st.selectbox(
        "Select algorithm",
        ["round_robin", "least_connections", "q_learning"],
        format_func=lambda x: {
            "round_robin": "Round Robin",
            "least_connections": "Least Connections",
            "q_learning": "Q-learning",
        }[x]
    )
    if st.button("Apply algorithm", use_container_width=True):
        try:
            r = requests.post(f"{LB_URL}/algorithm", json={"algorithm": selected}, timeout=3)
            r.raise_for_status()
            st.success("Algorithm updated")
        except requests.RequestException as exc:
            st.error(f"Could not update algorithm: {exc}")
    auto = st.checkbox("Auto-refresh every 3 seconds", value=False)

try:
    metrics = requests.get(f"{LB_URL}/metrics", timeout=3).json()
    servers = requests.get(f"{LB_URL}/servers", timeout=3).json()["servers"]
except requests.RequestException as exc:
    st.error(f"Cannot reach load balancer at {LB_URL}: {exc}")
    st.stop()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total requests", metrics["total_requests"])
c2.metric("Average latency", f'{metrics["average_latency_ms"]} ms')
c3.metric("P95 latency", f'{metrics["p95_latency_ms"]} ms')
c4.metric("Healthy servers", metrics["healthy_servers"])

st.subheader("Backend server status")
df = pd.DataFrame([{
    "Server": s["name"],
    "Healthy": "Yes" if s["healthy"] else "No",
    "CPU %": s["metrics"].get("cpu_percent", 0),
    "Memory %": s["metrics"].get("memory_percent", 0),
    "Active requests": s["metrics"].get("active_requests", 0),
    "Total requests": s["metrics"].get("total_requests", 0),
    "Average server latency (ms)": s["metrics"].get("average_latency_ms", 0),
} for s in servers])
st.dataframe(df, use_container_width=True, hide_index=True)

left, right = st.columns(2)
with left:
    st.subheader("Request distribution")
    dist = metrics["server_request_distribution"]
    st.bar_chart(pd.DataFrame({"Requests": dist}).T)
with right:
    st.subheader("Recent request latency")
    recent = pd.DataFrame(metrics["recent_requests"])
    if not recent.empty:
        recent = recent.reset_index(names="request_number")
        st.line_chart(recent.set_index("request_number")["latency_ms"])
    else:
        st.info("No requests recorded yet. Start Locust or call /proxy/work.")

st.subheader("Learning status")
a, b, c = st.columns(3)
a.metric("Current algorithm", metrics["algorithm"])
b.metric("Q-table updates", metrics["q_learning_updates"])
c.metric("Exploration rate (epsilon)", metrics["epsilon"])

st.info("Open http://localhost:8000/docs for the load balancer API. Use /proxy/work?delay=0.05 to send a test request.")

if auto:
    time.sleep(3)
    st.rerun()
