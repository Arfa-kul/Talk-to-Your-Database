"""
Integration tests: 5 sample natural-language questions against the real
Chinook SQLite DB (no LLM – SQL is pre-written, validated, and executed).
"""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import create_engine, text


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def db_path() -> Path:
    """Return path to Chinook DB; skip if not downloaded yet."""
    from dotenv import load_dotenv
    load_dotenv()
    path = Path(os.getenv("SQLITE_DB_PATH", "./data/chinook.db")).resolve()
    if not path.exists():
        pytest.skip(f"Chinook DB not found at {path}. Run setup_db.py first.")
    return path


@pytest.fixture(scope="session")
def engine(db_path):
    return create_engine(f"sqlite:///{db_path}")


def run_query(engine, sql: str) -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql_query(text(sql), conn)


# ──────────────────────────────────────────────────────────────────────────────
# Sample question tests
# ──────────────────────────────────────────────────────────────────────────────


def test_q1_track_count(engine) -> None:
    """Q: How many tracks are there in total?"""
    df = run_query(engine, "SELECT COUNT(*) AS total_tracks FROM Track")
    assert not df.empty
    total = df["total_tracks"].iloc[0]
    assert total > 3000, f"Expected >3000 tracks, got {total}"


def test_q2_top_customers(engine) -> None:
    """Q: Who are the top 5 customers by total spending?"""
    sql = """
    SELECT c.FirstName || ' ' || c.LastName AS customer,
           SUM(i.Total) AS total_spent
    FROM Customer c
    JOIN Invoice i ON i.CustomerId = c.CustomerId
    GROUP BY c.CustomerId
    ORDER BY total_spent DESC
    LIMIT 5
    """
    df = run_query(engine, sql)
    assert len(df) == 5
    assert "customer" in df.columns
    assert "total_spent" in df.columns
    # Top customer should have spent more than second
    assert df["total_spent"].iloc[0] >= df["total_spent"].iloc[1]


def test_q3_led_zeppelin_albums(engine) -> None:
    """Q: List all albums by Led Zeppelin."""
    sql = """
    SELECT al.Title AS album
    FROM Album al
    JOIN Artist ar ON ar.ArtistId = al.ArtistId
    WHERE ar.Name = 'Led Zeppelin'
    """
    df = run_query(engine, sql)
    assert len(df) >= 1, "Led Zeppelin should have at least 1 album"


def test_q4_top_genres(engine) -> None:
    """Q: What are the top 3 genres by track count?"""
    sql = """
    SELECT g.Name AS genre, COUNT(t.TrackId) AS track_count
    FROM Genre g
    JOIN Track t ON t.GenreId = g.GenreId
    GROUP BY g.GenreId
    ORDER BY track_count DESC
    LIMIT 3
    """
    df = run_query(engine, sql)
    assert len(df) == 3
    assert df["track_count"].iloc[0] >= df["track_count"].iloc[1]


def test_q5_revenue_by_country(engine) -> None:
    """Q: What are the top 5 countries by total revenue?"""
    sql = """
    SELECT c.Country, ROUND(SUM(i.Total), 2) AS total_revenue
    FROM Invoice i
    JOIN Customer c ON c.CustomerId = i.CustomerId
    GROUP BY c.Country
    ORDER BY total_revenue DESC
    LIMIT 5
    """
    df = run_query(engine, sql)
    assert len(df) == 5
    assert "Country" in df.columns
    # USA is a top market in Chinook
    countries = df["Country"].tolist()
    assert "USA" in countries, f"Expected USA in top 5, got {countries}"
