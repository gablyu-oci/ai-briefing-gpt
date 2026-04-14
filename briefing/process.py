"""
process.py — Article normalization, deduplication, and section tagging.

Takes raw ingested articles and returns a clean, deduplicated, tagged list.
"""

import logging
import re
from briefing.config import OCI_KEYWORDS

logger = logging.getLogger(__name__)

# Section keyword mapping for supplemental tagging
SECTION_KEYWORDS: dict[str, list[str]] = {
    "ai":           ["artificial intelligence", "machine learning", "llm", "neural", "gpt",
                     "claude", "gemini", "openai", "anthropic", "generative", "deep learning",
                     "foundation model", "large language", "inference", "gpu", "nvidia"],
    "financial":    ["earnings", "revenue", "profit", "ipo", "valuation", "stock", "quarterly",
                     "fiscal", "billion", "million", "forecast", "guidance"],
    "compete":      ["aws", "amazon web services", "azure", "google cloud", "gcp", "microsoft",
                     "alibaba cloud", "ibm cloud", "competitor", "market share", "beats"],
    "datacenter":   ["datacenter", "data center", "colocation", "colo", "facility", "campus",
                     "rack", "cooling", "pue"],
    "power":        ["megawatt", "gigawatt", "mw", "gw", "power grid", "energy", "electricity",
                     "nuclear", "solar", "renewable", "utility"],
    "deals":        ["acquisition", "merger", "deal", "contract", "agreement", "partnership",
                     "signed", "awarded", "procurement"],
    "security":     ["security", "breach", "vulnerability", "cve", "ransomware", "zero trust",
                     "soc2", "fedramp", "compliance", "audit"],
    "multicloud":   ["multicloud", "multi-cloud", "hybrid cloud", "cloud-agnostic", "portability"],
    "oss":          ["open source", "open-source", "github", "linux", "apache", "kubernetes",
                     "helm", "terraform", "pytorch", "hugging face"],
    "partnerships": ["partnership", "collaborate", "integrate", "ecosystem", "isv", "gsi"],
    "community":    ["hacker news", "reddit", "developer", "community", "forum", "discussion"],
    "infrastructure": ["infrastructure", "networking", "storage", "compute", "vpc", "cdn"],
}


def _tokenize(text: str) -> set[str]:
    """Return a set of lowercase word tokens (no punctuation)."""
    return set(re.findall(r"[a-z]+", text.lower()))


def _title_overlap(a: dict, b: dict) -> float:
    """
    Compute word overlap ratio between two article titles using Jaccard similarity.
    Returns 0.0-1.0.
    """
    ta = _tokenize(a["title"])
    tb = _tokenize(b["title"])
    if not ta or not tb:
        return 0.0
    intersection = len(ta & tb)
    union = len(ta | tb)
    return intersection / union if union else 0.0


def _infer_sections(article: dict) -> list[str]:
    """
    Supplement existing section tags by scanning title+summary for keywords.
    Returns a deduplicated merged list of section tags.
    """
    text = (article["title"] + " " + article.get("summary", "")).lower()
    sections = set(article.get("sections", []))

    for section, keywords in SECTION_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                sections.add(section)
                break

    return sorted(sections)


def deduplicate_articles(articles: list[dict]) -> list[dict]:
    """
    Remove duplicates:
    1. Exact URL dedup (handled upstream in ingest, but safety net here)
    2. Near-duplicate titles (>80% Jaccard word overlap) → keep higher max score
    """
    seen_urls: set[str] = set()
    unique: list[dict] = []

    for article in articles:
        if article["url"] in seen_urls:
            continue
        seen_urls.add(article["url"])
        unique.append(article)

    # Near-duplicate pass
    keep = []
    dropped: set[str] = set()

    for i, a in enumerate(unique):
        if a["url"] in dropped:
            continue
        for j, b in enumerate(unique):
            if i >= j or b["url"] in dropped:
                continue
            overlap = _title_overlap(a, b)
            if overlap > 0.80:
                score_a = max(a.get("scores", {}).values(), default=0)
                score_b = max(b.get("scores", {}).values(), default=0)
                loser = b if score_a >= score_b else a
                dropped.add(loser["url"])
                logger.debug("Dedup: dropped '%s' (overlap=%.2f)", loser["title"][:60], overlap)
        if a["url"] not in dropped:
            keep.append(a)

    logger.info("Dedup: %d → %d articles (%d dropped)", len(unique), len(keep), len(unique) - len(keep))
    return keep


def normalize_articles(raw_articles: list[dict]) -> list[dict]:
    """
    Main entry point:
    1. Enrich section tags from keyword matching
    2. Deduplicate by URL + title overlap
    3. Sort by max-audience score descending
    4. Return top 40 for the canonical bundle

    Note: Call AFTER score_all_articles so scores are available for dedup.
    """
    # Enrich sections
    for article in raw_articles:
        article["sections"] = _infer_sections(article)

    # Dedup
    cleaned = deduplicate_articles(raw_articles)

    # Sort by max score
    cleaned.sort(key=lambda a: max(a.get("scores", {}).values(), default=0), reverse=True)

    top = cleaned[:40]
    logger.info("normalize_articles: returning top %d of %d articles", len(top), len(cleaned))
    return top
