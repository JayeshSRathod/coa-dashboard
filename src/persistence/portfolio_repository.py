"""Append-only persistence boundary for CQRP portfolio identities."""

from __future__ import annotations

import sqlite3

from src.risk.models import Portfolio

from .repository import SQLiteRepository


def _decode(row: sqlite3.Row) -> Portfolio:
    return Portfolio(
        portfolio_id=row["portfolio_id"],
        name=row["name"],
        owner=row["owner"],
        initial_capital=float(row["initial_capital"]),
        created_at=row["created_at"],
        created_by=row["created_by"],
    )


class PortfolioRepository(SQLiteRepository):
    """Persist portfolio identities; capital changes are represented by events."""

    def insert(self, portfolio: Portfolio) -> Portfolio:
        existing = self.get(portfolio.portfolio_id)
        if existing is not None:
            return existing
        try:
            with self.connection:
                self.connection.execute(
                    "INSERT INTO portfolios (portfolio_id, name, owner, initial_capital, created_at, created_by) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (portfolio.portfolio_id, portfolio.name, portfolio.owner, portfolio.initial_capital,
                     portfolio.created_at, portfolio.created_by),
                )
        except sqlite3.IntegrityError:
            existing = self.get(portfolio.portfolio_id)
            if existing is not None:
                return existing
            raise
        return portfolio

    def get(self, portfolio_id: str) -> Portfolio | None:
        row = self.connection.execute(
            "SELECT * FROM portfolios WHERE portfolio_id = ?", (portfolio_id,)
        ).fetchone()
        return _decode(row) if row else None

    def list_all(self) -> list[Portfolio]:
        rows = self.connection.execute(
            "SELECT * FROM portfolios ORDER BY created_at ASC, portfolio_id ASC"
        ).fetchall()
        return [_decode(row) for row in rows]
