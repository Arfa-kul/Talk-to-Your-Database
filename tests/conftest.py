"""conftest.py – shared pytest fixtures."""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is on the path so `backend.*` imports work in tests
sys.path.insert(0, str(Path(__file__).parent.parent))
