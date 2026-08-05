"""Deterministic operational reports derived from the local PAPER worker."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Callable
from zoneinfo import ZoneInfo

from src.application.fyers_worker import UniverseCycle
from src.notifications.telegram import DeliveryResult, TelegramNotificationClient


IST = ZoneInfo("Asia/Kolkata")


class ResearchReportDispatcher:
    """Translate persisted-worker outcomes into concise opt-in Telegram reports.

    It is intentionally process-local: restart-safe research remains in CQRP's
    repositories while this component only prevents duplicate chat noise inside
    a running worker session.
    """

    def __init__(self, notifier: TelegramNotificationClient, *, heartbeat_minutes: int = 30,
                 now: Callable[[], datetime] | None = None) -> None:
        self.notifier = notifier
        self.heartbeat_minutes = heartbeat_minutes
        self.now = now or (lambda: datetime.now(timezone.utc))
        self.snapshot_counts: Counter[str] = Counter()
        self.valid_count = 0
        self.failed_count = 0
        self.last_snapshot_at: str | None = None
        self._started = False
        self._closed = False
        self._last_heartbeat: datetime | None = None
        self._reported_errors: set[tuple[str, str]] = set()
        self._reported_plans: set[str] = set()
        self._reported_trades: set[str] = set()

    def observe_cycle(self, cycle: UniverseCycle) -> list[DeliveryResult]:
        """Observe an already completed PAPER capture cycle; never changes it."""
        results: list[DeliveryResult] = []
        now = self.now()
        if not self._started:
            self._started = True
            self._closed = False
            self._last_heartbeat = now
            results.append(self.notifier.send(
                "system_health",
                "CQRP market-session monitoring started\nMode: PAPER ONLY\nFYERS data capture is active; no broker order endpoint is used.",
            ))
        for item in cycle.cycles:
            instrument = item.instrument_id or "UNKNOWN"
            if item.error:
                self.failed_count += 1
                key = (instrument, item.error)
                if key not in self._reported_errors:
                    self._reported_errors.add(key)
                    results.append(self.notifier.send(
                        "system_health",
                        f"CQRP capture warning\nInstrument: {instrument}\nStatus: {item.error}\nMode: PAPER ONLY",
                    ))
                continue
            outcome = item.outcome
            if outcome is None or not outcome.snapshot_id:
                self.failed_count += 1
                continue
            self.snapshot_counts[instrument] += 1
            self.valid_count += 1
            self.last_snapshot_at = item.captured_at
            if outcome.trade_plan_id and outcome.trade_plan_id not in self._reported_plans:
                self._reported_plans.add(outcome.trade_plan_id)
                results.append(self.notifier.send(
                    "preclose_plan",
                    f"CQRP pre-close plan recorded\nInstrument: {instrument}\nPlan ID: {outcome.trade_plan_id}\nStatus: conditional; revalidation at market open is compulsory.\nMode: PAPER ONLY",
                ))
            if outcome.paper_trade_id and outcome.paper_trade_id not in self._reported_trades:
                self._reported_trades.add(outcome.paper_trade_id)
                results.append(self.notifier.send(
                    "paper_portfolio",
                    f"CQRP paper-trade lifecycle event\nInstrument: {instrument}\nPaper trade ID: {outcome.paper_trade_id}\nThis is a simulation only, not a broker order.",
                ))
        if self._last_heartbeat is None or now - self._last_heartbeat >= timedelta(minutes=self.heartbeat_minutes):
            self._last_heartbeat = now
            results.append(self.notifier.send("system_health", self._heartbeat_message()))
        return results

    def close_session(self) -> DeliveryResult | None:
        """Send one daily capture digest after the local market session ends."""
        if not self._started or self._closed:
            return None
        self._closed = True
        return self.notifier.send("daily_research", self._daily_close_message())

    def _heartbeat_message(self) -> str:
        return "\n".join((
            "CQRP 30-minute health heartbeat",
            "Mode: PAPER ONLY | Source: FYERS",
            f"Last snapshot: {self._ist(self.last_snapshot_at)}",
            f"Snapshots: {self._counts()}",
            f"Capture results: valid {self.valid_count} | failed {self.failed_count}",
            "Database: snapshot persistence confirmed for successful captures",
            "Evidence: 18-scenario shadow evidence is building",
        ))

    def _daily_close_message(self) -> str:
        return "\n".join((
            "CQRP daily close digest",
            "Mode: PAPER ONLY | Source: FYERS",
            f"Snapshots captured: {self._counts()}",
            f"Successful captures: {self.valid_count} | capture failures: {self.failed_count}",
            f"Pre-close plans recorded: {len(self._reported_plans)}",
            f"Paper-trade events recorded: {len(self._reported_trades)}",
            "Review unresolved capture warnings and research evidence before changing any rule.",
        ))

    def _counts(self) -> str:
        return " | ".join(f"{name} {self.snapshot_counts[name]}" for name in ("NIFTY", "BANKNIFTY", "FINNIFTY"))

    @staticmethod
    def _ist(timestamp: str | None) -> str:
        if not timestamp:
            return "unavailable"
        try:
            return datetime.fromisoformat(timestamp).astimezone(IST).strftime("%H:%M:%S IST")
        except ValueError:
            return timestamp
