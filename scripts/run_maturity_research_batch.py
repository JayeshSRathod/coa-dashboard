"""Replay CQRP observational evidence after market close.

This script has no FYERS requests and no broker capability.  It is safe to run
after the worker is stopped.  It fills missing append-only scenario and dynamic
structure observations from the canonical snapshot store.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.application.fyers_research import FyersResearchService


def main() -> None:
    parser = argparse.ArgumentParser(description="CQRP post-market observational replay")
    parser.add_argument("--database", type=Path,
                        default=Path(os.getenv("CQRP_RESEARCH_DATABASE_PATH", Path.home() / ".cqrp" / "research.db")))
    parser.add_argument("--instruments", nargs="+", default=["NIFTY", "BANKNIFTY", "FINNIFTY"])
    parser.add_argument("--skip-dynamic", action="store_true",
                        help="Do not replay existing dynamic wall/event evidence.")
    args = parser.parse_args()

    service = FyersResearchService(args.database)
    try:
        report = {"mode": "PAPER_RESEARCH_ONLY", "database": str(args.database), "instruments": {}}
        for instrument in args.instruments:
            report["instruments"][instrument] = {
                "scenario_tracks_replayed": service.backfill_scenario_tracks(instrument),
                "dynamic_structure_replayed": 0 if args.skip_dynamic else service.backfill_dynamic_structure(instrument),
                "latest_preclose_plan": service.latest_trade_plan(instrument),
            }
        print(json.dumps(report, default=str, sort_keys=True, indent=2))
    finally:
        service.close()


if __name__ == "__main__":
    main()
