"""
test_cross_day_dedup.py — Tests for cross-day deduplication:
  - Fact extraction (numbers, entities, quotes)
  - Fact-delta scoring (same article, updated article)
  - Cosine threshold decisions (suppress, followup, new)
"""

import sys
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np

from app.dedup.fingerprint import extract_facts, compute_fact_delta
from app.dedup.cross_day import check_against_history


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_article(title, summary="", url=None, hours_ago=2):
    return {
        "title": title,
        "url": url or f"https://example.com/{hash(title) & 0xFFFFFFFF}",
        "summary": summary,
        "source": "Test Source",
        "tier": 2,
        "sections": ["ai"],
        "published_at": datetime.now(timezone.utc) - timedelta(hours=hours_ago),
        "scores": {"karan": 50.0},
        "topics": [],
        "entities": [],
        "per_audience_summaries": {},
    }


# ---------------------------------------------------------------------------
# test_extract_facts
# ---------------------------------------------------------------------------

def test_extract_facts():
    """Verify number, entity, and quote extraction from article text."""
    article = _make_article(
        title="Microsoft Acquires Activision Blizzard for $68.7 billion",
        summary=(
            'The deal valued at $68.7 billion was approved by the FTC. '
            'Bobby Kotick said "This is a transformative moment for gaming" '
            'and the European Commission also cleared the merger. '
            'Revenue is expected to grow 25% next quarter.'
        ),
    )
    facts = extract_facts(article)

    # Numbers: should find $68.7 billion, 25%
    assert len(facts["numbers"]) >= 2, f"Expected >=2 numbers, got {facts['numbers']}"

    # Entities: should find multi-word capitalized names
    assert len(facts["entities"]) >= 1, f"Expected >=1 entities, got {facts['entities']}"

    # Quotes: should find the Bobby Kotick quote
    assert len(facts["quotes"]) >= 1, f"Expected >=1 quotes, got {facts['quotes']}"

    print(f"PASS: test_extract_facts (numbers={facts['numbers']}, "
          f"entities={facts['entities'][:3]}, quotes={len(facts['quotes'])})")


# ---------------------------------------------------------------------------
# test_fact_delta_same_article
# ---------------------------------------------------------------------------

def test_fact_delta_same_article():
    """Same facts should produce a low delta (<0.20)."""
    article = _make_article(
        title="Microsoft Acquires Activision for $68.7 billion",
        summary="The deal valued at $68.7 billion marks a major shift.",
    )
    canonical_facts = extract_facts(article)
    # Add first_seen as now (no time gap)
    canonical_facts["first_seen"] = datetime.now(timezone.utc).isoformat()

    # Same article as candidate — delta should be very low
    delta = compute_fact_delta(canonical_facts, article)
    assert delta < 0.20, f"Same article delta should be <0.20, got {delta:.3f}"
    print(f"PASS: test_fact_delta_same_article (delta={delta:.3f})")


# ---------------------------------------------------------------------------
# test_fact_delta_update
# ---------------------------------------------------------------------------

def test_fact_delta_update():
    """New numbers and entities should produce a high delta (>0.30)."""
    original = _make_article(
        title="Microsoft Acquires Activision",
        summary="Microsoft is acquiring Activision in a major deal.",
        hours_ago=72,  # 3 days ago
    )
    canonical_facts = extract_facts(original)
    canonical_facts["first_seen"] = (
        datetime.now(timezone.utc) - timedelta(days=3)
    ).isoformat()

    # Updated article with new facts
    updated = _make_article(
        title="Microsoft Completes $68.7 billion Activision Deal After FTC Approval",
        summary=(
            'The European Commission and FTC approved the acquisition. '
            '"This deal will reshape the gaming industry" said Brad Smith. '
            'Revenue impact expected at $2.1 billion annually.'
        ),
        hours_ago=1,
    )

    delta = compute_fact_delta(canonical_facts, updated)
    assert delta > 0.30, f"Updated article delta should be >0.30, got {delta:.3f}"
    print(f"PASS: test_fact_delta_update (delta={delta:.3f})")


# ---------------------------------------------------------------------------
# test_cosine_threshold_suppress
# ---------------------------------------------------------------------------

def test_cosine_threshold_suppress():
    """High cosine + low fact delta → suppress."""
    article = _make_article(
        title="NVIDIA Announces H200 GPU",
        summary="NVIDIA unveiled the H200 GPU for AI training.",
    )

    # Create a fake cluster with nearly identical embedding
    base_embedding = list(np.random.randn(256).astype(float))
    # Use same embedding for article (cosine ~1.0)
    article_embedding = base_embedding.copy()

    cluster_facts = extract_facts(article)
    cluster_facts["first_seen"] = datetime.now(timezone.utc).isoformat()

    clusters = [{
        "id": 1,
        "canonical_url": "https://example.com/original",
        "headline": "NVIDIA Announces H200 GPU",
        "embedding": base_embedding,
        "fact_snapshot": cluster_facts,
    }]

    decision, matched = check_against_history(article, article_embedding, clusters)
    assert decision == "suppress", f"Expected 'suppress', got '{decision}'"
    assert matched is not None
    print(f"PASS: test_cosine_threshold_suppress (decision={decision})")


