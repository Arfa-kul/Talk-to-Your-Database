"""Database utilities: connection management and query execution."""
from __future__ import annotations

import re
import threading
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import create_engine, text

from backend.core.config import settings
from backend.core.sql_validator import SQLValidationError, validate_sql


class QueryTimeoutError(RuntimeError):
    """Raised when the DB query exceeds the configured timeout."""


class DatabaseService:
    """Thread-safe database service with read-only enforcement."""

    def __init__(self) -> None:
        db_url = settings.db_url
        connect_args: dict[str, Any] = {}

        if settings.db_type == "sqlite":
            connect_args["check_same_thread"] = False

        self._engine = create_engine(
            db_url,
            connect_args=connect_args,
            pool_pre_ping=True,
        )

    # ──────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────

    def run_query(self, sql: str) -> pd.DataFrame:
        """
        Validate *sql*, execute it with a row-limit and timeout, and
        return the result as a DataFrame.
        """
        safe_sql = validate_sql(sql)
        limited_sql = self._apply_row_limit(safe_sql)
        return self._execute_with_timeout(limited_sql)

    def get_schema_ddl(self) -> str:
        """Return the full DDL for every table in the database."""
        with self._engine.connect() as conn:
            if settings.db_type == "sqlite":
                rows = conn.execute(
                    text(
                        "SELECT sql FROM sqlite_master "
                        "WHERE type='table' AND sql IS NOT NULL "
                        "ORDER BY name"
                    )
                ).fetchall()
                return "\n\n".join(r[0] for r in rows)
            else:
                # Postgres: use information_schema
                rows = conn.execute(
                    text(
                        "SELECT table_name FROM information_schema.tables "
                        "WHERE table_schema = 'public'"
                    )
                ).fetchall()
                ddls: list[str] = []
                for (table_name,) in rows:
                    cols = conn.execute(
                        text(
                            "SELECT column_name, data_type, character_maximum_length, "
                            "is_nullable FROM information_schema.columns "
                            "WHERE table_schema='public' AND table_name=:t ORDER BY ordinal_position"
                        ),
                        {"t": table_name},
                    ).fetchall()
                    col_defs = ", ".join(
                        f"{c[0]} {c[1]}" + (f"({c[2]})" if c[2] else "")
                        for c in cols
                    )
                    ddls.append(f"CREATE TABLE {table_name} ({col_defs});")
                return "\n\n".join(ddls)

    # ──────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────

    @staticmethod
    def _apply_row_limit(sql: str) -> str:
        """Append LIMIT clause if not already present."""
        limit = settings.max_rows
        if re.search(r"\bLIMIT\b", sql, re.IGNORECASE):
            return sql
        return f"{sql} LIMIT {limit}"

    def _execute_with_timeout(self, sql: str) -> pd.DataFrame:
        """Execute *sql* and raise QueryTimeoutError if it takes too long."""
        timeout = settings.query_timeout_seconds
        result: list[pd.DataFrame] = []
        error: list[Exception] = []

        def _run() -> None:
            try:
                with self._engine.connect() as conn:
                    df = pd.read_sql_query(text(sql), conn)
                    result.append(df)
            except Exception as exc:  # noqa: BLE001
                error.append(exc)

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        t.join(timeout)

        if t.is_alive():
            raise QueryTimeoutError(
                f"Query exceeded {timeout}s timeout."
            )
        if error:
            raise error[0]
        return result[0]


# Singleton
db_service = DatabaseService()
