
import json
from pathlib import Path
from urllib.request import urlopen
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Experiments | Adaptive Load Balancer",
    page_icon="🧪",
    layout="wide",
)

st.title("🧪 Routing Algorithm Experiments")
st.caption(
    "Compare routing strategies using controlled benchmark results."
)

# Load saved benchmark results
DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "benchmark_results.json"

try:
    with open(DATA_FILE, "r") as file:
        benchmark_data = json.load(file)
except (FileNotFoundError, json.JSONDecodeError) as exc:
    st.error(f"Could not load benchmark results: {exc}")
    st.stop()

experiments = benchmark_data.get("experiments", [])

if not experiments:
    st.warning("No benchmark results available.")
    st.stop()

# Separate standalone algorithm benchmarks from adaptive experiments
standalone_experiments = [
    item for item in experiments
    if item["algorithm"] in ("round_robin", "least_connections", "q_learning")
]

adaptive_experiments = [
    item for item in experiments
    if item["algorithm"] == "adaptive"
]

df = pd.DataFrame(standalone_experiments)

# Header
st.subheader("Benchmark overview")

st.write(
    "All algorithms are compared using the same workload size "
    "where possible. Lower latency is better."
)

# Calculate Q-learning improvement against Round Robin
round_robin = next(
    (item for item in experiments
     if item["algorithm"] == "round_robin"),
    None,
)

q_learning = next(
    (item for item in experiments
     if item["algorithm"] == "q_learning"),
    None,
)

if round_robin and q_learning:
    rr_latency = round_robin["average_latency_ms"]
    q_latency = q_learning["average_latency_ms"]

    improvement = (
        (rr_latency - q_latency) / rr_latency * 100
        if rr_latency > 0 else 0
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Round Robin Average",
        f"{rr_latency:.2f} ms",
    )

    c2.metric(
        "Q-learning Average",
        f"{q_latency:.2f} ms",
    )

    c3.metric(
        "Average latency reduction",
        f"{improvement:.1f}%",
    )

    c4.metric(
        "Requests per experiment",
        str(round_robin["requests"]),
    )

st.divider()

# Average latency comparison
st.subheader("1. Average latency comparison")

latency_df = df[["display_name", "average_latency_ms"]].copy()
latency_df = latency_df.set_index("display_name")
latency_df.columns = ["Average latency (ms)"]

st.bar_chart(latency_df)

# P95 comparison
st.subheader("2. P95 latency comparison")

p95_df = df[["display_name", "p95_latency_ms"]].copy()
p95_df = p95_df.set_index("display_name")
p95_df.columns = ["P95 latency (ms)"]

st.bar_chart(p95_df)

st.caption(
    "P95 latency represents the threshold below which approximately "
    "95% of recorded requests completed."
)

# Request distribution
st.subheader("3. Backend request distribution")

distribution_rows = []

for experiment in experiments:
    for server, count in experiment["distribution"].items():
        distribution_rows.append({
            "Algorithm": experiment["display_name"],
            "Server": server,
            "Requests": count,
        })

distribution_df = pd.DataFrame(distribution_rows)

if not distribution_df.empty:
    distribution_chart = distribution_df.pivot(
        index="Server",
        columns="Algorithm",
        values="Requests",
    ).fillna(0)

    st.bar_chart(distribution_chart)

# Detailed results
st.subheader("4. Detailed benchmark results")

results_table = df[
    [
        "display_name",
        "requests",
        "concurrency",
        "average_latency_ms",
        "p95_latency_ms",
        "errors",
        "date",
    ]
].rename(columns={
    "display_name": "Algorithm",
    "requests": "Requests",
    "concurrency": "Concurrent workers",
    "average_latency_ms": "Average latency (ms)",
    "p95_latency_ms": "P95 latency (ms)",
    "errors": "Errors",
    "date": "Date",
})

st.dataframe(
    results_table,
    use_container_width=True,
    hide_index=True,
)

st.divider()

st.subheader("5. Average latency reduction vs Round Robin")

if round_robin:
    rr_latency = round_robin["average_latency_ms"]

    comparison_rows = []

    for experiment in experiments:
        latency = experiment["average_latency_ms"]

        reduction = (
            (rr_latency - latency) / rr_latency * 100
            if rr_latency > 0 else 0
        )

        comparison_rows.append({
            "Algorithm": experiment["display_name"],
            "Latency reduction (%)": round(reduction, 2),
        })

    comparison_df = pd.DataFrame(comparison_rows)
    st.bar_chart(
        comparison_df.set_index("Algorithm"),
        y="Latency reduction (%)",
    )

    st.caption(
    "Round Robin is the baseline (0% reduction). "
    "Positive values indicate lower average latency than Round Robin."
    )

