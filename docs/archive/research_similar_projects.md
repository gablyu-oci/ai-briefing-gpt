# Research Report: AI-Powered News Ranking, Scoring & Daily Briefing Systems

**Prepared:** 2026-03-11
**Scope:** Open-source repos, commercial tools, and techniques in the space of automated AI news aggregation with LLM-based scoring/ranking and briefing generation.

---

## Executive Summary

The "OCI AI Daily Executive Briefing" pipeline — fetching RSS, using Claude to score and rank stories, and generating audience-targeted HTML briefings — is doing something real and valuable. After surveying GitHub, HackerNews, and the broader web, the honest finding is: **there is no single open-source project that combines all of these concerns at a quality level that obviously surpasses what was built here.** Most open-source entries do one or two pieces well (RSS aggregation, or LLM summarization, or multi-agent orchestration) but lack the audience-segmentation angle and the editorial intentionality behind this project.

That said, there are meaningful techniques and libraries worth adopting, and a few production commercial tools worth understanding as competitive context.

---

## Top Relevant Repos and Tools

### 1. Horizon (Thysrael/Horizon)
**GitHub:** https://github.com/Thysrael/Horizon
**Stars:** 729 | **Language:** Python | **Active:** Yes (commits within hours as of research date)

**What it does:**
The most complete open-source analog to this project. A 7-stage automated pipeline: Fetch → Deduplicate → Score → Filter → Enrich → Summarize → Deploy. Supports Hacker News (with comment collection), RSS/Atom feeds, Reddit subreddits (with threads), Telegram channels, and GitHub release events — five source types vs. RSS-only here.

**Scoring approach:**
Sends each item to a configurable LLM (Claude, GPT-4, Gemini, DeepSeek, Doubao, or any OpenAI-compatible API) and rates it 0–10. Items below a configurable threshold (default: 6.0) are dropped. This is essentially the same scoring pattern as this project — naive LLM prompting per item.

**What it does better:**
- Cross-source deduplication (merges near-duplicate stories from RSS + HN + Reddit)
- Enrichment stage does web search for background context before summarizing
- Multi-provider LLM support (swap between Claude, GPT-4, Gemini without code changes)
- MCP server integration for programmatic control
- Email subscription via SMTP/IMAP
- Bilingual output (English + Chinese)
- Static site deployment via GitHub Actions

**What it lacks:**
No audience segmentation — it produces one unified briefing, not separate views for a CTO vs. CFO vs. business exec. No concept of "relevance to a specific organization or persona."

**Verdict:** Best open-source comparable. The enrichment web-search step before summarizing is worth borrowing. The multi-source architecture (Reddit + HN + Telegram alongside RSS) is more sophisticated.

---

### 2. News Minimalist (newsminimalist.com)
**GitHub:** Not open-source (commercial)
**HN Discussion:** 84 points, Jan 2025 | **URL:** https://www.newsminimalist.com/

**What it does:**
A commercial news aggregator where every story is rated on a 0–10 significance scale by GPT-4. Only high-scoring stories appear. The creator documented a key finding in the HN thread: **GPT-3 failed badly at significance scoring because it preferred "tragic, personal stories" and completely missed what makes news historically significant.** GPT-4 solved this — but only after careful prompt engineering to anchor what "significance" means (historical impact, not emotional salience).

**Why this matters:**
This is the most important documented insight for any LLM-based news ranking system. The naive prompt "rate this 0-10 for importance" systematically favors the wrong things. Prompts need to explicitly define: significance = long-term historical impact, not immediate tragedy or emotional weight. This is a known failure mode.

**Technique worth adopting:**
Explicitly define scoring rubrics in prompts. E.g., "10 = policy change, major product launch, scientific breakthrough with multi-year implications. 5 = notable but transient. 1 = human interest, tragedy without strategic relevance."

---

### 3. Perception (intent-solutions-io/perception-with-intent)
**GitHub:** https://github.com/intent-solutions-io/perception-with-intent
**Stars:** 5 | **Language:** Python + TypeScript | **Active:** Yes (v0.3.0, Nov 2025)

