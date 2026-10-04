"""Vanna service: wraps vanna-ai with Anthropic + ChromaDB backend."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import vanna
from vanna.chromadb import ChromaDB_VectorStore
from vanna.anthropic import Anthropic_Chat

from backend.core.config import settings


class VannaAnthropicChroma(ChromaDB_VectorStore, Anthropic_Chat):
    """Concrete Vanna class combining ChromaDB vector store + Anthropic LLM."""

    def __init__(self, config: dict):
        ChromaDB_VectorStore.__init__(self, config=config)
        Anthropic_Chat.__init__(self, config=config)


def _build_vanna() -> VannaAnthropicChroma:
    chroma_path = Path(settings.chroma_path).resolve()
    chroma_path.mkdir(parents=True, exist_ok=True)

    return VannaAnthropicChroma(
        config={
            "api_key": settings.anthropic_api_key,
            "model": settings.vanna_model,
            "path": str(chroma_path),
        }
    )


# Lazy singleton
_vanna_instance: Optional[VannaAnthropicChroma] = None


def get_vanna() -> VannaAnthropicChroma:
    global _vanna_instance
    if _vanna_instance is None:
        _vanna_instance = _build_vanna()
    return _vanna_instance
