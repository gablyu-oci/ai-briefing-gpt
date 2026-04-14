"""
fetcher.py — RSS feed ingestion with concurrent fetching.

Migrated from briefing/ingest.py with DB integration.
"""

import hashlib
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from typing import Any

import feedparser
from bs4 import BeautifulSoup
from dateutil import parser as dateutil_parser

from config.settings import INGEST_WINDOW_HOURS
from config.sources import RSS_SOURCES
from app.db.models import Article, Source, ProcessingLog, get_session, init_db

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _strip_html(raw: str) -> str:
    """Remove HTML tags and normalise whitespace."""
    if not raw:
        return ""
    soup = BeautifulSoup(raw, "html.parser")
    text = soup.get_text(separator=" ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _parse_date(entry: Any) -> datetime | None:
    """Try multiple feedparser date fields and return a UTC-aware datetime."""
    for field in ("published_parsed", "updated_parsed", "created_parsed"):
        val = getattr(entry, field, None)
        if val is not None:
            try:
                ts = time.mktime(val)
                return datetime.fromtimestamp(ts, tz=timezone.utc)
            except (OverflowError, ValueError, OSError):
                pass

    for field in ("published", "updated", "created"):
        raw = getattr(entry, field, None) or entry.get(field)
        if raw:
            try:
                dt = dateutil_parser.parse(raw)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
            except (ValueError, OverflowError):
                pass
    return None


def _make_article_id(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def _fetch_feed(source: dict, cutoff: datetime) -> list[dict]:
    """Fetch a single RSS source and return a list of article dicts."""
    articles: list[dict] = []
    try:
        feed = feedparser.parse(source["url"])
        if feed.bozo and not feed.entries:
            logger.warning("Feed %s is malformed and has no entries — skipping", source["name"])
            return articles

        for entry in feed.entries:
            url = getattr(entry, "link", None) or entry.get("link", "")
            if not url:
                continue

            title = _strip_html(getattr(entry, "title", "") or entry.get("title", ""))
            if not title:
                continue

            published_at = _parse_date(entry)
            if published_at is None:
                published_at = datetime.now(tz=timezone.utc)

            if published_at < cutoff:
                continue

            raw_summary = (
                getattr(entry, "summary", None)
                or entry.get("summary", "")
                or (entry.content[0].value if getattr(entry, "content", None) else "")
            )
            summary = _strip_html(raw_summary)[:1500]

            articles.append({
                "id": _make_article_id(url),
                "title": title,
                "url": url,
                "summary": summary,
                "published_at": published_at,
                "source": source["name"],
                "source_domain": source.get("domain", ""),
                "tier": source["tier"],
                "sections": list(source.get("sections", [])),
                "topics": [],
                "entities": [],
                "classified_section": None,
                "confidence": None,
                "scores": {},
                "per_audience_summaries": {},
            })

    except Exception as exc:
        logger.warning("Failed to fetch feed %s (%s): %s", source["name"], source["url"], exc)

    return articles


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def ingest_feeds(
    sources: list[dict] | None = None,
    window_hours: int = INGEST_WINDOW_HOURS,
    save_to_db: bool = True,
) -> list[dict]:
    """
    Fetch all RSS sources concurrently and return a flat deduplicated list
    of article dicts published within the last window_hours.
    Optionally persists to the database.
    """
    if sources is None:
        sources = RSS_SOURCES

    cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=window_hours)
    logger.info("Ingesting %d sources (cutoff: %s)", len(sources), cutoff.strftime("%Y-%m-%d %H:%M UTC"))

    all_articles: list[dict] = []
    seen_urls: set[str] = set()

    with ThreadPoolExecutor(max_workers=min(len(sources), 10)) as pool:
        futures = {pool.submit(_fetch_feed, src, cutoff): src for src in sources}
        for future in as_completed(futures):
            src = futures[future]
            try:
                batch = future.result()
                for article in batch:
                    if article["url"] not in seen_urls:
                        seen_urls.add(article["url"])
                        all_articles.append(article)
                logger.info("  [%s] fetched %d articles", src["name"], len(batch))
            except Exception as exc:
                logger.warning("  [%s] unexpected error: %s", src["name"], exc)

    logger.info("Total ingested: %d unique articles", len(all_articles))

    # Persist to DB
    if save_to_db and all_articles:
        _persist_articles(all_articles)

    return all_articles


def _persist_articles(articles: list[dict]) -> None:
    """Save ingested articles to the database."""
    try:
        engine = init_db()
        session = get_session(engine)

        # Build source lookup
        source_map = {}
        for src in session.query(Source).all():
            source_map[src.display_name] = src.id

        saved = 0
        for art in articles:
            existing = session.query(Article).filter_by(url=art["url"]).first()
            if existing:
                continue

            db_article = Article(
                url=art["url"],
                title=art["title"],
                source_id=source_map.get(art["source"]),
                published_at=art["published_at"],
                summary=art.get("summary", ""),
                tier=art["tier"],
                raw_score=0.0,
                ingest_at=datetime.now(timezone.utc),
            )
            session.add(db_article)
            saved += 1

        session.commit()
        logger.info("Persisted %d new articles to DB", saved)

        # Log ingestion in processing_log
        for art in articles:
            db_art = session.query(Article).filter_by(url=art["url"]).first()
            if db_art:
                art["_db_id"] = db_art.id
                log_entry = ProcessingLog(
                    article_id=db_art.id,
                    stage="ingest",
                    input_snapshot={"source": art["source"], "url": art["url"]},
                    output_snapshot={"title": art["title"], "tier": art["tier"]},
                    score_breakdown={},
                )
                session.add(log_entry)

        session.commit()
        session.close()

    except Exception as exc:
        logger.warning("Failed to persist articles to DB: %s", exc)
