# AI Daily Executive Briefing — System Architecture

**Version:** 2.0 (implemented)
**Updated:** 2026-04-13 (Oracle Code Assist auth copy)

---

## 1. System Overview

The AI Daily Briefing is an automated intelligence pipeline that ingests news from 31 RSS sources, deduplicates using sentence embeddings against a 7-day rolling cluster history, scores articles per executive audience, generates personalized summaries via Oracle Code Assist's locally authenticated `codex` CLI, and renders HTML briefings. It runs daily via cron on an OCI VM.

---

## 2. Pipeline Architecture

```
[1] Fetch (31 RSS feeds + Trafilatura full-text)
     ↓
[2] Pre-score (source tier + timeliness)
     ↓
[3] In-Run Dedup (5-stage Jaccard pipeline)
     ↓
[4] Cross-Day Dedup (embedding cosine similarity + fact-delta scoring)
     ↓
[5] Classify (Codex / Oracle Code Assist — topics, entities, section)
     ↓
[6] Full Audience Score (per-executive relevance ranking)
     ↓
[7] Summarize (Codex / Oracle Code Assist — per-audience summaries, top 12)
     ↓
[8] Executive Summaries (Codex / Oracle Code Assist — 3-5 bullet synthesis)
     ↓
[9] Render (HTML files to output/YYYY-MM-DD/)
```

### Why this order
- Pre-score before dedup: break ties between duplicates
- Dedup before classify: don't spend LLM calls on articles we'll suppress
- Classify before full score: classification provides topics/entities for accurate scoring
- Full score before summarize: only summarize articles that make the top 12

---

## 3. Components

### 3.1 Ingestion (`briefing/ingest.py`)
- **feedparser** polls 31 RSS feeds concurrently (ThreadPoolExecutor, 10 workers)
- **Trafilatura** + **httpx** (browser headers) fetches full article text from URLs
- Falls back to RSS summary (1500 chars) when full text extraction fails (paywalled sites)
- Full text capped at 5000 chars
- Filters to articles from last 48 hours
- Deduplicates by URL

### 3.2 Deduplication (two stages)

**Stage A — In-run dedup** (`app/dedup/pipeline.py`)
5 stages within a single ingestion batch:
1. Normalize: tokenize titles/summaries, extract entities
2. Cluster: group by title Jaccard similarity > 0.50 or 2+ shared entities
3. Compare: pairwise Jaccard within clusters
4. Detect follow-ups: >0.65 cross-source similarity → suppress; 0.40-0.65 → tag as follow-up
5. Apply suppressions: remove, log to suppression_log table

**Stage B — Cross-day dedup** (`app/dedup/cross_day.py`, `app/dedup/embeddings.py`)
Compares surviving articles against 7-day cluster history in SQLite:
1. Load cluster centroids from `story_clusters` table (last 7 days)
2. Compute embeddings via nomic-embed-text-v1.5 (768d → 256d Matryoshka)
3. Batch cosine similarity (numpy matrix multiply)
4. Decision: cosine ≥ 0.75 + fact-delta < 0.20 → suppress; fact-delta ≥ 0.30 → follow-up; cosine < 0.75 → new cluster
5. New clusters appended to in-memory list so subsequent articles in same batch can match

**Fact-delta scoring** (`app/dedup/fingerprint.py`)
6 regex signals determine if an article adds new information:
- Time gap (log-scaled, +0.35 max)
- New numbers (+0.30)
- New entities via SpaCy NER (+0.25)
- New quotes (+0.15)
- Verb progression (+0.10)

### 3.3 Scoring (`briefing/score.py`)
Per-article, per-audience score:
```
score = source_credibility(tier) + timeliness(age) + section_relevance(weights) + keyword_bonus
```
- Source credibility: T1=30, T2=20, T3=10, T4=5
- Timeliness: <6h=15, <12h=12, <24h=8, <48h=4
- Section relevance: audience section weights × 40
- Keyword bonus: OCI-relevant keywords, max 10

