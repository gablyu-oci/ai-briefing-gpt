# AI Daily Executive Briefing — Oracle Code Assist / Codex Copy

Automated intelligence digest for OCI executives. This Codex copy captures important external news every day, stores deduplicated articles in SQLite, and produces a weekly multi-audience briefing website plus email delivery. It uses Oracle Code Assist authentication through the local `codex` CLI for all LLM calls and does not require `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`.

## How It Works

```text
Daily ingest (05:00 UTC)
  → Fetch RSS feeds + full article text
  → Compute embeddings
  → Deduplicate within the batch
  → Skip URLs already stored in SQLite
  → Codex importance filter (keep only material news)
  → Save important articles + embeddings to SQLite

Weekly digest (Monday 06:00 UTC)
  → Load last 7 days from SQLite
  → Weekly embedding dedup
  → Classify + relevance filter
  → Score per audience (4 executives)
  → Summarize + generate executive summaries
  → Render HTML
  → Send weekly email via Gmail-compatible SMTP
```

## Quick Start

```bash
cd /home/ubuntu/projects/ai-daily-briefing-codex

# Optional but recommended
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
python3 -m spacy download en_core_web_sm

# Confirm Codex CLI is installed and available
codex --version

# Authenticate Codex via Oracle Code Assist
# Option A: run Oracle's "Copy Codex Environment Setup Command"
# Option B:
#   echo "<your_oracle_code_assist_api_key>" | codex login --with-api-key
codex login status

# Daily ingest (used by the daily cron job)
python3 scripts/daily_ingest.py

# Weekly digest render + email (used by the weekly cron job)
python3 scripts/weekly_pipeline.py

# Optional one-shot full run from fresh feeds
python3 main.py --dry-run

# Preview static briefing pages
python3 serve.py --no-browser

# Run the admin API separately
python3 -m uvicorn app.api.routes:app --host 127.0.0.1 --port 8002
```

Scheduled runs load environment variables from `~/.config/ai-daily-briefing-chatgpt/briefing.env`. The config directory still uses the older `ai-daily-briefing-chatgpt` name for compatibility with the existing VM setup.

## Key Features

- **Daily importance filter**: a Codex pass removes tutorials, explainers, opinion pieces, and low-signal feed items before they enter the database
- **Embedding-based dedup**: nomic-embed-text-v1.5 (256d Matryoshka) detects same stories across different sources and days
- **Fact-delta scoring**: 6-signal system distinguishes story updates from repeats (new numbers, entities, quotes, verb progression)
- **Full article extraction**: Trafilatura fetches article body text for richer embeddings and summaries
- **SpaCy NER**: proper named entity recognition for fact extraction
- **Per-audience personalization**: 4 executive profiles with different section weights and tone guidance
- **Admin dashboard**: articles, clusters, dedup stats, rankings, interactive 3D cluster visualization
- **Weekly email delivery**: Gmail-compatible SMTP send at the end of the weekly pipeline
- **31 RSS sources**: Tier 1 (Bloomberg, WSJ, FT, CNBC, Reuters), Tier 2 (TechCrunch, Ars Technica, KrebsOnSecurity, etc.), Tier 3 (vendor blogs), Tier 4 (HN, Reddit)

## Audiences

| Name | Title | Focus |
|---|---|---|
| Karan Batta | SVP Product | Financial signals, competitive positioning |
| Nathan Thomas | SVP Product | Multi-cloud ecosystem, partnerships |
| Greg Pavlik | EVP Data & AI | Technical competitive moves, AI infrastructure |
| Mahesh Thiagarajan | EVP Security | Datacenter/power, security, developer platform |

## Tech Stack

| Component | Technology |
|---|---|
| Embedding model | nomic-embed-text-v1.5 (local, CPU) |
| NER | SpaCy en_core_web_sm |
| Full text extraction | Trafilatura + httpx |
| LLM | `codex exec` via Oracle Code Assist / Codex auth |
| Database | SQLite |
| Admin API | FastAPI |
| Visualization | Plotly.js + UMAP + HDBSCAN |
| Email delivery | Gmail-compatible SMTP |
| Scheduling | cron + systemd |
| Web server | nginx reverse proxy |

## Deployment

Runs on an OCI VM with:
- daily ingest cron at `05:00 UTC` via `scripts/daily_run.sh ingest`
- weekly full digest cron at `06:00 UTC` every Monday via `scripts/daily_run.sh weekly`
- `systemctl` services for briefing server (`ai-briefing`, port 8000) and admin API (`ai-briefing-admin`, port 8002)
- nginx reverse proxy at `ainews.oci-incubations.com`
- config loaded from `~/.config/ai-daily-briefing-chatgpt/briefing.env`
- public URLs:
  - `http://ainews.oci-incubations.com/admin`
  - `http://ainews.oci-incubations.com/YYYY-MM-DD/index.html`

## Project Structure

```text
main.py                  — one-shot full pipeline from fresh feeds
briefing/
  config.py              — 31 RSS sources, 4 audience profiles
  ingest.py              — RSS fetching + Trafilatura full-text
  score.py               — per-audience scoring
  llm.py                 — `codex exec` wrapper (filter, classify, summarize)
  render.py              — briefing HTML generation
  render_email.py        — weekly email HTML rendering
app/
  dedup/                 — in-run + cross-day dedup, embeddings, fingerprinting
  db/                    — SQLAlchemy models
  api/                   — FastAPI admin endpoints
  delivery/              — Gmail-compatible SMTP delivery
scripts/
  daily_ingest.py        — daily lightweight ingest into SQLite
  weekly_pipeline.py     — weekly briefing render + email from SQLite
  daily_run.sh           — cron wrapper used on the VM
serve.py                 — static server for briefing pages
web/admin.html           — admin dashboard
docs/
  ARCHITECTURE.md        — system architecture
  GAP_ANALYSIS.md        — feature status
  PRD.md                 — product requirements
  archive/               — historical research/design docs (may reference Claude/Postmark)
```

## Documentation

- [ORACLE_CODE_ASSIST.md](ORACLE_CODE_ASSIST.md) — developer guide for the Oracle Code Assist / Codex-auth version
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — system architecture
- [docs/GAP_ANALYSIS.md](docs/GAP_ANALYSIS.md) — feature status and remaining work
- [docs/PRD.md](docs/PRD.md) — product requirements document
- [docs/archive/README.md](docs/archive/README.md) — historical planning docs; not the source of truth for the live Codex deployment
