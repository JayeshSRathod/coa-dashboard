from __future__ import annotations

import sqlite3

from dashboard.statistics_view import build_statistics_cards, build_statistics_tables
from src.api.statistics import StatisticsApiV1
from src.persistence.statistics_repository import StatisticsRepository
from src.statistics.engine import StatisticsEngine
from src.statistics.service import StatisticsService


def _rows():
    return [
        {
            "outcome": "WIN",
            "realized_pnl": 1000.0,
            "realized_r_multiple": 2.0,
            "mfe": 1500.0,
            "mae": -200.0,
            "holding_seconds": 1800.0,
            "instrument": "NIFTY",
            "scenario": "S7",
            "planning_horizon": "INTRADAY",
            "selected_plan": "A",
        },
        {
            "outcome": "LOSS",
            "realized_pnl": -500.0,
            "realized_r_multiple": -1.0,
            "mfe": 200.0,
            "mae": -700.0,
            "holding_seconds": 900.0,
            "instrument": "NIFTY",
            "scenario": "S7",
            "planning_horizon": "INTRADAY",
            "selected_plan": "B",
        },
        {
            "outcome": "BREAKEVEN",
            "realized_pnl": 0.0,
            "realized_r_multiple": 0.0,
            "mfe": 300.0,
            "mae": -100.0,
            "holding_seconds": 600.0,
            "instrument": "BANKNIFTY",
            "scenario": "S3",
            "planning_horizon": "NEXT_SESSION",
            "selected_plan": "B",
        },
        {
            "outcome": "CANCELLED",
            "realized_pnl": 0.0,
            "instrument": "NIFTY",
            "scenario": "S7",
            "planning_horizon": "NEXT_SESSION",
            "selected_plan": "C",
        },
    ]


def test_statistics_engine_calculates_core_metrics():
    report = StatisticsEngine().calculate(_rows())
    assert report.sample_size == 4
    assert report.wins == 1
    assert report.losses == 1
    assert report.breakeven == 1
    assert report.cancelled == 1
    assert report.win_rate == 33.333333
    assert report.total_realized_pnl == 500.0
    assert report.profit_factor == 2.0
    assert report.expectancy_r == 0.33333333
    assert report.max_drawdown == 500.0
    assert report.by_instrument["NIFTY"]["sample_size"] == 3


def test_statistics_engine_handles_empty_evidence():
    report = StatisticsEngine().calculate([])
    assert report.sample_size == 0
    assert report.win_rate == 0.0
    assert report.profit_factor is None
    assert report.expectancy_r is None


def test_service_persists_snapshot_and_api_reads_it():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    repository = StatisticsRepository(connection)
    service = StatisticsService(repository)
    snapshot = service.calculate(_rows())
    assert repository.get(snapshot.statistics_id)["evidence_count"] == 4
    api = StatisticsApiV1(service)
    response = api.latest()
    assert response["status"] == 200
    assert response["data"]["report"]["wins"] == 1


def test_dashboard_models_are_stable():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    service = StatisticsService(StatisticsRepository(connection))
    snapshot = service.calculate(_rows()).as_dict()
    cards = build_statistics_cards(snapshot)
    tables = build_statistics_tables(snapshot)
    assert cards["sample_size"] == 4
    assert cards["profit_factor"] == 2.0
    assert any(row["instrument"] == "NIFTY" for row in tables["instrument"])
