import threading
import json
import os
import random
from pathlib import Path

class QLearningAgent:
    """Tabular Q-learning agent for a small discrete server-selection problem.

    State: one load bucket (0=low, 1=medium, 2=high) per backend.
    Action: backend index.
    """
    def __init__(self, table_path="data/q_table.json", alpha=0.15,
                 gamma=0.90, epsilon=0.25, epsilon_min=0.03,
                 epsilon_decay=0.995):
        self.table_path = Path(table_path)
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_min = epsilon_min
        self.epsilon_decay = epsilon_decay
        self.q = {}
        self.updates = 0
        self.lock = threading.RLock()
        self._load()

    @staticmethod
    def state_from_metrics(metrics):
        buckets = []
        for m in metrics:
            # Combine CPU, active requests and recent latency into a rough
            # load score. These thresholds are initial experimental choices.
            cpu = float(m.get("cpu_percent", 0)) / 100.0
            active = min(float(m.get("active_requests", 0)) / 10.0, 1.0)
            latency = min(float(m.get("average_latency_ms", 0)) / 500.0, 1.0)
            score = max(cpu, active, latency)
            bucket = 0 if score < 0.35 else (1 if score < 0.70 else 2)
            buckets.append(str(bucket))
        return "".join(buckets) or "000"

    def _row(self, state, n_actions):
        if state not in self.q:
            self.q[state] = [0.0] * n_actions
        elif len(self.q[state]) < n_actions:
            self.q[state].extend([0.0] * (n_actions - len(self.q[state])))
        return self.q[state]


    def choose_action(self, state, healthy_indices, n_actions):
        with self.lock:
            if not healthy_indices:
                return None

            row = self._row(state, n_actions)

            if random.random() < self.epsilon:
                return random.choice(healthy_indices)

            # Random tie-breaking avoids always favouring server A at startup.
            best = max(row[i] for i in healthy_indices)
            candidates = [
                i for i in healthy_indices if row[i] == best
            ]
            return random.choice(candidates)



    def update(self, state, action, reward, next_state, next_healthy, n_actions):
        with self.lock:
            row = self._row(state, n_actions)
            next_row = self._row(next_state, n_actions)

            future = max(
                (next_row[i] for i in next_healthy),
                default=0.0,
            )

            old = row[action]
            row[action] = old + self.alpha * (
                reward + self.gamma * future - old
            )

            self.updates += 1
            self.epsilon = max(
                self.epsilon_min,
                self.epsilon * self.epsilon_decay,
            )

            if self.updates % 10 == 0:
                self.save()

    def export_state(self):
        with self.lock:
            return {
                "q_table": {
                    state: list(values)
                    for state, values in self.q.items()
                },
                "epsilon": self.epsilon,
                "updates": self.updates,
            }

    def restore_state(self, data):
        if not isinstance(data, dict):
            raise ValueError("Invalid Q-learning snapshot")

        q_table = data.get("q_table", {})
        if not isinstance(q_table, dict):
            raise ValueError("Invalid Q-table")

        with self.lock:
            self.q = {
                str(state): [float(value) for value in values]
                for state, values in q_table.items()
            }
            self.epsilon = float(data.get("epsilon", self.epsilon))
            self.updates = int(data.get("updates", 0))

    def save(self):
        with self.lock:
            self.table_path.parent.mkdir(parents=True, exist_ok=True)

            tmp = self.table_path.with_suffix(".tmp")

            tmp.write_text(json.dumps({
                "q_table": self.q,
                "epsilon": self.epsilon,
                "updates": self.updates
            }, indent=2))

            tmp.replace(self.table_path)

    def _load(self):
        if not self.table_path.exists():
            return
        try:
            data = json.loads(self.table_path.read_text())
            self.q = data.get("q_table", {})
            self.epsilon = float(data.get("epsilon", self.epsilon))
            self.updates = int(data.get("updates", 0))
        except (ValueError, OSError, TypeError):
            self.q = {}
