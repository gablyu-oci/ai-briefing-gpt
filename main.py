#!/usr/bin/env python3
"""
main.py — AI Daily Executive Briefing Pipeline

Usage:
  python3 main.py                     # full run (with LLM)
  python3 main.py --dry-run           # skip LLM, use placeholder text
  python3 main.py --audience karan    # run for a single audience
  python3 main.py --no-cache          # force regeneration (ignore cache)
  python3 main.py --dry-run --audience greg
"""

import argparse
import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

# ── Project imports ──────────────────────────────────────────────────────────
from briefing.config import (
    AUDIENCE_PROFILES,
    AUDIENCE_ORDER,
    MAX_ARTICLES_TO_CLASSIFY,
    MAX_CONCURRENT_LLM,
    TOP_ARTICLES_PER_AUDIENCE,
    TIER_CREDIBILITY_SCORES,
    TIMELINESS_SCORES,
)
from briefing.ingest  import ingest_feeds
from briefing.score   import (
    score_all_articles, get_top_articles_for_audience, get_top_articles_global,
    _source_credibility_score, _timeliness_score,
)
from briefing.render  import save_briefings
from app.dedup.pipeline import run_dedup_pipeline
from app.db.models import (
    init_db, get_session, Article as DBArticle, AudienceBriefing,
)

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── Output root ──────────────────────────────────────────────────────────────
OUTPUT_ROOT = Path(__file__).parent / "output"


# ---------------------------------------------------------------------------
# Dry-run placeholders
# ---------------------------------------------------------------------------

DRY_RUN_CLASSIFICATION = {
    "topics":    ["cloud computing", "AI infrastructure"],
    "entities":  ["Oracle", "OCI", "NVIDIA"],
    "section":   "ai",
    "confidence": "high",
}

def _dry_run_summary(article: dict, audience_id: str) -> dict:
    return {
        "headline":        f"[DRY RUN] {article['title'][:80]}",
        "summary":         (
            f"This is a placeholder summary for '{article['title'][:60]}'. "
            "In production, Oracle Code Assist generates a personalised 2-3 sentence summary "
            "tailored to this executive's role and priorities."
        ),
    }

def _dry_run_exec_summary(top_articles: list[dict], audience_id: str) -> dict:
    profile = AUDIENCE_PROFILES[audience_id]
    headlines = [a["title"][:70] for a in top_articles[:5]]
    bullets = [f"{h}..." for h in headlines] or ["No articles available for this period."]
    return {
        "bullets": bullets,
        "market_outlook": (
            f"[DRY RUN] Market outlook for {profile['name']} ({profile['title']}). "
            "Oracle Code Assist would synthesise today's top signals into a forward-looking market "
            "analysis — identifying key trends, competitive shifts, and inflection points "
            "most relevant to this executive's priorities."
        ),
    }


# ---------------------------------------------------------------------------
# Pipeline steps
# ---------------------------------------------------------------------------

def step_ingest() -> list[dict]:
    print("\n[1/9] Ingesting RSS feeds...")
    articles = ingest_feeds()
    print(f"      → {len(articles)} articles ingested")
    return articles


def step_prescore(articles: list[dict]) -> list[dict]:
    """Lightweight pre-score using only source credibility + timeliness."""
    print("\n[2/9] Pre-scoring articles (source credibility + timeliness)...")
    for article in articles:
        credibility = _source_credibility_score(article["tier"])
        timeliness = _timeliness_score(article["published_at"])
        prescore = credibility + timeliness
        article["scores"] = {"_prescore": prescore}
    articles.sort(key=lambda a: a["scores"].get("_prescore", 0), reverse=True)
    print(f"      → Pre-scored {len(articles)} articles")
    return articles


def step_inrun_dedup(articles: list[dict]) -> list[dict]:
    """In-run dedup: remove same-day duplicates within this batch."""
    print("\n[3/9] In-run deduplication...")
    articles = run_dedup_pipeline(articles, save_to_db=True)
    print(f"      → {len(articles)} articles after in-run dedup")
    return articles


