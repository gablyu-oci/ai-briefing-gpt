#!/usr/bin/env python3
"""
daily_ingest.py -- Lightweight daily article ingestion with Codex importance filtering.

Fetches RSS feeds, computes embeddings, deduplicates within the batch,
skips URLs already stored in the database, uses Codex / Oracle Code Assist
to keep only important news items, and saves the survivors to SQLite.

Intended to run daily via cron (e.g. 5 AM UTC) so that articles are
captured before RSS feeds rotate them out.

Usage:
    python3 scripts/daily_ingest.py
"""

import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

# Ensure the project root is on sys.path so that package imports work
# when this script is invoked directly (e.g. python3 scripts/daily_ingest.py).
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from briefing.ingest import ingest_feeds
from briefing.llm import filter_important_for_daily_ingest
from app.dedup.embeddings import compute_embeddings, batch_cosine_similarity
from app.db.models import init_db, get_session, Article
from config.settings import MAX_CONCURRENT_LLM

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
# Embedding-based dedup (same logic as app.dedup.pipeline._embedding_dedup)
# ---------------------------------------------------------------------------

COSINE_THRESHOLD = 0.80


def _embedding_dedup(articles: list[dict], embeddings: list[list[float]]) -> tuple[list[dict], list[list[float]]]:
    """
    Remove near-duplicate articles within a single batch using cosine
    similarity of their embeddings.  Keeps the article with the higher
    pre-score when two articles exceed the threshold.

    Returns the filtered (articles, embeddings) lists in the same order.
    """
    if len(articles) < 2:
        return articles, embeddings

    import numpy as np

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
                # Keep the article with the higher score; break ties by index
                score_i = max(articles[i].get("scores", {}).values(), default=0)
                score_j = max(articles[j].get("scores", {}).values(), default=0)
                loser = j if score_i >= score_j else i
                suppressed_indices.add(loser)
                logger.info(
                    "Embedding dedup: suppressed '%s' (cosine=%.3f with '%s')",
                    articles[loser]["title"][:50],
                    sims[j],
                    articles[i if loser == j else j]["title"][:50],
                )

    kept_articles = [a for idx, a in enumerate(articles) if idx not in suppressed_indices]
    kept_embeddings = [e for idx, e in enumerate(embeddings) if idx not in suppressed_indices]

    logger.info(
        "Embedding dedup: %d -> %d (%d suppressed)",
        len(articles), len(kept_articles), len(suppressed_indices),
    )
    return kept_articles, kept_embeddings


def _drop_existing_urls(
    session,
    articles: list[dict],
    embeddings: list[list[float]],
) -> tuple[list[dict], list[list[float]], int]:
    """
    Remove articles whose URLs are already present in the database so we
    avoid unnecessary Codex calls during the daily ingest.
    """
    if not articles:
        return articles, embeddings, 0

    urls = [article["url"] for article in articles]
    existing_urls = {
        row[0]
        for row in session.query(Article.url).filter(Article.url.in_(urls)).all()
    }
    if not existing_urls:
        return articles, embeddings, 0

    kept_articles = []
    kept_embeddings = []
    skipped = 0

    for article, embedding in zip(articles, embeddings):
        if article["url"] in existing_urls:
            skipped += 1
            continue
        kept_articles.append(article)
        kept_embeddings.append(embedding)

    return kept_articles, kept_embeddings, skipped


def _filter_important_news(
    articles: list[dict],
    embeddings: list[list[float]],
) -> tuple[list[dict], list[list[float]], int]:
    """
    Keep only important, reportable news items according to the Codex-based
    ingest filter. Fail-open so transient LLM issues do not drop signal.
    """
    if not articles:
        return articles, embeddings, 0

    keep_mask = [True] * len(articles)
    dropped = 0
    workers = max(1, min(MAX_CONCURRENT_LLM, len(articles)))

    with ThreadPoolExecutor(max_workers=workers) as pool:
        future_to_idx = {
            pool.submit(filter_important_for_daily_ingest, article): idx
            for idx, article in enumerate(articles)
        }
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            article = articles[idx]

            try:
                verdict = future.result()
            except Exception as exc:
                logger.warning(
                    "Daily importance filter crashed for %s: %s",
                    article["url"][:60],
                    exc,
                )
                verdict = {
                    "keep": True,
                    "importance": "unknown",
                    "reason": "filter_exception_keep_article",
                }

            article["_daily_filter"] = verdict
            if verdict.get("keep", True):
                continue

            keep_mask[idx] = False
            dropped += 1
            logger.info(
                "Daily importance filter: dropped '%s' (%s)",
                article["title"][:70],
                verdict.get("reason", "no reason provided"),
            )

    kept_articles = [article for idx, article in enumerate(articles) if keep_mask[idx]]
    kept_embeddings = [embedding for idx, embedding in enumerate(embeddings) if keep_mask[idx]]
    return kept_articles, kept_embeddings, dropped


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print(f"=== Daily Ingest — {datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} ===")

    # 1. Fetch RSS feeds
    print("\n[1/6] Fetching RSS feeds...")
    articles = ingest_feeds()
    total_fetched = len(articles)
    print(f"      Fetched {total_fetched} articles from RSS feeds")

    if not articles:
        print("No articles fetched. Feeds may be down or empty. Exiting.")
        return

    # 2. Compute embeddings for all articles
    print("\n[2/6] Computing embeddings...")
    texts = [f"{a['title']} {a.get('full_text', '') or a.get('summary', '')}" for a in articles]
    embeddings = compute_embeddings(texts)
    print(f"      Computed {len(embeddings)} embeddings")

    # 3. Embedding dedup within today's batch
    print("\n[3/6] Deduplicating within batch (cosine >= {:.2f})...".format(COSINE_THRESHOLD))
    articles, embeddings = _embedding_dedup(articles, embeddings)
    dedup_removed = total_fetched - len(articles)
    print(f"      {len(articles)} articles after dedup ({dedup_removed} duplicates removed)")

    print("\n[4/6] Checking for URLs already in the database...")
    engine = init_db()
    session = get_session(engine)
    articles, embeddings, existing_skipped = _drop_existing_urls(session, articles, embeddings)
    print(f"      {len(articles)} new candidate articles ({existing_skipped} already stored)")

    if not articles:
        session.close()
        print("\nNo new candidate articles remained after duplicate checks.")
        return

    print("\n[5/6] Filtering for important news with Codex...")
    before_filter = len(articles)
    articles, embeddings, filtered_out = _filter_important_news(articles, embeddings)
    print(f"      {len(articles)} important articles kept ({filtered_out} dropped as low-value/non-news)")

    if not articles:
        session.close()
        print("\nNo important articles remained after the Codex filter.")
        return

    # 6. Save to database
    print("\n[6/6] Saving important articles to database...")
    saved_count = 0
    now = datetime.now(tz=timezone.utc)

    for article, embedding in zip(articles, embeddings):
        db_article = Article(
            url=article["url"],
            title=article["title"],
            summary=article.get("summary", ""),
            full_text=article.get("full_text", ""),
            source_name=article.get("source", ""),
            tier=article.get("tier", 2),
            published_at=article.get("published_at"),
            embedding_json=embedding,
            ingest_at=now,
        )
        session.add(db_article)
        saved_count += 1

    session.commit()
    session.close()

    total_skipped = dedup_removed + existing_skipped + filtered_out
    print(
        f"\nIngested {saved_count} important articles "
        f"({total_fetched} fetched, {total_skipped} skipped across dedup/existing/filtering)"
    )


if __name__ == "__main__":
    main()
