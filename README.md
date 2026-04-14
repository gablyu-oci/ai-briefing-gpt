# AI Daily Executive Briefing — Oracle Code Assist / Codex Copy

Automated intelligence digest for OCI executives. Aggregates news from 31 sources, deduplicates using sentence embeddings, and delivers personalized daily briefings. This copy uses Oracle Code Assist authentication through the local `codex` CLI for all LLM calls and does not require `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`.

## How It Works

```
Fetch (31 RSS feeds + full article text)
  → Pre-score (source credibility + timeliness)
  → In-run dedup (Jaccard word overlap)
  → Cross-day dedup (embedding similarity vs 7-day cluster history)
  → Classify (Codex / Oracle Code Assist)
  → Score per audience (4 executives)
  → Summarize (Codex / Oracle Code Assist)
  → Executive summaries (Codex / Oracle Code Assist)
  → Render HTML
```

## Quick Start

```bash
cd /home/ubuntu/projects/ai-daily-briefing-chatgpt

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
# Then verify:
codex login status

# If codex is installed outside PATH, point the app at it
# export CODEX_BIN="/full/path/to/codex"

# Optional model/profile overrides
# export CODEX_PROFILE="gpt-5-4"
# export CODEX_SUMMARY_PROFILE="gpt-5-4"

# Dry run (no LLM calls, placeholder text)
python3 main.py --dry-run

# Full run
python3 main.py

# Preview output
python3 serve.py --no-browser
# Open http://localhost:8000/
```

## Key Features

- **Embedding-based dedup**: nomic-embed-text-v1.5 (256d Matryoshka) detects same stories across different sources and days
- **Fact-delta scoring**: 6-signal system distinguishes story updates from repeats (new numbers, entities, quotes, verb progression)
- **Full article extraction**: Trafilatura fetches article body text for richer embeddings and summaries
- **SpaCy NER**: proper named entity recognition for fact extraction
- **Per-audience personalization**: 4 executive profiles with different section weights and tone guidance
- **Admin dashboard**: articles, clusters, dedup stats, rankings, interactive 3D cluster visualization
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
| Web server | nginx reverse proxy |

## Deployment

Runs on OCI VM with:
- `systemctl` services for briefing server (8000) and admin API (8002)
- nginx reverse proxy at `ainews.oci-incubations.com`
- Daily cron at 5:00 AM UTC

## Project Structure

```
main.py                  — 9-step pipeline orchestrator
briefing/
  config.py              — 31 RSS sources, 4 audience profiles
  ingest.py              — RSS fetching + Trafilatura full-text
  score.py               — per-audience scoring
  llm.py                 — `codex exec` wrapper (classify, summarize)
  render.py              — HTML generation
app/
  dedup/                 — in-run + cross-day dedup, embeddings, fingerprinting
  db/                    — SQLAlchemy models
  api/                   — FastAPI admin endpoints
web/admin.html           — admin dashboard
docs/
  ARCHITECTURE.md        — system architecture
  GAP_ANALYSIS.md        — feature status
  PRD.md                 — product requirements
```

## Documentation

- [ORACLE_CODE_ASSIST.md](ORACLE_CODE_ASSIST.md) — developer guide for the Oracle Code Assist / Codex-auth version
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — system architecture
- [docs/GAP_ANALYSIS.md](docs/GAP_ANALYSIS.md) — feature status and remaining work
- [docs/PRD.md](docs/PRD.md) — product requirements document
