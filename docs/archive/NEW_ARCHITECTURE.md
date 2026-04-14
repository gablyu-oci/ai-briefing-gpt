# AI Daily Executive Briefing -- New Layered Architecture

**Version:** 2.0
**Date:** 2026-03-11
**Status:** Approved for implementation
**Supersedes:** docs/ARCHITECTURE.md (v1.0)

---

## Table of Contents

1. [Directory Structure](#1-directory-structure)
2. [DB Schema](#2-db-schema)
3. [Interface Contracts](#3-interface-contracts)
4. [Scoring Engine Spec](#4-scoring-engine-spec)
5. [Dedup Pipeline Spec](#5-dedup-pipeline-spec)
6. [API Endpoints](#6-api-endpoints)
7. [Migration Plan](#7-migration-plan)

---

## 1. Directory Structure

```
ai-daily-briefing/
  app/
    __init__.py
    api/
      __init__.py
      routes.py              # FastAPI route definitions
      schemas.py             # Pydantic request/response models
    db/
      __init__.py
      engine.py              # SQLAlchemy engine + session factory
      models.py              # All ORM table definitions
      queries.py             # Reusable query helpers
    ingestion/
      __init__.py
      fetcher.py             # RSS feed fetching (ThreadPoolExecutor)
      registry.py            # Source registry loader (from config + DB)
      normalizer.py          # Feed entry normalization (HTML strip, date parse, ID gen)
    processing/
      __init__.py
      article_normalizer.py  # Section tag inference from keyword matching
      entity_extractor.py    # Simple regex-based NER (companies, products, regions, amounts)
    scoring/
      __init__.py
      engine.py              # Orchestrates all 7 dimensions per article per audience
      dimensions.py          # Individual dimension calculators
      weights.py             # Scoring constants and tier tables
    dedup/
      __init__.py
      normalizer.py          # Stage 1: tokenize, compute fact signature
      cluster.py             # Stage 2: cluster articles by title/entity overlap
      comparator.py          # Stage 3: compare against 7-day delivered window
      followup.py            # Stage 4: detect fact deltas for follow-up tagging
      renderer.py            # Stage 5: tag articles with novelty badges
    llm/
      __init__.py
      client.py              # Claude subprocess wrapper with retry + cache
      classify.py            # Article classification (Haiku)
      summarize.py           # Per-audience article summaries (Sonnet)
      executive.py           # Executive summary generation (Sonnet)
    rendering/
      __init__.py
      html_builder.py        # Per-audience HTML page assembly
      components.py          # Hero cards, story rows, section blocks, exec summary
      css.py                 # BASE_CSS and design tokens
    delivery/
      __init__.py
      email_sender.py        # Postmark-ready email interface (stub)
  web/
    admin.html               # Admin dashboard (static HTML + JS)
  config/
    __init__.py
    settings.py              # Environment variables, paths, pipeline tuning
    audiences.py             # AUDIENCE_PROFILES dict and AUDIENCE_ORDER
    sources.py               # RSS_SOURCES list and source metadata
  scripts/
    pipeline.py              # Main CLI runner (--dry-run --audience --date --no-cache)
    serve.py                 # FastAPI dev server + static file serving
  output/
    briefing.db              # SQLite database
    .cache/                  # LLM response cache (JSON files)
    YYYY-MM-DD/              # Generated HTML briefings per date
      index.html
      karan.html
      nathan.html
      greg.html
      mahesh.html
  tests/
    __init__.py
    conftest.py              # Shared fixtures (in-memory DB, sample articles)
    test_scoring.py
    test_dedup.py
    test_ingestion.py
  docs/
    PRD.md
    ARCHITECTURE.md
    NEW_ARCHITECTURE.md
  requirements.txt
```

### File Purposes

| File | Responsibility |
|------|---------------|
| `app/__init__.py` | Package marker; exports `__version__` |
| `app/api/routes.py` | All FastAPI endpoint handlers |
| `app/api/schemas.py` | Pydantic models for API request/response validation |
| `app/db/engine.py` | `create_engine()`, `SessionLocal`, `get_db()` dependency |
| `app/db/models.py` | All 6 SQLAlchemy ORM model classes |
| `app/db/queries.py` | Helper functions for common DB operations |
| `app/ingestion/fetcher.py` | Concurrent RSS fetch using ThreadPoolExecutor + feedparser |
| `app/ingestion/registry.py` | Merge config sources with DB sources table |
| `app/ingestion/normalizer.py` | HTML stripping, date parsing, article ID generation |
| `app/processing/article_normalizer.py` | Keyword-based section tag inference |
| `app/processing/entity_extractor.py` | Regex NER for companies, products, amounts |
| `app/scoring/engine.py` | `score_article_for_audience()`, `score_all_articles()` |
| `app/scoring/dimensions.py` | 7 dimension calculator functions |
| `app/scoring/weights.py` | TIER_CREDIBILITY, TIMELINESS_DECAY, OCI_KEYWORDS |
| `app/dedup/normalizer.py` | Tokenize titles, compute fact_signature hash |
| `app/dedup/cluster.py` | Group articles by Jaccard title similarity |
| `app/dedup/comparator.py` | Check against 7-day delivered window in DB |
| `app/dedup/followup.py` | Detect fact deltas to override suppression |
| `app/dedup/renderer.py` | Assign novelty_status and visual badges |
| `app/llm/client.py` | `call_claude()` subprocess wrapper with cache |
| `app/llm/classify.py` | `classify_article()` using Haiku |
| `app/llm/summarize.py` | `generate_summary()` using Sonnet |
| `app/llm/executive.py` | `generate_executive_summary()` using Sonnet |
| `app/rendering/html_builder.py` | `render_combined_html()`, `save_briefings()` |
| `app/rendering/components.py` | `render_hero_card()`, `render_story_row()`, etc. |
| `app/rendering/css.py` | `BASE_CSS` constant |
| `app/delivery/email_sender.py` | `send_briefing_email()` stub |
| `config/settings.py` | `SETTINGS` dataclass with all env/config |
| `config/audiences.py` | `AUDIENCE_PROFILES`, `AUDIENCE_ORDER` |
| `config/sources.py` | `RSS_SOURCES`, `TIER_CREDIBILITY_SCORES` |
| `scripts/pipeline.py` | CLI entry point with argparse |
| `scripts/serve.py` | FastAPI app factory + uvicorn launch |

---

## 2. DB Schema

Database: SQLite at `output/briefing.db`
ORM: SQLAlchemy 2.0 with declarative base

### 2.1 Full SQLAlchemy Model Definitions

```python
"""
app/db/models.py -- SQLAlchemy ORM models for the briefing system.

All tables use SQLite-compatible types. JSON columns are stored as TEXT
and handled via SQLAlchemy's JSON type adapter.
"""

import datetime
from sqlalchemy import (
    Column, Integer, Float, String, Text, Boolean, DateTime, Date,
    ForeignKey, JSON, Index, create_engine
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Source(Base):
    """RSS feed sources and their metadata."""
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    domain = Column(String(255), nullable=False, unique=True, index=True,
                    comment="Canonical domain (e.g. 'reuters.com')")
    display_name = Column(String(255), nullable=False,
                          comment="Human-readable name (e.g. 'Reuters Tech')")
    tier = Column(Integer, nullable=False,
                  comment="Source tier: 1=authoritative, 2=quality journalism, "
                          "3=domain-specific, 4=community")
    credibility_score = Column(Float, nullable=False, default=5.0,
                               comment="Static credibility score 0-10, derived from tier")
    rss_url = Column(Text, nullable=False,
                     comment="RSS/Atom feed URL")
    crawl_freq_mins = Column(Integer, nullable=False, default=60,
                             comment="Poll frequency in minutes")
    active = Column(Boolean, nullable=False, default=True,
                    comment="Whether this source is currently being polled")

    # Relationships
    articles = relationship("Article", back_populates="source_rel")

    def __repr__(self):
        return f"<Source(id={self.id}, display_name='{self.display_name}', tier={self.tier})>"


class Article(Base):
    """Ingested and normalized articles."""
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(Text, nullable=False, unique=True, index=True,
                 comment="Canonical article URL (deduplicated on this)")
    title = Column(Text, nullable=False)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=True,
                       comment="FK to sources table; null if source not in registry")
    published_at = Column(DateTime, nullable=True,
                          comment="Publication timestamp in UTC")
    summary = Column(Text, nullable=True,
                     comment="Extracted or feed-provided summary (max 1500 chars)")
    full_text = Column(Text, nullable=True,
                       comment="Full article body text if available")
    tier = Column(Integer, nullable=False, default=4,
                  comment="Source tier at time of ingestion")
    raw_score = Column(Float, nullable=True,
                       comment="Max-audience raw score after scoring pass")
    ingest_at = Column(DateTime, nullable=False,
                       default=lambda: datetime.datetime.now(datetime.timezone.utc),
                       comment="When this article was ingested into the system")

    # Enrichment columns (populated by processing stage)
    sections_json = Column(JSON, nullable=True, default=list,
                           comment="List of section tags inferred from content")
    entities_json = Column(JSON, nullable=True, default=dict,
                           comment="Extracted entities: {companies:[], products:[], ...}")
    topics_json = Column(JSON, nullable=True, default=list,
                         comment="LLM-classified topic tags")
    classified_section = Column(String(64), nullable=True,
                                comment="Primary section from LLM classification")
    confidence = Column(String(16), nullable=True,
                        comment="Classification confidence: high/medium/low")

    # Scoring columns (populated by scoring stage)
    scores_json = Column(JSON, nullable=True, default=dict,
                         comment="Per-audience scores: {audience_id: float}")
    score_breakdown_json = Column(JSON, nullable=True, default=dict,
                                  comment="Full 7-dimension breakdown per audience")

    # Dedup columns
    cluster_id = Column(Integer, ForeignKey("story_clusters.id"), nullable=True)
    novelty_status = Column(String(32), nullable=True,
                            comment="new|follow_up|candidate_duplicate|suppressed")

    # Relationships
    source_rel = relationship("Source", back_populates="articles")
    cluster = relationship("StoryCluster", back_populates="articles")
    processing_logs = relationship("ProcessingLog", back_populates="article")
    suppression_logs = relationship("SuppressionLog", back_populates="article")

    __table_args__ = (
        Index("idx_articles_published_at", "published_at"),
        Index("idx_articles_tier", "tier"),
        Index("idx_articles_ingest_at", "ingest_at"),
    )

    def __repr__(self):
        return f"<Article(id={self.id}, title='{self.title[:50]}...')>"


class ProcessingLog(Base):
    """
    Traceability log for every processing stage an article passes through.
    Records input state, output state, and score breakdowns for debugging.
    """
    __tablename__ = "processing_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False, index=True)
    stage = Column(String(64), nullable=False,
                   comment="Pipeline stage: ingest|process|score|classify|summarize|"
                           "dedup|render")
    input_snapshot = Column(JSON, nullable=True,
                            comment="Serialized article state before this stage")
    output_snapshot = Column(JSON, nullable=True,
                             comment="Serialized article state after this stage")
    score_breakdown = Column(JSON, nullable=True,
                             comment="7-dimension score breakdown if stage=score")
    created_at = Column(DateTime, nullable=False,
                        default=lambda: datetime.datetime.now(datetime.timezone.utc))

    # Relationships
    article = relationship("Article", back_populates="processing_logs")

    __table_args__ = (
        Index("idx_processing_log_stage", "stage"),
        Index("idx_processing_log_created_at", "created_at"),
    )

    def __repr__(self):
        return f"<ProcessingLog(id={self.id}, article_id={self.article_id}, stage='{self.stage}')>"


class StoryCluster(Base):
    """
    Canonical deduplicated story groups. Multiple articles covering the same
    event are grouped into one cluster with a canonical headline.
    """
    __tablename__ = "story_clusters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    canonical_url = Column(Text, nullable=True,
                           comment="URL of the highest-credibility article in cluster")
    headline = Column(Text, nullable=False,
                      comment="Best headline from cluster articles")
    first_seen = Column(DateTime, nullable=False,
                        default=lambda: datetime.datetime.now(datetime.timezone.utc),
                        comment="When the first article in this cluster was ingested")
    last_seen = Column(DateTime, nullable=False,
                       default=lambda: datetime.datetime.now(datetime.timezone.utc),
                       comment="When the most recent article was added")
    fact_snapshot = Column(JSON, nullable=True, default=dict,
                           comment="Current known facts: {capacity_mw, customer_name, "
                                   "deal_size, model_name, partner_name, region, date, status}")
    cluster_embedding_json = Column(JSON, nullable=True,
                                    comment="Serialized representative embedding vector "
                                            "for similarity search (list of floats)")
    article_count = Column(Integer, nullable=False, default=1)
    primary_topic = Column(String(64), nullable=True)
    novelty_status = Column(String(32), nullable=True,
                            comment="new|follow_up|candidate_duplicate|suppressed")

    # Relationships
    articles = relationship("Article", back_populates="cluster")
    suppression_logs = relationship("SuppressionLog", back_populates="cluster")

    __table_args__ = (
        Index("idx_story_clusters_last_seen", "last_seen"),
        Index("idx_story_clusters_headline", "headline"),
    )

    def __repr__(self):
        return f"<StoryCluster(id={self.id}, headline='{self.headline[:50]}...')>"


class AudienceBriefing(Base):
    """
    Records of generated briefings per audience per date. Stores the article
    selection and executive summary for audit and replay.
    """
    __tablename__ = "audience_briefings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    audience_id = Column(String(32), nullable=False, index=True,
                         comment="Audience key: karan|nathan|greg|mahesh")
    briefing_date = Column(Date, nullable=False, index=True,
                           comment="Date this briefing covers")
    article_ids_json = Column(JSON, nullable=False, default=list,
                              comment="Ordered list of article IDs selected for this briefing")
    exec_summary_json = Column(JSON, nullable=True,
                               comment="Executive summary: {bullets:[], "
                                       "oci_implication_of_day: str}")
    generated_at = Column(DateTime, nullable=False,
                          default=lambda: datetime.datetime.now(datetime.timezone.utc))

    __table_args__ = (
        Index("idx_audience_briefings_date_audience", "briefing_date", "audience_id",
              unique=True),
    )

    def __repr__(self):
        return (f"<AudienceBriefing(id={self.id}, audience_id='{self.audience_id}', "
                f"date={self.briefing_date})>")


class SuppressionLog(Base):
    """
    Records why an article was suppressed (not included in a briefing).
    Enables audit of dedup decisions and threshold tuning.
    """
    __tablename__ = "suppression_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False, index=True)
    reason = Column(String(128), nullable=False,
                    comment="Suppression reason: duplicate_no_delta|"
                            "below_score_threshold|negative_topic|"
                            "editorial_guardrail|cluster_already_delivered")
    similarity_score = Column(Float, nullable=True,
                              comment="Similarity to matched cluster (0.0-1.0)")
    matched_cluster_id = Column(Integer, ForeignKey("story_clusters.id"), nullable=True,
                                comment="Cluster that caused suppression")
    suppressed_at = Column(DateTime, nullable=False,
                           default=lambda: datetime.datetime.now(datetime.timezone.utc))

    # Relationships
    article = relationship("Article", back_populates="suppression_logs")
    cluster = relationship("StoryCluster", back_populates="suppression_logs")

    __table_args__ = (
        Index("idx_suppression_log_reason", "reason"),
        Index("idx_suppression_log_suppressed_at", "suppressed_at"),
    )

    def __repr__(self):
        return (f"<SuppressionLog(id={self.id}, article_id={self.article_id}, "
                f"reason='{self.reason}')>")
```

### 2.2 Engine and Session Setup

```python
"""
app/db/engine.py -- SQLAlchemy engine and session factory.
"""

from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.models import Base

DB_PATH = Path(__file__).parent.parent.parent / "output" / "briefing.db"

def get_engine(db_path: Path = DB_PATH):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(
        f"sqlite:///{db_path}",
        echo=False,
        connect_args={"check_same_thread": False},
    )

engine = get_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

def init_db():
    """Create all tables if they do not exist."""
    Base.metadata.create_all(bind=engine)

def get_db():
    """FastAPI dependency that yields a DB session and closes it after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### 2.3 Entity-Relationship Diagram

```
sources 1───* articles *───1 story_clusters
   |              |                |
   |              |                |
   |         processing_log   suppression_log
   |              |                |
   |              *                *
   |         (per-stage log)  (per-suppression)
   |
   |         audience_briefings
   |              |
   |         (per-audience-per-date)
```

---

## 3. Interface Contracts

Every public function is specified below with its full signature, parameter types, return type, and a one-line description.

### 3.1 `app/ingestion/fetcher.py`

```python
def fetch_feed(source: dict, cutoff: datetime) -> list[dict]:
    """Fetch a single RSS feed and return articles published after cutoff.

    Args:
        source: Dict with keys {url, name, tier, sections}.
        cutoff: UTC datetime; articles older than this are excluded.

    Returns:
        List of article dicts with keys: id, title, url, summary,
        published_at, source, tier, sections.
    """

def ingest_feeds(
    sources: list[dict] | None = None,
    window_hours: int = 48,
) -> list[dict]:
    """Fetch all RSS sources concurrently, deduplicate by URL,
    and return articles from the last window_hours.

    Args:
        sources: Override source list (default: config.RSS_SOURCES).
        window_hours: Only include articles published within this window.

    Returns:
        Flat list of deduplicated article dicts.
    """
```

### 3.2 `app/ingestion/registry.py`

```python
def load_sources(db_session=None) -> list[dict]:
    """Merge config/sources.py with sources DB table.

    Returns active sources. DB entries take precedence over config
    when domain matches.

    Args:
        db_session: Optional SQLAlchemy session. If None, uses config only.

    Returns:
        List of source dicts with keys: url, name, tier, sections,
        credibility_score, crawl_freq_mins, active.
    """

def sync_sources_to_db(db_session, sources: list[dict]) -> int:
    """Upsert config sources into the sources table.

    Returns:
        Number of rows upserted.
    """
```

### 3.3 `app/ingestion/normalizer.py`

```python
def strip_html(raw: str) -> str:
    """Remove HTML tags and collapse whitespace."""

def parse_date(entry) -> datetime | None:
    """Extract UTC datetime from a feedparser entry."""

def make_article_id(url: str) -> str:
    """Return a 16-char SHA-256 hex digest of the URL."""

def normalize_entry(entry, source: dict, cutoff: datetime) -> dict | None:
    """Transform a feedparser entry into a normalized article dict.

    Returns None if the entry should be skipped (no URL, no title,
    or published before cutoff).
    """
```

### 3.4 `app/processing/article_normalizer.py`

```python
SECTION_KEYWORDS: dict[str, list[str]]
    # Mapping of section name to keyword lists for inference.

def infer_sections(article: dict) -> list[str]:
    """Scan title+summary for keywords and return merged section tags.

    Args:
        article: Dict with keys title, summary, sections.

    Returns:
        Sorted, deduplicated list of section tag strings.
    """

def normalize_articles(raw_articles: list[dict]) -> list[dict]:
    """Enrich section tags, deduplicate, sort by max score, return top 40.

    Must be called AFTER score_all_articles() so scores are available.

    Args:
        raw_articles: Articles with scores populated.

    Returns:
        Top 40 articles sorted by max-audience score descending.
    """
```

### 3.5 `app/processing/entity_extractor.py`

```python
# Regex patterns for entity extraction
COMPANY_PATTERNS: list[tuple[str, str]]  # (pattern, normalized_name)
AMOUNT_PATTERN: re.Pattern               # Matches "$X.XB", "$X.XM" etc.
REGION_PATTERNS: list[tuple[str, str]]   # (pattern, normalized_region)

def extract_entities(title: str, summary: str) -> dict:
    """Extract named entities using regex patterns.

    Returns:
        Dict with keys: companies (list[str]), products (list[str]),
        amounts (list[str]), regions (list[str]).
    """

def extract_event_verb(title: str, summary: str) -> str | None:
    """Identify the primary event verb from title+summary.

    Returns one of: launched, partnered, raised, expanded, delayed,
    announced, shipped, confirmed, denied, acquired, signed, or None.
    """
```

### 3.6 `app/scoring/engine.py`

```python
def score_article_for_audience(article: dict, audience_id: str) -> float:
    """Compute the final 7-dimension score for one article against one audience.

    Returns:
        Numeric score (can be negative due to duplication_penalty).
    """

def score_all_articles(articles: list[dict]) -> list[dict]:
    """Score every article against every audience. Mutates articles in-place,
    adding scores dict and score_breakdown dict. Returns sorted by max score.
    """

def get_top_articles_for_audience(
    articles: list[dict], audience_id: str, n: int = 12
) -> list[dict]:
    """Return top-N articles ranked for a specific audience."""

def get_top_articles_global(articles: list[dict], n: int = 60) -> list[dict]:
    """Return top-N articles by max score across all audiences."""
```

### 3.7 `app/scoring/dimensions.py`

```python
def source_credibility(tier: int) -> float:
    """Map source tier to credibility score (0-10 scale)."""

def audience_relevance(
    article: dict, audience_profile: dict
) -> float:
    """Compute audience relevance from section weights, keyword match,
    company match, and topic match (0-10 scale)."""

def novelty(article: dict, cluster: dict | None, days_window: int = 7) -> float:
    """Compute novelty score based on similarity to delivered clusters (0-10)."""

def momentum(article: dict, cluster_article_count: int = 1) -> float:
    """Compute momentum from cross-source coverage count (0-10)."""

def strategic_impact(title: str, summary: str, keywords: dict) -> float:
    """Compute strategic impact from OCI keyword density (0-10)."""

def timeliness(published_at: datetime) -> float:
    """Compute timeliness score from article age (0-10)."""

def duplication_penalty(novelty_score: float) -> float:
    """Compute penalty based on novelty score (0-10, subtracted from total)."""
```

### 3.8 `app/scoring/weights.py`

```python
# Tier-to-credibility mapping (0-10 scale)
TIER_CREDIBILITY: dict[int, float]  # {1: 10.0, 2: 7.5, 3: 5.0, 4: 2.5}

# Timeliness decay brackets
TIMELINESS_BRACKETS: list[tuple[int | None, float]]
    # [(6, 10.0), (24, 8.0), (48, 6.0), (96, 4.0), (168, 2.0), (None, 0.0)]

# OCI strategic keywords and their point values
OCI_KEYWORDS: dict[str, int]

# Max values for each dimension
MAX_KEYWORD_BONUS: float  # 10.0
MAX_DIMENSION_SCORE: float  # 10.0
```

### 3.9 `app/dedup/normalizer.py`

```python
def tokenize(text: str) -> set[str]:
    """Return a set of lowercase alphabetic tokens."""

def compute_fact_signature(article: dict) -> str:
    """Hash key structured fields (entities + event verb + amounts)
    into a 32-char hex digest for exact-match dedup."""

def normalize_for_dedup(article: dict) -> dict:
    """Add tokens, fact_signature, and normalized title to article dict."""
```

### 3.10 `app/dedup/cluster.py`

```python
def title_similarity(a: dict, b: dict) -> float:
    """Jaccard similarity between tokenized titles (0.0-1.0)."""

def entity_overlap(a: dict, b: dict) -> float:
    """Jaccard similarity between extracted entity sets (0.0-1.0)."""

def cluster_articles(
    articles: list[dict],
    title_threshold: float = 0.60,
    entity_threshold: float = 0.50,
) -> list[list[dict]]:
    """Group articles into clusters based on title and entity similarity.

    Returns:
        List of clusters, where each cluster is a list of article dicts.
    """

def assign_clusters_to_db(
    db_session, clusters: list[list[dict]]
) -> list[int]:
    """Create or update StoryCluster rows. Returns list of cluster IDs."""
```

### 3.11 `app/dedup/comparator.py`

```python
def get_delivered_clusters(
    db_session, days: int = 7
) -> list[dict]:
    """Fetch all story clusters delivered in the past N days.

    Returns:
        List of cluster dicts with id, headline, fact_snapshot,
        last_seen, article_count.
    """

def compare_against_delivered(
    article: dict,
    delivered_clusters: list[dict],
    similarity_threshold: float = 0.80,
) -> tuple[str, float | None, int | None]:
    """Compare an article against delivered clusters.

    Returns:
        Tuple of (status, similarity_score, matched_cluster_id) where
        status is 'new', 'candidate_duplicate', or 'follow_up'.
    """
```

### 3.12 `app/dedup/followup.py`

```python
FACT_FIELDS: list[str]
    # ['capacity_mw', 'customer_name', 'deal_size', 'model_name',
    #  'partner_name', 'region', 'date', 'status']

def extract_facts(article: dict) -> dict:
    """Extract structured facts from article using regex heuristics.

    Returns:
        Dict with FACT_FIELDS as keys, values or None.
    """

def detect_fact_delta(
    new_facts: dict,
    prior_snapshot: dict,
) -> tuple[bool, list[str]]:
    """Compare new facts against prior cluster snapshot.

    Returns:
        Tuple of (has_delta: bool, changed_fields: list[str]).
    """

def classify_followup(
    article: dict,
    matched_cluster: dict,
) -> str:
    """Determine if a candidate_duplicate is actually a follow-up.

    Returns:
        'follow_up' if fact delta detected, 'suppressed' otherwise.
    """
```

### 3.13 `app/dedup/renderer.py`

```python
NOVELTY_BADGES: dict[str, dict]
    # {'new': {'label': '', 'css_class': ''},
    #  'follow_up': {'label': 'UPDATE', 'css_class': 'badge-update'},
    #  'major_update': {'label': 'MAJOR UPDATE', 'css_class': 'badge-major'},
    #  'suppressed': {'label': '', 'css_class': ''}}

def tag_novelty(
    articles: list[dict],
    db_session=None,
) -> list[dict]:
    """Run the full 5-stage dedup pipeline on a list of articles.

    Mutates articles in-place, adding novelty_status and novelty_badge.
    Logs suppressed articles to suppression_log table.

    Returns:
        Articles with novelty_status != 'suppressed'.
    """
```

### 3.14 `app/llm/client.py`

```python
HAIKU_MODEL: str   # "claude-haiku-4-5"
SONNET_MODEL: str  # "claude-sonnet-4-6"
MAX_RETRIES: int   # 3
RETRY_BACKOFF: float  # 2.0

def call_claude(
    prompt: str,
    model: str = SONNET_MODEL,
    timeout: int = 120,
) -> str:
    """Invoke claude CLI as subprocess with CLAUDECODE unset.

    Retries up to MAX_RETRIES with exponential backoff.

    Raises:
        RuntimeError: After all retries exhausted.
    """

def cache_get(key: str) -> Any | None:
    """Read cached LLM response from output/.cache/{key}.json."""

def cache_set(key: str, value: Any) -> None:
    """Write LLM response to cache."""

def cache_key(text: str) -> str:
    """SHA-256 hash prefix for cache filename."""
```

### 3.15 `app/llm/classify.py`

```python
def classify_article(article: dict, use_cache: bool = True) -> dict:
    """Classify article topics, entities, section, and confidence using Haiku.

    Args:
        article: Dict with keys title, url, source, summary.
        use_cache: If True, return cached result when available.

    Returns:
        Dict with keys: topics (list[str]), entities (list[str]),
        section (str), confidence (str: high|medium|low).
    """
```

### 3.16 `app/llm/summarize.py`

```python
def generate_summary(
    article: dict,
    audience_profile: dict,
    use_cache: bool = True,
) -> dict:
    """Generate a personalized headline, summary, and OCI implication
    for one article using Sonnet.

    Returns:
        Dict with keys: headline (str), summary (str),
        oci_implication (str).
    """
```

### 3.17 `app/llm/executive.py`

```python
def generate_executive_summary(
    top_articles: list[dict],
    audience_profile: dict,
    use_cache: bool = True,
) -> dict:
    """Generate 3-5 bullet executive summary and OCI Implication of the Day.

    Returns:
        Dict with keys: bullets (list[str]),
        oci_implication_of_day (str).
    """
```

### 3.18 `app/rendering/html_builder.py`

```python
def render_combined_html(
    all_audience_data: dict[str, dict],
    generation_time: datetime | None = None,
) -> str:
    """Render a multi-audience HTML page with tab switching.

    Args:
        all_audience_data: {audience_id: {articles, exec_summary}}.

    Returns:
        Complete HTML string.
    """

def render_single_audience_html(
    audience_id: str,
    articles: list[dict],
    exec_summary: dict,
    generation_time: datetime | None = None,
) -> str:
    """Render a single-audience HTML page."""

def save_briefings(
    all_audience_data: dict[str, dict],
    output_dir: Path,
    generation_time: datetime | None = None,
) -> dict[str, Path]:
    """Write per-audience HTML files and combined index.html.

    Returns:
        Dict mapping audience_id (and 'index') to file paths.
    """
```

### 3.19 `app/rendering/components.py`

```python
def render_hero_card(article: dict, audience_id: str) -> str:
    """Render a hero card with image for the top article in a section."""

def render_story_row(article: dict, audience_id: str) -> str:
    """Render a compact text-only story row."""

def render_section(
    section: str, articles: list[dict], audience_id: str
) -> str:
    """Render a complete section block with header, hero, and rows."""

def render_exec_summary(
    exec_data: dict, audience_id: str, articles: list[dict]
) -> str:
    """Render the executive summary cover block."""

def render_masthead(generation_time: datetime) -> str:
    """Render the unified header bar."""

def render_audience_panel(
    audience_id: str,
    articles: list[dict],
    exec_summary: dict,
    generation_time: datetime,
) -> str:
    """Render a complete audience panel with all sections."""
```

### 3.20 `app/delivery/email_sender.py`

```python
def send_briefing_email(
    recipient_email: str,
    subject: str,
    html_body: str,
    from_address: str = "briefing@oci.oracle.com",
    postmark_api_key: str | None = None,
) -> dict:
    """Send an HTML briefing email via Postmark.

    This is a stub implementation that logs the send intent
    and returns a mock response. Replace with actual Postmark
    API call in production.

    Returns:
        Dict with keys: message_id (str), status (str: sent|stubbed),
        recipient (str), sent_at (str).
    """
```

### 3.21 `app/db/queries.py`

```python
def upsert_article(db_session, article_dict: dict) -> int:
    """Insert or update an article. Returns the article row ID."""

def get_articles_since(
    db_session, since: datetime, limit: int = 500
) -> list[Article]:
    """Fetch articles published after the given datetime."""

def log_processing_step(
    db_session, article_id: int, stage: str,
    input_snap: dict = None, output_snap: dict = None,
    score_breakdown: dict = None,
) -> int:
    """Write a processing_log entry. Returns log row ID."""

def log_suppression(
    db_session, article_id: int, reason: str,
    similarity_score: float = None, matched_cluster_id: int = None,
) -> int:
    """Write a suppression_log entry. Returns log row ID."""

def save_briefing_record(
    db_session, audience_id: str, briefing_date: date,
    article_ids: list[int], exec_summary: dict,
) -> int:
    """Upsert an audience_briefings row. Returns row ID."""

def get_delivered_article_ids(
    db_session, days: int = 7
) -> set[int]:
    """Return IDs of articles delivered in the past N days."""

def get_clusters_since(
    db_session, since: datetime
) -> list[StoryCluster]:
    """Fetch story clusters with last_seen after the given datetime."""
```

### 3.22 `scripts/pipeline.py`

```python
def parse_args() -> argparse.Namespace:
    """Parse CLI arguments: --dry-run, --audience NAME, --date YYYY-MM-DD, --no-cache."""

def run_pipeline(
    dry_run: bool = False,
    audience: str | None = None,
    date_str: str | None = None,
    no_cache: bool = False,
) -> dict[str, Path]:
    """Execute the full pipeline and return output file paths.

    Steps:
        1. Init DB
        2. Ingest feeds
        3. Process (normalize + entity extraction)
        4. Score (7-dimension scoring)
        5. Dedup (5-stage pipeline)
        6. Classify (LLM or dry-run placeholders)
        7. Generate summaries (LLM or dry-run)
        8. Generate executive summaries (LLM or dry-run)
        9. Render HTML
        10. Save briefing records to DB

    Returns:
        Dict mapping output keys to file paths.
    """

def main() -> None:
    """CLI entry point."""
```

### 3.23 `scripts/serve.py`

```python
def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Mounts:
        - /api/* routes from app.api.routes
        - /output/* static file serving
        - /admin/* admin dashboard
    """

def main() -> None:
    """Launch uvicorn dev server on port 8000."""
```

### 3.24 `config/settings.py`

```python
@dataclass
class Settings:
    # Paths
    PROJECT_ROOT: Path
    OUTPUT_DIR: Path
    DB_PATH: Path
    CACHE_DIR: Path

    # Pipeline tuning
    INGEST_WINDOW_HOURS: int = 48
    MAX_ARTICLES_TO_CLASSIFY: int = 60
    TOP_ARTICLES_PER_AUDIENCE: int = 12
    MAX_CONCURRENT_LLM: int = 5
    DEDUP_TITLE_THRESHOLD: float = 0.80
    DEDUP_ENTITY_THRESHOLD: float = 0.50
    DEDUP_SIMILARITY_THRESHOLD: float = 0.80
    DELIVERED_WINDOW_DAYS: int = 7

    # LLM
    HAIKU_MODEL: str = "claude-haiku-4-5"
    SONNET_MODEL: str = "claude-sonnet-4-6"
    LLM_MAX_RETRIES: int = 3
    LLM_RETRY_BACKOFF: float = 2.0

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

SETTINGS: Settings  # Module-level singleton
```

---

## 4. Scoring Engine Spec

### 4.1 Overview

Every article receives a score per audience. The score is the sum of 7 dimensions, each normalized to a 0-10 scale:

```
final_score = source_credibility     (0-10)
            + audience_relevance     (0-10)
            + novelty                (0-10)
            + momentum               (0-10)
            + strategic_impact       (0-10)
            + timeliness             (0-10)
            - duplication_penalty    (0-10)
```

**Maximum possible score:** 60 (all dimensions at 10, no penalty)
**Minimum possible score:** -10 (zero on all positives, max penalty)

### 4.2 Dimension 1: Source Credibility

**Range:** 0-10
**Type:** Static lookup by source tier

| Tier | Score | Examples |
|------|-------|---------|
| 1 | 10.0 | Reuters, Bloomberg, SEC filings, official press releases |
| 2 | 7.5 | Ars Technica, TechCrunch, VentureBeat, The Verge |
| 3 | 5.0 | AWS Blog, Azure Blog, OCI Blog, OpenAI Blog |
| 4 | 2.5 | Hacker News, Reddit |
| Unknown | 1.0 | Source not in registry |

**Formula:**
```python
def source_credibility(tier: int) -> float:
    return {1: 10.0, 2: 7.5, 3: 5.0, 4: 2.5}.get(tier, 1.0)
```

**Migration note:** The current system uses a 0-30 scale (`{1: 30, 2: 20, 3: 10, 4: 5}`). The new system normalizes to 0-10 for dimensional parity.

### 4.3 Dimension 2: Audience Relevance

**Range:** 0-10
**Type:** Computed per (article, audience) pair

**Sub-components:**

| Sub-component | Weight | Method |
|---------------|--------|--------|
| Section weight match | 40% | `section_weight[article.primary_section] * 10.0` -- maps 0.0-1.0 weight to 0-10 |
| Company name match | 25% | Count of article entities matching `companies_of_interest`, capped at 3 matches, scaled to 10 |
| Topic keyword match | 25% | Count of article topics matching `topics_of_interest`, capped at 5 matches, scaled to 10 |
| Geo focus match | 10% | Binary: 10 if any region overlap, 0 otherwise |

**Formula:**
```python
def audience_relevance(article: dict, profile: dict) -> float:
    section_score = profile["section_weights"].get(
        article.get("classified_section", ""), 0.05
    ) * 10.0

    entities = set(article.get("entities_json", {}).get("companies", []))
    interest = set(profile.get("companies_of_interest", []))
    company_score = min(len(entities & interest), 3) * (10.0 / 3.0)

    article_topics = set(article.get("topics_json", []))
    interest_topics = set(profile.get("topics_of_interest", []))
    topic_score = min(len(article_topics & interest_topics), 5) * 2.0

    article_regions = set(article.get("entities_json", {}).get("regions", []))
    interest_regions = set(profile.get("geo_focus", ["global"]))
    geo_score = 10.0 if (
        "global" in interest_regions or bool(article_regions & interest_regions)
    ) else 0.0

    raw = (
        section_score * 0.40
        + company_score * 0.25
        + topic_score * 0.25
        + geo_score * 0.10
    )

    # Negative topic penalty
    negative = set(profile.get("negative_topics", []))
    if article_topics & negative:
        raw *= 0.70  # 30% reduction

    return min(raw, 10.0)
```

### 4.4 Dimension 3: Novelty

**Range:** 0-10 (10 = completely new, 0 = exact duplicate)

**Formula:**
```python
def novelty(article: dict, delivered_clusters: list[dict]) -> float:
    if not delivered_clusters:
        return 10.0  # No history, everything is new

    max_similarity = 0.0
    for cluster in delivered_clusters:
        sim = title_similarity(article, cluster)
        max_similarity = max(max_similarity, sim)

    return 10.0 * (1.0 - max_similarity)
```

**Thresholds:**
- `max_similarity > 0.90` => novelty ~1.0 => near-duplicate, trigger dedup
- `max_similarity 0.70-0.89` => novelty 1.1-3.0 => related story, check fact delta
- `max_similarity 0.40-0.69` => novelty 3.1-6.0 => topically related, different
- `max_similarity < 0.40` => novelty 6.1-10.0 => new story

### 4.5 Dimension 4: Momentum

**Range:** 0-10

**Formula:**
```python
def momentum(article: dict, cluster_article_count: int = 1) -> float:
    # Based on how many sources cover the same story cluster
    if cluster_article_count >= 5:
        return 10.0
    elif cluster_article_count >= 3:
        return 7.0
    elif cluster_article_count >= 2:
        return 4.0
    else:
        return 1.0
```

**Implementation note:** In the current Phase 1 system, momentum is approximated by cluster article count. Future phases will incorporate HN position, Reddit upvotes, and GitHub star velocity.

### 4.6 Dimension 5: Strategic Impact

**Range:** 0-10

**Formula:**
```python
def strategic_impact(title: str, summary: str, keywords: dict) -> float:
    combined = (title + " " + summary).lower()
    bonus = 0.0
    for keyword, pts in keywords.items():
        if keyword in combined:
            bonus += pts
    # Scale: current OCI_KEYWORDS max practical ~20pts, normalize to 0-10
    return min(bonus / 2.0, 10.0)
```

**Keywords:** Same `OCI_KEYWORDS` dict from current `config.py`, with values divided by 2 to map to 0-10 scale.

### 4.7 Dimension 6: Timeliness

**Range:** 0-10

| Publication Age | Score |
|----------------|-------|
| 0-6 hours | 10.0 |
| 6-12 hours | 8.0 |
| 12-24 hours | 6.0 |
| 24-48 hours | 4.0 |
| 48-96 hours | 2.0 |
| 96-168 hours | 1.0 |
| >168 hours | 0.0 |

**Formula:**
```python
def timeliness(published_at: datetime) -> float:
    age_hours = (now_utc - published_at).total_seconds() / 3600
    brackets = [(6, 10.0), (12, 8.0), (24, 6.0), (48, 4.0),
                (96, 2.0), (168, 1.0), (None, 0.0)]
    for max_h, score in brackets:
        if max_h is None or age_hours < max_h:
            return score
    return 0.0
```

### 4.8 Dimension 7: Duplication Penalty

**Range:** 0-10 (subtracted from total)

| Novelty Score | Penalty | Effect |
|--------------|---------|--------|
| 0-1 (near-duplicate, no delta) | 10 | Full suppression |
| 1-3 (related, fact delta exists) | 3 | Render as follow-up |
| 4-6 (topically related) | 1 | Minor penalty |
| 7-10 (new story) | 0 | No penalty |

**Formula:**
```python
def duplication_penalty(novelty_score: float) -> float:
    if novelty_score <= 1.0:
        return 10.0
    elif novelty_score <= 3.0:
        return 3.0
    elif novelty_score <= 6.0:
        return 1.0
    else:
        return 0.0
```

**Hard suppression:** Articles with penalty = 10 are removed from the candidate pool entirely and logged to `suppression_log` with reason `duplicate_no_delta`.

---

## 5. Dedup Pipeline Spec

The deduplication pipeline runs as a 5-stage sequential process. It operates on the full set of scored articles before audience-specific selection.

### 5.1 Stage 1: Normalize

**Goal:** Transform articles into comparable representations.

**Operations:**
1. Tokenize title into lowercase word set (strip punctuation)
2. Compute `fact_signature` = SHA-256 hash of sorted (entities + event_verb + amounts)
3. Normalize title for comparison (lowercase, strip articles/prepositions)

**Implementation:**
```python
def normalize_for_dedup(article: dict) -> dict:
    article["_tokens"] = tokenize(article["title"])
    article["_fact_sig"] = compute_fact_signature(article)
    article["_norm_title"] = re.sub(
        r"\b(the|a|an|is|are|was|were|to|for|of|in|on|at)\b", "",
        article["title"].lower()
    ).strip()
    return article
```

### 5.2 Stage 2: Cluster

**Goal:** Group articles about the same real-world event.

**Criteria for same-cluster membership:**
1. Exact URL match (safety net), OR
2. Same `fact_signature` (exact structural match), OR
3. Title Jaccard similarity > 0.60 AND entity overlap > 0.30, OR
4. Title Jaccard similarity > 0.80 (title alone is sufficient)

**Algorithm:**
```python
def cluster_articles(articles: list[dict], ...) -> list[list[dict]]:
    clusters = []
    assigned = set()

    for i, a in enumerate(articles):
        if a["url"] in assigned:
            continue
        cluster = [a]
        assigned.add(a["url"])

        for j, b in enumerate(articles):
            if j <= i or b["url"] in assigned:
                continue
            title_sim = title_similarity(a, b)
            ent_sim = entity_overlap(a, b)
            sig_match = a.get("_fact_sig") == b.get("_fact_sig")

            if (sig_match
                or title_sim > 0.80
                or (title_sim > 0.60 and ent_sim > 0.30)):
                cluster.append(b)
                assigned.add(b["url"])

        clusters.append(cluster)
    return clusters
```

**Cluster representative:** The article with the highest source tier (lowest number) is chosen as the cluster representative. Ties broken by max audience score.

### 5.3 Stage 3: Compare Against 7-Day Window

**Goal:** Identify candidate duplicates of previously delivered stories.

**Process:**
1. Query `audience_briefings` for article_ids delivered in the past 7 days
2. Load those articles and their cluster associations
3. For each current article, compute title similarity against every delivered article
4. If `max_similarity > 0.80`, mark as `candidate_duplicate` and record matched cluster

**Implementation:**
```python
def compare_against_delivered(article, delivered_clusters, threshold=0.80):
    best_sim = 0.0
    best_cluster_id = None

    for cluster in delivered_clusters:
        sim = title_similarity(article, cluster)
        if sim > best_sim:
            best_sim = sim
            best_cluster_id = cluster.get("id")

    if best_sim > threshold:
        return ("candidate_duplicate", best_sim, best_cluster_id)
    return ("new", None, None)
```

### 5.4 Stage 4: Detect Follow-Up

**Goal:** Override suppression when an article adds materially new information.

**Fact fields tracked:**
- `capacity_mw` -- datacenter power/compute capacity
- `customer_name` -- named customer
- `deal_size` -- financial value
- `model_name` -- AI model name
- `partner_name` -- named partner
- `region` -- geographic location
- `date` -- key timeline date
- `status` -- announced/confirmed/delayed/cancelled/closed/live

**Detection logic:**
```python
def detect_fact_delta(new_facts, prior_snapshot):
    changed = []
    for field in FACT_FIELDS:
        new_val = new_facts.get(field)
        prior_val = prior_snapshot.get(field)
        if new_val is not None and new_val != prior_val:
            changed.append(field)
    has_delta = len(changed) >= 1
    return (has_delta, changed)
```

**Fact extraction** uses regex heuristics:
- Dollar amounts: `r'\$[\d,]+\.?\d*\s*[BMK](?:illion)?'`
- Megawatts: `r'(\d+)\s*(?:MW|megawatt)'`
- Status words: match against `{announced, confirmed, delayed, cancelled, closed, live}`
- Company names: match against known entity list
- Regions: match against known geography list

**Decision:**
- If `has_delta` is True => status = `follow_up`
- If `has_delta` is False => status = `suppressed`

### 5.5 Stage 5: Render Follow-Up

**Goal:** Tag articles with visual novelty badges and log suppressions.

**Badge assignment:**

| `novelty_status` | Badge | CSS Class | Rendering |
|-----------------|-------|-----------|-----------|
| `new` | (none) | (none) | Standard rendering |
| `follow_up` | "UPDATE" | `badge-update` | Orange badge; summary leads with "what changed" |
| `follow_up` + major delta (>=3 fields) | "MAJOR UPDATE" | `badge-major` | Red badge; promoted in section ordering |
| `suppressed` | Not rendered | N/A | Logged to `suppression_log` |

**Suppression logging:**
```python
def log_suppression(db_session, article_id, reason, sim_score, cluster_id):
    entry = SuppressionLog(
        article_id=article_id,
        reason=reason,
        similarity_score=sim_score,
        matched_cluster_id=cluster_id,
    )
    db_session.add(entry)
    db_session.commit()
```

### 5.6 Full Dedup Pipeline Orchestration

```python
def tag_novelty(articles: list[dict], db_session=None) -> list[dict]:
    # Stage 1: Normalize
    for a in articles:
        normalize_for_dedup(a)

    # Stage 2: Cluster
    clusters = cluster_articles(articles)
    if db_session:
        assign_clusters_to_db(db_session, clusters)

    # Stage 3: Compare against 7-day window
    delivered = []
    if db_session:
        delivered = get_delivered_clusters(db_session, days=7)

    for a in articles:
        status, sim, cid = compare_against_delivered(a, delivered)
        a["novelty_status"] = status
        a["_dedup_sim"] = sim
        a["_dedup_cluster"] = cid

    # Stage 4: Detect follow-up for candidate_duplicates
    for a in articles:
        if a["novelty_status"] == "candidate_duplicate":
            matched = next(
                (c for c in delivered if c["id"] == a["_dedup_cluster"]), None
            )
            if matched:
                a["novelty_status"] = classify_followup(a, matched)

    # Stage 5: Render badges, log suppressions
    result = []
    for a in articles:
        if a["novelty_status"] == "suppressed":
            if db_session:
                log_suppression(
                    db_session, a.get("db_id"),
                    reason="duplicate_no_delta",
                    similarity_score=a.get("_dedup_sim"),
                    matched_cluster_id=a.get("_dedup_cluster"),
                )
        else:
            a["novelty_badge"] = NOVELTY_BADGES.get(
                a["novelty_status"], {}
            )
            result.append(a)

    return result
```

---

## 6. API Endpoints

All endpoints are served by FastAPI at `http://localhost:8000`.

### 6.1 Admin Endpoints

#### `GET /admin/articles`

List articles with filtering and pagination.

**Query Parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `date` | str (YYYY-MM-DD) | today | Filter by ingest date |
| `tier` | int | (all) | Filter by source tier |
| `section` | str | (all) | Filter by classified section |
| `limit` | int | 50 | Max results |
| `offset` | int | 0 | Pagination offset |

**Response (200):**
```json
{
  "total": 142,
  "articles": [
    {
      "id": 1,
      "title": "NVIDIA Announces H200 Ultra GPU...",
      "url": "https://reuters.com/...",
      "source": "Reuters Tech",
      "tier": 1,
      "published_at": "2026-03-11T06:00:00Z",
      "classified_section": "ai",
      "confidence": "high",
      "scores": {"karan": 52.3, "nathan": 48.1, "greg": 55.7, "mahesh": 41.2},
      "novelty_status": "new",
      "ingest_at": "2026-03-11T08:00:00Z"
    }
  ]
}
```

---

#### `GET /admin/sources`

List all configured sources with status.

**Response (200):**
```json
{
  "sources": [
    {
      "id": 1,
      "domain": "feeds.reuters.com",
      "display_name": "Reuters Tech",
      "tier": 1,
      "credibility_score": 10.0,
      "rss_url": "https://feeds.reuters.com/reuters/technologyNews",
      "crawl_freq_mins": 30,
      "active": true,
      "last_fetch_at": "2026-03-11T07:30:00Z",
      "article_count_24h": 12
    }
  ]
}
```

---

#### `GET /admin/processing-log`

View processing log entries for traceability.

**Query Parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `article_id` | int | (all) | Filter by article |
| `stage` | str | (all) | Filter by stage name |
| `limit` | int | 100 | Max results |

**Response (200):**
```json
{
  "total": 847,
  "entries": [
    {
      "id": 1,
      "article_id": 42,
      "stage": "score",
      "score_breakdown": {
        "source_credibility": 10.0,
        "audience_relevance": {"karan": 7.2, "greg": 8.5},
        "novelty": 9.0,
        "momentum": 4.0,
        "strategic_impact": 6.5,
        "timeliness": 8.0,
        "duplication_penalty": 0.0
      },
      "created_at": "2026-03-11T08:05:00Z"
    }
  ]
}
```

---

#### `GET /admin/suppression-log`

View suppressed articles and reasons.

**Query Parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `date` | str (YYYY-MM-DD) | today | Filter by suppression date |
| `reason` | str | (all) | Filter by reason |
| `limit` | int | 100 | Max results |

**Response (200):**
```json
{
  "total": 23,
  "entries": [
    {
      "id": 1,
      "article_id": 55,
      "article_title": "OpenAI Releases GPT-5...",
      "reason": "duplicate_no_delta",
      "similarity_score": 0.92,
      "matched_cluster_id": 7,
      "matched_cluster_headline": "OpenAI GPT-5 Launch",
      "suppressed_at": "2026-03-11T08:06:00Z"
    }
  ]
}
```

---

#### `POST /run-pipeline`

Trigger a pipeline run via the API.

**Request Body:**
```json
{
  "dry_run": true,
  "audience": "karan",
  "date": "2026-03-11",
  "no_cache": false
}
```

All fields are optional. Defaults: `dry_run=false`, `audience=null` (all), `date=today`, `no_cache=false`.

**Response (202):**
```json
{
  "status": "started",
  "run_id": "20260311-080000",
  "params": {
    "dry_run": true,
    "audience": "karan",
    "date": "2026-03-11",
    "no_cache": false
  }
}
```

**Response (409) -- pipeline already running:**
```json
{
  "status": "error",
  "message": "Pipeline is already running (run_id: 20260311-070000)"
}
```

---

#### `GET /briefings/{date}`

Retrieve a generated briefing by date.

**Path Parameters:**

| Param | Type | Description |
|-------|------|-------------|
| `date` | str (YYYY-MM-DD) | Briefing date |

**Query Parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `audience` | str | (all) | Specific audience ID |
| `format` | str | "html" | Response format: "html" or "json" |

**Response (200) -- format=html:**
Returns the raw HTML briefing file.

**Response (200) -- format=json:**
```json
{
  "date": "2026-03-11",
  "audiences": {
    "karan": {
      "article_count": 12,
      "exec_summary": {
        "bullets": ["..."],
        "oci_implication_of_day": "..."
      },
      "articles": [
        {
          "id": 42,
          "title": "...",
          "section": "compete",
          "score": 52.3,
          "headline": "...",
          "summary": "...",
          "oci_implication": "..."
        }
      ],
      "generated_at": "2026-03-11T08:15:00Z"
    }
  }
}
```

**Response (404):**
```json
{
  "status": "error",
  "message": "No briefing found for date 2026-03-12"
}
```

---

### 6.2 Pydantic Schemas

```python
"""
app/api/schemas.py -- Pydantic models for API validation.
"""

from datetime import date, datetime
from pydantic import BaseModel, Field


class ArticleResponse(BaseModel):
    id: int
    title: str
    url: str
    source: str
    tier: int
    published_at: datetime | None
    classified_section: str | None
    confidence: str | None
    scores: dict[str, float]
    novelty_status: str | None
    ingest_at: datetime


class ArticleListResponse(BaseModel):
    total: int
    articles: list[ArticleResponse]


class SourceResponse(BaseModel):
    id: int
    domain: str
    display_name: str
    tier: int
    credibility_score: float
    rss_url: str
    crawl_freq_mins: int
    active: bool


class SourceListResponse(BaseModel):
    sources: list[SourceResponse]


class ProcessingLogEntry(BaseModel):
    id: int
    article_id: int
    stage: str
    score_breakdown: dict | None
    created_at: datetime


class ProcessingLogResponse(BaseModel):
    total: int
    entries: list[ProcessingLogEntry]


class SuppressionLogEntry(BaseModel):
    id: int
    article_id: int
    article_title: str | None
    reason: str
    similarity_score: float | None
    matched_cluster_id: int | None
    matched_cluster_headline: str | None
    suppressed_at: datetime


class SuppressionLogResponse(BaseModel):
    total: int
    entries: list[SuppressionLogEntry]


class PipelineRunRequest(BaseModel):
    dry_run: bool = False
    audience: str | None = None
    date: str | None = None
    no_cache: bool = False


class PipelineRunResponse(BaseModel):
    status: str
    run_id: str
    params: dict


class BriefingArticle(BaseModel):
    id: int
    title: str
    section: str | None
    score: float
    headline: str
    summary: str
    oci_implication: str


class AudienceBriefingData(BaseModel):
    article_count: int
    exec_summary: dict
    articles: list[BriefingArticle]
    generated_at: datetime


class BriefingResponse(BaseModel):
    date: str
    audiences: dict[str, AudienceBriefingData]
```

---

## 7. Migration Plan

### 7.1 File-to-Module Mapping

| Current File | New Module(s) | Notes |
|-------------|---------------|-------|
| `briefing/__init__.py` | `app/__init__.py` | Version string only |
| `briefing/config.py` (AUDIENCE_PROFILES) | `config/audiences.py` | Extract audience profiles |
| `briefing/config.py` (RSS_SOURCES) | `config/sources.py` | Extract source list |
| `briefing/config.py` (TIER_CREDIBILITY, etc.) | `app/scoring/weights.py` | Extract scoring constants |
| `briefing/config.py` (pipeline settings) | `config/settings.py` | Extract to Settings dataclass |
| `briefing/ingest.py` (_strip_html, _parse_date, _make_article_id) | `app/ingestion/normalizer.py` | Move helper functions |
| `briefing/ingest.py` (_fetch_feed) | `app/ingestion/fetcher.py` | Move feed fetching |
| `briefing/ingest.py` (ingest_feeds) | `app/ingestion/fetcher.py` | Move orchestrator |
| `briefing/score.py` (_source_credibility_score) | `app/scoring/dimensions.py` | Rescale 0-30 to 0-10 |
| `briefing/score.py` (_timeliness_score) | `app/scoring/dimensions.py` | Rescale to 0-10 |
| `briefing/score.py` (_section_relevance_score) | `app/scoring/dimensions.py` (audience_relevance) | Expand to full 4-component calc |
| `briefing/score.py` (_keyword_bonus) | `app/scoring/dimensions.py` (strategic_impact) | Rescale to 0-10 |
| `briefing/score.py` (score_article_for_audience, etc.) | `app/scoring/engine.py` | Add 3 new dimensions |
| `briefing/process.py` (SECTION_KEYWORDS) | `app/processing/article_normalizer.py` | Move keyword maps |
| `briefing/process.py` (_tokenize, _title_overlap) | `app/dedup/normalizer.py` + `app/dedup/cluster.py` | Split dedup logic |
| `briefing/process.py` (_infer_sections) | `app/processing/article_normalizer.py` | Move section inference |
| `briefing/process.py` (deduplicate_articles) | `app/dedup/cluster.py` | Expand to 5-stage pipeline |
| `briefing/process.py` (normalize_articles) | `app/processing/article_normalizer.py` | Orchestrator function |
| `briefing/llm.py` (call_claude, cache) | `app/llm/client.py` | Move subprocess + cache |
| `briefing/llm.py` (classify_article) | `app/llm/classify.py` | Isolate classification |
| `briefing/llm.py` (generate_summary) | `app/llm/summarize.py` | Isolate summarization |
| `briefing/llm.py` (generate_executive_summary) | `app/llm/executive.py` | Isolate exec summary |
| `briefing/render.py` (BASE_CSS) | `app/rendering/css.py` | Extract CSS |
| `briefing/render.py` (hero card, story row, section) | `app/rendering/components.py` | Extract components |
| `briefing/render.py` (render_combined_html, etc.) | `app/rendering/html_builder.py` | Page assembly |
| `briefing/render.py` (save_briefings) | `app/rendering/html_builder.py` | File output |
| `main.py` (pipeline steps) | `scripts/pipeline.py` | Restructure with --date flag |
| `main.py` (_synthetic_articles) | `scripts/pipeline.py` | Keep for dry-run fallback |
| `serve.py` | `scripts/serve.py` | Replace with FastAPI |
| (new) | `app/db/models.py` | All new ORM models |
| (new) | `app/db/engine.py` | New DB engine setup |
| (new) | `app/db/queries.py` | New query helpers |
| (new) | `app/api/routes.py` | New FastAPI routes |
| (new) | `app/api/schemas.py` | New Pydantic schemas |
| (new) | `app/processing/entity_extractor.py` | New regex NER |
| (new) | `app/dedup/comparator.py` | New 7-day window comparison |
| (new) | `app/dedup/followup.py` | New fact delta detection |
| (new) | `app/dedup/renderer.py` | New novelty badge tagging |
| (new) | `app/delivery/email_sender.py` | New Postmark stub |
| (new) | `web/admin.html` | New admin dashboard |

### 7.2 Migration Sequence

The migration should proceed in this order, with each step verifiable independently:

**Step 1: Config extraction**
- Create `config/settings.py`, `config/audiences.py`, `config/sources.py`
- All existing code continues to work by importing from new locations
- Add backward-compatible re-exports in `briefing/config.py`

**Step 2: Database layer**
- Create `app/db/models.py`, `app/db/engine.py`, `app/db/queries.py`
- Run `init_db()` to create SQLite tables
- Existing pipeline does not depend on DB yet; DB is additive

**Step 3: Ingestion refactor**
- Move `briefing/ingest.py` functions to `app/ingestion/`
- Verify: `python -c "from app.ingestion.fetcher import ingest_feeds; print('OK')"`

**Step 4: Processing refactor**
- Move `briefing/process.py` functions to `app/processing/`
- Add `app/processing/entity_extractor.py` (new)
- Verify: `python -c "from app.processing.article_normalizer import normalize_articles; print('OK')"`

**Step 5: Scoring expansion**
- Move `briefing/score.py` to `app/scoring/`
- Add 3 new dimensions (novelty, momentum, duplication_penalty)
- Rescale existing dimensions to 0-10
- Verify: `python -m pytest tests/test_scoring.py`

**Step 6: Dedup pipeline**
- Extract dedup from `briefing/process.py` to `app/dedup/`
- Add 5-stage pipeline with DB integration
- Verify: `python -m pytest tests/test_dedup.py`

**Step 7: LLM refactor**
- Split `briefing/llm.py` into `app/llm/client.py`, `classify.py`, `summarize.py`, `executive.py`
- Preserve cache format for backward compatibility
- Verify: `python -c "from app.llm.classify import classify_article; print('OK')"`

**Step 8: Rendering refactor**
- Split `briefing/render.py` into `app/rendering/` modules
- Verify HTML output matches current output

**Step 9: Pipeline runner**
- Create `scripts/pipeline.py` with new CLI flags (--date)
- Verify: `python scripts/pipeline.py --dry-run --date 2026-03-11`

**Step 10: API + Admin**
- Create `scripts/serve.py` with FastAPI
- Create `app/api/routes.py` with all endpoints
- Create `web/admin.html`
- Verify: `python scripts/serve.py` then curl endpoints

**Step 11: Delivery stub**
- Create `app/delivery/email_sender.py`

**Step 12: Tests**
- Create `tests/test_scoring.py`, `tests/test_dedup.py`, `tests/test_ingestion.py`

### 7.3 Backward Compatibility

During migration, the old `briefing/` package MUST continue to work. This is achieved by:

1. Adding `import` shims in `briefing/config.py` that re-export from `config/`
2. Not deleting any old files until the new modules are fully verified
3. Running both `python main.py --dry-run` and `python scripts/pipeline.py --dry-run` to confirm identical output

The old `briefing/` package and `main.py` can be removed once all tests pass against the new structure.

### 7.4 scripts/pipeline.py CLI Interface

```
usage: pipeline.py [-h] [--dry-run] [--audience NAME] [--date YYYY-MM-DD] [--no-cache]

OCI AI Daily Executive Briefing Pipeline

options:
  -h, --help          show this help message and exit
  --dry-run           Skip LLM calls and use placeholder text
  --audience NAME     Run for a single audience (karan|nathan|greg|mahesh)
  --date YYYY-MM-DD   Target briefing date (default: today)
  --no-cache          Force LLM regeneration (ignore existing cache)
```

The `--date` flag controls:
- The output directory name (`output/YYYY-MM-DD/`)
- The `briefing_date` in `audience_briefings` table
- The date displayed in the HTML header

---

## Architecture Diagram

```
+------------------------------------------------------------------+
|                        scripts/pipeline.py                        |
|  CLI: --dry-run --audience NAME --date YYYY-MM-DD --no-cache     |
+---+------+------+------+------+------+------+------+------+------+
    |      |      |      |      |      |      |      |      |
    v      v      v      v      v      v      v      v      v
 init_db  ingest process score  dedup classify summary exec  render
    |      |      |      |      |      |       |      |      |
    v      v      v      v      v      v       v      v      v
+------+ +----+ +----+ +-----+ +----+ +-----+ +---+ +---+ +------+
|app/db| |app/| |app/| |app/ | |app/| |app/ | |app| |app| |app/  |
|      | |ing.| |proc| |scor.| |ded.| |llm/ | |/  | |/  | |rend. |
+--+---+ +--+-+ +--+-+ +--+--+ +-+--+ +--+--+ |llm| |llm| +--+--+
   |        |      |       |      |       |     +---+ +---+    |
   v        v      v       v      v       v                    v
+--------------------------------------------------------------+
|                output/briefing.db (SQLite)                    |
|  sources | articles | processing_log | story_clusters         |
|  audience_briefings | suppression_log                         |
+--------------------------------------------------------------+
                               |
                               v
                    output/YYYY-MM-DD/*.html

+------------------------------------------------------------------+
|                       scripts/serve.py                            |
|               FastAPI + Static File Serving                      |
+--+-------+-------+----------+--------+----------+---------------+
   |       |       |          |        |          |
   v       v       v          v        v          v
  GET     GET     GET        GET      POST       GET
  /admin  /admin  /admin     /admin   /run-      /briefings
  /art.   /src.   /proc-log  /supp.   pipeline   /{date}
```

---

## Architecture Decision Records

### ADR-001: SQLite over PostgreSQL

**Context:** The original architecture doc specified PostgreSQL. The current system is file-based with no database.

**Decision:** Use SQLite at `output/briefing.db`.

**Rationale:**
- Single-user system (one pipeline run at a time, one admin viewer)
- No concurrent write pressure
- Zero deployment overhead (no separate DB process)
- Portable: the entire system state is in one file
- SQLAlchemy abstraction allows future migration to PostgreSQL if needed

**Consequences:** No concurrent pipeline runs. Acceptable for a daily batch system.

---

### ADR-002: Regex NER over spaCy

**Context:** The original architecture specified spaCy `en_core_web_trf` for NER.

**Decision:** Use simple regex patterns for entity extraction in Phase 2.

**Rationale:**
- spaCy transformer model adds ~500MB dependency and significant startup time
- For the known entity universe (cloud companies, products, regions), regex patterns achieve >90% recall
- The LLM classification step (Haiku) provides supplementary entity extraction
- Can upgrade to spaCy in a future phase if recall drops below acceptable thresholds

**Consequences:** May miss novel entities not in the pattern list. Mitigated by monthly pattern list updates and LLM fallback.

---

### ADR-003: Subprocess Claude CLI over SDK

**Context:** The system calls Claude via `claude -p` subprocess.

**Decision:** Preserve the subprocess approach from Phase 1.

**Rationale:**
- Avoids adding the Anthropic Python SDK as a dependency
- The `claude` CLI handles auth, token management, and model routing
- Retry and cache logic is already implemented and working
- Subprocess isolation prevents LLM failures from crashing the pipeline

**Consequences:** Slightly higher latency per call (~200ms overhead). Acceptable given the batch nature of the system.

---

### ADR-004: 7-Dimension Scoring Normalization

**Context:** Phase 1 uses heterogeneous scales (credibility 0-30, timeliness 0-15, relevance 0-40, keywords 0-10).

**Decision:** Normalize all dimensions to 0-10 scale.

**Rationale:**
- Equal-weight comparison between dimensions
- Easier to reason about thresholds
- Consistent with PRD specification
- Makes dimension contribution visible in processing_log

**Consequences:** Existing cached scores are invalidated. The --no-cache flag handles this.

---

### ADR-005: 5-Stage Dedup as Sequential Pipeline

**Context:** Phase 1 dedup is a single-pass Jaccard similarity filter on titles.

**Decision:** Implement the full 5-stage dedup pipeline (normalize, cluster, compare, detect_followup, render) as specified in the PRD.

**Rationale:**
- The PRD explicitly requires follow-up detection and suppression logging
- Single-pass dedup cannot distinguish between "same story, no new info" and "same story, material update"
- DB-backed 7-day window enables cross-day dedup
- Suppression logging enables audit and threshold tuning

**Consequences:** More DB reads per pipeline run (~100ms overhead). Acceptable.