**What it does:**
The most architecturally similar project to what this pipeline aspires to be at scale. Eight specialized Vertex AI agents coordinated via Google's A2A Protocol: Root Orchestrator, Topic Manager, News Aggregator, Relevance Scorer, Article Analyzer, Daily Synthesizer, Validator, and Storage Agent. Targets executives explicitly, emphasizing "what matters" filtering and daily executive briefs highlighting patterns and emerging trends.

**Scoring approach:**
Multi-stage: RSS collection → keyword/category relevance scoring via LLM → Gemini 2.0 Flash for summaries, tags, and "strategic implications" → daily synthesis pass that identifies cross-story patterns.

**What it does better:**
The synthesis stage is notable: it doesn't just summarize individual stories, it runs a second LLM pass to identify cross-story themes and macro patterns — much closer to what an actual analyst would do.

**What it lacks:**
Audience segmentation into distinct executive personas. Costs ~$70/month on GCP for 100 articles/day. Requires full Google Cloud infrastructure (Cloud Run, Firestore, Vertex AI).

**Verdict:** Architecturally ambitious. The two-pass approach (article summary + cross-story synthesis) is worth studying for the generation stage.

---

### 4. Argus (satriapamudji/argus)
**GitHub:** https://github.com/satriapamudji/argus
**Stars:** 0 | **Language:** Python | **Active:** Yes (Feb 2026)

**What it does:**
A production-focused market news briefing pipeline for Telegram: ingest → score → enrich → bundle → generate → validate → publish. Uses PostgreSQL for persistence throughout. Publishes to Telegram via MarkdownV2.

**Scoring approach:**
Multiple versioned heuristic scorers (v1, v2, v3) run first, then LLM (via OpenRouter API) generates the final briefing from top-scored items. This is the most interesting scoring pattern found: **deterministic heuristics pre-filter before LLM is invoked**, reducing cost and improving consistency.

**What makes it interesting:**
- Versioned scoring algorithms (not just one LLM call)
- Risk gating: checks market calendars and headline sentiment before deciding whether to publish
- Multi-stream execution (US markets vs. crypto) with per-stream subscriptions
- 24–120 hour rolling windows depending on mode
- LLM output validation before publication (catches hallucinations/formatting errors)

**Verdict:** Small project but the heuristic-first + LLM-second scoring architecture is smarter than pure LLM scoring. Worth studying for hybrid scoring approaches.

---

### 5. Dr. Headline / HeadlineSquare (headlinesquare)
**HN Discussion:** April 2025 | **GitHub:** headlinesquare organization on GitHub

**What it does:**
An autonomous AI agent that writes, reasons through, and publishes fully sourced daily political news briefings — no human editorial control. Processes ~450 Reddit candidates daily through **25 sequential LLM-guided evaluation stages** using OpenAI o3-mini-high and Claude 3.7 Sonnet.

**Why this is remarkable:**
25 evaluation stages is the most sophisticated scoring pipeline found in this research. Each stage presumably eliminates, reweights, or annotates candidates with progressively refined criteria. This eliminates single-prompt bias — different evaluation angles (relevance, sourcing quality, novelty, impact) run as separate passes.

**Technique worth borrowing:**
Multi-stage evaluation rather than a single 0–10 score. Stage 1 might filter for topic relevance, Stage 2 for source credibility, Stage 3 for novelty vs. yesterday's briefing, Stage 4 for executive relevance, etc.

---

### 6. Multi-Agent AI Newsletter (felixggj/multi-agent-ai-newsletter)
**GitHub:** https://github.com/felixggj/multi-agent-ai-newsletter
**Stars:** 28 | **Language:** Python | **Framework:** CrewAI

**What it does:**
Uses CrewAI to orchestrate multiple specialized AI agents — each with a distinct role (researcher, writer, editor, etc.) — to retrieve news and generate newsletter content. Built with OpenAI + Serper API for web search.

**What's useful:**
Demonstrates the CrewAI pattern for news pipelines. Agents with distinct roles (researcher vs. editor vs. fact-checker) produce better output than a single monolithic prompt because each agent's system prompt is narrowly focused.

**Verdict:** Low stars and domain-specific (football), but the CrewAI agent-role pattern is worth understanding for future architecture evolution.

---

### 7. News Radar (lfarroco/news-radar)
**GitHub:** https://github.com/lfarroco/news-radar
**Stars:** 26 | **Language:** TypeScript/Deno | **Live:** dev-radar.com

