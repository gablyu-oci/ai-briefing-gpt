"""
test_render.py — Regression tests for briefing HTML rendering.
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from briefing.render import render_combined_html, render_single_audience_html


def _make_article(section: str = "ai") -> dict:
    return {
        "title": "Cloudflare launches secure agent platform",
        "url": "https://example.com/cloudflare-agent-platform",
        "source": "OpenAI Blog",
        "tier": 1,
        "sections": [section],
        "summary": "A secure agent platform pairs frontier models with enterprise controls.",
        "published_at": datetime.now(timezone.utc) - timedelta(hours=2),
        "topics": [],
        "entities": [],
        "scores": {"greg": 91.0},
        "per_audience_summaries": {
            "greg": {"headline": "Cloudflare pairs frontier models with enterprise controls"}
        },
    }


def _make_exec_summary() -> dict:
    return {
        "bullets": ["Enterprise AI adoption is shifting toward governed agent platforms."],
        "market_outlook": "Security controls are becoming part of the product, not an add-on.",
    }


def test_render_combined_html_defaults_to_first_available_audience():
    generation_time = datetime(2026, 4, 13, 22, 0, tzinfo=timezone.utc)
    html = render_combined_html(
        {
            "greg": {
                "articles": [_make_article("ai"), _make_article("financial")],
                "exec_summary": _make_exec_summary(),
            }
        },
        generation_time=generation_time,
    )

    assert 'class="audience-panel active" data-audience="greg"' in html
    assert 'data-switch="greg"' in html
    assert 'data-switch="karan"' not in html
    assert "p = panels[0] || null;" in html
    assert 'href="#greg-ai"' in html
    assert "Financial &amp; Markets" in html


def test_render_single_audience_html_marks_panel_active_and_uses_index_links():
    generation_time = datetime(2026, 4, 13, 22, 0, tzinfo=timezone.utc)
    html = render_single_audience_html(
        "greg",
        [_make_article("ai")],
        _make_exec_summary(),
        generation_time=generation_time,
        available_audience_ids=["greg", "karan"],
    )

    assert html.count('class="audience-panel active"') == 1
    assert 'class="audience-panel" data-audience="greg"' not in html
    assert '<nav class="masthead-nav" id="header-nav"><a href="#greg-ai">Artificial Intelligence</a></nav>' in html
    assert 'href="index.html?audience=karan"' in html
