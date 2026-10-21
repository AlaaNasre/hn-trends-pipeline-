"""Streamlit dashboard for Hacker News history and pipeline health."""
from __future__ import annotations
import os
from datetime import date, timedelta
import pandas as pd
import plotly.express as px
import streamlit as st
from src.analytics import rising_stories, word_counts
from src.store import get_runs, get_snapshots

st.set_page_config(page_title="HN Trends", page_icon="📈", layout="wide")
st.title("📈 Hacker News Trends")
st.caption("Snapshot analytics with collection health, story growth, and a read-only FastAPI service.")

@st.cache_data(ttl=30)
def load_snapshots():
    return pd.DataFrame(get_snapshots())

@st.cache_data(ttl=30)
def load_runs():
    return pd.DataFrame(get_runs(limit=100))

try:
    df, runs = load_snapshots(), load_runs()
except Exception as exc:
    st.error(f"Could not load the configured database: {exc}")
    st.stop()

if df.empty:
    st.info("No snapshots yet. Run `python -m src.collect` or trigger the GitHub Actions workflow.")
    st.code("python -m src.collect\nstreamlit run app.py\nuvicorn api:app --reload")
    st.stop()

df["fetched_at"] = pd.to_datetime(df["fetched_at"], utc=True, errors="coerce")
df["score"] = pd.to_numeric(df["score"], errors="coerce").fillna(0)
df["comments"] = pd.to_numeric(df["comments"], errors="coerce").fillna(0)
df = df.dropna(subset=["fetched_at"])
latest_time = df["fetched_at"].max()
latest = df[df["fetched_at"] == latest_time].sort_values("score",ascending=False)
freshness_minutes = max(0,(pd.Timestamp.now(tz="UTC")-latest_time).total_seconds()/60)
status = "Fresh" if freshness_minutes <= 8*60 else "Stale"
c1,c2,c3,c4 = st.columns(4)
c1.metric("Snapshots", f"{df['fetched_at'].nunique():,}")
c2.metric("Latest stories", f"{len(latest):,}")
c3.metric("Average latest score", f"{latest['score'].mean():.1f}" if len(latest) else "—")
c4.metric("Data freshness", f"{freshness_minutes/60:.1f} h", status)

if status == "Stale":
    st.warning("The latest snapshot is older than eight hours. Check GitHub Actions and the configured database.")

st.subheader("Average score over time")
daily = df.assign(day=df["fetched_at"].dt.floor("D")).groupby("day",as_index=False)["score"].mean()
st.plotly_chart(px.line(daily,x="day",y="score",markers=True,
    labels={"day":"UTC day","score":"Average story score"}),width="stretch")

left,right=st.columns(2)
with left:
    st.subheader("Common title words")
    words=word_counts(df["title"])
    if not words.empty: st.bar_chart(words.set_index("word"))
    else: st.caption("No title words available.")
with right:
    st.subheader("Latest snapshot")
    st.dataframe(latest[["score","comments","title","url"]].rename(columns={
        "score":"Score","comments":"Comments","title":"Title","url":"URL"}),
        width="stretch",hide_index=True,
        column_config={"URL":st.column_config.LinkColumn("URL")})

st.subheader("Rising stories")
hours=st.select_slider("Comparison window",options=[6,12,24,48,72,168],value=24,format_func=lambda x:f"{x} hours")
rising=rising_stories(df,hours)
if rising.empty:
    st.info("Not enough history yet. Rising-story analysis requires the same story to be observed both before and after the selected window.")
else:
    st.dataframe(rising.head(25),width="stretch",hide_index=True)
    st.download_button("Download rising stories CSV",rising.to_csv(index=False).encode("utf-8"),
                       file_name="rising-stories.csv",mime="text/csv")

with st.expander("Pipeline health and collection history"):
    if runs.empty:
        st.info("No collection run metadata yet.")
    else:
        st.dataframe(runs,width="stretch",hide_index=True)
        successful=int((runs["status"]=="success").sum())
        failed=int((runs["status"]=="failed").sum())
        a,b,c=st.columns(3)
        a.metric("Successful runs (latest 100)",successful)
        b.metric("Failed runs (latest 100)",failed)
        c.metric("Success rate",f"{100*successful/max(1,successful+failed):.1f}%")
    st.caption("Collection is scheduled every six hours by GitHub Actions. Scheduler delays and API outages can affect freshness.")
with st.expander("Architecture notes"):
    st.markdown("SQLite is the default. Set `DATABASE_URL` to a PostgreSQL URL and install `requirements-postgres.txt` for a remote database. For Streamlit Community Cloud, use durable external storage: its local filesystem is not guaranteed to persist. See the official [Streamlit data connection guidance](https://docs.streamlit.io/develop/concepts/connections/connecting-to-data).")
