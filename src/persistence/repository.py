"""Base repository contract for future CQRP data repositories."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass
class SQLiteRepository:
    connection: sqlite3.Connection
