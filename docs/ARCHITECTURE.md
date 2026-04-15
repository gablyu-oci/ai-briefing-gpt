# AI Daily Executive Briefing — System Architecture

**Version:** 2.1 (implemented)
**Updated:** 2026-04-14 (Codex live deployment)

---

## 1. System Overview

The AI Daily Briefing is an automated intelligence pipeline that ingests news from 31 RSS sources, stores important articles in SQLite, and turns the past week of coverage into audience-specific OCI executive briefings. The live Codex copy runs as two scheduled jobs on an OCI VM:

- a lightweight daily ingest that captures and filters important news into SQLite
- a weekly full pipeline that loads the last 7 days, ranks and summarizes stories, renders HTML, and sends weekly email

All model-backed stages use Oracle Code Assist's locally authenticated `codex` CLI.

---

## 2. Pipeline Architecture

```text
Daily ingest (05:00 UTC)
[1] Fetch (31 RSS feeds + Trafilatura full-text)
     ↓
[2] Compute embeddings
     ↓
[3] In-batch embedding dedup (cosine >= 0.80)
     ↓
[4] Skip URLs already stored in SQLite
     ↓
[5] Codex importance filter
     ↓
[6] Save important articles + embeddings to SQLite

Weekly digest (Monday 06:00 UTC)
[1] Load last 7 days from SQLite
     ↓
[2] Pre-score (flat-timeliness weekly mode)
     ↓
[3] Weekly embedding dedup (cosine >= 0.80)
     ↓
[4] Classify + relevance filter
     ↓
[5] Full audience score
     ↓
[6] Summarize + executive summaries
     ↓
[7] Render HTML to output/YYYY-MM-DD/
     ↓
[8] Send weekly email via Gmail-compatible SMTP
```

### Why this split

- Daily ingest keeps feed coverage fresh before RSS items rotate out.
- Embeddings are computed once during ingest and reused by the weekly digest.
- Codex importance filtering removes tutorials, opinion pieces, and other low-value feed items before the ranking pipeline sees them.
- The weekly job can deduplicate and rank across the full 7-day window rather than a single day.

---

## 3. Components

### 3.1 Ingestion (`briefing/ingest.py`, `scripts/daily_ingest.py`)

- **feedparser** polls 31 RSS feeds concurrently (ThreadPoolExecutor, 10 workers)
- **Trafilatura** + **httpx** fetches full article text from source URLs
- Falls back to RSS summary when full-text extraction fails
- Filters to articles from the last 48 hours
- Deduplicates by URL during fetch
- Daily ingest computes embeddings, performs in-batch dedup, skips URLs already stored in SQLite, then runs the Codex importance filter before saving rows

### 3.2 Deduplication

**Daily ingest dedup** (`scripts/daily_ingest.py`)

- Computes 256d embeddings for each fetched article
- Suppresses near-duplicates within the current batch at cosine >= 0.80
- Keeps the higher pre-scored article when two items collide
- Skips URLs already present in the `articles` table before making Codex calls

**Weekly digest dedup** (`scripts/weekly_pipeline.py`)

- Loads the last 7 days of stored articles and reuses `embedding_json` where available
- Computes missing embeddings in a single batch
- Suppresses weekly near-duplicates at cosine >= 0.80
- Breaks ties by score first, then source tier

**Manual full-pipeline dedup** (`app/dedup/pipeline.py`, `app/dedup/cross_day.py`)

- The one-shot `main.py` path still contains the older 5-stage in-run Jaccard pipeline plus cross-day fact-delta logic
- Those modules remain useful for experimentation and tests, but the live scheduled flow is the daily-ingest + weekly-digest split above

### 3.3 Scoring (`briefing/score.py`, `scripts/weekly_pipeline.py`)

Weekly audience scoring still uses the original per-article formula:

```text
score = source_credibility(tier) + timeliness(age) + section_relevance(weights) + keyword_bonus
```