### 3.4 LLM Layer (`briefing/llm.py`)
- **Classification**: topics, entities, section, confidence per article
- **Summarization**: headline, 2-3 sentence summary, OCI implication per article × audience
- **Executive summaries**: 3-5 bullets + OCI implication of the day per audience
- All via `codex exec` using the locally authenticated Oracle Code Assist / Codex CLI session
- JSON file cache in output/.cache/ (keyed by content hash)
- 15 concurrent workers, retry with backoff

### 3.5 Rendering (`briefing/render.py`)
- Pure Python f-string HTML/CSS generation (~800 lines)
- Newspaper-style layout: header bar, executive summary, hero cards, compact rows
- Per-audience files + combined index with tab switcher
- Section navigation with jump links

### 3.6 Admin Dashboard (`web/admin.html`, `app/api/routes.py`)
FastAPI admin API + dark-themed SPA:
- **Articles**: filterable by search/tier/date/source, sortable columns
- **Sources**: all 31 feeds with tier and status
- **Clusters**: story clusters with suppression counts
- **Dedup Stats**: suppressions by reason, clusters per day timeline
- **Rankings**: per-audience article rankings with score breakdowns
- **Clusters 3D**: interactive Plotly.js scatter plot (UMAP + HDBSCAN)

---

## 4. Data Model (SQLite)

```
articles
  id, url, title, source_name, published_at, summary, full_text,
  tier, raw_score, embedding_json (256 floats), ingest_at

story_clusters
  id, canonical_url, headline, first_seen, last_seen,
  cluster_embedding_json (256 floats), fact_snapshot (JSON)

suppression_log
  id, article_id → articles, reason, similarity_score,
  matched_cluster_id → story_clusters, suppressed_at

audience_briefings
  id, audience_id, briefing_date, article_ids_json, exec_summary_json

sources
  id, domain, display_name, tier, credibility_score, rss_url, active

processing_log
  id, article_id → articles, stage, score_breakdown (JSON), created_at
```

---

## 5. Source Tiers (31 feeds)

| Tier | Sources | Credibility |
|---|---|---|
| 1 | Reuters (2), Bloomberg, WSJ, FT, CNBC | 30 pts |
| 2 | TechCrunch, Ars Technica, VentureBeat, CloudWars, DC Dynamics, The New Stack, Light Reading, SemiAnalysis, Import AI, KrebsOnSecurity, The Record | 20 pts |
| 3 | AWS Blog, Azure Blog, Google Cloud, OCI Blog, OpenAI, Anthropic, DeepMind, Hugging Face | 10 pts |
| 4 | Hacker News, r/cloudcomputing, r/aws, r/kubernetes, r/artificial, r/MachineLearning | 5 pts |

---

## 6. Embedding Model

**nomic-ai/nomic-embed-text-v1.5**
- 768d full → 256d Matryoshka truncation (~95% quality retained)
- 8K token context (supports full article text)
- ~4 seconds for 300 articles on CPU
- Stored as JSON arrays in SQLite
- Apache 2.0 license
- Loaded as lazy singleton, runs fully local (no API calls)

---

## 7. Deployment

- **VM**: OCI compute instance (145.241.199.237)
- **Services**: systemd (`ai-briefing`, `ai-briefing-admin`)
- **Reverse proxy**: nginx → ainews.oci-incubations.com
- **Cron**: daily 5:00 AM UTC (scripts/daily_run.sh)
- **Ports**: 8000 (briefing server), 8002 (admin API), 80 (nginx)

---

## 8. Not Yet Implemented

- Email delivery (Postmark — stub only)
- Click/link tracking
- Feedback controls (thumbs up/down)
- Full 7-dimension scoring (app/scoring/engine.py exists but main.py uses 4-dimension)
- Confidence tag vocabulary (using high/medium/low, PRD wants confirmed/credible_report/weak_signal)
- Editorial rules enforcement
- Email metrics

See docs/GAP_ANALYSIS.md for the full remaining work list.
