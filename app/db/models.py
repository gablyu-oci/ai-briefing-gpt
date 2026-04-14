"""
models.py — SQLAlchemy ORM models for the AI Daily Briefing system.

Tables: sources, articles, processing_log, story_clusters,
        audience_briefings, suppression_log
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, Text, Boolean, DateTime,
    ForeignKey, JSON, create_engine, event,
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

from config.settings import DATABASE_URL

Base = declarative_base()


class Source(Base):
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    domain = Column(String(255), unique=True, nullable=False)
    display_name = Column(String(255), nullable=False)
    tier = Column(Integer, nullable=False, default=2)
    credibility_score = Column(Float, nullable=False, default=20.0)
    rss_url = Column(Text, nullable=False)
    crawl_freq_mins = Column(Integer, default=60)
    active = Column(Boolean, default=True)

    articles = relationship("Article", back_populates="source_rel")

    def __repr__(self):
        return f"<Source {self.display_name} (T{self.tier})>"


class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(Text, unique=True, nullable=False)
    title = Column(Text, nullable=False)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=True)
    published_at = Column(DateTime, nullable=True)
    summary = Column(Text, default="")
    full_text = Column(Text, default="")
    tier = Column(Integer, default=2)
    raw_score = Column(Float, default=0.0)
    embedding_json = Column(JSON, nullable=True)  # 256-float embedding (nomic-embed-text-v1.5 Matryoshka)
    ingest_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    source_name = Column(String(255), nullable=True)

    # Relationships
    source_rel = relationship("Source", back_populates="articles")
    processing_logs = relationship("ProcessingLog", back_populates="article_rel")
    suppressions = relationship("SuppressionLog", back_populates="article_rel")

    def __repr__(self):
        return f"<Article {self.title[:50]}>"


class ProcessingLog(Base):
    __tablename__ = "processing_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False)
    stage = Column(String(50), nullable=False)  # ingest, score, classify, summarize, dedup
    input_snapshot = Column(JSON, default=dict)
    output_snapshot = Column(JSON, default=dict)
    score_breakdown = Column(JSON, default=dict)  # per-dimension scores for traceability
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    article_rel = relationship("Article", back_populates="processing_logs")

    def __repr__(self):
        return f"<ProcessingLog article={self.article_id} stage={self.stage}>"


class StoryCluster(Base):
    __tablename__ = "story_clusters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    canonical_url = Column(Text, nullable=False)
    headline = Column(Text, nullable=False)
    first_seen = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_seen = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    fact_snapshot = Column(Text, default="")
    cluster_embedding_json = Column(JSON, default=list)

    def __repr__(self):
        return f"<StoryCluster {self.headline[:50]}>"


class AudienceBriefing(Base):
    __tablename__ = "audience_briefings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    audience_id = Column(String(50), nullable=False)
    briefing_date = Column(String(10), nullable=False)  # YYYY-MM-DD
    article_ids_json = Column(JSON, default=list)
    exec_summary_json = Column(JSON, default=dict)
    generated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<AudienceBriefing {self.audience_id} {self.briefing_date}>"


class SuppressionLog(Base):
    __tablename__ = "suppression_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False)
    reason = Column(String(100), nullable=False)  # duplicate, low_score, stale, etc.
    similarity_score = Column(Float, default=0.0)
    matched_cluster_id = Column(Integer, ForeignKey("story_clusters.id"), nullable=True)
    suppressed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    article_rel = relationship("Article", back_populates="suppressions")

    def __repr__(self):
        return f"<SuppressionLog article={self.article_id} reason={self.reason}>"


# ---------------------------------------------------------------------------
# Engine & session factory
# ---------------------------------------------------------------------------

def get_engine(db_url: str | None = None):
    """Create SQLAlchemy engine. Uses DATABASE_URL from settings by default."""
    url = db_url or DATABASE_URL
    engine = create_engine(url, echo=False)
    # Enable WAL mode for better concurrent read performance on SQLite
    if url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    return engine


def get_session(engine=None):
    """Create a new session. If no engine provided, creates default."""
    if engine is None:
        engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()


def init_db(engine=None):
    """Create all tables if they don't exist."""
    if engine is None:
        engine = get_engine()
    Base.metadata.create_all(engine)
    return engine
