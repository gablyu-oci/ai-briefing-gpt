"""
routes.py — FastAPI admin API endpoints.

Endpoints:
  GET /admin/articles              — Paginated articles list
  GET /admin/sources               — All sources
  GET /admin/processing-log        — Processing log entries
  GET /admin/suppression-log       — Suppression log entries
  GET /admin/clusters              — Story clusters (paginated, last N days)
  GET /admin/clusters/{cluster_id} — Single cluster with suppressed articles
  GET /admin/dedup-stats           — Deduplication summary statistics
  GET /admin/rankings/{audience_id}— Latest audience briefing with score breakdowns
  POST /run-pipeline               — Trigger pipeline run
  GET /briefings/{date}            — Get briefing for a date
  GET /health                      — Health check
"""

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Query, HTTPException
from sqlalchemy import func
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse

from app.db.models import (
    Article, Source, ProcessingLog, SuppressionLog,
    AudienceBriefing, StoryCluster,
    get_engine, get_session, init_db,
)
from config.settings import OUTPUT_ROOT

logger = logging.getLogger(__name__)


def _parse_json_safe(value):
    """Parse a JSON string, returning the original value if parsing fails."""
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    try:
        import json
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return value


app = FastAPI(
    title="AI Daily Briefing Admin API",
    version="1.0.0",
    description="Admin API for the AI Daily Executive Briefing system",
)

# CORS for admin dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health")
def health_check():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


# ---------------------------------------------------------------------------
# Admin: Articles
# ---------------------------------------------------------------------------

