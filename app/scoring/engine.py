"""
engine.py — Full 7-dimension article scoring engine.

Dimensions:
  1. source_credibility  — Tier-based trust score (0-30)
  2. audience_relevance  — Section weight match for this audience (0-40)
  3. novelty             — Keyword uniqueness bonus (0-10)
  4. momentum            — Multiple sources covering same story (0-10)
  5. strategic_impact    — OCI keyword relevance bonus (0-10)
  6. timeliness          — Freshness decay (0-15)
  7. duplication_penalty — Penalty for near-duplicate content (0 to -20)
"""

import logging
import re
from datetime import datetime, timezone

from config.audiences import AUDIENCE_PROFILES
from config.sources import (
    TIER_CREDIBILITY_SCORES,
    TIMELINESS_SCORES,
    OCI_KEYWORDS,
    MAX_KEYWORD_BONUS,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Dimension 1: Source Credibility (0-30)
# ---------------------------------------------------------------------------

def score_source_credibility(tier: int) -> float:
    """Score based on source tier. T1=30, T2=20, T3=10, T4=5."""
    return float(TIER_CREDIBILITY_SCORES.get(tier, 0))


# ---------------------------------------------------------------------------
# Dimension 2: Audience Relevance (0-40)
# ---------------------------------------------------------------------------

def score_audience_relevance(article_sections: list[str], audience_weights: dict[str, float]) -> float:
    """Sum of audience weights for matching sections, scaled to 0-40."""
    score = 0.0
    for section in article_sections:
        weight = audience_weights.get(section, 0.0)
        score += weight
    return score * 40.0


# ---------------------------------------------------------------------------
# Dimension 3: Novelty (0-10)
# ---------------------------------------------------------------------------

def score_novelty(article: dict, all_articles: list[dict]) -> float:
    """
    Score novelty: articles with unique title words get higher scores.
    Measures how different this article's title is from all others.
    """
    if not all_articles:
        return 5.0

    title_words = set(re.findall(r"[a-z]+", article["title"].lower()))
    if not title_words:
        return 0.0

    # Count how many other articles share words
    all_other_words = set()
    for other in all_articles:
        if other["url"] != article["url"]:
            all_other_words.update(re.findall(r"[a-z]+", other["title"].lower()))

    if not all_other_words:
        return 10.0

    unique_words = title_words - all_other_words
    novelty_ratio = len(unique_words) / len(title_words) if title_words else 0
    return round(novelty_ratio * 10.0, 2)


# ---------------------------------------------------------------------------
# Dimension 4: Momentum (0-10)
# ---------------------------------------------------------------------------

def score_momentum(article: dict, all_articles: list[dict]) -> float:
    """
    Score momentum: stories covered by multiple sources get a boost.
    Checks for title word overlap across different sources.
    """
    title_words = set(re.findall(r"[a-z]{4,}", article["title"].lower()))
    if not title_words:
        return 0.0

    covering_sources = set()
    for other in all_articles:
        if other["url"] == article["url"]:
            continue
        if other["source"] == article["source"]:
            continue
        other_words = set(re.findall(r"[a-z]{4,}", other["title"].lower()))
        overlap = len(title_words & other_words)
        if overlap >= 2:  # At least 2 significant words in common
            covering_sources.add(other["source"])

    # More sources = more momentum, cap at 10
    momentum = min(len(covering_sources) * 3.0, 10.0)
    return round(momentum, 2)


# ---------------------------------------------------------------------------
# Dimension 5: Strategic Impact (0-10)
# ---------------------------------------------------------------------------

def score_strategic_impact(title: str, summary: str) -> float:
    """OCI-relevant keyword bonus, capped at MAX_KEYWORD_BONUS."""
    combined = (title + " " + summary).lower()
    bonus = 0.0
    for keyword, pts in OCI_KEYWORDS.items():
        if keyword in combined:
            bonus += pts
    return min(bonus, MAX_KEYWORD_BONUS)


# ---------------------------------------------------------------------------
# Dimension 6: Timeliness (0-15)
# ---------------------------------------------------------------------------

def score_timeliness(published_at: datetime) -> float:
    """Score based on article age. Fresher = higher."""
    now = datetime.now(tz=timezone.utc)
    age_hours = (now - published_at).total_seconds() / 3600
    for max_hours, pts in TIMELINESS_SCORES:
        if max_hours is None or age_hours < max_hours:
            return float(pts)
    return 0.0


# ---------------------------------------------------------------------------
# Dimension 7: Duplication Penalty (0 to -20)
# ---------------------------------------------------------------------------

def score_duplication_penalty(article: dict, all_articles: list[dict]) -> float:
    """
    Penalize articles that are near-duplicates of higher-scored articles.
    Uses Jaccard similarity on title words.
    """
    title_words = set(re.findall(r"[a-z]+", article["title"].lower()))
    if not title_words:
        return 0.0

    max_similarity = 0.0
    for other in all_articles:
        if other["url"] == article["url"]:
            continue
        other_words = set(re.findall(r"[a-z]+", other["title"].lower()))
        if not other_words:
            continue
        intersection = len(title_words & other_words)
        union = len(title_words | other_words)
        similarity = intersection / union if union else 0.0
        if similarity > max_similarity:
            max_similarity = similarity

    # Penalty kicks in at >50% similarity, max -20 at 100%
    if max_similarity > 0.5:
        penalty = -((max_similarity - 0.5) / 0.5) * 20.0
        return round(penalty, 2)
    return 0.0


# ---------------------------------------------------------------------------
# Composite scoring
# ---------------------------------------------------------------------------

def score_article_for_audience(
    article: dict,
    audience_id: str,
    all_articles: list[dict] | None = None,
) -> tuple[float, dict]:
    """
    Compute the full 7-dimension score for an article against one audience.
    Returns (total_score, breakdown_dict).
    """
    profile = AUDIENCE_PROFILES[audience_id]
    weights = profile["section_weights"]
    all_arts = all_articles or []

    breakdown = {
        "source_credibility": score_source_credibility(article["tier"]),
        "audience_relevance": score_audience_relevance(article.get("sections", []), weights),
        "novelty": score_novelty(article, all_arts),
        "momentum": score_momentum(article, all_arts),
        "strategic_impact": score_strategic_impact(article["title"], article.get("summary", "")),
        "timeliness": score_timeliness(article["published_at"]),
        "duplication_penalty": score_duplication_penalty(article, all_arts),
    }

    total = sum(breakdown.values())
    return round(total, 2), breakdown


def score_all_articles(articles: list[dict]) -> list[dict]:
    """
    Compute scores for every article against every audience.
    Mutates articles in-place, adding 'scores' and 'score_breakdowns' dicts.
    Returns articles sorted by max score descending.
    """
    for article in articles:
        article["scores"] = {}
        article["score_breakdowns"] = {}
        for audience_id in AUDIENCE_PROFILES:
            total, breakdown = score_article_for_audience(article, audience_id, articles)
            article["scores"][audience_id] = total
            article["score_breakdowns"][audience_id] = breakdown

    articles.sort(key=lambda a: max(a["scores"].values(), default=0), reverse=True)
    logger.info("Scored %d articles across %d audiences (7 dimensions)", len(articles), len(AUDIENCE_PROFILES))
    return articles


def get_top_articles_for_audience(articles: list[dict], audience_id: str, n: int = 12) -> list[dict]:
    """Return top-N articles ranked for a specific audience."""
    sorted_articles = sorted(articles, key=lambda a: a["scores"].get(audience_id, 0), reverse=True)
    return sorted_articles[:n]


def get_top_articles_global(articles: list[dict], n: int = 60) -> list[dict]:
    """Return top-N articles by max score across all audiences."""
    return articles[:n]
