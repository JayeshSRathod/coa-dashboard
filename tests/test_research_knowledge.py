import unittest

from src.knowledge.extractor import KnowledgeBuilder
from src.knowledge.query import KnowledgeQueryEngine
from src.knowledge.reports import ResearchReportGenerator
from src.persistence.configuration_repository import ConfigurationRepository
from src.persistence.connection import connect
from src.persistence.dataset_repository import DatasetRepository
from src.persistence.experiment_repository import ExperimentRepository
from src.persistence.knowledge_repository import KnowledgeRepository, KnowledgeReportRepository
from src.persistence.migration import apply_migrations
from src.persistence.promotion_repository import PromotionRepository
from src.persistence.research_notebook_repository import ResearchNotebookRepository
from src.persistence.schema import RESEARCH_MIGRATIONS
from src.persistence.strategy_repository import StrategyRepository
from src.strategy_lab.service import StrategyLabService


class Logger:
    def info(self, _event):
        pass


class ResearchKnowledgeTests(unittest.TestCase):
    def setUp(self):
        connection = connect(":memory:")
        apply_migrations(connection, RESEARCH_MIGRATIONS)
        self.knowledge = KnowledgeRepository(connection)
        self.builder = KnowledgeBuilder(self.knowledge, Logger())
        self.query = KnowledgeQueryEngine(self.knowledge)
        self.reports = ResearchReportGenerator(self.query, KnowledgeReportRepository(connection), Logger())
        self.lab = StrategyLabService(
            StrategyRepository(connection), ConfigurationRepository(connection), DatasetRepository(connection),
            ExperimentRepository(connection), PromotionRepository(connection),
            ResearchNotebookRepository(connection), knowledge_builder=self.builder,
        )

    def _run(self, *, name, market, symbols, win_rate, scenario_metrics):
        strategy = self.lab.create_strategy(
            strategy_name=name, description="deterministic", owner="owner", category="OPTIONS",
            asset_class="NSE_OPTIONS", market=market, version="1.0", status="EXPERIMENTAL",
        )
        config = self.lab.create_configuration(strategy.strategy_id, {"confidence": 75})
        dataset = self.lab.register_dataset(market=market, source="replay", symbols=symbols,
            from_date="2026-01-01", to_date="2026-01-31", snapshot_count=10)
        experiment = self.lab.create_experiment(
            strategy_id=strategy.strategy_id, experiment_name=name + "-experiment", objective="measure",
            hypothesis="stable", dataset_id=dataset.dataset_id, configuration_id=config.configuration_id,
            market=market, symbols=symbols, from_date="2026-01-01", to_date="2026-01-31",
            execution_mode="REPLAY",
        )
        run = self.lab.run_experiment(experiment.experiment_id, lambda *_: {
            "win_rate": win_rate, "profit_factor": 1.5, "maximum_drawdown": 5.0,
            "validation_metrics": {"average_confidence": 80.0, "validation_failures": 1},
            "portfolio_metrics": {"average_position_size": 2.0, "capital_usage": 0.25},
            "scenario_metrics": scenario_metrics,
            "instrument_metrics": {symbols[0]: {"win_rate": win_rate, "average_holding": 3.0}},
        })
        return strategy, experiment, run

    def test_completed_experiment_automatically_extracts_deterministic_facts(self):
        _, experiment, run = self._run(
            name="COA Momentum", market="NSE", symbols=["NIFTY"], win_rate=.70,
            scenario_metrics={"Scenario 5": {"win_rate": .75, "average_r": 1.2}},
        )
        first = self.knowledge.list()
        self.builder.process_completed_experiment(experiment, run)
        second = self.knowledge.list()
        self.assertEqual(len(first), len(second))
        self.assertEqual({fact.domain for fact in first},
                         {"STRATEGY", "EXPERIMENT", "MARKET", "PORTFOLIO", "VALIDATION", "INSTRUMENT", "SCENARIO"})

    def test_queries_and_structured_reports_are_deterministic(self):
        self._run(name="COA Momentum", market="NSE", symbols=["NIFTY"], win_rate=.70,
                  scenario_metrics={"Scenario 5": {"win_rate": .75}})
        self._run(name="COA Core", market="BSE", symbols=["SENSEX"], win_rate=.55,
                  scenario_metrics={"Scenario 1": {"win_rate": .50}})
        best = self.query.find_best_strategy()
        self.assertEqual(best["subject"], "COA Momentum")
        self.assertEqual(self.query.find_best_instrument()["subject"], "NIFTY")
        self.assertEqual(self.query.find_best_scenario()["subject"], "Scenario 5")
        first, second = self.reports.generate("WEEKLY"), self.reports.generate("WEEKLY")
        self.assertEqual(first.report_id, second.report_id)
        self.assertIn("research_summary", self.reports.export(first, "JSON"))
        self.assertIn("section,value", self.reports.export(first, "CSV"))

    def test_knowledge_tables_are_append_only(self):
        self._run(name="COA Core", market="NSE", symbols=["NIFTY"], win_rate=.6,
                  scenario_metrics={"Scenario 1": {"win_rate": .6}})
        fact = self.knowledge.list()[0]
        with self.assertRaises(Exception):
            self.knowledge.connection.execute("DELETE FROM knowledge_facts WHERE fact_id=?", (fact.fact_id,))


if __name__ == "__main__":
    unittest.main()
