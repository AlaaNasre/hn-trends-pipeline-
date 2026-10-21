import pandas as pd
from src.analytics import rising_stories, word_counts

def test_rising_story_requires_same_story_and_computes_delta():
    df=pd.DataFrame([
        {"fetched_at":"2026-01-01T00:00:00+00:00","id":1,"title":"Example story","score":10,"comments":2,"url":"https://example.com"},
        {"fetched_at":"2026-01-02T00:00:00+00:00","id":1,"title":"Example story","score":18,"comments":5,"url":"https://example.com"},
        {"fetched_at":"2026-01-02T00:00:00+00:00","id":2,"title":"New story","score":30,"comments":1,"url":None},
    ])
    result=rising_stories(df,24)
    assert len(result)==1
    assert result.iloc[0]["score_change"]==8
    assert result.iloc[0]["comments_change"]==3

def test_word_counts():
    result=word_counts(["Python pipeline pipeline", "Reliable pipeline"])
    assert result.iloc[0]["word"]=="pipeline"
    assert result.iloc[0]["count"]==3
