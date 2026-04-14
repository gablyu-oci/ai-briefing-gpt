"""
render.py — HTML briefing generation.

Design: Strict editorial grid. Per-section tint families, uniform card heights,
3-column layout, sharp rectangular tiles, controlled typography.
"""

import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path

from briefing.config import AUDIENCE_PROFILES, AUDIENCE_ORDER

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Section metadata — each section gets ONE tint family
# ---------------------------------------------------------------------------
SECTION_META: dict[str, dict] = {
    "financial":      {"label": "Financial & Markets",         "tint": "#E8ECF1", "accent": "#8B9BB5"},
    "ai":             {"label": "Artificial Intelligence",     "tint": "#E8ECF1", "accent": "#8B9BB5"},
    "compete":        {"label": "Competitive Intel",           "tint": "#E8ECF1", "accent": "#8B9BB5"},
    "datacenter":     {"label": "Datacenter & Infrastructure", "tint": "#E8ECF1", "accent": "#8B9BB5"},
    "power":          {"label": "Power & Energy",              "tint": "#E8ECF1", "accent": "#8B9BB5"},
    "security":       {"label": "Security & Compliance",       "tint": "#E8ECF1", "accent": "#8B9BB5"},
    "deals":          {"label": "Deals & Partnerships",        "tint": "#E8ECF1", "accent": "#8B9BB5"},
    "multicloud":     {"label": "Multi-Cloud & Ecosystem",     "tint": "#E8ECF1", "accent": "#8B9BB5"},
    "oss":            {"label": "Open Source",                 "tint": "#E8ECF1", "accent": "#8B9BB5"},
    "partnerships":   {"label": "Strategic Partnerships",      "tint": "#E8ECF1", "accent": "#8B9BB5"},
    "community":      {"label": "Community Signal",            "tint": "#E8ECF1", "accent": "#8B9BB5"},
    "infrastructure": {"label": "Infrastructure",              "tint": "#E8ECF1", "accent": "#8B9BB5"},
    "other":          {"label": "Technology",                  "tint": "#E8ECF1", "accent": "#8B9BB5"},
}

TIER_LABELS = {1: "Tier 1", 2: "Tier 2", 3: "Vendor", 4: "Community"}
TIER_COLORS = {1: "#C0392B", 2: "#2980B9", 3: "#27AE60", 4: "#8E44AD"}

# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------
BASE_CSS = """
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,600;9..40,700&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --ink:         #1A1D23;
  --ink-mid:     #3D4350;
  --ink-light:   #64748B;
  --ink-muted:   #94A3B8;
  --surface:     #F4F5F7;
  --rule:        #D1D5DB;
  --rule-light:  #E2E8F0;
  --accent:      #3B5998;
  --accent-pale: #EDF1F8;
  --lead-bg:     #1E293B;
  --lead-text:   #F1F5F9;
  --lead-muted:  #94A3B8;
  --new-bg:      #DEF7EC;
  --new-text:    #166534;
  --font:        'DM Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

html { font-size: 14px; }
body {
  background: var(--surface);
  color: var(--ink);
  font-family: var(--font);
  line-height: 1.45;
  -webkit-font-smoothing: antialiased;
}
a { color: inherit; text-decoration: none; }

/* ── Masthead ─────────────────────────────────────── */
.masthead { background: var(--lead-bg); }
.masthead-inner {
  max-width: 1060px; margin: 0 auto; padding: 0 28px;
  height: 42px; display: flex; align-items: center; justify-content: space-between;
}
.masthead-title { font-size: 14px; font-weight: 700; color: #F1F5F9; letter-spacing: 0.03em; }
.masthead-title em { font-style: normal; font-weight: 400; color: #64748B; margin-right: 2px; }
.masthead-date { font-size: 10px; color: #64748B; letter-spacing: 0.04em; }
.masthead-nav { display: flex; overflow-x: auto; flex-shrink: 1; min-width: 0; }
.masthead-nav a {
  padding: 12px 8px; font-size: 9px; font-weight: 600; letter-spacing: 0.1em;
  text-transform: uppercase; color: #64748B; white-space: nowrap;
  border-bottom: 2px solid transparent; display: block;
}
.masthead-nav a:hover { color: #CBD5E1; border-bottom-color: #475569; }

/* ── Page ─────────────────────────────────────────── */
.page { max-width: 1060px; margin: 0 auto; padding: 20px 28px 36px; }

/* ── Executive Summary ────────────────────────────── */
.exec-block {
  display: grid; grid-template-columns: 3fr 2fr; gap: 0;
  margin-bottom: 24px; overflow: hidden; border: 1px solid #334155;
}
.exec-left { background: var(--lead-bg); padding: 14px 18px; }
.exec-overline {
  font-size: 9px; font-weight: 700; letter-spacing: 0.18em;
  text-transform: uppercase; color: #64748B; margin-bottom: 10px;
}
.exec-items { list-style: none; }
.exec-item {
  display: flex; gap: 10px; align-items: baseline;
  padding: 5px 0; border-bottom: 1px solid rgba(255,255,255,0.06);
  font-size: 12.5px; line-height: 1.45; color: #CBD5E1;
}
.exec-item:last-child { border-bottom: none; }
.exec-item:first-child { color: #F1F5F9; font-weight: 600; }
.exec-num {
  font-size: 10px; font-weight: 700; color: #64748B;
  flex-shrink: 0; width: 12px; text-align: right;
}
.exec-right {
  background: var(--accent-pale); padding: 14px 18px;
  border-left: 2px solid var(--accent);
  display: flex; flex-direction: column; gap: 8px;
}
.outlook-label {
  font-size: 9px; font-weight: 700; letter-spacing: 0.16em;
  text-transform: uppercase; color: var(--accent);
}
.outlook-text { font-size: 12.5px; line-height: 1.6; color: var(--ink-mid); }

/* ── Section ──────────────────────────────────────── */
.section { margin-bottom: 20px; }
.section-header {
  display: flex; align-items: center; gap: 8px;
  margin-bottom: 6px; padding-bottom: 4px; border-bottom: 1px solid var(--rule);
}
.section-label {
  font-size: 9px; font-weight: 700; letter-spacing: 0.16em;
  text-transform: uppercase; color: var(--ink-light); white-space: nowrap;
}
.section-count {
  font-size: 9px; color: var(--ink-muted); margin-left: auto;
}

/* ── Card grid — strict 3 columns, equal height ──── */
.card-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 4px;
}

/* ── Card — sharp rectangular editorial tile ──────── */
.card {
  padding: 9px 12px;
  border-left: 2px solid transparent;
  border-radius: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-height: 56px;
}
.card a { color: var(--ink); }
.card a:hover { color: var(--accent); text-decoration: underline; }

.card-title {
  font-size: 12.5px;
  font-weight: 600;
  line-height: 1.35;
  margin-bottom: 2px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-meta {
  font-size: 10px;
  color: var(--ink-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* NEW badge */
.new-badge {
  font-size: 7px; font-weight: 700; letter-spacing: 0.04em;
  text-transform: uppercase; color: var(--new-text); background: var(--new-bg);
  padding: 1px 4px; display: inline-block; vertical-align: middle; margin-left: 4px;
}

/* ── Footer ───────────────────────────────────────── */
.page-rule { height: 1px; background: var(--rule); margin: 24px 0 14px; }
.colophon { font-size: 10px; color: var(--ink-muted); text-align: center; line-height: 2; }
.colophon a { color: var(--ink-light); }
.colophon-links { margin-top: 4px; padding-top: 4px; border-top: 1px solid var(--rule-light); }
.colophon-links-label { font-size: 8px; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; color: var(--ink-muted); margin-bottom: 2px; }
.colophon-link { font-size: 11px; font-weight: 500; color: var(--accent); padding: 1px 6px; }
.colophon-link:hover { background: var(--accent-pale); }
.colophon-link.current { color: var(--ink-muted); pointer-events: none; }

/* ── Audience panel ───────────────────────────────── */
.audience-panel { display: none; }
.audience-panel.active { display: block; }

/* ── Responsive ───────────────────────────────────── */
@media (max-width: 768px) {
  .masthead-inner { padding: 0 16px; flex-wrap: wrap; height: auto; }
  .masthead-nav { width: 100%; }
  .masthead-date { display: none; }
  .page { padding: 16px 14px 28px; }
  .exec-block { grid-template-columns: 1fr; }
  .exec-right { border-left: none; border-top: 2px solid var(--accent); }
  .card-grid { grid-template-columns: 1fr 1fr; }
}
@media (max-width: 480px) {
  .card-grid { grid-template-columns: 1fr; }
}
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _relative_time(dt: datetime) -> str:
    now  = datetime.now(tz=timezone.utc)
    diff = now - dt
    h    = diff.total_seconds() / 3600
    if h < 1:   return f"{int(diff.total_seconds()/60)}m ago"
    if h < 24:  return f"{int(h)}h ago"
    return f"{int(h/24)}d ago"

def _esc(text: str) -> str:
    return (text or "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")

def _image_seed(url: str) -> int:
    return int(hashlib.md5(url.encode()).hexdigest()[:8], 16) % 1000

def _tier_color(tier: int) -> str:
    return TIER_COLORS.get(tier, "#7F8C8D")

def _section_meta(section: str) -> dict:
    return SECTION_META.get(section, SECTION_META["other"])

def _conf_class(conf: str | None) -> str:
    return {"high": "conf-high", "medium": "conf-medium"}.get(conf or "", "conf-low")

def _group_by_section(articles: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {}
    for a in articles:
        sec = a.get("classified_section") or (a["sections"][0] if a.get("sections") else "other")
        if not sec or sec == "None":
            sec = "other"
        groups.setdefault(sec, []).append(a)
    return groups

def _is_fresh(pub: datetime | None, threshold_hours: int = 6) -> bool:
    if pub is None:
        return False
    return (datetime.now(tz=timezone.utc) - pub).total_seconds() / 3600 < threshold_hours

# ---------------------------------------------------------------------------
# Card rendering — all cards are uniform tiles
# ---------------------------------------------------------------------------

def _render_card(article: dict, audience_id: str, tint: str, accent: str) -> str:
    per   = article.get("per_audience_summaries", {}).get(audience_id, {})
    title = _esc(per.get("headline", article["title"]))
    pub   = article.get("published_at")
    rel   = _relative_time(pub) if pub else ""
    abs_t = pub.strftime("%b %d") if pub else ""
    src   = _esc(article.get("source", ""))
    url   = _esc(article["url"])

    new_badge = ""
    if _is_fresh(pub):
        new_badge = '<span class="new-badge">NEW</span>'

    meta = " · ".join(p for p in [src, abs_t, rel] if p)

    return f"""<div class="card" style="background:{tint};border-left-color:{accent}">
      <div class="card-title"><a href="{url}" target="_blank" rel="noopener">{title}</a>{new_badge}</div>
      <div class="card-meta">{meta}</div>
    </div>"""

# ---------------------------------------------------------------------------
# Section
# ---------------------------------------------------------------------------

def _render_section(section: str, articles: list[dict], audience_id: str) -> str:
    meta   = _section_meta(section)
    sec_id = f"{audience_id}-{section}"
    n      = len(articles)
    tint   = meta["tint"]
    accent = meta["accent"]

    cards = "".join(_render_card(a, audience_id, tint, accent) for a in articles)

    return f"""<section class="section" id="{sec_id}">
      <div class="section-header">
        <span class="section-label">{_esc(meta['label'])}</span>
        <span class="section-count">{n}</span>
      </div>
      <div class="card-grid">{cards}</div>
    </section>"""

# ---------------------------------------------------------------------------
# Section nav
# ---------------------------------------------------------------------------

def _render_section_nav(sections: list[tuple[str,int]], audience_id: str) -> str:
    return "".join(
        f'<a href="#{audience_id}-{s}">{_esc(_section_meta(s)["label"])}</a>'
        for s, c in sections
    )


def _ordered_sections_for_audience(audience_id: str, articles: list[dict]) -> list[tuple[str, list[dict]]]:
    """Return section groups in persona order, then append any remaining sections."""
    profile = AUDIENCE_PROFILES[audience_id]
    groups = _group_by_section(articles)

    ordered: list[tuple[str, list[dict]]] = []
    seen: set[str] = set()
    for sec in profile["section_weights"]:
        if sec in groups:
            ordered.append((sec, groups[sec]))
            seen.add(sec)
    for sec, items in groups.items():
        if sec not in seen:
            ordered.append((sec, items))
    return ordered


def _section_nav_for_audience(audience_id: str, articles: list[dict]) -> str:
    ordered = _ordered_sections_for_audience(audience_id, articles)
    return _render_section_nav([(section, len(items)) for section, items in ordered], audience_id)

# ---------------------------------------------------------------------------
# Executive summary
# ---------------------------------------------------------------------------

def _render_exec_summary(exec_data: dict, audience_id: str, articles: list[dict]) -> str:
    bullets = exec_data.get("bullets", [])
    outlook = _esc(exec_data.get("market_outlook", ""))

    import re as _re
    items = ""
    for i, b in enumerate(bullets):
        # Strip "Bullet N:" or "N." prefixes the LLM sometimes adds
        b = _re.sub(r'^(?:Bullet\s*\d+\s*[:\-–—]\s*|^\d+\.\s*)', '', b)
        items += f'<li class="exec-item"><span class="exec-num">{i+1}</span> {_esc(b)}</li>'

    outlook_html = ""
    if outlook:
        outlook_html = f"""<div class="outlook-label">Market Outlook</div>
        <div class="outlook-text">{outlook}</div>"""

    return f"""<div class="exec-block" id="{audience_id}-exec">
      <div class="exec-left">
        <div class="exec-overline">Executive Summary</div>
        <ul class="exec-items">{items}</ul>
      </div>
      <div class="exec-right">
        {outlook_html}
      </div>
    </div>"""

# ---------------------------------------------------------------------------
# Audience panel
# ---------------------------------------------------------------------------

def _render_audience_panel(
    audience_id: str,
    articles: list[dict],
    exec_summary: dict,
    generation_time: datetime,
    available_audience_ids: list[str] | None = None,
    link_prefix: str = "?audience=",
) -> str:
    profile = AUDIENCE_PROFILES[audience_id]
    ordered = _ordered_sections_for_audience(audience_id, articles)
    sec_with_counts = [(s, len(a)) for s, a in ordered]
    sec_nav   = _render_section_nav(sec_with_counts, audience_id)
    exec_html = _render_exec_summary(exec_summary, audience_id, articles)
    secs_html = "\n".join(_render_section(s, a, audience_id) for s, a in ordered)
    gen_str   = generation_time.strftime("%Y-%m-%d %H:%M UTC")
    footer_links_html = ""
    link_ids = available_audience_ids or [aud_id for aud_id in AUDIENCE_ORDER if aud_id in AUDIENCE_PROFILES]
    if len(link_ids) > 1:
        briefing_links = ""
        for aud_id in link_ids:
            p = AUDIENCE_PROFILES[aud_id]
            current_cls = " current" if aud_id == audience_id else ""
            briefing_links += (
                f'<a class="colophon-link{current_cls}" href="{link_prefix}{aud_id}">'
                f'{_esc(p["name"])}</a>\n'
            )

        footer_links_html = f"""<div class="colophon-links">
            <div class="colophon-links-label">View other briefings</div>
            {briefing_links}
          </div>"""

    return f"""<div class="audience-panel" data-audience="{audience_id}" data-sec-nav="{_esc(sec_nav)}">
      <main class="page">
        {exec_html}
        {secs_html}
        <div class="page-rule"></div>
        <footer class="colophon">
          <div>{_esc(profile['name'])} · {gen_str} · {len(articles)} stories ·
          Powered by Oracle Code Assist</div>
          {footer_links_html}
        </footer>
      </main>
    </div>"""

# ---------------------------------------------------------------------------
# Masthead
# ---------------------------------------------------------------------------

def _render_masthead(
    generation_time: datetime,
    date_range: str = "",
    section_nav: str = "",
) -> str:
    date_str = date_range or generation_time.strftime("%a %b %d, %Y")
    return f"""<header class="masthead">
      <div class="masthead-inner">
        <div class="masthead-title"><em>AI</em> Weekly Briefing</div>
        <div class="masthead-date">{date_str}</div>
        <nav class="masthead-nav" id="header-nav">{section_nav}</nav>
      </div>
    </header>"""

def _render_audience_tabs(audience_ids: list[str] | None = None) -> str:
    audience_ids = audience_ids or list(AUDIENCE_ORDER)
    tabs = ""
    for aud_id in audience_ids:
        p = AUDIENCE_PROFILES[aud_id]
        tabs += f"""<button class="audience-tab" data-switch="{aud_id}" onclick="switchAudience('{aud_id}')" style="display:none">
          {_esc(p['name'])}
        </button>"""
    return f'<div style="display:none">{tabs}</div>'

# ---------------------------------------------------------------------------
# JS
# ---------------------------------------------------------------------------
SWITCHER_JS = """
  function switchAudience(id) {
    var panels = Array.from(document.querySelectorAll('.audience-panel'));
    panels.forEach(function(el) { el.classList.remove('active'); });
    var p = document.querySelector('.audience-panel[data-audience="'+id+'"]');
    if (!p) {
      p = panels[0] || null;
    }
    if (!p) return;

    p.classList.add('active');
    var activeId = p.dataset.audience || '';
    var nav = document.getElementById('header-nav');
    if (nav) nav.innerHTML = p.dataset.secNav || '';
    document.querySelectorAll('.audience-tab').forEach(b => {
      b.classList.toggle('active', b.dataset.switch===activeId);
    });
    try { localStorage.setItem('briefing-aud', activeId); } catch(e) {}
  }
