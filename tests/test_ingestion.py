"""
test_ingestion.py — Tests for the ingestion module.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.ingestion.fetcher import _strip_html, _make_article_id, _parse_date


def test_strip_html():
    """HTML stripping should remove tags and normalize whitespace."""
    assert _strip_html("<p>Hello <b>world</b></p>") == "Hello world"
    assert _strip_html("") == ""
    assert _strip_html("plain text") == "plain text"
    assert _strip_html("<div>  spaces   here  </div>") == "spaces here"
    print("PASS: test_strip_html")


def test_make_article_id():
    """Article IDs should be deterministic and 16 chars."""
    id1 = _make_article_id("https://example.com/article1")
    id2 = _make_article_id("https://example.com/article1")
    id3 = _make_article_id("https://example.com/article2")

    assert id1 == id2, "Same URL should produce same ID"
    assert id1 != id3, "Different URLs should produce different IDs"
    assert len(id1) == 16, f"Expected 16 chars, got {len(id1)}"
    print("PASS: test_make_article_id")


def test_parse_date_none():
    """Missing date fields should return None."""
    class FakeEntry(dict):
        pass
    entry = FakeEntry()
    result = _parse_date(entry)
    assert result is None
    print("PASS: test_parse_date_none")


if __name__ == "__main__":
    test_strip_html()
    test_make_article_id()
    test_parse_date_none()
    print("\n✓ All ingestion tests passed!")
