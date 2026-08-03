"""Policy controls for CQRP shadow PAPER execution.

The policy layer is intentionally independent of brokers. It evaluates session
windows, concurrency, daily-loss, duplicate-execution, and feature-flag gates
before the ShadowExecutionService may persist a simulated trade.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from types import MappingProxyType
from typing import Any, Mapping
from zoneinfo import ZoneInfo


IST = ZoneInfo("Asia/Kolkata")


@dataclass(frozen=True)
class ExecutionPolicyConfig:
    shadow_research_enabled: bool = True
    paper_execution_enabled: bool = True
    assisted_execution_enabled: bool = False
    live_order_enabled: bool = False
    auto_trading_enabled: bool = False
    max_open_trades: int = 5
    max_open_trades_per_instrument: int = 1
    max_daily_realized_loss: float = 10000.0
    intraday_start: time = time(9, 15)
    intraday_last_entry: time = time(15, 15)
    next_session_start: time = time(9, 0)
    next_session_last_entry: time = time(10, 0)

    def __post_init__(self) -> None:
        if self.max_open_trades < 1:
            raise ValueError("max_open_trades must be positive")
        if self.max_open_trades_per_instrument < 1:
            raise ValueError("max_open_trades_per_instrument must be positive")
        if self.max_daily_realized_loss < 0:
            raise ValueError("max_daily_realized_loss cannot be negative")
        if self.assisted_execution_enabled or self.live_order_enabled or self.auto_trading_enabled:
            raise ValueError("Sprint-205 must remain SHADOW/PAPER-only")


@dataclass(frozen=True)
class ExecutionPolicyContext:
    observed_at: datetime
    planning_horizon: str
    instrument: str
    open_trade_count: int
    open_instrument_trade_count: int
    daily_realized_pnl: float
    duplicate_trade_exists: bool
    data_quality: str = "PASS"
    risk_status: str = "PASS"
    metadata: Mapping[str, Any] = MappingProxyType({})

    def __post_init__(self) -> None:
        horizon = str(self.planning_horizon).upper()
        if horizon not in {"NEXT_SESSION", "INTRADAY"}:
            raise ValueError("unsupported planning_horizon")
        object.__setattr__(self, "planning_horizon", horizon)
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))


@dataclass(frozen=True)
class ExecutionPolicyDecision:
    allowed: bool
    action: str
    reasons: tuple[str, ...]
    evidence: Mapping[str, Any]

    @classmethod
    def build(cls, *, allowed: bool, reasons: list[str], evidence: Mapping[str, Any]) -> "ExecutionPolicyDecision":
        return cls(
            allowed=allowed,
            action="ALLOW_PAPER_EXECUTION" if allowed else "BLOCK_PAPER_EXECUTION",
            reasons=tuple(reasons or ["All shadow execution policy gates passed."]),
            evidence=MappingProxyType(dict(evidence)),
        )


class ExecutionPolicyEngine:
    version = "execution-policy-v1"

    def __init__(self, config: ExecutionPolicyConfig | None = None) -> None:
        self.config = config or ExecutionPolicyConfig()

    def evaluate(self, context: ExecutionPolicyContext) -> ExecutionPolicyDecision:
        reasons: list[str] = []
        local = context.observed_at.astimezone(IST).time().replace(tzinfo=None)

        if not self.config.shadow_research_enabled:
            reasons.append("Shadow research is disabled.")
        if not self.config.paper_execution_enabled:
            reasons.append("Paper execution is disabled.")
        if context.duplicate_trade_exists:
            reasons.append("A paper trade already exists for this execution key.")
        if context.open_trade_count >= self.config.max_open_trades:
            reasons.append("Maximum concurrent paper trades reached.")
        if context.open_instrument_trade_count >= self.config.max_open_trades_per_instrument:
            reasons.append("Maximum concurrent paper trades for instrument reached.")
        if context.daily_realized_pnl <= -abs(self.config.max_daily_realized_loss):
            reasons.append("Daily simulated loss limit reached.")
        if str(context.data_quality).upper() not in {"PASS", "HEALTHY"}:
            reasons.append("Execution data quality gate failed.")
        if str(context.risk_status).upper() not in {"PASS", "APPROVED", "REDUCED_SIZE"}:
            reasons.append("Execution risk gate failed.")

        if context.planning_horizon == "INTRADAY":
            if not self.config.intraday_start <= local <= self.config.intraday_last_entry:
                reasons.append("Outside intraday paper-entry window.")
        else:
            if not self.config.next_session_start <= local <= self.config.next_session_last_entry:
                reasons.append("Outside next-session paper-entry window.")

        return ExecutionPolicyDecision.build(
            allowed=not reasons,
            reasons=reasons,
            evidence={
                "planning_horizon": context.planning_horizon,
                "instrument": context.instrument,
                "observed_at": context.observed_at.isoformat(),
                "open_trade_count": context.open_trade_count,
                "open_instrument_trade_count": context.open_instrument_trade_count,
                "daily_realized_pnl": round(float(context.daily_realized_pnl), 6),
                "duplicate_trade_exists": context.duplicate_trade_exists,
                "execution_policy_version": self.version,
                "paper_only": True,
            },
        )
