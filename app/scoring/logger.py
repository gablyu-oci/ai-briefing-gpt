"""
logger.py — Score logging to processing_log for full traceability.
"""

import logging
from datetime import datetime, timezone

from app.db.models import Article, ProcessingLog, get_session, init_db

logger = logging.getLogger(__name__)


def log_scores_to_db(articles: list[dict]) -> None:
    """
    Log per-dimension score breakdowns to the processing_log table.
    Each article gets one entry per audience with full breakdown.
    """
    try:
        engine = init_db()
        session = get_session(engine)

        logged = 0
        for art in articles:
            db_art = session.query(Article).filter_by(url=art["url"]).first()
            if not db_art:
                continue

            # Update raw_score on the article
            max_score = max(art.get("scores", {}).values(), default=0)
            db_art.raw_score = max_score

            breakdowns = art.get("score_breakdowns", {})
            for audience_id, breakdown in breakdowns.items():
                log_entry = ProcessingLog(
                    article_id=db_art.id,
                    stage="score",
                    input_snapshot={
                        "audience": audience_id,
                        "tier": art["tier"],
                        "sections": art.get("sections", []),
                    },
                    output_snapshot={
                        "total_score": art["scores"].get(audience_id, 0),
                    },
                    score_breakdown=breakdown,
                    created_at=datetime.now(timezone.utc),
                )
                session.add(log_entry)
                logged += 1

        session.commit()
        session.close()
        logger.info("Logged %d score breakdowns to processing_log", logged)

    except Exception as exc:
        logger.warning("Failed to log scores to DB: %s", exc)
