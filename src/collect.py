"""Collection orchestration with run metadata and operational metrics."""
from __future__ import annotations
import argparse, logging, time
from src.config import HN_STORY_COUNT, HN_REQUEST_DELAY, HN_REQUEST_TIMEOUT, HN_RETRIES
from src.fetch import top_stories
from src.store import clean_stories, finish_run, save, start_run

def collect(count=HN_STORY_COUNT, db=None, delay=HN_REQUEST_DELAY):
    run_id, _ = start_run(db)
    started = time.monotonic()
    stories = []
    try:
        stories = top_stories(count, delay=delay, attempts=HN_RETRIES, timeout=HN_REQUEST_TIMEOUT)
        cleaned, dropped = clean_stories(stories)
        if not stories:
            raise RuntimeError("No stories fetched; check API/network and retry later.")
        saved = save(stories, db)
        finish_run(run_id, status="success", fetched=len(stories), saved=saved,
                   dropped=dropped, duration=time.monotonic()-started, db=db)
        return {"run_id":run_id,"status":"success","fetched":len(stories),"saved":saved,
                "dropped":dropped,"duration_seconds":round(time.monotonic()-started,3)}
    except Exception as exc:
        finish_run(run_id, status="failed", fetched=len(stories), saved=0, dropped=0,
                   duration=time.monotonic()-started, error=str(exc)[:500], db=db)
        raise

def main():
    parser=argparse.ArgumentParser(description="Collect Hacker News top-story snapshots")
    parser.add_argument("--count", type=int, default=HN_STORY_COUNT)
    parser.add_argument("--db", default=None, help="optional SQLite path; defaults to configuration")
    parser.add_argument("--delay", type=float, default=HN_REQUEST_DELAY)
    args=parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    print(collect(args.count,args.db,args.delay))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
