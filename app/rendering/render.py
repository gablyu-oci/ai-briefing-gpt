"""
render.py — HTML briefing generation with multi-column newspaper layout.

Upgraded from briefing/render.py:
- 3-column grid for story rows within each section
- Full-width section headers with bold teal rule
- Compact 2-panel executive summary (charcoal + amber)
- Hero card: horizontal layout with image left (180px), content right, full width
- Prominent audience tabs with accent color fill on active
- Typography: 16px serif headlines, 11px body
- Max-width: 1200px
"""

import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path

from config.audiences import AUDIENCE_PROFILES, AUDIENCE_ORDER

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Section metadata
# ---------------------------------------------------------------------------
SECTION_META: dict[str, dict] = {
    "ai":             {"label": "Artificial Intelligence"},
    "compete":        {"label": "Competitive Intel"},
    "financial":      {"label": "Financial & Markets"},
    "datacenter":     {"label": "Datacenter & Infrastructure"},
    "power":          {"label": "Power & Energy"},
    "deals":          {"label": "Deals & Partnerships"},
    "security":       {"label": "Security & Compliance"},
    "multicloud":     {"label": "Multi-Cloud & Ecosystem"},
    "oss":            {"label": "Open Source"},
    "partnerships":   {"label": "Strategic Partnerships"},
    "community":      {"label": "Community Signal"},
    "infrastructure": {"label": "Infrastructure"},
    "other":          {"label": "Technology"},
}

TIER_LABELS = {1: "Tier 1", 2: "Tier 2", 3: "Vendor", 4: "Community"}
TIER_COLORS = {1: "#C0392B", 2: "#2980B9", 3: "#27AE60", 4: "#8E44AD"}

# Maps a classified section to candidate audience-weight keys in priority order.
# When the LLM-assigned section doesn't match any key in an audience's
# section_weights, we walk the candidate list and pick the first match.
SECTION_REMAP: dict[str, list[str]] = {
    # source_section -> [candidate_remaps in priority order]
    "security":       ["security", "compete"],
    "financial":      ["financial", "compete", "deals"],
    "datacenter":     ["datacenter", "power", "infrastructure"],
    "power":          ["power", "datacenter"],
    "deals":          ["deals", "partnerships", "multicloud"],
    "partnerships":   ["partnerships", "deals"],
    "multicloud":     ["multicloud", "compete", "deals"],
    "compete":        ["compete", "ai"],
    "ai":             ["ai", "compete"],
    "oss":            ["oss", "ai", "community"],
    "community":      ["community", "oss"],
    "infrastructure": ["infrastructure", "datacenter"],
}