**What it does:**
A five-stage pipeline (Scanner → Relevance Filter → Scraper → Writer → Publisher) that produces a static website. Most interesting feature: **the AI relevance filter runs before full-text scraping** — AI decides whether to invest the scraping cost based on title/snippet alone, then only approved items get scraped.

**What's useful:**
The lazy evaluation pattern: cheap filtering first, expensive processing only on survivors. Applied to this project: score on RSS title+summary first; only fetch full article text for stories that score above a threshold.

**Verdict:** Small project but the staged-cost architecture is a good pattern.

---

### 8. Folo / Follow (RSSNext/Follow)
**GitHub:** https://github.com/RSSNext/Follow
**Stars:** 37.6k | **Language:** TypeScript | **License:** AGPL-3.0

**What it does:**
The highest-starred RSS reader with AI capabilities found in this research. A full-stack cross-platform RSS reader (iOS, Android, macOS, Windows, Linux, web) with AI-powered translation, summarization, and daily digest generation. Built on top of RSSHub (42.5k stars) which converts non-RSS sources into RSS feeds.

**Relevance:**
Not a briefing generator — it's a reader. But the RSSHub ecosystem (42.5k stars) is the most complete collection of RSS adapters for non-RSS sources (Twitter/X, YouTube, Instagram, GitHub, Telegram, etc.). As this project expands its source list, RSSHub routes are worth considering.

**AI features:**
Timeline summarization and daily digest emails, but the exact LLM integration isn't publicly documented.

---

### 9. Feeds.fun (Tiendil/feeds.fun)
**GitHub:** https://github.com/Tiendil/feeds.fun
**Stars:** 347 | **Language:** Python (FastAPI) + Vue/TypeScript

**What it does:**
A self-hosted RSS reader that uses LLMs (OpenAI, Gemini) to auto-tag articles, then lets users define scoring rules against those tags. Example: "tag:kubernetes AND tag:security → score +5."

**Why this is interesting:**
Hybrid scoring: LLM does the semantic understanding (tagging), deterministic rules do the scoring. This separates concerns cleanly and makes the scoring system transparent and auditable. Users can see exactly why a story ranked high.

**Technique worth borrowing:**
LLM-generated tags as an intermediate representation, then rule-based scoring on tags. This is more predictable than end-to-end LLM scoring because the LLM's job is classification (bounded), not scoring (open-ended and drift-prone).

---

### 10. Nyan (NyanNyanovich/nyan)
**GitHub:** https://github.com/NyanNyanovich/nyan
**Stars:** 289 | **Language:** Python | **License:** Apache 2.0

**What it does:**
Aggregates posts from multiple Telegram channels, clusters similar posts using embeddings, and publishes a unified feed. Source credibility is managed by classifying channels into trustworthiness tiers.

**What's useful:**
The embedding-based deduplication/clustering approach is more semantically accurate than title-similarity hashing. Two stories about the same event with different headlines get merged. Also: **source credibility tiers** — not all sources are weighted equally, which is a missing concept in most simple aggregators.

**Technique worth borrowing:**
Embedding-based deduplication (using sentence-transformers or similar) rather than exact URL or title matching. Source credibility weighting as a scoring multiplier.

---

## Commercial Tools: Brief Survey

### Feedly (Leo AI)
**URL:** https://feedly.com
**Model:** SaaS, not open-source
**Relevant features:** ML models for reading pattern learning, topic tracking across millions of sources, "strategic insights" (summarized trend reports), threat intelligence feeds. Leo AI personalizes feeds based on click behavior over time — a feedback loop this project lacks.
**API:** Available but proprietary and paid.
**Takeaway:** The personalization feedback loop (what did the user actually click on?) is how Feedly improves ranking over time. A simple thumbs-up/down mechanism on generated briefings could enable similar learning.

### Perplexity (Discover / Daily)
**URL:** https://perplexity.ai
**Model:** Commercial, partially open through API
**Relevant features:** Real-time web search + LLM synthesis with citations. The "Discover" feed surfaces trending stories with multi-source synthesis. No audience segmentation.
**Takeaway:** The citation-grounded approach (every claim links to source) is more trustworthy than citation-free summaries. Worth adding source attribution to briefing stories.

