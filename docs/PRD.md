# Product Requirements Document: AI Daily Executive Briefing

**Version:** 1.0
**Date:** 2026-03-10
**Status:** Draft
**Owner:** Product Management

---

## Table of Contents

1. [Product Vision & Goals](#1-product-vision--goals)
2. [Audience Profiles](#2-audience-profiles)
3. [Audience Profile Schema](#3-audience-profile-schema)
4. [Briefing Section Specification](#4-briefing-section-specification)
5. [Scoring Model Specification](#5-scoring-model-specification)
6. [Content Deduplication Requirements](#6-content-deduplication-requirements)
7. [Editorial Rules & Content Governance](#7-editorial-rules--content-governance)
8. [Delivery Requirements](#8-delivery-requirements)
9. [Feedback & Analytics Requirements](#9-feedback--analytics-requirements)
10. [Success Metrics & KPIs](#10-success-metrics--kpis)
11. [Feature Prioritization](#11-feature-prioritization)
12. [Open Questions with Recommendations](#12-open-questions-with-recommendations)

---

## 1. Product Vision & Goals

### What It Is

The AI Daily Executive Briefing is an automated, personalized intelligence digest delivered every morning to Oracle Cloud Infrastructure (OCI) senior executives. It ingests signals from dozens of sources across Tier 1 journalism, company press releases, trade media, and community platforms, then scores, deduplicates, and renders a concise briefing tailored to each executive's role and priorities.

The system is not a news aggregator. It is an editorial intelligence layer that applies scoring, deduplication, source credibility, and role-specific framing to surface only what is strategically relevant — and to suppress everything that is noise, redundant, or low signal.

### Why It Exists

Senior OCI executives operate in a fast-moving competitive environment where:

- AI infrastructure, cloud competition, and power/datacenter dynamics shift daily
- The same story is covered by dozens of outlets with varying degrees of accuracy and depth
- Each executive has a distinct charter and therefore a distinct definition of "what matters today"
- Reading the news manually is high-cost and inconsistent — critical signals get missed, and low-quality stories consume attention

The briefing solves this by providing a single, trusted, pre-digested morning read that is specific enough to be actionable and concise enough to be consumed in under 10 minutes.

### What Success Looks Like

**For executives:** The briefing becomes a trusted, essential start-of-day ritual. Readers consistently feel informed before their first meeting and credit the product with surfacing signals they would not have found on their own.

**For the organization:** The briefing improves OCI's speed-to-insight on competitive moves, market shifts, and emerging threats. It reduces the time executives spend on reactive news-gathering and increases time spent on strategic action.

**Quantitative success thresholds** (see Section 10 for full KPI specification):

- Email open rate above 70% within 30 days
- Click-through rate above 25% within 60 days
- Audience relevance rating above 4.0/5.0 within 90 days
- Deduplication accuracy above 90% (no repeated stories without a material fact delta)

---

## 2. Audience Profiles

The system supports a shared ingestion, scoring, and deduplication pipeline. Personalization happens at the rendering stage. Each audience profile drives: which items surface from the canonical bundle, how those items are ordered, which sections appear first, the summary tone, and the total word count budget.

### 2.1 Karan Batta — SVP, OCI Product Management

**Role context:** Leads overall product management for OCI. Prior background includes Azure compute, GPUs, and FPGAs. Operates at the intersection of product strategy and financial performance. Needs to understand competitive positioning, capital allocation signals from hyperscalers, and OCI's relative market position.

**Primary concerns:** Where is hyperscaler capex going? What product gaps are emerging? What are the financial signals that indicate competitive momentum?

**Section weights:**

| Section | Weight |
|---|---|
| Market & Financial Analysis | 35% |
| Competitive Moves | 25% |
| Power & Datacenter | 15% |
| AI Platform & Model News | 15% |
| Deals | 10% |

**Tone:** Concise. High signal-to-noise. Strategic framing with explicit OCI implications. Every item should answer "so what for OCI?" Avoid speculation without sourcing. Prefer numbers and named entities over abstractions.

**Length budget:** Maximum 800 words per briefing (excluding Executive Summary).

**Community signals:** Exclude. Karan's briefing should not surface Reddit or HN items in the main body. Community signal data may still inform scoring but should not appear as content.

**Speculative analysis:** Limited. Include only when sourced from credible analysts or when the strategic implication is significant and the uncertainty is clearly labeled.

**Audience profile schema values:**

```json
{
  "topics_of_interest": ["cloud capex", "GPU supply chain", "hyperscaler financials", "OCI competitive position", "product roadmaps", "margins", "data center financing"],
  "negative_topics": ["consumer AI apps", "social media", "developer tutorials", "open source tooling minutiae"],
  "companies_of_interest": ["AWS", "Azure", "Google Cloud", "NVIDIA", "AMD", "Intel", "Oracle"],
  "geo_focus": ["global", "US", "EU"],
  "preferred_tone": "concise_strategic",
  "time_horizon": "near_term",
  "section_weights": {"financial": 0.35, "compete": 0.25, "datacenter": 0.15, "ai_platform": 0.15, "deals": 0.10},
  "max_length": 800,
  "include_community_signals": false,
  "include_speculative_analysis": "limited"
}
```

---

### 2.2 Nathan Thomas — SVP, OCI Product Management (Cloud & Multicloud)

**Role context:** Oversees product strategy for Oracle's cloud and multicloud services. Operates at the intersection of cloud platforms, partner ecosystems, and enterprise customer expectations. Needs to understand what multicloud customers are buying, where the ecosystem is moving, and which AI deals are closing.

**Primary concerns:** Multicloud adoption patterns, partner ecosystem dynamics, AI-driven deal flow, enterprise procurement trends.

**Section weights:**

| Section | Weight |
|---|---|
| Competitive Moves (multicloud focus) | 30% |
| AI Platform & Model News | 25% |
| Deals | 25% |
| Competitive Moves (partnerships) | 10% |
| Market & Financial Analysis | 10% |

**Tone:** Ecosystem-oriented. Partner-aware. Customer-facing implications are prioritized. Frame stories in terms of what customers and partners are choosing and why. Less internally focused than Karan; more externally focused on buying patterns and ecosystem momentum.

**Length budget:** Maximum 1,000 words per briefing (Nathan benefits from slightly more deal and partnership context).

**Community signals:** Include selectively. GitHub trending and developer sentiment can inform platform signal.

**Speculative analysis:** Moderate. Ecosystem trend analysis and partnership speculation is acceptable when labeled.

**Audience profile schema values:**

```json
{
  "topics_of_interest": ["multicloud", "cloud partnerships", "AI deals", "enterprise procurement", "platform ecosystems", "Kubernetes", "database-as-a-service", "AI workloads"],
  "negative_topics": ["consumer hardware", "chip fabrication minutiae", "power utility regulation"],
  "companies_of_interest": ["AWS", "Azure", "Google Cloud", "Snowflake", "Databricks", "VMware", "Red Hat", "Oracle", "Palantir", "ServiceNow"],
  "geo_focus": ["global", "US", "EU", "APAC"],
  "preferred_tone": "ecosystem_partner_aware",
  "time_horizon": "near_to_mid_term",
  "section_weights": {"multicloud_compete": 0.30, "ai_platform": 0.25, "deals": 0.25, "partnerships": 0.10, "financial": 0.10},
  "max_length": 1000,
  "include_community_signals": true,
  "include_speculative_analysis": "moderate"
}
```

---

### 2.3 Greg Pavlik — EVP, OCI Data & AI

**Role context:** EVP for AI and Data Management Services. Responsible for strategy and delivery across Oracle's AI-centered portfolio. Deep technical background; evaluates competitive AI capability at the model, platform, and infrastructure layer. Needs to understand where capability gaps exist, which AI platforms are winning, and how OSS momentum affects Oracle's position.

**Primary concerns:** AI model and platform landscape, competitive capability gaps, open source innovation velocity, research-to-product pipeline signals.

**Section weights:**

| Section | Weight |
|---|---|
| Competitive Moves | 35% |
| AI Platform & Model News | 35% |
| OSS / Innovation (within AI Platform section) | 15% |
| Partnerships | 10% |
| Community Signal | 5% |

**Tone:** Technical but executive. Does not need basics explained. Prefers capability-level framing (e.g., "model X beats Oracle's current offering on benchmark Y") over financial framing. Focuses on gaps and opportunities, not just news recitation.

**Length budget:** Maximum 1,100 words per briefing. Greg is the most likely to read deeper technical detail.

**Community signals:** Include. HN and GitHub trending are meaningful signal sources for this audience — they indicate developer adoption and momentum before it appears in mainstream press.

**Speculative analysis:** Include. Greg operates at the strategic frontier and benefits from labeled speculative analysis of where AI capabilities are heading.

**Audience profile schema values:**

```json
{
  "topics_of_interest": ["foundation models", "AI infrastructure", "vector databases", "ML frameworks", "OSS AI tooling", "GPU architectures", "AI benchmarks", "inference optimization", "RAG", "agent frameworks"],
  "negative_topics": ["financial earnings detail", "real estate / site selection", "power utility contracts"],
  "companies_of_interest": ["OpenAI", "Anthropic", "Google DeepMind", "Meta AI", "Mistral", "Cohere", "Hugging Face", "NVIDIA", "AMD", "Oracle"],
  "geo_focus": ["global"],
  "preferred_tone": "technical_executive",
  "time_horizon": "near_to_long_term",
  "section_weights": {"compete": 0.35, "ai_platform": 0.35, "oss_innovation": 0.15, "partnerships": 0.10, "community": 0.05},
  "max_length": 1100,
  "include_community_signals": true,
  "include_speculative_analysis": "full"
}
```

---

### 2.4 Mahesh — EVP, OCI Security & Developer Platform

**Role context:** EVP of OCI Security and Developer Platform. Mission is flexible, open, secure cloud platforms. Needs to understand infrastructure resilience, physical scale readiness (power, datacenter capacity), AI platform dynamics as they affect developer tooling, and deal signals that indicate scale requirements.

**Primary concerns:** Physical infrastructure readiness (power availability, datacenter capacity), AI platform tooling for developers, security implications of AI platforms, deals that signal scale requirements for OCI infrastructure.

**Section weights:**

| Section | Weight |
|---|---|
| Power & Datacenter | 45% (Power 20% + Datacenter 25%) |
| AI Platform & Model News | 20% |
| Deals | 20% |
| Security / Platform Implications (within OCI Implications section) | 15% |

**Tone:** Platform and resilience focused. Scale readiness framing. Implications for secure operations. Less interested in financial performance, more interested in physical capacity and developer platform signals.

**Length budget:** Maximum 900 words per briefing.

**Community signals:** Exclude from main content. May be used for scoring only.

**Speculative analysis:** Limited. Mahesh needs actionable signals, not speculative trend analysis.

**Audience profile schema values:**

```json
{
  "topics_of_interest": ["power availability", "datacenter capacity", "site selection", "grid infrastructure", "cooling technology", "rack density", "developer platforms", "AI security", "open platforms", "container infrastructure"],
  "negative_topics": ["financial analysis", "VC funding rounds", "social media AI products"],
  "companies_of_interest": ["NVIDIA", "AWS", "Google Cloud", "Azure", "Equinix", "Digital Realty", "Oracle", "Intel", "AMD"],
  "geo_focus": ["US", "EU", "APAC"],
  "preferred_tone": "resilience_operations_focused",
  "time_horizon": "near_term",
  "section_weights": {"power": 0.20, "datacenter": 0.25, "ai_platform": 0.20, "deals": 0.20, "security_platform": 0.15},
  "max_length": 900,
  "include_community_signals": false,
  "include_speculative_analysis": "limited"
}
```

---

## 3. Audience Profile Schema

Each executive is represented by a profile object conforming to the following schema. This schema is the authoritative contract between the personalization engine and the rendering pipeline.

### 3.1 Schema Definition

```typescript
interface AudienceProfile {
  audience_id: string;                          // Unique identifier (e.g., "karan_batta")
  display_name: string;                         // Human-readable name
  role: string;                                 // Job title
  topics_of_interest: string[];                 // See field 1
  negative_topics: string[];                    // See field 2
  companies_of_interest: string[];              // See field 3
  geo_focus: GeoScope[];                        // See field 4
  preferred_tone: ToneType;                     // See field 5
  time_horizon: TimeHorizonType;                // See field 6
  section_weights: SectionWeightMap;            // See field 7
  max_length: number;                           // See field 8 (words)
  include_community_signals: boolean;           // See field 9
  include_speculative_analysis: SpecLevel;      // See field 10
}
```

---

### 3.2 Field Specifications

#### Field 1: `topics_of_interest`

**Type:** `string[]`
**Required:** Yes
**Cardinality:** 3–20 items recommended

**Description:** Free-form topic tags that bias the scoring engine toward content matching these themes. These are used for keyword matching, embedding similarity comparison, and topic taxonomy lookups during the audience relevance scoring step.

**Examples:**
```json
["cloud capex", "GPU supply chain", "hyperscaler financials", "multicloud", "AI benchmarks", "power availability"]
```

**Validation rules:**
- Minimum 3 items required
- Maximum 20 items (beyond this, signal dilutes)
- Each item must be a non-empty string, maximum 60 characters
- Items should be in English; multi-language support is out of scope for V1
- No duplicates allowed (case-insensitive)

---

#### Field 2: `negative_topics`

**Type:** `string[]`
**Required:** No
**Cardinality:** 0–10 items

**Description:** Topics that should actively suppress content from appearing in this audience's briefing. Items matching negative topics are scored down during the audience relevance step and filtered from the final selection unless their overall score is exceptionally high (above the 95th percentile of the day's bundle).

**Examples:**
```json
["consumer AI apps", "social media", "developer tutorials", "VC seed rounds"]
```

**Validation rules:**
- Optional field; defaults to empty array
- Maximum 10 items
- Items should not overlap with `topics_of_interest` (warn if overlap detected)
- Negative topics reduce score by 30% of the audience relevance dimension, not a hard filter

---

#### Field 3: `companies_of_interest`

**Type:** `string[]`
**Required:** Yes
**Cardinality:** 3–30 items

**Description:** Named companies whose mentions in articles trigger a relevance boost during scoring. Matched against the normalized entity extraction output (NER). Company name variations and common aliases should be captured in the entity normalization layer (e.g., "Microsoft Azure" → "Azure" and "Microsoft").

**Examples:**
```json
["AWS", "Azure", "Google Cloud", "NVIDIA", "AMD", "Oracle", "Snowflake"]
```

**Validation rules:**
- Minimum 3 items required
- Maximum 30 items
- Exact name matching after normalization; aliases handled at the entity extraction layer, not in this field
- "Oracle" should always be included for all audiences (hardcoded fallback)

---

#### Field 4: `geo_focus`

**Type:** `GeoScope[]` where `GeoScope` is an enum: `"global" | "US" | "EU" | "APAC" | "LATAM" | "MEA"`
**Required:** Yes
**Cardinality:** 1–6 items

**Description:** Geographic scope for filtering and boosting content. Articles from or about regions outside the audience's geo focus receive a 20% penalty on audience relevance score. "global" includes all regions.

**Examples:**
```json
["US", "EU"]
// or
["global"]
```

**Validation rules:**
- Minimum 1 item required
- If "global" is included, other values are redundant and will be ignored
- At least one geography required to ensure the scoring engine does not default to global for all audiences

---

#### Field 5: `preferred_tone`

**Type:** Enum
**Required:** Yes
**Allowed values:**

| Value | Description |
|---|---|
| `concise_strategic` | Short, high signal, implication-heavy, minimal narrative |
| `ecosystem_partner_aware` | Ecosystem and customer framing; partner implications foregrounded |
| `technical_executive` | Technical depth without basic explanations; capability-gap framing |
| `resilience_operations_focused` | Physical infrastructure, uptime, scale, and security framing |

**Validation rules:**
- Must be one of the four allowed enum values
- Used by the LLM generation step to select the appropriate system prompt variant for summary generation
- Cannot be null; defaults to `concise_strategic` if omitted

---

#### Field 6: `time_horizon`

**Type:** Enum
**Required:** Yes
**Allowed values:**

| Value | Description | Scoring effect |
|---|---|---|
| `near_term` | Focus on events happening now or in the next 30 days | Boosts timeliness score for items published in last 24h; de-emphasizes trend analysis |
| `near_to_mid_term` | Events now through next 90 days | Balanced timeliness and trend weighting |
| `near_to_long_term` | Now through 12+ months | Allows speculative analysis; trend signals weighted equally with news |

**Validation rules:**
- Must be one of the three allowed enum values
- Influences timeliness scoring weight in the final score formula

---

#### Field 7: `section_weights`

**Type:** `SectionWeightMap` — an object mapping section identifiers to decimal weights
**Required:** Yes

**Description:** Determines how aggressively the ranking engine favors items from each briefing section. Weights must sum to 1.0. Section identifiers must match the canonical section list.

**Canonical section identifiers:**
```
executive_summary | financial | power | datacenter | compete | ai_platform | deals | community | oci_implications
```

**Note:** `executive_summary` and `oci_implications` are generated sections that do not receive explicit weights — they are always included. Weights apply to the five content sections.

**Example:**
```json
{
  "financial": 0.35,
  "compete": 0.25,
  "datacenter": 0.15,
  "ai_platform": 0.15,
  "deals": 0.10
}
```

**Validation rules:**
- All weights must be non-negative floats
- Sum of all section weights must equal 1.0 (±0.01 tolerance for floating point)
- Minimum weight per included section: 0.05 (to avoid zero-weight sections that render blank)
- Sections with weight 0.0 may be omitted from the briefing entirely

---

#### Field 8: `max_length`

**Type:** `integer` (word count)
**Required:** Yes
**Range:** 400–1,500

**Description:** Maximum total word count for the rendered briefing body, excluding the Executive Summary (which has its own fixed length budget of approximately 150 words). The rendering engine will truncate or reduce item counts to meet this budget.

**Examples:**
- `800` — Karan (tightest budget, highest signal density)
- `1000` — Nathan
- `1100` — Greg (most technical depth)
- `900` — Mahesh

**Validation rules:**
- Must be an integer between 400 and 1,500
- Executive Summary word count (~150 words) is additive and not counted against this budget
- OCI Implications section (~100 words) is also additive
- Rendering engine must log a warning if output exceeds `max_length * 1.1` (10% overflow tolerance)

---

#### Field 9: `include_community_signals`

**Type:** `boolean`
**Required:** Yes

**Description:** Controls whether Tier 4 community sources (Hacker News, Reddit, GitHub trending, LinkedIn posts) appear as content items in the rendered briefing. When `false`, community signal data still flows through the pipeline and contributes to momentum scoring, but is not rendered as a standalone briefing item.

**Values:**
- `true` — Community Signal section is included in the briefing (Greg, Nathan)
- `false` — Community Signal section is suppressed (Karan, Mahesh)

**Validation rules:**
- Must be a boolean
- Cannot be null
- When `false`, the section_weights map should not include a non-zero weight for `community`; validation will warn if inconsistent

---

#### Field 10: `include_speculative_analysis`

**Type:** Enum
**Required:** Yes
**Allowed values:**

| Value | Description |
|---|---|
| `none` | No speculative content; only confirmed or credible report confidence tags |
| `limited` | Speculation allowed only when labeled and sourced from credible analysts |
| `moderate` | Trend analysis and labeled speculation acceptable |
| `full` | Full speculative analysis; weak signal items can be surfaced with explicit labeling |

**Validation rules:**
- Must be one of four allowed enum values
- Controls which confidence tags are allowed in the audience's rendered output
- `none` and `limited` suppress items tagged `weak_signal`
- `moderate` allows `weak_signal` if source is Tier 2 or above
- `full` allows `weak_signal` from any tier with appropriate labeling

---

## 4. Briefing Section Specification

The briefing consists of eight sections. Two sections (Executive Summary and OCI Implications) are always rendered. The remaining six are weighted and filtered per audience profile.

### Section 4.1 — Executive Summary

**Purpose:** Orient the reader in under 60 seconds. Surfaces only the highest-scoring items across all sections. Not a duplicate of section content — written as a standalone synthesized view.

**Content types:**
- 3–5 bullet points of "what matters today" across all domains
- One standalone line: "OCI implication of the day" — the single most strategically important signal for OCI

**Source tiers:** Derived from selected section items; no independent sourcing. Sources are inherited from the items cited.

**Typical item count:** 3–5 bullets + 1 implication line

**Max length per audience:**
- All audiences: ~150 words (fixed, does not count against `max_length` budget)

**Generation note:** The LLM generates the Executive Summary last, after all section items are finalized, so it can accurately represent the day's selection. It should not introduce new facts not covered in section items.

**Hardcoded rules:**
- Must always be present regardless of audience profile
- OCI implication line is mandatory
- Bullets must reference only items that appear in the body sections

---

### Section 4.2 — Market & Financial Analysis

**Purpose:** Capture financial signals that indicate where capital, competition, and demand are moving. Primary input for strategic resource allocation decisions.

**Content types:**
- Hyperscaler capex announcements and guidance
- Cloud bookings, revenue growth, and margin commentary
- Data center financing and REIT activity
- Major earnings call quotes relevant to cloud/AI
- Demand signal language from CFO/CEO commentary
- Analyst forecast changes for cloud/AI infrastructure

**Source tiers to use:**
- Tier 1 primary: Earnings transcripts, SEC filings, investor relations pages (highest weight)
- Tier 2: Reuters, Bloomberg, WSJ, FT, CNBC, The Information
- Tier 3: SemiAnalysis (when accessible), major analyst reports
- Tier 4: Not used for factual claims; may inform momentum scoring only

**Typical item count:** 2–4 items

**Max length per audience:**
- Karan: 300 words (section-level; highest weight audience)
- Nathan: 120 words
- Greg: 100 words
- Mahesh: Typically omitted (weight 0.0); may appear if financial item has security/infra implications

**Confidence tag guidance:** Financial claims from earnings transcripts: `confirmed`. Analyst forecasts: `credible report`. Rumored deals: `weak signal` or omit.

---

### Section 4.3 — Power & Datacenter

**Purpose:** Track physical infrastructure signals: where power is constrained, where new capacity is coming online, and how supply chain dynamics affect cloud build-out velocity.

**Content types:**
- Power availability signals (grid constraints, utility agreements, new power contracts)
- Grid/transmission/utility partnerships
- New datacenter campus announcements, expansions, and delays
- Site selection decisions and permitting activity
- Cooling technology developments and rack density improvements
- Supply chain signals affecting datacenter build-out

**Source tiers to use:**
- Tier 1 primary: Utility press releases, regulatory filings (FERC, state utility commissions), government economic development announcements
- Tier 2: Reuters, Bloomberg for major financing/expansion stories
- Tier 3: Data Center Dynamics (highest-value Tier 3 source for this section), Fierce Network
- Tier 4: Not used

**Typical item count:** 2–3 items

**Max length per audience:**
- Mahesh: 400 words (highest weight; split Power 20% + Datacenter 25%)
- Karan: 150 words
- Nathan: 100 words (only if cross-cloud relevance)
- Greg: Typically omitted

**Confidence tag guidance:** Utility regulatory filings: `confirmed`. Company announcements without regulatory filing: `credible report`. Unconfirmed site selection rumors: `weak signal`.

---

### Section 4.4 — Competitive Moves

**Purpose:** Track what Oracle's cloud competitors are doing at the infrastructure, product, partnership, and multi-cloud layers.

**Content types:**
- Cloud infrastructure announcements (new regions, new services, capacity expansions)
- Product launches and feature announcements from hyperscalers
- Partnership announcements (especially multi-cloud, cross-cloud integrations)
- Competitive positioning moves (pricing, bundling, enterprise terms)
- Multi-cloud and distributed cloud strategy signals

**Source tiers to use:**
- Tier 1 primary: Vendor blogs, official product launch pages, partner press releases
- Tier 2: Bloomberg, WSJ, The Information for scoops on competitive deals
- Tier 3: CloudWars, The Register, cloud trade press
- Tier 4: Not used for claims; developer community reaction may inform momentum

**Typical item count:** 2–4 items

**Max length per audience:**
- Greg: 350 words (35% weight; technical capability-gap framing)
- Karan: 225 words (25% weight)
- Nathan: 280 words (30% multicloud weight + 10% partnerships)
- Mahesh: ~100 words (only security/platform-relevant compete moves)

**Confidence tag guidance:** Official vendor announcements: `confirmed`. Reported but unconfirmed roadmap: `credible report`. Industry speculation: `weak signal`.

---

### Section 4.5 — AI Platform & Model News

**Purpose:** Track the AI model and platform landscape — new model launches, infrastructure demand signals, and the open source ecosystem.

**Content types:**
- Model launches and major updates (GPT, Claude, Gemini, Llama, Mistral, Cohere, etc.)
- RLM (reasoning language model) preorders and availability
- AI infrastructure demand signals from AI labs
- Open source framework releases and OSS ecosystem momentum
- Research blog posts signaling near-term productization
- Breaking technical announcements

**Source tiers to use:**
- Tier 1 primary: OpenAI / Anthropic / Google / Meta / xAI / Mistral / Cohere official blogs and newsrooms, Hugging Face model pages
- Tier 2: The Information, MIT Technology Review, Ars Technica (for AI), Bloomberg Tech
- Tier 3: Reputable AI-focused press, research paper blogs from major labs
- Tier 4: GitHub trending (for OSS momentum signal), HN discussion velocity (for developer adoption signal)

**Typical item count:** 2–4 items

**Max length per audience:**
- Greg: 350 words (35% weight; full technical depth)
- Nathan: 250 words (25% weight; customer and ecosystem framing)
- Mahesh: 200 words (20% weight; developer platform framing)
- Karan: 150 words (15% weight; strategic competitive framing)

**Confidence tag guidance:** Official lab announcements: `confirmed`. Research previews: `credible report`. Unconfirmed model capability claims: `weak signal`.

---

### Section 4.6 — Deals

**Purpose:** Track commercial momentum — customer wins, enterprise rollouts, procurement trends, and partner channel signals.

**Content types:**
- Named customer wins at hyperscalers (especially AI/cloud deals)
- Large enterprise cloud rollout announcements
- Government cloud procurement
- Procurement trend signals (preference shifts, multi-cloud adoption, price sensitivity)
- Partner channel activity and reseller signals

**Source tiers to use:**
- Tier 1 primary: Customer press releases, vendor case studies, earnings call commentary
- Tier 2: Bloomberg, WSJ, The Information for major deal reporting
- Tier 3: CloudWars (strong for deals), cloud trade press
- Tier 4: LinkedIn deal announcements may be surfaced if corroborated

**Typical item count:** 2–3 items

**Max length per audience:**
- Nathan: 250 words (25% weight; customer and partner framing)
- Mahesh: 200 words (20% weight; scale implications for infrastructure)
- Karan: 100 words (10% weight; financial and competitive framing)
- Greg: 80 words (minimal; only if AI platform implications)

**Confidence tag guidance:** Named customer in press release: `confirmed`. Reported deal from journalist: `credible report`. Rumored procurement: `weak signal`.

---

### Section 4.7 — Community Signal

**Purpose:** Surface developer sentiment, OSS momentum, and emerging grassroots signals before they reach mainstream press. This section is distinct from the other sections — it is explicitly a weak-signal layer, not a facts layer.

**Content types:**
- Hacker News top posts or hot discussions relevant to AI/cloud topics
- Reddit community sentiment shifts (r/MachineLearning, r/sysadmin, r/aws, r/googlecloud)
- GitHub trending repositories (velocity of stars, new AI tooling gaining adoption)
- Stack Overflow question volume trends on specific technologies

**Source tiers to use:**
- Tier 4 exclusively: HN Algolia API, Reddit API, GitHub trending API
- No Tier 1-3 sources should appear in this section (they belong in other sections)

**Typical item count:** 2–3 items

**Max length per audience:**
- Greg: 100 words (5% weight; developer pulse signal)
- Nathan: 80 words (selective; GitHub/OSS momentum only)
- Karan: Section omitted (`include_community_signals: false`)
- Mahesh: Section omitted (`include_community_signals: false`)

**Hardcoded rule:** No community post may be elevated to a top story or Executive Summary bullet without corroboration from a Tier 1–3 source.

**Confidence tag guidance:** All community signal items are tagged `weak signal` by default. Exception: if a GitHub repo crosses a defined velocity threshold (e.g., 1,000 new stars in 24 hours) it may be tagged `credible report` of momentum.

---

### Section 4.8 — OCI Implications

**Purpose:** Synthesize actionable implications for Oracle / OCI from the day's news. This is the most important section for converting intelligence into action. It appears at the end of every briefing and is always included.

**Content types:**
- Threat or opportunity flag: one clearly labeled item per significant story
- Watch item: something to monitor with a specific trigger condition defined
- Suggested internal follow-up: a concrete recommended action (e.g., "check with BD team on X deal," "assess power capacity in region Y")

**Source tiers:** Derived entirely from body section items. No independent sourcing.

**Typical item count:** 2–4 implication items

**Max length per audience:**
- All audiences: ~100 words (fixed; additive to `max_length`, not counted against it)

**Generation rules:**
- Every body section item must map to at least one OCI implication (tracked internally even if not all implications surface in the rendered section)
- The OCI Implications section surfaces the 2–4 highest-priority implications from the day
- Each implication must be labeled: `[THREAT]`, `[OPPORTUNITY]`, `[WATCH]`, or `[ACTION]`
- No implication may be a generic observation (e.g., "AI is growing"); must be specific and actionable

---

## 5. Scoring Model Specification

Every candidate article is scored before selection. The score determines which articles enter the daily canonical bundle and which are suppressed.

### 5.1 Score Formula

```
final_score = source_credibility
            + audience_relevance
            + novelty
            + momentum
            + strategic_impact
            + timeliness
            - duplication_penalty
```

All dimensions are normalized to a 0–10 scale before summing. The maximum possible `final_score` before penalty is 60. After deduplication penalty, minimum possible score is −10. The canonical bundle selects the top 20–40 items by score, subject to section diversity constraints (no section may represent more than 40% of the bundle).

---

### 5.2 Dimension Specifications

#### Dimension 1: Source Credibility

**Definition:** A static score reflecting the inherent trustworthiness and authority of the publishing source.

**Scoring range:** 0–10

**Computation:**

| Tier | Examples | Score |
|---|---|---|
| Tier 1 — Authoritative/Primary | Company press releases, earnings transcripts, SEC filings, official product blogs, regulatory filings | 9–10 |
| Tier 2 — High-quality journalism | Reuters, Bloomberg, WSJ, FT, CNBC, The Information | 7–8 |
| Tier 3 — Domain-specific media | CloudWars, The Register, Data Center Dynamics, Fierce Network, SemiAnalysis | 5–6 |
| Tier 4 — Community/sentiment | Hacker News, Reddit, GitHub trending, LinkedIn posts, TechCrunch | 2–4 |
| Unknown / unverified | No identifiable publisher | 0–1 |

**Implementation notes:**
- Source scores are stored in a static source registry table, keyed by domain
- New sources not in the registry receive a default score of 3 (Tier 4 equivalent) pending manual classification
- The source registry must be reviewed and updated monthly

---

#### Dimension 2: Audience Relevance

**Definition:** How closely the article matches the specific audience's profile — their topics, companies, geographic focus, and tone preferences.

**Scoring range:** 0–10

**Computation (weighted sub-components):**

| Sub-component | Weight | Method |
|---|---|---|
| Company name match | 35% | Named entity extraction; match against `companies_of_interest`; +1 point per matched company (max 3) |
| Topic taxonomy match | 30% | Map article topics to taxonomy; compare against `topics_of_interest` using keyword and embedding similarity |
| Embedding similarity | 25% | Cosine similarity between article embedding and a pre-computed "audience profile embedding" derived from profile fields |
| Geo focus match | 10% | Article geo tags vs. `geo_focus`; 0 if no geo overlap |

**Negative topic penalty:** If article matches any `negative_topics` item (keyword or embedding similarity above 0.7), apply a 30% reduction to the audience relevance score for that audience.

**Implementation notes:**
- Audience relevance is computed separately for each audience after shared scoring
- Embeddings use the same model as the novelty and deduplication pipeline (OpenAI text-embedding-3-large or equivalent)
- Profile embeddings are pre-computed at profile load time and refreshed when profile is updated

---

#### Dimension 3: Novelty

**Definition:** How different is this item from stories already delivered in the past 7 days?

**Scoring range:** 0–10 (10 = completely new; 0 = exact duplicate)

**Computation:**

1. Retrieve all story clusters sent in the past 7 days from the memory system
2. For each retrieved cluster, compute:
   - Embedding cosine similarity to the candidate article (headline + summary embeddings)
   - Entity overlap score (Jaccard similarity on extracted entities)
   - Event-type overlap (same event verb + same subject entity)
3. Take the maximum similarity score across all retrieved clusters
4. Map to novelty score: `novelty = 10 × (1 - max_similarity)`

**Thresholds:**
- `max_similarity > 0.90`: Item is a near-duplicate; `novelty = 0`; trigger deduplication pipeline
- `max_similarity 0.70–0.89`: Item is related to a prior story; check for fact delta; `novelty = 1–3`
- `max_similarity 0.40–0.69`: Item is topically related but substantively different; `novelty = 4–6`
- `max_similarity < 0.40`: Item is new; `novelty = 7–10`

---

#### Dimension 4: Momentum

**Definition:** Is this story gaining traction across multiple sources simultaneously? High momentum indicates the story is likely consequential.

**Scoring range:** 0–10

**Computation:**

| Signal | Points |
|---|---|
| Story covered by 2+ Tier 1–2 sources within 24 hours | +4 |
| Story covered by 3+ Tier 1–2 sources within 24 hours | +6 (not additive with above) |
| Story on HN front page (position ≤ 30) at time of ingestion | +2 |
| HN discussion thread above 100 comments | +1 |
| Reddit post above 500 upvotes in relevant subreddit | +1 |
| GitHub repo gaining >500 stars in 24h | +2 |
| LinkedIn post from named C-suite exec (verified) gaining >1,000 reactions | +1 |

**Cap:** Maximum momentum score is 10.

**Implementation notes:**
- Multi-source coverage is detected by clustering articles with high entity overlap (same story, different publishers)
- Community momentum signals are pulled from API at ingestion time; stored in the article metadata

---

#### Dimension 5: Strategic Impact

**Definition:** Does this story directly affect OCI's competitive position, supply chain, power/capacity, multicloud strategy, model ecosystem, or commercial motion?

**Scoring range:** 0–10

**Computation:** A rubric-based score computed by the LLM classification step, with the following criteria:

| Impact Category | Score Range | Examples |
|---|---|---|
| Direct OCI threat or opportunity | 8–10 | Competitor launches product that directly overlaps OCI service; major OCI customer announced switching to competitor |
| Adjacent competitive signal | 5–7 | New hyperscaler partnership that may affect OCI ecosystem; power constraint that affects all cloud providers |
| Background market context | 2–4 | General AI infrastructure investment trends; macro cloud market sizing |
| Tangential or low-relevance | 0–1 | Consumer AI app launches; unrelated tech industry news |

**Implementation notes:**
- Strategic impact is scored by an LLM call during the story intelligence layer step
- The LLM receives: article summary, entity list, and a system prompt describing OCI's strategic priorities
- The output is a structured JSON object: `{"score": int, "category": str, "rationale": str}`
- The rationale is stored for audit and debugging; not shown to the executive reader

---

#### Dimension 6: Timeliness

**Definition:** How recent is the article? Fresh news is generally more actionable than older news.

**Scoring range:** 0–10

**Computation:**

| Publication age | Base score | Notes |
|---|---|---|
| 0–6 hours old | 10 | Recency boost |
| 6–24 hours old | 8 | Standard fresh content |
| 1–2 days old | 6 | Still highly eligible |
| 2–4 days old | 4 | Eligible if high strategic impact |
| 4–7 days old | 2 | Eligible only if follow-up context or very high strategic impact |
| >7 days old | 0 | Ineligible unless major ongoing story with confirmed new development |

**Adjustment for `time_horizon`:**
- `near_term` profiles: timeliness weight multiplied by 1.3 (recency matters more)
- `near_to_mid_term` profiles: timeliness weight unchanged
- `near_to_long_term` profiles: timeliness weight multiplied by 0.8 (slightly more tolerance for older trend pieces)

---

#### Dimension 7: Duplication Penalty

**Definition:** Reduces score for items that are near-duplicates of recently delivered stories, scaling with degree of overlap.

**Scoring range:** 0–10 (subtracted from total)

**Computation:**

| Condition | Penalty |
|---|---|
| Novelty score = 0 (near-exact duplicate, no fact delta) | 10 (full suppression) |
| Novelty score 1–3 (related story, fact delta detected) | 3 (render as follow-up with reduced score) |
| Novelty score 4–6 (topically related, substantively different) | 1 |
| Novelty score 7–10 (new story) | 0 |

**Hard suppression rule:** Any item with `duplication_penalty = 10` is removed from the candidate pool entirely regardless of other scores. It is logged to the suppression log with reason `duplicate_no_delta`.

---

## 6. Content Deduplication Requirements

### 6.1 Overview

The deduplication pipeline is the most critical correctness requirement of the system. An executive who reads the same story twice loses trust in the briefing. The 5-step pipeline described below ensures no story is repeated within a 7-day rolling window unless it contains materially new information.

### 6.2 The 5-Step Deduplication Pipeline

#### Step 1: Normalize

Extract structured fields from each incoming article:

**Entities to extract:**
- Companies (NER: ORG)
- Products and services (NER: PRODUCT + custom taxonomy)
- Named executives (NER: PERSON + role validation)
- Regions and locations (NER: GPE + LOC)
- Dates and time references (NER: DATE)
- Numbers: financial figures, capacity figures, headcount
- Event verbs: `launched`, `partnered`, `raised`, `expanded`, `delayed`, `sued`, `announced`, `shipped`, `closed`, `acquired`, `signed`, `cancelled`, `confirmed`, `denied`

**Output:** A structured `normalized_article` object with all extracted fields plus:
- `headline_embedding` (vector)
- `summary_embedding` (vector)
- `fact_signature` (hash of key structured fields; used for exact-match dedup)

**Implementation notes:**
- Use spaCy or similar NER library for entity extraction
- Custom product taxonomy for OCI, AWS, Azure, GCP products maintained as a lookup table
- Normalization must be idempotent — running twice on the same article produces identical output

---

#### Step 2: Cluster into a Canonical Story

Group multiple articles that describe the same underlying event into a single story cluster.

**Clustering criteria:** Two articles belong to the same cluster if:
- Embedding similarity (headline + summary) > 0.85, OR
- Entity overlap (Jaccard) > 0.60 AND event verb matches, OR
- Same URL (canonical dedup), OR
- Same `fact_signature` (exact structural match)

**Story cluster object:**
```typescript
interface StoryCluster {
  story_id: string;           // UUID, stable across updates
  canonical_headline: string; // Best headline selected from cluster
  event_type: string;         // Derived from dominant event verb
  entities: Entity[];         // Union of entities across cluster
  first_seen_at: timestamp;
  last_updated_at: timestamp;
  source_count: number;       // Number of articles in cluster
  delivered_at: timestamp[];  // When this cluster was included in briefings
  fact_snapshot: FactDelta;   // Current known facts (see 6.3)
  status: "new" | "candidate_duplicate" | "follow_up" | "suppressed";
}
```

**Example clustering:** "OpenAI and Oracle expand AI data center", "Oracle/OpenAI Abilene site grows", and "Texas AI campus financing talks shift" should all merge into one evolving `StoryCluster` if they describe the same core event (same entities, same location, same deal).

---

#### Step 3: Compare with Sent Items from Last 7 Days

For each new item (or story cluster), compare against all story clusters delivered in the past 7 days:

**Comparison signals:**
- Embedding cosine similarity (headline embedding vs. stored cluster embeddings)
- Named entity overlap (Jaccard similarity on company + product + location entities)
- Event-type overlap (same event verb applied to same subject entity)
- Location identity (same physical site, same region)
- Deal identity (same deal, same parties)
- Product identity (same product name + same announcement type)

**Decision:**
- If any comparison signal exceeds its threshold, mark the incoming cluster as `candidate_duplicate`
- Log the matched prior cluster ID and similarity scores

**Similarity thresholds:**
- Embedding similarity > 0.85: `candidate_duplicate`
- Entity Jaccard > 0.70 + event-type match: `candidate_duplicate`
- Entity Jaccard > 0.85 (regardless of event verb): `candidate_duplicate`

---

#### Step 4: Detect Whether It Is a True Follow-Up

For each `candidate_duplicate`, evaluate whether it contains materially new information using the fact delta model.

**Fact delta data model:**

```typescript
interface FactDelta {
  capacity_mw?: number;       // Power or compute capacity in megawatts
  customer_name?: string;     // Named customer (previously unnamed or new customer)
  deal_size?: number;         // Financial value of a deal in USD
  model_name?: string;        // Specific AI model name
  partner_name?: string;      // Named partner (new or changed)
  region?: string;            // Geographic location (new or changed)
  date?: string;              // Timeline date (new or changed)
  status?: string;            // Status change (e.g., "rumored" → "confirmed", "announced" → "closed")
}
```

**A `candidate_duplicate` qualifies as a follow-up if:**
- Any `FactDelta` field is newly populated (was null in prior cluster, now has a value), OR
- Any `FactDelta` field has changed value from the prior cluster, OR
- A new named entity appears that was not in the prior cluster (new customer named, new partner added), OR
- The article contains an official confirmation or denial of something previously reported as unconfirmed

**Examples of valid follow-up signals:**
- New capacity number revealed (e.g., prior story said "large campus"; new story says "200MW campus")
- Customer named (prior story: unnamed government agency; new story: Department of Defense confirmed)
- Financing closed (prior: rumored financing; new: deal closed at $4B)
- Timeline changed (prior: "expected 2025"; new: "delayed to Q3 2026")
- Deal value revealed (prior: undisclosed terms; new: $500M multi-year deal)
- Partner list expanded (prior: 2 partners; new: 3rd partner added)
- Outage update (prior: "outage reported"; new: "outage resolved after 4 hours")
- Geographic expansion (prior: US datacenter; new: EU site announced for same initiative)

**If no fact delta is detected:** Mark as `status: suppressed`. Log to suppression log with reason and matched prior cluster ID.

---

#### Step 5: Render as Follow-Up

Items passing the follow-up check are rendered with explicit follow-up labeling. They must not appear as new, standalone stories.

**Follow-up rendering rules:**
- Prepend a follow-up label to the headline: `[UPDATE]`, `[FOLLOW-UP]`, or `[NEW DETAIL]`
- Include a one-sentence reference to prior coverage: "Previously reported: [canonical headline of prior cluster]"
- LLM summary prompt should focus on the delta: "What is new in this story that was not previously known?"
- Follow-up items receive a reduced novelty score (see Section 5) but are not suppressed

**Suppression log fields:**
```typescript
interface SuppressionLogEntry {
  article_id: string;
  story_cluster_id: string;
  matched_prior_cluster_id: string;
  suppression_reason: "duplicate_no_delta" | "below_score_threshold" | "section_budget_exceeded";
  similarity_score: number;
  scored_at: timestamp;
  briefing_date: string;
}
```

**Suppression log retention:** 30 days. Used for debugging, model calibration, and editorial review.

---

## 7. Editorial Rules & Content Governance

### 7.1 Hardcoded Rules (Cannot Be Disabled by Profile)

The following rules apply unconditionally to all briefings regardless of audience profile settings:

1. **Source label required:** Every item must display its source publication and a link to the original article. Source label format: `[Source Name, Publication Date]`. No anonymous sourcing in rendered content.

2. **No community post as top story:** No item sourced exclusively from Tier 4 (HN, Reddit, GitHub, LinkedIn) may appear in the Executive Summary or as the first item in any section. Community posts must be corroborated by a Tier 1–3 source to be promoted beyond the Community Signal section.

3. **No duplicate in 7 days without fact delta:** The deduplication pipeline enforces this. Any article that passes with `status: candidate_duplicate` and no detected fact delta must be suppressed. This rule cannot be overridden by any scoring signal.

4. **OCI implication required:** Every rendered body section item must have an "OCI implication" annotation generated by the LLM. If the LLM cannot generate a meaningful OCI implication for an item, the item is ineligible for the briefing.

5. **Max word count enforced:** The rendering engine must enforce the `max_length` per audience. If the scored items exceed the budget, items are removed in ascending score order until the budget is met.

6. **Cross-audience story wording:** One major story may appear across multiple audience briefings, but the LLM must generate distinct summaries for each audience using the audience's tone and framing. Identical text blocks across audiences are not allowed.

7. **Track everything suppressed:** The suppression log must capture every article that was scored but not rendered, with reason. This is required for model calibration and editorial review.

8. **Avoid social buzz overfitting:** Items with high momentum scores driven exclusively by community signal (Tier 4 only) without Tier 1–3 corroboration receive a forced `strategic_impact` cap of 4/10.

9. **Primary source preference:** When multiple articles cover the same story, the version closest to the primary source (Tier 1) is preferred for summary generation. The Tier 1 source is cited; secondary sources are noted as "also covered by."

---

### 7.2 Confidence Tags

All items are tagged with a confidence level at ingestion. The tag is used internally for scoring and in the rendered briefing for reader transparency.

| Tag | Definition | Rendering |
|---|---|---|
| `confirmed` | Fact stated in a Tier 1 primary source (official announcement, SEC filing, earnings transcript) | No special label in rendered output (assumed baseline) |
| `credible report` | Fact reported by Tier 2 journalism with named sources; not yet officially confirmed | Rendered as: *(Credible report — not officially confirmed)* |
| `weak signal` | Fact from Tier 4 source, or speculation from any tier, or analyst forecast | Rendered as: *(Weak signal — treat as directional)* |
| `follow_up` | Item is a follow-up to a previously covered story with new fact delta | Rendered with `[UPDATE]` prefix and prior coverage reference |

**Tag assignment rules:**
- Tags are assigned during the story intelligence layer step
- The LLM assigns the initial tag; it may be overridden by source tier lookup (e.g., if source is Tier 1, tag is always at least `credible report`)
- `weak_signal` items are only rendered for audiences where `include_speculative_analysis` is `moderate` or `full`
- All four tags are stored in the canonical bundle; filtering by audience happens at render time

---

### 7.3 Community Post Validation Rules

Community signal items require additional validation before appearing in any briefing:

1. A Hacker News post must be in the top 30 of the front page at time of ingestion, OR have >100 comments, OR have been cited or linked in a Tier 2 article
2. A Reddit post must have >500 upvotes in a relevant subreddit (defined list: r/MachineLearning, r/aws, r/googlecloud, r/sysadmin, r/artificial, r/LocalLLaMA)
3. A GitHub repository must have >1,000 total stars AND >200 new stars in the past 24 hours to qualify as a signal item
4. LinkedIn posts are only eligible if from a verified C-suite executive at a company in any audience's `companies_of_interest` list AND have >1,000 reactions
5. All community signal items are automatically tagged `weak signal` unless independently corroborated

---

## 8. Delivery Requirements

### 8.1 Email Delivery (P0 — Must-Have at Launch)

**Delivery method:** HTML email via Postmark transactional email API.

**Schedule:** Daily at 6:00 AM in each recipient's local timezone. Default timezone is US/Eastern. Timezone per recipient is configurable in the audience profile.

**Email format requirements:**
- Responsive HTML email template (renders correctly on mobile and desktop email clients)
- Plain-text fallback required (stripped version of content for non-HTML clients)
- Subject line format: `OCI Intelligence Brief — [Day, Month Date]` (consistent for inbox filtering)
- Preview text (preheader): The first Executive Summary bullet, truncated to 100 characters
- Sender name: `OCI Intelligence Brief` from a dedicated sending address (e.g., `brief@oci-intel.oracle.com`)
- Unsubscribe link required (CAN-SPAM compliance)

**Postmark configuration:**
- Use Postmark's Message Streams for transactional email
- Enable open tracking (Postmark pixel) on all emails
- Enable click tracking on all links
- Store Postmark message IDs in the delivery log for event correlation

**Tracking links:**
- Every story link must be replaced with a unique per-audience, per-story tracking URL
- Tracking URL format: `https://track.oci-intel.oracle.com/c/{tracking_id}`
- The tracking redirect endpoint logs the click event and redirects to the canonical article URL
- Tracking URL parameters stored: `audience_id`, `briefing_date`, `section`, `story_id`, `source`, `position_in_email`
- Bitly short links may be used as an alternative redirect layer for visual cleanliness in email rendering

**Feedback controls (inline in email):**
- Each story item includes micro-feedback links: `[Useful]` | `[Not useful]` | `[Too repetitive]`
- Each story item includes a simple `[More like this]` / `[Less like this]` link pair
- Feedback clicks are tracked through the same tracking URL infrastructure
- Feedback events are stored separately from click events in the analytics database

---

### 8.2 Web Archive Copy (P0)

**Requirement:** Every briefing rendered for every audience must be saved as a static HTML page and stored in object storage (OCI Object Storage bucket).

**Naming convention:** `briefings/{audience_id}/{YYYY-MM-DD}/index.html`

**Purpose:**
- Provides a web-accessible archive link that can be shared in Slack or other channels
- Serves as the canonical record for auditing and debugging briefing content
- Enables future web archive search functionality

**Access control:** Archive pages should be access-controlled; not publicly accessible. Direct link access with a signed URL is acceptable for V1.

---

### 8.3 Slack / Chat Delivery (P1 — Post-Launch)

**Requirement:** A condensed version of the Executive Summary (3 bullets + OCI implication) formatted for Slack block kit, deliverable to a designated private Slack channel per audience.

**Not required at launch.** Architecture should be designed to support this as an output format without significant refactoring (i.e., the rendering layer should be pluggable).

---

### 8.4 Scheduling and Triggers

**Primary trigger:** Daily cron job at 5:00 AM (pipeline start; briefing delivered by 6:00 AM)

**Pipeline execution sequence:**
1. 5:00 AM — Ingestion runs (RSS, crawlers, community APIs)
2. 5:15 AM — Normalization and entity extraction
3. 5:25 AM — Story clustering and deduplication
4. 5:35 AM — Scoring (all dimensions)
5. 5:45 AM — Audience-specific selection and ranking
6. 5:50 AM — LLM generation (summaries, OCI implications, executive summary)
7. 5:58 AM — Rendering (HTML email + web archive)
8. 6:00 AM — Email delivery via Postmark

**Error handling:** If the pipeline fails before LLM generation, send an alert to the system operator. Do not send a partial or empty briefing. A configurable fallback allows sending the prior day's briefing with a "data unavailable" notice in extreme cases (this must be explicitly enabled by an operator).

---

## 9. Feedback & Analytics Requirements

### 9.1 Email Metrics

Tracked via Postmark event API (webhooks or polling):

| Metric | Definition |
|---|---|
| Delivered | Email accepted by recipient mail server |
| Bounced | Email rejected by recipient mail server (hard or soft bounce) |
| Opened | Postmark open event (pixel fire) |
| Unique opens | Deduplicated opens per recipient per briefing |
| Clicked | Any tracked link clicked |
| Unique clicks | Deduplicated clicks per recipient per briefing |
| CTR | Unique clicks / Delivered |
| Click-to-open rate | Unique clicks / Unique opens |

All email metrics are stored per `(audience_id, briefing_date)` tuple.

---

### 9.2 Content Metrics

Tracked via the click tracking layer:

| Metric | Definition |
|---|---|
| Top clicked section | Which section has the highest unique click rate across all audience members |
| Top clicked story | Which specific story_id has the highest click count |
| Reading depth proxy | Ratio of links clicked to total links in the briefing (used as a reading depth signal) |
| Repeated clicks on same topic | Same audience member clicking multiple stories in the same topic cluster across multiple briefings |
| No-click streak by user | Number of consecutive briefings with zero clicks from a specific audience member |

Content metrics are stored per `(story_id, section, audience_id, briefing_date)`.

---

### 9.3 Personalization Metrics

Derived from aggregated click and feedback data:

| Metric | Definition |
|---|---|
| Topic click affinity | For each audience member, aggregate click rate by topic tag over rolling 30 days |
| Source affinity | Click rate by source tier and specific publication per audience member |
| Preferred article length | Average word count of clicked items vs. non-clicked items per audience member |
| Preferred time of delivery | Future: correlates open time with time-of-day to recommend optimal send time |

Personalization metrics feed back into the audience profile scoring as learned signals in P1 (not required at launch).

---

### 9.4 Explicit Feedback Controls

**In-email controls per story:**
- `[Useful]` — positive signal; increases `audience_relevance` score for similar future items
- `[Not useful]` — negative signal; decreases score for similar future items
- `[Too repetitive]` — specific signal for deduplication calibration
- `[More like this]` — topic affinity signal; similar to `topics_of_interest` positive update
- `[Less like this]` — topic aversion signal; similar to `negative_topics` update

**Simple thumbs up/down fallback:** A thumbs up / thumbs down per story is the minimum viable feedback control for launch. The five-option set above is P1.

**Feedback data model:**
```typescript
interface FeedbackEvent {
  audience_id: string;
  story_id: string;
  briefing_date: string;
  feedback_type: "useful" | "not_useful" | "too_repetitive" | "more_like_this" | "less_like_this" | "thumbs_up" | "thumbs_down";
  section: string;
  clicked_at: timestamp;
  source_ip_hash: string;  // Hashed for privacy; used for dedup only
}
```

**Feedback application:** V1 — Feedback is stored and reported. V2 — Feedback directly adjusts audience profile weights and scoring parameters (requires A/B testing framework).

---

## 10. Success Metrics & KPIs

### 10.1 30-Day Targets (Baseline Establishment)

| KPI | Target | Measurement method |
|---|---|---|
| Email open rate | >70% | Postmark open events / delivered |
| Click-through rate | >20% | Unique clicks / delivered |
| Delivery success rate | >99% | Delivered / attempted |
| Pipeline on-time delivery | >95% | Briefing delivered by 6:00 AM ±5 min |
| Deduplication accuracy | >85% | Manual audit of 5 random briefings; count repeated stories |
| OCI implication coverage | 100% | Every rendered item has an OCI implication (automated check) |
| Source label coverage | 100% | Every item has a source label (automated check) |

### 10.2 60-Day Targets (Engagement Validation)

| KPI | Target | Measurement method |
|---|---|---|
| Email open rate | >75% | Postmark |
| Click-through rate | >25% | Tracking URLs |
| Click-to-open rate | >35% | CTR / open rate |
| Top section identification | At least 1 dominant section per audience | Content metrics aggregation |
| Feedback response rate | >20% (at least 1 feedback click per 5 briefings per person) | Feedback event count |
| No-click streak | No audience member with >5 consecutive no-click briefings | Content metrics |
| Deduplication accuracy | >90% | Manual audit + suppression log review |

### 10.3 90-Day Targets (Quality and Relevance)

| KPI | Target | Measurement method |
|---|---|---|
| Email open rate | >80% | Postmark |
| Click-through rate | >30% | Tracking URLs |
| Audience relevance score | >4.0/5.0 (from explicit feedback) | Feedback event aggregation |
| Useful/Not useful ratio | >4:1 | Feedback events |
| "Too repetitive" feedback rate | <5% of all feedback events | Feedback events |
| Section diversity | No single section >50% of all clicks across all audiences | Content metrics |
| Suppression log accuracy | >90% of suppressed items would have been duplicates (spot audit) | Manual editorial review |
| Personalization delta | Topic affinity click rate improves >15% vs. day-1 baseline | Personalization metrics |

---

## 11. Feature Prioritization

### P0 — MVP Must-Have (Required at Launch)

These features are required for the system to be usable. Launch is blocked if any P0 item is incomplete.

| Feature | Description |
|---|---|
| Ingestion pipeline | RSS feed polling, source crawlers for Tier 1–3 sources, HN/Reddit API fetchers |
| Normalization | Entity extraction (NER), canonical URL, publisher metadata, timestamps |
| 7-day deduplication | All 5 pipeline steps: normalize → cluster → compare → detect follow-up → render as follow-up |
| Scoring engine | All 7 dimensions: source credibility, audience relevance, novelty, momentum, strategic impact, timeliness, duplication penalty |
| Audience profiles | All 4 executive profiles (Karan, Nathan, Greg, Mahesh) with schema-conformant configuration |
| Profile schema validation | All 10 schema fields validated at load time with explicit error messages |
| 8 briefing sections | All sections defined with source mapping, content types, and per-audience length budgets |
| LLM generation | Headline, 2–4 sentence summary, OCI implication, audience-specific tone |
| Confidence tags | All 4 tags assigned and rendered appropriately |
| Source labels | Every item has source label and original URL |
| Editorial rules enforcement | All 9 hardcoded rules checked before render |
| HTML email delivery | Via Postmark with open tracking and click tracking |
| Web archive copy | Static HTML saved to object storage |
| Tracked links | Per-audience, per-story tracking URLs |
| Suppression log | All suppressed items logged with reason |
| Daily cron schedule | Pipeline runs daily at 5:00 AM with email delivery by 6:00 AM |
| Basic feedback controls | Thumbs up / thumbs down per story (minimum viable) |
| Email metrics | Open, click, CTR tracked via Postmark and stored |

### P1 — Launch Plus (Target: 30–60 days post-launch)

These features significantly improve the product but are not required for initial delivery.

| Feature | Description |
|---|---|
| Full feedback controls | Five-option feedback (Useful / Not useful / Too repetitive / More like this / Less like this) |
| Feedback-driven profile updates | Explicit feedback adjusts audience scoring weights |
| Personalization metrics dashboard | Topic affinity, source affinity, article length preference per audience |
| Slack/Chat delivery | Condensed executive summary format for Slack channels |
| Source registry management UI | Admin interface to classify new sources and set tier scores |
| Newsletter email parser | Ingest paid newsletters via email forwarding |
| Content metrics reporting | Top sections, top stories, reading depth proxy |
| No-click streak alerting | Alert if an audience member has >5 consecutive no-click briefings |
| A/B section ordering | Test different section orders per audience to optimize CTR |
| Section diversity enforcement | Automated check preventing single section from >40% of bundle |

### P2 — Nice to Have (Target: 60–90 days post-launch or later)

These features enhance the product but depend on P0 and P1 being stable.

| Feature | Description |
|---|---|
| Optimal send-time per audience | Correlate open times to identify each executive's ideal delivery window |
| SemiAnalysis integration | Paid source; evaluate ROI before building |
| LinkedIn post monitoring | C-suite executive signal tracking |
| Audience profile self-service | Let executives adjust their own topic preferences via a web interface |
| Briefing web archive search | Search past briefings by topic, company, date |
| Multiple audience support | Add additional OCI executives beyond the initial four |
| Learned topic affinity model | Replace static profile weights with ML-derived weights from click history |
| Multi-language source support | Ingest non-English sources (Japanese, German, French cloud press) |
| Executive Summary audio version | Text-to-speech audio briefing as an optional email attachment |
| Source reliability tracking | Track prediction accuracy of sources (did rumored stories come true?) over time |

---

## 12. Open Questions with Recommendations

### Question 1: Search Engine — What powers news discovery?

**Original question:** "Search engine?"

**Context:** The briefing needs to discover relevant articles daily across a large, varied source universe. The choice of search/discovery infrastructure affects both coverage quality and operational cost.

**Recommendation:** Use a layered approach:

**Primary layer — RSS + direct source polling** for Tier 1 and Tier 2 sources. RSS is free, reliable, and provides near-real-time coverage for the most important sources (Reuters, Bloomberg RSS where available, official company blogs, SEC EDGAR RSS, utility press release RSS). Build a source registry table of RSS endpoints, crawl frequency (every 30 min for Tier 1; every 2 hours for Tier 2), and associated source tier. This should cover 70–80% of the relevant content.

**Secondary layer — Web/news search API** for discovery and gap-filling. Use Exa.ai or Brave Search API (both support fresh content search) as the primary discovery tool for Tier 2–3 sources not available via RSS, and for breaking news not yet in RSS feeds. Run daily queries per topic cluster (e.g., "oracle cloud competitor datacenter 2026") and score results through the ingestion pipeline. Bing News API is a fallback option.

**Community layer — dedicated APIs.** HN Algolia API (free, no rate limit concern), Reddit API (register an app; PRAW library), GitHub REST API for trending repos (approximated via stars velocity endpoint).

**Newsletter layer** — For private newsletters (e.g., SemiAnalysis), set up a dedicated email address that forwards to a parser. Use a service like Zapier or a custom inbound email webhook (Postmark supports inbound email) to ingest newsletter content.

**Do not** build a web scraper-first architecture. RSS and search APIs are more reliable, more scalable, and less likely to be blocked. Scraping should be reserved for the small number of high-value Tier 1 sources that do not publish RSS (specific utility commission websites, some regulatory databases).

---

### Question 2: How to deliver customized content based on audience?

**Original question:** "How to deliver customized content based on audience"

**Recommendation:** Implement the two-stage renderer described in the brief, with the following concrete architecture:

**Stage 1 — Common editorial bundle:** Run the full pipeline once daily. Output: a JSON bundle of 20–40 scored story objects, each with full metadata (scores, entities, confidence tags, OCI implications, per-audience summaries).

**Stage 2 — Audience-specific selection and rendering:** For each audience, run a selection function that filters the bundle by:
1. Section weight map (select top N items per section proportional to weights)
2. Topic and company filters (boost or suppress per `topics_of_interest` and `negative_topics`)
3. `include_community_signals` filter
4. `include_speculative_analysis` filter (suppress `weak signal` items if setting is `none` or `limited`)
5. `max_length` budget enforcement

Then pass the selected items to the LLM with an audience-specific system prompt that encodes the `preferred_tone`. The LLM generates audience-specific summaries — the same underlying facts rendered in different voices.

The rendering output is an audience-specific HTML email template populated with the selected and re-voiced content.

**Key implementation point:** Do not generate separate summaries for each audience from scratch. Generate one canonical summary, then re-voice it per audience. This halves LLM cost and ensures factual consistency across briefings.

---

### Question 3: What are the sources and how is credibility established?

**Original question:** "What are the sources, need credibility"

**Recommendation:** The source tier framework in Section 5.2 (Dimension 1: Source Credibility) provides the scoring model. For operational implementation:

**Build a static source registry** (Postgres table: `sources`) with fields: `domain`, `display_name`, `tier`, `credibility_score`, `rss_url`, `crawl_frequency`, `active`. Pre-populate with all sources listed in Section 4 (Briefing Section Specification) and the scoring section of the brief.

**For initial launch,** the following sources are hardcoded as Tier 1 (score 10):
- SEC EDGAR
- Oracle Newsroom / Oracle Blogs
- NVIDIA Newsroom
- All hyperscaler official newsrooms (AWS, Azure, Google Cloud, Meta Newsroom)
- OpenAI / Anthropic / Mistral official blogs
- FERC regulatory filings
- Utility commission press releases

**For credibility of unknown sources,** implement a heuristic: if a domain is not in the registry, default to Tier 4 (score 3) and flag for manual review. Add a source classification queue where new domains are reviewed weekly and assigned a tier.

**Do not** attempt to programmatically infer source credibility from domain metrics (PageRank, Moz score, etc.) — these are noisy signals. Manual tier assignment by a human editor reviewing the source list monthly is more reliable.

---

### Question 4: Implementation platform — OpenAI / ChatGPT + cronjob vs. OpenClaw?

**Original question:** "Implemented with Claude Code + cronjob or OpenClaw (preferrably claude code takes most of the token usage b/c paid by company)"

**Updated recommendation for this copy:** Build with OpenAI models accessed through Oracle Code Assist's Codex CLI, deployed as a scheduled Python application running on OCI Compute (or OCI Container Instances for easier management).

**Architecture:**
- **Orchestration:** Python application with APScheduler or a simple cron job on OCI Compute. A cronjob is operationally simpler than a full workflow engine for this use case.
- **LLM calls:** `codex exec` authenticated through Oracle Code Assist. All summarization, OCI implication generation, and strategic impact scoring go through OpenAI models surfaced through the Oracle-managed Codex configuration.
- **LLM cost optimization:** Run entity extraction, clustering, and scoring with lighter-weight models or rule-based systems. Reserve the stronger Codex/OpenAI profile for: (a) per-item summary generation, (b) OCI implication generation, (c) strategic impact scoring, and (d) executive summary generation.
- **Vector search:** Qdrant (open source, self-hosted on OCI) for semantic similarity. Alternatively, PgVector as a Postgres extension to reduce infrastructure complexity.
- **Storage:** Postgres (OCI Database) for canonical truth; OCI Object Storage for web archive HTML.

**Do not** use OpenClaw or any third-party workflow automation platform for the core pipeline — this adds complexity, latency, and cost without meaningful benefit for a pipeline of this scale. The system is a scheduled batch job, not a real-time pipeline.

---

### Question 5: How to get user feedback and data tracking?

**Original question:** "How to get user feedback? need some data tracking, like Click through rate, impression, etc."

**Recommendation:** Three-layer tracking system:

**Layer 1 — Postmark for email-level metrics.** Postmark provides open tracking (pixel) and click tracking (link rewriting) out of the box. Enable both in Postmark message stream settings. Use the Postmark webhook to push open/click events to the application database in near-real-time. Store in a `email_events` table: `(postmark_message_id, event_type, occurred_at, audience_id, briefing_date)`.

**Layer 2 — Custom tracking URLs for story-level metrics.** Every story link in every email is replaced with a unique tracking URL (`https://track.oci-intel.oracle.com/c/{tracking_id}`). The tracking endpoint (a simple web service) logs the click and issues a 302 redirect to the canonical article. This gives story-level, section-level, and position-level click attribution that Postmark's built-in click tracking cannot provide alone.

**Layer 3 — Feedback pixel URLs for explicit feedback.** Feedback controls (`[Useful]`, `[Not useful]`, etc.) are implemented as plain HTML links pointing to `https://track.oci-intel.oracle.com/f/{feedback_tracking_id}?type={feedback_type}`. The tracking endpoint logs the feedback event and returns a minimal "Thank you" response (or redirects to a confirmation page). No JavaScript required; works in all email clients.

**For V1 simplicity:** Postmark + custom tracking URLs is sufficient. Bitly can optionally be added as a link-shortening layer on top of the custom tracking URLs for visual cleanliness in the email, but it is not required.

---

### Question 6: How to implement the "no repetitive news in 7 days unless new info" rule?

**Original question:** "How to implement the No repetitive news in 7 days unless new info?"

**Recommendation:** The full specification is in Section 6 (Content Deduplication Requirements). For implementation guidance:

**Data infrastructure:**
- **Postgres** stores canonical story clusters with delivered-at timestamps. The 7-day window is a simple `WHERE last_delivered_at > NOW() - INTERVAL '7 days'` query.
- **Vector search (Qdrant or PgVector)** stores headline and summary embeddings for all delivered story clusters. ANN (approximate nearest neighbor) search retrieves the most similar past items for each new candidate in milliseconds.
- **Keyword/full-text search** (Postgres `tsvector`) provides a fast fallback for cases where embeddings may miss literal matches (e.g., exact company names, deal sizes).

**Implementation sequence:**
1. When a new article is ingested, compute its `headline_embedding` and `summary_embedding` using the same embedding model as stored clusters (consistency is critical — model changes require re-embedding all stored clusters)
2. Query Qdrant for the top-5 most similar stored cluster embeddings within the 7-day window
3. For each similar cluster above the 0.85 cosine similarity threshold, run the fact delta check against the stored `FactDelta` object
4. If no fact delta: suppress and log. If fact delta detected: approve as follow-up, update the cluster's `fact_snapshot`, render with follow-up label.

**Embedding model recommendation:** Use a single embedding model for the entire pipeline — OpenAI `text-embedding-3-large` (1,536 dimensions, good multilingual support) or Anthropic's embeddings if available. Do not mix embedding models; similarity comparisons are only valid within the same embedding space.

**Calibration:** The 0.85 cosine similarity threshold for `candidate_duplicate` is a starting estimate. Run a 2-week calibration period after launch where the editorial team manually reviews all suppressed items daily and flags false positives (suppressed items that should have been delivered) and false negatives (delivered items that were actually duplicates). Adjust the threshold based on observed precision/recall.

---

*End of Product Requirements Document*

*Document version 1.0 — authored 2026-03-10*
*Next review: 2026-04-10 or upon significant pipeline design changes*