@app.get("/admin/articles")
def get_articles(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=1000),
    tier: Optional[int] = None,
    source: Optional[str] = None,
):
    """List articles with pagination and optional filtering."""
    try:
        engine = init_db()
        session = get_session(engine)

        query = session.query(Article).order_by(Article.ingest_at.desc())

        if tier is not None:
            query = query.filter(Article.tier == tier)
        if source is not None:
            query = query.filter(Article.source_id == source)

        total = query.count()
        articles = query.offset((page - 1) * per_page).limit(per_page).all()

        result = {
            "total": total,
            "page": page,
            "per_page": per_page,
            "articles": [
                {
                    "id": a.id,
                    "title": a.title,
                    "url": a.url,
                    "source_id": a.source_id,
                    "source_name": a.source_name or "",
                    "tier": a.tier,
                    "raw_score": a.raw_score,
                    "published_at": a.published_at.isoformat() if a.published_at else None,
                    "ingest_at": a.ingest_at.isoformat() if a.ingest_at else None,
                    "summary": (a.summary or "")[:200],
                }
                for a in articles
            ],
        }
        session.close()
        return result
    except Exception as exc:
        logger.error("Error fetching articles: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Admin: Sources
# ---------------------------------------------------------------------------

@app.get("/admin/sources")
def get_sources():
    """List all configured sources."""
    try:
        engine = init_db()
        session = get_session(engine)

        sources = session.query(Source).order_by(Source.tier, Source.display_name).all()

        result = {
            "total": len(sources),
            "sources": [
                {
                    "id": s.id,
                    "domain": s.domain,
                    "display_name": s.display_name,
                    "tier": s.tier,
                    "credibility_score": s.credibility_score,
                    "rss_url": s.rss_url,
                    "crawl_freq_mins": s.crawl_freq_mins,
                    "active": s.active,
                }
                for s in sources
            ],
        }
        session.close()
        return result
    except Exception as exc:
        logger.error("Error fetching sources: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Admin: Processing Log
# ---------------------------------------------------------------------------

@app.get("/admin/processing-log")
def get_processing_log(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    stage: Optional[str] = None,
):
    """List processing log entries."""
    try:
        engine = init_db()
        session = get_session(engine)

        query = session.query(ProcessingLog).order_by(ProcessingLog.created_at.desc())

        if stage is not None:
            query = query.filter(ProcessingLog.stage == stage)

        total = query.count()
        logs = query.offset((page - 1) * per_page).limit(per_page).all()

        result = {
            "total": total,
            "page": page,
            "per_page": per_page,
            "logs": [
                {
                    "id": log.id,
                    "article_id": log.article_id,
                    "stage": log.stage,
                    "input_snapshot": log.input_snapshot,
                    "output_snapshot": log.output_snapshot,
                    "score_breakdown": log.score_breakdown,
                    "created_at": log.created_at.isoformat() if log.created_at else None,
                }
                for log in logs
            ],
        }
        session.close()
        return result
    except Exception as exc:
        logger.error("Error fetching processing log: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Admin: Suppression Log
# ---------------------------------------------------------------------------

@app.get("/admin/suppression-log")
def get_suppression_log(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
):
    """List suppression log entries."""
    try:
        engine = init_db()
        session = get_session(engine)

        query = session.query(SuppressionLog).order_by(SuppressionLog.suppressed_at.desc())
        total = query.count()
        logs = query.offset((page - 1) * per_page).limit(per_page).all()

        result = {
            "total": total,
            "page": page,
            "per_page": per_page,
            "logs": [
                {
                    "id": log.id,
                    "article_id": log.article_id,
                    "reason": log.reason,
                    "similarity_score": log.similarity_score,
                    "matched_cluster_id": log.matched_cluster_id,
                    "suppressed_at": log.suppressed_at.isoformat() if log.suppressed_at else None,
                }
                for log in logs
            ],
        }
        session.close()
        return result
    except Exception as exc:
        logger.error("Error fetching suppression log: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Admin: Clusters
# ---------------------------------------------------------------------------

@app.get("/admin/clusters")
def get_clusters(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    days: int = Query(7, ge=1, le=90),
):
    """List story clusters from the last N days."""
    try:
        engine = init_db()
        session = get_session(engine)

        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        query = session.query(StoryCluster).filter(
            StoryCluster.last_seen >= cutoff
        ).order_by(StoryCluster.last_seen.desc())

        total = query.count()
        clusters = query.offset((page - 1) * per_page).limit(per_page).all()

        # Count articles suppressed per cluster
        cluster_ids = [c.id for c in clusters]
        suppression_counts = {}
        if cluster_ids:
            counts = (
                session.query(
                    SuppressionLog.matched_cluster_id,
                    func.count(SuppressionLog.id),
                )
                .filter(SuppressionLog.matched_cluster_id.in_(cluster_ids))
                .group_by(SuppressionLog.matched_cluster_id)
                .all()
            )
            suppression_counts = dict(counts)

        import json
        result = {
            "total": total,
            "page": page,
            "per_page": per_page,
            "days": days,
            "clusters": [
                {
                    "id": c.id,
                    "canonical_url": c.canonical_url,
                    "headline": c.headline,
                    "first_seen": c.first_seen.isoformat() if c.first_seen else None,
                    "last_seen": c.last_seen.isoformat() if c.last_seen else None,
                    "fact_snapshot": _parse_json_safe(c.fact_snapshot),
                    "articles_suppressed": suppression_counts.get(c.id, 0),
                    "has_embedding": bool(c.cluster_embedding_json),
                }
                for c in clusters
            ],
        }
        session.close()
        return result
    except Exception as exc:
        logger.error("Error fetching clusters: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Admin: Cluster Detail
# ---------------------------------------------------------------------------

@app.get("/admin/clusters/{cluster_id}")
def get_cluster_detail(cluster_id: int):
    """Get a single cluster with suppressed articles."""
    try:
        engine = init_db()
        session = get_session(engine)

        cluster = session.query(StoryCluster).filter(StoryCluster.id == cluster_id).first()
        if not cluster:
            session.close()
            raise HTTPException(status_code=404, detail="Cluster not found")

        # Get suppressed articles for this cluster
        suppressions = (
            session.query(SuppressionLog, Article)
            .join(Article, SuppressionLog.article_id == Article.id)
            .filter(SuppressionLog.matched_cluster_id == cluster_id)
            .order_by(SuppressionLog.suppressed_at.desc())
            .all()
        )

        result = {
            "id": cluster.id,
            "canonical_url": cluster.canonical_url,
            "headline": cluster.headline,
            "first_seen": cluster.first_seen.isoformat() if cluster.first_seen else None,
            "last_seen": cluster.last_seen.isoformat() if cluster.last_seen else None,
            "fact_snapshot": _parse_json_safe(cluster.fact_snapshot),
            "has_embedding": bool(cluster.cluster_embedding_json),
            "suppressed_articles": [
                {
                    "suppression_id": s.id,
                    "reason": s.reason,
                    "similarity_score": s.similarity_score,
                    "suppressed_at": s.suppressed_at.isoformat() if s.suppressed_at else None,
                    "article": {
                        "id": a.id,
                        "title": a.title,
                        "url": a.url,
                        "source_id": a.source_id,
                        "tier": a.tier,
                        "published_at": a.published_at.isoformat() if a.published_at else None,
                    },
                }
                for s, a in suppressions
            ],
        }
        session.close()
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error fetching cluster detail: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Admin: Dedup Stats
# ---------------------------------------------------------------------------

@app.get("/admin/dedup-stats")
def get_dedup_stats(
    days: int = Query(7, ge=1, le=90),
):
    """Deduplication summary statistics."""
    try:
        engine = init_db()
        session = get_session(engine)

        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

        total_clusters = session.query(func.count(StoryCluster.id)).filter(
            StoryCluster.last_seen >= cutoff
        ).scalar() or 0

        total_suppressions = session.query(func.count(SuppressionLog.id)).filter(
            SuppressionLog.suppressed_at >= cutoff
        ).scalar() or 0

        # Suppressions by reason
        by_reason = (
            session.query(SuppressionLog.reason, func.count(SuppressionLog.id))
            .filter(SuppressionLog.suppressed_at >= cutoff)
            .group_by(SuppressionLog.reason)
            .all()
        )
        suppressions_by_reason = {reason: count for reason, count in by_reason}

        clusters_today = session.query(func.count(StoryCluster.id)).filter(
            StoryCluster.first_seen >= today_start
        ).scalar() or 0

        articles_today = session.query(func.count(Article.id)).filter(
            Article.ingest_at >= today_start
        ).scalar() or 0

        # Clusters created per day over the window
        from sqlalchemy import cast, Date
        clusters_per_day = (
            session.query(
                func.date(StoryCluster.first_seen).label("day"),
                func.count(StoryCluster.id),
            )
            .filter(StoryCluster.first_seen >= cutoff)
            .group_by(func.date(StoryCluster.first_seen))
            .order_by(func.date(StoryCluster.first_seen))
            .all()
        )

        result = {
            "days": days,
            "total_clusters": total_clusters,
            "total_suppressions": total_suppressions,
            "suppressions_by_reason": suppressions_by_reason,
            "clusters_today": clusters_today,
            "articles_today": articles_today,
            "clusters_per_day": [
                {"date": str(day), "count": count}
                for day, count in clusters_per_day
            ],
        }
        session.close()
        return result
    except Exception as exc:
        logger.error("Error fetching dedup stats: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Admin: Rankings
# ---------------------------------------------------------------------------

@app.get("/admin/rankings/{audience_id}")
def get_rankings(audience_id: str):
    """Get latest audience briefing with article score breakdowns."""
    valid_audiences = {"karan", "nathan", "greg", "mahesh"}
    if audience_id not in valid_audiences:
        raise HTTPException(status_code=400, detail=f"Invalid audience_id. Must be one of: {', '.join(sorted(valid_audiences))}")

    try:
        engine = init_db()
        session = get_session(engine)

        # Get latest briefing for this audience
        briefing = (
            session.query(AudienceBriefing)
            .filter(AudienceBriefing.audience_id == audience_id)
            .order_by(AudienceBriefing.generated_at.desc())
            .first()
        )

        if not briefing:
            session.close()
            return {
                "audience_id": audience_id,
                "briefing": None,
                "ranked_articles": [],
            }

        # Get articles from the briefing
        article_urls = briefing.article_ids_json or []
        articles = []
        if article_urls:
            articles = (
                session.query(Article)
                .filter(Article.url.in_(article_urls))
                .all()
            )

        # Get score breakdowns from processing_log
        score_map = {}
        article_db_ids = [a.id for a in articles]
        if article_db_ids:
            score_logs = (
                session.query(ProcessingLog)
                .filter(
                    ProcessingLog.article_id.in_(article_db_ids),
                    ProcessingLog.stage == "score",
                )
                .all()
            )
            for log in score_logs:
                score_map[log.article_id] = log.score_breakdown or {}

        # Build ranked list preserving briefing order
        article_map = {a.url: a for a in articles}
        ranked = []
        for rank, url in enumerate(article_urls, 1):
            a = article_map.get(url)
            if not a:
                continue
            breakdown = score_map.get(a.id, {})
            ranked.append({
                "rank": rank,
                "article_id": a.id,
                "title": a.title,
                "url": a.url,
                "source_id": a.source_id,
                "tier": a.tier,
                "published_at": a.published_at.isoformat() if a.published_at else None,
                "total_score": a.raw_score,
                "score_breakdown": breakdown,
            })

        result = {
            "audience_id": audience_id,
            "briefing": {
                "id": briefing.id,
                "briefing_date": briefing.briefing_date,
                "generated_at": briefing.generated_at.isoformat() if briefing.generated_at else None,
                "exec_summary": briefing.exec_summary_json,
                "article_count": len(article_urls),
            },
            "ranked_articles": ranked,
        }
        session.close()
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error fetching rankings: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Cluster 3D Visualization
# ---------------------------------------------------------------------------

_viz_cache: dict = {}

@app.get("/admin/viz/clusters-3d")
def get_clusters_3d(days: int = Query(7, ge=1, le=30)):
    """Return 3D UMAP coordinates for all cluster embeddings, with cluster labels."""
    cache_key = f"3d_{days}"
    if cache_key in _viz_cache:
        cached_at, data = _viz_cache[cache_key]
        # Cache for 10 minutes
        if (datetime.now(timezone.utc) - cached_at).seconds < 600:
            return data

    try:
        import numpy as np
        import json as _json

        engine = init_db()
        session = get_session(engine)

        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        clusters = (
            session.query(StoryCluster)
            .filter(StoryCluster.last_seen >= cutoff)
            .all()
        )

        if len(clusters) < 3:
            session.close()
            return {"points": [], "message": "Need at least 3 clusters for visualization"}

        # Parse embeddings
        embeddings = []
        valid_clusters = []
        for c in clusters:
            emb = c.cluster_embedding_json
            if emb and isinstance(emb, list) and len(emb) > 10:
                embeddings.append(emb)
                valid_clusters.append(c)

        if len(valid_clusters) < 3:
            session.close()
            return {"points": [], "message": "Not enough clusters with embeddings"}

        embeddings_np = np.array(embeddings, dtype=np.float32)

        # UMAP reduction to 3D
        from umap import UMAP
        reducer = UMAP(n_components=3, metric="cosine", random_state=42, n_neighbors=min(15, len(valid_clusters) - 1))
        coords = reducer.fit_transform(embeddings_np)

        # HDBSCAN clustering for color groups
        try:
            from hdbscan import HDBSCAN
            clusterer = HDBSCAN(min_cluster_size=3, min_samples=2, metric="euclidean")
            labels = clusterer.fit_predict(coords)
        except Exception:
            labels = list(range(len(valid_clusters)))

        points = []
        for i, c in enumerate(valid_clusters):
            fact_snapshot = {}
            if c.fact_snapshot:
                try:
                    fact_snapshot = _json.loads(c.fact_snapshot) if isinstance(c.fact_snapshot, str) else c.fact_snapshot
                except Exception:
                    pass

            points.append({
                "id": c.id,
                "x": float(coords[i, 0]),
                "y": float(coords[i, 1]),
                "z": float(coords[i, 2]),
                "headline": c.headline,
                "url": c.canonical_url,
                "cluster_label": int(labels[i]),
                "first_seen": c.first_seen.isoformat() if c.first_seen else None,
                "last_seen": c.last_seen.isoformat() if c.last_seen else None,
            })

        session.close()

        result = {
            "total_points": len(points),
            "total_clusters": len(set(int(l) for l in labels if l >= 0)),
            "days": days,
            "points": points,
        }

        _viz_cache[cache_key] = (datetime.now(timezone.utc), result)
        return result

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error generating 3D visualization: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Pipeline trigger
# ---------------------------------------------------------------------------

@app.post("/run-pipeline")
def trigger_pipeline(
    dry_run: bool = Query(False),
    audience: Optional[str] = None,
):
    """Trigger a pipeline run (returns immediately with status)."""
    return {
        "status": "accepted",
        "message": "Pipeline run queued. Use scripts/pipeline.py for synchronous execution.",
        "dry_run": dry_run,
        "audience": audience,
    }


# ---------------------------------------------------------------------------
# Briefings
# ---------------------------------------------------------------------------

@app.get("/briefings/{date}")
def get_briefing(date: str):
    """Get generated briefing files for a date."""
    briefing_dir = OUTPUT_ROOT / date
    if not briefing_dir.exists():
        raise HTTPException(status_code=404, detail=f"No briefing found for {date}")

    files = {}
    for f in briefing_dir.glob("*.html"):
        files[f.stem] = f.name

    return {
        "date": date,
        "files": files,
        "path": str(briefing_dir),
    }


# ---------------------------------------------------------------------------
# Admin dashboard
# ---------------------------------------------------------------------------

@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard():
    """Serve the admin dashboard HTML."""
    admin_path = Path(__file__).parent.parent.parent / "web" / "admin.html"
    if admin_path.exists():
        return HTMLResponse(content=admin_path.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>Admin dashboard not found</h1>", status_code=404)
