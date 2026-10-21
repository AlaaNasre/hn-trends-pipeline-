import sqlite3
import logging
from src.store import save, clean_stories, start_run, finish_run, get_runs, get_snapshots

def test_save_expected_rows(tmp_path):
    db=tmp_path/"test.db"
    stories=[{"id":1,"title":"First","score":12,"descendants":3,"url":"https://example.com"},
             {"id":2,"title":"Second","score":4}]
    assert save(stories,db,fetched_at="2026-01-01T00:00:00+00:00")==2
    rows=get_snapshots(db)
    assert len(rows)==2 and rows[0]["score"]==12

def test_invalid_title_dropped(tmp_path,caplog):
    db=tmp_path/"test.db"
    with caplog.at_level(logging.WARNING):
        assert save([{"id":1,"title":" "},{"id":2,"score":3},
                     {"id":3,"title":"Valid","score":"8"}],db,
                    fetched_at="2026-01-01T00:00:00+00:00")==1
    assert "Dropped 2" in caplog.text

def test_schema_migrates_starter_database(tmp_path):
    db=tmp_path/"old.db"
    with sqlite3.connect(db) as con:
        con.execute("CREATE TABLE snapshots (fetched_at TEXT, id INTEGER, title TEXT, score INTEGER, comments INTEGER, url TEXT)")
    save([{"id":1,"title":"Migrated"}],db,fetched_at="2026-01-01T00:00:00+00:00")
    assert "by" in [r[1] for r in sqlite3.connect(db).execute("PRAGMA table_info(snapshots)")]

def test_run_metadata(tmp_path):
    db=tmp_path/"runs.db"
    rid,_=start_run(db)
    finish_run(rid,status="success",fetched=3,saved=2,dropped=1,duration=.5,db=db)
    run=get_runs(db)[0]
    assert run["status"]=="success" and run["saved_count"]==2
