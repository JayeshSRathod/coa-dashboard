import unittest

from src.research.backtester import BacktestRunner
from src.research.governance import validate_transition
from src.research.metrics import metric_delta, performance_metrics
from src.research.monte_carlo import MonteCarloSimulator
from src.research.optimizer import GridSearchOptimizer
from src.research.walk_forward import WalkForwardValidator


class ResearchStudioTests(unittest.TestCase):
    def test_backtest_orders_snapshots_and_is_repeatable(self):
        snapshots = [
            {"snapshot_id": "b", "market_captured_at": "2026-01-01T09:16:00", "pnl": -2},
            {"snapshot_id": "a", "market_captured_at": "2026-01-01T09:15:00", "pnl": 5},
        ]
        runner = BacktestRunner()
        first = runner.run(snapshots, lambda row: {"pnl": row["pnl"]})
        second = runner.run(reversed(snapshots), lambda row: {"pnl": row["pnl"]})
        self.assertEqual(first.input_fingerprint, second.input_fingerprint)
        self.assertEqual(first.trade_pnls, (5.0, -2.0))
        self.assertEqual(first.metrics["net_profit"], 3.0)

    def test_metrics_optimizer_walk_forward_and_monte_carlo_are_deterministic(self):
        metrics = performance_metrics([4, -2, 3])
        self.assertEqual(metrics["total_trades"], 3)
        self.assertEqual(metric_delta({"net_profit": 5}, {"net_profit": 2})["net_profit"], 3.0)
        optimized = GridSearchOptimizer().optimize({"risk": [1, 2], "target": [1, 3]}, lambda values: values["risk"] + values["target"])
        self.assertEqual(dict(optimized[0].parameters), {"risk": 2, "target": 3})
        observations = tuple({"n": number} for number in range(8))
        result = WalkForwardValidator().evaluate(observations, training_size=3, validation_size=2,
            evaluator=lambda train, validation: sum(item["n"] for item in validation), minimum_score=7)
        self.assertTrue(result.passed)
        first = MonteCarloSimulator().simulate([4, -2, 3], simulations=10, seed=7)
        second = MonteCarloSimulator().simulate([4, -2, 3], simulations=10, seed=7)
        self.assertEqual(first, second)

    def test_production_requires_human_approval(self):
        self.assertEqual(validate_transition("DRAFT", "TESTING"), "TESTING")
        with self.assertRaises(ValueError):
            validate_transition("APPROVED", "PRODUCTION")
        self.assertEqual(validate_transition("APPROVED", "PRODUCTION", approved_by="Jayesh"), "PRODUCTION")


if __name__ == "__main__":
    unittest.main()