def step_cross_day_dedup(articles: list[dict], skip_history: bool = False) -> list[dict]:
    """Cross-day dedup: compare against 7-day cluster history using embeddings."""
    print("\n[4/9] Cross-day deduplication (embedding-based)...")

    if skip_history:
        print("      Synthetic demo articles detected — skipping cross-day history check")
        return articles

    from app.dedup.embeddings import compute_embeddings
    from app.dedup.fingerprint import extract_facts
    from app.dedup.cross_day import (
        load_recent_clusters,
        check_against_history,
        save_new_cluster,
        update_cluster_seen,
    )
    from app.db.models import (
        init_db as _init_db, get_session as _get_session,
        Article as _Article, SuppressionLog as _SuppressionLog,
    )

    # 4a. Load cluster history
    clusters = load_recent_clusters(days=7)
    print(f"      Loaded {len(clusters)} clusters from last 7 days")

    if not articles:
        print("      → No articles to process")
        return articles

    # 4b. Compute embeddings for all surviving articles
    texts = [f"{a['title']} {a.get('full_text', '') or a.get('summary', '')}" for a in articles]
    embeddings = compute_embeddings(texts)
    print(f"      Computed embeddings for {len(embeddings)} articles")

    # 4c-d. Check each article against history
    kept: list[dict] = []
    suppressed_articles: list[dict] = []
    suppressed_count = 0
    followup_count = 0
    new_count = 0

    for article, embedding in zip(articles, embeddings):
        decision, matched_cluster = check_against_history(
            article, embedding, clusters
        )

        if decision == "suppress":
            suppressed_count += 1
            article["_suppression_reason"] = "cross_day_duplicate"
            article["_similarity_score"] = matched_cluster.get("_cosine_score", 0.0) if matched_cluster else 0.0
            article["_matched_cluster_id"] = matched_cluster["id"] if matched_cluster else None
            suppressed_articles.append(article)
            logger.info(
                "cross_day_suppress: %s (matched cluster %s)",
                article["title"][:60],
                matched_cluster["headline"][:40] if matched_cluster else "?",
            )
            # Update cluster last_seen (skip for in-memory-only clusters)
            if matched_cluster and matched_cluster.get("id") is not None:
                facts = extract_facts(article)
                update_cluster_seen(matched_cluster["id"], facts)
        elif decision == "followup":
            followup_count += 1
            article["_is_followup"] = True
            article["_followup_of"] = matched_cluster["canonical_url"] if matched_cluster else None
            kept.append(article)
            logger.info(
                "cross_day_followup: %s (follow-up to %s)",
                article["title"][:60],
                matched_cluster["headline"][:40] if matched_cluster else "?",
            )
            # Update cluster with new facts (skip for in-memory-only clusters)
            if matched_cluster and matched_cluster.get("id") is not None:
                facts = extract_facts(article)
                update_cluster_seen(matched_cluster["id"], facts)
        else:
            # New story — save as new cluster
            new_count += 1
            facts = extract_facts(article)
            save_new_cluster(article, embedding, facts)
            kept.append(article)
            # Append to in-memory cluster list so subsequent articles
            # in this batch can match against it (fixes duplicate clusters)
            clusters.append({
                "id": None,  # DB id not needed for comparison
                "canonical_url": article["url"],
                "headline": article["title"],
                "embedding": embedding,
                "fact_snapshot": facts,
            })

    # 4f. Persist suppressions to DB
    if suppressed_articles:
        try:
            _engine = _init_db()
            _session = _get_session(_engine)
            for sup in suppressed_articles:
                db_art = _session.query(_Article).filter_by(url=sup["url"]).first()
                if not db_art:
                    db_art = _Article(
                        url=sup["url"],
                        title=sup["title"],
                        published_at=sup.get("published_at"),
                        summary=sup.get("summary", ""),
                        tier=sup.get("tier", 2),
                        raw_score=max(sup.get("scores", {}).values(), default=0),
                        source_name=sup.get("source", ""),
                    )
                    _session.add(db_art)
                    _session.flush()
                log = _SuppressionLog(
                    article_id=db_art.id,
                    reason=sup["_suppression_reason"],
                    similarity_score=sup.get("_similarity_score", 0.0),
                    matched_cluster_id=sup.get("_matched_cluster_id"),
                )
                _session.add(log)
            _session.commit()
            _session.close()
            logger.info("Persisted %d suppressions to DB", len(suppressed_articles))
        except Exception as exc:
            logger.warning("Failed to persist suppressions: %s", exc)

    print(f"      → {len(kept)} kept, {suppressed_count} suppressed, "
          f"{followup_count} follow-ups, {new_count} new clusters")
    return kept


