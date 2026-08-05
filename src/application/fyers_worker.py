"""Local, data-only FYERS polling runtime for CQRP research and PAPER tracking."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timezone
from typing import Callable
from zoneinfo import ZoneInfo

from src.application.fyers_research import FyersResearchOutcome, FyersResearchService
from src.market_data.contracts import OptionChainRequest
from src.market_data.fyers_session import FyersDataSessionFactory


@dataclass(frozen=True)
class WorkerCycle:
    captured_at: str
    outcome: FyersResearchOutcome | None
    error: str | None = None
    instrument_id: str | None = None


@dataclass(frozen=True)
class UniverseCycle:
    captured_at: str
    cycles: tuple[WorkerCycle, ...]

    @property
    def failures(self) -> int:
        return sum(cycle.error is not None for cycle in self.cycles)


class FyersPollingWorker:
    """Runs one explicit, read-only FYERS capture cycle at a caller-owned interval."""

    def __init__(self, session_factory: FyersDataSessionFactory, research: FyersResearchService,
                 request: OptionChainRequest, market_open: Callable[[], bool] | None = None) -> None:
        self.session_factory, self.research, self.request = session_factory, research, request
        self.market_open = market_open or market_is_open

    def run_once(self) -> WorkerCycle:
        if not self.market_open():
            return WorkerCycle(_now(), None, "market is closed; capture skipped", self.request.instrument_id)
        status = self.session_factory.status()
        if not status.ready:
            return WorkerCycle(_now(), None, status.reason, self.request.instrument_id)
        try:
            snapshot = self.session_factory.provider().fetch_option_chain(self.request)
            return WorkerCycle(snapshot.captured_at, self.research.process(snapshot), instrument_id=self.request.instrument_id)
        except Exception as exc:
            return WorkerCycle(_now(), None, f"FYERS capture failed: {type(exc).__name__}", self.request.instrument_id)


class FyersUniversePollingWorker:
    """Sequential, rate-conscious multi-index wrapper; it never submits orders."""

    def __init__(self, session_factory, research, requests, market_open: Callable[[], bool] | None = None) -> None:
        self.workers = tuple(FyersPollingWorker(session_factory, research, request, market_open) for request in requests)

    def run_once(self) -> UniverseCycle:
        cycles = tuple(worker.run_once() for worker in self.workers)
        repository = getattr(self.workers[0].research, "snapshots", None) if self.workers else None
        if repository is not None:
            repository.record_event("FYERS_UNIVERSE_CYCLE", "ERROR" if any(item.error for item in cycles) else "INFO", {"instruments": len(cycles), "failures": sum(item.error is not None for item in cycles)})
        return UniverseCycle(_now(), cycles)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def market_is_open(now: datetime | None = None) -> bool:
    """Return whether a regular NSE weekday session is open in India."""
    india = (now or datetime.now(timezone.utc)).astimezone(ZoneInfo("Asia/Kolkata"))
    return india.weekday() < 5 and time(9, 15) <= india.time() < time(15, 30)
