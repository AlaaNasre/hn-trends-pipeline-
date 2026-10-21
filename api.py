"""FastAPI read-only API for collected Hacker News snapshots."""
from fastapi import FastAPI, HTTPException, Query
from src.store import get_runs, get_snapshots
from src.analytics import rising_stories
import pandas as pd

app = FastAPI(title="HN Trends API", version="2.0.0",
              description="Read-only API for Hacker News snapshot analytics.")

@app.get("/health")
def health():
    try:
        runs = get_runs(limit=1)
        return {"status":"ok","latest_run":runs[0] if runs else None}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}")

@app.get("/snapshots")
def snapshots(limit: int = Query(500, ge=1, le=10000)):
    rows = get_snapshots()
    return {"count":min(len(rows),limit),"items":rows[-limit:]}

@app.get("/runs")
def runs(limit: int = Query(50, ge=1, le=500)):
    return {"items":get_runs(limit=limit)}

@app.get("/trends/rising")
def rising(window_hours: int = Query(24, ge=1, le=720), limit: int = Query(20, ge=1, le=100)):
    df = pd.DataFrame(get_snapshots())
    if df.empty:
        return {"window_hours":window_hours,"items":[]}
    result = rising_stories(df,window_hours)
    if result.empty:
        return {"window_hours":window_hours,"items":[],"note":"Need observations on both sides of the selected time window."}
    return {"window_hours":window_hours,"items":result.head(limit).where(pd.notna(result),None).to_dict("records")}