# ---------------------------------------------------------------------------
# CSS — Multi-column newspaper layout
# ---------------------------------------------------------------------------
BASE_CSS = """
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --teal:        #5B9DB5;
    --teal-dark:   #3D7A96;
    --teal-light:  #D6EAF2;
    --teal-pale:   #EBF5FA;
    --charcoal:    #2C3E50;
    --charcoal2:   #34495E;
    --gray-dark:   #7F8C8D;
    --gray-mid:    #BDC3C7;
    --gray-light:  #ECF0F1;
    --gray-bg:     #F4F6F8;
    --white:       #FFFFFF;
    --text:        #2C3E50;
    --text-mid:    #555E68;
    --text-muted:  #95A5A6;
    --border:      #D5DDE3;
    --shadow:      0 2px 8px rgba(44,62,80,0.10);
    --shadow-sm:   0 1px 3px rgba(44,62,80,0.06);
    --oci-accent:      #D4880F;
    --oci-bg:          #FFF8EE;
    --oci-text:        #7A5200;
    --oci-label:       #B8730C;
    --new-badge-bg:    #E8F5E9;
    --new-badge-text:  #2E7D32;
    --new-border:      var(--teal);
    --radius:      4px;
    --serif:       Georgia, 'Times New Roman', serif;
  }

  html { font-size: 13px; scroll-behavior: smooth; }

  body {
    background: var(--gray-bg);
    color: var(--text);
    font-family: 'Helvetica Neue', Arial, sans-serif;
    line-height: 1.5;
  }

  a { color: var(--teal-dark); text-decoration: none; }
  a:hover { text-decoration: underline; }

  a:focus-visible, button:focus-visible {
    outline: 2px solid var(--teal);
    outline-offset: 2px;
  }

  @media (prefers-reduced-motion: reduce) {
    *, *::before, *::after { transition-duration: 0.01ms !important; }
    html { scroll-behavior: auto; }
  }

  /* -- Unified Header Bar (40px) ---------------------- */
  .unified-header {
    background: var(--charcoal);
    border-bottom: 3px solid var(--teal);
  }

  .unified-header-inner {
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 24px;
    height: 40px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
  }

  .header-title {
    font-family: var(--serif);
    font-size: 18px;
    font-weight: 700;
    color: var(--white);
    letter-spacing: -0.5px;
    line-height: 1;
    text-transform: uppercase;
    white-space: nowrap;
    flex-shrink: 0;
  }

  .header-title span {
    color: var(--teal);
    font-style: italic;
    font-size: 14px;
    vertical-align: middle;
    margin-right: 3px;
  }

  .header-date {
    font-size: 9px;
    font-weight: 400;
    letter-spacing: 0.06em;
    color: rgba(255,255,255,0.55);
    white-space: nowrap;
    flex-shrink: 0;
  }

  .header-nav {
    display: flex;
    align-items: center;
    gap: 0;
    overflow-x: auto;
    flex-shrink: 1;
    min-width: 0;
  }

  .header-nav-link {
    padding: 11px 9px;
    font-size: 9px;
    font-weight: 600;
    letter-spacing: 0.07em;
    text-transform: uppercase;
    color: rgba(255,255,255,0.60);
    white-space: nowrap;
    border-bottom: 2px solid transparent;
    transition: all 0.1s;
    display: block;
    text-decoration: none;
    line-height: 1;
  }

  .header-nav-link:hover {
    color: white;
    border-bottom-color: var(--teal);
    text-decoration: none;
  }

  /* -- Audience Tabs (prominent) ---------------------- */
  .audience-tabs {
    display: flex;
    gap: 0;
    background: var(--charcoal2);
    border-bottom: 1px solid rgba(255,255,255,0.1);
  }

  .audience-tabs-inner {
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 24px;
    display: flex;
    gap: 0;
    width: 100%;
  }

  .audience-tab {
    padding: 8px 18px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: rgba(255,255,255,0.5);
    background: transparent;
    border: none;
    border-bottom: 3px solid transparent;
    cursor: pointer;
    transition: all 0.15s;
    white-space: nowrap;
  }

  .audience-tab:hover {
    color: rgba(255,255,255,0.85);
    background: rgba(255,255,255,0.05);
  }

  .audience-tab.active {
    color: white;
    border-bottom-color: var(--tab-accent, var(--teal));
    background: rgba(255,255,255,0.08);
  }

  /* -- NEW badge ------------------------------------- */
  .new-badge {
    font-size: 7.5px;
    font-weight: 800;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--new-badge-text);
    background: var(--new-badge-bg);
    padding: 1px 4px;
    border-radius: 3px;
    flex-shrink: 0;
    display: inline-block;
    line-height: 1.4;
  }

  /* -- Audience panel -------------------------------- */
  .audience-panel { display: none; }
  .audience-panel.active { display: block; }

  /* -- Page wrapper ---------------------------------- */
  .page-wrap {
    max-width: 1200px;
    margin: 0 auto;
    padding: 14px 24px 32px;
  }

  /* -- Executive summary (compact 2-panel) ----------- */
  .cover-block {
    display: grid;
    grid-template-columns: 3fr 2fr;
    gap: 0;
    background: var(--white);
    border: 1px solid var(--border);
    box-shadow: var(--shadow-sm);
    margin-bottom: 16px;
    border-radius: var(--radius);
    overflow: hidden;
  }

  .cover-left {
    background: var(--charcoal);
    color: white;
    padding: 12px 16px;
  }

  .cover-overline {
    font-size: 8px;
    font-weight: 700;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--teal);
    margin-bottom: 5px;
  }

  .cover-bullets {
    list-style: none;
    padding: 0;
    margin: 0;
  }

  .cover-bullets li {
    display: flex;
    gap: 7px;
    align-items: flex-start;
    padding: 3px 0;
    border-bottom: 1px solid rgba(255,255,255,0.08);
    font-size: 11px;
    color: rgba(255,255,255,0.88);
    line-height: 1.4;
  }

  .cover-bullets li:last-child { border-bottom: none; }

  .bullet-num {
    width: 15px;
    height: 15px;
    background: var(--teal);
    color: white;
    font-size: 8px;
    font-weight: 700;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    margin-top: 1px;
  }

  .cover-right {
    background: var(--oci-bg);
    border-left: 4px solid var(--oci-accent);
    padding: 12px 16px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: 6px;
  }

  .oci-badge-strip {
    display: flex;
    align-items: center;
    gap: 5px;
  }

  .oci-badge-icon {
    color: var(--oci-accent);
    font-size: 10px;
  }

  .oci-callout-label {
    font-size: 8px;
    font-weight: 800;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--oci-label);
  }

  .oci-callout-text {
    font-size: 11px;
    color: var(--oci-text);
    line-height: 1.5;
  }

  /* -- Section header (full-width bold teal rule) ---- */
  .section-block { margin-bottom: 16px; }

  .section-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 10px;
    border-bottom: 3px solid var(--teal);
    padding-bottom: 6px;
  }

  .section-label-bar {
    font-family: var(--serif);
    font-size: 14px;
    font-weight: 800;
    letter-spacing: 0.02em;
    text-transform: uppercase;
    color: var(--charcoal);
    white-space: nowrap;
  }

  .section-count {
    font-size: 9px;
    color: var(--text-muted);
    font-weight: 600;
    white-space: nowrap;
    margin-left: auto;
  }

  /* -- Hero card (full width, image left 180px) ------ */
  .hero-card {
    display: grid;
    grid-template-columns: 180px 1fr;
    background: var(--white);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    overflow: hidden;
    box-shadow: var(--shadow-sm);
    margin-bottom: 10px;
    transition: box-shadow 0.12s;
  }

  .hero-card:hover { box-shadow: var(--shadow); }

  .hero-img {
    height: 100%;
    min-height: 120px;
    overflow: hidden;
    position: relative;
    background: var(--gray-light);
  }

  .hero-img img { width: 100%; height: 100%; object-fit: cover; display: block; }

  .hero-img-badge {
    position: absolute;
    top: 5px; left: 5px;
    font-size: 7.5px;
    font-weight: 800;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    padding: 2px 6px;
    border-radius: 2px;
    color: white;
  }

  .hero-body {
    padding: 10px 14px;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .hero-meta {
    display: flex;
    align-items: center;
    gap: 4px;
    flex-wrap: wrap;
  }

  .hero-headline {
    font-family: var(--serif);
    font-size: 16px;
    font-weight: 700;
    color: var(--charcoal);
    line-height: 1.28;
  }

  .hero-headline a { color: var(--charcoal); }
  .hero-headline a:hover { color: var(--teal-dark); text-decoration: underline; }

  .hero-summary {
    font-size: 11px;
    color: var(--text-mid);
    line-height: 1.5;
    flex: 1;
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  .hero-oci {
    font-size: 10px;
    color: var(--oci-text);
    background: var(--oci-bg);
    border-left: 3px solid var(--oci-accent);
    padding: 4px 8px;
    border-radius: 2px;
    line-height: 1.4;
  }

  .hero-footer {
    font-size: 9px;
    color: var(--text-muted);
    border-top: 1px solid var(--gray-light);
    padding-top: 4px;
    margin-top: 2px;
  }

  /* -- 3-column story grid --------------------------- */
  .story-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
  }

  .story-card {
    background: var(--white);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 10px 12px;
    transition: background 0.1s, box-shadow 0.1s;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .story-card:hover {
    background: var(--teal-pale);
    box-shadow: var(--shadow-sm);
  }

  .story-card.is-fresh {
    border-left: 3px solid var(--new-border);
    padding-left: 9px;
  }

  .card-meta {
    display: flex;
    align-items: center;
    gap: 4px;
    flex-wrap: wrap;
  }

  .src-badge {
    font-size: 8px;
    font-weight: 800;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    padding: 1px 5px;
    border-radius: 2px;
    color: white;
    white-space: nowrap;
  }

  .card-timestamp {
    font-size: 8px;
    color: var(--text-muted);
    margin-left: auto;
  }

  .card-headline {
    font-family: var(--serif);
    font-size: 16px;
    font-weight: 700;
    color: var(--charcoal);
    line-height: 1.25;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  .card-headline a { color: var(--charcoal); }
  .card-headline a:hover { color: var(--teal-dark); text-decoration: underline; }

  .card-summary {
    font-size: 11px;
    color: var(--text-mid);
    line-height: 1.4;
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  .topic-pill {
    font-size: 8px;
    font-weight: 600;
    color: var(--teal-dark);
    background: var(--teal-light);
    padding: 1px 5px;
    border-radius: 8px;
  }

  .conf-pill {
    font-size: 8px;
    font-weight: 600;
    padding: 1px 5px;
    border-radius: 8px;
  }

  .conf-high   { background: #D5EFE0; color: #1A7A3C; }
  .conf-medium { background: #FEF3CD; color: #856404; }
  .conf-low    { background: #E9ECEF; color: #6C757D; }

  /* -- Divider & footer ------------------------------ */
  .divider { height: 1px; background: var(--border); margin: 16px 0; }

  .page-footer {
    text-align: center;
    font-size: 9px;
    color: var(--text-muted);
    letter-spacing: 0.04em;
    line-height: 2;
  }

  .page-footer a { color: var(--teal-dark); }

  .footer-briefings {
    margin-top: 8px;
    padding-top: 8px;
    border-top: 1px solid var(--border);
  }

  .footer-briefings-label {
    font-size: 8.5px;
    font-weight: 700;
    letter-spacing: 0.10em;
    text-transform: uppercase;
    color: var(--text-muted);
    margin-bottom: 4px;
  }

  .footer-briefing-link {
    font-size: 10px;
    font-weight: 600;
    color: var(--teal-dark);
    text-decoration: none;
    padding: 2px 8px;
    border-radius: 3px;
    transition: background 0.1s;
  }

  .footer-briefing-link:hover {
    background: var(--teal-pale);
    text-decoration: none;
  }

  .footer-briefing-link.current {
    color: var(--text-muted);
    pointer-events: none;
    font-weight: 400;
  }

  /* -- Responsive ------------------------------------ */
  @media (max-width: 900px) {
    .story-grid { grid-template-columns: repeat(2, 1fr); }
  }

  @media (max-width: 680px) {
    .unified-header-inner {
      flex-wrap: wrap;
      height: auto;
      padding: 8px 16px;
      gap: 4px;
    }
    .header-nav { width: 100%; overflow-x: auto; }
    .header-date { display: none; }
    .cover-block { grid-template-columns: 1fr; }
    .cover-right { border-left: none; border-top: 4px solid var(--oci-accent); }
    .hero-card { grid-template-columns: 1fr; }
    .hero-img { min-height: 120px; max-height: 160px; }
    .story-grid { grid-template-columns: 1fr; }
    .audience-tabs-inner { overflow-x: auto; }
  }

  ::-webkit-scrollbar { width: 5px; height: 5px; }
  ::-webkit-scrollbar-track { background: var(--gray-bg); }
  ::-webkit-scrollbar-thumb { background: var(--gray-mid); border-radius: 3px; }
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

def _remap_section_for_audience(article: dict, audience_id: str) -> str:
    """Return the best section key for *article* given the audience's weights.

    If the article's classified section already exists in the audience's
    ``section_weights`` we keep it.  Otherwise we consult ``SECTION_REMAP``
    (and the article's full ``sections`` list) to find the first candidate
    that the audience actually weights.  As a last resort we fall back to
    the audience's highest-weighted section.
    """
    profile = AUDIENCE_PROFILES[audience_id]
    weights = profile["section_weights"]

    classified = article.get("classified_section") or (
        article["sections"][0] if article.get("sections") else "other"
    )

    # Fast path: the classified section is already weighted by this audience.
    if classified in weights:
        return classified

    # Check all sections the article was tagged with; use the first that
    # directly matches an audience weight key.
    for sec in article.get("sections", []):
        if sec in weights:
            return sec

    # Walk the SECTION_REMAP candidates for the classified section.
    for candidate in SECTION_REMAP.get(classified, []):
        if candidate in weights:
            return candidate

    # Also try remap candidates for every section in the article's list.
    for sec in article.get("sections", []):
        for candidate in SECTION_REMAP.get(sec, []):
            if candidate in weights:
                return candidate

    # Fallback: audience's highest-weighted section.
    return max(weights, key=weights.get)


def _group_by_section(articles: list[dict]) -> dict[str, list[dict]]:
    """Group articles by section.

    If an article carries an ``_audience_section`` key (set by the
    per-audience remapping step) that value takes priority over the
    generic ``classified_section``.
    """
    groups: dict[str, list[dict]] = {}
    for a in articles:
        sec = a.get("_audience_section") or a.get("classified_section") or (
            a["sections"][0] if a.get("sections") else "other"
        )
        groups.setdefault(sec, []).append(a)
    return groups

def _is_fresh(pub: datetime | None, threshold_hours: int = 6) -> bool:
    if pub is None:
        return False
    return (datetime.now(tz=timezone.utc) - pub).total_seconds() / 3600 < threshold_hours


# ---------------------------------------------------------------------------
# Hero card (first article per section — has image, full width)
# ---------------------------------------------------------------------------

def _render_hero_card(article: dict, audience_id: str) -> str:
    per   = article.get("per_audience_summaries", {}).get(audience_id, {})
    head  = _esc(per.get("headline", article["title"]))
    summ  = _esc(per.get("summary",  article.get("summary","")[:250]))
    impl  = _esc(per.get("oci_implication",""))
    conf  = article.get("confidence","medium")
    topics= article.get("topics",[])[:2]
    pub   = article.get("published_at")
    rel   = _relative_time(pub) if pub else ""
    abs_t = pub.strftime("%b %d, %H:%M") if pub else ""
    tcol  = _tier_color(article["tier"])
    src   = _esc(article["source"])
    url   = _esc(article["url"])
    seed  = _image_seed(article["url"])
    pills = "".join(f'<span class="topic-pill">{_esc(t)}</span>' for t in topics)

    oci = f'<div class="hero-oci">{impl}</div>' if impl else ""

    new_badge = ""
    if _is_fresh(pub):
        new_badge = ' <span class="new-badge" aria-label="Published within the last 6 hours">NEW</span>'

    return f"""<article class="hero-card">
      <div class="hero-img">
        <img src="https://picsum.photos/seed/{seed}/400/260" alt="" loading="lazy">
        <span class="hero-img-badge" style="background:{tcol}">{src}</span>
      </div>
      <div class="hero-body">
        <div class="hero-meta">
          {pills}
          <span class="conf-pill {_conf_class(conf)}">{conf}</span>
          {new_badge}
        </div>
        <div class="hero-headline"><a href="{url}" target="_blank" rel="noopener">{head}</a></div>
        <div class="hero-summary">{summ}</div>
        {oci}
        <div class="hero-footer">{src} &nbsp;·&nbsp; {abs_t} &nbsp;·&nbsp; {rel}</div>
      </div>
    </article>"""


# ---------------------------------------------------------------------------
# Story card (3-column grid item — no image)
# ---------------------------------------------------------------------------

def _render_story_card(article: dict, audience_id: str) -> str:
    per   = article.get("per_audience_summaries", {}).get(audience_id, {})
    head  = _esc(per.get("headline", article["title"]))
    summ  = _esc(per.get("summary",  article.get("summary","")[:180]))
    pub   = article.get("published_at")
    rel   = _relative_time(pub) if pub else ""
    tcol  = _tier_color(article["tier"])
    src   = _esc(article["source"])
    url   = _esc(article["url"])

    fresh = _is_fresh(pub)
    fresh_class = " is-fresh" if fresh else ""
    new_badge = ""
    if fresh:
        new_badge = '<span class="new-badge">NEW</span>'

    return f"""<article class="story-card{fresh_class}">
      <div class="card-meta">
        <span class="src-badge" style="background:{tcol}">{src}</span>
        {new_badge}
        <span class="card-timestamp">{rel}</span>
      </div>
      <div class="card-headline"><a href="{url}" target="_blank" rel="noopener">{head}</a></div>
      <div class="card-summary">{summ}</div>
    </article>"""


# ---------------------------------------------------------------------------
# Section (full-width header + hero + 3-column grid)
# ---------------------------------------------------------------------------

def _render_section(section: str, articles: list[dict], audience_id: str) -> str:
    meta   = _section_meta(section)
    sec_id = f"{audience_id}-{section}"
    n      = len(articles)

    hero_html = _render_hero_card(articles[0], audience_id) if articles else ""
    cards_html = "".join(_render_story_card(a, audience_id) for a in articles[1:])
    grid_block = f'<div class="story-grid">{cards_html}</div>' if articles[1:] else ""

    return f"""<section class="section-block" id="{sec_id}" aria-label="{_esc(meta['label'])}">
      <div class="section-header">
        <span class="section-label-bar">{_esc(meta['label'])}</span>
        <span class="section-count">{n} {"story" if n==1 else "stories"}</span>
      </div>
      {hero_html}
      {grid_block}
    </section>"""


# ---------------------------------------------------------------------------
# Section nav
# ---------------------------------------------------------------------------

def _render_section_nav(sections: list[tuple[str,int]], audience_id: str) -> str:
    return "".join(
        f'<a class="header-nav-link" href="#{audience_id}-{s}">{_esc(_section_meta(s)["label"])}</a>'
        for s, c in sections
    )


# ---------------------------------------------------------------------------
# Executive summary
# ---------------------------------------------------------------------------

def _render_exec_summary(exec_data: dict, audience_id: str, articles: list[dict]) -> str:
    bullets = exec_data.get("bullets", [])
    impl    = _esc(exec_data.get("oci_implication_of_day", ""))

    bullet_items = "".join(
        f'<li><span class="bullet-num">{i+1}</span> {_esc(b)}</li>'
        for i, b in enumerate(bullets)
    )

    oci_box = ""
    if impl:
        oci_box = f"""<div class="oci-badge-strip">
          <span class="oci-badge-icon">&#9670;</span>
          <span class="oci-callout-label">OCI Implication of the Day</span>
        </div>
        <div class="oci-callout-text">{impl}</div>"""

    return f"""<div class="cover-block" id="{audience_id}-exec" aria-label="Executive Summary">
      <div class="cover-left">
        <div class="cover-overline">Executive Summary</div>
        <ul class="cover-bullets">{bullet_items}</ul>
      </div>
      <div class="cover-right" aria-label="OCI Implication of the Day">
        {oci_box}
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
) -> str:
    profile = AUDIENCE_PROFILES[audience_id]

    # Remap sections for this audience so articles land under the correct
    # section_weights keys (e.g. "deals" -> "multicloud" for Nathan).
    for a in articles:
        a["_audience_section"] = _remap_section_for_audience(a, audience_id)

    groups  = _group_by_section(articles)

    # Order sections by audience weights
    ordered: list[tuple[str, list[dict]]] = []
    seen: set[str] = set()
    for sec in profile["section_weights"]:
        if sec in groups:
            ordered.append((sec, groups[sec]))
            seen.add(sec)
    for sec, arts in groups.items():
        if sec not in seen:
            ordered.append((sec, arts))

    # Deduplicate articles by URL across sections.
    # The first occurrence wins (highest-weighted section).
    seen_urls: set[str] = set()
    deduped_ordered: list[tuple[str, list[dict]]] = []
    for sec, arts in ordered:
        unique_arts = []
        for a in arts:
            url = a.get("url", "")
            if url not in seen_urls:
                seen_urls.add(url)
                unique_arts.append(a)
        if unique_arts:
            deduped_ordered.append((sec, unique_arts))
    ordered = deduped_ordered

    sec_with_counts = [(s, len(a)) for s, a in ordered]
    sec_nav   = _render_section_nav(sec_with_counts, audience_id)
    exec_html = _render_exec_summary(exec_summary, audience_id, articles)
    secs_html = "\n".join(_render_section(s, a, audience_id) for s, a in ordered)
    gen_str   = generation_time.strftime("%Y-%m-%d %H:%M UTC")

    briefing_links = ""
    for aud_id in AUDIENCE_ORDER:
        p = AUDIENCE_PROFILES[aud_id]
        current_cls = " current" if aud_id == audience_id else ""
        aria_current = ' aria-current="page"' if aud_id == audience_id else ""
        briefing_links += f'<a class="footer-briefing-link{current_cls}" href="?audience={aud_id}"{aria_current}>{_esc(p["name"])}</a>\n'

    return f"""<div class="audience-panel" data-audience="{audience_id}" data-sec-nav="{_esc(sec_nav)}">
      <main>
        <div class="page-wrap">
          {exec_html}
          {secs_html}
          <div class="divider"></div>
          <footer class="page-footer">
            <div>{_esc(profile['name'])} &middot; {gen_str} &middot; {len(articles)} stories &middot;
            Powered by Oracle Code Assist</div>
            <div class="footer-briefings">
              <div class="footer-briefings-label">View other briefings</div>
              {briefing_links}
            </div>
          </footer>
        </div>
      </main>
    </div>"""