### Event Registry (eventregistry.org)
**GitHub:** https://github.com/EventRegistry/event-registry-python (251 stars)
**Model:** Commercial API with free tier (30-day window)
**Relevant features:** Semantic concept extraction, cross-language news search, social engagement scoring ("socialScore"), sentiment analysis. Goes beyond RSS parsing to provide structured article metadata including named entities, topics, and sentiment.
**Takeaway:** If source diversity is a priority (non-English press, paywalled outlets), Event Registry's API is the most structured alternative to pure RSS. Free tier is limited but real.

---

## Key Patterns and Techniques Worth Adopting

### 1. Multi-Stage Scoring (vs. Single Prompt)
The Dr. Headline system's 25-stage evaluation and Argus's heuristic-first approach both point to the same lesson: **a single "rate this 0-10" prompt is unreliable and gameable**. Better architecture:

- Stage 1: Topic relevance filter (binary: in-scope vs. out)
- Stage 2: Novelty filter (is this genuinely new vs. covered yesterday?)
- Stage 3: Source quality weighting (tier-1 outlet vs. blog)
- Stage 4: Executive relevance (does this affect strategy/operations?)
- Stage 5: Final 0-10 score with explicit rubric

### 2. Explicit Scoring Rubrics (vs. Intuitive Rating)
The News Minimalist creator documented that GPT models systematically prefer emotional stories over historically significant ones without explicit rubric anchoring. The fix: define what each score means concretely in the prompt. This is the single most actionable finding in this research.

### 3. Heuristic Pre-filter + LLM Scoring
Argus uses versioned deterministic heuristics (keyword lists, source tier, recency) to pre-score and pre-filter, then invokes the LLM only for finalists. This reduces LLM API cost significantly on days with high feed volume and reduces model-induced variance.

### 4. Embedding-Based Deduplication
Most projects use URL matching or exact-title hashing for deduplication. Nyan and Horizon use semantic embeddings. When Reuters and AP both publish "OpenAI announces GPT-6" with different headlines, embedding similarity catches the duplicate; string matching doesn't.

### 5. LLM-Tag → Rule-Score Hybrid (Feeds.fun)
Instead of asking the LLM to produce a score directly, ask it to produce tags (semantic labels), then apply deterministic rules to tags. This makes the scoring system debuggable: you can see which tags fired and why a story ranked where it did.

### 6. Lazy Evaluation / Staged Cost
News Radar's pattern: use cheap signals (title, feed snippet) for initial filtering, only fetch and process full article text for items that survive. Applied here: score on RSS summary first (cheap), full-article analysis only for top-N candidates.

### 7. Two-Pass Generation (Per-Story + Cross-Story Synthesis)
Perception's two-pass approach: summarize individual articles in pass 1, then run a synthesis LLM call in pass 2 to identify cross-story themes, emerging trends, and macro patterns. This is what distinguishes a briefing from a list of summaries.

### 8. Source Credibility Weighting
Nyan tiers its Telegram sources by trustworthiness. The same concept applies to RSS: a Reuters article about AI regulation should score higher than a random AI-hype blog article on the same topic, independent of LLM scoring.

---

## Libraries Worth Evaluating

### trafilatura (adbar/trafilatura)
**Stars:** 5.5k | **PyPI:** `trafilatura`
The current stack uses BeautifulSoup for article content extraction. Trafilatura consistently outperforms in independent benchmarks (best single tool by ROUGE-LSum, 2023; used by HuggingFace, IBM, Microsoft Research). It handles metadata extraction (title, author, date), full-text extraction, and feed discovery in one package. Version 2.0.0 released Dec 2024 — actively maintained. Worth replacing BeautifulSoup for full-text extraction.

