"""Environment-based configuration."""
import os
from pathlib import Path

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
SQLITE_PATH = os.getenv("HN_DB_PATH", "data/hn.db")
HN_STORY_COUNT = int(os.getenv("HN_STORY_COUNT", "30"))
HN_REQUEST_DELAY = float(os.getenv("HN_REQUEST_DELAY", "0.1"))
HN_REQUEST_TIMEOUT = float(os.getenv("HN_REQUEST_TIMEOUT", "10"))
HN_RETRIES = int(os.getenv("HN_RETRIES", "3"))

def ensure_parent(path: str) -> None:
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
