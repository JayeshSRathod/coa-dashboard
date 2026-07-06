"""
Trade Ledger (SQLite)
---------------------
All persistence for the dashboard lives here. Two things are tracked:
  - The single currently OPEN trade (if any)
  - CLOSED trades, which build up the historical record used for the
    "past month" view and the scenario win-rate stat.

Kept deliberately dependency-free (stdlib sqlite3 + pandas) so it can be
unit tested without a running Streamlit app.
"""

import sqlite3
import datetime
import pandas as pd

DB_PATH = "coa_trading_ledger.db"


def init_db(db_path: str = DB_PATH) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS intraday_ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp_in TEXT NOT NULL,
            timestamp_out TEXT,
            ticker TEXT,
            trade_type TEXT,
            strike_traded TEXT,
            scenario TEXT,
            lots INTEGER,
            entry_spot REAL,
            exit_spot REAL,
            sl_spot REAL,
            t1_spot REAL,
            t2_spot REAL,
            exit_reason TEXT,
            net_pnl REAL,
            status TEXT NOT NULL DEFAULT 'OPEN'
        )
    """)
    conn.commit()
    conn.close()


def open_trade(record: dict, db_path: str = DB_PATH) -> int:
    """Inserts a new OPEN trade. Returns the new row id."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO intraday_ledger
            (timestamp_in, ticker, trade_type, strike_traded, scenario,
             lots, entry_spot, sl_spot, t1_spot, t2_spot, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN')
    """, (
        record["timestamp_in"], record["ticker"], record["trade_type"],
        record["strike_traded"], record.get("scenario", ""),
        record["lots"], record["entry_spot"], record["sl_spot"],
        record["t1_spot"], record["t2_spot"],
    ))
    conn.commit()
    trade_id = cur.lastrowid
    conn.close()
    return trade_id


def get_active_trade(db_path: str = DB_PATH) -> dict | None:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM intraday_ledger WHERE status = 'OPEN' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def close_trade(trade_id: int, exit_spot: float, exit_reason: str,
                 net_pnl: float, db_path: str = DB_PATH) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute("""
        UPDATE intraday_ledger
        SET timestamp_out = ?, exit_spot = ?, exit_reason = ?,
            net_pnl = ?, status = 'CLOSED'
        WHERE id = ?
    """, (
        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        exit_spot, exit_reason, net_pnl, trade_id,
    ))
    conn.commit()
    conn.close()


def get_trade_history(days: int = 30, db_path: str = DB_PATH) -> pd.DataFrame:
    """All CLOSED trades in the last N days, most recent first."""
    conn = sqlite3.connect(db_path)
    cutoff = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    df = pd.read_sql_query("""
        SELECT * FROM intraday_ledger
        WHERE status = 'CLOSED' AND timestamp_in >= ?
        ORDER BY id DESC
    """, conn, params=(cutoff,))
    conn.close()
    return df


def get_monthly_summary(days: int = 30, db_path: str = DB_PATH) -> dict:
    """Aggregate stats for the past N days: trade count, net P&L, win rate."""
    df = get_trade_history(days=days, db_path=db_path)
    if df.empty:
        return {"total_trades": 0, "net_pnl": 0.0, "win_rate": 0.0, "wins": 0, "losses": 0}

    wins = int((df["net_pnl"] > 0).sum())
    total = len(df)
    return {
        "total_trades": total,
        "net_pnl": float(df["net_pnl"].sum()),
        "win_rate": round((wins / total) * 100, 1) if total else 0.0,
        "wins": wins,
        "losses": total - wins,
    }


def get_scenario_stats(scenario: str, days: int = 30, db_path: str = DB_PATH) -> dict:
    """Win rate for a specific scenario label, e.g. 'Bearish breakdown building'."""
    df = get_trade_history(days=days, db_path=db_path)
    if df.empty or "scenario" not in df.columns:
        return {"total": 0, "wins": 0, "win_rate": 0.0}

    subset = df[df["scenario"] == scenario]
    total = len(subset)
    wins = int((subset["net_pnl"] > 0).sum())
    return {
        "total": total,
        "wins": wins,
        "win_rate": round((wins / total) * 100, 1) if total else 0.0,
    }
