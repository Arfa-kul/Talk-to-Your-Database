"""DB bootstrap: download Chinook SQLite and verify it is accessible."""
from __future__ import annotations

import logging
import urllib.request
from pathlib import Path

from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)

CHINOOK_URL = (
    "https://github.com/lerocha/chinook-database/raw/master/"
    "ChinookDatabase/DataSources/Chinook_Sqlite.sqlite"
)


def download_chinook(dest: Path) -> None:
    """Download the Chinook SQLite database if it doesn't exist."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        logger.info("Chinook DB already exists at %s", dest)
        return
    logger.info("Downloading Chinook DB to %s …", dest)
    urllib.request.urlretrieve(CHINOOK_URL, dest)  # noqa: S310
    logger.info("Download complete (%d bytes)", dest.stat().st_size)


def verify_chinook(db_path: Path) -> bool:
    """Quick smoke-test: count rows in the Track table."""
    url = f"sqlite:///{db_path}"
    engine = create_engine(url)
    try:
        with engine.connect() as conn:
            row = conn.execute(text("SELECT COUNT(*) FROM Track")).fetchone()
            count = row[0] if row else 0
            logger.info("Chinook verification: %d tracks found.", count)
            return count > 0
    except Exception as exc:
        logger.error("Chinook verification failed: %s", exc)
        return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from dotenv import load_dotenv
    load_dotenv()

    from backend.core.config import settings
    dest = Path(settings.sqlite_db_path).resolve()
    download_chinook(dest)
    ok = verify_chinook(dest)
    print("DB ready:", ok)
