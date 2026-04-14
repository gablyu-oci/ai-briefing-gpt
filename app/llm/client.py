"""
client.py — Codex / Oracle Code Assist integration with DB logging hooks.

Thin wrappers around `briefing.llm` so alternate app entrypoints share the
same Codex CLI prompts and cache behavior.
"""

import logging
from datetime import datetime, timezone

from briefing.llm import (
    classify_article as _classify_article,
    generate_executive_summary as _generate_executive_summary,
    generate_summary as _generate_summary,
)
from app.db.models import ProcessingLog, Article, get_session, init_db

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Article classification
# ---------------------------------------------------------------------------

def classify_article(article: dict) -> dict:
    """
    Classify an article using the shared Codex / Oracle Code Assist client and record
    the result in processing_log.
    """
    result = _classify_article(article)

    _log_processing(article, "classify", {}, result)
    return result


# ---------------------------------------------------------------------------
# Per-article summary
# ---------------------------------------------------------------------------

def generate_summary(article: dict, audience_profile: dict) -> dict:
    """
    Generate a personalized headline, summary, and OCI implication for one
    article using the shared Codex / Oracle Code Assist client.
    """
    return _generate_summary(article, audience_profile)


# ---------------------------------------------------------------------------
# Executive summary
# ---------------------------------------------------------------------------

def generate_executive_summary(top_articles: list[dict], audience_profile: dict) -> dict:
    """
    Generate a 3-5 bullet executive summary and OCI implication of the day.
    """
    return _generate_executive_summary(top_articles, audience_profile)


# ---------------------------------------------------------------------------
# Processing log helper
# ---------------------------------------------------------------------------

def _log_processing(article: dict, stage: str, input_snap: dict, output_snap: dict) -> None:
    """Log a processing step to the database."""
    try:
        engine = init_db()
        session = get_session(engine)
        db_art = session.query(Article).filter_by(url=article["url"]).first()
        if db_art:
            log = ProcessingLog(
                article_id=db_art.id,
                stage=stage,
                input_snapshot=input_snap,
                output_snapshot=output_snap,
                score_breakdown={},
                created_at=datetime.now(timezone.utc),
            )
            session.add(log)
            session.commit()
        session.close()
    except Exception as exc:
        logger.debug("Failed to log processing: %s", exc)
