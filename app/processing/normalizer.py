"""
normalizer.py — Article normalization and entity extraction.

Migrated from briefing/process.py with enhanced NER capabilities.
"""

import logging
import re

from config.sources import SECTION_KEYWORDS

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Entity extraction (regex-based NER)
# ---------------------------------------------------------------------------

# Known entities for regex NER
KNOWN_ENTITIES = {
    # Companies
    "oracle", "oci", "aws", "amazon", "microsoft", "azure", "google", "gcp",
    "nvidia", "amd", "intel", "ibm", "meta", "apple", "tesla", "salesforce",
    "snowflake", "databricks", "openai", "anthropic", "google cloud",
    "alibaba", "sap", "vmware", "broadcom", "arm", "qualcomm",
    # Products
    "kubernetes", "docker", "terraform", "pytorch", "tensorflow",
    "bedrock", "sagemaker", "vertex ai", "gpt", "claude", "gemini", "llama",
    "h100", "h200", "b200", "a100", "graviton",
    # People (common tech leaders)
    "larry ellison", "satya nadella", "andy jassy", "sundar pichai",
    "jensen huang", "mark zuckerberg", "elon musk", "sam altman", "dario amodei",
}

# Patterns for extracting capitalized entity names
ENTITY_PATTERN = re.compile(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b')


def extract_entities(title: str, summary: str) -> list[str]:
    """
    Extract named entities from title and summary using regex NER.
    Combines known entity matching with capitalized name detection.
    """
    combined = f"{title} {summary}"
    combined_lower = combined.lower()
    entities = set()

    # Match known entities
    for entity in KNOWN_ENTITIES:
        if entity in combined_lower:
            entities.add(entity.title() if len(entity) > 3 else entity.upper())

    # Extract capitalized multi-word names (potential entities)
    for match in ENTITY_PATTERN.finditer(combined):
        name = match.group(1)
        # Skip common non-entity words
        if name.lower() not in {
            "the", "this", "that", "with", "from", "into", "over",
            "after", "before", "about", "between", "through", "during",
            "their", "there", "where", "which", "these", "those",
            "monday", "tuesday", "wednesday", "thursday", "friday",
            "saturday", "sunday", "january", "february", "march",
            "april", "may", "june", "july", "august", "september",
            "october", "november", "december",
        } and len(name) > 2:
            entities.add(name)

    return sorted(list(entities))[:10]  # Cap at 10


# ---------------------------------------------------------------------------
# Section inference
# ---------------------------------------------------------------------------

def infer_sections(article: dict) -> list[str]:
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


# ---------------------------------------------------------------------------
# Main normalize function
# ---------------------------------------------------------------------------

def normalize_articles(articles: list[dict]) -> list[dict]:
    """
    Normalize articles:
    1. Enrich section tags from keyword matching
    2. Extract entities from title/summary
    3. Sort by max score descending
    4. Return top 40 for the canonical bundle
    """
    for article in articles:
        # Enrich sections
        article["sections"] = infer_sections(article)

        # Extract entities if not already done
        if not article.get("entities"):
            article["entities"] = extract_entities(
                article["title"],
                article.get("summary", ""),
            )

    # Sort by max score
    articles.sort(key=lambda a: max(a.get("scores", {}).values(), default=0), reverse=True)

    top = articles[:40]
    logger.info("normalize_articles: returning top %d of %d articles", len(top), len(articles))
    return top