def step_classify(articles: list[dict], dry_run: bool, no_cache: bool) -> list[dict]:
    """Classify top-N articles with Haiku (or use placeholders in dry-run mode)."""
    print(f"\n[5/9] Classifying top {MAX_ARTICLES_TO_CLASSIFY} articles...")

    to_classify = get_top_articles_global(articles, n=MAX_ARTICLES_TO_CLASSIFY)

    if dry_run:
        for a in to_classify:
            a.update(DRY_RUN_CLASSIFICATION)
            if a.get("sections"):
                a["classified_section"] = a["sections"][0]
            else:
                a["classified_section"] = DRY_RUN_CLASSIFICATION["section"]
        print(f"      → [DRY RUN] Skipped LLM — applied placeholder classification to {len(to_classify)} articles")
        return articles

    from briefing.llm import classify_article, CACHE_DIR

    if no_cache:
        # Remove existing cache files (only classification ones)
        for f in CACHE_DIR.glob("*.json"):
            if f.name.startswith("classify_"):
                f.unlink()

    classified_count = 0
    cache_hits = 0

    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_LLM) as pool:
        future_to_article = {
            pool.submit(classify_article, a): a for a in to_classify
        }
        for i, future in enumerate(as_completed(future_to_article), 1):
            article = future_to_article[future]
            try:
                result = future.result()
                article["topics"]    = result.get("topics", [])
                article["entities"]  = result.get("entities", [])
                article["classified_section"] = result.get("section") or (
                    article["sections"][0] if article["sections"] else "other"
                )
                article["confidence"] = result.get("confidence", "medium")
                article["executive_relevance"] = result.get("executive_relevance", "medium")
                classified_count += 1
                print(f"      [{i}/{len(to_classify)}] {article['source']}: {article['title'][:60]}...")
            except Exception as exc:
                logger.warning("Classification failed for %s: %s", article["url"][:50], exc)
                article["classified_section"] = article["sections"][0] if article["sections"] else "other"
                article["confidence"] = "low"

    print(f"      → Classified {classified_count} articles ({cache_hits} cache hits)")
    return articles


def step_relevance_filter(articles: list[dict]) -> list[dict]:
    """Drop articles that are irrelevant or not executive-grade."""
    all_relevant_sections: set[str] = set()
    for profile in AUDIENCE_PROFILES.values():
        all_relevant_sections.update(profile["section_weights"].keys())

    # Keyword patterns that indicate non-executive content
    LOW_VALUE_PATTERNS = [
        "how to ", "how do ", "how i ", "best apps", "tips for", "ways to",
        "review:", "hands-on", "deal:", "sale:", "deals:", "% off",
        "unboxing", "vs.", "which is better", "beginners guide",
        "podcast:", "recipe", "horoscope", "obituary",
        "opinion |", "opinion:", "| opinion", "what your ", "what you ",
        "why you should", "why you might", "should you ",
        "here's how", "here's why", "here's what",
        "readers share", "readers say",
    ]

    kept = []
    dropped = 0
    for article in articles:
        classified = article.get("classified_section") not in (None, "", "None")
        section = article.get("classified_section") or ""
        confidence = article.get("confidence") or "medium"
        exec_relevance = article.get("executive_relevance")  # None if not classified
        title_lower = article.get("title", "").lower()

        # Drop if title matches low-value patterns (runs first, catches everything)
        if any(p in title_lower for p in LOW_VALUE_PATTERNS):
            dropped += 1
            logger.info("Relevance filter (pattern): dropped '%s'", article["title"][:60])
            continue

        # Drop if LLM flagged as low executive relevance
        if exec_relevance == "low":
            dropped += 1
            logger.info("Relevance filter (exec=low): dropped '%s'", article["title"][:60])
            continue

        # Drop unclassified articles (never went through LLM) — they have no quality signal
        if not classified:
            dropped += 1
            logger.info("Relevance filter (unclassified): dropped '%s'", article["title"][:60])
            continue

        # Drop if confidence is low AND section doesn't match any audience
        if confidence == "low" and section not in all_relevant_sections:
            if not any(s in all_relevant_sections for s in article.get("sections", [])):
                dropped += 1
                logger.info("Relevance filter (conf=low): dropped '%s'", article["title"][:60])
                continue

        kept.append(article)

    if dropped:
        print(f"      → Relevance filter: dropped {dropped} irrelevant articles")
    return kept


