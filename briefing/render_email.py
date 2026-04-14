"""
render_email.py — Email-safe HTML briefing generation.

Produces inline-styled, table-based HTML that works in Gmail, Outlook, Apple Mail.
Same content as the web version but email-client compatible.
"""

import re
import logging
from datetime import datetime, timezone

from briefing.config import AUDIENCE_PROFILES

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Section metadata (same as render.py)
# ---------------------------------------------------------------------------
SECTION_META = {
    "financial":      {"label": "Financial & Markets"},
    "ai":             {"label": "Artificial Intelligence"},
    "compete":        {"label": "Competitive Intel"},
    "datacenter":     {"label": "Datacenter & Infrastructure"},
    "power":          {"label": "Power & Energy"},
    "security":       {"label": "Security & Compliance"},
    "deals":          {"label": "Deals & Partnerships"},
    "multicloud":     {"label": "Multi-Cloud & Ecosystem"},
    "oss":            {"label": "Open Source"},
    "partnerships":   {"label": "Strategic Partnerships"},
    "community":      {"label": "Community Signal"},
    "infrastructure": {"label": "Infrastructure"},
    "other":          {"label": "Technology"},
}

def _esc(text: str) -> str:
    return (text or "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")

def _relative_time(dt: datetime) -> str:
    now = datetime.now(tz=timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    diff = now - dt
    h = diff.total_seconds() / 3600
    if h < 1: return f"{int(diff.total_seconds()/60)}m ago"
    if h < 24: return f"{int(h)}h ago"
    return f"{int(h/24)}d ago"

def _group_by_section(articles: list[dict]) -> dict[str, list[dict]]:
    groups = {}
    for a in articles:
        sec = a.get("classified_section") or (a["sections"][0] if a.get("sections") else "other")
        if not sec or sec == "None":
            sec = "other"
        groups.setdefault(sec, []).append(a)
    return groups


def render_email_html(
    audience_id: str,
    articles: list[dict],
    exec_summary: dict,
    generation_time: datetime | None = None,
    date_range: str = "",
) -> str:
    """Render email-safe HTML for a single audience briefing."""
    if generation_time is None:
        generation_time = datetime.now(tz=timezone.utc)

    profile = AUDIENCE_PROFILES[audience_id]
    date_str = date_range or generation_time.strftime("%a %b %d, %Y")

    # Executive summary
    bullets = exec_summary.get("bullets", [])
    outlook = _esc(exec_summary.get("market_outlook", ""))

    bullet_rows = ""
    for i, b in enumerate(bullets):
        b = re.sub(r'^(?:Bullet\s*\d+\s*[:\-–—]\s*|^\d+\.\s*)', '', b)
        bg = "rgba(255,255,255,0.08)" if i == 0 else "rgba(255,255,255,0.04)"
        color = "#F1F5F9" if i == 0 else "#CBD5E1"
        weight = "600" if i == 0 else "400"
        bullet_rows += f"""<tr><td style="padding:6px 10px;font-size:13px;line-height:1.5;color:{color};font-weight:{weight};background:{bg};border-left:3px solid {'#3B82F6' if i == 0 else '#334155'};border-radius:3px;">
            <span style="color:#64748B;font-size:10px;font-weight:700;margin-right:8px;">{i+1}</span>{_esc(b)}
        </td></tr>
        <tr><td style="height:3px;"></td></tr>"""

    outlook_html = ""
    if outlook:
        outlook_html = f"""<td style="background:#EFF6FF;padding:16px 18px;border-left:2px solid #2563EB;vertical-align:top;">
            <div style="font-size:9px;font-weight:700;letter-spacing:0.16em;text-transform:uppercase;color:#2563EB;margin-bottom:8px;">Market Outlook</div>
            <div style="font-size:13px;line-height:1.6;color:#334155;">{outlook}</div>
        </td>"""

    # Group articles by section
    groups = _group_by_section(articles)
    ordered = []
    seen = set()
    for sec in profile["section_weights"]:
        if sec in groups:
            ordered.append((sec, groups[sec]))
            seen.add(sec)

    # Render sections
    sections_html = ""
    for sec, arts in ordered:
        meta = SECTION_META.get(sec, SECTION_META["other"])
        label = _esc(meta["label"])
        count = len(arts)

        # Section header
        sections_html += f"""<tr><td style="padding:20px 0 6px 0;">
            <table width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
                <td style="font-size:9px;font-weight:700;letter-spacing:0.16em;text-transform:uppercase;color:#64748B;padding-bottom:4px;border-bottom:1px solid #D1D5DB;">
                    {label} <span style="color:#94A3B8;font-weight:400;margin-left:8px;">{count}</span>
                </td>
            </tr></table>
        </td></tr>"""

        # Article cards — 3-column table
        cells = []
        for a in arts:
            per = a.get("per_audience_summaries", {}).get(audience_id, {})
            title = _esc(per.get("headline", a["title"]))
            pub = a.get("published_at")
            src = _esc(a.get("source", ""))
            abs_t = pub.strftime("%b %d") if pub else ""
            rel = _relative_time(pub) if pub else ""
            meta_str = " · ".join(p for p in [src, abs_t, rel] if p)
            url = _esc(a["url"])

            cell = f"""<td width="33%" style="padding:4px 3px;vertical-align:top;">
                <div style="background:#E8ECF1;padding:9px 12px;border-left:2px solid #8B9BB5;">
                    <div style="font-size:12.5px;font-weight:600;line-height:1.35;color:#1A1D23;margin-bottom:2px;">
                        <a href="{url}" style="color:#1A1D23;text-decoration:none;">{title}</a>
                    </div>
                    <div style="font-size:10px;color:#94A3B8;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
                        {meta_str}
                    </div>
                </div>
            </td>"""
            cells.append(cell)

        # Fill into 3-column rows
        for row_start in range(0, len(cells), 3):
            row_cells = cells[row_start:row_start + 3]
            while len(row_cells) < 3:
                row_cells.append('<td width="33%" style="padding:4px 3px;"></td>')
            sections_html += f"""<tr><td>
                <table width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
                    {"".join(row_cells)}
                </tr></table>
            </td></tr>"""

    gen_str = generation_time.strftime("%Y-%m-%d %H:%M UTC")

    return f"""<!DOCTYPE html>
<html lang="en" xmlns="http://www.w3.org/1999/xhtml">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Weekly Briefing — {_esc(profile['name'])}</title>
    <!--[if mso]>
    <style>table {{ border-collapse: collapse; }}</style>
    <![endif]-->
</head>
<body style="margin:0;padding:0;background-color:#F4F5F7;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;">
    <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#F4F5F7;">
    <tr><td align="center" style="padding:0;">

        <!-- Masthead -->
        <table width="640" cellpadding="0" cellspacing="0" border="0" style="background-color:#1E293B;">
        <tr><td style="padding:12px 24px;">
            <table width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
                <td style="font-size:14px;font-weight:700;color:#F1F5F9;letter-spacing:0.03em;">
                    <span style="color:#64748B;font-weight:400;">AI</span> Weekly Briefing
                </td>
                <td align="right" style="font-size:10px;color:#64748B;letter-spacing:0.04em;">
                    {date_str}
                </td>
            </tr></table>
        </td></tr>
        </table>

        <!-- Content -->
        <table width="640" cellpadding="0" cellspacing="0" border="0" style="background-color:#F4F5F7;">
        <tr><td style="padding:20px 16px;">

            <!-- Executive Summary -->
            <table width="100%" cellpadding="0" cellspacing="0" border="0" style="border:1px solid #334155;">
            <tr>
                <!-- Left: Bullets -->
                <td width="60%" style="background:#1E293B;padding:16px 18px;vertical-align:top;">
                    <div style="font-size:9px;font-weight:700;letter-spacing:0.18em;text-transform:uppercase;color:#64748B;margin-bottom:10px;">Executive Summary</div>
                    <table width="100%" cellpadding="0" cellspacing="0" border="0">
                        {bullet_rows}
                    </table>
                </td>
                <!-- Right: Outlook -->
                {outlook_html}
            </tr>
            </table>

            <!-- Sections -->
            <table width="100%" cellpadding="0" cellspacing="0" border="0">
                {sections_html}
            </table>

            <!-- Footer -->
            <table width="100%" cellpadding="0" cellspacing="0" border="0">
            <tr><td style="padding:20px 0 8px;border-top:1px solid #D1D5DB;">
                <div style="font-size:10px;color:#94A3B8;text-align:center;">
                    {_esc(profile['name'])} · {gen_str} · {len(articles)} stories · Powered by Oracle Code Assist
                </div>
            </td></tr>
            </table>

        </td></tr>
        </table>

    </td></tr>
    </table>
</body>
</html>"""
