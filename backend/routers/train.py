"""FastAPI router: /train endpoint."""
from __future__ import annotations

import logging
import threading
from enum import Enum

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from backend.services.training_data import (
    CHINOOK_DDL,
    CHINOOK_DOCUMENTATION,
    EXAMPLE_QA_PAIRS,
)
from backend.services.vanna_service import get_vanna

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/train", tags=["train"])

# ─── Simple in-memory training state ─────────────────────────────────────────
class TrainingState(str, Enum):
    idle = "idle"
    running = "running"
    done = "done"
    error = "error"

_training_status: dict = {"state": TrainingState.idle, "message": "", "items": 0}
_training_lock = threading.Lock()


class TrainRequest(BaseModel):
    ddl: str | None = None
    documentation: str | None = None
    question: str | None = None
    sql: str | None = None


class TrainResponse(BaseModel):
    message: str
    items_trained: int = 0


class TrainStatusResponse(BaseModel):
    state: str
    message: str
    items_trained: int


def _run_full_training_bg() -> None:
    """Background thread: load the full Chinook corpus into Vanna."""
    global _training_status
    with _training_lock:
        _training_status = {"state": TrainingState.running, "message": "Training in progress…", "items": 0}

    count = 0
    try:
        vn = get_vanna()

        logger.info("Training: DDL")
        vn.train(ddl=CHINOOK_DDL)
        count += 1

        logger.info("Training: documentation")
        vn.train(documentation=CHINOOK_DOCUMENTATION)
        count += 1

        for i, (question, sql) in enumerate(EXAMPLE_QA_PAIRS, 1):
            logger.info("Training Q/SQL pair %d/%d", i, len(EXAMPLE_QA_PAIRS))
            vn.train(question=question, sql=sql)
            count += 1

        with _training_lock:
            _training_status = {
                "state": TrainingState.done,
                "message": f"Training complete. {count} items loaded.",
                "items": count,
            }
        logger.info("Training complete: %d items.", count)

    except Exception as exc:
        logger.exception("Training failed")
        with _training_lock:
            _training_status = {
                "state": TrainingState.error,
                "message": f"Training failed: {exc}",
                "items": count,
            }


@router.post("/full", status_code=202)
def train_full(background_tasks: BackgroundTasks) -> dict:
    """
    Kick off full Chinook training in the background.
    Returns 202 immediately — poll GET /train/status to check progress.
    """
    with _training_lock:
        if _training_status["state"] == TrainingState.running:
            raise HTTPException(status_code=409, detail="Training already in progress.")

    background_tasks.add_task(_run_full_training_bg)
    return {"message": "Training started in background. Poll GET /train/status for progress."}


@router.get("/status", response_model=TrainStatusResponse)
def train_status() -> TrainStatusResponse:
    """Check the current training job state."""
    with _training_lock:
        s = _training_status.copy()
    return TrainStatusResponse(
        state=s["state"],
        message=s["message"],
        items_trained=s["items"],
    )


@router.post("", response_model=TrainResponse)
def train_single(req: TrainRequest) -> TrainResponse:
    """Add a single DDL statement, documentation string, or Q/SQL pair to Vanna."""
    if not any([req.ddl, req.documentation, req.question]):
        raise HTTPException(status_code=400, detail="Provide ddl, documentation, or question+sql.")

    vn = get_vanna()
    count = 0

    try:
        if req.ddl:
            vn.train(ddl=req.ddl)
            count += 1
        if req.documentation:
            vn.train(documentation=req.documentation)
            count += 1
        if req.question and req.sql:
            vn.train(question=req.question, sql=req.sql)
            count += 1
        elif req.question and not req.sql:
            raise HTTPException(status_code=400, detail="Provide sql along with question.")

        return TrainResponse(message="Training item(s) added.", items_trained=count)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Single-item training failed")
        raise HTTPException(status_code=500, detail=str(exc))