def step_full_score(articles: list[dict]) -> list[dict]:
    """Full audience-relevance scoring (after classification)."""
    print("\n[6/9] Full audience scoring...")
    articles = score_all_articles(articles)
    print(f"      → Scored {len(articles)} articles across all audiences")
    return articles


def step_generate_summaries(
    articles: list[dict],
    audience_ids: list[str],
    dry_run: bool,
    no_cache: bool,
) -> list[dict]:
    """Generate per-audience summaries for top articles."""
    print(f"\n[7/9] Generating article summaries (audiences: {', '.join(audience_ids)})...")

    if not dry_run:
        from briefing.llm import generate_summary, CACHE_DIR
        if no_cache:
            for f in CACHE_DIR.glob("*.json"):
                if not f.name.startswith("classify_"):
                    f.unlink()

    total_generated = 0
    summary_jobs: list[tuple[str, dict, dict, int, int]] = []

    for aud_id in audience_ids:
        profile   = AUDIENCE_PROFILES[aud_id]
        top_arts  = get_top_articles_for_audience(articles, aud_id, n=TOP_ARTICLES_PER_AUDIENCE)
        print(f"\n      Audience: {profile['name']} — {len(top_arts)} articles")

        for i, article in enumerate(top_arts, 1):
            if dry_run:
                summary = _dry_run_summary(article, aud_id)
                article.setdefault("per_audience_summaries", {})[aud_id] = summary
                total_generated += 1
            else:
                summary_jobs.append((aud_id, profile, article, i, len(top_arts)))

    if not dry_run and summary_jobs:
        summary_workers = max(1, min(MAX_CONCURRENT_LLM, len(summary_jobs)))
        print(f"      Using {summary_workers} parallel Codex workers for summaries")

        with ThreadPoolExecutor(max_workers=summary_workers) as pool:
            future_to_job = {
                pool.submit(generate_summary, article, profile): (aud_id, article, i, total)
                for aud_id, profile, article, i, total in summary_jobs
            }
            for future in as_completed(future_to_job):
                aud_id, article, i, total = future_to_job[future]
                try:
                    summary = future.result()
                except Exception as exc:
                    logger.warning(
                        "Summary failed for %s / %s: %s",
                        aud_id,
                        article["url"][:40],
                        exc,
                    )
                    summary = _dry_run_summary(article, aud_id)
                article.setdefault("per_audience_summaries", {})[aud_id] = summary
                total_generated += 1
                print(f"        [{aud_id} {i}/{total}] {article['title'][:55]}...")

    if dry_run:
        print(f"      → [DRY RUN] Placeholder summaries for {total_generated} article×audience pairs")
    else:
        print(f"      → Generated {total_generated} summaries")
    return articles


def step_executive_summaries(
    articles: list[dict],
    audience_ids: list[str],
    dry_run: bool,
) -> dict[str, dict]:
    """Generate executive summary per audience."""
    print(f"\n[8/9] Generating executive summaries...")
    exec_summaries: dict[str, dict] = {}
    exec_jobs: list[tuple[str, dict, list[dict]]] = []

    for aud_id in audience_ids:
        profile  = AUDIENCE_PROFILES[aud_id]
        top_arts = get_top_articles_for_audience(articles, aud_id, n=TOP_ARTICLES_PER_AUDIENCE)

        if dry_run:
            exec_summaries[aud_id] = _dry_run_exec_summary(top_arts, aud_id)
            print(f"      [{aud_id}] [DRY RUN] placeholder executive summary")
        else:
            exec_jobs.append((aud_id, profile, top_arts))

    if not dry_run and exec_jobs:
        from briefing.llm import generate_executive_summary

        exec_workers = max(1, min(MAX_CONCURRENT_LLM, len(exec_jobs)))
        if exec_workers > 1:
            print(f"      Using {exec_workers} parallel Codex workers for executive summaries")

        with ThreadPoolExecutor(max_workers=exec_workers) as pool:
            future_to_job = {
                pool.submit(generate_executive_summary, top_arts, profile): (aud_id, top_arts)
                for aud_id, profile, top_arts in exec_jobs
            }
            for future in as_completed(future_to_job):
                aud_id, top_arts = future_to_job[future]
                try:
                    exec_summaries[aud_id] = future.result()
                    print(f"      [{aud_id}] Executive summary generated")
                except Exception as exc:
                    logger.warning("exec_summary failed for %s: %s", aud_id, exc)
                    exec_summaries[aud_id] = _dry_run_exec_summary(top_arts, aud_id)

    return exec_summaries


def step_render(
    articles: list[dict],
    audience_ids: list[str],
    exec_summaries: dict[str, dict],
    output_dir: Path,
    generation_time: datetime,
) -> dict[str, Path]:
    """Render HTML files."""
    print(f"\n[9/9] Rendering HTML briefings...")

    all_audience_data: dict[str, dict] = {}
    for aud_id in audience_ids:
        top_arts = get_top_articles_for_audience(articles, aud_id, n=TOP_ARTICLES_PER_AUDIENCE)
        all_audience_data[aud_id] = {
            "articles":     top_arts,
            "exec_summary": exec_summaries.get(aud_id, {}),
            "nav_links":    "",  # populated by save_briefings
        }

    paths = save_briefings(all_audience_data, output_dir, generation_time)

    for key, path in paths.items():
        size_kb = path.stat().st_size // 1024
        print(f"      [{key}] {path}  ({size_kb} KB)")

    return paths


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="AI Daily Executive Briefing Pipeline"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Skip LLM calls and use placeholder text (fast pipeline test)"
    )
    parser.add_argument(
        "--audience", metavar="AUDIENCE_ID",
        choices=list(AUDIENCE_PROFILES.keys()),
        help="Run for a single audience only (e.g. karan, nathan, greg, mahesh)"
    )
    parser.add_argument(
        "--no-cache", action="store_true",
        help="Force LLM regeneration (ignore existing cache)"
    )
    args = parser.parse_args()

    dry_run  = args.dry_run
    no_cache = args.no_cache
    audience_ids = [args.audience] if args.audience else AUDIENCE_ORDER

    generation_time = datetime.now(tz=timezone.utc)
    date_str = generation_time.strftime("%Y-%m-%d")
    output_dir = OUTPUT_ROOT / date_str
    using_synthetic_articles = False

    print("=" * 60)
    print(f"  AI Daily Executive Briefing — {date_str}")
    print(f"  Audiences : {', '.join(audience_ids)}")
    print(f"  Dry run   : {'YES (no LLM calls)' if dry_run else 'NO'}")
    print(f"  Output    : {output_dir}")
    print("=" * 60)

    # ── 1. Fetch ──────────────────────────────────────────────────────────
    articles = step_ingest()

    if not articles:
        print("\nWARNING: No articles ingested. Feeds may be down or all articles are older than 48h.")
        print("         Using synthetic demo articles for dry-run mode...")
        articles = _synthetic_articles(generation_time)
        using_synthetic_articles = True

    # ── 2. Pre-score ──────────────────────────────────────────────────────
    articles = step_prescore(articles)

    # ── 3. In-run dedup ──────────────────────────────────────────────────
    articles = step_inrun_dedup(articles)

    if not articles:
        print("ERROR: No articles after in-run dedup. Exiting.")
        sys.exit(1)

    # ── 4. Cross-day dedup (runs even in dry-run — no LLM needed) ────────
    articles = step_cross_day_dedup(articles, skip_history=using_synthetic_articles)

    if not articles:
        print("ERROR: No articles after cross-day dedup. Exiting.")
        sys.exit(1)

    # ── 5. Classify ────────────────────────────────────────────────────────
    articles = step_classify(articles, dry_run=dry_run, no_cache=no_cache)

    # ── 5b. Relevance filter ──────────────────────────────────────────────
    articles = step_relevance_filter(articles)

    # ── 6. Full audience score ────────────────────────────────────────────
    articles = step_full_score(articles)

    # ── 7. Generate summaries ──────────────────────────────────────────────
    articles = step_generate_summaries(articles, audience_ids, dry_run=dry_run, no_cache=no_cache)

    # ── 8. Executive summaries ─────────────────────────────────────────────
    exec_summaries = step_executive_summaries(articles, audience_ids, dry_run=dry_run)

    # ── 9. Render ──────────────────────────────────────────────────────────
    paths = step_render(articles, audience_ids, exec_summaries, output_dir, generation_time)

    # ── Persist to DB ─────────────────────────────────────────────────────
    _persist_to_db(articles, audience_ids, exec_summaries, date_str)

    # ── Done ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  DONE")
    print(f"  Open: http://localhost:8000/{date_str}/index.html")
    print("  Run:  python3 serve.py")
    print("=" * 60)


# ---------------------------------------------------------------------------
# DB persistence — save articles, scores, and briefings to SQLite
# ---------------------------------------------------------------------------

def _persist_to_db(
    articles: list[dict],
    audience_ids: list[str],
    exec_summaries: dict[str, dict],
    date_str: str,
) -> None:
    """Save pipeline results to the database for admin dashboard monitoring."""
    try:
        engine = init_db()
        session = get_session(engine)

        # Save/update articles
        article_count = 0
        for article in articles:
            existing = session.query(DBArticle).filter_by(url=article["url"]).first()
            if existing:
                existing.raw_score = max(article.get("scores", {}).values(), default=0)
                existing.embedding_json = article.get("_embedding_json")
                existing.source_name = article.get("source", "")
            else:
                db_art = DBArticle(
                    url=article["url"],
                    title=article["title"],
                    published_at=article.get("published_at"),
                    summary=article.get("summary", ""),
                    tier=article.get("tier", 2),
                    raw_score=max(article.get("scores", {}).values(), default=0),
                    embedding_json=article.get("_embedding_json"),
                    source_name=article.get("source", ""),
                )
                session.add(db_art)
                article_count += 1

        # Save audience briefings
        briefing_count = 0
        for aud_id in audience_ids:
            existing = session.query(AudienceBriefing).filter_by(
                audience_id=aud_id, briefing_date=date_str
            ).first()
            if existing:
                existing.exec_summary_json = exec_summaries.get(aud_id, {})
                existing.article_ids_json = [
                    a["url"] for a in sorted(
                        articles,
                        key=lambda a: a.get("scores", {}).get(aud_id, 0),
                        reverse=True,
                    )[:TOP_ARTICLES_PER_AUDIENCE]
                ]
            else:
                briefing = AudienceBriefing(
                    audience_id=aud_id,
                    briefing_date=date_str,
                    article_ids_json=[
                        a["url"] for a in sorted(
                            articles,
                            key=lambda a: a.get("scores", {}).get(aud_id, 0),
                            reverse=True,
                        )[:TOP_ARTICLES_PER_AUDIENCE]
                    ],
                    exec_summary_json=exec_summaries.get(aud_id, {}),
                )
                session.add(briefing)
                briefing_count += 1

        session.commit()
        session.close()
        logger.info("Persisted %d new articles and %d briefings to DB", article_count, briefing_count)
    except Exception as exc:
        logger.warning("Failed to persist to DB: %s", exc)


# ---------------------------------------------------------------------------
# Synthetic fallback articles (for when feeds are down)
# ---------------------------------------------------------------------------

