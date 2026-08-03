"""Run CQRP's provider-field availability audit against an existing research DB.

Usage:
    python scripts/audit_market_data.py database/cqrp_research.db NIFTY
    python scripts/audit_market_data.py database/cqrp_research.db NIFTY --latest 100
"""

from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import sys

# Permit direct execution from the repository root without requiring package installation.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.persistence.snapshot_repository import SnapshotRepository
from src.research.market_data_audit import MarketDataAvailabilityAuditor


def main(argv: list[str] | None = None) -> int:
    arguments = argv or sys.argv[1:]
    if not arguments:
        print("Usage: python scripts/audit_market_data.py DATABASE_PATH [INSTRUMENT]")
        return 2

    database_path = Path(arguments[0])
    instrument = arguments[1] if len(arguments) > 1 and not arguments[1].startswith("--") else None
    latest_limit: int | None = None
    if "--latest" in arguments:
        position = arguments.index("--latest")
        try:
            latest_limit = int(arguments[position + 1])
        except (IndexError, ValueError):
            print("--latest requires a positive integer")
            return 2
        if latest_limit < 1:
            print("--latest requires a positive integer")
            return 2
    if not database_path.is_file():
        print(f"Database not found: {database_path}")
        return 2

    # Availability review must never migrate or otherwise alter a research DB.
    connection = sqlite3.connect(f"file:{database_path.resolve().as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        repository = SnapshotRepository(connection)
        snapshots = (
            repository.list_by_instrument(instrument)
            if instrument
            else [
                snapshot
                for name in ("NIFTY", "BANKNIFTY", "FINNIFTY")
                for snapshot in repository.list_by_instrument(name)
            ]
        )
        if latest_limit is not None:
            snapshots = snapshots[-latest_limit:]
        reports = MarketDataAvailabilityAuditor().audit(snapshots)
        payload = {
            "requested_instrument": instrument,
            "latest_snapshot_limit": latest_limit,
            "reports": [report.as_dict() for report in reports],
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
    except sqlite3.OperationalError as error:
        print(f"Cannot audit this database: {error}")
        return 2
    finally:
        connection.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
