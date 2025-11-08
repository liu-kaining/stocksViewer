"""Database connection management for stocksViewer."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Iterable

_DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "stocks_viewer.db"


class Database:
    """Lightweight SQLite helper encapsulating connection handling."""

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = Path(db_path or _DEFAULT_DB_PATH)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager yielding a SQLite connection with row factory applied."""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def execute_script(self, script: str) -> None:
        """Execute a multi-statement SQL script."""
        with self.connect() as conn:
            conn.executescript(script)

    def execute(self, sql: str, params: Iterable[object] | None = None) -> None:
        """Execute a single SQL statement."""
        with self.connect() as conn:
            conn.execute(sql, params or [])

    def query(self, sql: str, params: Iterable[object] | None = None) -> list[sqlite3.Row]:
        """Return result rows for a SELECT statement."""
        with self.connect() as conn:
            cursor = conn.execute(sql, params or [])
            return cursor.fetchall()


db = Database()

