"""
llm.py — Oracle Code Assist / Codex CLI integration.

Uses `codex exec` non-interactively for classification, per-article
summaries, and executive summaries. Authentication is handled by the local
Codex CLI login state, which matches Oracle Code Assist's weekly API-key
setup flow.
"""

import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from threading import BoundedSemaphore
from typing import Any

from config.settings import (
    CACHE_DIR,
    CODEX_BIN,
    CODEX_CLASSIFIER_MODEL,
    CODEX_CLASSIFIER_PROFILE,
    CODEX_EXEC_SUMMARY_MODEL,
    CODEX_EXEC_SUMMARY_PROFILE,
    CODEX_MAX_PARALLEL_REQUESTS,
    CODEX_SUMMARY_MODEL,
    CODEX_SUMMARY_PROFILE,
    LLM_CLASSIFY_TIMEOUT,
    LLM_EXEC_SUMMARY_TIMEOUT,
    LLM_MAX_RETRIES,
    LLM_REQUEST_TIMEOUT_GROWTH,
    LLM_RETRY_BACKOFF,
    LLM_SUMMARY_TIMEOUT,
    PROJECT_ROOT,
)

logger = logging.getLogger(__name__)

_codex_checked = False
_codex_slots = BoundedSemaphore(max(1, CODEX_MAX_PARALLEL_REQUESTS))


def _resolve_codex_bin() -> str:
    if os.path.sep in CODEX_BIN:
        if Path(CODEX_BIN).exists():
            return CODEX_BIN
    resolved = shutil.which(CODEX_BIN)
    if resolved:
        return resolved
    raise RuntimeError(
        "codex CLI not found. Install Codex CLI or set CODEX_BIN to the executable path."
    )


