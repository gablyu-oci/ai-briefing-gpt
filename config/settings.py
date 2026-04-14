"""
settings.py — Environment and global configuration for the AI Daily Briefing system.
"""

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_ROOT = PROJECT_ROOT / "output"
DB_PATH = OUTPUT_ROOT / "briefing.db"
CACHE_DIR = OUTPUT_ROOT / ".cache"

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{DB_PATH}")

# ---------------------------------------------------------------------------
# Pipeline settings
# ---------------------------------------------------------------------------
INGEST_WINDOW_HOURS = int(os.environ.get("INGEST_WINDOW_HOURS", "48"))
MAX_ARTICLES_TO_CLASSIFY = int(os.environ.get("MAX_ARTICLES_TO_CLASSIFY", "60"))
TOP_ARTICLES_PER_AUDIENCE = int(os.environ.get("TOP_ARTICLES_PER_AUDIENCE", "12"))
MAX_CONCURRENT_LLM = int(os.environ.get("MAX_CONCURRENT_LLM", "5"))
CODEX_MAX_PARALLEL_REQUESTS = int(
    os.environ.get("CODEX_MAX_PARALLEL_REQUESTS", str(MAX_CONCURRENT_LLM))
)

# ---------------------------------------------------------------------------
# LLM
# ---------------------------------------------------------------------------
CODEX_BIN = os.environ.get("CODEX_BIN", "codex").strip() or "codex"
CODEX_PROFILE = os.environ.get("CODEX_PROFILE", "").strip()
CODEX_MODEL = os.environ.get("CODEX_MODEL", "").strip()
CODEX_CLASSIFIER_PROFILE = os.environ.get("CODEX_CLASSIFIER_PROFILE", CODEX_PROFILE).strip()
CODEX_SUMMARY_PROFILE = os.environ.get("CODEX_SUMMARY_PROFILE", CODEX_PROFILE).strip()
CODEX_EXEC_SUMMARY_PROFILE = os.environ.get("CODEX_EXEC_SUMMARY_PROFILE", CODEX_SUMMARY_PROFILE).strip()
CODEX_CLASSIFIER_MODEL = os.environ.get("CODEX_CLASSIFIER_MODEL", CODEX_MODEL).strip()
CODEX_SUMMARY_MODEL = os.environ.get("CODEX_SUMMARY_MODEL", CODEX_MODEL).strip()
CODEX_EXEC_SUMMARY_MODEL = os.environ.get("CODEX_EXEC_SUMMARY_MODEL", CODEX_SUMMARY_MODEL).strip()
LLM_MAX_RETRIES = int(os.environ.get("LLM_MAX_RETRIES", "3"))
LLM_RETRY_BACKOFF = float(os.environ.get("LLM_RETRY_BACKOFF", "2.0"))
LLM_REQUEST_TIMEOUT_GROWTH = float(os.environ.get("LLM_REQUEST_TIMEOUT_GROWTH", "1.5"))
LLM_CLASSIFY_TIMEOUT = int(os.environ.get("LLM_CLASSIFY_TIMEOUT", "90"))
LLM_SUMMARY_TIMEOUT = int(os.environ.get("LLM_SUMMARY_TIMEOUT", "120"))
LLM_EXEC_SUMMARY_TIMEOUT = int(os.environ.get("LLM_EXEC_SUMMARY_TIMEOUT", "180"))

# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------
SERVER_HOST = os.environ.get("SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.environ.get("SERVER_PORT", "8000"))
