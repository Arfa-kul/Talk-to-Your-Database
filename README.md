# 🗄️ Talk-to-Your-Database Agent

A natural-language-to-SQL agent powered by **Vanna** (RAG), **Claude** (LLM), **ChromaDB** (vector store), and **SQLite/Chinook** — with a **Streamlit** chat UI and a **FastAPI** backend.

---

## Architecture

```
User (Streamlit UI)
       │
       ▼
FastAPI Backend ──► Vanna (RAG) ──► Claude API (LLM)
       │                │
       │           ChromaDB (vector store)
       │
       ▼
SQL Safety Validator
       │
       ▼
SQLite / Postgres (read-only)
       │
       ▼
Result DataFrame → Plotly Chart
```

---

## Project Structure

```
proj7/
├── backend/
│   ├── core/
│   │   ├── config.py          # Pydantic-settings (reads .env)
│   │   ├── database.py        # DB service: read-only, timeout, row-limit
│   │   └── sql_validator.py   # SELECT-only safety layer
│   ├── routers/
│   │   ├── ask.py             # POST /ask   POST /ask/feedback
│   │   └── train.py           # POST /train  POST /train/full
│   ├── scripts/
│   │   └── setup_db.py        # Download & verify Chinook SQLite
│   ├── services/
│   │   ├── agent.py           # Orchestration: Vanna → validate → execute (retry ×2)
│   │   ├── chart_generator.py # Auto Plotly chart selector
│   │   ├── training_data.py   # DDL + docs + 25 Q/SQL pairs
│   │   └── vanna_service.py   # Vanna + Anthropic + ChromaDB wiring
│   └── main.py                # FastAPI app entry point
├── frontend/
│   └── app.py                 # Streamlit chat UI
├── tests/
│   ├── conftest.py
│   ├── test_sql_validator.py  # Unit tests for safety validator
│   └── test_sample_questions.py # Integration tests (5 sample Qs)
├── data/                      # Chinook DB + ChromaDB store (git-ignored)
├── .env.example
├── requirements.txt
├── Dockerfile
└── README.md
```

---

## Quick Start

### 1. Clone & set up environment

```bash
git clone <repo>
cd proj7
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

Key variables:

| Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | *(required)* | Your Claude API key |
| `DB_TYPE` | `sqlite` | `sqlite` or `postgres` |
| `SQLITE_DB_PATH` | `./data/chinook.db` | Path to SQLite DB |
| `CHROMA_PATH` | `./data/chroma_store` | ChromaDB persistence path |
| `QUERY_TIMEOUT_SECONDS` | `30` | Per-query execution timeout |
| `MAX_ROWS` | `1000` | Maximum rows returned |

### 3. Download the Chinook database

```bash
python -m backend.scripts.setup_db
```

### 4. Start the FastAPI backend

```bash
python -m uvicorn backend.main:app --reload --port 8000
```

Open: http://localhost:8000/docs

### 5. Train Vanna (first run)

```bash
curl -X POST http://localhost:8000/train/full
```

Or click **"Load Chinook Training Data"** in the Streamlit sidebar.

### 6. Start the Streamlit frontend

```bash
streamlit run frontend/app.py
```

Open: http://localhost:8501

---

## Using a PostgreSQL database

Update `.env`:

```env
DB_TYPE=postgres
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=chinook
POSTGRES_USER=your_user
POSTGRES_PASSWORD=your_password
```

Then restore the Chinook Postgres dump ([download here](https://github.com/lerocha/chinook-database/releases)) and retrain.

---

## API Reference

### `POST /ask`

Convert a natural-language question to SQL and return results.

**Request:**
```json
{
  "question": "Who are the top 5 customers by revenue?",
  "conversation_history": [
    {"role": "user", "content": "Show me all genres"},
    {"role": "assistant", "content": "[Generated SQL: SELECT ...]"}
  ]
}
```

**Response:**
```json
{
  "question": "...",
  "sql": "SELECT ...",
  "success": true,
  "retries": 0,
  "rows": 5,
  "columns": ["customer", "total_spent"],
  "data": [...],
  "chart": { /* Plotly figure dict */ }
}
```

### `POST /ask/feedback`

Submit thumbs-up/down. A thumbs-up adds the Q/SQL pair back to Vanna training.

```json
{
  "question": "Who are the top 5 customers by revenue?",
  "sql": "SELECT ...",
  "is_correct": true
}
```

### `POST /train/full`

Load the complete Chinook corpus (DDL + documentation + 25 Q/SQL pairs) into Vanna.

### `POST /train`

Add a single training item:

```json
{ "ddl": "CREATE TABLE ..." }
{ "documentation": "The Invoice table records purchases..." }
{ "question": "How many tracks?", "sql": "SELECT COUNT(*) FROM Track" }
```

### `GET /health`

Returns `{"status": "ok"}`.

---

## Running Tests

```bash
# Unit tests (no DB or API required)
pytest tests/test_sql_validator.py -v

# Integration tests (requires Chinook DB)
pytest tests/test_sample_questions.py -v

# All tests
pytest -v
```

---

## Safety Features

| Feature | Implementation |
|---|---|
| SELECT-only | `sql_validator.py` — regex allowlist, blocks DROP/DELETE/UPDATE/INSERT/TRUNCATE/ALTER/CREATE/EXEC/ATTACH |
| Read-only connection | SQLite URI mode `?mode=ro` ; Postgres: use a DB user with SELECT-only privileges |
| Row limit | Automatic `LIMIT 1000` appended if not present |
| Query timeout | Thread-based timeout (default 30s) |
| LLM retries | Error message fed back to Claude, up to 2 retries |

---

## Docker

```bash
# Build
docker build -t db-agent .

# Run
docker run -p 8000:8000 -p 8501:8501 \
  -e ANTHROPIC_API_KEY=sk-ant-... \
  db-agent
```

Both services start automatically:
- API: http://localhost:8000
- UI: http://localhost:8501

---

## Swapping the LLM or Vector Store

Vanna's modular design makes swaps easy:

- **Different LLM**: Replace `Anthropic_Chat` with `vanna.openai.OpenAI_Chat`, `vanna.google.GoogleGeminiChat`, etc.
- **Different vector store**: Replace `ChromaDB_VectorStore` with `vanna.qdrant.Qdrant_VectorStore`, `vanna.pinecone.PineconeDB_VectorStore`, etc.
- Just update `vanna_service.py` and the relevant env vars.
