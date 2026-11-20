
import tempfile
import unittest
from pathlib import Path

from load_balancer.algorithms.q_learning import QLearningAgent


class TestQLearningAgent(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.table_path = Path(self.temp_dir.name) / "q_table.json"
        self.agent = QLearningAgent(table_path=self.table_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_state_from_metrics(self):
        metrics = [
            {"cpu_percent": 10, "active_requests": 0},
            {"cpu_percent": 50, "active_requests": 5},
            {"cpu_percent": 90, "active_requests": 10},
        ]

        state = self.agent.state_from_metrics(metrics)

        self.assertEqual(state, "012")

    def test_choose_action_only_from_healthy_servers(self):
        self.agent.epsilon = 0

        action = self.agent.choose_action(
            state="000",
            healthy_indices=[1, 2],
            n_actions=3,
        )

        self.assertIn(action, [1, 2])

    def test_no_healthy_server_returns_none(self):
        action = self.agent.choose_action(
            state="000",
            healthy_indices=[],
            n_actions=3,
        )

        self.assertIsNone(action)

    def test_update_increments_training_count(self):
        self.agent.update(
            state="000",
            action=0,
            reward=2.0,
            next_state="001",
            next_healthy=[0, 1, 2],
            n_actions=3,
        )

        self.assertEqual(self.agent.updates, 1)
        self.assertNotEqual(self.agent.q["000"][0], 0.0)

    def test_save_and_reload(self):
        self.agent.update(
            state="000",
            action=1,
            reward=3.0,
            next_state="001",
            next_healthy=[0, 1, 2],
            n_actions=3,
        )

        self.agent.save()

        loaded_agent = QLearningAgent(table_path=self.table_path)

        self.assertEqual(loaded_agent.updates, 1)
        self.assertEqual(loaded_agent.q, self.agent.q)

    def test_export_state(self):
        self.agent.update(
            state="000",
            action=1,
            reward=3.0,
            next_state="001",
            next_healthy=[0, 1, 2],
            n_actions=3,
        )

        snapshot = self.agent.export_state()

        self.assertEqual(snapshot["updates"], 1)
        self.assertEqual(snapshot["epsilon"], self.agent.epsilon)
        self.assertEqual(snapshot["q_table"], self.agent.q)

    def test_restore_state(self):
        snapshot = {
            "q_table": {
                "000": [0.0, 2.5, 1.0],
                "001": [1.5, 0.0, 0.5],
            },
            "epsilon": 0.12,
            "updates": 42,
        }

        self.agent.restore_state(snapshot)

        self.assertEqual(self.agent.q, snapshot["q_table"])
        self.assertEqual(self.agent.epsilon, 0.12)
        self.assertEqual(self.agent.updates, 42)


if __name__ == "__main__":
    unittest.main()
