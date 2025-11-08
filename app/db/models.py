"""SQLite schema and CRUD helpers."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional

from . import db

INIT_SCRIPT = """
CREATE TABLE IF NOT EXISTS app_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT NOT NULL UNIQUE,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS historical_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    interval TEXT NOT NULL,
    range TEXT NOT NULL,
    adjusted INTEGER DEFAULT 1,
    as_of_date DATE,
    data TEXT NOT NULL,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, interval, range, adjusted)
);

CREATE TABLE IF NOT EXISTS indicator_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    indicator TEXT NOT NULL,
    params TEXT NOT NULL,
    interval TEXT NOT NULL,
    data TEXT NOT NULL,
    as_of_date DATE,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, indicator, interval, params)
);

CREATE TABLE IF NOT EXISTS recent_quotes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL UNIQUE,
    data TEXT NOT NULL,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def initialize_schema() -> None:
    """Create database tables if they do not exist."""
    db.execute_script(INIT_SCRIPT)


def upsert_config(key: str, value_json: str) -> None:
    sql = """
        INSERT INTO app_config (key, value, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at
    """
    db.execute(sql, (key, value_json, datetime.utcnow()))


def fetch_all_configs() -> dict[str, str]:
    rows = db.query("SELECT key, value FROM app_config")
    return {row["key"]: row["value"] for row in rows}


def delete_historical_data() -> None:
    db.execute("DELETE FROM historical_data")


def delete_recent_quotes() -> None:
    db.execute("DELETE FROM recent_quotes")


def delete_indicator_data() -> None:
    db.execute("DELETE FROM indicator_data")


def get_recent_quote(symbol: str) -> Optional[dict[str, Any]]:
    rows = db.query(
        "SELECT data, fetched_at FROM recent_quotes WHERE symbol = ?",
        (symbol,),
    )
    if not rows:
        return None
    row = rows[0]
    payload = json.loads(row["data"])
    payload["fetched_at"] = row["fetched_at"]
    return payload


def upsert_recent_quote(symbol: str, data: dict[str, Any]) -> None:
    sql = """
        INSERT INTO recent_quotes (symbol, data, fetched_at)
        VALUES (?, ?, ?)
        ON CONFLICT(symbol) DO UPDATE SET data=excluded.data, fetched_at=excluded.fetched_at
    """
    db.execute(sql, (symbol, json.dumps(data), datetime.utcnow()))


def get_historical_entry(symbol: str, interval: str, range_key: str, adjusted: bool) -> Optional[dict[str, Any]]:
    rows = db.query(
        """
        SELECT data, as_of_date, fetched_at
        FROM historical_data
        WHERE symbol = ? AND interval = ? AND range = ? AND adjusted = ?
        """,
        (symbol, interval, range_key, int(adjusted)),
    )
    if not rows:
        return None
    row = rows[0]
    payload = json.loads(row["data"])
    payload["as_of_date"] = row["as_of_date"]
    payload["fetched_at"] = row["fetched_at"]
    return payload


def upsert_historical_entry(
    symbol: str,
    interval: str,
    range_key: str,
    adjusted: bool,
    as_of_date: str,
    data: dict[str, Any],
) -> None:
    sql = """
        INSERT INTO historical_data (symbol, interval, range, adjusted, as_of_date, data, fetched_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(symbol, interval, range, adjusted)
        DO UPDATE SET as_of_date=excluded.as_of_date, data=excluded.data, fetched_at=excluded.fetched_at
    """
    db.execute(
        sql,
        (
            symbol,
            interval,
            range_key,
            int(adjusted),
            as_of_date,
            json.dumps(data),
            datetime.utcnow(),
        ),
    )


def get_indicator_entry(
    symbol: str,
    indicator: str,
    interval: str,
    params: dict[str, Any],
) -> Optional[dict[str, Any]]:
    params_json = json.dumps(params, sort_keys=True)
    rows = db.query(
        """
        SELECT data, as_of_date, fetched_at
        FROM indicator_data
        WHERE symbol = ? AND indicator = ? AND interval = ? AND params = ?
        """,
        (symbol, indicator, interval, params_json),
    )
    if not rows:
        return None
    row = rows[0]
    payload = json.loads(row["data"])
    payload["as_of_date"] = row["as_of_date"]
    payload["fetched_at"] = row["fetched_at"]
    return payload


def upsert_indicator_entry(
    symbol: str,
    indicator: str,
    interval: str,
    params: dict[str, Any],
    as_of_date: str,
    data: dict[str, Any],
) -> None:
    sql = """
        INSERT INTO indicator_data (symbol, indicator, params, interval, as_of_date, data, fetched_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(symbol, indicator, interval, params)
        DO UPDATE SET as_of_date=excluded.as_of_date, data=excluded.data, fetched_at=excluded.fetched_at
    """
    db.execute(
        sql,
        (
            symbol,
            indicator,
            json.dumps(params, sort_keys=True),
            interval,
            as_of_date,
            json.dumps(data),
            datetime.utcnow(),
        ),
    )

