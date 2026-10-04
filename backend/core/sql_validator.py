"""SQL safety validator – blocks any mutating or dangerous statements."""
from __future__ import annotations

import re

# Statements that are never permitted
_BLOCKED_PATTERNS: list[re.Pattern] = [
    re.compile(r"\b(DROP|DELETE|UPDATE|INSERT|TRUNCATE|ALTER|CREATE|REPLACE|MERGE)\b", re.IGNORECASE),
    re.compile(r"\b(EXEC|EXECUTE|CALL|PRAGMA)\b", re.IGNORECASE),
    re.compile(r"--.*?(DROP|DELETE|UPDATE|INSERT)", re.IGNORECASE),  # inline comment bypass
    re.compile(r";.*?(DROP|DELETE|UPDATE|INSERT)", re.IGNORECASE),    # multi-statement bypass
    re.compile(r"\bATTACH\b", re.IGNORECASE),
    re.compile(r"\bDETACH\b", re.IGNORECASE),
    re.compile(r"\bLOAD_EXTENSION\b", re.IGNORECASE),
]

_SELECT_RE = re.compile(r"^\s*SELECT\b", re.IGNORECASE)


class SQLValidationError(ValueError):
    """Raised when the generated SQL fails safety checks."""


def validate_sql(sql: str) -> str:
    """
    Validate *sql* is a safe read-only SELECT statement.

    Returns the stripped SQL if valid, raises ``SQLValidationError`` otherwise.
    """
    if not sql or not sql.strip():
        raise SQLValidationError("Empty SQL statement.")

    stripped = sql.strip().rstrip(";")

    # Must start with SELECT
    if not _SELECT_RE.match(stripped):
        raise SQLValidationError(
            f"Only SELECT statements are allowed. Got: {stripped[:80]!r}"
        )

    # Block dangerous keywords
    for pattern in _BLOCKED_PATTERNS:
        if pattern.search(stripped):
            raise SQLValidationError(
                f"Disallowed SQL keyword detected (pattern: {pattern.pattern!r})."
            )

    return stripped