### newspaper4k
**PyPI:** `newspaper4k` | Version: 0.9.5 (Feb 2026)
The actively maintained fork of the abandoned newspaper3k. Adds Google News integration, 80+ language support, and improved extraction accuracy (F1: 0.946 vs. newspaper3k's 0.910). Requires Python >=3.10. Worth evaluating alongside trafilatura.

### RSSHub
**Stars:** 42.5k | **Language:** TypeScript
Not a Python library — a self-hosted service that generates RSS feeds for sources without them (Twitter/X, YouTube, GitHub starred repos, LinkedIn, etc.). As the project's source list grows beyond traditional tech media, RSSHub routes would enable aggregating from GitHub trending, HN front page, Reddit, YouTube channels, and Telegram channels without per-source scrapers.

### feedparser
Already in use. The de-facto standard. ETag/Last-Modified conditional GET support (avoiding re-downloading unchanged feeds) is worth using if not already implemented.

### foorilla/allainews_sources
**Stars:** 389 | **GitHub:** https://github.com/foorilla/allainews_sources
A curated list of 150+ AI/ML/Data Science RSS feed URLs including TechCrunch, VentureBeat, The Verge, MarkTechPost, The Decoder, DeepMind, OpenAI, arXiv, Latent Space, and dozens of niche newsletters. Useful as a source expansion reference — organized by category with both website URL and RSS feed URL for each.

---

## Honest Assessment: Is Anything Clearly Better?

**No single open-source project is clearly better than what was built here end-to-end.** The combination of:
- RSS ingestion
- Claude-powered scoring
- Audience-segmented HTML output (different views for different executive personas)
- Scheduled pipeline execution

...does not exist in a polished, integrated form anywhere in the open-source ecosystem at the time of this research.

**What comes closest:** Horizon (729 stars) is the most complete single-repo analog, but lacks audience segmentation. Perception (5 stars) has the most sophisticated architecture for executive briefing, but requires full Google Cloud and costs ~$70/month.

**Where this project is behind:**

1. **Scoring sophistication:** A single LLM "score this 0-10" prompt is the weakest approach found. The multi-stage approach (Dr. Headline's 25 stages, or even a 4-stage funnel) would produce more reliable ranking. The Feeds.fun tag-then-rule-score hybrid is worth exploring.

2. **Deduplication:** If not using embeddings, the project is likely showing duplicates when multiple outlets cover the same story.

3. **Cross-story synthesis:** Most briefing systems generate per-story summaries. A second LLM pass to identify "the three themes that matter this week" would significantly elevate the executive value of the output.

4. **Source diversity:** Horizon ingests from HN (with comment sentiment), Reddit, Telegram, and GitHub releases in addition to RSS. The current RSS-only approach misses community signal (what engineers are actually discussing vs. what PR teams are publishing).

5. **Feedback loop:** None of the open-source projects solve this either, but commercial tools like Feedly improve ranking over time based on click behavior. Even a simple "thumbs up/down" on the HTML output that feeds back into scoring weights would be valuable.

**Where this project is ahead:**

- Audience segmentation (persona-specific views) — genuinely uncommon in the space
- Clean Python-native architecture without heavy infrastructure dependencies
- Claude OAuth integration (no API key management overhead)
- HTML output quality and design intentionality

The project is well-positioned relative to the open-source ecosystem. The highest-ROI improvements are: (1) multi-stage scoring with explicit rubrics, (2) embedding-based deduplication, and (3) a second-pass cross-story synthesis call.

---

## Reference Links

| Project | URL | Stars |
|---|---|---|
| Horizon | https://github.com/Thysrael/Horizon | 729 |
| News Minimalist | https://www.newsminimalist.com/ | — (commercial) |
| Perception | https://github.com/intent-solutions-io/perception-with-intent | 5 |
| Argus | https://github.com/satriapamudji/argus | 0 |
| Dr. Headline | https://github.com/headlinesquare | — |
| Multi-Agent Newsletter | https://github.com/felixggj/multi-agent-ai-newsletter | 28 |
| News Radar | https://github.com/lfarroco/news-radar | 26 |
| Folo/Follow | https://github.com/RSSNext/Follow | 37.6k |
| Feeds.fun | https://github.com/Tiendil/feeds.fun | 347 |
| Nyan | https://github.com/NyanNyanovich/nyan | 289 |
| hacker-news-digest | https://github.com/polyrabbit/hacker-news-digest | 745 |
| trafilatura | https://github.com/adbar/trafilatura | 5.5k |
| newspaper4k | https://pypi.org/project/newspaper4k/ | — |
| RSSHub | https://github.com/DIYgod/RSSHub | 42.5k |
| allainews_sources | https://github.com/foorilla/allainews_sources | 389 |
| Event Registry | https://github.com/EventRegistry/event-registry-python | 251 |
| Feedly Leo AI | https://feedly.com/leo | — (commercial) |

---

*Research conducted March 11, 2026. GitHub search, HackerNews Algolia API, and direct repository inspection.*
