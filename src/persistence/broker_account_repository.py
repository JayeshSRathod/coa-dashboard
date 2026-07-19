"""Append-only broker-account and portfolio mapping repository."""

from __future__ import annotations

import json

from src.multimarket.models import BrokerAccount

from .repository import SQLiteRepository


def _decode(row):
    return BrokerAccount.new(
        account_id=row["account_id"], broker_name=row["broker_name"], client_id=row["client_id"],
        display_name=row["display_name"], default_portfolio_id=row["default_portfolio_id"],
        status=row["status"], permissions=json.loads(row["permissions_json"]),
        execution_enabled=bool(row["execution_enabled"]), last_sync_at=row["last_sync_at"],
        created_at=row["created_at"], created_by=row["created_by"],
    )


class BrokerAccountRepository(SQLiteRepository):
    def insert(self, account: BrokerAccount) -> BrokerAccount:
        existing = self.get_by_client(account.broker_name, account.client_id)
        if existing:
            return existing
        with self.connection:
            self.connection.execute(
                "INSERT INTO broker_accounts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (account.account_id, account.broker_name, account.client_id, account.display_name,
                 account.default_portfolio_id, account.status,
                 json.dumps(dict(account.permissions), sort_keys=True), int(account.execution_enabled),
                 account.last_sync_at, account.created_at, account.created_by),
            )
        return account

    def get(self, account_id):
        row = self.connection.execute("SELECT * FROM broker_accounts WHERE account_id=?", (account_id,)).fetchone()
        return _decode(row) if row else None

    def get_by_client(self, broker_name, client_id):
        row = self.connection.execute("SELECT * FROM broker_accounts WHERE broker_name=? AND client_id=?",
                                      (broker_name, client_id)).fetchone()
        return _decode(row) if row else None