def _ensure_codex_ready() -> str:
    global _codex_checked
    codex_bin = _resolve_codex_bin()
    if _codex_checked:
        return codex_bin

    try:
        result = subprocess.run(
            [codex_bin, "login", "status"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(PROJECT_ROOT),
        )
    except Exception as exc:
        raise RuntimeError(f"Failed to check Codex login status: {exc}") from exc

    if result.returncode != 0:
        details = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(
            "Codex CLI is not authenticated. Run Oracle's 'Copy Codex Environment Setup Command' "
            "or `codex login --with-api-key` first."
            + (f" Details: {details}" if details else "")
        )

    _codex_checked = True
    return codex_bin


def _format_process_error(result: subprocess.CompletedProcess[str]) -> str:
    stderr = (result.stderr or "").strip()
    stdout = (result.stdout or "").strip()
    combined = "\n".join(part for part in (stderr, stdout) if part).strip()
    if not combined:
        return f"exit code {result.returncode}"
    lines = combined.splitlines()
    return "\n".join(lines[-12:])


def call_codex(
    prompt: str,
    *,
    profile: str = "",
    model: str = "",
    timeout: int = 120,
) -> str:
    """
    Invoke `codex exec` as a non-interactive subprocess and return the last
    assistant message.
    """
    codex_bin = _ensure_codex_ready()

    for attempt in range(1, LLM_MAX_RETRIES + 1):
        attempt_timeout = max(
            timeout,
            int(round(timeout * (LLM_REQUEST_TIMEOUT_GROWTH ** (attempt - 1)))),
        )
        try:
            with _codex_slots:
                with tempfile.TemporaryDirectory(prefix="briefing_codex_", dir="/tmp") as temp_dir:
                    output_path = Path(temp_dir) / "last_message.txt"
                    cmd = [
                        codex_bin,
                        "exec",
                        "--skip-git-repo-check",
                        "--sandbox",
                        "read-only",
                        "--color",
                        "never",
                        "--ephemeral",
                        "--output-last-message",
                        str(output_path),
                    ]
                    if profile:
                        cmd.extend(["--profile", profile])
                    if model:
                        cmd.extend(["--model", model])
                    cmd.append("-")

                    result = subprocess.run(
                        cmd,
                        input=prompt,
                        capture_output=True,
                        text=True,
                        timeout=attempt_timeout,
                        cwd=str(PROJECT_ROOT),
                    )
                    if result.returncode == 0 and output_path.exists():
                        text = output_path.read_text().strip()
                        if text:
                            return text
                    raise RuntimeError(_format_process_error(result))
        except subprocess.TimeoutExpired as exc:
            logger.warning(
                "Codex attempt %d/%d timed out after %ds (profile=%s model=%s)",
                attempt,
                LLM_MAX_RETRIES,
                attempt_timeout,
                profile or "<default>",
                model or "<default>",
            )
            err = f"timeout after {attempt_timeout}s"
        except Exception as exc:
            logger.warning(
                "Codex attempt %d/%d failed after %ds (profile=%s model=%s): %s",
                attempt,
                LLM_MAX_RETRIES,
                attempt_timeout,
                profile or "<default>",
                model or "<default>",
                exc,
            )
            err = str(exc)

        if attempt < LLM_MAX_RETRIES:
            time.sleep(LLM_RETRY_BACKOFF * attempt)

    raise RuntimeError(f"Codex request failed after {LLM_MAX_RETRIES} attempts: {err}")


def _cache_key(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:24]


def _cache_path(kind: str, key: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{kind}_{key}.json"


def _cache_get(kind: str, key: str) -> Any | None:
    path = _cache_path(kind, key)
    if path.exists():
        try:
            return json.loads(path.read_text())
        except json.JSONDecodeError:
            logger.warning("Ignoring malformed cache file: %s", path)
    return None


def _cache_set(kind: str, key: str, value: Any) -> None:
    _cache_path(kind, key).write_text(json.dumps(value, indent=2, default=str))


def _strip_code_fences(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-zA-Z0-9_-]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)
    return raw.strip()


def _load_json_response(raw: str) -> dict:
    cleaned = _strip_code_fences(raw)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def classify_article(article: dict) -> dict:
    """
    Classify an article using Codex / Oracle Code Assist.
    """
    model_key = CODEX_CLASSIFIER_PROFILE or CODEX_CLASSIFIER_MODEL or "default"
    cache_key = _cache_key(f"classify:{model_key}:{article['url']}")
    cached = _cache_get("classify", cache_key)
    if cached:
        return cached

    prompt = f"""You are an editorial classifier for an OCI executive technology briefing.

Classify this article and respond ONLY with valid JSON (no markdown, no code fences).
Use ONLY the article text below. Do not use tools, shell commands, repository inspection, or web search.

Article title: {article['title']}
Source: {article['source']}
Summary: {article.get('full_text', '')[:1500] or article.get('summary', '')[:800]}

Allowed sections: financial, compete, ai, datacenter, power, deals, security, multicloud, oss, partnerships, community, infrastructure

Return this exact JSON structure:
{{
  "topics": ["topic1", "topic2"],
  "entities": ["entity1", "entity2"],
  "sections": ["primary_section", "optional_secondary"],
  "section": "primary_section",
  "confidence": "one of: high, medium, low",
  "executive_relevance": "one of: high, medium, low"
}}

Rules:
- topics: 2-4 short topic tags
- entities: company names, people, products mentioned (max 5)
- sections: 1-3 sections this article belongs to, ordered by relevance
- section: the single primary section (same as the first item in sections)
- confidence: high if clearly relevant to cloud/AI/tech enterprise, medium if tangential, low if unclear
- executive_relevance: high for major launches, earnings, infrastructure buildouts, security issues, regulatory changes, or strategic deals
- Be generous with multi-section assignment when an article clearly spans more than one category"""

    should_cache = True

    try:
        raw = call_codex(
            prompt,
            profile=CODEX_CLASSIFIER_PROFILE,
            model=CODEX_CLASSIFIER_MODEL,
            timeout=LLM_CLASSIFY_TIMEOUT,
        )
        result = _load_json_response(raw)
        if not isinstance(result.get("sections"), list) or not result.get("sections"):
            section = result.get("section") or (
                article["sections"][0] if article.get("sections") else "compete"
            )
            result["sections"] = [section]
        if not result.get("section"):
            result["section"] = result["sections"][0]
        result.setdefault("executive_relevance", "medium")
    except (json.JSONDecodeError, RuntimeError) as exc:
        logger.warning("classify_article failed for %s: %s", article["url"][:60], exc)
        fallback_section = article["sections"][0] if article.get("sections") else "compete"
        result = {
            "topics": [],
            "entities": [],
            "sections": [fallback_section],
            "section": fallback_section,
            "confidence": "low",
            "executive_relevance": "low",
        }
        should_cache = False

    if should_cache:
        _cache_set("classify", cache_key, result)
    return result


def filter_important_for_daily_ingest(article: dict) -> dict:
    """
    Decide whether an article is important enough to retain during the
    lightweight daily ingest stage.

    This is intentionally narrower than full classification: it keeps
    timely, reportable developments and drops tutorials, evergreen
    explainers, and other low-signal feed items.
    """
    model_key = CODEX_CLASSIFIER_PROFILE or CODEX_CLASSIFIER_MODEL or "default"
    cache_key = _cache_key(f"ingest_filter:{model_key}:{article['url']}")
    cached = _cache_get("ingest_filter", cache_key)
    if cached:
        return cached

    prompt = f"""You are an editorial gatekeeper for an OCI executive intelligence pipeline.

Decide whether this RSS item is important enough to keep in the database for the weekly executive briefing.
Respond ONLY with valid JSON (no markdown, no code fences).
Use ONLY the article text below. Do not use tools, shell commands, repository inspection, or web search.

Article title: {article['title']}
Source: {article['source']}
Summary: {article.get('full_text', '')[:1200] or article.get('summary', '')[:700]}

Return this exact JSON structure:
{{
  "keep": true,
  "importance": "one of: high, medium, low",
  "reason": "short reason"
}}

Rules:
- keep=true for timely, reportable developments relevant to OCI leadership: launches, earnings, funding, partnerships, deals, infrastructure buildouts, model releases, security incidents, regulation, enterprise adoption, notable open-source momentum, major product updates, leadership changes, or strategic ecosystem moves
- keep=false for tutorials, how-to guides, explainers, listicles, buying guides, opinion pieces, generic productivity advice, broad trend essays without a new event, or low-signal community chatter
- If the item contains a concrete new event or fact that could matter strategically, prefer keep=true
- importance=low when the item is clearly not important news
- reason should be very short, e.g. "tutorial", "major funding", "security incident", "product launch"
"""

    should_cache = True

    try:
        raw = call_codex(
            prompt,
            profile=CODEX_CLASSIFIER_PROFILE,
            model=CODEX_CLASSIFIER_MODEL,
            timeout=LLM_CLASSIFY_TIMEOUT,
        )
        result = _load_json_response(raw)
        keep = result.get("keep")
        if isinstance(keep, str):
            keep = keep.strip().lower() in {"true", "yes", "1", "keep"}
        elif keep is None:
            keep = str(result.get("importance", "medium")).strip().lower() != "low"

        result = {
            "keep": bool(keep),
            "importance": str(result.get("importance", "medium")).strip().lower() or "medium",
            "reason": str(result.get("reason", "")).strip() or "no reason provided",
        }
    except (json.JSONDecodeError, RuntimeError) as exc:
        logger.warning(
            "filter_important_for_daily_ingest failed for %s: %s",
            article["url"][:60],
            exc,
        )
        result = {
            "keep": True,
            "importance": "unknown",
            "reason": "filter_failed_keep_article",
        }
        should_cache = False

    if should_cache:
        _cache_set("ingest_filter", cache_key, result)
    return result


def generate_summary(article: dict, audience_profile: dict) -> dict:
    """
    Generate a personalized headline, summary, and OCI implication using
    Codex / Oracle Code Assist.
    """
    model_key = CODEX_SUMMARY_PROFILE or CODEX_SUMMARY_MODEL or "default"
    cache_key = _cache_key(
        f"summary:{model_key}:{article['url']}:{audience_profile['id']}"
    )
    cached = _cache_get("summary", cache_key)
    if cached:
        return cached

    pub_str = (
        article["published_at"].strftime("%Y-%m-%d %H:%M UTC")
        if hasattr(article["published_at"], "strftime")
        else str(article["published_at"])
    )

    prompt = f"""You are the editorial AI for an executive intelligence briefing delivered to OCI senior leadership.

Your audience: {audience_profile['name']}, {audience_profile['title']}
Tone: {audience_profile['tone_guidance']}

    Write a personalized briefing item and respond ONLY with valid JSON (no markdown, no code fences).
    Use ONLY the article text below. Do not use tools, shell commands, repository inspection, or web search.

Article title: {article['title']}
Source: {article['source']} (published: {pub_str})
Summary: {article.get('full_text', '')[:2200] or article.get('summary', '')[:1200]}

Return this exact JSON structure:
{{
  "headline": "A rewritten, punchy 10-15 word headline optimized for this executive",
  "summary": "2-3 sentences. Lead with the most important fact. Add context. End with the strategic implication.",
  "oci_implication": "1-2 sentences on what this means for OCI's strategy or operations."
}}"""

    should_cache = True

    try:
        raw = call_codex(
            prompt,
            profile=CODEX_SUMMARY_PROFILE,
            model=CODEX_SUMMARY_MODEL,
            timeout=LLM_SUMMARY_TIMEOUT,
        )
        result = _load_json_response(raw)
    except (json.JSONDecodeError, RuntimeError) as exc:
        logger.warning(
            "generate_summary failed for %s (%s): %s",
            article["url"][:60],
            audience_profile["id"],
            exc,
        )
        result = {
            "headline": article["title"],
            "summary": article.get("summary", "")[:300],
            "oci_implication": "Assess impact on OCI strategy.",
        }
        should_cache = False

    if should_cache:
        _cache_set("summary", cache_key, result)
    return result


def generate_executive_summary(top_articles: list[dict], audience_profile: dict) -> dict:
    """
    Generate a 3-5 bullet executive summary, a market outlook, and an OCI
    implication of the day for an audience.
    """
    model_key = CODEX_EXEC_SUMMARY_PROFILE or CODEX_EXEC_SUMMARY_MODEL or "default"
    cache_key = _cache_key(
        f"exec_summary:{model_key}:{audience_profile['id']}:"
        + ":".join(a["url"] for a in top_articles[:12])
    )
    cached = _cache_get("exec_summary", cache_key)
    if cached:
        return cached

    articles_text = "\n\n".join(
        f"[{i + 1}] {a['title']} ({a['source']})\n{a.get('summary', '')[:400]}"
        for i, a in enumerate(top_articles[:12])
    )

    prompt = f"""You are the chief editorial AI for an executive intelligence briefing for OCI senior leadership.

Your audience: {audience_profile['name']}, {audience_profile['title']}
Tone: {audience_profile['tone_guidance']}

    Based on today's top stories, write an executive briefing summary and respond ONLY with valid JSON (no markdown, no code fences).
    Use ONLY the stories below. Do not use tools, shell commands, repository inspection, or web search.

TOP STORIES:
{articles_text}

Return this exact JSON structure:
{{
  "bullets": [
    "Bullet 1: the single most important development today",
    "Bullet 2: second key development",
    "Bullet 3: third key development"
  ],
  "market_outlook": "2-3 sentences. Based on today's top stories, where is the market heading?",
  "oci_implication_of_day": "2-3 sentences. The single most important strategic implication for OCI leadership today."
}}

Rules:
- 3-5 bullets only
- Each bullet must be a complete, standalone insight
- The market outlook must be concrete and forward-looking
- The OCI implication must be actionable and specific"""

    should_cache = True

    try:
        raw = call_codex(
            prompt,
            profile=CODEX_EXEC_SUMMARY_PROFILE,
            model=CODEX_EXEC_SUMMARY_MODEL,
            timeout=LLM_EXEC_SUMMARY_TIMEOUT,
        )
        result = _load_json_response(raw)
        if not isinstance(result.get("bullets"), list):
            result["bullets"] = [str(result.get("bullets", ""))]
    except (json.JSONDecodeError, RuntimeError) as exc:
        logger.warning(
            "generate_executive_summary failed for %s: %s",
            audience_profile["id"],
            exc,
        )
        result = {
            "bullets": [
                "Multiple significant developments across cloud, AI, and infrastructure today.",
                "Competitive landscape continues to shift; see individual stories for detail.",
            ],
            "market_outlook": (
                "Market dynamics continue to evolve as hyperscalers and AI labs invest heavily in "
                "capacity, partnerships, and model differentiation."
            ),
            "oci_implication_of_day": (
                "Review the top stories for the most immediate implications to OCI strategy, "
                "capacity planning, and competitive positioning."
            ),
        }
        should_cache = False

    if should_cache:
        _cache_set("exec_summary", cache_key, result)
    return result
