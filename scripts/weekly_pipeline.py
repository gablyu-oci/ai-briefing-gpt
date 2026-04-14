#!/usr/bin/env python3
"""
weekly_pipeline.py -- Full briefing pipeline reading from the article DB.

Loads articles ingested over the past N days (default 7), deduplicates
across the entire window using stored embeddings, then runs the same
classify -> score -> summarize -> render pipeline as main.py.

Usage:
    python3 scripts/weekly_pipeline.py                     # full run
    python3 scripts/weekly_pipeline.py --dry-run           # skip LLM calls
    python3 scripts/weekly_pipeline.py --audience karan    # single audience
    python3 scripts/weekly_pipeline.py --days 3            # last 3 days only
"""

import argparse
import json
import logging
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np

# Ensure the project root is on sys.path so that package imports work
# when this script is invoked directly (e.g. python3 scripts/weekly_pipeline.py).
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from briefing.config import AUDIENCE_PROFILES, AUDIENCE_ORDER, RSS_SOURCES
from app.dedup.embeddings import compute_embeddings, batch_cosine_similarity
from app.db.models import init_db, get_session, Article as DBArticle

from main import (
    step_prescore,
    step_classify,
    step_relevance_filter,
    step_full_score,
    step_generate_summaries,
    step_executive_summaries,
    step_render,
    _persist_to_db,
    OUTPUT_ROOT,
)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Build a lookup from source_name -> sections using RSS_SOURCES config
# ---------------------------------------------------------------------------
_SOURCE_SECTIONS: dict[str, list[str]] = {
    src["name"]: list(src["sections"]) for src in RSS_SOURCES
}


def _db_row_to_article_dict(row: DBArticle) -> dict:
    """
    Convert a SQLAlchemy Article row back to the article dict format
    that the pipeline expects (same shape as briefing.ingest.ingest_feeds).
    """
    import hashlib

    url = row.url or ""
    source_name = row.source_name or ""
    sections = _SOURCE_SECTIONS.get(source_name, [])

    # Reconstruct the published_at as a UTC-aware datetime
    published_at = row.published_at
    if published_at is not None and published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=timezone.utc)

    return {
        "id": hashlib.sha256(url.encode()).hexdigest()[:16],
        "title": row.title or "",
        "url": url,
        "summary": row.summary or "",
        "full_text": row.full_text or "",
        "image_url": "",
        "published_at": published_at or datetime.now(tz=timezone.utc),
        "source": source_name,
        "tier": row.tier or 2,
        "sections": sections,
        "topics": [],
        "entities": [],
        "classified_section": None,
        "confidence": None,
        "scores": {},
        "per_audience_summaries": {},
        # Carry the stored embedding so we can reuse it in dedup
        "_stored_embedding": row.embedding_json,
    }


# ---------------------------------------------------------------------------
# Embedding dedup across the week
# ---------------------------------------------------------------------------

COSINE_THRESHOLD = 0.80


