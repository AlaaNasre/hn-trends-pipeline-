"""SQLite-first persistence, run metadata, schema versioning, and query helpers."""
from __future__ import annotations
import datetime as dt
import logging
import sqlite3
from pathlib import Path
from typing import Any, Iterable
from src.config import DATABASE_URL, SQLITE_PATH, ensure_parent

logger = logging.getLogger(__name__)
SCHEMA_VERSION = 2
SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS collection_runs (
 run_id INTEGER PRIMARY KEY AUTOINCREMENT,
 started_at TEXT NOT NULL,
 finished_at TEXT,
 status TEXT NOT NULL,
 fetched_count INTEGER NOT NULL DEFAULT 0,
 saved_count INTEGER NOT NULL DEFAULT 0,
 dropped_count INTEGER NOT NULL DEFAULT 0,
 duration_seconds REAL NOT NULL DEFAULT 0,
 error TEXT
);
CREATE TABLE IF NOT EXISTS snapshots (
 fetched_at TEXT NOT NULL,
 id INTEGER NOT NULL,
 title TEXT NOT NULL,
 score INTEGER NOT NULL,
 comments INTEGER NOT NULL DEFAULT 0,
 url TEXT,
 by TEXT,
 descendants INTEGER NOT NULL DEFAULT 0,
 PRIMARY KEY (fetched_at, id)
);
CREATE INDEX IF NOT EXISTS idx_snapshots_fetched_at ON snapshots(fetched_at);
CREATE INDEX IF NOT EXISTS idx_snapshots_story_id ON snapshots(id);
"""

def _connect_sqlite(db: str | Path) -> sqlite3.Connection:
    ensure_parent(str(db))
    con = sqlite3.connect(str(db), timeout=20)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA journal_mode = WAL")
    con.executescript(SCHEMA)
    # Inspect actual columns even when migrating a starter database that did not
    # have a schema_version row/table before this version.
    cols = {r["name"] for r in con.execute("PRAGMA table_info(snapshots)")}
    if "by" not in cols:
        con.execute('ALTER TABLE snapshots ADD COLUMN "by" TEXT')
    if "descendants" not in cols:
        con.execute("ALTER TABLE snapshots ADD COLUMN descendants INTEGER NOT NULL DEFAULT 0")
    row = con.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
    if row is None:
        con.execute("INSERT INTO schema_version(version) VALUES (?)", (SCHEMA_VERSION,))
    else:
        con.execute("UPDATE schema_version SET version=?", (SCHEMA_VERSION,))
    con.commit()
    return con

def connect(db: str | Path | None = None):
    """Open configured database. SQLite is default; PostgreSQL is optional via DATABASE_URL."""
    url = DATABASE_URL if db is None else ""
    if url.startswith(("postgres://", "postgresql://")):
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:
            raise RuntimeError("PostgreSQL support requires `pip install -r requirements-postgres.txt`") from exc
        pg = psycopg.connect(url, row_factory=dict_row)
        with pg.cursor() as cur:
            cur.execute("""CREATE TABLE IF NOT EXISTS collection_runs (
                run_id BIGSERIAL PRIMARY KEY, started_at TEXT NOT NULL, finished_at TEXT,
                status TEXT NOT NULL, fetched_count INTEGER NOT NULL DEFAULT 0,
                saved_count INTEGER NOT NULL DEFAULT 0, dropped_count INTEGER NOT NULL DEFAULT 0,
                duration_seconds DOUBLE PRECISION NOT NULL DEFAULT 0, error TEXT)""")
            cur.execute("""CREATE TABLE IF NOT EXISTS snapshots (
                fetched_at TEXT NOT NULL, id BIGINT NOT NULL, title TEXT NOT NULL,
                score INTEGER NOT NULL, comments INTEGER NOT NULL DEFAULT 0, url TEXT,
                by TEXT, descendants INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (fetched_at, id))""")
            cur.execute("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)")
            cur.execute("SELECT version FROM schema_version LIMIT 1")
            if cur.fetchone() is None:
                cur.execute("INSERT INTO schema_version(version) VALUES (%s)", (SCHEMA_VERSION,))
        pg.commit()
        return pg
    return _connect_sqlite(db or SQLITE_PATH)

def is_postgres(con) -> bool:
    return con.__class__.__module__.startswith("psycopg")

def clean_stories(stories: Iterable[dict[str, Any]]) -> tuple[list[tuple], int]:
    rows, dropped = [], 0
    for s in stories:
        title, story_id = s.get("title"), s.get("id")
        if not isinstance(title, str) or not title.strip() or story_id is None:
            dropped += 1
            continue
        try:
            sid, score = int(story_id), int(s.get("score") or 0)
            comments = int(s.get("descendants") or 0)
        except (TypeError, ValueError, OverflowError):
            dropped += 1
            continue
        url = s.get("url") if isinstance(s.get("url"), str) else None
        author = s.get("by") if isinstance(s.get("by"), str) else None
        rows.append((sid, title.strip(), score, comments, url, author, comments))
    return rows, dropped

def save(stories: Iterable[dict[str, Any]], db: str | Path | None = None,
         fetched_at: str | None = None) -> int:
    rows, dropped = clean_stories(stories)
    if dropped:
        logger.warning("Dropped %d invalid story record(s)", dropped)
    now = fetched_at or dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    con = connect(db)
    try:
        if is_postgres(con):
            with con.cursor() as cur:
                cur.executemany("""INSERT INTO snapshots
                    (fetched_at,id,title,score,comments,url,"by",descendants)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (fetched_at,id) DO UPDATE SET title=EXCLUDED.title,
                    score=EXCLUDED.score, comments=EXCLUDED.comments, url=EXCLUDED.url,
                    "by"=EXCLUDED."by", descendants=EXCLUDED.descendants""",
                    [(now,*r) for r in rows])
            con.commit()
        else:
            with con:
                con.executemany("""INSERT OR REPLACE INTO snapshots
                    (fetched_at,id,title,score,comments,url,"by",descendants)
                    VALUES (?,?,?,?,?,?,?,?)""", [(now,*r) for r in rows])
    finally:
        con.close()
    logger.info("Saved %d snapshot row(s); dropped %d", len(rows), dropped)
    return len(rows)

def start_run(db: str | Path | None = None) -> tuple[int, str]:
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    con = connect(db)
    try:
        if is_postgres(con):
            with con.cursor() as cur:
                cur.execute("INSERT INTO collection_runs(started_at,status) VALUES (%s,%s) RETURNING run_id", (now,"running"))
                run_id = cur.fetchone()["run_id"]
            con.commit()
        else:
            with con:
                cur = con.execute("INSERT INTO collection_runs(started_at,status) VALUES (?,?)", (now,"running"))
                run_id = cur.lastrowid
        return int(run_id), now
    finally:
        con.close()

def finish_run(run_id: int, *, status: str, fetched: int, saved: int, dropped: int,
               duration: float, error: str | None = None, db: str | Path | None = None) -> None:
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    con = connect(db)
    try:
        params = (now,status,fetched,saved,dropped,duration,error,run_id)
        if is_postgres(con):
            with con.cursor() as cur:
                cur.execute("""UPDATE collection_runs SET finished_at=%s,status=%s,
                    fetched_count=%s,saved_count=%s,dropped_count=%s,duration_seconds=%s,error=%s
                    WHERE run_id=%s""", params)
            con.commit()
        else:
            with con:
                con.execute("""UPDATE collection_runs SET finished_at=?,status=?,fetched_count=?,
                    saved_count=?,dropped_count=?,duration_seconds=?,error=? WHERE run_id=?""", params)
    finally:
        con.close()

def read_query(query: str, params: tuple = (), db: str | Path | None = None):
    con = connect(db)
    try:
        if is_postgres(con):
            with con.cursor() as cur:
                cur.execute(query.replace("?", "%s"), params)
                return cur.fetchall()
        return [dict(r) for r in con.execute(query, params).fetchall()]
    finally:
        con.close()

def get_snapshots(db: str | Path | None = None):
    return read_query('SELECT * FROM snapshots ORDER BY fetched_at', db=db)

def get_runs(db: str | Path | None = None, limit: int = 100):
    return read_query('SELECT * FROM collection_runs ORDER BY run_id DESC LIMIT ?', (limit,), db=db)
