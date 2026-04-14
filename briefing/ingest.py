"""
ingest.py — RSS feed ingestion with concurrent fetching.

Fetches all configured RSS sources concurrently using a ThreadPoolExecutor
(feedparser is sync-only), normalizes dates to UTC, strips HTML from
summaries, and returns a flat list of Article dicts filtered to the last
INGEST_WINDOW_HOURS hours.
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

from briefing.config import RSS_SOURCES, INGEST_WINDOW_HOURS

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
    # collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _parse_date(entry: Any) -> datetime | None:
    """
    Try multiple feedparser date fields and return a UTC-aware datetime,
    or None if parsing fails completely.
    """
    # feedparser provides parsed time tuples as `published_parsed` / `updated_parsed`
    for field in ("published_parsed", "updated_parsed", "created_parsed"):
        val = getattr(entry, field, None)
        if val is not None:
            try:
                ts = time.mktime(val)
                return datetime.fromtimestamp(ts, tz=timezone.utc)
            except (OverflowError, ValueError, OSError):
                pass

    # Fallback: raw string fields
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


_BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
}


def _fetch_full_text(url: str) -> tuple[str, str]:
    """Download page with httpx (browser headers) and extract text + og:image.

    Returns (text, image_url) tuple. Text capped at 5000 chars.
    Both default to empty string on failure.
    """
    try:
        import trafilatura
        import httpx as _httpx
        resp = _httpx.get(url, headers=_BROWSER_HEADERS, follow_redirects=True, timeout=15)
        if resp.status_code >= 400:
            return ("", "")
        html = resp.text
        text = trafilatura.extract(html) or ""
        # Extract og:image
        image_url = ""
        try:
            from bs4 import BeautifulSoup as _BS
            soup = _BS(html, "html.parser")
            og = soup.find("meta", property="og:image")
            if og and og.get("content"):
                image_url = og["content"]
        except Exception:
            pass
        return (text[:5000], image_url)
    except Exception as exc:
        logger.warning("Full text extraction failed for %s: %s", url[:60], exc)
        return ("", "")


def _fetch_feed(source: dict, cutoff: datetime) -> list[dict]:
    """
    Fetch a single RSS source and return a list of Article dicts.
    Errors are caught and logged; an empty list is returned on failure.
    """
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
                # If we can't determine the date, use now (generous fallback)
                published_at = datetime.now(tz=timezone.utc)

            # Filter to ingest window
            if published_at < cutoff:
                continue

            # Prefer `summary` → `content` → empty
            raw_summary = (
                getattr(entry, "summary", None)
                or entry.get("summary", "")
                or (entry.content[0].value if getattr(entry, "content", None) else "")
            )
            summary = _strip_html(raw_summary)[:1500]  # cap length

            # Extract image from RSS feed (media_content, media_thumbnail, or enclosure)
            image_url = ""
            if hasattr(entry, "media_content") and entry.media_content:
                image_url = entry.media_content[0].get("url", "")
            elif hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
                image_url = entry.media_thumbnail[0].get("url", "")
            elif hasattr(entry, "enclosures") and entry.enclosures:
                enc = entry.enclosures[0]
                href = enc.get("href", "")
                if href and enc.get("type", "").startswith("image"):
                    image_url = href

            articles.append({
                "id":           _make_article_id(url),
                "title":        title,
                "url":          url,
                "summary":      summary,
                "full_text":    "",
                "image_url":    image_url,
                "published_at": published_at,
                "source":       source["name"],
                "tier":         source["tier"],
                "sections":     list(source["sections"]),
                # These fields are populated later by score.py / process.py / llm.py
                "topics":       [],
                "entities":     [],
                "classified_section": None,
                "confidence":   None,
                "scores":       {},
                "per_audience_summaries": {},
            })

    except Exception as exc:
        logger.warning("Failed to fetch feed %s (%s): %s", source["name"], source["url"], exc)

    return articles


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def ingest_feeds(sources: list[dict] | None = None, window_hours: int = INGEST_WINDOW_HOURS) -> list[dict]:
    """
    Fetch all RSS sources concurrently and return a flat deduplicated list
    of Article dicts published within the last `window_hours` hours.
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

    # Fetch full article text + og:image concurrently using trafilatura
    if all_articles:
        logger.info("Fetching full text for %d articles...", len(all_articles))
        with ThreadPoolExecutor(max_workers=10) as text_pool:
            future_to_article = {
                text_pool.submit(_fetch_full_text, a["url"]): a
                for a in all_articles
            }
            for future in as_completed(future_to_article):
                article = future_to_article[future]
                try:
                    text, og_image = future.result(timeout=10)
                    article["full_text"] = text
                    # Use og:image if RSS didn't provide one
                    if not article.get("image_url") and og_image:
                        article["image_url"] = og_image
                except Exception:
                    article["full_text"] = ""
        fetched = sum(1 for a in all_articles if a.get("full_text"))
        images = sum(1 for a in all_articles if a.get("image_url"))
        logger.info("Full text fetched for %d/%d articles, images for %d", fetched, len(all_articles), images)

    return all_articles
