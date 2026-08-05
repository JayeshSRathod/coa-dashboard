"""Run CQRP's local FYERS data and PAPER-research worker.

The worker fetches market data only. It never submits a FYERS order.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from threading import Event
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.application.fyers_research import FyersResearchService
from src.application.fyers_worker import FyersUniversePollingWorker, market_is_open
from src.common.instruments import configured_index_requests
from src.configuration_console.service import ConfigurationConsoleService
from src.configuration_console.secrets import CompositeSecretStore
from src.market_data.contracts import OptionChainRequest
from src.market_data.fyers_session import FyersDataSessionFactory
from src.notifications import ResearchReportDispatcher, TelegramNotificationClient


def _database_path() -> Path:
    return Path(os.getenv("CQRP_RESEARCH_DATABASE_PATH", Path.home() / ".cqrp" / "research.db"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run CQRP's local FYERS data-only PAPER worker.")
    parser.add_argument("--interval-seconds", type=float, default=60.0,
                        help="FYERS polling interval; defaults to 60 seconds.")
    parser.add_argument("--once", action="store_true", help="Run exactly one capture cycle, then exit.")
    args = parser.parse_args()
    if args.interval_seconds < 1:
        raise ValueError("interval-seconds must be at least 1")

    research = FyersResearchService(_database_path())
    requests = configured_index_requests()
    worker = FyersUniversePollingWorker(FyersDataSessionFactory(CompositeSecretStore()), research, requests)
    configuration = ConfigurationConsoleService()
    notifier = TelegramNotificationClient(configuration)
    dispatcher = ResearchReportDispatcher(
        notifier, heartbeat_minutes=configuration.telegram_delivery_settings()["heartbeat_minutes"]
    )
    stop = Event()
    was_open = False
    print(f"CQRP local FYERS worker started: instruments={','.join(request.instrument_id for request in requests)} | interval={args.interval_seconds:g}s | mode=PAPER_ONLY")
    try:
        while not stop.is_set():
            is_open = market_is_open()
            cycle = worker.run_once()
            for item in cycle.cycles:
                if item.error:
                    print(f"{item.captured_at} | {item.error}")
                else:
                    outcome = item.outcome
                    signal_type = outcome.signal.signal_type if outcome and outcome.signal else "UNAVAILABLE"
                    print(f"{item.captured_at} | snapshot={outcome.snapshot_id if outcome else None} | signal={signal_type} | paper_trade={outcome.paper_trade_id if outcome else None}")
            if is_open:
                dispatcher.observe_cycle(cycle)
            elif was_open:
                dispatcher.close_session()
            was_open = is_open
            if args.once:
                return
            stop.wait(args.interval_seconds)
    except KeyboardInterrupt:
        dispatcher.close_session()
        print("\nCQRP FYERS worker stopped.")


if __name__ == "__main__":
    main()
