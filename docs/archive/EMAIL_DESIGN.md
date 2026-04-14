# OCI AI Daily Executive Briefing — Email UX & Design Specification

**Version:** 1.0
**Date:** 2026-03-10
**Audience:** Frontend engineers, content engineers, and the editorial pipeline team
**Purpose:** Complete design and UX specification for the AI-powered daily executive briefing delivered to OCI leadership. A frontend engineer must be able to implement the full email template from this document without additional design decisions.

---

## Table of Contents

1. [Design Principles](#1-design-principles)
2. [Email Layout Wireframe](#2-email-layout-wireframe-ascii)
3. [Visual Design System](#3-visual-design-system)
4. [Per-Audience Visual Differentiation](#4-per-audience-visual-differentiation)
5. [Story Card Anatomy (Detailed)](#5-story-card-anatomy-detailed)
6. [Executive Summary Section](#6-executive-summary-section)
7. [Section Navigation](#7-section-navigation)
8. [Mobile Responsiveness](#8-mobile-responsiveness)
9. [Subject Line & Preview Text Formula](#9-subject-line--preview-text-formula)
10. [Tone & Voice Guidelines Per Persona](#10-tone--voice-guidelines-per-persona)
11. [Tracked Link UX](#11-tracked-link-ux)
12. [Feedback Widget Design](#12-feedback-widget-design)
13. [HTML Email Implementation Notes](#13-html-email-implementation-notes)

---

## 1. Design Principles

### Core UX Principles for Executive Email Design

**1. Scannability First**
Executives spend 30–90 seconds on a newsletter before deciding whether to read deeper. Every design decision must support scanning before reading. This means: strong typographic hierarchy, consistent left-rail anchors (section labels, confidence tags), and a predictable grid. A recipient must be able to extract the five most important facts from this briefing without reading a single full sentence.

**2. Signal Density Without Clutter**
High density is appropriate for this audience — these are experienced executives who can process information quickly. However, density must be structured. Use whitespace to separate sections, not to pad empty space within them. The goal is maximum information per vertical inch, not maximum whitespace per card. A useful mental model: think Bloomberg Terminal, not Medium.com.

**3. Trust Signals Are Structural**
Source credibility, confidence tags, and recency timestamps are not optional decorations — they are load-bearing elements of the briefing's value proposition. Every story must show its source and its confidence level. The credibility tier badge (T1/T2/T3/T4) must always be visible without scrolling within the story card. Executives calibrate their response to information based on source quality; hiding this information destroys trust.

**4. Mobile-First Interaction, Desktop-First Layout**
These executives will read on iPhone (Apple Mail) during morning commutes or at the gym. The email must be fully functional on a 390px viewport. However, the canonical reading experience is designed for a 600px desktop email client. Interactions (feedback buttons, tracked links) must have minimum 44px tap targets on mobile.

**5. Zero Cognitive Tax on Navigation**
Section navigation anchors at the top of the email let a recipient jump directly to their highest-weighted section. For example, Karan Batta should be able to tap "Financial" and land instantly there. This is more valuable than any other UX feature because it respects time.

**6. Personalization Must Be Invisible but Felt**
The email should never announce "this is personalized for you." Instead, the content ordering, section prominence, and depth of summaries should feel self-evidently right. If Karan's version leads with Financial and Greg's version leads with Competitive, neither should need explanation.

**7. Feedback Must Be Frictionless**
Feedback buttons must be single-click image links — no redirects to forms, no JS required. The confirmation experience should be a lightweight redirect to a static thank-you page or a pre-populated mailto link. If it takes more than one tap, the feedback rate will be near zero.

**8. Consistent Structure Across Editions**
Executives form habits. The same sections appear in the same order every day (ordered by that recipient's weights). Changes to structure should be versioned and communicated. Structural unpredictability destroys the scannability of a recurring briefing.

---

### What NOT to Do: Anti-Patterns for Executive Email

| Anti-Pattern | Why It Fails for This Audience |
|---|---|
| Hero image banner with stock photo | Communicates "marketing email," triggers skip reflex |
| More than 3 typeface weights | Visual noise, suggests lack of editorial discipline |
| Sentence-level repetition across summary and OCI implication | Wastes executive time, signals low editorial quality |
| Long paragraphs (5+ sentences) | No executive reads walls of text in email |
| Untracked "Read more" links that go to full articles with no summary | No value added by the briefing; just an RSS reader |
| Confidence/source label hidden or in fine print | Destroys trust; executive cannot calibrate the information |
| Subject lines that are vague ("Your daily briefing") | No open incentive; low open rate |
| Emojis in subject lines for C-suite | Perceived as unprofessional for this audience |
| More than 2 colors of text in body | Creates visual confusion, not hierarchy |
| Centered body text | Hard to scan; always left-align body content |
| Social sharing buttons | Not relevant; this is a private intelligence briefing |
| "Sent by [ESP name]" footer branding | Undermines OCI brand ownership of the content |
| GIF animations | Distracting; not appropriate for executive context |
| Tables that break on mobile | Guaranteed to frustrate Apple Mail / Gmail mobile readers |
| More than 5 CTAs above the fold | Attention fragmentation |
| Missing preheader / preview text | Loses the second line of the subject-line pitch |

---

## 2. Email Layout Wireframe (ASCII)

The canonical email width is **600px**. The wireframe below represents the full email at desktop scale. Mobile behavior is covered in Section 8.

```
┌─────────────────────────────────────────────────────────────────────┐
│                         [PREHEADER TEXT]                            │
│         "Today: AWS doubles GPU cluster capacity, Azure..."         │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓  │   │
│  │  ▓                  HEADER BAND                            ▓  │   │
│  │  ▓  [OCI wordmark/logo — left]   [Edition No. · Date — right] ▓ │
│  │  ▓  OCI Intelligence Briefing    Ed. #147 · Tue Mar 10 2026 ▓  │   │
│  │  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓  │   │
│  │  Background: #0F1923 (deep navy)  Text: #FFFFFF             │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  SECTION NAV (anchor links bar)                              │   │
│  │  [Financial] [Power] [Compete] [AI/Models] [Deals]          │   │
│  │  [Community] [OCI Intel]   ← personalized order, weighted   │   │
│  │  Background: #1C2B3A  |  Pill-style links  |  14px          │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  ╔═══════════════════════════════════════════════════════╗   │   │
│  │  ║  EXECUTIVE SUMMARY                        [★ PRIORITY] ║   │   │
│  │  ║  "What matters today"                                 ║   │   │
│  │  ╠═══════════════════════════════════════════════════════╣   │   │
│  │  ║                                                       ║   │   │
│  │  ║  ● AWS committed $15B capex expansion — OCI           ║   │   │
│  │  ║    pricing pressure imminent in H2 2026               ║   │   │
│  │  ║                                                       ║   │   │
│  │  ║  ● Nvidia H200 allocation shortfall confirmed by      ║   │   │
│  │  ║    3 hyperscalers — OCI cluster lead may widen        ║   │   │
│  │  ║                                                       ║   │   │
│  │  ║  ● Google Cloud wins Spotify AI workload migration    ║   │   │
│  │  ║    — Deals team should track vertical pattern         ║   │   │
│  │  ║                                                       ║   │   │
│  │  ║  ● Meta releases Llama 4 — OSS pressure on            ║   │   │
│  │  ║    proprietary model pricing accelerates              ║   │   │
│  │  ║                                                       ║   │   │
│  │  ║  ┌───────────────────────────────────────────────┐   ║   │   │
│  │  ║  │  ◆ OCI IMPLICATION OF THE DAY                │   ║   │   │
│  │  ║  │  AWS capex surge + Nvidia shortage = window   │   ║   │   │
│  │  ║  │  for OCI to lock in GPU reservation deals     │   ║   │   │
│  │  ║  │  before supply normalizes in Q3.              │   ║   │   │
│  │  ║  └───────────────────────────────────────────────┘   ║   │   │
│  │  ╚═══════════════════════════════════════════════════════╝   │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ── SECTION DIVIDER ─────────────────────────────────────────────  │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  SECTION HEADER                                              │   │
│  │  [📊] MARKET & FINANCIAL ANALYSIS          5 stories ›      │   │
│  │  ▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔  │   │
│  │                                                              │   │
│  │  ┌───────────────────────────────────────────────────────┐  │   │
│  │  │  STORY CARD (standard)                                │  │   │
│  │  │                                                       │  │   │
│  │  │  [CONFIRMED]  Via Reuters · 2h ago                    │  │   │
│  │  │                                                       │  │   │
│  │  │  AWS Plans $15B Data Center Expansion,                │  │   │
│  │  │  Accelerating Global GPU Cluster Buildout             │  │   │
│  │  │                                                       │  │   │
│  │  │  Amazon Web Services announced a $15 billion capital  │  │   │
│  │  │  commitment to expand its global data center          │  │   │
│  │  │  footprint through 2027, with 40% allocated to new    │  │   │
│  │  │  GPU-dense AI clusters. The company cited record      │  │   │
│  │  │  enterprise AI demand as the primary driver.          │  │   │
│  │  │                                                       │  │   │
│  │  │  ┌─────────────────────────────────────────────────┐ │  │   │
│  │  │  │ ▶ OCI: Pricing pressure on on-demand GPU        │ │  │   │
│  │  │  │   compute likely by Q4 2026. Reserved capacity   │ │  │   │
│  │  │  │   contracts should be prioritized now.           │ │  │   │
│  │  │  └─────────────────────────────────────────────────┘ │  │   │
│  │  │                                                       │  │   │
│  │  │  [Read full story →]                                  │  │   │
│  │  │                                                       │  │   │
│  │  │  [👍 Useful] [👎 Not useful] [➕ More] [🚫 Less]      │  │   │
│  │  └───────────────────────────────────────────────────────┘  │   │
│  │                                                              │   │
│  │  ┌───────────────────────────────────────────────────────┐  │   │
│  │  │  STORY CARD (follow-up variant)                       │  │   │
│  │  │                                                       │  │   │
│  │  │  [↻ FOLLOW-UP]  Via Bloomberg · 5h ago               │  │   │
│  │  │                                                       │  │   │
│  │  │  UPDATE: Azure GPU Reservation Backlog Now 6 Months   │  │   │
│  │  │  (Previously reported: 4-month wait, Mar 5)           │  │   │
│  │  │                                                       │  │   │
│  │  │  New detail: wait time has grown from 4 to 6 months   │  │   │
│  │  │  following Microsoft's internal reallocation to       │  │   │
│  │  │  Copilot+ enterprise deployments.                     │  │   │
│  │  │                                                       │  │   │
│  │  │  ┌─────────────────────────────────────────────────┐ │  │   │
│  │  │  │ ▶ OCI: Opportunity to capture Azure overflow.   │ │  │   │
│  │  │  └─────────────────────────────────────────────────┘ │  │   │
│  │  │                                                       │  │   │
│  │  │  [Read update →]                                      │  │   │
│  │  │  [👍] [👎] [➕] [🚫]                                  │  │   │
│  │  └───────────────────────────────────────────────────────┘  │   │
│  │                                                              │   │
│  │  ┌───────────────────────────────────────────────────────┐  │   │
│  │  │  STORY CARD (watch item variant)                      │  │   │
│  │  │                                                       │  │   │
│  │  │  [◉ WATCH]  Via WSJ · 1d ago                         │  │   │
│  │  │                                                       │  │   │
│  │  │  Analysts Flag Margin Compression Risk in Cloud       │  │   │
│  │  │  Infra as Power Costs Rise                            │  │   │
│  │  │                                                       │  │   │
│  │  │  Weak signal: No public commitments yet, but three    │  │   │
│  │  │  sell-side notes this week have flagged energy cost   │  │   │
│  │  │  trajectory as an emerging margin risk for H2.        │  │   │
│  │  │                                                       │  │   │
│  │  │  ┌─────────────────────────────────────────────────┐ │  │   │
│  │  │  │ ▶ OCI: Monitor OCI energy contract renewals     │ │  │   │
│  │  │  │   before lock-in decisions.                     │ │  │   │
│  │  │  └─────────────────────────────────────────────────┘ │  │   │
│  │  │                                                       │  │   │
│  │  │  [Read analysis →]   [👍] [👎] [➕] [🚫]              │  │   │
│  │  └───────────────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  [Sections 3–8 follow the same pattern, ordered by audience weight] │
│                                                                      │
│  ── SECTION DIVIDER ─────────────────────────────────────────────  │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  FOOTER                                                      │   │
│  │                                                              │   │
│  │  OCI Intelligence Briefing · Edition #147 · March 10, 2026  │   │
│  │  Personalized for: [Recipient Name]                          │   │
│  │                                                              │   │
│  │  [View in browser] · [Archive] · [Manage preferences]        │   │
│  │  [Unsubscribe]                                               │   │
│  │                                                              │   │
│  │  How was today's briefing?                                   │   │
│  │  [★★★★★ Rate this edition]                                   │   │
│  │                                                              │   │
│  │  Oracle Cloud Infrastructure · 500 Oracle Pkwy, Redwood City │   │
│  │  This briefing is confidential and intended only for         │   │
│  │  [Recipient Name].                                           │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Visual Design System

### 3.1 Color Palette

The palette is designed around a **deep navy primary** with an **OCI red accent**, reflecting Oracle's brand identity while feeling more like a premium intelligence product than a marketing email. It must function in both light-mode email clients (Gmail web) and dark-mode clients (Apple Mail dark mode).

#### Base Palette (Light Mode)

| Role | Name | Hex | Usage |
|---|---|---|---|
| Primary brand | OCI Navy | `#0F1923` | Header band, section header backgrounds |
| Accent | OCI Red | `#C74634` | Accent borders, confidence tags (confirmed), CTA buttons |
| Accent secondary | OCI Blue | `#1A6FA8` | Links, interactive elements, OCI implication callout border |
| Background | Off-White | `#F7F8FA` | Email body background |
| Card background | Pure White | `#FFFFFF` | Story card background |
| Text primary | Charcoal | `#1A1A2E` | Headlines, body text |
| Text secondary | Slate | `#4A5568` | Summary body, source label |
| Text muted | Cool Gray | `#8896A5` | Timestamps, captions, minor metadata |
| Border | Light Gray | `#E2E8F0` | Card borders, section dividers |
| Section header bg | Deep Navy | `#0F1923` | Section header bar background |
| Executive Summary bg | Dark Navy | `#162232` | Executive summary section background |
| OCI Implication bg | Blue Tint | `#EBF4FB` | OCI implication callout box fill |
| Watch item border | Amber | `#D97706` | Left-border accent on watch item cards |
| Follow-up border | Teal | `#0D9488` | Left-border accent on follow-up cards |
| Tag: Confirmed | Green | `#059669` | Confirmed confidence tag background |
| Tag: Credible report | Blue | `#1A6FA8` | Credible report tag background |
| Tag: Weak signal | Amber | `#D97706` | Weak signal tag background |
| Tag: Follow-up | Teal | `#0D9488` | Follow-up tag background |
| Tag text | White | `#FFFFFF` | Text on all confidence tags |

#### Dark Mode Overrides (via `@media (prefers-color-scheme: dark)`)

| Role | Light Hex | Dark Mode Hex |
|---|---|---|
| Email background | `#F7F8FA` | `#0D1117` |
| Card background | `#FFFFFF` | `#161B22` |
| Text primary | `#1A1A2E` | `#E6EDF3` |
| Text secondary | `#4A5568` | `#8B949E` |
| Text muted | `#8896A5` | `#656D76` |
| Border | `#E2E8F0` | `#30363D` |
| OCI Implication bg | `#EBF4FB` | `#0D2137` |

---

### 3.2 Typography

#### Font Stack

```css
/* Headlines */
font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;

/* Body and metadata */
font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;

/* Monospace (financial data, numbers) */
font-family: 'SF Mono', 'Courier New', Courier, monospace;
```

All fonts are web-safe system stacks. Do not use Google Fonts or custom font imports — email client support is inconsistent and adds load weight.

#### Type Scale

| Element | Size | Weight | Color | Line Height |
|---|---|---|---|---|
| Email title (header wordmark) | 20px | 700 (Bold) | `#FFFFFF` | 1.2 |
| Edition/date label | 12px | 400 (Regular) | `#8896A5` | 1.4 |
| Section header title | 13px | 700 (Bold) | `#FFFFFF` | 1.3 |
| Section item count | 12px | 400 (Regular) | `#8896A5` | 1.3 |
| Story headline | 17px | 600 (Semibold) | `#1A1A2E` | 1.35 |
| Story summary | 14px | 400 (Regular) | `#4A5568` | 1.6 |
| Source label | 12px | 500 (Medium) | `#8896A5` | 1.4 |
| Confidence tag text | 10px | 700 (Bold) | `#FFFFFF` | 1.0 |
| OCI Implication body | 14px | 400 (Regular) | `#1A6FA8` | 1.55 |
| OCI Implication label | 11px | 700 (Bold) | `#1A6FA8` | 1.0 |
| Exec Summary bullet | 15px | 400 (Regular) | `#E6EDF3` | 1.55 |
| Exec Summary OCI callout | 14px | 500 (Medium) | `#FFFFFF` | 1.5 |
| Navigation link | 12px | 500 (Medium) | `#A8C8E8` | 1.0 |
| CTA link text | 13px | 600 (Semibold) | `#C74634` | 1.0 |
| Footer text | 11px | 400 (Regular) | `#8896A5` | 1.5 |
| Financial data (monospace) | 14px | 500 (Medium) | `#1A1A2E` | 1.4 |

#### Font Weight Guide

- **700 Bold**: Section headers, confidence tags, navigation labels, wordmark
- **600 Semibold**: Story headlines, CTA links, OCI implication label
- **500 Medium**: Source labels, navigation pills, financial figures
- **400 Regular**: Body summaries, footer text, metadata

---

### 3.3 Spacing System

**Base unit: 8px**

All spacing values are multiples of the base unit.

| Context | Value | Pixels |
|---|---|---|
| Base unit | 1u | 8px |
| Email outer padding (desktop) | 0 auto; max-width 600px | — |
| Email body side padding | 2u | 16px |
| Section outer padding (top/bottom) | 3u | 24px |
| Section header padding (top/bottom) | 1.5u | 12px |
| Section header padding (left/right) | 2u | 16px |
| Story card padding (all sides) | 2u | 16px |
| Story card margin-bottom | 1.5u | 12px |
| Story card border-radius | 1u | 8px |
| Story card border-left width (watch/follow-up) | 4px | 4px |
| Confidence tag padding (v/h) | 0.5u / 1u | 4px / 8px |
| Confidence tag border-radius | 3px | 3px |
| OCI Implication box padding | 1.5u | 12px |
| OCI Implication border-left width | 3px | 3px |
| Feedback button row margin-top | 1.5u | 12px |
| Feedback button padding (v/h) | 0.75u / 1.5u | 6px / 12px |
| Between headline and summary | 1u | 8px |
| Between summary and OCI callout | 1.5u | 12px |
| Between OCI callout and CTA link | 1u | 8px |
| Between CTA link and feedback row | 1u | 8px |
| Section divider height | 1px | 1px |
| Section divider margin (top/bottom) | 3u | 24px |
| Executive Summary bullet spacing | 1.5u | 12px |
| Nav pill padding (v/h) | 0.75u / 1.5u | 6px / 12px |
| Nav pill gap between pills | 1u | 8px |
| Footer padding (top/bottom) | 4u | 32px |

---

### 3.4 Component Library

#### Component 1: Section Header

Visual treatment: Full-width dark navy bar with a left-aligned section icon (emoji or inline SVG — use emoji for email compatibility), section title in white bold, and a right-aligned item count in muted text followed by a chevron (›).

```
┌────────────────────────────────────────────────────────────────┐
│ Background: #0F1923 | Padding: 12px 16px | Border-radius: 0   │
│                                                                │
│  📊  MARKET & FINANCIAL ANALYSIS              5 stories ›      │
│  ↑    ↑ 13px, 700, #FFFFFF                   ↑ 12px, #8896A5  │
│  16px emoji                                                    │
└────────────────────────────────────────────────────────────────┘
```

- Icon: 16px emoji, rendered as text (not image), with 8px right margin
- Title: 13px, 700, `#FFFFFF`, all-caps, letter-spacing: 0.08em
- Item count: 12px, 400, `#8896A5`, right-aligned
- Background: `#0F1923`
- No border-radius (full width, flush with card edges)

Section icons by section:
- Executive Summary: ★
- Market & Financial: 📊
- Power & Datacenter: ⚡
- Competitive: ⚔
- AI Platform & Models: 🤖
- Deals: 🤝
- Community Signal: 💬
- OCI Implications: 🔵

---

#### Component 2: Story Card — Standard Variant

- Background: `#FFFFFF`
- Border: 1px solid `#E2E8F0`
- Border-radius: 8px
- Padding: 16px
- Box-shadow: 0 1px 3px rgba(0,0,0,0.06)
- Margin-bottom: 12px
- No colored left border (distinguishes from watch/follow-up variants)

Structure from top to bottom:
1. Meta row: [confidence tag] [source label · timestamp]
2. Headline (17px, 600, `#1A1A2E`)
3. Summary (14px, 400, `#4A5568`, max 4 lines, line-clamp: 4)
4. OCI Implication box
5. CTA link
6. Feedback button row

---

#### Component 3: Story Card — Follow-Up Variant

- All standard card styles apply
- **Left border**: 4px solid `#0D9488` (Teal)
- **Background tint**: `#F0FDFA` (very light teal) — subtle, not strong
- Confidence tag: `[↻ FOLLOW-UP]` in teal
- Below headline, a parenthetical in 12px muted text: `(Previously reported: [date])`
- Summary focuses on the delta — what is new, not full re-summary

---

#### Component 4: Story Card — Watch Item Variant

- All standard card styles apply
- **Left border**: 4px solid `#D97706` (Amber)
- **Background tint**: `#FFFBEB` (very light amber)
- Confidence tag: `[◉ WATCH]` in amber
- Summary includes explicit "weak signal" framing in first sentence
- OCI Implication box has amber border-left instead of blue

---

#### Component 5: Executive Summary Bullet Item

- Container background: `#162232` (dark navy)
- Bullet character: `●` in `#C74634` (OCI Red), 16px
- Text: 15px, 400, `#E6EDF3`, line-height 1.55
- Bullet + text on same line; text wraps under text, not under bullet (use `padding-left: 20px; text-indent: -20px` on the `<td>`)
- Each bullet separated by 12px margin-bottom
- No numbered list — bullets only
- Maximum 5 bullets

---

#### Component 6: OCI Implication of the Day (Executive Summary)

This is a distinct sub-component within the Executive Summary.

- Background: `#0F1923`
- Border: 1px solid `#1A6FA8`
- Border-left: 4px solid `#C74634` (OCI Red)
- Border-radius: 6px
- Padding: 12px 16px
- Label: `◆ OCI IMPLICATION OF THE DAY` in 11px, 700, `#C74634`, letter-spacing: 0.1em
- Body: 14px, 500, `#FFFFFF`, line-height 1.5
- Margin-top: 20px (separated from bullet list)

---

#### Component 7: OCI Implication Callout Box (Story-Level)

- Background: `#EBF4FB`
- Border-left: 3px solid `#1A6FA8`
- Border-radius: 0 4px 4px 0
- Padding: 12px
- Label: `▶ OCI:` in 11px, 700, `#1A6FA8`
- Body: 14px, 400, `#1A6FA8`, line-height 1.55
- Dark mode: Background `#0D2137`, text `#A8C8E8`

---

#### Component 8: Source Credibility Badge

The badge appears as part of the source label row, to the right of the source name.

| Tier | Label | Color | When |
|---|---|---|---|
| T1 | `[T1]` | `#059669` (Green) | Press release, earnings, SEC, official blog |
| T2 | `[T2]` | `#1A6FA8` (Blue) | Reuters, Bloomberg, WSJ, FT, The Information |
| T3 | `[T3]` | `#D97706` (Amber) | CloudWars, The Register, Data Center Dynamics |
| T4 | `[T4]` | `#8896A5` (Gray) | HN, Reddit, GitHub, LinkedIn |

Badge styling: 9px, 700, white text on colored background, 2px 4px padding, 2px border-radius, displayed inline after source name.

Example rendering: `Via Reuters [T2] · 2h ago`

---

#### Component 9: Confidence Tag

Displayed as the first element in the meta row, before the source label.

| State | Label | Background | Icon |
|---|---|---|---|
| Confirmed | `CONFIRMED` | `#059669` | — |
| Credible report | `CREDIBLE` | `#1A6FA8` | — |
| Weak signal | `WEAK SIGNAL` | `#D97706` | — |
| Follow-up | `FOLLOW-UP` | `#0D9488` | ↻ |
| Watch item | `WATCH` | `#D97706` | ◉ |

Styling: 10px, 700, `#FFFFFF`, padding: 3px 7px, border-radius: 3px, letter-spacing: 0.06em, displayed as inline-block. Right margin: 8px.

---

#### Component 10: Feedback Micro-Interaction Buttons

Implemented as image links (see Section 12 for full spec). Visual appearance:

- Four buttons in a horizontal row below CTA link
- Separated by 8px gaps
- Each button: 32px height, auto width, with text label
- Font: 12px, 400, `#8896A5`
- Border: 1px solid `#E2E8F0`
- Border-radius: 16px (pill shape)
- Background: `#F7F8FA`
- Padding: 6px 12px
- Hover state (for web archive version only): background `#E2E8F0`

Button labels and icons:
1. `👍 Useful`
2. `👎 Not useful`
3. `➕ More like this`
4. `🚫 Less like this`

In email HTML, these are rendered as plain `<a>` links styled to look like pills (no JS, no image requirement for the pill itself — use inline CSS).

---

#### Component 11: Section Divider

- Full-width horizontal rule
- Height: 1px
- Background: `#E2E8F0`
- Margin: 24px 0
- In dark mode: `#30363D`

---

#### Component 12: Footer

- Background: `#0F1923`
- Padding: 32px 24px
- All text: 11px, 400, `#8896A5`
- Links: 11px, 400, `#A8C8E8`, no underline
- Link separator: ` · ` (centered dot)
- Edition info centered
- "Confidential" disclaimer in italic

---

## 4. Per-Audience Visual Differentiation

The same canonical story bundle is rendered differently per executive using persona-specific parameters injected at render time. The underlying HTML template is the same; CSS classes and conditional blocks handle differentiation.

### 4.1 Karan Batta — SVP, Product Management

**Profile weight:** Financial 35%, Compete/Infra 25%, Datacenter/Power 15%, AI Platform 15%, Deals 10%
**Tone:** Concise, high-signal, strategic, implication-heavy

**Visual choices:**
- **Section order:** Financial leads, then Compete, then Datacenter/Power, then AI Platform, then Deals. Community Signal section is omitted or collapsed to 1 item.
- **Density:** Tighter. Summary is line-clamped to **2 lines** (not 4). A "Expand" link in 12px muted text follows clamped summaries.
- **Financial data highlighting:** Numbers and financial figures in the summary are rendered in **monospace font** (`'SF Mono'`, 14px, 500) and colored `#1A1A2E` (primary text, not muted). Dollar amounts, percentages, and basis points are bolded inline.
- **Story count per section:** Maximum 3 stories per section. High density, fewer items, higher signal threshold.
- **OCI Implication:** Always shown, full weight. This persona receives the most explicit strategic framing.
- **Section nav:** Financial section pill appears first, visually highlighted with a subtle red underline.
- **Executive Summary bullets:** Maximum 4 bullets (not 5), phrased with financial implication first ("$X impact on OCI..." pattern).
- **Speculative analysis:** Off. Only confirmed or credible report items shown by default.
- **Card border accent:** No watch items shown from Tier 4 sources.

---

### 4.2 Nathan Thomas — SVP, Product Management (Multicloud/Ecosystem)

**Profile weight:** Multi-cloud 30%, AI Platform 25%, Deals 25%, Compete partnerships 10%, Financial 10%
**Tone:** Ecosystem-oriented, partner-aware, customer-facing implications

**Visual choices:**
- **Section order:** AI Platform leads, then Deals, then Competitive (filtered to Partnerships and Multi-cloud subsection only), then Financial (condensed to 1–2 items).
- **Partner logos:** If a story involves a named partner (Google, Microsoft, Snowflake, Databricks, etc.), the partner name is rendered in **bold** within the source label area — e.g., `Microsoft · Via Bloomberg [T2] · 3h ago`. This makes partner signals visually scannable.
- **Multi-cloud section prominence:** The Competitive section is filtered to show multi-cloud and partnership stories first. Stories about infra pricing or raw GPU specs are deprioritized.
- **Deal cards:** Show "customer vertical" metadata below the source label in 11px muted text — e.g., `Vertical: Financial Services · Region: EMEA`.
- **Story count per section:** Maximum 4 stories per section in AI/Deals sections; 2 stories in Financial.
- **OCI Implication phrasing:** Customer-facing and partner-channel language. "What does this mean for OCI's go-to-market?" framing.
- **Community Signal:** Included if the signal relates to developer sentiment about a competing platform or a partner ecosystem (HN and GitHub only).
- **Summary length:** 3–4 sentences standard (not clamped as aggressively as Karan).
- **Watch items:** Shown for deal pipeline signals and partnership risk signals.

---

### 4.3 Greg Pavlik — EVP, Data/AI

**Profile weight:** Compete 35%, AI Platform & Models 35%, OSS/Innovation 15%, Partnerships 10%, Community Signal 5%
**Tone:** Technical but executive — capability gaps and strategic opportunities

**Visual choices:**
- **Section order:** AI Platform & Models leads (largest section, up to 5 stories), then Competitive (filtered to product and model announcements), then Community Signal (OSS/GitHub only), then Deals (AI-related only).
- **Technical depth visible:** Summary line-clamp is set to **4 lines** (full). No truncation. Greg reads deeper.
- **OSS Section prominence:** A dedicated "OSS & Tooling" subsection appears within the AI Platform section, visually separated by a thin teal rule and a `[OSS]` badge.
- **Model launch cards:** When a story covers a model release (Llama, GPT, Gemini, etc.), the card receives a special `[MODEL LAUNCH]` badge in purple (`#7C3AED`) in the confidence tag position, alongside the actual confidence tag.
- **GitHub trending items:** Community Signal cards from GitHub trending show the repo name in monospace, the star velocity in parentheses — e.g., `▲ 1,240 stars/day`.
- **Technical metadata row:** Beneath the summary, a thin metadata row in 11px monospace shows structured facts extracted by the pipeline — e.g., `Context window: 1M tokens · Params: 70B · License: Apache 2.0`.
- **Competitive cards:** Show a "capability gap" framing in OCI Implication — e.g., "OCI does not yet offer X. Estimated time to parity: [assessment]."
- **Speculative analysis:** Enabled. Weak signals shown with appropriate confidence tags.
- **Community Signal:** Included for HN and GitHub. Reddit included only if score threshold is high.

---

### 4.4 Mahesh — EVP, Security & Developer Platform

**Profile weight:** Datacenter 25%, Power 20%, Deals 20%, AI Platform 20%, Security/Platform 15%
**Tone:** Platform, resilience, secure operations, scale readiness

**Visual choices:**
- **Section order:** Datacenter/Power leads (combined into a single "Infrastructure Readiness" section header for this audience), then AI Platform (filtered to infrastructure and deployment stories), then Deals (filtered to platform/security deals), then Security Callouts.
- **Security callouts:** Any story touching security, compliance, or developer platform gets a `[SECURITY]` badge in red (`#C74634`) alongside the confidence tag. These stories are sorted to the top of their respective sections.
- **Infrastructure prominence:** Datacenter and Power stories show an additional metadata row beneath the source label: `Region: [extracted region] · Capacity: [MW if available] · Status: [online/planned/delayed]`. Rendered in 11px monospace, `#8896A5`.
- **Platform/resilience OCI Implication framing:** OCI Implication is always phrased in terms of operational readiness, SLA posture, or security compliance. "What does this mean for OCI's platform reliability?" framing.
- **Story cards:** Border-left on infra stories uses a steel blue accent (`#4682B4`) instead of default.
- **Watch items:** Emphasized. Mahesh receives more watch items than other personas — operational risks need early visibility.
- **Community Signal:** Included only for developer sentiment (Stack Overflow, HN programming discussions). GitHub trending included for security/DevSecOps tools.
- **Summary length:** 3–4 sentences, focused on operational and platform implications.
- **Financial data:** Minimal. Financial section shows only 1 story (if highly relevant to capex/infrastructure).

---

## 5. Story Card Anatomy (Detailed)

This section specifies every element of a single story card at the pixel level.

```
┌──────────────────────────────────────────────────────────────────┐
│ Card container                                                   │
│ background: #FFFFFF; border: 1px solid #E2E8F0;                 │
│ border-radius: 8px; padding: 16px; margin-bottom: 12px;         │
│                                                                  │
│ ┌──────────────────────────────────────────────────────────┐    │
│ │ META ROW                                                 │    │
│ │                                                          │    │
│ │ [CONFIRMED]          Via Reuters [T2] · 2h ago           │    │
│ │  ↑                    ↑                  ↑               │    │
│ │  Confidence tag       Source name +      Timestamp       │    │
│ │  10px, 700, white     tier badge         12px, #8896A5   │    │
│ │  on #059669           12px, 500, #8896A5                 │    │
│ │  padding: 3px 7px     Tier badge: 9px,                   │    │
│ │  border-radius: 3px   white on tier color                │    │
│ │  margin-right: 8px    margin-left: 4px                   │    │
│ └──────────────────────────────────────────────────────────┘    │
│                                                                  │
│ Margin-bottom: 8px                                               │
│                                                                  │
│ ┌──────────────────────────────────────────────────────────┐    │
│ │ HEADLINE                                                 │    │
│ │                                                          │    │
│ │ AWS Plans $15B Data Center Expansion, Accelerating       │    │
│ │ Global GPU Cluster Buildout                              │    │
│ │                                                          │    │
│ │ 17px, font-weight: 600, color: #1A1A2E                   │    │
│ │ line-height: 1.35                                        │    │
│ │ max 2 lines on display; overflow: hidden                 │    │
│ │ -webkit-line-clamp: 2; display: -webkit-box             │    │
│ │ -webkit-box-orient: vertical                             │    │
│ │ Max characters: 90 chars; truncate with ellipsis (…)    │    │
│ └──────────────────────────────────────────────────────────┘    │
│                                                                  │
│ Margin-bottom: 8px                                               │
│                                                                  │
│ ┌──────────────────────────────────────────────────────────┐    │
│ │ SUMMARY                                                  │    │
│ │                                                          │    │
│ │ Amazon Web Services announced a $15 billion capital      │    │
│ │ commitment to expand its global data center footprint    │    │
│ │ through 2027, with 40% allocated to GPU-dense AI         │    │
│ │ clusters. The company cited record enterprise AI demand  │    │
│ │ as the primary driver, with CFO comments suggesting...   │    │
│ │                                                          │    │
│ │ 14px, 400, color: #4A5568, line-height: 1.6             │    │
│ │ Default: -webkit-line-clamp: 4 (Karan: 2, Greg: none)   │    │
│ │ 2–4 sentences generated by LLM per persona max-length   │    │
│ │ After clamp: [show more] link in 12px #C74634            │    │
│ └──────────────────────────────────────────────────────────┘    │
│                                                                  │
│ Margin-bottom: 12px                                              │
│                                                                  │
│ ┌──────────────────────────────────────────────────────────┐    │
│ │ OCI IMPLICATION CALLOUT                                  │    │
│ │                                                          │    │
│ │ background: #EBF4FB; border-left: 3px solid #1A6FA8;    │    │
│ │ border-radius: 0 4px 4px 0; padding: 12px;              │    │
│ │                                                          │    │
│ │ ▶ OCI:  Pricing pressure on on-demand GPU compute        │    │
│ │  ↑       likely by Q4 2026. Reserved capacity           │    │
│ │  11px,   contracts should be prioritized now.            │    │
│ │  700,                                                    │    │
│ │  #1A6FA8 14px, 400, #1A6FA8, line-height: 1.55         │    │
│ │                                                          │    │
│ └──────────────────────────────────────────────────────────┘    │
│                                                                  │
│ Margin-bottom: 8px                                               │
│                                                                  │
│ ┌──────────────────────────────────────────────────────────┐    │
│ │ CTA LINK ROW                                             │    │
│ │                                                          │    │
│ │ [Read full story →]                                      │    │
│ │  ↑                                                       │    │
│ │  13px, 600, #C74634, no underline by default            │    │
│ │  text-decoration: underline on hover (web archive only)  │    │
│ │  Tracked via redirect: briefing.oci.oracle.com/r/...     │    │
│ │  Clean display URL; actual URL is opaque redirect        │    │
│ │  Padding: 0 (inline text link, not a button here)       │    │
│ │                                                          │    │
│ │  For high-priority stories: styled as pill button        │    │
│ │  background: #C74634, color: #FFFFFF, padding: 8px 16px │    │
│ │  border-radius: 4px, font: 13px 600                     │    │
│ └──────────────────────────────────────────────────────────┘    │
│                                                                  │
│ Margin-bottom: 0                                                 │
│                                                                  │
│ ┌──────────────────────────────────────────────────────────┐    │
│ │ FEEDBACK ROW                                             │    │
│ │                                                          │    │
│ │ margin-top: 12px; border-top: 1px solid #E2E8F0;        │    │
│ │ padding-top: 10px;                                       │    │
│ │                                                          │    │
│ │ [👍 Useful] [👎 Not useful] [➕ More] [🚫 Less]          │    │
│ │                                                          │    │
│ │ Each button: <a> tag styled as pill                      │    │
│ │ 12px, 400, #8896A5; border: 1px solid #E2E8F0           │    │
│ │ border-radius: 16px; padding: 6px 12px                  │    │
│ │ margin-right: 8px; display: inline-block                │    │
│ │ background: #F7F8FA                                     │    │
│ │ Min tap target on mobile: 44px height (use padding)     │    │
│ │ Each links to unique tracking URL encoding:             │    │
│ │   recipient_id, story_id, date, feedback_type           │    │
│ └──────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────┘
```

### Follow-Up Variant Differences

- `border-left: 4px solid #0D9488` on the outer card container
- `background: #F0FDFA` on card container
- Confidence tag shows `[↻ FOLLOW-UP]` with teal background
- Below headline, on its own line: `Previously reported [date] · New: [one-line delta description]` — 12px, italic, `#8896A5`
- Summary paragraph focuses only on what is new, not the full context
- CTA link text changes to `Read update →`

### Watch Item Variant Differences

- `border-left: 4px solid #D97706` on the outer card container
- `background: #FFFBEB` on card container
- Confidence tag shows `[◉ WATCH]` with amber background
- OCI Implication callout: `border-left: 3px solid #D97706` (amber instead of blue)
- Summary first sentence explicitly signals signal strength: "Early indicators suggest..." or "Multiple sell-side sources note..."

---

## 6. Executive Summary Section

### Visual Treatment Spec

The Executive Summary is always the first content section, appearing immediately below the section navigation bar. It must be above the fold on a 600px desktop viewport (approximately the top 500–600px of email body).

```
Container:
  background: #162232 (dark navy, distinct from both body and header)
  border: 1px solid #1A6FA8 (blue border to signal special status)
  border-radius: 8px
  padding: 24px
  margin-bottom: 24px
```

**Section label treatment (not a standard section header bar):**
```
★ EXECUTIVE SUMMARY — WHAT MATTERS TODAY
Font: 11px, 700, #C74634, letter-spacing: 0.12em, all-caps
Margin-bottom: 16px
```

**Bullet list:**
- 3–5 bullets (minimum 3, maximum 5)
- Bullet character: `●` in `#C74634`, 14px
- Text: 15px, 400, `#E6EDF3`, line-height 1.55
- Each bullet on a single `<tr>` with two `<td>`: one for the bullet, one for the text
- Bullet `<td>` width: 20px; text `<td>` width: remaining
- Spacing between bullets: 12px (margin-bottom on each row)
- Each bullet is self-contained: no multi-sentence paragraphs. Max 30 words per bullet.

**OCI Implication of the Day (sub-component):**
```
Placement: Always last element within Executive Summary, after bullet list
Margin-top: 20px
Background: #0F1923
Border: 1px solid #1A6FA8
Border-left: 4px solid #C74634
Border-radius: 6px
Padding: 14px 16px
```
Label: `◆ OCI IMPLICATION OF THE DAY` — 11px, 700, `#C74634`, letter-spacing: 0.1em
Body: 14px, 500, `#FFFFFF`, line-height 1.5
This text is distinct from any individual story's OCI Implication — it is synthesized across all stories by the editorial pipeline as the single most important cross-story insight for this recipient today.

**Visual weight signals:**
1. Dark navy background (contrasts sharply with off-white body and white cards below)
2. Red OCI accent on border and implication callout
3. Larger bullet text (15px vs 14px summary)
4. Blue border on container (authority signal)
5. Always first — no other section can appear above it

**Persona-specific adjustments:**
- Karan: 4 bullets max, first bullet always financial
- Nathan: 4 bullets, first two bullets about partnerships/deals/ecosystem
- Greg: 5 bullets allowed, technical model/capability angle leads
- Mahesh: 5 bullets allowed, infra/security angle leads; OCI Implication of the Day always phrased in operational terms

---

## 7. Section Navigation

### Anchor Link Bar

Placed immediately below the header band, above the Executive Summary. This is a full-width bar.

```
Container:
  background: #1C2B3A
  padding: 10px 16px
  border-bottom: 1px solid #0F1923

Content:
  Horizontally scrollable on mobile (overflow-x: auto)
  No-wrap (white-space: nowrap)
  Display as inline-block <a> pills
```

**Navigation pill styling:**
- 12px, 500, `#A8C8E8`
- Padding: 5px 12px
- Border: 1px solid `#2D4A5E`
- Border-radius: 12px
- Background: transparent (default)
- Margin-right: 8px
- No underline

**Active/relevant section indicator:**
The persona's top-weighted section has a visual heat treatment. The top-weighted section pill receives:
- Background: `rgba(199, 70, 52, 0.15)` (subtle red tint)
- Border: 1px solid `#C74634`
- Text: `#FFFFFF` (brighter)
- This is the only pill that is visually elevated; others are uniform.

**Section ordering in nav:**
Sections appear in the nav in the same order as they appear in the email body — which is ordered by descending weight for the recipient. The nav always shows all sections, even if some have 0 items (show grayed out with line-through text if section is empty for this edition).

**Example nav for each persona:**

Karan:
`[Financial ●] [Compete] [Power] [AI/Models] [Deals] [OCI Intel] [Community —]`

Nathan:
`[AI/Models ●] [Deals] [Compete] [Power] [Financial] [OCI Intel] [Community]`

Greg:
`[AI/Models ●] [Compete] [Community] [Deals] [OCI Intel] [Power] [Financial]`

Mahesh:
`[Power ●] [Datacenter] [AI/Models] [Deals] [OCI Intel] [Community] [Financial]`

The `●` dot appears on the recipient's #1 weighted section. The `—` dash indicates an empty section for this edition.

---

## 8. Mobile Responsiveness

### Single-Column Stack Behavior

The email is designed as a 600px single-column layout at all breakpoints. There are no multi-column layouts to collapse — the desktop layout is already single-column. On viewports under 600px, the following adjustments apply via media query (`@media only screen and (max-width: 600px)`):

| Element | Desktop | Mobile (≤600px) |
|---|---|---|
| Email wrapper width | 600px | 100% |
| Body side padding | 16px | 12px |
| Story card padding | 16px | 12px |
| Section header padding | 12px 16px | 10px 12px |
| Headline font size | 17px | 16px |
| Summary font size | 14px | 14px (unchanged) |
| Executive Summary bullet | 15px | 15px (unchanged) |
| Section nav | horizontal scroll | horizontal scroll, smaller pills |
| Nav pill font size | 12px | 11px |
| Nav pill padding | 5px 12px | 4px 8px |
| Footer font size | 11px | 11px (unchanged) |
| Card border-radius | 8px | 6px |

### Minimum Tap Target Sizes

All interactive elements must meet **44px × 44px minimum tap target** on mobile per Apple HIG and WCAG 2.5.5. Implementation approach:

- **Feedback buttons:** `padding: 13px 12px` on mobile (top/bottom padding increased to reach 44px height). Width is auto based on text.
- **CTA text links:** `display: inline-block; padding: 13px 0` on mobile to expand the tap zone vertically without changing visual appearance.
- **CTA pill buttons:** `padding: 12px 20px` minimum on mobile.
- **Nav pills:** `padding: 12px 8px` on mobile to reach 44px height.
- **Section header links (› chevron):** Make entire section header a tappable link on mobile (`<a>` wrapping the header bar), not just the `›` character.

### Font Size Floor

- Body text: **14px minimum** — never drop below this on mobile
- Caption/metadata: **11px minimum** — muted text like timestamps
- Confidence tags: **10px minimum** — acceptable given the pill container provides visual context
- Never use `font-size` below 10px anywhere in the email

### Table / Data Degradation

Financial and data-heavy sections may occasionally contain structured data (e.g., capex comparison tables). Rules for graceful degradation:

1. **Avoid HTML tables for layout** entirely — use single-column stacked blocks.
2. **For genuine data tables** (e.g., competitor capex comparison): implement as a scrollable container on mobile using `overflow-x: auto` on the wrapper `<div>`. Table has `min-width: 480px` so it scrolls rather than wraps.
3. **Alternative for mobile:** Generate a text-based equivalent of any table as a fallback below the table, hidden on desktop via `mso-hide:all` and shown on mobile via the media query. Format: bullet list of key facts.
4. **Financial figures inline in summary text** do not require special treatment — they naturally reflow with body text.

---

## 9. Subject Line & Preview Text Formula

### Subject Line Formula

```
[Signal anchor]: [Specific fact or number] — [OCI relevance hook]
```

The subject line must contain:
1. A leading signal (most important story or theme today)
2. One specific data point or named entity (makes it feel curated, not generic)
3. A trailing OCI relevance hook (tells the executive "this matters to your job")

**Subject line rules:**
- Maximum 60 characters (Gmail clips at ~60 on mobile)
- No emojis for this audience
- Never start with "Your" or "Daily" (triggers "marketing" perception)
- Always personalized to recipient's top-weight section
- Sentence case (not title case except for proper nouns)

**Formula applied per persona:**

Karan Batta (Financial/Compete lead):
```
Formula: [Competitor action]: $[amount] — [OCI strategic implication in 4 words]
Example: "AWS $15B expansion: OCI pricing window opens"
Example: "Azure GPU backlog hits 6 months: capture opportunity now"
Example: "Google cuts compute pricing 12%: renewal timing matters"
```

Nathan Thomas (Multi-cloud/Deals lead):
```
Formula: [Partner/deal signal]: [entity] + [OCI channel hook]
Example: "Snowflake expands AWS deal: OCI path still open"
Example: "Multi-cloud mandate grows at F500: pipeline implication"
Example: "Databricks on Azure: partner displacement risk flagged"
```

Greg Pavlik (AI/Compete lead):
```
Formula: [Model/capability name] [action verb]: [capability gap / OCI angle]
Example: "Llama 4 released: 70B open-weights, OCI serving gap"
Example: "Gemini 2.0 tops benchmark: what OCI AI must answer"
Example: "OpenAI cuts API pricing 30%: OSS vs hosted calculus shifts"
```

Mahesh (Platform/Infra lead):
```
Formula: [Infra/security signal]: [location or scale detail] — [readiness framing]
Example: "Texas power grid delay hits 3 data centers: OCI risk map"
Example: "NIST framework v2 final: OCI compliance posture check"
Example: "AWS outage N. Virginia: resilience comparison surface"
```

### Preview Text (Preheader) Formula

Preview text appears in the email client after the subject line (typically 85–100 characters visible). It should complement, not repeat, the subject line.

```
Formula: [Second most important story today] + [One action or implication]
```

Implementation: Insert a preheader `<span>` immediately inside `<body>` at the top, styled `display: none; max-height: 0; overflow: hidden; mso-hide: all;` — this is the standard preheader hack for email.

Examples:
- Subject: `AWS $15B expansion: OCI pricing window opens`
- Preheader: `Also: Meta Llama 4 released open-weights. Azure GPU wait now 6 months. OCI implication inside.`

Rules:
- Always 85–100 characters
- Tease the #2 and #3 stories from the Executive Summary
- End with an action phrase: "OCI implication inside" or "Read before your 9am"

### A/B Testing Recommendations

For subject lines, A/B test across four variables. Each test should run for a minimum of 4 editions before evaluating (small send list requires patience):

| Variable | Variant A | Variant B |
|---|---|---|
| Specificity | Named entity + number | Theme only |
| Framing | Threat framing ("X wins deal") | Opportunity framing ("OCI path opens") |
| Length | Short (40–50 chars) | Medium (55–65 chars) |
| Lead section | Financial-led | Competitive-led |

Track: open rate per variant, per persona. Given 4 recipients initially, treat every edition as a data point and measure trend over weeks, not individual editions.

---

## 10. Tone & Voice Guidelines Per Persona

### Vocabulary Framework

**Shared across all personas:**
- Use: "signals," "implication," "watch," "confirmed," "credible report," "pattern," "opportunity," "risk," "momentum"
- Avoid: "exciting," "revolutionary," "game-changing," "disruptive" (overused), "synergy," "leverage" (as verb), "utilize"
- Always: cite the source in the body when making a factual claim. "Per Bloomberg..." or "Per AWS earnings call..."
- Sentence length: maximum 25 words per sentence in summaries.
- Active voice always. "AWS launched X" not "X was launched by AWS."

---

### 10.1 Karan Batta

**Vocabulary to use:** Capex, margin, pricing, bookings, ARR, churn, revenue, deal size, competitive displacement, unit economics, headroom, TAM, pipeline, velocity, ROI, basis points
**Vocabulary to avoid:** "Developer experience," "ecosystem," "open-source momentum," "community sentiment"
**Sentence length:** Short. Max 20 words per sentence. No preamble. Start with the fact.
**OCI Implication framing:** "What does this cost us or earn us?" Frame every implication as a financial or strategic competitive consequence.

**Example — same story rewritten for Karan:**
Story: Meta releases Llama 4 (70B open-weights, Apache 2.0 license)

> Llama 4 is now public under Apache 2.0. OCI-hosted model pricing will face pressure as enterprises adopt self-hosted open-weights on OCI bare metal. Reserved GPU inventory absorbs this — commodity API pricing does not. Watch enterprise model API renewal conversations in Q2.

---

### 10.2 Nathan Thomas

**Vocabulary to use:** Ecosystem, partner, channel, multi-cloud, customer success, go-to-market, ISV, marketplace, workload portability, enterprise buyer, strategic alliance
**Vocabulary to avoid:** Highly technical model specs (parameter counts, quantization formats), low-level infra details
**Sentence length:** Medium. 20–25 words per sentence. Narrative connective tissue is acceptable.
**OCI Implication framing:** "What does this mean for our partners and customers?" Frame as deal impact, partner channel signal, or customer retention/acquisition signal.

**Example — same story rewritten for Nathan:**
Story: Meta releases Llama 4 (70B open-weights, Apache 2.0 license)

> Meta's Llama 4 release puts open-source AI capability within reach of any enterprise IT team without a proprietary model contract. Partners building on OCI have a clear pitch: run Llama 4 on OCI Compute with no model licensing cost. This is a go-to-market moment for AI workload acquisition from Azure and AWS accounts that are locked into proprietary model pricing.

---

### 10.3 Greg Pavlik

**Vocabulary to use:** Architecture, inference, fine-tuning, quantization, benchmark, throughput, latency, context window, parameter count, RLHF, OSS, Apache 2.0, capability gap, model family, embedding, retrieval
**Vocabulary to avoid:** "Game-changer," vague business framing without technical grounding
**Sentence length:** Medium to long. 22–28 words acceptable. Technical precision over brevity.
**OCI Implication framing:** "What capability does OCI have or lack relative to this development?" Frame as competitive technical assessment with estimated time-to-parity or differentiation opportunity.

**Example — same story rewritten for Greg:**
Story: Meta releases Llama 4 (70B open-weights, Apache 2.0 license)

> Meta released Llama 4 at 70B parameters under Apache 2.0, with a reported 1M token context window and strong performance on MMLU and HumanEval benchmarks. The open-weight release enables fine-tuning and self-hosting without licensing restriction. OCI's A100/H100 cluster density is well-positioned for Llama 4 inference at scale, but OCI does not yet offer a managed fine-tuning service comparable to Azure ML or Vertex AI. This gap is now commercially material.

---

### 10.4 Mahesh

**Vocabulary to use:** Resilience, availability, secure, compliance, platform, developer platform, SLA, hardened, zero-trust, identity, posture, sovereign, workload isolation, operational readiness
**Vocabulary to avoid:** Detailed financial modeling language, partnership deal structure details
**Sentence length:** Medium. 20–24 words per sentence. Operational framing.
**OCI Implication framing:** "What does this mean for OCI's security posture, platform readiness, or developer trust?" Frame as platform risk, compliance requirement, or operational opportunity.

**Example — same story rewritten for Mahesh:**
Story: Meta releases Llama 4 (70B open-weights, Apache 2.0 license)

> Llama 4's open-weight Apache 2.0 release means enterprises can run frontier-class models on-premises or on sovereign cloud deployments without vendor data sharing. For security-conscious OCI customers — government, financial services, healthcare — this changes the AI adoption calculus. OCI's bare metal compute and network isolation posture is directly relevant here. The platform team should assess whether OCI's AI deployment docs and hardened runtime guides are current for Llama 4-class workloads.

---

## 11. Tracked Link UX

### How Tracked Links Appear to the Reader

Tracked links must never display a suspicious URL, tracker domain, or raw UTM string in the email body. The reader should see either:
1. A clean CTA label: `Read full story →` (inline text link)
2. A styled button: `Read full story` (pill button)
3. A domain-branded redirect: the href points to `briefing.oci.oracle.com/r/{encoded_token}` which transparently redirects to the article

The reader never sees `bit.ly`, `utm_source=...`, `track.mailchimp.com`, or any ESP tracking domain. This is critical for an executive audience — suspicious-looking links destroy trust.

### CTA Button vs Inline Text Link: When to Use Each

**Inline text link** (`Read full story →`):
- Default treatment for all standard story cards
- Used when the card already has visual weight from the confidence tag and OCI implication callout
- Color: `#C74634` (OCI Red), 13px, 600, no underline by default
- The `→` character is part of the link text, not a separate element

**Pill button** (`Read full story`):
- Used only for the **Executive Summary** items (linked to the full story) and for the top 1–2 highest-scored stories in the briefing
- Background: `#C74634`, text: `#FFFFFF`, 13px, 600, padding: 8px 20px, border-radius: 4px
- Never use pill buttons for feedback actions (those are ghost pills)
- On mobile: ensure minimum 44px height tap target

**Rule:** Never use more than one pill button above the fold. Use inline text links for everything else.

### Redirect Implementation

Every outbound link in the email is replaced by a unique tracking URL at render time:

```
https://briefing.oci.oracle.com/r/{base64_encoded_payload}
```

The payload encodes:
- `recipient_id` (SHA-256 of email address, truncated)
- `edition_date` (YYYY-MM-DD)
- `section_id` (e.g., `financial`, `compete`)
- `story_id` (canonical story hash)
- `link_position` (integer, 1-indexed within section)
- `canonical_url` (the actual destination URL)

The redirect endpoint: receives the token, logs the click event to the analytics store, then issues a `302 Location:` to the canonical URL. This is transparent to the reader (browser shows the canonical URL in the address bar after redirect).

**Do not use external link shorteners** (Bitly, etc.) for the primary tracking mechanism — use the OCI-owned redirect endpoint. Bitly can be used as a secondary signal if already in the pipeline, but the primary CTA link should be on an oracle.com subdomain.

---

## 12. Feedback Widget Design

### Placement

The feedback row appears at the bottom of every story card, separated from the CTA link by a thin horizontal rule:
- `border-top: 1px solid #E2E8F0`
- `padding-top: 10px`
- `margin-top: 12px`

It is always the last element inside the story card container.

### The Four Feedback Actions

| Button | Label | Feedback type | Icon |
|---|---|---|---|
| 1 | `Useful` | `useful` | 👍 |
| 2 | `Not useful` | `not_useful` | 👎 |
| 3 | `More like this` | `more_like_this` | ➕ |
| 4 | `Less like this` | `less_like_this` | 🚫 |

Layout: Horizontal row, left-aligned, buttons separated by 8px margin-right.

On mobile: The four buttons wrap to two rows of two if viewport is under 480px. Each button maintains 44px minimum height via padding.

### HTML Implementation in Email (No JavaScript)

Since email clients do not execute JavaScript, feedback buttons are implemented as styled `<a>` (anchor) links. Each button is a unique URL that encodes the feedback signal.

```html
<!-- Feedback row implementation -->
<table role="presentation" cellpadding="0" cellspacing="0" border="0"
       style="margin-top:12px; border-top:1px solid #E2E8F0; padding-top:10px; width:100%;">
  <tr>
    <td>
      <a href="https://briefing.oci.oracle.com/feedback/{token}?type=useful"
         style="display:inline-block; font-family:-apple-system,Arial,sans-serif;
                font-size:12px; font-weight:400; color:#8896A5;
                border:1px solid #E2E8F0; border-radius:16px;
                padding:6px 12px; margin-right:8px;
                background:#F7F8FA; text-decoration:none;">
        👍 Useful
      </a>
      <a href="https://briefing.oci.oracle.com/feedback/{token}?type=not_useful"
         style="display:inline-block; font-family:-apple-system,Arial,sans-serif;
                font-size:12px; font-weight:400; color:#8896A5;
                border:1px solid #E2E8F0; border-radius:16px;
                padding:6px 12px; margin-right:8px;
                background:#F7F8FA; text-decoration:none;">
        👎 Not useful
      </a>
      <a href="https://briefing.oci.oracle.com/feedback/{token}?type=more_like_this"
         style="display:inline-block; font-family:-apple-system,Arial,sans-serif;
                font-size:12px; font-weight:400; color:#8896A5;
                border:1px solid #E2E8F0; border-radius:16px;
                padding:6px 12px; margin-right:8px;
                background:#F7F8FA; text-decoration:none;">
        ➕ More like this
      </a>
      <a href="https://briefing.oci.oracle.com/feedback/{token}?type=less_like_this"
         style="display:inline-block; font-family:-apple-system,Arial,sans-serif;
                font-size:12px; font-weight:400; color:#8896A5;
                border:1px solid #E2E8F0; border-radius:16px;
                padding:6px 12px; margin-right:0;
                background:#F7F8FA; text-decoration:none;">
        🚫 Less like this
      </a>
    </td>
  </tr>
</table>
```

The `{token}` is a unique per-story-per-recipient token that encodes:
- `recipient_id`
- `story_id`
- `edition_date`
- `section_id`
- `feedback_type` (also passed as query param for readability)

### "Too Repetitive" Flag

"Too repetitive" is a special feedback signal that fires at the story level when the recipient believes this story has already been covered adequately. Implementation:

- Appears as a 5th option **only** on stories tagged as `[↻ FOLLOW-UP]` (follow-up variant cards)
- Label: `🔁 Too repetitive`
- Same pill styling as other feedback buttons
- URL: `briefing.oci.oracle.com/feedback/{token}?type=too_repetitive`
- This signal feeds back into the novelty score and duplication threshold for the next 7 days for this recipient

### Confirmation Feedback

When a recipient clicks a feedback button:

1. The tracking endpoint records the feedback event
2. The endpoint issues a `302` redirect to a **static thank-you page** hosted on OCI Object Storage:
   - URL: `https://briefing.oci.oracle.com/thanks?type={feedback_type}`
   - Page: Minimal HTML with message "Thanks — your feedback has been recorded." and OCI wordmark
   - Auto-closes after 3 seconds via `<meta http-equiv="refresh" content="3;url=about:blank">`
3. Do **not** use mailto links for feedback confirmation — email reply loops add noise
4. Do **not** redirect back into the email or inbox — this confuses users
5. The static thank-you page should have no navigation, no additional links — it is a receipt only

---

## 13. HTML Email Implementation Notes

### Recommended Framework: MJML

**Recommendation: MJML** (https://mjml.io)

Rationale:
- MJML compiles to table-based HTML that is compatible with Outlook (which requires table layout)
- MJML handles MSO conditional comments automatically (targeting old Outlook rendering engine)
- MJML's component system (`mj-section`, `mj-column`, `mj-button`, `mj-text`) maps cleanly to the component library in Section 3
- The generated HTML is inline-CSS, which is required for most email clients
- MJML is actively maintained and battle-tested across all major email clients
- Alternative consideration: **Hand-coded table layout** is acceptable if the engineering team has email HTML expertise and wants full control. Foundation for Email (Zurb) is not recommended — it adds unnecessary CSS complexity and its grid system is overkill for a single-column layout.

**Do not use:** React Email, HEML, or any framework that requires a Node.js runtime for rendering — the rendering pipeline should produce static HTML that can be stored in OCI Object Storage.

### MJML Project Structure

```
/templates
  base.mjml           ← shared header, footer, nav, exec summary structure
  section-header.mjml ← section header component (parameterized)
  story-card.mjml     ← story card component (standard, follow-up, watch variants)
  exec-summary.mjml   ← executive summary block
  feedback-row.mjml   ← feedback button row component

/personas
  karan.json          ← section order, density, tone params
  nathan.json
  greg.json
  mahesh.json

/renderer
  render.py           ← ingests canonical story bundle + persona JSON, outputs HTML
```

### CSS Inlining Approach

MJML inlines all CSS at compile time. For any custom styles not supported by MJML attributes:
1. Use `mj-style` block within the MJML template for media queries (MJML preserves these in `<head>`)
2. Use `mj-raw` to inject raw HTML blocks where MJML components are insufficient
3. Never rely on `<style>` blocks for properties that must render in Gmail — Gmail strips `<head>` styles for non-Gmail-specific build configurations
4. Test all CSS via Can I Email (caniemail.com) before deploying

### Image Hosting

- **All images hosted on OCI Object Storage** in a public-read bucket with a long-lived CDN URL
- Image types in this template: OCI wordmark (PNG, 2x retina), section emoji icons (text, not images — no hosting needed), feedback button icons (text emoji, no hosting needed), footer logo (PNG)
- Max image width in email: 600px; provide @2x versions (1200px) for retina displays using `width="600"` attribute + `style="max-width:100%;"`
- Always include `alt` text for all images; if image fails to load, alt text must be legible and not break layout
- CDN URL format: `https://objectstorage.{region}.oraclecloud.com/n/{namespace}/b/{bucket}/o/{filename}`
- Use a custom domain alias (e.g., `assets.briefing.oci.oracle.com`) via CDN to avoid the raw OCI URL appearing in the email source

### Dark Mode CSS Media Query Pattern

```css
/* In <head> via mj-style — preserved by MJML */

@media (prefers-color-scheme: dark) {
  /* Email body background */
  body, .email-body { background-color: #0D1117 !important; }

  /* Card backgrounds */
  .story-card { background-color: #161B22 !important; border-color: #30363D !important; }

  /* Text */
  .text-primary { color: #E6EDF3 !important; }
  .text-secondary { color: #8B949E !important; }
  .text-muted { color: #656D76 !important; }

  /* Borders and dividers */
  .border-default { border-color: #30363D !important; }

  /* OCI implication box */
  .oci-implication { background-color: #0D2137 !important; }
  .oci-implication-text { color: #A8C8E8 !important; }

  /* Feedback buttons */
  .feedback-btn { background-color: #21262D !important; border-color: #30363D !important; color: #8B949E !important; }

  /* Section header — already dark, no change needed */
  /* Header band — already dark, no change needed */
}

/* Outlook dark mode (Windows 10+ Mail app) */
[data-ogsc] .story-card { background-color: #161B22 !important; }
[data-ogsb] body { background-color: #0D1117 !important; }
```

**Notes on dark mode:**
- Gmail web does not support `prefers-color-scheme` as of 2026; Gmail Android does
- Apple Mail (macOS and iOS) has full dark mode support — this is the primary dark mode target
- Outlook desktop (Windows) uses a different dark mode mechanism (`data-ogsc`/`data-ogsb` attributes)
- Always test dark mode in Apple Mail on iOS before each template change
- Avoid white backgrounds on images — use transparent PNGs so they adapt to dark backgrounds

### Email Client Compatibility Matrix

| Client | Dark Mode | CSS Support | Table Layout | Notes |
|---|---|---|---|---|
| Gmail Web | No `@media` | Partial | Required | Strips `<head>` CSS; inline only |
| Gmail Android | `prefers-color-scheme` | Partial | Required | Better than web |
| Gmail iOS | `prefers-color-scheme` | Partial | Required | Similar to Android |
| Apple Mail (macOS) | Full | Excellent | Optional | Best rendering; supports media queries |
| Apple Mail (iOS) | Full | Excellent | Optional | Best mobile rendering |
| Outlook 2016–2021 (Windows) | `data-ogsc` | Minimal | Required (Word engine) | Use MSO conditionals; avoid CSS3 |
| Outlook 365 (Windows) | `data-ogsc` | Minimal | Required | Same as Outlook desktop |
| Outlook (macOS) | `prefers-color-scheme` | Good | Optional | Modern WebKit engine; much better |
| Samsung Mail | `prefers-color-scheme` | Moderate | Required | Test border-radius support |
| Yahoo Mail | None | Partial | Required | Strips many styles; test carefully |

**MSO conditional comments for Outlook:**
Use MSO conditionals to add Outlook-specific spacing and layout fixes:

```html
<!--[if mso]>
<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0">
  <tr><td>
<![endif]-->
  <!-- email content -->
<!--[if mso]>
  </td></tr>
</table>
<![endif]-->
```

All border-radius values: set `mso-border-radius` in Outlook conditionals if needed, or accept that Outlook renders square corners (acceptable for this use case).

### Max Email File Size

**Target: under 100KB of HTML source.**

Gmail clips emails above approximately 102KB and shows a "Message clipped" warning with a "View entire message" link — this destroys the reading experience and breaks tracked links.

Strategies to stay under 100KB:
1. Inline CSS is verbose — MJML-generated HTML is typically 60–90KB for a 10-story briefing
2. Limit the number of story cards per edition: maximum 15 cards total across all sections
3. Strip HTML comments from the final rendered output before sending
4. Compress whitespace in the generated HTML (minify) — target output should have no unnecessary whitespace
5. Do not embed base64-encoded images in the HTML — always reference external URLs
6. Feedback button rows and OCI implication boxes are the most verbose components — audit their generated HTML size during development

**Pre-send check:** Run `wc -c` on the final rendered HTML. If above 95,000 bytes, reduce story count or shorten OCI implication text before sending.

### Sending Infrastructure

- **ESP:** Postmark (per project brief) — configured for transactional email, not marketing ESP
- Postmark open tracking: enabled via Postmark's tracking pixel (auto-injected)
- Postmark click tracking: **disabled** — use the custom OCI redirect endpoint instead of Postmark's click tracking, so that all click data is under OCI control
- DKIM: configured on `oci.oracle.com` or a sending subdomain (e.g., `briefing.oci.oracle.com`)
- SPF and DMARC: must be configured for the sending domain before first send
- From address: `OCI Intelligence <briefing@oci.oracle.com>` (not a personal name — treat as a product, not a personal assistant)
- Reply-to: a monitored inbox (e.g., `oci-briefing-feedback@oracle.com`) that can route editorial feedback to the team

---

*End of OCI AI Daily Executive Briefing — Email UX & Design Specification v1.0*
