"""
score.py — Article scoring engine.

Computes a relevance score per article per audience using:
  final_score = source_credibility + timeliness + section_relevance + keyword_bonus
"""

import logging
import re
from datetime import datetime, timezone

from briefing.config import (
    AUDIENCE_PROFILES,
    TIER_CREDIBILITY_SCORES,
    TIMELINESS_SCORES,
    OCI_KEYWORDS,
    MAX_KEYWORD_BONUS,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Sub-scores
# ---------------------------------------------------------------------------

def _source_credibility_score(tier: int) -> float:
    return float(TIER_CREDIBILITY_SCORES.get(tier, 0))


def _timeliness_score(published_at: datetime) -> float:
    now = datetime.now(tz=timezone.utc)
    age_hours = (now - published_at).total_seconds() / 3600
    for max_hours, pts in TIMELINESS_SCORES:
        if max_hours is None or age_hours < max_hours:
            return float(pts)
    return 0.0


def _section_relevance_score(article_sections: list[str], audience_weights: dict[str, float]) -> float:
    """
    For each section tag on the article, look up the audience's weight for that
    section. Sum of weights for matching sections, scaled to 0-40 range.
    """
    score = 0.0
    for section in article_sections:
        weight = audience_weights.get(section, 0.0)
        score += weight
    # Scale: max possible = 1.0 → map to 0-40 pts
    return score * 40.0


def _keyword_bonus(title: str, summary: str) -> float:
    """
    Check title + summary for relevant keywords.
    Returns a bonus capped at MAX_KEYWORD_BONUS.
    """
    combined = (title + " " + summary).lower()
    bonus = 0.0
    for keyword, pts in OCI_KEYWORDS.items():
        if keyword in combined:
            bonus += pts
    return min(bonus, MAX_KEYWORD_BONUS)


def _deal_size_bonus(title: str, summary: str) -> float:
    """
    Bonus for articles mentioning large dollar amounts.
    Articles about $1B+ deals, revenue, or investments get boosted.
    Returns 0-8 pts.
    """
    import re
    combined = (title + " " + summary).lower()
    # Match patterns like "$21 billion", "$15b", "$200 million", "21bn"
    amounts = re.findall(
        r'\$\s*([\d,.]+)\s*(billion|bn|b|trillion|tn|t)\b', combined
    )
    if not amounts:
        # Also match "X billion" without $ sign
        amounts = re.findall(
            r'([\d,.]+)\s*(billion|bn|b|trillion|tn|t)\s*(?:deal|revenue|investment|capex|funding|contract|agreement)',
            combined
        )
    if not amounts:
        return 0.0

    # Parse the largest amount
    max_val = 0
    for num_str, unit in amounts:
        try:
            val = float(num_str.replace(",", ""))
            if unit in ("trillion", "tn", "t"):
                val *= 1000
            max_val = max(max_val, val)
        except ValueError:
            pass

    if max_val >= 10:    # $10B+
        return 8.0
    elif max_val >= 1:   # $1B+
        return 5.0
    elif max_val >= 0.1: # $100M+
        return 2.0
    return 0.0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def score_article_for_audience(article: dict, audience_id: str) -> float:
    """Return a numeric score for a single article against one audience."""
    profile = AUDIENCE_PROFILES[audience_id]
    weights = profile["section_weights"]

    credibility = _source_credibility_score(article["tier"])
    timeliness  = _timeliness_score(article["published_at"])
    relevance   = _section_relevance_score(article["sections"], weights)
    keyword     = _keyword_bonus(article["title"], article.get("summary", ""))
    deal_size   = _deal_size_bonus(article["title"], article.get("summary", ""))

    total = credibility + timeliness + relevance + keyword + deal_size
    return round(total, 2)


def score_all_articles(articles: list[dict]) -> list[dict]:
    """
    Compute scores for every article against every audience.
    Mutates articles in-place, adding a `scores` dict: {audience_id: float}.
    Returns the articles list sorted by max score descending.
    """
    for article in articles:
        article["scores"] = {}
        for audience_id in AUDIENCE_PROFILES:
            article["scores"][audience_id] = score_article_for_audience(article, audience_id)

    articles.sort(key=lambda a: max(a["scores"].values(), default=0), reverse=True)
    logger.info("Scored %d articles across %d audiences", len(articles), len(AUDIENCE_PROFILES))
    return articles


def get_top_articles_for_audience(articles: list[dict], audience_id: str, n: int = 12) -> list[dict]:
    """Return top-N articles ranked for a specific audience."""
    sorted_articles = sorted(articles, key=lambda a: a["scores"].get(audience_id, 0), reverse=True)
    return sorted_articles[:n]


def get_top_articles_global(articles: list[dict], n: int = 60) -> list[dict]:
    """Return top-N articles by max score across all audiences (for classification)."""
    return articles[:n]  # already sorted by max score in score_all_articles
