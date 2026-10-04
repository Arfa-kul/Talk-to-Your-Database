# ─── Stage 1: base ────────────────────────────────────────────────────────────
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ─── Stage 2: dependencies ────────────────────────────────────────────────────
FROM base AS deps

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# ─── Stage 3: runtime ─────────────────────────────────────────────────────────
FROM deps AS runtime

COPY . .

# Create data dir
RUN mkdir -p data

# Download Chinook DB at build time
RUN python -m backend.scripts.setup_db || true

EXPOSE 8000 8501

# Default: run both API + Streamlit via a simple shell script
CMD ["sh", "-c", "\
    python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 & \
    streamlit run frontend/app.py --server.port 8501 --server.address 0.0.0.0 \
"]
