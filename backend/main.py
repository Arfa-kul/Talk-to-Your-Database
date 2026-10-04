"""FastAPI application entry point."""
from __future__ import annotations

import logging
import os

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import ask as ask_router
from backend.routers import train as train_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = FastAPI(
    title="Talk-to-Your-Database Agent",
    description="Natural language → SQL via Vanna + Claude + ChromaDB",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ask_router.router)
app.include_router(train_router.router)


@app.get("/health", tags=["health"])
def health_check() -> dict:
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    from backend.core.config import settings

    uvicorn.run(
        "backend.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )
