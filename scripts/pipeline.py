#!/usr/bin/env python3
"""
pipeline.py — OCI AI Daily Executive Briefing Pipeline

Usage:
  python3 scripts/pipeline.py                          # full run (with LLM)
  python3 scripts/pipeline.py --dry-run                # skip LLM, use placeholders
  python3 scripts/pipeline.py --audience karan         # single audience
  python3 scripts/pipeline.py --date 2026-03-11        # specific date
  python3 scripts/pipeline.py --no-cache               # force regeneration
  python3 scripts/pipeline.py --dry-run --audience greg
"""

import argparse
import hashlib
import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import (
    OUTPUT_ROOT, MAX_ARTICLES_TO_CLASSIFY,
    MAX_CONCURRENT_LLM, TOP_ARTICLES_PER_AUDIENCE,
    CACHE_DIR,
)
from config.audiences import AUDIENCE_PROFILES, AUDIENCE_ORDER
from app.db.models import init_db, get_session, AudienceBriefing
from app.db.seed import seed_sources
from app.ingestion.fetcher import ingest_feeds
from app.scoring.engine import score_all_articles, get_top_articles_for_audience, get_top_articles_global
from app.scoring.logger import log_scores_to_db
from app.processing.normalizer import normalize_articles
from app.dedup.pipeline import run_dedup_pipeline
from app.rendering.render import save_briefings

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


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
        "oci_implication": (
            "OCI implication placeholder: Oracle Code Assist would generate a concrete, "
            "strategic implication for OCI leadership here."
        ),
    }

def _dry_run_exec_summary(top_articles: list[dict], audience_id: str) -> dict:
    profile = AUDIENCE_PROFILES[audience_id]
    headlines = [a["title"][:70] for a in top_articles[:5]]
    bullets = [f"{h}..." for h in headlines] or ["No articles available for this period."]
    return {
        "bullets": bullets,
        "oci_implication_of_day": (
            f"[DRY RUN] Executive summary for {profile['name']} ({profile['title']}). "
            "Oracle Code Assist would synthesise today's top signals into a concrete strategic "
            "implication for OCI leadership."
        ),
    }


# ---------------------------------------------------------------------------
# Pipeline steps
# ---------------------------------------------------------------------------

def step_init_db() -> None:
    """Initialize database and seed sources."""
    print("\n[0/8] Initializing database...")
    engine = init_db()
    seed_sources()
    print("      → Database ready, sources seeded")


def step_ingest() -> list[dict]:
    print("\n[1/8] Ingesting RSS feeds...")
    articles = ingest_feeds()
    print(f"      → {len(articles)} articles ingested")
    return articles


def step_score(articles: list[dict]) -> list[dict]:
    print("\n[2/8] Scoring articles (7 dimensions) across all audiences...")
    articles = score_all_articles(articles)
    log_scores_to_db(articles)
    print(f"      → Scored {len(articles)} articles")
    return articles


def step_normalize(articles: list[dict]) -> list[dict]:
    print("\n[3/8] Normalizing and extracting entities...")
    articles = normalize_articles(articles)
    print(f"      → {len(articles)} articles normalized")
    return articles


def step_dedup(articles: list[dict]) -> list[dict]:
    print("\n[4/8] Running 5-stage dedup pipeline...")
    articles = run_dedup_pipeline(articles)
    print(f"      → {len(articles)} articles after dedup")
    return articles


def step_classify(articles: list[dict], dry_run: bool, no_cache: bool) -> list[dict]:
    """Classify top-N articles with Haiku (or placeholders in dry-run)."""
    print(f"\n[5/8] Classifying top {MAX_ARTICLES_TO_CLASSIFY} articles...")

    to_classify = get_top_articles_global(articles, n=MAX_ARTICLES_TO_CLASSIFY)

    if dry_run:
        for a in to_classify:
            a.update(DRY_RUN_CLASSIFICATION)
            if a.get("sections"):
                a["classified_section"] = a["sections"][0]
            else:
                a["classified_section"] = DRY_RUN_CLASSIFICATION["section"]
        print(f"      → [DRY RUN] Placeholder classification for {len(to_classify)} articles")
        return articles

    from app.llm.client import classify_article

    if no_cache:
        for f in CACHE_DIR.glob("*.json"):
            if f.name.startswith("classify_"):
                f.unlink()

    classified_count = 0
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_LLM) as pool:
        future_to_article = {
            pool.submit(classify_article, a): a for a in to_classify
        }
        for i, future in enumerate(as_completed(future_to_article), 1):
            article = future_to_article[future]
            try:
                result = future.result()
                article["topics"] = result.get("topics", [])
                article["entities"] = result.get("entities", [])
                article["confidence"] = result.get("confidence", "medium")
                llm_sections = result.get("sections", [])
                if llm_sections:
                    article["sections"] = llm_sections
                article["classified_section"] = result.get("section") or (
                    llm_sections[0] if llm_sections else
                    article["sections"][0] if article["sections"] else "other"
                )
                classified_count += 1
                print(f"      [{i}/{len(to_classify)}] {article['source']}: {article['title'][:60]}...")
            except Exception as exc:
                logger.warning("Classification failed for %s: %s", article["url"][:50], exc)
                article["classified_section"] = article["sections"][0] if article["sections"] else "other"
                article["confidence"] = "low"

    print(f"      → Classified {classified_count} articles")
    return articles


def step_generate_summaries(
    articles: list[dict],
    audience_ids: list[str],
    dry_run: bool,
    no_cache: bool,
) -> list[dict]:
    """Generate per-audience summaries for top articles."""
    print(f"\n[6/8] Generating article summaries (audiences: {', '.join(audience_ids)})...")

    if not dry_run:
        from app.llm.client import generate_summary
        if no_cache:
            for f in CACHE_DIR.glob("*.json"):
                if not f.name.startswith("classify_"):
                    f.unlink()

    total_generated = 0
    for aud_id in audience_ids:
        profile = AUDIENCE_PROFILES[aud_id]
        top_arts = get_top_articles_for_audience(articles, aud_id, n=TOP_ARTICLES_PER_AUDIENCE)
        print(f"\n      Audience: {profile['name']} — {len(top_arts)} articles")

        for i, article in enumerate(top_arts, 1):
            if dry_run:
                summary = _dry_run_summary(article, aud_id)
                total_generated += 1
            else:
                try:
                    summary = generate_summary(article, profile)
                    total_generated += 1
                    print(f"        [{i}/{len(top_arts)}] {article['title'][:55]}...")
                except Exception as exc:
                    logger.warning("Summary failed for %s / %s: %s", aud_id, article["url"][:40], exc)
                    summary = _dry_run_summary(article, aud_id)

            article.setdefault("per_audience_summaries", {})[aud_id] = summary

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
    print(f"\n[7/8] Generating executive summaries...")
    exec_summaries: dict[str, dict] = {}

    for aud_id in audience_ids:
        profile = AUDIENCE_PROFILES[aud_id]
        top_arts = get_top_articles_for_audience(articles, aud_id, n=TOP_ARTICLES_PER_AUDIENCE)

        if dry_run:
            exec_summaries[aud_id] = _dry_run_exec_summary(top_arts, aud_id)
            print(f"      [{aud_id}] [DRY RUN] placeholder executive summary")
        else:
            from app.llm.client import generate_executive_summary
            try:
                exec_summaries[aud_id] = generate_executive_summary(top_arts, profile)
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
    """Render HTML files and log to DB."""
    print(f"\n[8/8] Rendering HTML briefings...")

    all_audience_data: dict[str, dict] = {}
    for aud_id in audience_ids:
        top_arts = get_top_articles_for_audience(articles, aud_id, n=TOP_ARTICLES_PER_AUDIENCE)
        all_audience_data[aud_id] = {
            "articles":     top_arts,
            "exec_summary": exec_summaries.get(aud_id, {}),
            "nav_links":    "",
        }

    paths = save_briefings(all_audience_data, output_dir, generation_time)

    for key, path in paths.items():
        size_kb = path.stat().st_size // 1024
        print(f"      [{key}] {path}  ({size_kb} KB)")

    # Log briefings to DB
    _log_briefings_to_db(all_audience_data, audience_ids, generation_time)

    return paths


def _log_briefings_to_db(
    all_audience_data: dict,
    audience_ids: list[str],
    generation_time: datetime,
) -> None:
    """Log generated briefings to the audience_briefings table."""
    try:
        engine = init_db()
        session = get_session(engine)
        date_str = generation_time.strftime("%Y-%m-%d")

        for aud_id in audience_ids:
            data = all_audience_data.get(aud_id, {})
            articles = data.get("articles", [])

            briefing = AudienceBriefing(
                audience_id=aud_id,
                briefing_date=date_str,
                article_ids_json=[a.get("_db_id") or a.get("id") for a in articles],
                exec_summary_json=data.get("exec_summary", {}),
                generated_at=generation_time,
            )
            session.add(briefing)

        session.commit()
        session.close()
        logger.info("Logged %d briefings to DB", len(audience_ids))
    except Exception as exc:
        logger.warning("Failed to log briefings to DB: %s", exc)


# ---------------------------------------------------------------------------
# Synthetic fallback articles
# ---------------------------------------------------------------------------

def _synthetic_articles(generation_time: datetime) -> list[dict]:
    """Return realistic synthetic articles for dry-run / demo mode."""

    def make(title, source, tier, sections, summary, hours_ago=2):
        url = f"https://example.com/{hashlib.md5(title.encode()).hexdigest()[:8]}"
        return {
            "id":           hashlib.sha256(url.encode()).hexdigest()[:16],
            "title":        title,
            "url":          url,
            "summary":      summary,
            "published_at": generation_time - timedelta(hours=hours_ago),
            "source":       source,
            "source_domain": "example.com",
            "tier":         tier,
            "sections":     sections,
            "topics":       [],
            "entities":     [],
            "classified_section": sections[0] if sections else "other",
            "confidence":   "high",
            "scores":       {},
            "score_breakdowns": {},
            "per_audience_summaries": {},
        }

    return [
        make("NVIDIA Announces H200 Ultra GPU with 2x Training Throughput for Enterprise AI",
             "Reuters Tech", 1, ["ai", "compete", "financial"],
             "NVIDIA unveiled the H200 Ultra GPU claiming 2x training throughput over H100, targeting hyperscaler and enterprise AI workloads.",
             hours_ago=3),
        make("Microsoft Azure Signs $2.1B Multi-Year AI Infrastructure Deal with Saudi Aramco",
             "Reuters Business", 1, ["deals", "financial", "compete"],
             "Microsoft announced a $2.1 billion, 5-year agreement with Saudi Aramco to build AI-powered operations.",
             hours_ago=5),
        make("OpenAI Releases GPT-5 with Native Multimodal Reasoning",
             "TechCrunch", 2, ["ai", "compete"],
             "OpenAI released GPT-5 achieving state-of-the-art on 47 of 50 benchmarks. The model runs on Microsoft Azure exclusively at launch.",
             hours_ago=1),
        make("AWS Re:Invent Preview: Amazon to Announce Graviton5 Chips and 25% Price Cuts",
             "Ars Technica", 2, ["compete", "financial", "ai"],
             "Sources indicate AWS will announce Graviton5 ARM-based compute chips and across-the-board price reductions.",
             hours_ago=6),
        make("Google Deepens Partnership with SAP: All S/4HANA Workloads on GCP by 2027",
             "CloudWars", 2, ["compete", "deals", "multicloud"],
             "Google Cloud and SAP announced a deepened partnership for all SAP S/4HANA workloads on GCP by Q4 2027.",
             hours_ago=8),
        make("Data Center Power Crunch: Utilities Warn of 18-Month Wait for Grid Connections",
             "DC Dynamics", 2, ["datacenter", "power"],
             "Multiple US utilities are imposing 12-18 month queues for new large-scale power interconnections.",
             hours_ago=10),
        make("Oracle's Ellison Commits $20B to US AI Infrastructure in WH Meeting",
             "Reuters Business", 1, ["financial", "ai", "datacenter"],
             "Larry Ellison joined tech CEOs at the White House to announce $20B in planned US AI infrastructure investment.",
             hours_ago=2),
        make("Anthropic Claude 4 Achieves AGI-Level Coding: 72% on SWE-Bench Verified",
             "VentureBeat AI", 2, ["ai", "compete"],
             "Anthropic released Claude 4 with a 72% solve rate on SWE-Bench Verified, the highest score ever recorded.",
             hours_ago=4),
        make("Kubernetes 1.32 Drops Docker Runtime Support — Enterprise Upgrade Wave Expected",
             "Ars Technica", 2, ["oss", "infrastructure", "compete"],
             "The Kubernetes project officially removed the dockershim compatibility layer in v1.32.",
             hours_ago=14),
        make("Zero-Day in Linux Kernel Affects All Major Cloud Providers — Patch Available",
             "Reuters Tech", 1, ["security", "compete", "infrastructure"],
             "A critical zero-day vulnerability (CVE-2026-1337) in the Linux kernel affects all major cloud providers.",
             hours_ago=1),
        make("Meta Llama 4 Released as Open Source: 400B Parameter Model Free to Download",
             "TechCrunch", 2, ["ai", "oss", "compete"],
             "Meta released Llama 4, a 400B parameter open-source model, under a permissive commercial licence.",
             hours_ago=7),
        make("Show HN: Self-Hosted Kubernetes Cluster on OCI Always-Free Tier",
             "Hacker News", 4, ["community", "oss", "infrastructure"],
             "A developer shared a tutorial on running a 4-node Kubernetes cluster on OCI's Always-Free tier.",
             hours_ago=12),
        make("Microsoft and Oracle Extend Multi-Cloud Database Partnership to 10 New Regions",
             "OCI Blog", 3, ["partnerships", "multicloud", "deals"],
             "Oracle and Microsoft announced expansion of Oracle Database@Azure to 10 additional Azure regions.",
             hours_ago=9),
        make("EU AI Act Enforcement Begins: Cloud Providers Must Certify High-Risk AI Systems",
             "Reuters Tech", 1, ["security", "financial", "ai"],
             "The EU AI Act entered its first enforcement phase, requiring cloud providers to certify high-risk AI systems.",
             hours_ago=11),
        make("xAI Raises $6B Series D at $80B Valuation to Build Colossus-2 Supercluster",
             "TechCrunch", 2, ["financial", "ai", "datacenter"],
             "Elon Musk's xAI closed a $6 billion round at an $80 billion valuation to fund Colossus-2.",
             hours_ago=16),
    ]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="OCI AI Daily Executive Briefing Pipeline"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Skip LLM calls and use placeholder text"
    )
    parser.add_argument(
        "--audience", metavar="AUDIENCE_ID",
        choices=list(AUDIENCE_PROFILES.keys()),
        help="Run for a single audience (e.g. karan, nathan, greg, mahesh)"
    )
    parser.add_argument(
        "--date", metavar="YYYY-MM-DD",
        help="Override briefing date (default: today UTC)"
    )
    parser.add_argument(
        "--no-cache", action="store_true",
        help="Force LLM regeneration (ignore existing cache)"
    )
    args = parser.parse_args()

    dry_run  = args.dry_run
    no_cache = args.no_cache
    audience_ids = [args.audience] if args.audience else AUDIENCE_ORDER

    if args.date:
        try:
            generation_time = datetime.strptime(args.date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            print(f"ERROR: Invalid date format '{args.date}'. Use YYYY-MM-DD.")
            sys.exit(1)
    else:
        generation_time = datetime.now(tz=timezone.utc)

    date_str = generation_time.strftime("%Y-%m-%d")
    output_dir = OUTPUT_ROOT / date_str

    print("=" * 60)
    print(f"  OCI AI Daily Executive Briefing — {date_str}")
    print(f"  Audiences : {', '.join(audience_ids)}")
    print(f"  Dry run   : {'YES (no LLM calls)' if dry_run else 'NO'}")
    print(f"  Output    : {output_dir}")
    print("=" * 60)

    # ── 0. Init DB ────────────────────────────────────────────────────────
    step_init_db()

    # ── 1. Ingest ─────────────────────────────────────────────────────────
    articles = step_ingest()

    if not articles:
        print("\nWARNING: No articles ingested. Using synthetic demo articles...")
        articles = _synthetic_articles(generation_time)

    # ── 2. Score (7 dimensions) ───────────────────────────────────────────
    articles = step_score(articles)

    # ── 3. Normalize + Entity Extraction ──────────────────────────────────
    articles = step_normalize(articles)

    if not articles:
        print("ERROR: No articles after normalization. Exiting.")
        sys.exit(1)

    # ── 4. Dedup (5-stage pipeline) ───────────────────────────────────────
    articles = step_dedup(articles)

    # ── 5. Classify ───────────────────────────────────────────────────────
    articles = step_classify(articles, dry_run=dry_run, no_cache=no_cache)

    # ── 6. Generate summaries ─────────────────────────────────────────────
    articles = step_generate_summaries(articles, audience_ids, dry_run=dry_run, no_cache=no_cache)

    # ── 7. Executive summaries ────────────────────────────────────────────
    exec_summaries = step_executive_summaries(articles, audience_ids, dry_run=dry_run)

    # ── 8. Render ─────────────────────────────────────────────────────────
    paths = step_render(articles, audience_ids, exec_summaries, output_dir, generation_time)

    # ── Done ──────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  DONE")
    print(f"  Open: http://localhost:8000/{date_str}/index.html")
    print(f"  DB:   {OUTPUT_ROOT / 'briefing.db'}")
    print("  Run:  python3 scripts/serve.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
