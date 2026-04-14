"""
Fact extraction and delta scoring for cross-day deduplication.

Extracts structured facts (numbers, entities, quotes) from articles using
SpaCy NER (with regex fallback), then scores how much genuinely new information a
candidate article carries compared to an already-seen canonical cluster.
"""

import logging
import math
import re
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# Numbers with optional magnitude suffix (e.g. "3.5 billion", "12%", "400mn")
_NUMBER_RE = re.compile(
    r"\b\d[\d,.]*\s*(?:%|bn|billion|million|thousand|mn)?\b",
    re.IGNORECASE,
)

# Multi-word capitalised names (minimum two consecutive capitalised words)
_ENTITY_RE = re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+")

# Quoted strings between 15 and 100 characters
_QUOTE_RE = re.compile(r'"[^"]{15,100}"')

# Verbs that signal story progression / escalation
_PROGRESSION_VERBS = {
    "completes",
    "finalizes",
    "confirms",
    "approves",
    "launches",
    "closes",
    "signs",
    "announces",
}

# ---------------------------------------------------------------------------
# SpaCy NER (lazy-loaded singleton)
# ---------------------------------------------------------------------------

_nlp = None

def _get_nlp():
    """Lazy-load the SpaCy English model (singleton)."""
    global _nlp
    if _nlp is None:
        import spacy
        _nlp = spacy.load("en_core_web_sm")
    return _nlp

_NER_LABELS = {"PERSON", "ORG", "GPE", "PRODUCT", "EVENT", "MONEY"}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _safe_text(article: dict) -> str:
    """Combine title and best available body text into a single searchable string."""
    title = article.get("title") or ""
    body = article.get("full_text") or article.get("summary") or ""
    return f"{title} {body}"


def _parse_datetime(value) -> datetime:
    """Best-effort parse of a datetime value into a timezone-aware datetime.

    Accepts ``datetime`` objects, ISO-format strings, or ``None``.  Returns
    a UTC ``datetime``; falls back to *now* when parsing fails.
    """
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    if isinstance(value, str) and value:
        for fmt in (
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S.%f%z",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
        ):
            try:
                dt = datetime.strptime(value, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError:
                continue

    logger.debug("Could not parse datetime value %r; falling back to utcnow", value)
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_facts(article: dict) -> dict:
    """Extract structured facts from an article dict.

    Parameters
    ----------
    article : dict
        Must contain at least ``title`` and ``summary`` keys.  Other keys
        (``url``, ``published_at``, ``source``, ...) are ignored here.

    Returns
    -------
    dict
        ``{"numbers": [...], "entities": [...], "quotes": [...]}``
    """
    text = _safe_text(article)

    numbers = _NUMBER_RE.findall(text)
    # Normalise whitespace inside each match for cleaner comparisons
    numbers = [n.strip() for n in numbers]

    # Entity extraction via SpaCy NER
    try:
        nlp = _get_nlp()
        doc = nlp(text[:10000])  # cap input length for performance
        entities = list(dict.fromkeys(
            ent.text.strip() for ent in doc.ents if ent.label_ in _NER_LABELS
        ))
    except Exception as exc:
        logger.warning("SpaCy NER failed, falling back to regex: %s", exc)
        entities = _ENTITY_RE.findall(text)

    quotes = _QUOTE_RE.findall(text)

    logger.debug(
        "Extracted facts  numbers=%d  entities=%d  quotes=%d  from article '%s'",
        len(numbers),
        len(entities),
        len(quotes),
        (article.get("title") or "")[:60],
    )

    return {
        "numbers": numbers,
        "entities": entities,
        "quotes": quotes,
    }


def compute_fact_delta(canonical_facts: dict, candidate: dict) -> float:
    """Score how much *new* factual content ``candidate`` adds over a canonical cluster.

    Parameters
    ----------
    canonical_facts : dict
        Accumulated facts for the canonical cluster.  Expected keys:
        ``numbers``, ``entities``, ``quotes``, and optionally ``first_seen``
        (datetime or ISO string of when the cluster was first observed).
    candidate : dict
        An article dict with at least ``title``, ``summary``, and
        ``published_at``.

    Returns
    -------
    float
        A score between 0.0 (pure duplicate) and 1.0 (entirely new info).
    """
    if not canonical_facts or not candidate:
        logger.warning("compute_fact_delta called with empty input; returning 0.0")
        return 0.0

    candidate_facts = extract_facts(candidate)

    score = 0.0

    # ------------------------------------------------------------------
    # 1. time_gap  (max +0.35)
    # ------------------------------------------------------------------
    candidate_dt = _parse_datetime(candidate.get("published_at"))
    first_seen_dt = _parse_datetime(
        canonical_facts.get("first_seen", candidate.get("published_at"))
    )
    days_gap = max(
        (candidate_dt - first_seen_dt).total_seconds() / 86400.0,
        0.0,
    )
    time_gap = min(0.15 * math.log1p(days_gap), 0.35)
    score += time_gap

    # ------------------------------------------------------------------
    # 2. new_numbers  (max +0.30)
    # ------------------------------------------------------------------
    canonical_numbers = set(canonical_facts.get("numbers") or [])
    cand_numbers = candidate_facts["numbers"]
    if cand_numbers:
        new_count = sum(1 for n in cand_numbers if n not in canonical_numbers)
        score += min((new_count / len(cand_numbers)) * 0.30, 0.30)

    # ------------------------------------------------------------------
    # 3. new_entities  (max +0.25)
    # ------------------------------------------------------------------
    canonical_entities = set(canonical_facts.get("entities") or [])
    cand_entities = candidate_facts["entities"]
    if cand_entities:
        new_count = sum(1 for e in cand_entities if e not in canonical_entities)
        score += min((new_count / len(cand_entities)) * 0.25, 0.25)

    # ------------------------------------------------------------------
    # 4. new_quotes  (max +0.15)
    # ------------------------------------------------------------------
    canonical_quotes = set(canonical_facts.get("quotes") or [])
    cand_quotes = candidate_facts["quotes"]
    if cand_quotes:
        new_count = sum(1 for q in cand_quotes if q not in canonical_quotes)
        score += min((new_count / len(cand_quotes)) * 0.15, 0.15)

    # ------------------------------------------------------------------
    # 5. verb_progression  (max +0.10)
    # ------------------------------------------------------------------
    canonical_title_lower = " ".join(
        (canonical_facts.get("title") or "").lower().split()
    )
    candidate_title_lower = (candidate.get("title") or "").lower()
    for verb in _PROGRESSION_VERBS:
        if verb in candidate_title_lower and verb not in canonical_title_lower:
            score += 0.10
            break  # only count once

    # ------------------------------------------------------------------
    # Cap at 1.0
    # ------------------------------------------------------------------
    final_score = min(score, 1.0)

    logger.debug(
        "Fact delta=%.3f  (time=%.3f num=%.3f ent=%.3f quot=%.3f verb=%s)  "
        "candidate='%s'",
        final_score,
        time_gap,
        min((sum(1 for n in cand_numbers if n not in canonical_numbers) / len(cand_numbers)) * 0.30, 0.30) if cand_numbers else 0.0,
        min((sum(1 for e in cand_entities if e not in canonical_entities) / len(cand_entities)) * 0.25, 0.25) if cand_entities else 0.0,
        min((sum(1 for q in cand_quotes if q not in canonical_quotes) / len(cand_quotes)) * 0.15, 0.15) if cand_quotes else 0.0,
        any(v in candidate_title_lower and v not in canonical_title_lower for v in _PROGRESSION_VERBS),
        (candidate.get("title") or "")[:60],
    )

    return final_score
