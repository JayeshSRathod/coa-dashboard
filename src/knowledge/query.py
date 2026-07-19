"""Pure deterministic query and aggregation functions for research knowledge."""

from __future__ import annotations

from collections import defaultdict
from statistics import fmean


def _numeric_metrics(facts):
    values = defaultdict(list)
    for fact in facts:
        for key, value in fact.metrics.items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                values[key].append(float(value))
    return {key: fmean(items) for key, items in sorted(values.items()) if items}


def summarise(facts):
    return {"observations": len(facts), "metrics": _numeric_metrics(facts)}


class KnowledgeQueryEngine:
    """Searches immutable evidence and ranks subjects through explicit metrics only."""

    def __init__(self, repository, logger=None) -> None:
        self.repository = repository
        self.logger = logger

    def _rank(self, domain, metric="win_rate", reverse=True):
        grouped = defaultdict(list)
        for fact in self.repository.list(domain=domain):
            grouped[fact.subject_key].append(fact)
        ranked = []
        for key, facts in grouped.items():
            aggregate = summarise(facts)
            value = aggregate["metrics"].get(metric, float("-inf") if reverse else float("inf"))
            display_name = (
                facts[0].summary.get("strategy_name") if domain == "STRATEGY" else key
            ) or key
            ranked.append({"subject": display_name, "subject_key": key, "score": value, **aggregate})
        ranked.sort(key=lambda item: item["subject_key"])
        ranked.sort(key=lambda item: item["score"], reverse=reverse)
        return ranked

    def find_best_strategy(self):
        return (self._rank("STRATEGY") or [None])[0]

    def find_best_instrument(self):
        return (self._rank("INSTRUMENT") or [None])[0]

    def find_best_market(self):
        return (self._rank("MARKET") or [None])[0]

    def find_best_scenario(self):
        return (self._rank("SCENARIO") or [None])[0]

    def compare_strategy_versions(self):
        return self._rank("STRATEGY")

    def compare_instruments(self):
        return self._rank("INSTRUMENT")

    def compare_markets(self):
        return self._rank("MARKET")

    def get_research_summary(self):
        domains = ("STRATEGY", "EXPERIMENT", "SCENARIO", "INSTRUMENT", "MARKET", "VALIDATION", "PORTFOLIO")
        return {domain.lower(): summarise(self.repository.list(domain=domain)) for domain in domains}
