"""
test_daily_ingest.py — Tests for daily ingest importance filtering.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import scripts.daily_ingest as daily_ingest


def _article(title: str, url: str) -> dict:
    return {
        "title": title,
        "url": url,
        "summary": "Summary text",
        "full_text": "",
        "source": "Test Source",
        "tier": 2,
        "published_at": datetime.now(timezone.utc),
        "scores": {},
    }


def test_filter_important_news_drops_non_news(monkeypatch):
    def fake_filter(article):
        if "how to" in article["title"].lower():
            return {"keep": False, "importance": "low", "reason": "tutorial"}
        return {"keep": True, "importance": "high", "reason": "news"}

    monkeypatch.setattr(daily_ingest, "filter_important_for_daily_ingest", fake_filter)

    articles = [
        _article("How to use AI agents at work", "https://example.com/tutorial"),
        _article("Oracle expands AI data center footprint", "https://example.com/news"),
    ]
    embeddings = [[0.1, 0.2], [0.3, 0.4]]

    kept_articles, kept_embeddings, dropped = daily_ingest._filter_important_news(
        articles,
        embeddings,
    )

    assert dropped == 1
    assert [article["url"] for article in kept_articles] == ["https://example.com/news"]
    assert kept_embeddings == [[0.3, 0.4]]


def test_filter_important_news_keeps_article_on_filter_exception(monkeypatch):
    def fake_filter(article):
        raise RuntimeError("codex unavailable")

    monkeypatch.setattr(daily_ingest, "filter_important_for_daily_ingest", fake_filter)

    articles = [_article("Oracle signs major AI partnership", "https://example.com/deal")]
    embeddings = [[0.5, 0.6]]

    kept_articles, kept_embeddings, dropped = daily_ingest._filter_important_news(
        articles,
        embeddings,
    )

    assert dropped == 0
    assert kept_articles == articles
    assert kept_embeddings == embeddings
