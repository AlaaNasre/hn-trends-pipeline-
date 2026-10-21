"""Pure analytics helpers used by the dashboard and API."""
from __future__ import annotations
import re
from collections import Counter
import pandas as pd

STOP_WORDS = {
    "about","after","again","against","also","among","been","before","being","between",
    "could","does","doing","down","from","have","having","here","into","just","more","most",
    "only","other","over","same","some","such","than","that","their","there","these","they",
    "this","those","through","under","using","very","what","when","where","which","while",
    "with","would","your","you've","https","story","show","hacker","news","about","http"
}

def word_counts(titles, limit: int = 15) -> pd.DataFrame:
    counts = Counter()
    for title in pd.Series(titles).dropna().astype(str):
        for word in re.findall(r"[A-Za-z][A-Za-z'-]*", title.lower()):
            if len(word) > 4 and word not in STOP_WORDS:
                counts[word] += 1
    return pd.DataFrame(counts.most_common(limit), columns=["word","count"])

def rising_stories(snapshots: pd.DataFrame, window_hours: int = 24) -> pd.DataFrame:
    """Estimate score/comment deltas for stories with observations on both sides of a time window."""
    columns = ["id","title","url","score_before","score_now","score_change",
               "comments_before","comments_now","comments_change","observed_hours"]
    if snapshots.empty:
        return pd.DataFrame(columns=columns)
    df = snapshots.copy()
    df["fetched_at"] = pd.to_datetime(df["fetched_at"], utc=True, errors="coerce")
    df = df.dropna(subset=["fetched_at"])
    if df.empty:
        return pd.DataFrame(columns=columns)
    end = df["fetched_at"].max()
    start = end - pd.Timedelta(hours=window_hours)
    earlier = df[df["fetched_at"] <= start].sort_values("fetched_at").groupby("id").tail(1)
    latest = df.sort_values("fetched_at").groupby("id").tail(1)
    merged = latest.merge(earlier[["id","score","comments","fetched_at"]],
                          on="id", how="inner", suffixes=("_now","_before"))
    if merged.empty:
        return pd.DataFrame(columns=columns)
    merged["observed_hours"] = (merged["fetched_at_now"] - merged["fetched_at_before"]).dt.total_seconds()/3600
    merged = merged[merged["observed_hours"] > 0]
    merged["score_change"] = merged["score_now"] - merged["score_before"]
    merged["comments_change"] = merged["comments_now"] - merged["comments_before"]
    return merged.rename(columns={"title":"title","url":"url","score_before":"score_before",
        "score_now":"score_now","comments_before":"comments_before","comments_now":"comments_now"})[columns].sort_values(
        ["score_change","comments_change"], ascending=False).reset_index(drop=True)
