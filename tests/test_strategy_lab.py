import unittest

from src.persistence.configuration_repository import ConfigurationRepository
from src.persistence.connection import connect
from src.persistence.dataset_repository import DatasetRepository
from src.persistence.experiment_repository import ExperimentRepository
from src.persistence.migration import apply_migrations
from src.persistence.promotion_repository import PromotionRepository
from src.persistence.research_notebook_repository import ResearchNotebookRepository
from src.persistence.schema import RESEARCH_MIGRATIONS
from src.persistence.strategy_repository import StrategyRepository
from src.strategy_lab.service import StrategyLabService


class StrategyLabTests(unittest.TestCase):
    def setUp(self):
        connection = connect(":memory:")
        apply_migrations(connection, RESEARCH_MIGRATIONS)
        self.service = StrategyLabService(
            StrategyRepository(connection), ConfigurationRepository(connection), DatasetRepository(connection),
            ExperimentRepository(connection), PromotionRepository(connection), ResearchNotebookRepository(connection),
        )

    def test_strategy_clone_inherits_configuration(self):
        original = self.service.create_strategy(
            strategy_name="COA", description="baseline", owner="owner", category="OPTIONS",
            asset_class="NSE_OPTIONS", market="NSE", version="1.0", status="PRODUCTION",
        )
        self.service.create_configuration(original.strategy_id, {"validation": {"confidence": 70}})
        clone = self.service.clone_strategy(original.strategy_id, strategy_name="COA Momentum",
                                            version="1.1")
        configs = self.service.configurations.list_for_strategy(clone.strategy_id)
        self.assertEqual(clone.parent_strategy_id, original.strategy_id)
        self.assertEqual(dict(configs[0].values)["validation"]["confidence"], 70)

    def test_dataset_duplicate_and_deterministic_experiment_run(self):
        strategy = self.service.create_strategy(
            strategy_name="COA", description="baseline", owner="owner", category="OPTIONS",
            asset_class="NSE_OPTIONS", market="NSE", version="2.0", status="EXPERIMENTAL",
        )
        config = self.service.create_configuration(strategy.strategy_id, {"risk": {"capital": 500000}})
        dataset = self.service.register_dataset(market="NSE", source="replay", symbols=["NIFTY"],
            from_date="2026-01-01", to_date="2026-01-31", snapshot_count=100)
        duplicate = self.service.register_dataset(market="NSE", source="replay", symbols=["NIFTY"],
            from_date="2026-01-01", to_date="2026-01-31", snapshot_count=100)
        self.assertEqual(dataset.dataset_id, duplicate.dataset_id)
        experiment = self.service.create_experiment(
            strategy_id=strategy.strategy_id, experiment_name="baseline-jan", objective="test",
            hypothesis="positive expectancy", dataset_id=dataset.dataset_id,
            configuration_id=config.configuration_id, market="NSE", symbols=["NIFTY"],
            from_date="2026-01-01", to_date="2026-01-31", execution_mode="REPLAY",
        )
        pipeline = lambda e, d, c: {"minimum_trades": 600, "win_rate": 0.65, "profit_factor": 2.0,
                                     "maximum_drawdown": 8.0, "sharpe_ratio": 1.7}
        first, second = self.service.run_experiment(experiment.experiment_id, pipeline), self.service.run_experiment(experiment.experiment_id, pipeline)
        self.assertEqual(first.run_id, second.run_id)
        self.assertEqual(first.status, "COMPLETED")

    def test_comparison_and_manual_promotion_evaluation(self):
        strategy = self.service.create_strategy(
            strategy_name="COA", description="baseline", owner="owner", category="OPTIONS",
            asset_class="NSE_OPTIONS", market="NSE", version="3.0", status="CANDIDATE",
        )
        config = self.service.create_configuration(strategy.strategy_id, {"x": 1})
        dataset = self.service.register_dataset(market="NSE", source="replay", symbols=["NIFTY"],
            from_date="2026-02-01", to_date="2026-02-02", snapshot_count=5)
        experiment = self.service.create_experiment(strategy_id=strategy.strategy_id, experiment_name="candidate",
            objective="test", hypothesis="test", dataset_id=dataset.dataset_id, configuration_id=config.configuration_id,
            market="NSE", symbols=["NIFTY"], from_date="2026-02-01", to_date="2026-02-02", execution_mode="REPLAY")
        self.service.run_experiment(experiment.experiment_id, lambda *_: {"minimum_trades": 500, "win_rate": .7,
            "profit_factor": 2, "maximum_drawdown": 5, "sharpe_ratio": 2})
        comparison = self.service.compare_experiments([experiment.experiment_id])
        self.assertEqual(comparison[experiment.experiment_id]["profit_factor"], 2)
        promotion_id = self.service.evaluate_promotion(experiment.experiment_id, {
            "minimum_trades": 500, "win_rate": .6, "profit_factor": 1.8,
            "maximum_drawdown": 10, "sharpe_ratio": 1.5,
        })
        self.assertTrue(promotion_id)


if __name__ == "__main__":
    unittest.main()
