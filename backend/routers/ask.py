"""FastAPI router: /ask and /feedback endpoints."""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.services.agent import ask
from backend.services.chart_generator import auto_chart
from backend.services.vanna_service import get_vanna

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ask", tags=["ask"])


# ──────────────────────────────────────────────────────────────────────────────
# Request / Response schemas
# ──────────────────────────────────────────────────────────────────────────────


class ConversationTurn(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    conversation_history: list[ConversationTurn] = Field(default_factory=list)


class AskResponse(BaseModel):
    question: str
    sql: str
    success: bool
    retries: int
    error: Optional[str] = None
    rows: int
    columns: list[str]
    data: list[dict]
    chart: Optional[dict] = None  # Plotly figure dict


class FeedbackRequest(BaseModel):
    question: str
    sql: str
    is_correct: bool  # True = thumbs up, False = thumbs down


class FeedbackResponse(BaseModel):
    message: str


# ──────────────────────────────────────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────────────────────────────────────


@router.post("", response_model=AskResponse)
def ask_question(req: AskRequest) -> AskResponse:
    """Convert a natural-language question to SQL, execute it, and return results."""
    history = [t.model_dump() for t in req.conversation_history]
    result = ask(req.question, conversation_history=history)

    chart = None
    if result.success and result.dataframe is not None:
        chart = auto_chart(result.dataframe, question=req.question)

    return AskResponse(
        question=result.question,
        sql=result.sql,
        success=result.success,
        retries=result.retries,
        error=result.error,
        rows=result.to_dict()["rows"],
        columns=result.to_dict()["columns"],
        data=result.to_dict()["data"],
        chart=chart,
    )


@router.post("/feedback", response_model=FeedbackResponse)
def submit_feedback(req: FeedbackRequest) -> FeedbackResponse:
    """
    Thumbs-up: add the question/SQL pair back to Vanna's training data.
    Thumbs-down: log for human review (future enhancement).
    """
    if req.is_correct:
        try:
            vn = get_vanna()
            vn.train(question=req.question, sql=req.sql)
            logger.info("Feedback accepted: added Q/SQL pair to training data.")
            return FeedbackResponse(message="Thank you! This pair has been added to training data.")
        except Exception as exc:
            logger.error("Failed to add training pair: %s", exc)
            raise HTTPException(status_code=500, detail=str(exc))
    else:
        logger.info("Negative feedback received for question: %r", req.question)
        return FeedbackResponse(message="Thank you for the feedback. We'll review this.")