# Adaptive benchmark results
st.divider()
st.subheader("6. Adaptive Load Balancer Experiment")

if adaptive_experiments:
    adaptive = adaptive_experiments[0]

    st.write(
        "Unlike standalone benchmarks, this experiment allows the "
        "controller to switch routing algorithms dynamically based "
        "on workload conditions."
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Total requests", adaptive["requests"])
    c2.metric("Concurrent workers", adaptive["concurrency"])
    c3.metric(
        "Average latency",
        f'{adaptive["average_latency_ms"]:.2f} ms'
    )
    c4.metric(
        "P95 latency",
        f'{adaptive["p95_latency_ms"]:.2f} ms'
    )

    st.markdown("#### Requests handled by each algorithm")

    algorithm_distribution = adaptive.get(
        "algorithm_distribution", {}
    )

    if algorithm_distribution:
        algorithm_df = pd.DataFrame(
            [
                {"Algorithm": name.replace("_", " ").title(),
                 "Requests": count}
                for name, count in algorithm_distribution.items()
            ]
        )

        st.bar_chart(
            algorithm_df.set_index("Algorithm")
        )

        total = sum(algorithm_distribution.values())

        for name, count in algorithm_distribution.items():
            percentage = count / total * 100 if total else 0

            st.write(
                f"**{name.replace('_', ' ').title()}:** "
                f"{count:,} requests ({percentage:.1f}%)"
            )

    st.markdown("#### Backend distribution")

    adaptive_distribution_df = pd.DataFrame(
        [
            {"Backend": server, "Requests": count}
            for server, count in adaptive["distribution"].items()
        ]
    )

    st.bar_chart(
        adaptive_distribution_df.set_index("Backend")
    )

    st.metric("Errors", adaptive["errors"])

    st.caption(
        "This is a separate, larger experiment (1,800 requests, "
        "20 workers). Its latency results should not be treated as "
        "a directly controlled comparison with the standalone "
        "60-request benchmarks."
    )

else:
    st.info("No adaptive benchmark results available.")


# Adaptive switching history
st.divider()
st.subheader("7. Adaptive Switching History")

st.write(
    "Live controller history showing how routing strategies "
    "change in response to workload conditions."
)

try:
    with urlopen(
        "http://load-balancer:8000/adaptive/history",
        timeout=5,
    ) as response:
        history_data = json.loads(response.read().decode("utf-8"))

    history = history_data.get("history", [])
    total_switches = history_data.get("total_switches", 0)

    if history:
        st.metric("Recorded algorithm switches", total_switches)

        history_rows = []

        for event in reversed(history):
            stats = event.get("statistics", {})

            history_rows.append({
                "Time (UTC)": pd.to_datetime(
                    event["timestamp"], unit="s", utc=True
                ).strftime("%Y-%m-%d %H:%M:%S"),
                "Transition": (
                    f'{event["from"].replace("_", " ").title()} → '
                    f'{event["to"].replace("_", " ").title()}'
                ),
                "Workload": event.get("workload", "unknown").title(),
                "Request rate (req/s)": stats.get("request_rate", 0),
                "Average latency (ms)": stats.get(
                    "average_latency_ms", 0
                ),
                "Max CPU (%)": stats.get("max_cpu_percent", 0),
                "Max active requests": stats.get(
                    "max_active_requests", 0
                ),
                "Reason": event.get("reason", ""),
            })

        history_df = pd.DataFrame(history_rows)

        st.markdown("#### Algorithm transition timeline")

        transition_counts = (
            history_df["Transition"].value_counts().to_frame("Switches")
        )

        st.bar_chart(transition_counts)

        st.markdown("#### Detailed switching history")

        st.dataframe(
            history_df,
            use_container_width=True,
            hide_index=True,
        )

    else:
        st.info("No adaptive switching events recorded yet.")

except Exception as exc:
    st.warning(f"Could not retrieve adaptive history: {exc}")

# Environment details
st.divider()
st.subheader("8. Benchmark environment")

environment = benchmark_data.get("environment", {})

delays = environment.get("backend_delays_ms", {})

if delays:
    delay_columns = st.columns(len(delays))

    for column, (server, delay) in zip(delay_columns, delays.items()):
        column.metric(server, f"{delay} ms")

st.info(environment.get("description", "No environment description available."))

st.warning(
    "These are controlled benchmark results using simulated backend delays. "
    "They demonstrate performance under this specific workload, not a "
    "guarantee that Q-learning will outperform every algorithm in all conditions."
)
