"""
pipeline.py — 5-stage deduplication pipeline.

Stages:
  1. normalize  — Clean and tokenize titles/summaries
  2. cluster    — Group similar articles by keyword overlap
  3. compare    — Compute pairwise similarity within clusters
  4. detect_followup — Identify follow-up stories vs true duplicates
  5. suppress   — Mark duplicates for suppression, keep follow-ups with tags
"""

import logging
import re
from datetime import datetime, timezone
from typing import Optional

from app.db.models import (
    StoryCluster, SuppressionLog, Article,
    get_session, init_db,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Stage 1: Normalize
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> set[str]:
    """Return a set of lowercase word tokens."""
    return set(re.findall(r"[a-z]{3,}", text.lower()))


def _extract_entities(title: str) -> set[str]:
    """Extract likely entity names from title (capitalized words that aren't common)."""
    common = {
        "the", "a", "an", "is", "are", "was", "were", "has", "have", "had",
        "for", "and", "or", "but", "in", "on", "at", "to", "of", "by",
        "with", "from", "its", "as", "new", "how", "why", "what", "will",
        "can", "may", "all", "not",
    }
    entities = set()
    for w in title.split():
        clean = re.sub(r"[^a-zA-Z]", "", w)
        if clean and clean[0].isupper() and len(clean) > 1 and clean.lower() not in common:
            entities.add(clean.lower())
    return entities


def normalize_text(articles: list[dict]) -> list[dict]:
    """Add normalized tokens to each article."""
    for art in articles:
        combined = f"{art['title']} {art.get('summary', '')}"
        art["_tokens"] = _tokenize(combined)
        art["_title_tokens"] = _tokenize(art["title"])
        art["_entities"] = _extract_entities(art["title"])
    return articles


# ---------------------------------------------------------------------------
# Stage 2: Cluster
# ---------------------------------------------------------------------------

def cluster_articles(articles: list[dict]) -> list[list[dict]]:
    """
    Group articles into clusters based on token overlap and entity matching.

    Two articles are clustered together if ANY of these conditions hold:
      - Title-only Jaccard similarity > 30%
      - Combined (title + summary) Jaccard similarity > 25% AND they share >= 2 entities
      - They share >= 2 title entities
    """
    clusters: list[list[dict]] = []
    assigned: set[str] = set()

    for i, art in enumerate(articles):
        if art["url"] in assigned:
            continue

        cluster = [art]
        assigned.add(art["url"])

        for j, other in enumerate(articles):
            if j <= i or other["url"] in assigned:
                continue

            title_a = art.get("_title_tokens", set())
            title_b = other.get("_title_tokens", set())

            # Title-only Jaccard (lowered threshold)
            title_union = len(title_a | title_b)
            title_sim = len(title_a & title_b) / title_union if title_union else 0.0

            if title_sim > 0.50:
                cluster.append(other)
                assigned.add(other["url"])
                continue

            # Entity overlap — if 2+ shared entities, cluster immediately
            entities_a = art.get("_entities", set())
            entities_b = other.get("_entities", set())
            shared_entities = len(entities_a & entities_b)

            if shared_entities >= 2:
                cluster.append(other)
                assigned.add(other["url"])
                continue

            # Combined (title + summary) token Jaccard with entity boost
            combined_a = art.get("_title_tokens", set()) | art.get("_tokens", set())
            combined_b = other.get("_title_tokens", set()) | other.get("_tokens", set())
            combined_union = len(combined_a | combined_b)
            combined_sim = len(combined_a & combined_b) / combined_union if combined_union else 0.0

            if combined_sim > 0.25 and shared_entities >= 1:
                cluster.append(other)
                assigned.add(other["url"])
                continue

        clusters.append(cluster)

    logger.info("Clustered %d articles into %d clusters", len(articles), len(clusters))
    return clusters


# ---------------------------------------------------------------------------
# Stage 3: Compare
# ---------------------------------------------------------------------------

def compute_similarity(art_a: dict, art_b: dict) -> float:
    """Compute Jaccard similarity between two articles' full token sets."""
    tokens_a = art_a.get("_tokens", set())
    tokens_b = art_b.get("_tokens", set())
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = len(tokens_a & tokens_b)
    union = len(tokens_a | tokens_b)
    return intersection / union if union else 0.0


def compare_within_clusters(clusters: list[list[dict]]) -> list[list[dict]]:
    """Annotate each cluster with pairwise similarity scores."""
    for cluster in clusters:
        for i, art in enumerate(cluster):
            art["_cluster_similarities"] = {}
            for j, other in enumerate(cluster):
                if i == j:
                    continue
                sim = compute_similarity(art, other)
                art["_cluster_similarities"][other["url"]] = sim
    return clusters


# ---------------------------------------------------------------------------
# Stage 4: Detect Follow-ups
# ---------------------------------------------------------------------------

def detect_followups(clusters: list[list[dict]]) -> list[list[dict]]:
    """
    Within each cluster, distinguish:
    - Cross-source duplicates (>50% combined similarity, different source) → suppress
    - Same-source duplicates (>80% similarity) → suppress
    - Follow-ups (40-50/80% similarity + different publish time) → keep with tag
    """
    for cluster in clusters:
        if len(cluster) <= 1:
            continue

        # Sort by max score descending
        cluster.sort(
            key=lambda a: max(a.get("scores", {}).values(), default=0),
            reverse=True,
        )

        canonical = cluster[0]
        canonical["_is_canonical"] = True
        canonical["_suppressed"] = False

        for art in cluster[1:]:
            sims = art.get("_cluster_similarities", {})
            sim_to_canonical = sims.get(canonical["url"], 0.0)

            same_source = art.get("source") == canonical.get("source")

            if same_source and sim_to_canonical > 0.80:
                # Same-source true duplicate — suppress
                art["_suppressed"] = True
                art["_suppression_reason"] = "duplicate"
                art["_similarity_score"] = sim_to_canonical
            elif not same_source and sim_to_canonical > 0.65:
                # Cross-source duplicate covering the same event — suppress
                art["_suppressed"] = True
                art["_suppression_reason"] = "cross_source_duplicate"
                art["_similarity_score"] = sim_to_canonical
            elif sim_to_canonical > 0.40:
                # Follow-up — keep but tag
                art["_suppressed"] = False
                art["_is_followup"] = True
                art["_followup_of"] = canonical["url"]
            else:
                art["_suppressed"] = False

    return clusters


# ---------------------------------------------------------------------------
# Stage 5: Suppress & render follow-ups
# ---------------------------------------------------------------------------

def apply_suppressions(
    clusters: list[list[dict]],
    save_to_db: bool = True,
) -> list[dict]:
    """
    Flatten clusters back to a list, removing suppressed articles.
    Logs suppressions to the database.
    """
    kept: list[dict] = []
    suppressed: list[dict] = []

    for cluster in clusters:
        for art in cluster:
            if art.get("_suppressed", False):
                suppressed.append(art)
            else:
                kept.append(art)

    logger.info(
        "Dedup result: %d kept, %d suppressed",
        len(kept), len(suppressed),
    )

    # Persist suppressions to DB
    if save_to_db and suppressed:
        _persist_suppressions(suppressed, clusters)

    # Clean up internal fields
    for art in kept:
        for key in list(art.keys()):
            if key.startswith("_"):
                del art[key]

    return kept


def _persist_suppressions(suppressed: list[dict], clusters: list[list[dict]]) -> None:
    """Log suppressed articles to the suppression_log table."""
    try:
        engine = init_db()
        session = get_session(engine)

        for art in suppressed:
            db_art = session.query(Article).filter_by(url=art["url"]).first()
            if not db_art:
                continue

            log = SuppressionLog(
                article_id=db_art.id,
                reason=art.get("_suppression_reason", "duplicate"),
                similarity_score=art.get("_similarity_score", 0.0),
                matched_cluster_id=None,
                suppressed_at=datetime.now(timezone.utc),
            )
            session.add(log)

        session.commit()
        session.close()
    except Exception as exc:
        logger.warning("Failed to persist suppressions: %s", exc)


# ---------------------------------------------------------------------------
# Main pipeline entry point
# ---------------------------------------------------------------------------

def _embedding_dedup(articles: list[dict]) -> list[dict]:
    """
    Stage 6: Embedding-based same-day dedup.

    Catches articles from different sources covering the same event with
    different wording — cases that Jaccard misses.

    For each pair with cosine >= 0.85, keeps the higher-scored article
    and suppresses the other.
    """
    if len(articles) < 2:
        return articles

    import numpy as np
    from app.dedup.embeddings import compute_embeddings, batch_cosine_similarity

    # Compute embeddings for all articles
    texts = [f"{a['title']} {a.get('full_text', '') or a.get('summary', '')}" for a in articles]
    embeddings = compute_embeddings(texts)
    emb_matrix = np.array(embeddings, dtype=np.float32)

    # Find duplicates: for each article, check if a higher-scored article
    # already covers the same story (cosine >= 0.85)
    suppressed_indices: set[int] = set()
    THRESHOLD = 0.80

    for i in range(len(articles)):
        if i in suppressed_indices:
            continue
        vec = emb_matrix[i]
        sims = batch_cosine_similarity(vec, emb_matrix)

        for j in range(i + 1, len(articles)):
            if j in suppressed_indices:
                continue
            if sims[j] >= THRESHOLD:
                # Same story — keep the one with higher score
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

    kept = [a for idx, a in enumerate(articles) if idx not in suppressed_indices]
    logger.info("Embedding dedup: %d → %d (%d suppressed)", len(articles), len(kept), len(suppressed_indices))
    return kept


def run_dedup_pipeline(articles: list[dict], save_to_db: bool = True) -> list[dict]:
    """
    Run the full 6-stage dedup pipeline:
    1. normalize → 2. cluster → 3. compare → 4. detect_followup → 5. suppress
    → 6. embedding dedup (catches same-day cross-source duplicates)
    """
    logger.info("Starting dedup pipeline with %d articles", len(articles))

    # Stage 1: Normalize
    articles = normalize_text(articles)

    # Stage 2: Cluster
    clusters = cluster_articles(articles)

    # Stage 3: Compare within clusters
    clusters = compare_within_clusters(clusters)

    # Stage 4: Detect follow-ups
    clusters = detect_followups(clusters)

    # Stage 5: Apply suppressions
    kept = apply_suppressions(clusters, save_to_db=save_to_db)

    # Stage 6: Embedding-based dedup (catches paraphrased same-day duplicates)
    kept = _embedding_dedup(kept)

    # Sort by max score
    kept.sort(key=lambda a: max(a.get("scores", {}).values(), default=0), reverse=True)

    logger.info("Dedup pipeline complete: %d articles retained", len(kept))
    return kept