"""
INIT_JS = """
  (function(){
    // Priority: URL param > localStorage > first panel
    var params = new URLSearchParams(window.location.search);
    var fromUrl = params.get('audience');
    var saved = null;
    try { saved = localStorage.getItem('briefing-aud'); } catch(e) {}
    var first = document.querySelector('.audience-panel');
    switchAudience(fromUrl || saved || (first ? first.dataset.audience : ''));
    var tabs = document.querySelectorAll('.audience-tab');
    if (tabs.length > 1) tabs.forEach(function(t){ t.style.display = ''; });
  })();
"""

# ---------------------------------------------------------------------------
# Full page renderers
# ---------------------------------------------------------------------------

def render_combined_html(all_audience_data, generation_time=None):
    if generation_time is None:
        generation_time = datetime.now(tz=timezone.utc)

    available_audience_ids = [aud_id for aud_id in AUDIENCE_ORDER if aud_id in all_audience_data]
    panels = ""
    default_nav = ""
    for idx, aud_id in enumerate(available_audience_ids):
        data = all_audience_data.get(aud_id)
        if not data:
            continue
        panel = _render_audience_panel(
            aud_id,
            data["articles"],
            data.get("exec_summary", {}),
            generation_time,
            available_audience_ids=available_audience_ids,
            link_prefix="?audience=",
        )
        if idx == 0:
            panel = panel.replace('class="audience-panel"', 'class="audience-panel active"', 1)
            default_nav = _section_nav_for_audience(aud_id, data["articles"])
        panels += panel
    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>AI Weekly Briefing</title><style>{BASE_CSS}</style></head>
<body>{_render_masthead(generation_time, section_nav=default_nav)}{_render_audience_tabs(available_audience_ids)}{panels}
<script>{SWITCHER_JS}{INIT_JS}</script></body></html>"""