# ---------------------------------------------------------------------------
# Masthead + audience tabs
# ---------------------------------------------------------------------------

def _render_masthead(generation_time: datetime) -> str:
    date_str = generation_time.strftime("%a %b %d, %Y")
    return f"""<header class="unified-header">
      <div class="unified-header-inner">
        <div class="header-title"><span>AI</span> Daily Briefing</div>
        <div class="header-date">{date_str}</div>
        <nav class="header-nav" aria-label="Section navigation" id="header-nav">
        </nav>
      </div>
    </header>"""


def _render_audience_tabs() -> str:
    tabs = ""
    for aud_id in AUDIENCE_ORDER:
        p = AUDIENCE_PROFILES[aud_id]
        accent = _esc(p.get('accent_color', '#5B9DB5'))
        tabs += f"""<button class="audience-tab" data-switch="{aud_id}" style="--tab-accent:{accent}" onclick="switchAudience('{aud_id}')">
          {_esc(p['name'])}
        </button>"""
    return f"""<div class="audience-tabs">
      <div class="audience-tabs-inner">
        {tabs}
      </div>
    </div>"""


# ---------------------------------------------------------------------------
# JS switcher
# ---------------------------------------------------------------------------
SWITCHER_JS = """
  function switchAudience(id) {
    document.querySelectorAll('.audience-panel').forEach(el => el.classList.remove('active'));
    const p = document.querySelector('.audience-panel[data-audience="'+id+'"]');
    if (p) {
      p.classList.add('active');
      var nav = document.getElementById('header-nav');
      if (nav && p.dataset.secNav) {
        nav.innerHTML = p.dataset.secNav;
      }
    }
    document.querySelectorAll('.audience-tab').forEach(b => {
      b.classList.toggle('active', b.dataset.switch===id);
    });
    try { localStorage.setItem('oci-aud', id); } catch(e) {}
  }
  (function(){
    var params = new URLSearchParams(window.location.search);
    var urlAud = params.get('audience') || '';
    var last=''; try { last=localStorage.getItem('oci-aud')||''; } catch(e) {}
    var ids=Array.from(document.querySelectorAll('.audience-panel')).map(function(p){return p.dataset.audience});
    var pick = ids.includes(urlAud) ? urlAud : (ids.includes(last) ? last : (ids[0]||''));
    switchAudience(pick);
  })();
"""


