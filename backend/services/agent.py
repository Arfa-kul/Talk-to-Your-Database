"""
Agent service: orchestrates Vanna → SQL validation → DB execution,
with up to 2 LLM retries on SQL errors.
"""
from __future__ import annotations

import json
import logging
from typing import Optional

import pandas as pd

from backend.core.config import settings
from backend.core.database import QueryTimeoutError, db_service
from backend.core.sql_validator import SQLValidationError, validate_sql
from backend.services.vanna_service import get_vanna

logger = logging.getLogger(__name__)

MAX_RETRIES = 2


class AgentResult:
    """Container for a single question→answer round."""

    def __init__(
        self,
        question: str,
        sql: str,
        dataframe: Optional[pd.DataFrame] = None,
        error: Optional[str] = None,
        retries: int = 0,
    ) -> None:
        self.question = question
        self.sql = sql
        self.dataframe = dataframe
        self.error = error
        self.retries = retries

    @property
    def success(self) -> bool:
        return self.dataframe is not None and self.error is None

    def to_dict(self) -> dict:
        return {
            "question": self.question,
            "sql": self.sql,
            "success": self.success,
            "retries": self.retries,
            "error": self.error,
            "rows": len(self.dataframe) if self.dataframe is not None else 0,
            "columns": list(self.dataframe.columns) if self.dataframe is not None else [],
            "data": (
                self.dataframe.to_dict(orient="records")
                if self.dataframe is not None
                else []
            ),
        }


def ask(question: str, conversation_history: list[dict] | None = None) -> AgentResult:
    """
    Convert *question* to SQL via Vanna, run it, and return an AgentResult.

    Retries up to MAX_RETRIES times, feeding back the error message to the LLM.
    """
    vn = get_vanna()

    # Build a context-aware prompt when there's conversation history
    full_question = _build_question_with_context(question, conversation_history)

    last_error: str = ""
    sql: str = ""

    for attempt in range(MAX_RETRIES + 1):
        # 1. Generate SQL
        try:
            if attempt == 0:
                sql = vn.generate_sql(full_question)
            else:
                # Feed the error back so the LLM can self-correct
                retry_prompt = (
                    f"The previous SQL caused an error: {last_error}\n"
                    f"Original question: {full_question}\n"
                    f"Previous SQL:\n{sql}\n"
                    "Please generate a corrected SQL query."
                )
                sql = vn.generate_sql(retry_prompt)
        except Exception as exc:
            last_error = str(exc)
            logger.warning("SQL generation failed (attempt %d): %s", attempt + 1, exc)
            continue

        # 2. Safety check
        try:
            validate_sql(sql)
        except SQLValidationError as exc:
            last_error = f"Safety validation failed: {exc}"
            logger.warning("SQL safety check failed: %s", exc)
            continue

        # 3. Execute
        try:
            df = db_service.run_query(sql)
            return AgentResult(
                question=question,
                sql=sql,
                dataframe=df,
                retries=attempt,
            )
        except QueryTimeoutError as exc:
            return AgentResult(question=question, sql=sql, error=str(exc), retries=attempt)
        except Exception as exc:
            last_error = str(exc)
            logger.warning("Query execution failed (attempt %d): %s", attempt + 1, exc)

    return AgentResult(
        question=question,
        sql=sql,
        error=f"Failed after {MAX_RETRIES + 1} attempts. Last error: {last_error}",
        retries=MAX_RETRIES,
    )


def _build_question_with_context(
    question: str, history: list[dict] | None
) -> str:
    """Prepend recent conversation turns so Vanna can resolve pronouns / references."""
    if not history:
        return question

    # Include up to last 3 turns for context
    recent = history[-3:]
    context_lines = ["Previous conversation context:"]
    for turn in recent:
        role = turn.get("role", "unknown")
        content = turn.get("content", "")
        context_lines.append(f"  [{role}]: {content}")
    context_lines.append(f"\nCurrent question: {question}")
    return "\n".join(context_lines)
