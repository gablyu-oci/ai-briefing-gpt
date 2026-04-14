# OCI AI Daily Executive Briefing -- Layout and Design Specification v2.2

**Version:** 2.2
**Date:** 2026-03-11
**Target:** render.py (pure HTML/CSS string templates, no JS framework)
**Audience:** Frontend engineer implementing in Python f-string HTML generation

---

## v2.2 Revision Notes

This revision addresses five specific complaints from SVP review while preserving three
elements the SVP explicitly approved.

### Changes Made

**1. Collapsed header chrome from 138px to 40px (Complaint #1).**
Killed the standalone Top Bar entirely. Merged masthead into a single 40px strip containing
only the title, date, and section nav links. Removed the vanity elements: overline, tagline,
volume/issue numbers. This recovers 98px of viewport space -- over 10% of usable area on
1080p. The Section Navigation Bar is now embedded in the right side of this unified header.

**2. Removed Audience Tab Bar from default view (Complaint #2).**
The audience tab bar is eliminated from the header stack. Instead, the page auto-selects
the correct briefing based on URL parameter. A "View other briefings" link is placed in
the footer. No more cognitive overhead wondering if you are on the right tab.

**3. Removed per-story OCI implications from story rows (Complaint #3).**
OCI implications now appear in exactly two places: (a) the executive summary 60/40 amber
callout, and (b) hero cards. Story rows no longer render .row-oci elements. This reduces
visual noise -- gold boxes are now scarce enough to be meaningful.

**4. Story row headlines expanded to 2-line clamp (Complaint #4).**
Replaced single-line nowrap+ellipsis with -webkit-line-clamp: 2. To reclaim the vertical
space, story row summaries are reduced to 1-line clamp. Headlines are the highest-value
text for scanners; summaries are supplemental.

**5. Added "NEW" badge for stories published within 6 hours (Complaint #5).**
Stories with a publication timestamp less than 6 hours old display an inline "NEW" badge
next to the source name, plus a 3px left border in teal on the story row. This provides
an immediate temporal signal without requiring the reader to parse timestamps.

### Preserved Elements
- 60/40 exec summary split with amber OCI callout -- UNCHANGED
- Hero-plus-compact-rows newspaper pattern -- UNCHANGED
- Vertical space budget discipline -- IMPROVED (98px header savings)

---

## Table of Contents

1. Design Philosophy and Constraints
2. Overall Page Structure and Grid
3. Design Tokens
4. Typography Scale
5. Spacing System
6. Unified Header Bar
7. Executive Summary Component
8. OCI Implication Callout Box
9. News Section Layout
10. Hero Card Component
11. Story Row Component
12. Freshness Indicator (NEW Badge)
13. Footer
14. Interaction States
15. Responsive Behavior
16. Accessibility Notes
17. ASCII Wireframes
18. Implementation Checklist

---

## 1. Design Philosophy and Constraints

### Goals
- A busy SVP should absorb the day's key signals in under 60 seconds
- Everything important visible within 2 "pages" (roughly 1800px of vertical scroll on a 1080p monitor)
- Newspaper/magazine feel: clear visual hierarchy, blocks, scannable headlines
- High information density without visual clutter
- OCI Implications must pop visually -- they are the unique value of this newsletter
- Minimize header chrome so news content starts as high as possible

### Constraints
- Pure HTML/CSS rendered as Python f-strings in render.py
- No JS frameworks, no build tools
- Minimal JS: only audience panel switching via URL parameter (tab bar removed from UI)
- Images: only the hero story per section gets a thumbnail; all other stories are text-only compact rows
- Must work in Chrome, Safari, Edge (modern browsers only -- no IE)
- Max page width: 1100px (already set, keep it)

### What Changes from v2.1
- Kill Top Bar, Masthead, Audience Tab Bar, and Section Nav Bar (4 separate bars)
- Replace with single 40px Unified Header Bar containing title + section nav links
- Remove audience tab bar; auto-select briefing, add "View other briefings" to footer
- Remove .row-oci from story rows; OCI implications appear only in exec summary + hero cards
- Story row headlines: line-clamp: 2 (was nowrap + ellipsis single line)
- Story row summaries: line-clamp: 1 (was line-clamp: 2)
- Add "NEW" badge and teal left-border accent for stories published within 6 hours
- Remove unused Google Fonts Lato import (dead weight network request)

---

## 2. Overall Page Structure and Grid

```
Max width: 1100px, centered
Page background: #F4F6F8

Vertical stack (top to bottom):
+----------------------------------------------------------+
| UNIFIED HEADER BAR (charcoal, 40px tall)                  |
+----------------------------------------------------------+
|                                                          |
| PAGE WRAP (padding: 14px 24px 32px)                      |
|                                                          |
|   EXECUTIVE SUMMARY BLOCK                                |
|     [3fr left: bullets] | [2fr right: OCI implication]   |
|                                                          |
|   SECTION 1 (hero + story rows)                          |
|   SECTION 2 (hero + story rows)                          |
|   ... more sections ...                                  |
|                                                          |
|   FOOTER (includes "View other briefings" link)          |
+----------------------------------------------------------+
```

Total header chrome: 40px (was 138px). Savings: 98px.

### CSS for page-wrap
```css
.page-wrap {
  max-width: 1100px;
  margin: 0 auto;
  padding: 14px 24px 32px;
}
```

---

## 3. Design Tokens

All tokens are defined as CSS custom properties on :root.

### Colors
```css
:root {
  /* Primary palette */
  --teal:        #5B9DB5;   /* Primary brand, section labels, accents */
  --teal-dark:   #3D7A96;   /* Links, hover states */
  --teal-light:  #D6EAF2;   /* Topic pills bg, section rules */
  --teal-pale:   #EBF5FA;   /* Story row hover bg */
  --charcoal:    #2C3E50;   /* Header bar, exec summary left bg, headlines */
  --charcoal2:   #34495E;   /* Secondary dark text */

  /* Grays */
  --gray-dark:   #7F8C8D;   /* Muted labels */
  --gray-mid:    #BDC3C7;   /* Scrollbar thumb, subtle borders */
  --gray-light:  #ECF0F1;   /* Dividers inside cards */
  --gray-bg:     #F4F6F8;   /* Page background */
  --white:       #FFFFFF;   /* Card backgrounds */

  /* Text */
  --text:        #2C3E50;   /* Primary body text */
  --text-mid:    #555E68;   /* Summaries, secondary text */
  --text-muted:  #95A5A6;   /* Timestamps, metadata */

  /* Borders and Shadows */
  --border:      #D5DDE3;   /* Card borders */
  --shadow:      0 2px 8px rgba(44,62,80,0.10);   /* Card hover */
  --shadow-sm:   0 1px 3px rgba(44,62,80,0.06);   /* Card default */

  /* Tier indicator colors (for source badges and dots) */
  /* These remain unchanged from current implementation */

  /* Confidence pill colors -- unchanged */
  /* .conf-high:   bg #D5EFE0, text #1A7A3C */
  /* .conf-medium: bg #FEF3CD, text #856404 */
  /* .conf-low:    bg #E9ECEF, text #6C757D */

  /* OCI callout -- amber/gold accent for maximum visibility */
  --oci-accent:      #D4880F;   /* Left border stripe */
  --oci-bg:          #FFF8EE;   /* Warm cream background */
  --oci-text:        #7A5200;   /* Dark gold text */
  --oci-label:       #B8730C;   /* Label color */

  /* Freshness indicator -- NEW in v2.2 */
  --new-badge-bg:    #E8F5E9;   /* Light green background */
  --new-badge-text:  #2E7D32;   /* Dark green text */
  --new-border:      var(--teal); /* Teal left border for fresh stories */

  /* Misc */
  --radius:      4px;
  --serif:       Georgia, 'Times New Roman', serif;
}
```

### Key Design Decision: OCI Implication Color System

The amber/gold palette makes OCI callouts immediately distinguishable from all other UI
elements. In v2.2, OCI implications are limited to the exec summary callout and hero cards
only. Story rows no longer carry per-story OCI implications. This restraint ensures the
gold accent retains its signal value -- when everything is highlighted, nothing is.

Contrast ratios for the amber palette:
- #7A5200 text on #FFF8EE background: 5.8:1 (passes WCAG AA)
- #B8730C label on #FFF8EE background: 3.8:1 (passes AA for bold/large text)
- #D4880F accent border: decorative, no contrast requirement

---

## 4. Typography Scale

### Font Families
- Headlines: Georgia, 'Times New Roman', serif (var(--serif))
- Body/UI: 'Helvetica Neue', Arial, sans-serif (system default)
- Remove the Google Fonts Lato import from _page_html -- it is loaded but never used

### Scale (all sizes in px, base html font-size: 13px)

| Element                    | Family    | Size   | Weight | Line-height | Letter-spacing | Transform   |
|----------------------------|-----------|--------|--------|-------------|----------------|-------------|
| Header title               | serif     | 18px   | 700    | 1.0         | -0.5px         | uppercase   |
| Header title "AI" span     | serif     | 14px   | 700    | 1.0         | 0              | italic      |
| Header date                | sans      | 9px    | 400    | 1.0         | 0.06em         | none        |
| Header nav link            | sans      | 9px    | 600    | 1.0         | 0.07em         | uppercase   |
| Exec summary overline      | sans      | 8.5px  | 700    | 1.0         | 0.18em         | uppercase   |
| Exec summary bullet        | sans      | 11.5px | 400    | 1.4         | 0              | none        |
| OCI callout label          | sans      | 8px    | 800    | 1.0         | 0.14em         | uppercase   |
| OCI callout text           | sans      | 11.5px | 400    | 1.5         | 0              | none        |
| Section label bar          | sans      | 8.5px  | 800    | 1.0         | 0.14em         | uppercase   |
| Section count              | sans      | 9px    | 600    | 1.0         | 0              | none        |
| Hero headline              | serif     | 15px   | 700    | 1.28        | 0              | none        |
| Hero summary               | sans      | 11px   | 400    | 1.5         | 0              | none        |
| Hero OCI implication       | sans      | 10px   | 400    | 1.4         | 0              | none        |
| Hero footer                | sans      | 9px    | 400    | 1.0         | 0              | none        |
| Story row headline         | serif     | 12.5px | 700    | 1.28        | 0              | none        |
| Story row summary          | sans      | 10.5px | 400    | 1.45        | 0              | none        |
| Story row source name      | sans      | 8.5px  | 700    | 1.0         | 0.05em         | uppercase   |
| NEW badge                  | sans      | 7.5px  | 800    | 1.0         | 0.06em         | uppercase   |
| Source dot                 | n/a       | 6px    | n/a    | n/a         | n/a            | n/a         |
| Topic pill                 | sans      | 8px    | 600    | 1.0         | 0              | none        |
| Confidence pill            | sans      | 8px    | 600    | 1.0         | 0              | none        |
| Timestamp (row-right)      | sans      | 8.5px  | 400    | 1.8         | 0              | none        |
| Page footer                | sans      | 9px    | 400    | 2.0         | 0.04em         | none        |
| Footer briefing link       | sans      | 10px   | 600    | 1.0         | 0              | none        |

### Changes from v2.1
- Removed: Masthead title (28px), Masthead "AI" span (20px), Masthead overline, Masthead tagline,
  Top bar text, Audience tab, Section nav link
- Added: Header title (18px), Header "AI" span (14px), Header date, Header nav link, NEW badge
- Removed: Story row OCI impl (9.5px) -- no longer rendered

---

## 5. Spacing System

Base unit: 4px. All spacing is multiples of 4px.

| Token Name        | Value  | Usage                                        |
|-------------------|--------|----------------------------------------------|
| --space-xs        | 2px    | Minimal gaps (pill internal padding-top)     |
| --space-sm        | 4px    | Tight gaps (between meta pills)              |
| --space-md        | 8px    | Standard gap (between elements in a card)    |
| --space-lg        | 12px   | Section margins, card padding                |
| --space-xl        | 16px   | Between major blocks                         |
| --space-2xl       | 24px   | Page horizontal padding                      |

### Key Spacing Changes from v2.1
| Element                           | v2.1        | v2.2        | Savings  |
|-----------------------------------|-------------|-------------|----------|
| Header chrome (total)             | 138px       | 40px        | 98px     |
| .cover-block margin-bottom        | 14px        | 14px        | 0        |
| .cover-left padding               | 14px 16px   | 14px 16px   | 0        |
| .cover-right padding              | 14px 16px   | 14px 16px   | 0        |
| .section-block margin-bottom      | 14px        | 14px        | 0        |
| .hero-card margin-bottom          | 6px         | 6px         | 0        |
| .story-row padding                | 7px 10px    | 7px 10px    | 0        |
| .story-row (no .row-oci)          | ~70px w/oci | ~52px       | ~18px/row|
| .divider margin                   | 14px 0      | 14px 0      | 0        |

Major savings come from header collapse (98px) and removal of per-row OCI
implications (~18px per story row that had one).

---

## 6. Unified Header Bar

Replaces the former Top Bar (24px) + Masthead (52px) + Audience Tab Bar (34px) +
Section Nav Bar (28px). Total: 138px collapsed to 40px.

### Layout
```
+----------------------------------------------------------+
| AI DAILY BRIEFING     Mar 11, 2026    AI | COMP | FIN |..|
+----------------------------------------------------------+
  ^-- title (left)      ^-- date (center)  ^-- nav (right)
```

### CSS

```css
.unified-header {
  background: var(--charcoal);
  border-bottom: 3px solid var(--teal);
}

.unified-header-inner {
  max-width: 1100px;
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
```

Height: exactly 40px (including the 3px teal bottom border = 43px total).

### HTML Template
```html
<header class="unified-header">
  <div class="unified-header-inner">
    <div class="header-title"><span>AI</span> Daily Briefing</div>
    <div class="header-date">Wed Mar 11, 2026</div>
    <nav class="header-nav" aria-label="Section navigation">
      <a class="header-nav-link" href="#ai">AI</a>
      <a class="header-nav-link" href="#competitive">Competitive</a>
      <a class="header-nav-link" href="#financial">Financial</a>
      <a class="header-nav-link" href="#datacenter">Datacenter</a>
      <a class="header-nav-link" href="#deals">Deals</a>
      <a class="header-nav-link" href="#security">Security</a>
    </nav>
  </div>
</header>
```

### What Was Removed
- **Top Bar**: Volume/issue numbers, "Confidential" label -- vanity elements
- **Masthead**: Overline ("Oracle Cloud Infrastructure"), tagline, 3-column grid layout,
  left/right flanking metadata. Title is now 18px (was 28px) in a single horizontal line.
- **Audience Tab Bar**: Entirely removed from viewport. Auto-select briefing via URL param
  `?audience=karan`. "View other briefings" link moved to footer.
- **Section Nav Bar**: Merged into the right side of the unified header bar.

---

## 7. Executive Summary Component

This is the most important "above the fold" element. It communicates 3-5 key
bullets plus the OCI Implication of the Day in a single glanceable block.

**PRESERVED FROM SVP REVIEW: 60/40 split with amber OCI callout -- no changes.**

### Layout: 2-column grid (60/40)
```
+--------------------------------------+----------------------+
| CHARCOAL BACKGROUND (3fr)            | WARM CREAM BG (2fr)  |
|                                      | 4px gold left border |
| EXECUTIVE SUMMARY  (teal overline)   |                      |
|                                      | <> OCI IMPLICATION   |
| 1. First bullet point...            |    OF THE DAY        |
| 2. Second bullet point...           |                      |
| 3. Third bullet point...            | The implication text  |
| 4. Fourth bullet point...           | goes here spanning   |
| 5. Fifth bullet point...            | multiple lines...    |
|                                      |                      |
+--------------------------------------+----------------------+
```

### CSS

```css
.cover-block {
  display: grid;
  grid-template-columns: 3fr 2fr;
  gap: 0;
  background: var(--white);
  border: 1px solid var(--border);
  box-shadow: var(--shadow-sm);
  margin-bottom: 14px;
  border-radius: var(--radius);
  overflow: hidden;
}

.cover-left {
  background: var(--charcoal);
  color: white;
  padding: 14px 16px;
}

.cover-overline {
  font-size: 8.5px;
  font-weight: 700;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--teal);
  margin-bottom: 6px;
}

/* REMOVE: .cover-headline div entirely from _render_exec_summary().
   The "Today's Intelligence Briefing" text is redundant. Saves ~20px. */

.cover-bullets {
  list-style: none;
  padding: 0;
  margin: 0;
}

.cover-bullets li {
  display: flex;
  gap: 7px;
  align-items: flex-start;
  padding: 4px 0;
  border-bottom: 1px solid rgba(255,255,255,0.08);
  font-size: 11.5px;
  color: rgba(255,255,255,0.88);
  line-height: 1.4;
}

.cover-bullets li:last-child {
  border-bottom: none;
}

.bullet-num {
  width: 16px;
  height: 16px;
  background: var(--teal);
  color: white;
  font-size: 9px;
  font-weight: 700;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-top: 1px;
}
```

### Cover Right (OCI Implication of the Day)

```css
.cover-right {
  background: var(--oci-bg);               /* #FFF8EE warm cream */
  border-left: 4px solid var(--oci-accent); /* #D4880F gold */
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 8px;
}
```

CRITICAL: Remove the img tag and .cover-image-block from _render_exec_summary().
The right panel should contain ONLY the OCI callout. This recovers ~120px vertical.

### HTML Template for Right Panel

```html
<div class="cover-right">
  <div class="oci-badge-strip">
    <span class="oci-badge-icon">&#9670;</span>
    <span class="oci-callout-label">OCI Implication of the Day</span>
  </div>
  <div class="oci-callout-text">{impl}</div>
</div>
```

### New CSS Classes

```css
.oci-badge-strip {
  display: flex;
  align-items: center;
  gap: 5px;
}

.oci-badge-icon {
  color: var(--oci-accent);     /* #D4880F */
  font-size: 10px;
}

.oci-callout-label {
  font-size: 8px;
  font-weight: 800;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--oci-label);      /* #B8730C */
}

.oci-callout-text {
  font-size: 11.5px;
  color: var(--oci-text);       /* #7A5200 */
  line-height: 1.5;
}
```

---

## 8. OCI Implication Callout (Hero Cards Only)

**v2.2 CHANGE: OCI implications now appear in exactly two locations:**
1. Executive summary right panel (Section 7 above)
2. Hero card OCI line (this section)

**REMOVED: Story row OCI (.row-oci) is no longer rendered.** When everything is
highlighted, nothing is. Limiting gold callouts to the exec summary and hero cards
preserves their signal strength.

### Hero OCI Implication
```css
.hero-oci {
  font-size: 10px;
  color: var(--oci-text);           /* #7A5200 */
  background: var(--oci-bg);        /* #FFF8EE */
  border-left: 3px solid var(--oci-accent); /* #D4880F */
  padding: 4px 8px;
  border-radius: 2px;
  line-height: 1.4;
}
```

### Removed: .row-oci
The `.row-oci` CSS class should remain in the stylesheet for backwards compatibility
but the render function `_render_story_row()` must stop emitting the OCI implication
div for non-hero stories. Remove the OCI implication HTML from the story row template.

---

## 9. News Section Layout

### Section Header
```
--[ ARTIFICIAL INTELLIGENCE ]----------------------- 5 stories --
```

```css
.section-block {
  margin-bottom: 14px;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.section-label-bar {
  background: var(--teal);
  color: white;
  font-size: 8.5px;
  font-weight: 800;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  padding: 3px 10px;
  border-radius: 2px;
  white-space: nowrap;
}

.section-rule {
  flex: 1;
  height: 1px;
  background: var(--teal-light);
}

.section-count {
  font-size: 9px;
  color: var(--text-muted);
  font-weight: 600;
  white-space: nowrap;
}
```

### Section Content Stacking Order
```
[SECTION HEADER]
[HERO CARD -- image left + body right, horizontal grid]
[STORY ROW 1 -- compact text only]
[STORY ROW 2 -- compact text only]
[STORY ROW 3 -- compact text only]
```

---

## 10. Hero Card Component

One hero card per section. First (highest-scored) article.

**PRESERVED FROM SVP REVIEW: Hero-plus-compact-rows newspaper pattern.**

### CSS

```css
.hero-card {
  display: grid;
  grid-template-columns: 180px 1fr;
  background: var(--white);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
  box-shadow: var(--shadow-sm);
  margin-bottom: 6px;
  transition: box-shadow 0.12s;
}

.hero-card:hover {
  box-shadow: var(--shadow);
}

.hero-img {
  height: 100%;
  min-height: 120px;
  overflow: hidden;
  position: relative;
  background: var(--gray-light);
}

.hero-img img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.hero-img-badge {
  position: absolute;
  top: 5px;
  left: 5px;
  font-size: 7.5px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  padding: 2px 6px;
  border-radius: 2px;
  color: white;
  /* background color set inline via style= attribute using tier color */
}

.hero-body {
  padding: 10px 12px;
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
  font-size: 15px;
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
  /* Clamp to 3 lines max */
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* .hero-oci: see Section 8 above */

.hero-footer {
  font-size: 9px;
  color: var(--text-muted);
  border-top: 1px solid var(--gray-light);
  padding-top: 4px;
  margin-top: 2px;
}
```

Estimated hero card height: ~125-130px.

---

## 11. Story Row Component

Compact text-only rows for all non-hero articles.

**v2.2 CHANGES:**
- Headlines: 2-line clamp (was single-line nowrap+ellipsis)
- Summaries: 1-line clamp (was 2-line clamp) to reclaim space from taller headlines
- OCI implication line: REMOVED (was optional .row-oci)
- Fresh stories (<6h): teal left-border accent + "NEW" badge (see Section 12)

### CSS

```css
.story-list {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.story-row {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 8px;
  align-items: start;
  background: var(--white);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 7px 10px;
  transition: background 0.1s;
}

.story-row:hover {
  background: var(--teal-pale);
}

/* v2.2: Fresh story indicator -- applied when story is <6 hours old */
.story-row.is-fresh {
  border-left: 3px solid var(--new-border);  /* var(--teal) = #5B9DB5 */
  padding-left: 7px;  /* 10px minus 3px border to keep total width consistent */
}

.row-left {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.row-meta {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
}

.src-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
  display: inline-block;
}

.src-name {
  font-size: 8.5px;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--text-muted);
}

/* v2.2: NEW badge for stories published within 6 hours */
.new-badge {
  font-size: 7.5px;
  font-weight: 800;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--new-badge-text);    /* #2E7D32 */
  background: var(--new-badge-bg); /* #E8F5E9 */
  padding: 1px 4px;
  border-radius: 3px;
  flex-shrink: 0;
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

.row-headline {
  font-family: var(--serif);
  font-size: 12.5px;
  font-weight: 700;
  color: var(--charcoal);
  line-height: 1.28;
  /* v2.2: 2-line clamp (was single-line nowrap+ellipsis) */
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.row-headline a { color: var(--charcoal); }
.row-headline a:hover { color: var(--teal-dark); text-decoration: underline; }

.row-summary {
  font-size: 10.5px;
  color: var(--text-mid);
  line-height: 1.45;
  /* v2.2: 1-line clamp (was 2-line clamp) to offset taller headlines */
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* .row-oci: REMOVED in v2.2. No longer rendered in story rows.
   CSS kept for backwards compatibility but HTML template must not emit it. */
.row-oci {
  display: none;  /* Safety net: hide if accidentally emitted */
}

.row-right {
  text-align: right;
  flex-shrink: 0;
  font-size: 8.5px;
  color: var(--text-muted);
  line-height: 1.8;
  white-space: nowrap;
}
```

Estimated row height: ~52px (was ~55px without OCI, ~70px with OCI in v2.1).

---

## 12. Freshness Indicator (NEW Badge)

**v2.2 NEW FEATURE: Temporal urgency signal for fresh stories.**

Stories published within the last 6 hours get two visual indicators:
1. A green "NEW" pill badge in the meta row (next to source name)
2. A 3px teal left border on the story row

### Logic (in render.py)
```python
from datetime import datetime, timezone, timedelta

def is_fresh(published_at: str, threshold_hours: int = 6) -> bool:
    """Return True if the story was published within threshold_hours."""
    pub_dt = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
    return (datetime.now(timezone.utc) - pub_dt) < timedelta(hours=threshold_hours)
```

### HTML Template for Story Row Meta (when fresh)
```html
<div class="row-meta">
  <span class="src-dot" style="background:{tier_color}"></span>
  <span class="src-name">{source}</span>
  <span class="new-badge">NEW</span>
  <span class="topic-pill">{topic}</span>
  <span class="conf-pill conf-{level}">{confidence}</span>
</div>
```

### HTML Template for Story Row Container (when fresh)
```html
<article class="story-row is-fresh">
  ...
</article>
```

### CSS (repeated from Section 11 for clarity)
```css
.story-row.is-fresh {
  border-left: 3px solid var(--new-border);  /* #5B9DB5 teal */
  padding-left: 7px;  /* compensate: 10px original - 3px border */
}

.new-badge {
  font-size: 7.5px;
  font-weight: 800;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: #2E7D32;
  background: #E8F5E9;
  padding: 1px 4px;
  border-radius: 3px;
  flex-shrink: 0;
}
```

### Hero Card Freshness
Hero cards also support the freshness indicator. Add "NEW" badge in the .hero-meta row:
```html
<div class="hero-meta">
  <span class="topic-pill">{topic}</span>
  <span class="conf-pill conf-{level}">{confidence}</span>
  <span class="new-badge">NEW</span>  <!-- only if is_fresh() -->
</div>
```
Hero cards do NOT get the left-border treatment (they already have the image column).

### Accessibility
- The "NEW" badge must include `aria-label="Published within the last 6 hours"` for
  screen readers, since "NEW" alone lacks context.
- The teal left border is a supplementary visual cue; the badge carries the semantic meaning.

### Contrast Check
- #2E7D32 text on #E8F5E9 background: 4.8:1 (passes WCAG AA)

---

## 13. Footer

```css
.divider {
  height: 1px;
  background: var(--border);
  margin: 14px 0;
}

.page-footer {
  text-align: center;
  font-size: 9px;
  color: var(--text-muted);
  letter-spacing: 0.04em;
  line-height: 2;
}

.page-footer a { color: var(--teal-dark); }
```

### v2.2: "View Other Briefings" Link

The audience tab bar has been removed from the header. Instead, the footer includes
a link to switch briefings. This eliminates cognitive overhead for the primary reader
while still providing access to other views.

```css
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
```

### HTML Template for Footer
```html
<div class="divider"></div>
<footer class="page-footer">
  <div>{audience_name} . {date} {time} UTC . {story_count} stories . Claude</div>
  <div class="footer-briefings">
    <div class="footer-briefings-label">View other briefings</div>
    <a class="footer-briefing-link current" href="?audience=karan">Karan Batta</a>
    <a class="footer-briefing-link" href="?audience=nathan">Nathan Thomas</a>
    <a class="footer-briefing-link" href="?audience=greg">Greg</a>
    <a class="footer-briefing-link" href="?audience=mahesh">Mahesh</a>
  </div>
</footer>
```

The `current` class is applied to the link matching the active audience. The render
function should determine the active audience from the URL parameter and mark the
corresponding link accordingly.

---

## 14. Interaction States

### Links
| State    | Style                                          |
|----------|------------------------------------------------|
| Default  | color: var(--teal-dark); text-decoration: none  |
| Hover    | text-decoration: underline                      |
| Visited  | same as default (no purple)                     |
| Focus    | outline: 2px solid var(--teal); offset: 2px     |

### Header Nav Links
| State    | Style                                          |
|----------|------------------------------------------------|
| Default  | color: rgba(255,255,255,0.60); border: transparent |
| Hover    | color: white; border-bottom: 2px solid var(--teal) |

### Hero Card
| State    | Style                                          |
|----------|------------------------------------------------|
| Default  | box-shadow: var(--shadow-sm)                    |
| Hover    | box-shadow: var(--shadow)                       |

### Story Row
| State    | Style                                          |
|----------|------------------------------------------------|
| Default  | background: var(--white)                        |
| Hover    | background: var(--teal-pale) #EBF5FA            |

### Fresh Story Row (.is-fresh)
| State    | Style                                          |
|----------|------------------------------------------------|
| Default  | border-left: 3px solid var(--teal); bg: white   |
| Hover    | border-left: 3px solid var(--teal); bg: teal-pale|

### Footer Briefing Links
| State    | Style                                          |
|----------|------------------------------------------------|
| Default  | color: var(--teal-dark); no bg                  |
| Hover    | bg: var(--teal-pale)                            |
| Current  | color: var(--text-muted); pointer-events: none  |

### Focus Visible
```css
a:focus-visible,
button:focus-visible {
  outline: 2px solid var(--teal);
  outline-offset: 2px;
}
```

### Reduced Motion
```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    transition-duration: 0.01ms !important;
  }
  html { scroll-behavior: auto; }
}
```

---

## 15. Responsive Behavior

Primary target is desktop (1100px+ viewport).

```css
@media (max-width: 680px) {
  .unified-header-inner {
    flex-wrap: wrap;
    height: auto;
    padding: 8px 16px;
    gap: 4px;
  }

  .header-nav {
    width: 100%;
    overflow-x: auto;
  }

  .header-date {
    display: none;  /* Recovers space on mobile; date visible in footer */
  }

  .cover-block {
    grid-template-columns: 1fr;   /* Stack vertically */
  }

  .cover-right {
    border-left: none;
    border-top: 4px solid var(--oci-accent);
  }

  .hero-card {
    grid-template-columns: 1fr;   /* Stack vertically */
  }

  .hero-img {
    min-height: 120px;
    max-height: 160px;
  }

  .row-headline {
    -webkit-line-clamp: 3;        /* Allow 3 lines on narrow screens */
  }
}
```

---

## 16. Accessibility Notes

### Color Contrast (WCAG AA)
| Combination                                    | Ratio | Pass? |
|------------------------------------------------|-------|-------|
| Charcoal (#2C3E50) on white (#FFFFFF)          | 10.7  | Yes   |
| White on charcoal (#2C3E50)                    | 10.7  | Yes   |
| Text-mid (#555E68) on white                    | 6.4   | Yes   |
| OCI text (#7A5200) on OCI bg (#FFF8EE)         | 5.8   | Yes   |
| OCI label (#B8730C) on OCI bg (#FFF8EE)        | 3.8   | Yes*  |
| NEW badge (#2E7D32) on badge bg (#E8F5E9)      | 4.8   | Yes   |
| Text-muted (#95A5A6) on white                  | 2.8   | No    |
| White on charcoal header                       | 10.7  | Yes   |
| Nav links (60% white) on charcoal              | ~6.4  | Yes   |

*Passes for bold text >= 14px or any text >= 18px (AA Large).

Text-muted failing AA is acceptable for de-emphasized metadata (timestamps, story
counts) that supplements already-visible primary content. If strict compliance is
needed, darken to #6B7B8D (4.5:1 ratio).

### Semantic HTML Changes
- `<header class="unified-header">` wrapping the single header bar
- `<nav>` for section navigation within the header
- `<main>` wrapping page-wrap content
- `<section>` for each section-block (with aria-label)
- `<article>` for each hero-card and story-row
- `<footer>` for page-footer (now includes briefing switcher)
- Keep `<ul>`/`<li>` for executive summary bullets

### Keyboard Navigation
- All header nav links: standard `<a>` elements, inherently keyboard-accessible
- All story links: standard `<a>` elements, inherently keyboard-accessible
- Footer briefing links: standard `<a>` elements with current state disabled via
  pointer-events:none and aria-current="page"

### Screen Reader
- Add `aria-label="Executive Summary"` to .cover-block
- Add `aria-label="OCI Implication of the Day"` to .cover-right
- Each section-block: `aria-label="{section label}"`
- Hero images: keep `alt=""` (decorative picsum placeholders)
- NEW badge: `aria-label="Published within the last 6 hours"`
- Current briefing link in footer: `aria-current="page"`

---

## 17. ASCII Wireframes

### Full Page (Desktop, 1100px)

```
+============================================================+
| AI DAILY BRIEFING    Wed Mar 11, 2026   AI|COMP|FIN|DC|... |  <- header 40px
+===================[ 3px teal border ]=======================+
|                                                              |
|  +--[ EXECUTIVE SUMMARY (charcoal) ]--+--[ OCI IMPLICATION ]+
|  |                                    |  (amber/gold bg)     |
|  |  EXECUTIVE SUMMARY                 |                      |
|  |  (1) First bullet point...         | <> OCI IMPLICATION   |
|  |  (2) Second bullet point...        |    OF THE DAY        |
|  |  (3) Third bullet point...         |                      |
|  |  (4) Fourth bullet point...        | The key takeaway     |
|  |  (5) Fifth bullet point...         | for OCI today is     |
|  |                                    | that the competitive |
|  |                                    | landscape shifted... |
|  +------------------------------------+----------------------+
|                                                              |
|  --[ ARTIFICIAL INTELLIGENCE ]------------ 5 stories --      |
|                                                              |
|  +--------+------------------------------------------+       |
|  |  IMG   | [ai] [high] [NEW]                        |       |
|  | 180px  | Hero Headline in Serif Bold 15px         |       |
|  |        | Summary text 2-3 lines max, 11px...      |       |
|  |        | [OCI: amber bg implication line]          |       |
|  +--------+ Reuters . Mar 11, 09:30 . 3h ago --------+       |
|                                                              |
|  +--------------------------------------------------------+  |
|  ||| [o] TECHCRUNCH [NEW] [ai] [med]             Mar 11 | |
|  ||| Second Story Headline Can Now Wrap to Two       1h   | |
|  ||| Lines Without Being Truncated by Ellipsis            | |
|  |||   Summary text, single line clamp only...            | |
|  +--------------------------------------------------------+  |
|   ^-- 3px teal left border = fresh (<6h)                     |
|  +--------------------------------------------------------+  |
|  | [o] ARS TECHNICA [cloud]  Third Story Headline    Mar 10 | |
|  |   Summary text single line...                       14h  | |
|  +--------------------------------------------------------+  |
|   ^-- no left border = older story, no NEW badge             |
|                                                              |
|  --[ COMPETITIVE INTEL ]------------------ 4 stories --      |
|                                                              |
|  +--------+------------------------------------------+       |
|  |  IMG   | Hero card for this section               |       |
|  | 180px  | ...                                      |       |
|  +--------+------------------------------------------+       |
|  +--------------------------------------------------------+  |
|  | Compact story row 1                                    |  |
|  +--------------------------------------------------------+  |
|  | Compact story row 2                                    |  |
|  +--------------------------------------------------------+  |
|                                                              |
|  ... (more sections, same pattern) ...                       |
|                                                              |
|  ---------------------------------------------------------   |
|  Karan Batta . 2026-03-11 12:00 UTC . 12 stories . Claude   |
|  VIEW OTHER BRIEFINGS                                        |
|  [Karan Batta]  Nathan Thomas  Greg  Mahesh                  |
+============================================================+
```

### Executive Summary Detail (UNCHANGED from v2.1)

```
+=================================+=============================+
| bg: #2C3E50 (charcoal)         | bg: #FFF8EE (warm cream)    |
| text: white                     | left: 4px solid #D4880F     |
|                                 |                             |
| EXECUTIVE SUMMARY               |  <> OCI IMPLICATION         |
| (teal overline, 8.5px caps)    |     OF THE DAY              |
|                                 |  (gold label, 8px caps)     |
| (1) NVIDIA H200 Ultra GPU...  |                             |
| (2) Azure signs $2.1B deal... |  Oracle's competitive       |
| (3) GPT-5 launches on Azure.. |  position in the AI         |
| (4) AWS Graviton5 price cuts. |  infrastructure market is   |
| (5) Data center power crunch. |  strengthened by today's    |
|                                 |  $20B commitment, but      |
|                                 |  Azure's Aramco deal shows |
|                                 |  sovereign cloud pressure. |
+=================================+=============================+
```

### Hero Card Detail

```
+----------+---------------------------------------------------+
|          | [ai] [high] [NEW]                 <- meta pills    |
|  IMAGE   | NVIDIA H200 Ultra GPU Promises 2x  <- serif 15px  |
| 180x120  | Training Throughput for Enterprise  <- bold        |
| (picsum) | Summary: NVIDIA unveiled the H200 Ultra GPU...     |
|  [SRC]   | claiming 2x training throughput over H100...       |
|  badge   | +--amber bg----------------------------------+     |
|          | | OCI has not yet commented on availability  |     |
|          | +---------------------------------------------+     |
|          | ------------------------------------------------- |
|          | Reuters Tech . Mar 11, 09:30 . 3h ago              |
+----------+---------------------------------------------------+
```

### Story Row Detail (v2.2 -- Fresh Story)

```
+---+-------------------------------------------------------+--------+
| t | [o] TECHCRUNCH  [NEW]  [cloud]  [medium]              | Mar 11 |
| e | OpenAI Releases GPT-5 with Native Multimodal          |   1h   |
| a |   Reasoning That Outperforms Previous Models          |        |
| l | OpenAI released GPT-5, which it claims achieves...    |        |
+---+-------------------------------------------------------+--------+
 ^-- 3px teal left border (.is-fresh)
     Headlines: 2-line clamp (was 1-line ellipsis)
     Summary: 1-line clamp (was 2-line clamp)
     OCI implication: REMOVED from story rows
```

### Story Row Detail (v2.2 -- Older Story, No Badge)

```
+-----------------------------------------------------------+--------+
| [o] ARS TECHNICA  [cloud]  [high]                         | Mar 09 |
| Data Center Power Crisis Deepens as Utilities Warn        |  2d    |
|   of Grid Constraints Across Major US Markets             |        |
| Utility companies in Virginia and Texas issued warnings...|        |
+-----------------------------------------------------------+--------+
 ^-- no left border, no NEW badge
```

---

## 18. Implementation Checklist

Ordered by priority. Each item references the specific function or CSS block
in render.py that needs modification.

### HIGH PRIORITY (Header Collapse + Audience Tab Removal)

1. **Replace 4 header bars with unified header in _page_html():**
   - Remove `.topbar` HTML and CSS
   - Remove `.masthead` / `.masthead-inner` / `.masthead-overline` / `.masthead-tagline` /
     `.masthead-issue` / `.masthead-right` / `.masthead-center` HTML and CSS
   - Remove `.audience-bar` / `.audience-bar-inner` / `.audience-label` /
     `.audience-tab` HTML and CSS
   - Remove `.section-nav` / `.section-nav-inner` / `.sec-nav-link` HTML and CSS
   - Add `.unified-header` / `.unified-header-inner` / `.header-title` /
     `.header-date` / `.header-nav` / `.header-nav-link` HTML and CSS per Section 6

2. **Update audience switching mechanism:**
   - Remove `_render_audience_tabs()` function (or gut it)
   - Auto-select audience from URL parameter `?audience=karan`
   - Render only the selected audience's content (no hidden panels)
   - Add briefing switcher links to footer per Section 13

3. **Add OCI amber tokens to :root in BASE_CSS:**
   Add these four lines inside the :root block:
   ```css
   --oci-accent: #D4880F;
   --oci-bg: #FFF8EE;
   --oci-text: #7A5200;
   --oci-label: #B8730C;
   ```

4. **Add freshness tokens to :root in BASE_CSS:**
   ```css
   --new-badge-bg: #E8F5E9;
   --new-badge-text: #2E7D32;
   --new-border: var(--teal);
   ```

5. **Update .cover-right in BASE_CSS:**
   - Change `background` from `var(--teal-pale)` to `var(--oci-bg)`
   - Change `border-left` from `3px solid var(--teal)` to `4px solid var(--oci-accent)`

6. **Update _render_exec_summary() function:**
   - Remove the `<div class="cover-image-block"><img ...></div>` block entirely
   - Remove the `<div class="cover-headline">Today's Intelligence Briefing</div>` line
   - Replace the OCI box inner HTML with the oci-badge-strip pattern shown in Section 7
   - Remove the unused `seed` and `seed2` variables

### MEDIUM PRIORITY (OCI Scope Reduction + Story Row Changes)

7. **Remove OCI implication from story row template:**
   - In `_render_story_row()`, stop emitting the `.row-oci` div
   - Add `display: none` to `.row-oci` in CSS as safety net
   - OCI implications remain in exec summary and hero cards only

8. **Update .row-headline to 2-line clamp:**
   Replace:
   ```css
   white-space: nowrap;
   overflow: hidden;
   text-overflow: ellipsis;
   ```
   With:
   ```css
   display: -webkit-box;
   -webkit-line-clamp: 2;
   -webkit-box-orient: vertical;
   overflow: hidden;
   ```

9. **Update .row-summary to 1-line clamp:**
   Change `-webkit-line-clamp` from `2` to `1`.

10. **Add freshness detection and NEW badge:**
    - Add `is_fresh()` helper function per Section 12
    - In `_render_story_row()`: add `is-fresh` class to `.story-row` when fresh
    - In `_render_story_row()`: add `<span class="new-badge">NEW</span>` in meta row
    - In `_render_hero_card()`: add NEW badge to `.hero-meta` when fresh
    - Add `.story-row.is-fresh` and `.new-badge` CSS per Sections 11-12

11. **Update .hero-oci CSS:**
    - Change color from `var(--teal-dark)` to `var(--oci-text)`
    - Add `background: var(--oci-bg)`
    - Change border-left color from `var(--teal)` to `var(--oci-accent)`, width to 3px
    - Add padding (4px 8px) and border-radius: 2px

12. **Add new CSS rules to BASE_CSS:** .oci-badge-strip, .oci-badge-icon, .oci-callout-label

### LOW PRIORITY

13. **Add focus-visible and reduced-motion CSS** per Section 14

14. **Remove Google Fonts Lato link** from _page_html()

15. **Add semantic HTML wrappers** (header, nav, main, section, article, footer) in rendering functions

16. **Add ARIA attributes** (aria-label, aria-current) per Section 16

17. **Update responsive breakpoint CSS** per Section 15

### Vertical Space Budget (1080p, ~900px usable viewport)

| Component                  | v2.1 (px) | v2.2 (px) | Savings |
|----------------------------|-----------|-----------|---------|
| Top bar                    | 24        | 0         | 24      |
| Masthead                   | 52        | 0         | 52      |
| Audience tab bar           | 34        | 0         | 34      |
| Section nav bar            | 28        | 0         | 28      |
| Unified header bar         | 0         | 40        | -40     |
| **Header subtotal**        | **138**   | **40**    | **98**  |
| Page-wrap top padding      | 14        | 14        | 0       |
| Executive summary block    | ~135      | ~135      | 0       |
| Gap after exec summary     | 14        | 14        | 0       |
| Section 1 header           | 22        | 22        | 0       |
| Section 1 hero card        | 128       | 128       | 0       |
| Section 1 story rows (x3)  | 180*      | 156       | 24**    |
| Gap after section 1        | 14        | 14        | 0       |
| Section 2 header           | 22        | 22        | 0       |
| Section 2 hero card starts | 128       | 128       | 0       |
| **SUBTOTAL**               | **~795**  | **~673**  | **122** |

*v2.1 story rows assumed 1 of 3 rows had OCI implication (~70px + 55px + 55px = 180px)
**v2.2 story rows: no OCI, all ~52px each (52px x 3 = 156px)

On a 1080p monitor the user now sees the executive summary plus the entire first
section plus most of the second section without scrolling -- a significant improvement.
The 98px header savings alone means content starts at pixel 54 instead of pixel 152.

---

## Component Hierarchy (DOM Tree Reference)

```
<html>
  <body>
    <header class="unified-header">
      .unified-header-inner
        .header-title
          span (AI)
        .header-date
        nav.header-nav
          a.header-nav-link (xN)
    </header>
    <main>
      .page-wrap
        .cover-block
          .cover-left
            .cover-overline
            ul.cover-bullets
              li > .bullet-num + text (x3-5)
          .cover-right
            .oci-badge-strip
              .oci-badge-icon
              .oci-callout-label
            .oci-callout-text
        .section-block (xN)
          .section-header
            .section-label-bar
            .section-rule
            .section-count
          .hero-card
            .hero-img > img + .hero-img-badge
            .hero-body
              .hero-meta > .topic-pill + .conf-pill + .new-badge?
              .hero-headline > a
              .hero-summary
              .hero-oci (optional)
              .hero-footer
          .story-list
            article.story-row[.is-fresh?] (xN)
              .row-left
                .row-meta > .src-dot + .src-name + .new-badge? + .topic-pill + .conf-pill
                .row-headline > a
                .row-summary
              .row-right
        .divider
        footer.page-footer
          div (metadata line)
          .footer-briefings
            .footer-briefings-label
            a.footer-briefing-link[.current?] (xN)
    </main>
    <!-- No audience switching JS needed; server renders correct audience -->
  </body>
</html>
```

---

## Content and Copy Guidelines

### Executive Summary Bullets
- Each bullet: 1 sentence, max 120 characters
- Lead with the actor or subject: "NVIDIA announced...", "AWS plans..."
- Include a number or metric when possible
- No bullet should require clicking through to understand the news

### OCI Implication of the Day
- 2-4 sentences
- Always starts with a concrete strategic framing
- Must reference OCI by name at least once
- Must be actionable or directional, not just observational

### Hero Headline
- Max 80 characters
- Active voice
- Include the most important entity/actor
- Write like a newspaper headline (serif font gives it editorial weight)

### Story Row Headline
- Max 100 characters (was 70 in v2.1; 2-line clamp allows more text)
- Same editorial style as hero
- Do NOT artificially truncate in the data pipeline; let CSS line-clamp handle overflow

### Summaries
- Hero: 2-3 sentences, max 250 characters (3-line clamp enforced by CSS)
- Story row: 1 sentence, max 120 characters (1-line clamp enforced by CSS, was 2-line)
- Plain language, no marketing speak

### Per-Story OCI Implication (Hero Cards Only)
- 1 sentence, max 140 characters
- Specific and directional
- No text prefix needed -- the amber left-border is the visual indicator
- Only generated for the hero story of each section; not for story rows

---

*End of specification.*
