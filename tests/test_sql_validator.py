"""Unit tests for the SQL safety validator."""
from __future__ import annotations

import pytest

from backend.core.sql_validator import SQLValidationError, validate_sql


# ──────────────────────────────────────────────────────────────────────────────
# Happy-path: valid SELECT statements
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM Track",
        "SELECT COUNT(*) FROM Artist",
        "  select name from genre  ",
        "SELECT t.Name, a.Name FROM Track t JOIN Album a ON a.AlbumId = t.AlbumId",
        "SELECT * FROM Invoice WHERE Total > 10 LIMIT 50",
        "SELECT strftime('%Y', InvoiceDate) AS year, SUM(Total) FROM Invoice GROUP BY year",
    ],
)
def test_valid_select(sql: str) -> None:
    result = validate_sql(sql)
    assert result  # non-empty


def test_trailing_semicolon_stripped() -> None:
    sql = "SELECT * FROM Track;"
    result = validate_sql(sql)
    assert not result.endswith(";")


# ──────────────────────────────────────────────────────────────────────────────
# Blocked: non-SELECT statements
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "sql,reason",
    [
        ("DROP TABLE Track", "DROP"),
        ("DELETE FROM Customer WHERE CustomerId = 1", "DELETE"),
        ("UPDATE Track SET UnitPrice = 0", "UPDATE"),
        ("INSERT INTO Artist VALUES (999, 'Hacker')", "INSERT"),
        ("TRUNCATE TABLE Invoice", "TRUNCATE"),
        ("ALTER TABLE Track ADD COLUMN foo TEXT", "ALTER"),
        ("CREATE TABLE evil (x TEXT)", "CREATE"),
        ("REPLACE INTO Artist VALUES (1, 'X')", "REPLACE"),
        ("EXEC sp_danger", "EXEC"),
        ("ATTACH DATABASE 'evil.db' AS evil", "ATTACH"),
    ],
)
def test_blocked_statements(sql: str, reason: str) -> None:
    with pytest.raises(SQLValidationError):
        validate_sql(sql)


def test_must_start_with_select() -> None:
    with pytest.raises(SQLValidationError, match="Only SELECT"):
        validate_sql("SHOW TABLES")


def test_empty_sql_rejected() -> None:
    with pytest.raises(SQLValidationError, match="Empty"):
        validate_sql("")


def test_whitespace_only_rejected() -> None:
    with pytest.raises(SQLValidationError, match="Empty"):
        validate_sql("   ")


# ──────────────────────────────────────────────────────────────────────────────
# Bypass attempts
# ──────────────────────────────────────────────────────────────────────────────


def test_inline_comment_bypass_blocked() -> None:
    """SELECT followed by comment-hidden DROP should be blocked."""
    with pytest.raises(SQLValidationError):
        validate_sql("SELECT 1; DROP TABLE Track")


def test_select_with_subquery_allowed() -> None:
    sql = "SELECT * FROM (SELECT TrackId FROM Track WHERE Milliseconds > 200000) sub"
    result = validate_sql(sql)
    assert result


def test_case_insensitive_drop() -> None:
    with pytest.raises(SQLValidationError):
        validate_sql("select * from track; drop table track")