- Source credibility: T1=30, T2=20, T3=10, T4=5
- Timeliness: <6h=15, <12h=12, <24h=8, <48h=4
- Section relevance: audience section weights × 40
- Keyword bonus: OCI-relevant keywords, max 10
- Weekly mode temporarily flattens timeliness across the 7-day window and applies date/company diversity caps per audience before rendering
- Daily ingest does not run full audience ranking; it uses lightweight scoring only for dedup tie-breaks and importance filtering

### 3.4 LLM Layer (`briefing/llm.py`)

- **Daily importance filter**: keep/drop decision for RSS items before DB persistence
- **Classification**: topics, entities, section, confidence per article
- **Summarization**: headline, 2-3 sentence summary, OCI implication per article × audience
- **Executive summaries**: 3-5 bullets + OCI implication of the day per audience
- All via `codex exec` using the locally authenticated Oracle Code Assist / Codex CLI session
- JSON cache in `output/.cache/` keyed by content hash
- Configurable concurrency (`CODEX_MAX_PARALLEL_REQUESTS`, default 5), retry with backoff, and growing timeouts per attempt

### 3.5 Rendering (`briefing/render.py`, `briefing/render_email.py`)

- Pure Python HTML/CSS generation
- Newspaper-style layout: header bar, executive summary, hero cards, compact rows
- Per-audience files plus combined index with audience switching
- Section navigation with jump links
- Separate weekly email HTML rendering path used before SMTP delivery

### 3.6 Admin Dashboard (`web/admin.html`, `app/api/routes.py`)

FastAPI admin API plus HTML SPA:

- **Articles**: browse ingested articles
- **Sources**: inspect configured feed sources
- **Clusters**: review story clusters and suppressions
- **Dedup Stats**: view suppression summaries
- **Rankings**: inspect per-audience score output
- **Clusters 3D**: interactive Plotly.js scatter plot

Served live at `http://ainews.oci-incubations.com/admin`.

---

## 4. Data Model (SQLite)

```text
articles
  id, url, title, source_name, published_at, summary, full_text,
  tier, raw_score, embedding_json (256 floats), ingest_at

story_clusters
  id, canonical_url, headline, first_seen, last_seen,
  cluster_embedding_json (256 floats), fact_snapshot

suppression_log
  id, article_id → articles, reason, similarity_score,
  matched_cluster_id → story_clusters, suppressed_at

audience_briefings
  id, audience_id, briefing_date, article_ids_json, exec_summary_json

sources
  id, domain, display_name, tier, credibility_score, rss_url, active

processing_log
  id, article_id → articles, stage, score_breakdown, created_at
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

- 768d full -> 256d Matryoshka truncation
- Supports article-body embeddings without external API calls
- Stored as JSON arrays in SQLite
- Loaded as a lazy singleton, runs fully local on the VM

---

## 7. Deployment

- **VM**: OCI compute instance
- **Services**: systemd (`ai-briefing`, `ai-briefing-admin`)
- **Reverse proxy**: nginx -> `ainews.oci-incubations.com`
- **Cron**:
  - `05:00 UTC` daily -> `scripts/daily_run.sh ingest`
  - `06:00 UTC` Monday -> `scripts/daily_run.sh weekly`
- **Ports**: 8000 (briefing server), 8002 (admin API), 80 (nginx)
- **Runtime config**: `~/.config/ai-daily-briefing-chatgpt/briefing.env`
- **Public URLs**:
  - `http://ainews.oci-incubations.com/admin`
  - `http://ainews.oci-incubations.com/YYYY-MM-DD/index.html`

---

## 8. Not Yet Implemented

- Daily rendered digest/email delivery (current daily cron is ingest-only)
- Click/link tracking
- Feedback controls (thumbs up/down)
- Full 7-dimension scoring in the scheduled pipeline
- Confidence tag vocabulary (`confirmed`, `credible_report`, `weak_signal`, `follow_up`)
- Editorial rules enforcement
- Email metrics (open/click/bounce tracking)
- Internal-source ingestion beyond external RSS feeds

See `docs/GAP_ANALYSIS.md` for the current gap list.
