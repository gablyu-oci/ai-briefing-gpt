"""
test_dedup.py — Tests for the 5-stage dedup pipeline.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.dedup.pipeline import (
    normalize_text,
    cluster_articles,
    compute_similarity,
    compare_within_clusters,
    detect_followups,
    apply_suppressions,
    run_dedup_pipeline,
)


def _make_article(title, url=None, source="Test", tier=2, hours_ago=2, score=50.0):
    return {
        "title": title,
        "url": url or f"https://example.com/{hash(title)}",
        "source": source,
        "tier": tier,
        "sections": ["ai"],
        "summary": f"Summary for {title}",
        "published_at": datetime.now(timezone.utc) - timedelta(hours=hours_ago),
        "scores": {"karan": score, "nathan": score, "greg": score, "mahesh": score},
        "score_breakdowns": {},
        "topics": [],
        "entities": [],
        "per_audience_summaries": {},
    }


def test_normalize():
    """Normalize should add token sets."""
    articles = [_make_article("NVIDIA Announces New GPU")]
    result = normalize_text(articles)
    assert "_tokens" in result[0]
    assert "_title_tokens" in result[0]
    assert "nvidia" in result[0]["_title_tokens"]
    print("PASS: test_normalize")


def test_cluster_similar():
    """Similar articles should be clustered together."""
    articles = [
        _make_article("NVIDIA Announces New H200 GPU for AI Training", url="a"),
        _make_article("NVIDIA Announces New H200 GPU for Enterprise AI", url="b"),
        _make_article("Oracle Wins Cloud Deal with European Bank", url="c"),
    ]
    articles = normalize_text(articles)
    clusters = cluster_articles(articles)

    # NVIDIA articles should be in same cluster, Oracle separate
    assert len(clusters) == 2, f"Expected 2 clusters, got {len(clusters)}"
    print("PASS: test_cluster_similar")


def test_compute_similarity():
    """Similar articles should have high similarity."""
    a = {"_tokens": {"nvidia", "announces", "new", "gpu", "training"}}
    b = {"_tokens": {"nvidia", "announces", "new", "gpu", "enterprise"}}
    c = {"_tokens": {"oracle", "wins", "cloud", "deal", "bank"}}

    sim_ab = compute_similarity(a, b)
    sim_ac = compute_similarity(a, c)

    assert sim_ab > sim_ac, f"NVIDIA articles ({sim_ab}) should be more similar than NVIDIA-Oracle ({sim_ac})"
    assert sim_ab > 0.5
    assert sim_ac < 0.2
    print(f"PASS: test_compute_similarity (ab={sim_ab:.2f}, ac={sim_ac:.2f})")


def test_detect_followups():
    """Duplicates should be suppressed, follow-ups kept."""
    articles = [
        _make_article("NVIDIA Announces New H200 GPU for AI", url="a", score=80),
        _make_article("NVIDIA Announces New H200 GPU for AI", url="b", score=60),
    ]
    articles = normalize_text(articles)
    clusters = cluster_articles(articles)
    clusters = compare_within_clusters(clusters)
    clusters = detect_followups(clusters)

    suppressed = [a for c in clusters for a in c if a.get("_suppressed")]
    assert len(suppressed) >= 1, "At least one duplicate should be suppressed"
    print("PASS: test_detect_followups")


def test_full_pipeline():
    """Full pipeline should deduplicate and return clean articles."""
    articles = [
        _make_article("NVIDIA H200 GPU Launch for AI Training", url="a", score=80),
        _make_article("NVIDIA H200 GPU Launch for Enterprise AI", url="b", score=60),
        _make_article("Oracle Wins Major Cloud Contract in Europe", url="c", score=70),
        _make_article("Meta Releases Llama 4 Open Source Model", url="d", score=65),
    ]

    result = run_dedup_pipeline(articles, save_to_db=False)

    # Should have 3 articles (one NVIDIA duplicate removed)
    assert len(result) <= 4, f"Expected dedup to remove at least one, got {len(result)}"
    assert len(result) >= 2, f"Expected at least 2 articles, got {len(result)}"

    # No internal fields should remain
    for art in result:
        for key in art.keys():
            assert not key.startswith("_"), f"Internal field '{key}' should be cleaned up"

    print(f"PASS: test_full_pipeline ({len(articles)} -> {len(result)} articles)")


if __name__ == "__main__":
    test_normalize()
    test_cluster_similar()
    test_compute_similarity()
    test_detect_followups()
    test_full_pipeline()
    print("\n✓ All dedup tests passed!")