def _synthetic_articles(generation_time: datetime) -> list[dict]:
    """Return a set of realistic synthetic articles for dry-run / demo mode."""
    from datetime import timedelta
    import hashlib

    def make(title, source, tier, sections, summary, hours_ago=2):
        url = f"https://example.com/{hashlib.md5(title.encode()).hexdigest()[:8]}"
        return {
            "id":           hashlib.sha256(url.encode()).hexdigest()[:16],
            "title":        title,
            "url":          url,
            "summary":      summary,
            "published_at": generation_time - timedelta(hours=hours_ago),
            "source":       source,
            "tier":         tier,
            "sections":     sections,
            "topics":       [],
            "entities":     [],
            "classified_section": sections[0] if sections else "other",
            "confidence":   "high",
            "scores":       {},
            "per_audience_summaries": {},
            "_synthetic":   True,
        }

    return [
        make(
            "NVIDIA Announces H200 Ultra GPU with 2x Training Throughput for Enterprise AI",
            "Reuters Tech", 1, ["ai", "compete", "financial"],
            "NVIDIA unveiled the H200 Ultra GPU claiming 2x training throughput over H100, "
            "targeting hyperscaler and enterprise AI workloads. The chip enters volume production "
            "in Q3 2026. AWS, Azure, and Google Cloud have all pre-ordered. OCI has not yet "
            "commented publicly on H200 Ultra availability.",
            hours_ago=3,
        ),
        make(
            "Microsoft Azure Signs $2.1B Multi-Year AI Infrastructure Deal with Saudi Aramco",
            "Reuters Business", 1, ["deals", "financial", "compete"],
            "Microsoft announced a $2.1 billion, 5-year agreement with Saudi Aramco to build "
            "AI-powered operations across the energy giant's global infrastructure. The deal "
            "includes sovereign cloud deployment in the Kingdom. OCI has an existing presence "
            "in the Gulf region and competes directly for energy-sector cloud contracts.",
            hours_ago=5,
        ),
        make(
            "OpenAI Releases GPT-5 with Native Multimodal Reasoning — Benchmarks Crush All Rivals",
            "TechCrunch", 2, ["ai", "compete"],
            "OpenAI released GPT-5, which it claims achieves state-of-the-art on 47 of 50 "
            "benchmarks including MMLU, HumanEval, and MATH. The model runs on Microsoft Azure "
            "exclusively at launch. Google DeepMind said Gemini Ultra 2 will respond next month.",
            hours_ago=1,
        ),
        make(
            "AWS Re:Invent Preview: Amazon to Announce New Graviton5 Chips and 25% Price Cuts",
            "Ars Technica", 2, ["compete", "financial", "ai"],
            "Sources close to Amazon indicate AWS will announce Graviton5 ARM-based compute chips "
            "and across-the-board price reductions averaging 25% on EC2 instances ahead of re:Invent. "
            "The move is seen as a direct response to OCI's aggressive pricing strategy.",
            hours_ago=6,
        ),
        make(
            "Google Deepens Partnership with SAP: All S/4HANA Workloads Can Run on GCP by 2027",
            "CloudWars", 2, ["compete", "deals", "multicloud"],
            "Google Cloud and SAP announced a deepened partnership under which all SAP S/4HANA "
            "workloads will be certified and optimised for Google Cloud Platform by Q4 2027. "
            "Oracle runs a significant portion of SAP competitor workloads and this deal "
            "could redirect ERP migration projects away from OCI.",
            hours_ago=8,
        ),
        make(
            "Data Center Power Crunch Worsens: Utilities Warn of 18-Month Wait for New Grid Connections",
            "Data Center Dynamics", 2, ["datacenter", "power"],
            "Multiple US utilities are imposing 12-18 month queues for new large-scale power "
            "interconnections as hyperscaler and AI lab demand outpaces grid capacity. "
            "Virginia, Texas, and Arizona are seeing the most severe bottlenecks. "
            "Operators with existing power agreements are at a significant advantage.",
            hours_ago=10,
        ),
        make(
            "Oracle's Ellison Commits $20B to US AI Infrastructure in WH Meeting",
            "Reuters Business", 1, ["financial", "ai", "datacenter"],
            "Larry Ellison joined other tech CEOs at the White House to announce over $20 billion "
            "in planned US AI infrastructure investment over the next 3 years, including new "
            "OCI datacenter capacity and partnerships with national labs. The announcement "
            "positions OCI as a key AI sovereign-cloud player in the US.",
            hours_ago=2,
        ),
        make(
            "Anthropic Claude 4 Achieves AGI-Level Coding: Solves 72% of SWE-Bench Verified",
            "VentureBeat AI", 2, ["ai", "compete"],
            "Anthropic released Claude 4 with a 72% solve rate on SWE-Bench Verified, the highest "
            "score ever recorded and what Anthropic calls 'AGI-level software engineering'. "
            "Claude 4 is available via API. Amazon Bedrock will carry the model; OCI Generative AI "
            "availability has not been announced.",
            hours_ago=4,
        ),
        make(
            "Kubernetes 1.32 Drops Docker Runtime Support — Enterprise Upgrade Wave Expected",
            "Ars Technica", 2, ["oss", "infrastructure", "compete"],
            "The Kubernetes project officially removed the dockershim compatibility layer in v1.32, "
            "forcing all clusters still using Docker as a runtime to migrate to containerd or CRI-O. "
            "Analysts estimate 40% of enterprise clusters are affected. Cloud providers will see "
            "a wave of re-platforming projects.",
            hours_ago=14,
        ),
        make(
            "Zero-Day in Linux Kernel Affects All Major Cloud Providers — Patch Available",
            "Reuters Tech", 1, ["security", "compete", "infrastructure"],
            "A critical zero-day vulnerability (CVE-2026-1337) in the Linux kernel affects bare-metal "
            "and virtualised environments across AWS, Azure, GCP, and OCI. A patch was released "
            "today. Cloud providers have begun rolling out emergency mitigations. OCI's security "
            "team confirmed patching is underway across all regions.",
            hours_ago=1,
        ),
        make(
            "Meta Llama 4 Released as Open Source: 400B Parameter Model Free to Download",
            "TechCrunch", 2, ["ai", "oss", "compete"],
            "Meta released Llama 4, a 400-billion parameter open-source model, under a permissive "
            "commercial licence. Early benchmarks show performance approaching GPT-4 on many tasks. "
            "The release could reshape the enterprise AI market, favouring cloud providers who "
            "can offer cost-efficient Llama 4 inference at scale.",
            hours_ago=7,
        ),
        make(
            "Show HN: I Built a Self-Hosted Kubernetes Cluster on OCI Always-Free Tier",
            "Hacker News", 4, ["community", "oss", "infrastructure"],
            "A developer shared a detailed tutorial on running a 4-node Kubernetes cluster entirely "
            "on OCI's Always-Free tier, attracting 1,200+ upvotes and 340 comments. The post is "
            "driving significant developer interest in OCI's free-tier offerings.",
            hours_ago=12,
        ),
        make(
            "Microsoft and Oracle Extend Multi-Cloud Database Partnership to 10 New Regions",
            "OCI Blog", 3, ["partnerships", "multicloud", "deals"],
            "Oracle and Microsoft announced the expansion of Oracle Database@Azure to 10 additional "
            "Azure regions, including Southeast Asia, Brazil, and Canada. The partnership now covers "
            "25 regions globally. Revenue sharing terms were not disclosed.",
            hours_ago=9,
        ),
        make(
            "EU AI Act Enforcement Begins: Cloud Providers Must Certify High-Risk AI Systems",
            "Reuters Tech", 1, ["security", "financial", "ai"],
            "The EU AI Act entered its first enforcement phase, requiring cloud providers to certify "
            "high-risk AI systems deployed in Europe. Non-compliance fines can reach 3% of global "
            "revenue. AWS and Azure have published compliance roadmaps; OCI's European compliance "
            "documentation is pending.",
            hours_ago=11,
        ),
        make(
            "xAI Raises $6B Series D at $80B Valuation to Build Colossus-2 Supercluster",
            "TechCrunch", 2, ["financial", "ai", "datacenter"],
            "Elon Musk's xAI closed a $6 billion round at an $80 billion valuation to fund "
            "Colossus-2, a 1-million GPU training cluster. The facility will require 4 gigawatts "
            "of power. Investors include sovereign wealth funds from the Gulf region, a geography "
            "where OCI is actively expanding.",
            hours_ago=16,
        ),
    ]


if __name__ == "__main__":
    main()