# ---------------------------------------------------------------------------
# Page assembly
# ---------------------------------------------------------------------------

def _page_html(title: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <style>
{BASE_CSS}
  .mt {{ margin-top: 16px; }}
  </style>
</head>
<body>
{body}
</body>
</html>"""


def render_combined_html(
    all_audience_data: dict[str, dict],
    generation_time: datetime | None = None,
) -> str:
    if generation_time is None:
        generation_time = datetime.now(tz=timezone.utc)

    date_str = generation_time.strftime("%Y-%m-%d")
    panels = ""
    for aud_id in AUDIENCE_ORDER:
        data = all_audience_data.get(aud_id, {})
        panels += _render_audience_panel(
            aud_id,
            data.get("articles", []),
            data.get("exec_summary", {"bullets":[], "oci_implication_of_day":""}),
            generation_time,
        )

    body = f"""
    {_render_masthead(generation_time)}
    {_render_audience_tabs()}
    {panels}
    <script>{SWITCHER_JS}</script>"""

    return _page_html(f"OCI AI Intelligence — {date_str}", body)


def render_single_audience_html(
    audience_id: str,
    articles: list[dict],
    exec_summary: dict,
    generation_time: datetime | None = None,
) -> str:
    if generation_time is None:
        generation_time = datetime.now(tz=timezone.utc)

    profile  = AUDIENCE_PROFILES[audience_id]
    date_str = generation_time.strftime("%Y-%m-%d")
    panel    = _render_audience_panel(audience_id, articles, exec_summary, generation_time)

    panel = panel.replace('class="audience-panel"', 'class="audience-panel active"', 1)

    # Build section nav links from the audience's articles so we can
    # server-render them directly into the masthead instead of relying on JS.
    groups  = _group_by_section(articles)
    ap      = AUDIENCE_PROFILES[audience_id]
    nav_ordered: list[tuple[str, int]] = []
    nav_seen: set[str] = set()
    for sec in ap["section_weights"]:
        if sec in groups:
            nav_ordered.append((sec, len(groups[sec])))
            nav_seen.add(sec)
    for sec, arts in groups.items():
        if sec not in nav_seen:
            nav_ordered.append((sec, len(arts)))
    sec_nav_html = _render_section_nav(nav_ordered, audience_id)

    # Inject section nav links directly into the header-nav element.
    masthead = _render_masthead(generation_time)
    masthead = masthead.replace(
        '<nav class="header-nav" aria-label="Section navigation" id="header-nav">\n        </nav>',
        f'<nav class="header-nav" aria-label="Section navigation" id="header-nav">\n          {sec_nav_html}\n        </nav>',
    )

    body = f"""
    {masthead}
    {panel}"""

    return _page_html(f"OCI AI Intelligence — {_esc(profile['name'])} — {date_str}", body)


# ---------------------------------------------------------------------------
# File output
# ---------------------------------------------------------------------------

def save_briefings(
    all_audience_data: dict[str, dict],
    output_dir: Path,
    generation_time: datetime | None = None,
) -> dict[str, Path]:
    if generation_time is None:
        generation_time = datetime.now(tz=timezone.utc)

    output_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}

    for aud_id in AUDIENCE_ORDER:
        if aud_id not in all_audience_data:
            continue
        data     = all_audience_data[aud_id]
        articles = data.get("articles", [])
        html     = render_single_audience_html(aud_id, articles, data.get("exec_summary", {}), generation_time)
        p        = output_dir / f"{aud_id}.html"
        p.write_text(html, encoding="utf-8")
        paths[aud_id] = p
        logger.info("Wrote %s (%d bytes)", p, len(html))

    combined   = render_combined_html(all_audience_data, generation_time)
    index_path = output_dir / "index.html"
    index_path.write_text(combined, encoding="utf-8")
    paths["index"] = index_path
    logger.info("Wrote %s (%d bytes)", index_path, len(combined))

    return paths
