from __future__ import annotations

import sqlite3

from dashboard.evidence_view import build_evidence_cards, build_evidence_workspace
from src.api.evidence import EvidenceApiV1
from src.evidence.engine import EvidenceEngine
from src.execution.lifecycle import PaperTradeLifecycleSummary
from src.persistence.evidence_repository import EvidenceRepository


def _lifecycle(**overrides):
    values = {
        "trade_id": "trade-1",
        "stage": "EXITED",
        "status": "CLOSED",
        "entry_price": 100.0,
        "average_exit_price": 125.0,
        "quantity": 100,
        "quantity_remaining": 0,
        "realized_pnl": 2500.0,
        "unrealized_pnl": 0.0,
        "mfe": 3200.0,
        "mae": -600.0,
        "initial_risk_per_unit": 10.0,
        "realized_r_multiple": 2.5,
        "holding_seconds": 1800.0,
        "exit_reason": "TARGET_2",
        "event_count": 8,
        "milestones": ("CREATED", "ENTERED", "TP1_HIT", "TP2_HIT", "EXITED"),
        "metrics": {
            "target_1_hit": True,
            "target_2_hit": True,
            "trailing_activated": True,
            "lifecycle_version": "paper-lifecycle-v1",
        },
    }
    values.update(overrides)
    return PaperTradeLifecycleSummary(**values)


def _inputs():
    trade = {
        "trade_id": "trade-1",
        "signal_id": "sig-1",
        "snapshot_id": "snap-1",
        "experiment_id": "exp-1",
        "instrument": "NIFTY",
        "direction": "BUY",
        "strategy_version": "strategy-v1",
        "execution_version": "paper-v1",
    }
    plan = {
        "trade_plan_id": "plan-1",
        "instrument": "NIFTY",
        "planning_horizon": "INTRADAY",
        "market_bias": "BULLISH",
        "expected_opening": "FLAT",
        "readiness": "READY",
        "confidence_score": 80.0,
    }
    validation = {
        "validation_id": "validation-1",
        "validation_result": "VALIDATED",
        "opening_classification": "FLAT",
        "risk_status": "PASS",
        "data_quality": "PASS",
        "confidence_after": 88.0,
        "selected_plan": "B",
        "evidence": {"gap_pct": 0.08},
    }
    audit = {"audit_id": "audit-1"}
    signal = {"signal_id": "sig-1", "scenario_number": 7, "scenario": "BULLISH_MOMENTUM"}
    snapshot = {
        "snapshot_id": "snap-1",
        "technical_status": "CONFIRMED",
        "technical_bias": "BULLISH",
        "momentum_state": "STRONG",
        "regime": "TRENDING",
    }
    return trade, plan, validation, audit, signal, snapshot


def test_engine_builds_winning_terminal_evidence():
    trade, plan, validation, audit, signal, snapshot = _inputs()
    record = EvidenceEngine().build(
        trade=trade,
        lifecycle=_lifecycle(),
        plan=plan,
        validation=validation,
        execution_audit=audit,
        signal=signal,
        snapshot=snapshot,
    )
    assert record.outcome == "WIN"
    assert record.realized_r_multiple == 2.5
    assert record.selected_plan == "B"
    assert record.scenario_number == 7
    assert record.feature_vector["target_2_hit"] is True
    assert record.lineage["execution_audit_id"] == "audit-1"


def test_engine_rejects_non_terminal_trade():
    trade, plan, validation, audit, signal, snapshot = _inputs()
    try:
        EvidenceEngine().build(
            trade=trade,
            lifecycle=_lifecycle(stage="ACTIVE", status="OPEN"),
            plan=plan,
            validation=validation,
            execution_audit=audit,
            signal=signal,
            snapshot=snapshot,
        )
    except ValueError as exc:
        assert "terminal" in str(exc).lower()
    else:
        raise AssertionError("expected terminal-state validation failure")


def test_cancelled_trade_produces_cancelled_outcome():
    trade, plan, validation, audit, signal, snapshot = _inputs()
    record = EvidenceEngine().build(
        trade=trade,
        lifecycle=_lifecycle(stage="CANCELLED", status="CANCELLED", realized_pnl=0.0),
        plan=plan,
        validation=validation,
        execution_audit=audit,
        signal=signal,
        snapshot=snapshot,
    )
    assert record.outcome == "CANCELLED"


def test_repository_is_idempotent_and_api_reads_record():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    repository = EvidenceRepository(connection)
    trade, plan, validation, audit, signal, snapshot = _inputs()
    record = EvidenceEngine().build(
        trade=trade,
        lifecycle=_lifecycle(),
        plan=plan,
        validation=validation,
        execution_audit=audit,
        signal=signal,
        snapshot=snapshot,
    )
    first = repository.append(record)
    second = repository.append(record)
    assert first == second
    stored = repository.get_for_trade("trade-1")
    assert stored is not None
    assert stored["outcome"] == "WIN"
    assert stored["feature_vector"]["market_bias"] == "BULLISH"

    api = EvidenceApiV1(repository)
    response = api.for_trade("trade-1")
    assert response["status"] == 200
    assert response["mode"] == "SHADOW_PAPER_ONLY"


def test_workspace_aggregates_outcomes_and_r_multiple():
    records = [
        {"evidence_id": "e1", "trade_id": "t1", "instrument": "NIFTY", "outcome": "WIN", "realized_pnl": 1000.0, "realized_r_multiple": 2.0},
        {"evidence_id": "e2", "trade_id": "t2", "instrument": "NIFTY", "outcome": "LOSS", "realized_pnl": -500.0, "realized_r_multiple": -1.0},
    ]
    workspace = build_evidence_workspace(records)
    assert workspace["cards"]["total_records"] == 2
    assert workspace["cards"]["wins"] == 1
    assert workspace["cards"]["losses"] == 1
    assert workspace["cards"]["total_realized_pnl"] == 500.0
    assert workspace["cards"]["average_r_multiple"] == 0.5

    cards = build_evidence_cards(records[0])
    assert cards["outcome"] == "WIN"
    assert cards["mode"] == "SHADOW_PAPER_ONLY"
