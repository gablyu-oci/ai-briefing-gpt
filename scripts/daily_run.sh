#!/bin/bash
# AI Daily Briefing — ChatGPT / Codex cron wrapper
# Daily at 5 AM UTC — lightweight ingest + Codex importance filter
# Weekly on Monday at 6 AM UTC — full pipeline + email delivery
#
# Crontab entries:
#   0 5 * * * /home/ubuntu/projects/ai-daily-briefing-codex/scripts/daily_run.sh ingest
#   0 6 * * 1 /home/ubuntu/projects/ai-daily-briefing-codex/scripts/daily_run.sh weekly
#
# This wrapper is for the Codex copy only. The env file lives under the
# legacy config directory name ~/.config/ai-daily-briefing-chatgpt/ so the
# current VM setup does not need to move secrets.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONFIG_DIR="${HOME}/.config/ai-daily-briefing-chatgpt"
ENV_FILE="${CONFIG_DIR}/briefing.env"

cd "$PROJECT_ROOT"

if [ -f "$ENV_FILE" ]; then
    set -a
    # shellcheck disable=SC1090
    . "$ENV_FILE"
    set +a
fi

MODE="${1:-ingest}"

mkdir -p logs

if [ "$MODE" = "weekly" ]; then
    echo "=== Weekly pipeline started at $(date -u) ===" >> logs/weekly_pipeline.log
    /usr/bin/python3 scripts/weekly_pipeline.py >> logs/weekly_pipeline.log 2>&1
    echo "=== Weekly pipeline completed at $(date -u) ===" >> logs/weekly_pipeline.log
else
    echo "=== Daily ingest started at $(date -u) ===" >> logs/daily_ingest.log
    /usr/bin/python3 scripts/daily_ingest.py >> logs/daily_ingest.log 2>&1
    echo "=== Daily ingest completed at $(date -u) ===" >> logs/daily_ingest.log
fi
