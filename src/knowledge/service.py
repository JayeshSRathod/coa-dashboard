"""Dashboard-facing deterministic Research Knowledge Engine APIs."""

from __future__ import annotations


class ResearchKnowledgeService:
    def __init__(self, builder, query_engine, report_generator) -> None:
        self.builder = builder
        self.query = query_engine
        self.reports = report_generator

    def process_completed_experiment(self, experiment, run, strategy=None, dataset=None):
        return self.builder.process_completed_experiment(experiment, run, strategy, dataset)

    def knowledge_search(self, *, domain=None, subject_key=None, market=None):
        return self.builder.repository.list(domain=domain, subject_key=subject_key, market=market)

    def get_research_summary(self):
        return self.query.get_research_summary()

    def best_strategy(self):
        return self.query.find_best_strategy()

    def best_instrument(self):
        return self.query.find_best_instrument()

    def market_analysis(self):
        return self.query.compare_markets()

    def experiment_explorer(self):
        return self.builder.repository.list(domain="EXPERIMENT")