# ---------------------------------------------------------------------------
# test_cosine_threshold_followup
# ---------------------------------------------------------------------------

def test_cosine_threshold_followup():
    """Medium-high cosine + high fact delta → followup."""
    original = _make_article(
        title="Microsoft Acquires Activision",
        summary="Microsoft is acquiring Activision in a major deal.",
        hours_ago=72,
    )

    # Build an embedding with cosine ~0.85 (related but not identical)
    base_vec = np.random.randn(256)
    base_vec = base_vec / np.linalg.norm(base_vec)
    # Perturb to get cosine ~0.85
    noise = np.random.randn(256) * 0.4
    article_vec = base_vec + noise
    article_vec = article_vec / np.linalg.norm(article_vec)
    # Adjust to ensure cosine is in 0.75-0.95 range
    cosine = float(np.dot(base_vec, article_vec))
    # If cosine is too low or too high, blend more carefully
    if cosine < 0.75 or cosine >= 0.95:
        # Force cosine to ~0.85 by blending
        target_cos = 0.85
        article_vec = target_cos * base_vec + np.sqrt(1 - target_cos**2) * (
            noise / np.linalg.norm(noise)
        )
        article_vec = article_vec / np.linalg.norm(article_vec)

    canonical_facts = extract_facts(original)
    canonical_facts["first_seen"] = (
        datetime.now(timezone.utc) - timedelta(days=3)
    ).isoformat()

    clusters = [{
        "id": 1,
        "canonical_url": "https://example.com/original",
        "headline": "Microsoft Acquires Activision",
        "embedding": base_vec.tolist(),
        "fact_snapshot": canonical_facts,
    }]

    # Updated article with lots of new facts
    updated = _make_article(
        title="Microsoft Completes $68.7 billion Activision Deal After FTC Approval",
        summary=(
            'The $68.7 billion deal is now complete after FTC and EU approval. '
            '"A landmark moment" said Satya Nadella. Bobby Kotick will step down. '
            'Annual revenue impact: $2.1 billion. Shares rose 15%.'
        ),
        hours_ago=1,
    )

    decision, matched = check_against_history(updated, article_vec.tolist(), clusters)
    assert decision == "followup", f"Expected 'followup', got '{decision}'"
    assert matched is not None
    print(f"PASS: test_cosine_threshold_followup (decision={decision})")


# ---------------------------------------------------------------------------
# test_cosine_threshold_new
# ---------------------------------------------------------------------------

def test_cosine_threshold_new():
    """Low cosine → new story."""
    article = _make_article(
        title="Oracle Wins $2B Navy Contract",
        summary="Oracle has been awarded a $2 billion Navy cloud contract.",
    )

    # Completely different embedding (cosine near 0)
    base_embedding = np.random.randn(256)
    base_embedding = base_embedding / np.linalg.norm(base_embedding)
    # Orthogonal vector
    article_embedding = np.random.randn(256)
    article_embedding = article_embedding / np.linalg.norm(article_embedding)
    # Ensure low cosine by making them somewhat orthogonal
    # Subtract the component along base
    article_embedding = article_embedding - np.dot(article_embedding, base_embedding) * base_embedding
    article_embedding = article_embedding / np.linalg.norm(article_embedding)

    cluster_facts = {
        "numbers": ["68.7 billion"],
        "entities": ["Microsoft", "Activision"],
        "quotes": [],
        "first_seen": datetime.now(timezone.utc).isoformat(),
    }

    clusters = [{
        "id": 1,
        "canonical_url": "https://example.com/microsoft",
        "headline": "Microsoft Acquires Activision",
        "embedding": base_embedding.tolist(),
        "fact_snapshot": cluster_facts,
    }]

    decision, matched = check_against_history(
        article, article_embedding.tolist(), clusters
    )
    assert decision == "new", f"Expected 'new', got '{decision}'"
    assert matched is None
    print(f"PASS: test_cosine_threshold_new (decision={decision})")


def test_in_memory_cluster_logging_uses_string_label(caplog):
    """In-memory clusters should log with a string label instead of crashing."""
    article = _make_article(
        title="NVIDIA Announces H200 GPU",
        summary="NVIDIA unveiled the H200 GPU for AI training.",
    )

    embedding = list(np.random.randn(256).astype(float))
    cluster_facts = extract_facts(article)
    cluster_facts["first_seen"] = datetime.now(timezone.utc).isoformat()

    clusters = [{
        "id": None,
        "canonical_url": "https://example.com/original",
        "headline": "NVIDIA Announces H200 GPU",
        "embedding": embedding,
        "fact_snapshot": cluster_facts,
    }]

    with caplog.at_level(logging.INFO):
        decision, matched = check_against_history(article, embedding, clusters)

    assert decision == "suppress"
    assert matched is not None
    assert any(
        "Fact delta for article vs cluster in_memory" in rec.message
        for rec in caplog.records
    )
    print("PASS: test_in_memory_cluster_logging_uses_string_label")


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    test_extract_facts()
    test_fact_delta_same_article()
    test_fact_delta_update()
    test_cosine_threshold_suppress()
    test_cosine_threshold_followup()
    test_cosine_threshold_new()
    print("\n✓ All cross-day dedup tests passed!")