def _weekly_embedding_dedup(articles: list[dict]) -> list[dict]:
    """
    Deduplicate articles across the entire week using embedding cosine
    similarity.  Reuses embeddings already stored in the DB when available;
    computes new embeddings only for articles that lack them.
    """
    if len(articles) < 2:
        return articles

    # Build the embedding matrix, computing only where needed
    embeddings: list[list[float]] = []
    needs_compute: list[int] = []

    for idx, article in enumerate(articles):
        stored = article.get("_stored_embedding")
        if stored and isinstance(stored, list) and len(stored) > 0:
            embeddings.append(stored)
        else:
            embeddings.append([])  # placeholder
            needs_compute.append(idx)

    # Compute missing embeddings in a single batch
    if needs_compute:
        texts = [
            f"{articles[i]['title']} {articles[i].get('full_text', '') or articles[i].get('summary', '')}"
            for i in needs_compute
        ]
        new_embeddings = compute_embeddings(texts)
        for pos, idx in enumerate(needs_compute):
            embeddings[idx] = new_embeddings[pos]

    emb_matrix = np.array(embeddings, dtype=np.float32)
    suppressed_indices: set[int] = set()

    for i in range(len(articles)):
        if i in suppressed_indices:
            continue
        vec = emb_matrix[i]
        sims = batch_cosine_similarity(vec, emb_matrix)

        for j in range(i + 1, len(articles)):
            if j in suppressed_indices:
                continue
            if sims[j] >= COSINE_THRESHOLD:
                # Keep the higher-scored; break ties by source tier (lower = better)
                score_i = max(articles[i].get("scores", {}).values(), default=0)
                score_j = max(articles[j].get("scores", {}).values(), default=0)
                if score_i != score_j:
                    loser = j if score_i >= score_j else i
                else:
                    tier_i = articles[i].get("tier", 4)
                    tier_j = articles[j].get("tier", 4)
                    loser = j if tier_i <= tier_j else i
                suppressed_indices.add(loser)
                logger.info(
                    "Weekly embedding dedup: suppressed '%s' (cosine=%.3f with '%s')",
                    articles[loser]["title"][:50],
                    sims[j],
                    articles[i if loser == j else j]["title"][:50],
                )

    kept = [a for idx, a in enumerate(articles) if idx not in suppressed_indices]
    logger.info(
        "Weekly embedding dedup: %d -> %d (%d suppressed)",
        len(articles), len(kept), len(suppressed_indices),
    )
    return kept


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Weekly Briefing Pipeline (reads from article DB)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Skip LLM calls and use placeholder text",
    )
    parser.add_argument(
        "--audience", metavar="AUDIENCE_ID",
        choices=list(AUDIENCE_PROFILES.keys()),
        help="Run for a single audience only",
    )
    parser.add_argument(
        "--days", type=int, default=7,
        help="Number of days back to load articles (default: 7)",
    )
    parser.add_argument(
        "--no-cache", action="store_true",
        help="Force LLM regeneration (ignore existing cache)",
    )
    args = parser.parse_args()

    dry_run = args.dry_run
    no_cache = args.no_cache
    days = args.days
    audience_ids = [args.audience] if args.audience else AUDIENCE_ORDER

    generation_time = datetime.now(tz=timezone.utc)
    date_str = generation_time.strftime("%Y-%m-%d")
    output_dir = OUTPUT_ROOT / date_str

    print("=" * 60)
    print(f"  Weekly Briefing Pipeline -- {date_str}")
    print(f"  Audiences : {', '.join(audience_ids)}")
    print(f"  Lookback  : {days} days")
    print(f"  Dry run   : {'YES (no LLM calls)' if dry_run else 'NO'}")
    print(f"  Output    : {output_dir}")
    print("=" * 60)

    # ── 1. Load articles from DB ──────────────────────────────────────────
    print(f"\n[1/8] Loading articles from DB (last {days} days)...")
    engine = init_db()
    session = get_session(engine)

    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days)
    db_rows = session.query(DBArticle).filter(DBArticle.ingest_at >= cutoff).all()
    session.close()

    articles = [_db_row_to_article_dict(row) for row in db_rows]
    print(f"      Loaded {len(articles)} articles from database")

    if not articles:
        print("WARNING: No articles found in the database for the given time window.")
        print("         Run scripts/daily_ingest.py first to populate the database.")
        sys.exit(1)

    # ── 2. Pre-score ──────────────────────────────────────────────────────
    # For weekly: give all articles a flat timeliness score (no recency bias)
    # Importance comes from source credibility + section relevance, not freshness
    from briefing.score import _source_credibility_score, _keyword_bonus, _deal_size_bonus
    print("\n[2/8] Pre-scoring articles (weekly mode: flat timeliness + keyword + deal-size boost)...")
    for article in articles:
        credibility = _source_credibility_score(article["tier"])
        keywords = _keyword_bonus(article.get("title", ""), article.get("summary", ""))
        deal_size = _deal_size_bonus(article.get("title", ""), article.get("summary", ""))
        article["scores"] = {"_prescore": credibility + 8 + keywords + deal_size}
    articles.sort(key=lambda a: a["scores"].get("_prescore", 0), reverse=True)
    print(f"      → Pre-scored {len(articles)} articles")

    # ── 3. Embedding dedup across the week ────────────────────────────────
    # Sort by published_at ASC so earliest (breaking news) version survives dedup
    articles.sort(key=lambda a: a.get("published_at") or datetime.min.replace(tzinfo=timezone.utc))
    print(f"\n[3/8] Cross-day embedding deduplication (cosine >= {COSINE_THRESHOLD})...")
    before = len(articles)
    articles = _weekly_embedding_dedup(articles)
    print(f"      {len(articles)} articles after dedup ({before - len(articles)} removed)")

    # Clean up the internal _stored_embedding field
    for article in articles:
        article.pop("_stored_embedding", None)

    if not articles:
        print("ERROR: No articles remaining after dedup. Exiting.")
        sys.exit(1)

    # ── 4. Classify ───────────────────────────────────────────────────────
    # For weekly: classify top articles from EACH day (not just global top N)
    # This ensures articles from all days get classified, not just the latest
    from collections import defaultdict
    by_date: dict[str, list] = defaultdict(list)
    for a in articles:
        pub = a.get("published_at")
        day = pub.strftime("%Y-%m-%d") if pub else "unknown"
        by_date[day].append(a)

    n_days = max(len(by_date), 1)
    per_day = max(60, 300 // n_days)  # ~60-75 per day = ~300 total for the week
    diverse_top: list[dict] = []
    for day in sorted(by_date.keys()):
        day_sorted = sorted(by_date[day], key=lambda a: max(a.get("scores", {}).values(), default=0), reverse=True)
        diverse_top.extend(day_sorted[:per_day])

    import briefing.config as _cfg2
    import main as _main_mod2
    _orig_max_cfg = _cfg2.MAX_ARTICLES_TO_CLASSIFY
    _orig_max_main = _main_mod2.MAX_ARTICLES_TO_CLASSIFY
    _cfg2.MAX_ARTICLES_TO_CLASSIFY = len(diverse_top)
    _main_mod2.MAX_ARTICLES_TO_CLASSIFY = len(diverse_top)

    # Replace article list order so diverse_top comes first
    diverse_urls = {a["url"] for a in diverse_top}
    rest = [a for a in articles if a["url"] not in diverse_urls]
    articles = diverse_top + rest

    articles = step_classify(articles, dry_run=dry_run, no_cache=no_cache)
    _cfg2.MAX_ARTICLES_TO_CLASSIFY = _orig_max_cfg
    _main_mod2.MAX_ARTICLES_TO_CLASSIFY = _orig_max_main

    # ── 4b. Relevance filter ─────────────────────────────────────────────
    articles = step_relevance_filter(articles)

    # ── 5. Full audience score (weekly: override timeliness to be flat) ──
    # Temporarily patch timeliness scores so all 7 days are equal
    import briefing.config as _cfg
    _original_timeliness = _cfg.TIMELINESS_SCORES
    _cfg.TIMELINESS_SCORES = [(168, 8), (None, 4)]  # all within 7 days get 8, older get 4
    articles = step_full_score(articles)
    _cfg.TIMELINESS_SCORES = _original_timeliness  # restore

    # ── 6. Generate summaries ─────────────────────────────────────────────
    # Override get_top_articles_for_audience to enforce date diversity
    import briefing.score as _score_mod
    _orig_get_top = _score_mod.get_top_articles_for_audience

    WEEKLY_ARTICLES_PER_AUDIENCE = 25

    def _diverse_top(articles, audience_id, n=None):
        """Pick top articles with date + company diversity."""
        n = n or WEEKLY_ARTICLES_PER_AUDIENCE
        ranked = sorted(articles, key=lambda a: a.get("scores", {}).get(audience_id, 0), reverse=True)
        from collections import defaultdict
        import re as _re

        day_counts = defaultdict(int)
        company_counts = defaultdict(int)
        n_days = len(set(
            a.get("published_at").strftime("%Y-%m-%d") if a.get("published_at") else "x"
            for a in ranked
        ))
        max_per_day = max(5, n // max(n_days, 1) + 2)
        max_per_company = 4  # cap per company to prevent flooding

        # Major companies to track for diversity
        company_patterns = [
            ("anthropic", r"\banthropic\b"),
            ("openai", r"\bopenai\b"),
            ("meta", r"\bmeta\b"),
            ("google", r"\bgoogle\b"),
            ("amazon", r"\b(?:amazon|aws)\b"),
            ("microsoft", r"\b(?:microsoft|azure)\b"),
            ("nvidia", r"\bnvidia\b"),
            ("apple", r"\bapple\b"),
            ("coreweave", r"\bcoreweave\b"),
        ]

        def _get_company(article):
            title = article.get("title", "").lower()
            for name, pattern in company_patterns:
                if _re.search(pattern, title):
                    return name
            return "other"

        result = []
        for a in ranked:
            day = a.get("published_at").strftime("%Y-%m-%d") if a.get("published_at") else "x"
            company = _get_company(a)

            if day_counts[day] >= max_per_day:
                continue
            if company != "other" and company_counts[company] >= max_per_company:
                continue

            result.append(a)
            day_counts[day] += 1
            company_counts[company] += 1

            if len(result) >= n:
                break
        return result

    _score_mod.get_top_articles_for_audience = _diverse_top
    # Also patch in main.py's namespace (it imports the function directly)
    import main as _main_mod
    _orig_main_get_top = _main_mod.get_top_articles_for_audience
    _main_mod.get_top_articles_for_audience = _diverse_top
    # Override articles per audience from 12 to 25 for weekly
    _orig_top_n = _cfg.TOP_ARTICLES_PER_AUDIENCE
    _cfg.TOP_ARTICLES_PER_AUDIENCE = WEEKLY_ARTICLES_PER_AUDIENCE
    _main_mod.TOP_ARTICLES_PER_AUDIENCE = WEEKLY_ARTICLES_PER_AUDIENCE

    articles = step_generate_summaries(
        articles, audience_ids, dry_run=dry_run, no_cache=no_cache,
    )
    # Keep _diverse_top active through exec summaries and render too

    # ── 7. Executive summaries ────────────────────────────────────────────
    exec_summaries = step_executive_summaries(
        articles, audience_ids, dry_run=dry_run,
    )

    # ── 8. Render ─────────────────────────────────────────────────────────
    # Compute date range from article published dates
    pub_dates = [a["published_at"] for a in articles if a.get("published_at")]
    if pub_dates:
        earliest = min(pub_dates)
        latest = max(pub_dates)
        if earliest.date() == latest.date():
            date_range = latest.strftime("%a %b %d, %Y")
        else:
            date_range = f"{earliest.strftime('%b %d')} – {latest.strftime('%b %d, %Y')}"
    else:
        date_range = generation_time.strftime("%a %b %d, %Y")

    # Monkey-patch the render masthead to include date range
    import briefing.render as _render
    _original_masthead = _render._render_masthead
    _render._render_masthead = lambda gt, **kw: _original_masthead(gt, date_range=date_range)

    paths = step_render(articles, audience_ids, exec_summaries, output_dir, generation_time)

    # Restore overrides
    _score_mod.get_top_articles_for_audience = _orig_get_top
    _main_mod.get_top_articles_for_audience = _orig_main_get_top
    _cfg.TOP_ARTICLES_PER_AUDIENCE = _orig_top_n
    _main_mod.TOP_ARTICLES_PER_AUDIENCE = _orig_top_n

    # ── Persist to DB ─────────────────────────────────────────────────────
    _persist_to_db(articles, audience_ids, exec_summaries, date_str)

    # ── Email delivery ────────────────────────────────────────────────────
    if not dry_run:
        from briefing.render_email import render_email_html
        from app.delivery.email_delivery import send_all_briefings as _send_emails

        print("\n[Email] Rendering email versions...")
        email_html = {}
        for aud_id in audience_ids:
            top_arts = _diverse_top(articles, aud_id)
            email_html[aud_id] = render_email_html(
                aud_id, top_arts, exec_summaries.get(aud_id, {}),
                generation_time, date_range=date_range,
            )
            print(f"      [{aud_id}] {len(email_html[aud_id])} bytes")

        results = _send_emails(email_html, date_str)
        for r in results:
            print(f"      [{r['to']}] {r['status']}")

    # ── Done ──────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  DONE")
    print(f"  Open: http://localhost:8000/{date_str}/index.html")
    print("  Run:  python3 serve.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
