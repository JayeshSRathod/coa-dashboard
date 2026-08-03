"""Application service joining existing CQRP evidence to the trade planner.

This service reads the already-persisted snapshot, COA, validation, signal and
risk decision. It creates one idempotent preliminary PAPER plan per snapshot and
planner version. It has no broker or execution dependency.
"""

from __future__ import annotations

from datetime import datetime, timezone
