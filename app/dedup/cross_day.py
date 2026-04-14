"""
Cross-day deduplication orchestration.

Queries the story_clusters table for recent clusters, compares new articles
against them using embedding similarity + fact delta, and persists results
(new clusters, updated clusters, or suppression logs).
"""

import json
import logging
import numpy as np
from datetime import datetime, timezone, timedelta

from app.db.models import StoryCluster, SuppressionLog, Article, get_session, init_db
from app.dedup.embeddings import batch_cosine_similarity
from app.dedup.fingerprint import compute_fact_delta, extract_facts

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------
HIGH_SIM_THRESHOLD = 0.95
MED_SIM_THRESHOLD = 0.75
LOW_DELTA = 0.20
HIGH_DELTA = 0.30


def load_recent_clusters(days: int = 7) -> list[dict]:
    """Load story clusters whose last_seen is within the last *days* days.

    Returns a list of dicts with keys:
        id, canonical_url, headline, embedding (list[float]), fact_snapshot (dict)
    Clusters with empty or unparseable embeddings are silently skipped.
    """
    session = None
    try:
        init_db()
        session = get_session()
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        rows = (
            session.query(StoryCluster)
            .filter(StoryCluster.last_seen > cutoff)
            .all()
        )

        clusters: list[dict] = []
        for row in rows:
            # Parse embedding -- skip clusters without a usable embedding
            raw_emb = row.cluster_embedding_json
            if not raw_emb:
                logger.debug("Skipping cluster %s: empty embedding", row.id)
                continue

            # cluster_embedding_json is stored as a JSON column (list of floats).
            # Depending on the driver it may already be a list or still a string.
            if isinstance(raw_emb, str):
                try:
                    embedding = json.loads(raw_emb)
                except (json.JSONDecodeError, TypeError):
                    logger.warning("Skipping cluster %s: malformed embedding JSON", row.id)
                    continue
            else:
                embedding = raw_emb

            if not isinstance(embedding, list) or len(embedding) == 0:
                logger.debug("Skipping cluster %s: embedding list is empty", row.id)
                continue

            # Parse fact_snapshot
            fact_snapshot: dict = {}
            if row.fact_snapshot:
                try:
                    fact_snapshot = (
                        json.loads(row.fact_snapshot)
                        if isinstance(row.fact_snapshot, str)
                        else row.fact_snapshot
                    )
                except (json.JSONDecodeError, TypeError):
                    logger.warning("Cluster %s has malformed fact_snapshot; treating as empty", row.id)

            clusters.append(
                {
                    "id": row.id,
                    "canonical_url": row.canonical_url,
                    "headline": row.headline,
                    "embedding": [float(v) for v in embedding],
                    "fact_snapshot": fact_snapshot,
                }
            )

        logger.info("Loaded %d recent clusters (within %d days)", len(clusters), days)
        return clusters

    except Exception:
        logger.exception("Failed to load recent clusters")
        return []
    finally:
        if session is not None:
            session.close()


