"""Dashboard-facing deterministic analytics service APIs."""

from __future__ import annotations
from hashlib import sha256
import json
from src.research.observability import emit_snapshot_event
from .engine import calculate_portfolio, calculate_position
from .greeks import calculate_greeks
from .options import analyze_option_chain, iv_statistics, max_pain
from .strategy import analyze_strategy
from .stress import stress_test


def _fingerprint(value): return sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


class PortfolioOptionsAnalyticsService:
    def __init__(self, repositories: dict, logger=None):
        self.repositories, self.logger = repositories, logger

    def _store(self, name, subject, payload):
        value=self.repositories[name].append(subject_id=subject, payload=payload, fingerprint=_fingerprint(payload))
        if self.logger: emit_snapshot_event(self.logger, "portfolio_analytics_stored", analysis_type=name, subject_id=subject, analysis_id=value)
        return value, payload

    def calculate_portfolio(self, portfolio_id, positions, prices, greeks_inputs=None):
        return self._store("portfolio", portfolio_id, calculate_portfolio(positions, prices, greeks_inputs))
    def calculate_position(self, position, price, greeks_input=None):
        return self._store("position", position["position_id"], calculate_position(position, price, greeks_input))
    def calculate_greeks(self, option_id, **inputs):
        g=calculate_greeks(**inputs); return self._store("greeks", option_id, g.__dict__)
    def calculate_portfolio_greeks(self, portfolio_id, positions, prices, greeks_inputs):
        return self.calculate_portfolio(portfolio_id, positions, prices, greeks_inputs)
    def analyze_option_chain(self, chain_id, chain, spot):
        return self._store("chain", chain_id, analyze_option_chain(chain, spot) | {"max_pain": max_pain(chain)})
    def calculate_iv_rank(self, symbol, current_iv, history):
        return self._store("iv", symbol, iv_statistics(current_iv, history))
    def calculate_max_pain(self, chain_id, chain):
        return self._store("chain", chain_id, max_pain(chain))
    def stress_test(self, portfolio_id, positions, prices, scenarios, greeks_inputs=None):
        return self._store("stress", portfolio_id, {"scenarios": stress_test(positions, prices, scenarios, greeks_inputs)})
    def analyze_strategy(self, strategy_id, legs, underlying_prices):
        return self._store("strategy", strategy_id, analyze_strategy(legs=legs, underlying_prices=underlying_prices))
