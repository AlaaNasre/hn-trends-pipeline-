"""Polite, retrying client for the official Hacker News API."""
from __future__ import annotations
import logging
import time
from typing import Any
import requests

BASE = "https://hacker-news.firebaseio.com/v0"
logger = logging.getLogger(__name__)

def get(path: str, *, session: Any = requests, attempts: int = 3,
        timeout: float = 10.0, backoff: float = 1.0) -> Any | None:
    if attempts < 1:
        raise ValueError("attempts must be at least 1")
    url = f"{BASE}/{path.lstrip('/').removesuffix('.json')}.json"
    for attempt in range(attempts):
        try:
            response = session.get(url, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            logger.warning("Request failed (%d/%d) for %s: %s", attempt+1, attempts, path, exc)
            if attempt < attempts - 1:
                time.sleep(backoff * (2 ** attempt))
    return None

def top_stories(n: int = 30, *, delay: float = 0.1, session: Any = requests,
                attempts: int = 3, timeout: float = 10.0) -> list[dict[str, Any]]:
    if n < 0:
        raise ValueError("n must be non-negative")
    ids = get("topstories", session=session, attempts=attempts, timeout=timeout)
    if not isinstance(ids, list):
        logger.error("Could not retrieve top story IDs")
        return []
    stories = []
    for story_id in ids[:n]:
        item = get(f"item/{story_id}", session=session, attempts=attempts, timeout=timeout)
        if isinstance(item, dict):
            stories.append(item)
        if delay > 0:
            time.sleep(delay)
    return stories