def check_against_history(
    article: dict,
    article_embedding: list[float],
    clusters: list[dict],
) -> tuple[str, dict | None]:
    """Compare an article against historical clusters.

    Returns a tuple of (decision, matched_cluster_or_none) where decision is
    one of: "new", "suppress", "followup".

    Decision matrix (best-match cosine similarity vs. fact delta):
        cosine >= 0.95  and  delta < 0.20  -> suppress
        cosine >= 0.95  and  delta >= 0.30 -> followup
        cosine >= 0.75  and  delta < 0.20  -> suppress
        cosine >= 0.75  and  delta >= 0.30 -> followup
        cosine >= 0.75  and  0.20 <= delta < 0.30 -> suppress (minor variation)
        cosine < 0.75  -> new
    """
    if not clusters:
        logger.debug("No clusters to compare against; article is new")
        return ("new", None)

    # Build numpy matrix of cluster embeddings (N x D)
    cluster_embeddings = np.array([c["embedding"] for c in clusters], dtype=np.float32)
    query_vec = np.array(article_embedding, dtype=np.float32)

    similarities = batch_cosine_similarity(query_vec, cluster_embeddings)
    best_idx = int(np.argmax(similarities))
    best_score = float(similarities[best_idx])
    best_cluster = clusters[best_idx]

    cluster_label = best_cluster["id"] if best_cluster["id"] is not None else "in_memory"
    logger.info(
        "Best match for '%s': cluster %s ('%s') with cosine=%.4f",
        article.get("title", ""),
        cluster_label,
        best_cluster["headline"],
        best_score,
    )

    # Below medium threshold -> brand-new story
    if best_score < MED_SIM_THRESHOLD:
        return ("new", None)

    # Attach cosine score to cluster for logging
    best_cluster["_cosine_score"] = best_score

    # Compute fact delta between the cluster's snapshot and the incoming article
    fact_delta = compute_fact_delta(best_cluster["fact_snapshot"], article)
    logger.info(
        "Fact delta for article vs cluster %s: %.4f",
        cluster_label,
        fact_delta,
    )

    # Apply decision rules
    if fact_delta >= HIGH_DELTA:
        # Significant new facts -> follow-up regardless of sim tier
        return ("followup", best_cluster)

    if fact_delta < LOW_DELTA:
        # Very few new facts -> suppress
        return ("suppress", best_cluster)

    # 0.20 <= fact_delta < 0.30 -- minor variation, treat as suppress
    return ("suppress", best_cluster)


def save_new_cluster(article: dict, embedding: list[float], facts: dict) -> None:
    """Persist a brand-new story cluster derived from an article."""
    session = None
    try:
        init_db()
        session = get_session()
        now = datetime.now(timezone.utc)

        cluster = StoryCluster(
            canonical_url=article["url"],
            headline=article["title"],
            first_seen=now,
            last_seen=now,
            cluster_embedding_json=embedding,
            fact_snapshot=json.dumps(facts),
        )
        session.add(cluster)
        session.commit()
        logger.info("Saved new cluster for article '%s' (url=%s)", article["title"], article["url"])

    except Exception:
        logger.exception("Failed to save new cluster for article '%s'", article.get("title", "unknown"))
        if session is not None:
            session.rollback()
    finally:
        if session is not None:
            session.close()


def update_cluster_seen(cluster_id: int, new_facts: dict) -> None:
    """Update a cluster's last_seen timestamp and merge new facts into its snapshot.

    Fact merging strategy: for list-valued keys (numbers, entities, quotes),
    extend the existing list and deduplicate.  For other keys, overwrite with
    the new value only if non-empty.
    """
    session = None
    try:
        init_db()
        session = get_session()
        cluster = session.query(StoryCluster).filter_by(id=cluster_id).first()

        if cluster is None:
            logger.warning("update_cluster_seen: cluster %d not found", cluster_id)
            return

        cluster.last_seen = datetime.now(timezone.utc)

        # Parse existing fact_snapshot
        existing_facts: dict = {}
        if cluster.fact_snapshot:
            try:
                existing_facts = (
                    json.loads(cluster.fact_snapshot)
                    if isinstance(cluster.fact_snapshot, str)
                    else cluster.fact_snapshot
                )
            except (json.JSONDecodeError, TypeError):
                logger.warning("Cluster %d has malformed fact_snapshot; resetting", cluster_id)

        # Merge new_facts into existing_facts
        list_keys = {"numbers", "entities", "quotes"}
        for key, value in new_facts.items():
            if key in list_keys and isinstance(value, list):
                existing_list = existing_facts.get(key, [])
                if not isinstance(existing_list, list):
                    existing_list = []
                # Extend and deduplicate while preserving order
                seen = set()
                merged: list = []
                for item in existing_list + value:
                    # Use a hashable representation for dedup
                    item_key = json.dumps(item, sort_keys=True) if isinstance(item, dict) else item
                    if item_key not in seen:
                        seen.add(item_key)
                        merged.append(item)
                existing_facts[key] = merged
            elif value:
                existing_facts[key] = value

        cluster.fact_snapshot = json.dumps(existing_facts)
        session.commit()
        logger.info("Updated cluster %d: refreshed last_seen and merged facts", cluster_id)

    except Exception:
        logger.exception("Failed to update cluster %d", cluster_id)
        if session is not None:
            session.rollback()
    finally:
        if session is not None:
            session.close()
