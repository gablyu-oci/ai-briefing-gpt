# AI Daily Briefing — Oracle Code Assist / Codex Instructions

## What Changed

This copy uses the local `codex` CLI for all LLM calls.
Authentication comes from Oracle Code Assist's weekly API-key flow rather than `OPENAI_API_KEY`.

## Prerequisites

- Python 3.10+ available locally
- `codex` CLI installed and reachable on your `PATH`
- An Oracle Code Assist API key that you refresh every 7 days

## Setup

```bash
cd /home/ubuntu/projects/ai-daily-briefing-codex

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
python3 -m spacy download en_core_web_sm
codex --version
```

Then authenticate Codex through Oracle Code Assist:

1. Run Oracle's "Copy Codex Environment Setup Command", or
2. Run:

```bash
echo "<your_oracle_code_assist_api_key>" | codex login --with-api-key
```

Verify:

```bash
codex login status
```

Oracle Code Assist API keys expire every 7 days. Refresh the key and rerun the login flow before the token expires, or model-backed stages will start failing.

If `codex` is installed but not on your `PATH`, point the app at it explicitly:

```bash
export CODEX_BIN="/full/path/to/codex"
```

## Running

```bash
# Daily ingest used by cron
python3 scripts/daily_ingest.py

# Weekly digest used by cron
python3 scripts/weekly_pipeline.py
python3 scripts/weekly_pipeline.py --audience karan

# Optional one-shot full run from fresh feeds
python3 main.py --dry-run
python3 main.py

# Static briefing preview
python3 serve.py --no-browser

# Admin API
python3 -m uvicorn app.api.routes:app --host 127.0.0.1 --port 8002
```

## Optional Overrides

If your default Oracle Code Assist profile is not the one you want, set one or more of these:

```bash
export CODEX_PROFILE="gpt-5-4"
export CODEX_CLASSIFIER_PROFILE="gpt-5-4"
export CODEX_SUMMARY_PROFILE="gpt-5-4"
export CODEX_EXEC_SUMMARY_PROFILE="gpt-5-4"
```

You can also override by model name directly if needed:

```bash
export CODEX_MODEL="oca/gpt-5.4"
```

Profile overrides are preferred because they align with your local `~/.codex/config.toml`.

Typical setup is to set only `CODEX_PROFILE`. The per-stage overrides are there if you want different profiles for classification vs summaries.

## Scheduled Runtime

- The VM cron wrapper is `scripts/daily_run.sh`.
- Scheduled env vars are loaded from `~/.config/ai-daily-briefing-chatgpt/briefing.env`.
- The config directory keeps the older `ai-daily-briefing-chatgpt` name for compatibility with the existing VM deployment.
- Weekly email delivery reads SMTP settings from env vars such as:
  - `GMAIL_USER`
  - `GMAIL_FROM_EMAIL`
  - `GMAIL_APP_PASSWORD` or `GMAIL_SECRET_FILE`
  - `BRIEFING_EMAIL_KARAN`, `BRIEFING_EMAIL_NATHAN`, `BRIEFING_EMAIL_GREG`, `BRIEFING_EMAIL_MAHESH`

## Key Conventions

- LLM calls go through `briefing/llm.py` using `codex exec`.
- `app/llm/client.py` is a thin wrapper around `briefing/llm.py`.
- Cache files are stored in `output/.cache/` and prefixed by task type (`classify_`, `summary_`, `exec_summary_`).
- Dry runs do not require live model access.
- In offline environments, embeddings fall back to a deterministic hashed lexical representation so tests and dry runs still work.

## Troubleshooting

- `python3 main.py --dry-run` should work even without live Oracle model access.
- If model calls fail, rerun Oracle's setup command or refresh your 7-day Oracle Code Assist API key.
- If the default model is not entitled for your account, set `CODEX_PROFILE` to a profile you do have access to.
- If `codex login status` fails, fix that before running the briefing pipeline.
- If you see `codex CLI not found`, install Codex CLI or export `CODEX_BIN` to the executable path.
- If weekly email sends are stubbed instead of real, verify the SMTP/Gmail env vars in `~/.config/ai-daily-briefing-chatgpt/briefing.env`.
