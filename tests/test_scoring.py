"""
test_scoring.py — Tests for the 7-dimension scoring engine.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Ensure project root on path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.scoring.engine import (
    score_source_credibility,
    score_audience_relevance,
    score_novelty,
    score_momentum,
    score_strategic_impact,
    score_timeliness,
    score_duplication_penalty,
    score_article_for_audience,
    score_all_articles,
)


def _make_article(title="Test Article", source="Reuters Tech", tier=1,
                   sections=None, summary="", hours_ago=2, url=None):
    """Helper to create a test article."""
    return {
        "title": title,
        "url": url or f"https://example.com/{hash(title)}",
        "source": source,
        "tier": tier,
        "sections": sections or ["ai", "compete"],
        "summary": summary,
        "published_at": datetime.now(timezone.utc) - timedelta(hours=hours_ago),
        "topics": [],
        "entities": [],
        "scores": {},
        "score_breakdowns": {},
        "per_audience_summaries": {},
    }


def test_source_credibility():
    """Tier 1 should score 30, Tier 4 should score 5."""
    assert score_source_credibility(1) == 30.0
    assert score_source_credibility(2) == 20.0
    assert score_source_credibility(3) == 10.0
    assert score_source_credibility(4) == 5.0
    assert score_source_credibility(99) == 0.0
    print("PASS: test_source_credibility")


def test_audience_relevance():
    """Section weights matching should produce scaled scores."""
    weights = {"ai": 0.35, "compete": 0.25, "financial": 0.15}
    assert score_audience_relevance(["ai"], weights) == 14.0  # 0.35 * 40
    assert score_audience_relevance(["ai", "compete"], weights) == 24.0  # (0.35+0.25)*40
    assert score_audience_relevance(["unknown"], weights) == 0.0
    print("PASS: test_audience_relevance")


def test_timeliness():
    """Fresh articles should score higher."""
    now = datetime.now(timezone.utc)
    assert score_timeliness(now - timedelta(hours=1)) == 15.0   # < 6h
    assert score_timeliness(now - timedelta(hours=8)) == 12.0   # < 12h
    assert score_timeliness(now - timedelta(hours=18)) == 8.0   # < 24h
    assert score_timeliness(now - timedelta(hours=36)) == 4.0   # < 48h
    assert score_timeliness(now - timedelta(hours=72)) == 0.0   # > 48h
    print("PASS: test_timeliness")


def test_strategic_impact():
    """OCI keywords should boost score."""
    assert score_strategic_impact("Oracle Cloud Infrastructure", "") >= 3.0
    assert score_strategic_impact("Random article about cooking", "") == 0.0
    assert score_strategic_impact("NVIDIA GPU H100 for AI training", "oracle cloud") >= 5.0
    print("PASS: test_strategic_impact")


def test_novelty():
    """Unique titles should score higher."""
    articles = [
        _make_article("NVIDIA announces new GPU for cloud computing", url="a"),
        _make_article("NVIDIA announces new GPU for AI workloads", url="b"),
        _make_article("Oracle wins cloud deal with European bank", url="c"),
    ]
    # The Oracle article is more unique vs NVIDIA articles
    novelty_nvidia = score_novelty(articles[0], articles)
    novelty_oracle = score_novelty(articles[2], articles)
    assert novelty_oracle > 0, "Oracle article should have some novelty"
    print("PASS: test_novelty")


def test_momentum():
    """Stories covered by multiple sources should score higher."""
    articles = [
        _make_article("NVIDIA H200 Ultra GPU launch", source="Reuters Tech", url="a"),
        _make_article("NVIDIA launches H200 Ultra GPU for AI", source="TechCrunch", url="b"),
        _make_article("NVIDIA H200 Ultra announced for enterprise", source="Ars Technica", url="c"),
        _make_article("Oracle wins cloud deal with European bank", source="Reuters Business", url="d"),
    ]
    momentum_nvidia = score_momentum(articles[0], articles)
    momentum_oracle = score_momentum(articles[3], articles)
    assert momentum_nvidia > momentum_oracle, "NVIDIA story covered by 3 sources should have more momentum"
    print("PASS: test_momentum")


def test_duplication_penalty():
    """Near-duplicate titles should be penalized."""
    articles = [
        _make_article("NVIDIA Announces New H200 GPU", url="a"),
        _make_article("NVIDIA Announces New H200 GPU for Enterprise", url="b"),
    ]
    penalty = score_duplication_penalty(articles[0], articles)
    assert penalty < 0, f"Expected negative penalty, got {penalty}"
    print("PASS: test_duplication_penalty")


def test_composite_scoring():
    """Full scoring pipeline should return reasonable total scores."""
    articles = [
        _make_article("Oracle Cloud wins $1B deal with Saudi Arabia",
                       summary="Oracle OCI sovereign cloud deal", hours_ago=1),
        _make_article("Random tech blog about JavaScript frameworks",
                       source="Hacker News", tier=4, sections=["community"],
                       summary="A blog post about React vs Vue", hours_ago=24),
    ]

    # Score for Karan (SVP Product, financial/compete focused)
    total1, breakdown1 = score_article_for_audience(articles[0], "karan", articles)
    total2, breakdown2 = score_article_for_audience(articles[1], "karan", articles)

    assert total1 > total2, f"Oracle deal ({total1}) should outscore JS blog ({total2}) for Karan"
    assert "source_credibility" in breakdown1
    assert "audience_relevance" in breakdown1
    assert "novelty" in breakdown1
    assert "momentum" in breakdown1
    assert "strategic_impact" in breakdown1
    assert "timeliness" in breakdown1
    assert "duplication_penalty" in breakdown1
    assert len(breakdown1) == 7, f"Expected 7 dimensions, got {len(breakdown1)}"
    print(f"PASS: test_composite_scoring (Oracle: {total1}, JS blog: {total2})")


def test_score_all_articles():
    """score_all_articles should populate scores for all audiences."""
    articles = [
        _make_article("NVIDIA H200 for AI", url="a"),
        _make_article("Oracle Cloud deal", url="b"),
    ]
    scored = score_all_articles(articles)
    assert len(scored) == 2
    for a in scored:
        assert "karan" in a["scores"]
        assert "nathan" in a["scores"]
        assert "greg" in a["scores"]
        assert "mahesh" in a["scores"]
        assert "karan" in a["score_breakdowns"]
    print("PASS: test_score_all_articles")


if __name__ == "__main__":
    test_source_credibility()
    test_audience_relevance()
    test_timeliness()
    test_strategic_impact()
    test_novelty()
    test_momentum()
    test_duplication_penalty()
    test_composite_scoring()
    test_score_all_articles()
    print("\n✓ All scoring tests passed!")
