# HN Trends Pipeline

A Python pipeline that collects public Hacker News story metadata, stores timestamped snapshots, and presents trends through a Streamlit dashboard and read-only FastAPI endpoints.

## Results

| Measure | Observed result | Context |
|---|---:|---|
| Stories fetched in a collection run | 30 | Actual local run on 21 October 2026 |
| Snapshot rows saved | 30 | Same collection run |
| Rows dropped by validation | 0 | Same collection run |
| Collection duration | 29.672 seconds | Reported by the local collector |
| Unit tests | 8 passed in 0.05 seconds | Test run during package creation |
| Classification accuracy | Not applicable | This is a data-ingestion and analytics pipeline, not a classifier |

These figures describe the observed run and package-build test run; they are not a guarantee of future API response times or ongoing scheduler performance.

## How it works

1. **Fetch:** request the current top-story IDs and story details from the official Hacker News Firebase API, using timeouts and bounded retries.
2. **Validate and clean:** normalize story metadata and reject records that do not meet the required data checks.
3. **Store snapshots:** write story observations with UTC timestamps to SQLite by default; PostgreSQL is an optional configuration.
4. **Track runs:** record collection status, counts, duration, and error details for operational visibility.
5. **Analyze trends:** compare observations across timestamps and calculate score/comment changes only when a story has a usable baseline.
6. **Explore results:** use the Streamlit dashboard for freshness, scores, title words, rising stories, and CSV export; use FastAPI for read-only data endpoints.

## How to run it

Use Python 3.11 or newer. Run these commands from the repository root.

### 1. Create and activate a virtual environment

**Windows PowerShell**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 3. Collect a snapshot

```bash
python -m src.collect
```

The default configuration requests 30 stories. Configuration can be adjusted with environment variables; see `.env.example`.

### 4. Start the dashboard

```bash
python -m streamlit run app.py
```

Open `http://localhost:8501`.

### 5. Start the API in a second terminal

Activate the same virtual environment, then run:

```bash
python -m uvicorn api:app --reload
```

Open `http://127.0.0.1:8000/docs` for interactive API documentation. Available endpoints include `/health`, `/snapshots`, `/runs`, and `/trends/rising?window_hours=24`.

### 6. Run tests

```bash
python -m pytest -q
```

### Optional: Docker

With Docker Desktop or another Docker Engine running:

```bash
docker compose up --build dashboard api
```

To run a collector using the Compose configuration:

```bash
docker compose --profile tools run --rm collector
```

## Limits

- **Historical trends need repeated observations.** A single collection run is enough to display the latest stories, but not enough to calculate meaningful rising-story changes over a lookback window. Collect regularly and build up history first.
- **Changes are raw deltas.** Score and comment differences are not normalized by elapsed time or exposure, so stories sampled at different intervals are not perfectly comparable.
- **The source can change or be unavailable.** API rate limits, network problems, deleted stories, and upstream schema changes can delay or reduce collection.
- **SQLite is intended for a simple portfolio deployment.** A high-write, multi-instance production service would benefit from a managed database, connection pooling, backups, and formal migrations.
- **The API is read-only, not production-hardened.** Add authentication, rate limits, monitoring, and access controls before exposing operational endpoints publicly.
- **Scheduled workflows are not guaranteed to run at the exact scheduled minute.** Verify GitHub Actions runs and use durable external storage if the dashboard must maintain reliable history across deployments.

## What I would improve next

- Build a longer, reproducible history and report trends across several days or weeks.
- Add integration tests for PostgreSQL and API endpoints, alongside the existing unit tests.
- Add structured logs, alerting, and retry/error metrics for collection runs.
- Use a formal migration tool such as Alembic and add database backup/retention policies.
- Add dashboard screenshots and a deployed demo only after capturing and verifying them.
- Add a data-retention policy and normalize trend metrics for the elapsed time between observations.

## Data and credits

- **Source:** [Official Hacker News Firebase API](https://github.com/HackerNews/API), which provides public story metadata through a keyless API.
- **Data type:** story IDs, titles, scores, comment counts, timestamps, author handles, and source URLs returned by the API.
- **Licence:** the API documentation is publicly available, but that does not establish a blanket open-data licence for all story content or linked websites. Story content and linked material remain subject to their respective owners' rights and terms. This project primarily stores metadata and links; check the source terms before redistributing or using data commercially.
- **Code:** this repository does not claim affiliation with or endorsement by Hacker News.