def render_single_audience_html(
    audience_id,
    articles,
    exec_summary,
    generation_time=None,
    available_audience_ids: list[str] | None = None,
):
    if generation_time is None:
        generation_time = datetime.now(tz=timezone.utc)

    panel = _render_audience_panel(
        audience_id,
        articles,
        exec_summary,
        generation_time,
        available_audience_ids=available_audience_ids,
        link_prefix="index.html?audience=",
    )
    panel = panel.replace('class="audience-panel"', 'class="audience-panel active"', 1)
    section_nav = _section_nav_for_audience(audience_id, articles)
    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>AI Weekly Briefing — {_esc(AUDIENCE_PROFILES[audience_id]['name'])}</title><style>{BASE_CSS}</style></head>
<body>{_render_masthead(generation_time, section_nav=section_nav)}
{panel}</body></html>"""

# ---------------------------------------------------------------------------
# Save to disk
# ---------------------------------------------------------------------------

def save_briefings(all_audience_data, output_dir, generation_time=None):
    if generation_time is None:
        generation_time = datetime.now(tz=timezone.utc)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {}
    available_audience_ids = [aud_id for aud_id in AUDIENCE_ORDER if aud_id in all_audience_data]
    for aud_id in AUDIENCE_ORDER:
        data = all_audience_data.get(aud_id)
        if not data: continue
        html = render_single_audience_html(
            aud_id,
            data["articles"],
            data.get("exec_summary", {}),
            generation_time,
            available_audience_ids=available_audience_ids,
        )
        path = output_dir / f"{aud_id}.html"
        path.write_text(html, encoding="utf-8")
        logger.info("Wrote %s (%d bytes)", path, len(html))
        paths[aud_id] = path
    combined = render_combined_html(all_audience_data, generation_time)
    index_path = output_dir / "index.html"
    index_path.write_text(combined, encoding="utf-8")
    logger.info("Wrote %s (%d bytes)", index_path, len(combined))
    paths["index"] = index_path
    return paths
