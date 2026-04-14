# Deep Dive Capabilities for OCI AI Daily Executive Briefing

**Prepared:** 2026-03-11
**Scope:** Research into "deep dive" capabilities — going beyond RSS headline + summary aggregation to substantive, multi-source, contextually-enriched intelligence briefings
**Project context:** OCI AI Daily Executive Briefing — Python pipeline using Claude LLM via subprocess, feedparser RSS ingestion, scoring/ranking engine, HTML rendering for four Oracle Cloud executive audiences

---

## Table of Contents

1. [What "Deep Dive" Means in Practice](#1-what-deep-dive-means-in-practice)
2. [Full-Text Extraction: Libraries and Approaches](#2-full-text-extraction-libraries-and-approaches)
3. [Story Clustering and Cross-Reference](#3-story-clustering-and-cross-reference)
4. [Agentic Research Patterns](#4-agentic-research-patterns)
5. [Search APIs for Topic Expansion](#5-search-apis-for-topic-expansion)
6. [Community Signal Aggregation: Hacker News and Beyond](#6-community-signal-aggregation-hacker-news-and-beyond)
7. [What Leading Briefing Products Do for Depth](#7-what-leading-briefing-products-do-for-depth)
8. [Weekly Synthesis and Temporal Context](#8-weekly-synthesis-and-temporal-context)
9. [Feature Ranking: Value vs. Implementation Effort](#9-feature-ranking-value-vs-implementation-effort)
10. [Concrete Feature Designs with Implementation Sketches](#10-concrete-feature-designs-with-implementation-sketches)
11. [What Deep Dive Looks Like for OCI Executives Specifically](#11-what-deep-dive-looks-like-for-oci-executives-specifically)
12. [Recommended Phasing](#12-recommended-phasing)

---

## 1. What "Deep Dive" Means in Practice

The current pipeline operates at one level of depth: it fetches RSS feeds, reads the summary field (typically 150-400 words of feed-provided text), scores articles against audience weights, and asks Claude to rewrite each summary with an OCI lens. The pipeline never reads the actual article. It cannot compare what five outlets are saying about the same event. It has no memory of prior briefings to detect trends. And it never follows threads — a paper announcement, its GitHub repo, the Hacker News discussion, and subsequent analyst commentary are all invisible unless each happens to have its own RSS entry.

"Deep dive" should be understood as five distinct capability layers, each with increasing value and implementation complexity:

**Layer 1 — Full-text ingestion:** Reading the complete article body rather than the RSS excerpt. The current pipeline's summaries are what the publisher chose to put in their feed, which is often a teaser rather than the substance. Full-text gives Claude the complete facts, numbers, direct quotes, and context needed to write a genuinely informed briefing item.

**Layer 2 — Story clustering and synthesis:** Recognizing that five articles are all reporting on the same event and producing one synthesized item rather than five separate rows. Today the system would show five entries for the same AWS re:Invent announcement from Reuters, TechCrunch, Ars Technica, AWS Blog, and CloudWars — taking up five slots of the twelve per audience and giving each exec a false sense that this is five separate developments.

**Layer 3 — Thread following:** When a high-scoring article appears, automatically fetching related materials — the original research paper, the GitHub repo, the Hacker News discussion, prior analyst reports on the same company. This transforms a headline into a briefing package.

**Layer 4 — Historical contextualization:** Comparing today's articles against prior briefings stored in a persistent database to detect trend lines, repeat players, and escalating dynamics. "This is the third week in a row that Google has announced a new sovereign cloud region" is a different signal than treating each announcement in isolation.

**Layer 5 — Expert commentary aggregation:** Pulling in informed reactions — HN top comments, Reddit expert threads, analyst quotes — to give executives a sense of how the technical and investment communities are responding to a story, not just the journalist's framing.

---

## 2. Full-Text Extraction: Libraries and Approaches

### 2.1 Library Comparison

Based on the Scrapinghub article extraction benchmark and independent evaluations, the current state of Python article extraction libraries is:

| Library | F1 Score | Precision | Recall | Speed | Maintenance |
|---------|----------|-----------|--------|-------|-------------|
| trafilatura 2.0.0 | 0.958 | 0.938 | 0.978 | Fastest | Active |
| newspaper4k 0.9.3.1 | 0.949 | 0.964 | 0.934 | Slow | Active (fork) |
| readability-lxml 0.8.4.1 | 0.922 | 0.913 | 0.931 | Fast | Active |
| goose3 3.1.20 | 0.896 | 0.940 | 0.856 | Slow | Active |

**Recommendation: trafilatura as primary, readability-lxml as fallback.**

Trafilatura achieves the highest overall F1 (0.958), is the fastest library, is actively maintained, and handles metadata extraction (publish date, author, language) alongside content. It processes HTML 4.8x faster than news-please. The basic Python usage is minimal:

```python
from trafilatura import fetch_url, extract

downloaded = fetch_url(url, timeout=10)
if downloaded:
    text = extract(downloaded, include_comments=False, include_tables=True,
                   output_format="txt", with_metadata=True)
```

For speed-critical paths (bulk pre-fetching during ingestion), use `fast=True` which doubles throughput by skipping fallback heuristics.

For pages where trafilatura returns None or under ~200 words, fall back to readability-lxml, which tends to handle structured/CMS-heavy sites differently and has the "highest median score" in some benchmarks — the two approaches complement each other.

**Do not use newspaper3k.** It has not had a release since 2018. newspaper4k (the maintained fork) is acceptable as a third-tier fallback for its NLP extras (keyword extraction) but is significantly slower and should not be in the critical path.

### 2.2 Practical Integration Strategy

The current `ingest.py` fetches feeds with `feedparser` and stores RSS summaries. The cleanest integration for full-text is to add a post-ingest enrichment step (a new `enrich.py` module) that runs after ingestion and before scoring:

```
ingest_feeds() → enrich_full_text(top_N) → score_all_articles() → ...
```

Key design decisions for this enrichment step:

**Which articles to enrich:** Full-text fetching adds latency (1-3 seconds per article, or up to 15 seconds for slow sites). Do not enrich every article ingested — the current pipeline ingests from 15 RSS sources over a 48-hour window, potentially yielding 300+ articles. Enrich only the top-60 by initial keyword/timeliness score (the same set that gets classified). This keeps total enrichment time under 3 minutes with 10 concurrent workers.

**Caching:** Store extracted full text in the existing `output/.cache/` directory keyed by URL hash, identical to the current LLM cache pattern. Full text changes rarely once published; a 24-hour TTL is appropriate.

**Length management:** Full articles can be 3,000-8,000 words. Claude's context is not the bottleneck, but prompt cost is. For the summary generation prompts in `llm.py`, pass the first 2,500 words of extracted text (covering the full article for most news pieces) rather than the RSS summary. The `generate_summary()` prompt currently passes `article.get('summary', '')[:1200]` — this can be replaced with `article.get('full_text', article.get('summary', ''))[:2500]`.

**Failure handling:** Many sites block scrapers. Trafilatura's `fetch_url()` returns None on failure. The system should fall back gracefully to the RSS summary — adding a field `full_text_available: bool` to each article dict so downstream prompts know the quality of their input.

### 2.3 Paywall Handling

There are three legitimate approaches to paywalled content, ordered by practicality for this use case:

**1. Archive fallback via archive.org:** Trafilatura accepts `https://web.archive.org/web/*/ORIGINAL_URL` as input. For major outlets (Reuters, FT, Bloomberg), the Wayback Machine typically has a copy within hours. This can be implemented as a fallback: if direct fetch returns no content or the paywall pattern is detected, construct the archive URL and retry. Limitation: some very fresh articles (<6 hours old) may not be archived yet.

**2. Jina Reader API (r.jina.ai):** Simply prepend `https://r.jina.ai/` to any URL. Jina renders the page in a browser headless environment and returns clean, LLM-optimized Markdown. Free tier: 200 requests/minute with API key (20 req/min without). This works for many paywalled sites because Jina renders JavaScript and may bypass metered paywalls. Cost: token-based for the returned content. For a briefing pipeline extracting 60 articles/day, this is negligible.

**3. Accept incomplete extraction:** For hard paywalls (WSJ, FT, Bloomberg subscribers only), the RSS summary is often the maximum publicly accessible text. The system should accept this gracefully rather than engineering around paid content. The OCI briefing audiences have enterprise media subscriptions — a useful future enhancement is an email-forwarding ingestion pathway for newsletters and paywalled outlets (noted in the GAP_ANALYSIS.md as a P1 feature for SemiAnalysis).

### 2.4 Jina Reader vs. Firecrawl vs. Trafilatura

For this use case (daily briefing pipeline, ~60 articles/day, no JavaScript-heavy SPA sites):

- **Trafilatura (open source, no API cost):** Best for the 80% of articles on standard news sites. Zero API cost. Fastest.
- **Jina Reader (free/cheap API):** Best fallback for JavaScript-rendered pages and paywalled content. Minimal implementation (just prepend the URL prefix). Apache-2.0 licensed SDK.
- **Firecrawl (commercial):** Purpose-built for RAG pipelines, handles full crawls and complex SPAs. Overkill for article extraction from known news URLs. More appropriate if the system ever needs to crawl a company's press release page or documentation site.

**Recommendation for this project:** Use trafilatura as primary, Jina Reader API as fallback for pages where trafilatura returns under 200 words. Skip Firecrawl for now.

---

## 3. Story Clustering and Cross-Reference

### 3.1 The Problem

The current system treats every article as an independent item. When OpenAI releases GPT-5, the pipeline might ingest 8 articles — from Reuters, TechCrunch, Ars Technica, The Verge, VentureBeat, OpenAI Blog, AWS Blog (their model integration angle), and Azure Blog — and present them as eight separate briefing items. This is the single most trust-destroying behavior for executive consumers, and it is called out in the project's GAP_ANALYSIS.md as the "single biggest trust-destroyer."

### 3.2 Embedding-Based Story Clustering

The research-proven approach is semantic embedding + cosine similarity:

1. **Embed** each article's title + first paragraph using a sentence embedding model
2. **Cluster** articles where cosine similarity exceeds a threshold (0.85-0.90 for same-event detection)
3. **Select** the canonical article per cluster (highest-tier source, or most complete)
4. **Synthesize** a cluster summary from all articles' full text

**Embedding model options for this use case:**

| Model | Quality | Speed | Cost | Notes |
|-------|---------|-------|------|-------|
| `all-MiniLM-L6-v2` (SBERT) | Good | Very fast | Free | Best default; 80MB; 14,000 sentences/sec on CPU |
| `text-embedding-3-small` (OpenAI) | Excellent | Fast | $0.02/1M tokens | API call; not free |
| Claude embeddings (via API) | Excellent | Medium | Via Anthropic API | Project already uses Claude; natural fit |
| `paraphrase-multilingual-MiniLM-L12-v2` | Good | Fast | Free | If non-English sources added later |

For a pipeline embedding ~300 articles/day (titles + first 100 words), `all-MiniLM-L6-v2` is the right default — zero API cost, runs in milliseconds on CPU, and produces cosine similarity scores that reliably cluster same-event news.

**Important implementation note:** SBERT reduced the time to find the most similar pair from 65 hours with vanilla BERT to 5 seconds for 10,000 documents. The briefing pipeline's scale (300 articles) makes this trivially fast — full pairwise comparison is feasible without any approximate nearest-neighbor tricks.

**Threshold calibration:** For same-event news clustering, a cosine threshold of 0.85-0.90 is the appropriate range:
- 0.90+ catches near-identical rewrites (wire copy republished by multiple outlets)
- 0.85 catches same story, different angle (Reuters "AWS announces X" vs TechCrunch "What AWS's X means for developers")
- 0.80 groups related stories (useful for a "theme" view but risks merging distinct stories)

Use 0.85 as the default with manual override available in config.

### 3.3 LLM-Powered Cluster Synthesis

Once a cluster of articles is identified, Claude can synthesize them into a single, richer briefing item. This is where the deep-dive value materializes:

**Input to Claude:** Full text from all cluster members (capped at 1,500 words per article, top 4 articles by tier)
**Output from Claude:** A synthesized 4-6 sentence summary that:
- States the confirmed facts (what all sources agree on)
- Notes divergent framings or additional details from secondary sources
- Identifies which source is most authoritative
- Produces the OCI implication from the aggregate picture

This is qualitatively better than summarizing any single article, because it surfaces discrepancies between sources (e.g., Reuters says "$2B deal," TechCrunch says "$1.8B" — the synthesis should note this), additional context only one source mentions, and the range of reactions.

The cluster synthesis should replace the per-article `generate_summary()` call for clustered items, and should receive a `cluster_members` list in addition to the canonical article.

### 3.4 Source Coverage Heuristic

Before embedding infrastructure is in place, a simpler heuristic can be implemented immediately: count how many distinct sources (by `source` field) have articles with high keyword overlap on the same entity within a 12-hour window. Articles sharing 3+ entity keywords from the same 6-hour window are candidate duplicates. This is the "momentum" scoring dimension already identified as missing in GAP_ANALYSIS.md — two birds, one stone.

---

## 4. Agentic Research Patterns

### 4.1 What "Research Agent" Means

A research agent is an LLM that, given a topic, autonomously decides what to search for, executes searches, reads results, identifies gaps in its understanding, searches again, and synthesizes a comprehensive answer. The key distinction from the current pipeline is *autonomy and iteration*: the agent decides what to look at next based on what it has already learned.

Anthropic's own Claude Research capability (announced in 2025) demonstrates the pattern: given a question, Claude conducts multiple searches that build on each other, explores different angles automatically, and works through open questions systematically — conducting the equivalent of 20+ targeted searches and synthesizing them into a structured report, in minutes.

For the OCI briefing, the research agent pattern is most valuable for **on-demand deep dives on a flagged story** rather than bulk processing. The daily pipeline should surface the top items efficiently; the deep dive capability is triggered when an executive clicks "investigate this further."

### 4.2 Patterns for This Pipeline

**Pattern 1: Synchronous research during pipeline run (for top-5 stories)**

During the daily run, for the top 5 stories by score, trigger a lightweight research loop:
1. Fetch full text (trafilatura/Jina)
2. Claude extracts the key claims and entities
3. For each major claim/entity, query a search API for additional context
4. Claude synthesizes all sources into a "deep brief" section

This adds 30-60 seconds of wall-clock time for top-5 stories and is appropriate to run during the regular pipeline execution.

**Pattern 2: On-demand research via "Investigate" button (async, user-triggered)**

Add an "Investigate further" link to each briefing item (rendered as a URL parameter or a lightweight server endpoint). When clicked, triggers the research pipeline in the background and updates the briefing page. The user gets a loading state, then the enriched view.

This is architecturally cleaner because it keeps the daily pipeline fast and concentrates latency where the executive expects it (clicking "read more").

**Pattern 3: Weekly synthesis agent (batch, once-weekly)**

A separate weekly run that:
1. Loads all 5 daily briefings for the week
2. Identifies which entities/topics appeared multiple days
3. Synthesizes the week's evolution of those threads
4. Produces a "Week in Review" section

This is well-suited to the existing LLM infrastructure — it is just a new `generate_weekly_synthesis()` function in `llm.py` consuming stored article data.

### 4.3 LangChain/LlamaIndex for This Use Case

The existing pipeline uses `claude -p` via subprocess — a deliberately minimal LLM integration that avoids framework dependencies. This was a sound architectural choice for the current scope.

For deep-dive capabilities, the question is whether to introduce LangChain or LlamaIndex.

**Assessment:** For this project's scope, they are unnecessary. The pipeline's LLM calls are all structured prompt→JSON-response interactions. The "agentic" behavior needed (search → read → synthesize → search again) can be implemented as explicit Python loops using the existing `call_claude()` function with new prompts and the search API SDKs (httpx calls to Tavily or Exa). Adding LangChain for this purpose would add a large dependency tree, version management overhead, and the abstraction cost without meaningful gain.

LlamaIndex is more relevant if the project evolves toward a persistent vector database with semantic search over archived briefings — the LlamaIndex Query Engine pattern fits that use case well. But that can be deferred until the vector database is introduced.

**Decision:** Implement research agent behavior with plain Python + httpx + new `research.py` module. Do not add LangChain or LlamaIndex unless the project's architecture evolves to need their abstractions.

---

## 5. Search APIs for Topic Expansion

### 5.1 Tavily vs. Exa vs. Jina vs. Brave

For a research agent that needs to search the web on a topic, the current options are:

| API | Best For | Accuracy (WebWalker) | p95 Latency | Pricing | Notes |
|-----|----------|---------------------|-------------|---------|-------|
| **Exa** | Semantic/neural search, company/people/code search | 81% | ~1.7s | $5/1K searches + $1/1K pages | Best semantic quality; 1,200-domain filters |
| **Tavily** | Factual lookups, LangChain-native agents | 71% | ~4.0s | $0.008/credit | Simpler; good default for basic RAG |
| **Jina Reader** | Converting specific URLs to text | N/A (URL-based, not search) | Fast | Free tier 200 req/min | Not a search engine; complements others |
| **Brave Search API** | Privacy-respecting general search | Good | Fast | $3/1K queries (free tier available) | Independent index; no Google dependency |
| **Perplexity API** | Full research reports | Excellent | Slow | Usage-based | Returns synthesized text, not raw results |

**Recommendation for this project:**

Use **Exa** for research agent queries. The semantic search quality (81% vs 71% on complex multi-hop queries) matters significantly for an OCI-focused briefing where queries are entity-specific ("What is Azure's data center expansion strategy in the Gulf?"). Exa also offers company search as a structured endpoint, which is directly useful for the OCI competitive intelligence use case.

The key Exa feature for deep dives: `highlights` — query-dependent excerpts from retrieved pages that improve RAG accuracy by ~10% compared to full-page retrieval. This reduces downstream Claude token usage.

**Exa research agent call pattern for this pipeline:**

```python
import httpx

def exa_search(query: str, num_results: int = 5) -> list[dict]:
    """Search Exa for related articles. Returns list of {url, title, highlights}."""
    response = httpx.post(
        "https://api.exa.ai/search",
        headers={"x-api-key": EXA_API_KEY},
        json={
            "query": query,
            "num_results": num_results,
            "highlights": {"numSentences": 3, "highlightsPerUrl": 2},
            "contents": {"text": {"maxCharacters": 1000}},
        },
        timeout=10,
    )
    return response.json().get("results", [])
```

Cost for the briefing pipeline: If 5 top stories each trigger an Exa search for 5 results + page content, that is 25 searches + 25 page fetches per day = $0.125 + $0.025 = ~$0.15/day. Entirely negligible.

### 5.2 Tavily's Research Endpoint

Tavily launched a "Research" endpoint (late 2025) that performs end-to-end deep research through a single API call — essentially the research agent loop as a service. This is an interesting alternative to building the agent loop manually. The tradeoff: less control over the research path, but much simpler implementation.

For the OCI briefing, **the manual research loop is preferred** because:
- OCI-specific framing must be woven in at each step ("What does this mean for OCI specifically?")
- The Tavily Research endpoint produces a generic research report, not an OCI intelligence item
- Cost transparency is clearer with explicit API calls

---

## 6. Community Signal Aggregation: Hacker News and Beyond

### 6.1 Hacker News API

The current pipeline ingests HN's RSS feed, which gives post titles and URLs. It does not fetch comments. For OCI executive briefings, HN comment threads on technical topics (cloud architecture, GPU availability, open-source model releases) provide a qualitatively different signal than journalist coverage: immediate reactions from practitioners, early bug reports, benchmarks, and opinions from people who will influence enterprise technology buying.

**HN Official API** (free, no authentication):
- `https://hacker-news.firebaseio.com/v0/item/{id}.json` — fetch any item (story or comment)
- `https://hacker-news.firebaseio.com/v0/topstories.json` — top 500 story IDs

**HN Algolia API** (better for this use case):
- `https://hn.algolia.com/api/v1/search?query=oracle+cloud` — full-text search with date filtering
- Returns complete story metadata + top comment IDs in a single call
- Supports fetching entire comment trees in one request

**For the briefing pipeline, the recommended pattern:**

When an article in the briefing matches a known technology topic (detected via entities from the classification step), query HN Algolia to find if there is a corresponding discussion thread. If the thread has 200+ points or 50+ comments, fetch the top 10 root comments (by score) and pass them to a new `extract_expert_reactions()` LLM call that distills the practitioner perspective into 2-3 sentences.

This is the "expert commentary aggregation" use case. It answers the question: "What are senior engineers actually saying about this?"

Example: An article about "NVIDIA H200 Ultra GPU" would trigger an HN search, find the 800-point thread, and surface: "HN discussion highlights concerns about H200 Ultra's memory bandwidth vs. B200 for inference workloads; several practitioners report that OCI's existing H100 allocation is still unavailable in most regions."

### 6.2 Reddit

Reddit's API became restrictive in 2023 and remains challenging for automated use. The `/r/devops`, `/r/MachineLearning`, and `/r/CloudComputing` subreddits would theoretically add value, but the API rate limits and authentication overhead make it a lower priority than HN. The HN Algolia API is significantly easier to integrate and covers a comparable expert audience for the OCI briefing's topics.

**Decision:** Implement HN comment aggregation first. Add Reddit only if HN signal proves insufficient.

### 6.3 GitHub Signal

For stories about open-source releases (a significant fraction of the AI news cycle), GitHub provides objective momentum signals: star velocity, fork count, issues opened in the last 24 hours, PR activity. The GitHub REST API is free for public repos with OAuth token (5,000 requests/hour):

```
GET https://api.github.com/repos/{owner}/{repo}
→ stargazers_count, forks_count, open_issues_count, pushed_at
```

When the briefing contains an article about an open-source model or tool release (detected via classified_section = "oss" or "ai" + "open source" in entities), the pipeline can automatically fetch the associated GitHub repo metrics and include them in the briefing item: "Meta's Llama 4 repo gained 12,400 stars in 18 hours; 340 forks; 89 issues opened."

This transforms a "Meta released X" story into "Meta released X, and the developer community responded with [specific signal]."

---

## 7. What Leading Briefing Products Do for Depth

### 7.1 Axios Smart Brevity

Axios's methodology is highly relevant as a model for what to emulate at each depth level:

**Core structure:**
1. Headline: What's new (10-15 words)
2. Why it matters: 1-2 sentences — the so-what
3. The big picture: 2-3 sentences of context
4. Go deeper: links to longer treatment

The "Go deeper" element is Axios's version of deep dive — they write it as "Wikipedia article in newsletter form," covering more depth without requiring the reader to leave. The formula: lead concisely, offer context, then optionally go long for those who want it.

**Implication for the OCI briefing:** The current system already does well at the first two layers (punchy headline, 2-3 sentence summary with OCI implication). The gap is the "Go deeper" layer — the optional, expandable, richer context. Deep dive capabilities should be architected as exactly this: additional depth that is off by default but available on demand.

**Smart Brevity's AI tool (Axios HQ):** Axios has built AI writing assistance into their HQ product, which uses LLMs to help communicators follow the Smart Brevity format. The key lesson: AI is best used to enforce the *format* and *framing*, while the depth comes from richer source material going into the LLM context.

### 7.2 Bloomberg Intelligence and Terminal

Bloomberg's approach to depth is instructive for an executive briefing:

**BloombergGPT architecture:** A 50B parameter model trained on 700B tokens (363B financial domain + 345B general text). It is fine-tuned on financial NLP tasks — sentiment, NER, news classification, Q&A — but the key architectural insight is that domain-specific training data dramatically outperforms general-purpose LLMs on financial analysis tasks.

**Bloomberg AI Document Insights:** Their production AI tool lets analysts pose natural-language questions against earnings transcripts, regulatory filings, Bloomberg News articles, and independent analyst research — all in a single query. The answer cites specific sentences from specific documents. This is essentially RAG over a curated financial document corpus.

**Implication for OCI briefing:** The Bloomberg approach points toward a future state where the briefing system maintains a persistent vector store of all prior briefings, company filings, OCI press releases, and competitor earnings reports, and can answer "How does today's Azure announcement compare to their Q3 capex guidance?" in real time. The path there is: (1) build the persistent storage/archive first, (2) add vector embeddings on top of the archive, (3) wire search over that archive into the LLM context for each new briefing item.

### 7.3 Elicit and Consensus (AI Research Tools)

Elicit and Consensus are AI research assistants for academic literature. Their architectural patterns are directly applicable:

**Elicit's approach:**
- Searches 138M+ papers on a natural language question
- Extracts structured data from full text (methods, results, confidence intervals)
- Can screen 500+ papers automatically using LLM-generated criteria
- Reduces literature review time by up to 80%

**Consensus approach:**
- Synthesizes up to 20 papers using full text
- Produces TL;DR headers, structured comparisons, in-line citations
- Uses citation count, method quality, and journal reputation as quality signals

The pattern applicable to the OCI briefing: treat news articles like research papers. For a given topic (e.g., "cloud provider sovereign cloud expansion"), gather all articles covering it over the last 30 days, extract structured claims from each (which regions, which companies, which dollar values), and produce a synthesized "state of the topic" view. This is exactly what the weekly synthesis capability should do.

---

## 8. Weekly Synthesis and Temporal Context

### 8.1 Rolling Window Trend Detection

The current system has no memory between runs. Each day is a fresh slate. This means it cannot detect:
- A competitor (e.g., Google) making sovereign cloud announcements three weeks in a row
- A security vulnerability story that is evolving (patch released, then bypass discovered, then re-patch)
- A gradual shift in AI model pricing that individually appears minor but is strategically significant in aggregate

The GAP_ANALYSIS.md identifies the "7-day deduplication pipeline" and "persistent storage" as missing P0 features. Once those are implemented, temporal context becomes straightforward: the vector database and cluster table enable queries like "has any article in the last 14 days covered the same entity cluster as today's article?"

For the deep-dive roadmap, temporal context manifests as:

1. **Trend arrows:** A simple `[NEW]` / `[DEVELOPING]` / `[FOLLOW-UP]` tag on each briefing item based on whether the story cluster appeared in prior briefings
2. **Multi-day story packages:** When the same cluster appears 3+ days, synthesize the full arc into a "Story So Far" section
3. **Entity frequency tracking:** Count mentions of key entities (AWS, Google, NVIDIA, specific people) over rolling 7-day windows and flag when frequency spikes

### 8.2 Weekly Briefing Architecture

A Friday or Monday weekly synthesis briefing — "Week in Review" — is a high-value, low-implementation-cost feature once daily storage is in place. The structure:

1. Pull all articles from the week's canonical bundles
2. Cluster by entity/topic across the week (same algorithm as daily clustering, wider time window)
3. For each major cluster, call `generate_weekly_synthesis()` which asks Claude:
   - "These 8 articles all covered [topic] this week. What is the arc? What changed between Monday and Friday? What is the net strategic implication for OCI?"
4. Produce a distinct HTML briefing with a "week-that-was" format

This directly addresses what the Trendtracker-style tools provide: pattern recognition over time, not just daily snapshot intelligence.

### 8.3 OCI-Specific Historical Context

A particularly high-value application of temporal context for the OCI audiences: comparing competitor moves to their prior commitments. When AWS announces a new price cut, the briefing should note "AWS has now made three separate price cut announcements in the last 90 days, following a period where OCI pricing was publicly cited as a competitive pressure by AWS on earnings calls." This kind of context transforms a news item into strategic intelligence.

Implementation path: tag competitor-related articles with a `competitor_entity` field and maintain a per-competitor timeline in persistent storage. When a new competitor article is processed, retrieve the last 5 items for that competitor and pass them to Claude as context.

---

## 9. Feature Ranking: Value vs. Implementation Effort

The following table ranks all identified deep-dive capabilities by strategic value to OCI executive audiences and implementation effort. The scoring uses a 1-5 scale (5 = highest value / lowest effort = best ROI).

| Feature | Value (1-5) | Effort (1-5, lower=easier) | ROI Score | Notes |
|---------|-------------|---------------------------|-----------|-------|
| **Full-text extraction (trafilatura)** | 5 | 1 | **High** | Single `pip install trafilatura`; drops into existing pipeline at one integration point |
| **Story clustering (SBERT + cosine)** | 5 | 2 | **High** | Eliminates the biggest executive trust problem; SBERT is fast and free |
| **Cluster synthesis prompt** | 5 | 1 | **High** | New LLM prompt using existing `call_claude()` infrastructure; no new dependencies |
| **HN comment aggregation** | 4 | 2 | **High** | Free API; adds practitioner perspective; transformative for AI/OSS stories |
| **Jina Reader fallback** | 4 | 1 | **High** | Two-line code change; `https://r.jina.ai/` + URL; handles paywalls and JS sites |
| **Exa search for related articles** | 4 | 2 | **High** | New API integration; $0.15/day; enriches top-5 stories significantly |
| **GitHub repo signal for OSS stories** | 3 | 2 | **Medium** | Free API; adds objective momentum data; limited to OSS/AI articles |
| **Trend tags (NEW/DEVELOPING/FOLLOW-UP)** | 4 | 2 | **Medium** | Requires persistent storage (P0 dependency) but simple once storage exists |
| **Weekly synthesis briefing** | 4 | 2 | **Medium** | Requires storage; new prompt only; very high exec value |
| **Thread following (paper → HN → GitHub)** | 4 | 3 | **Medium** | High value for AI/research stories; needs entity extraction + conditional logic |
| **OCI competitor timeline context** | 5 | 3 | **Medium** | Very high value; requires persistent competitor tagging + retrieval |
| **On-demand "Investigate" button** | 4 | 3 | **Medium** | Requires async endpoint or JS; high value when exec wants depth |
| **Archive.org fallback for paywalls** | 3 | 2 | **Medium** | Legitimate, free; not all articles archived promptly |
| **Structured competitor comparison** | 4 | 4 | **Low-Med** | Requires schema design + multi-article extraction; high value but complex |
| **Vector search over archive** | 5 | 4 | **Low-Med** | Transformative long-term; requires Qdrant/PgVector + embedding infrastructure |
| **Reddit expert commentary** | 2 | 3 | **Low** | API friction high; HN covers most of same expert audience |
| **Bloomberg-style Q&A over corpus** | 5 | 5 | **Low** | Very high value long-term; requires full vector archive first |

---

## 10. Concrete Feature Designs with Implementation Sketches

### Feature A: Full-Text Enrichment Module

**What it does:** After `ingest_feeds()`, fetch full article text for the top 60 articles. Replaces RSS summary with full text in LLM prompts.

**New file:** `briefing/enrich.py`

**Core logic:**
```python
from trafilatura import fetch_url, extract
import httpx

def fetch_full_text(url: str, timeout: int = 10) -> str | None:
    """Try trafilatura first, fall back to Jina Reader API."""
    # Attempt 1: trafilatura direct fetch
    downloaded = fetch_url(url, timeout=timeout)
    if downloaded:
        text = extract(downloaded, include_comments=False, fast=True,
                       output_format="txt")
        if text and len(text) > 200:
            return text[:3000]  # cap at 3k chars for LLM context

    # Attempt 2: Jina Reader API (handles JS-heavy and some paywalled sites)
    try:
        jina_url = f"https://r.jina.ai/{url}"
        resp = httpx.get(jina_url, timeout=15,
                         headers={"Accept": "text/plain",
                                  "X-Return-Format": "text"})
        if resp.status_code == 200 and len(resp.text) > 200:
            return resp.text[:3000]
    except Exception:
        pass

    return None  # fallback to RSS summary in callers


def enrich_articles(articles: list[dict], top_n: int = 60) -> list[dict]:
    """Fetch full text for top_n articles; store in article['full_text']."""
    to_enrich = articles[:top_n]  # already sorted by score
    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {pool.submit(fetch_full_text, a["url"]): a for a in to_enrich}
        for future in as_completed(futures):
            article = futures[future]
            text = future.result()
            article["full_text"] = text
            article["full_text_available"] = bool(text)
    return articles
```

**Pipeline change:** Add `articles = enrich_articles(articles)` between `step_normalize()` and `step_classify()` in `main.py`.

**LLM prompt change:** In `llm.py`, both `classify_article()` and `generate_summary()` should use `article.get('full_text') or article.get('summary', '')` as their content input.

**Estimated implementation:** 2-3 hours. Dependencies to add: `trafilatura>=2.0`, `httpx` (already in requirements.txt).

---

### Feature B: Story Clustering with SBERT

**What it does:** Groups articles covering the same event into clusters. Selects one canonical article per cluster. Enables the cluster synthesis prompt in Feature C.

**New module:** Add to `briefing/process.py` (clustering is part of normalization).

**Core logic:**
```python
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

_MODEL = None

def _get_model():
    global _MODEL
    if _MODEL is None:
        _MODEL = SentenceTransformer('all-MiniLM-L6-v2')
    return _MODEL

def cluster_articles(articles: list[dict],
                     threshold: float = 0.85) -> list[dict]:
    """
    Cluster articles by semantic similarity. Mutates each article with:
      article['cluster_id'] — shared ID for same-event articles
      article['is_canonical'] — True for the best-source article in cluster
      article['cluster_members'] — list of other article dicts in cluster
    Returns articles with cluster metadata added.
    """
    model = _get_model()
    texts = [f"{a['title']} {a.get('summary', '')[:150]}" for a in articles]
    embeddings = model.encode(texts, show_progress_bar=False)

    n = len(articles)
    sim_matrix = cosine_similarity(embeddings)
    assigned = [False] * n
    clusters = []

    for i in range(n):
        if assigned[i]:
            continue
        cluster = [i]
        for j in range(i + 1, n):
            if not assigned[j] and sim_matrix[i][j] >= threshold:
                cluster.append(j)
                assigned[j] = True
        assigned[i] = True
        clusters.append(cluster)

    # Assign cluster IDs and canonical flag
    for cluster_idxs in clusters:
        cluster_id = articles[cluster_idxs[0]]['id']
        # Canonical = lowest tier number (highest quality source)
        canonical_idx = min(cluster_idxs,
                            key=lambda k: articles[k]['tier'])
        for idx in cluster_idxs:
            a = articles[idx]
            a['cluster_id'] = cluster_id
            a['is_canonical'] = (idx == canonical_idx)
            a['cluster_members'] = [articles[k] for k in cluster_idxs
                                    if k != idx]

    return articles
```

**Dependencies to add:** `sentence-transformers>=3.0`, `scikit-learn>=1.4` (scikit-learn may already be present indirectly).

**Scoring change:** After clustering, scoring should apply a `duplication_penalty` to non-canonical articles in the same cluster, reducing their score so only the canonical article surfaces in each audience's top-12.

**Estimated implementation:** 3-4 hours, plus 1-2 hours for threshold calibration against real feed data.

---

### Feature C: Cluster Synthesis Prompt

**What it does:** When a story cluster has 2+ members, calls Claude with all members' full text to produce a synthesized, multi-source briefing item.

**Change to `llm.py`:**
```python
def generate_cluster_summary(canonical: dict,
                              cluster_members: list[dict],
                              audience_profile: dict) -> dict:
    """
    Generate a synthesized summary for a story cluster from multiple sources.
    Uses full_text from all members if available, else summary.
    """
    cache_key = _cache_key(
        f"cluster:{canonical['url']}:{audience_profile['id']}"
        + "".join(m['url'] for m in cluster_members[:3])
    )
    cached = _cache_get(cache_key)
    if cached:
        return cached

    def article_text(a: dict, cap: int = 800) -> str:
        content = a.get('full_text') or a.get('summary', '')
        return f"[{a['source']} — Tier {a['tier']}]\n{content[:cap]}"

    sources_text = "\n\n".join(
        [article_text(canonical)] +
        [article_text(m) for m in cluster_members[:3]]
    )

    prompt = f"""You are the editorial AI for an executive intelligence briefing for OCI (Oracle Cloud Infrastructure) senior leadership.

Multiple sources are reporting on the same story. Your job is to synthesize them into a single, authoritative briefing item — richer than any one source alone.

Audience: {audience_profile['name']}, {audience_profile['title']}
Tone: {audience_profile['tone_guidance']}

SOURCES (most authoritative first):
{sources_text}

Respond ONLY with valid JSON:
{{
  "headline": "Synthesized 10-15 word headline for this executive",
  "summary": "3-4 sentences. Lead with confirmed facts agreed across sources. Note any significant discrepancies or additional details from secondary sources. End with the strategic picture.",
  "oci_implication": "1-2 sentences on what this means for OCI strategy or competitive position.",
  "sources_cited": ["Source1", "Source2"],
  "coverage_count": {len(cluster_members) + 1}
}}"""

    try:
        raw = call_claude(prompt, model=SONNET_MODEL, timeout=90)
        # ... strip fences, parse JSON (same pattern as existing functions)
        result = json.loads(raw.strip())
    except Exception as exc:
        logger.warning("cluster_summary failed: %s", exc)
        result = generate_summary(canonical, audience_profile)

    _cache_set(cache_key, result)
    return result
```

**Rendering change:** The HTML template should display a small "synthesized from N sources" indicator (e.g., "Reuters + TechCrunch + 2 more") when `coverage_count > 1`. This is a quality signal — it tells the executive "we read everything so you don't have to."

---

### Feature D: HN Expert Commentary Injection

**What it does:** For articles about AI/OSS topics, search HN for a matching discussion thread and inject a "Practitioner reaction" block into the briefing item.

**New module:** `briefing/community.py`

**Core logic:**
```python
import httpx

HN_ALGOLIA = "https://hn.algolia.com/api/v1"

def find_hn_thread(article: dict, min_points: int = 100) -> dict | None:
    """Search HN Algolia for a matching discussion for this article."""
    # Use title keywords as query
    keywords = " ".join(article['title'].split()[:6])
    resp = httpx.get(
        f"{HN_ALGOLIA}/search",
        params={
            "query": keywords,
            "tags": "story",
            "numericFilters": f"points>{min_points}",
        },
        timeout=5,
    )
    hits = resp.json().get("hits", [])
    if not hits:
        return None
    # Prefer hits with matching URL domain
    article_domain = article['url'].split('/')[2]
    for hit in hits:
        if article_domain in hit.get("url", ""):
            return hit
    return hits[0] if hits else None


def fetch_top_comments(hn_story_id: str, n: int = 8) -> list[str]:
    """Fetch top-level comments from an HN story, return as text list."""
    resp = httpx.get(
        f"{HN_ALGOLIA}/items/{hn_story_id}",
        timeout=5,
    )
    story = resp.json()
    comments = []
    for child in (story.get("children") or [])[:n]:
        text = child.get("text", "")
        if text and len(text) > 50:
            # Strip HTML tags
            from bs4 import BeautifulSoup
            comments.append(BeautifulSoup(text, "html.parser").get_text()[:400])
    return comments
```

**LLM call to synthesize comments:**
```python
def summarize_hn_reactions(comments: list[str], article_title: str) -> str:
    """Distill HN practitioner reactions into 1-2 sentences."""
    prompt = f"""An article titled "{article_title}" is being discussed on Hacker News by technical practitioners.

Top comments (lightly edited for length):
{chr(10).join(f'- {c}' for c in comments[:6])}

In 1-2 sentences, summarize the key practitioner reaction: what do engineers/technologists think about this? Note any significant concerns, enthusiasm, or skepticism. Be specific — cite concrete points raised."""
    return call_claude(prompt, model=HAIKU_MODEL, timeout=30)
```

**Integration:** Add `hn_reaction` field to articles where found. Render it in the HTML as a callout block labeled "Practitioner view" with the HN thread link and point/comment count.

---

### Feature E: Trend Tags and Story Status

**What it does:** Labels each briefing item as `NEW`, `DEVELOPING`, or `FOLLOW-UP` based on whether the story cluster appeared in recent prior briefings. Requires persistent storage (dependent on GAP_ANALYSIS.md P0 item 3.2).

**Story status logic:**
```python
def determine_story_status(article: dict, db_conn) -> str:
    """
    Check prior briefings for matching cluster.
    Returns: "new" | "developing" | "follow_up"
    """
    cluster_id = article.get('cluster_id', article['id'])
    recent = db_conn.execute("""
        SELECT MIN(briefing_date), COUNT(DISTINCT briefing_date)
        FROM delivered_items
        WHERE cluster_id = ?
        AND briefing_date >= DATE('now', '-14 days')
    """, (cluster_id,)).fetchone()

    if not recent or not recent[0]:
        return "new"
    prior_count = recent[1]
    if prior_count == 1:
        return "developing"
    return "follow_up"
```

**Rendering:** Small colored pill badges: `[NEW]` (green), `[DEVELOPING]` (amber), `[FOLLOW-UP]` (blue) next to the source tier badge.

---

### Feature F: Weekly Synthesis Briefing

**What it does:** A separate weekly pipeline run (e.g., Friday at 6 AM) that synthesizes the week's briefings into a "Week in Review" per executive.

**New pipeline entry point:** `main_weekly.py` or `main.py --weekly`

**Core logic:**
```python
def generate_weekly_synthesis(weekly_articles: list[dict],
                               audience_profile: dict) -> dict:
    """Generate a week-in-review synthesis for one audience."""
    # Group by cluster, select top clusters by coverage frequency
    from collections import Counter
    cluster_freq = Counter(a.get('cluster_id', a['id'])
                           for a in weekly_articles)
    top_clusters = [cid for cid, _ in cluster_freq.most_common(8)]

    # Get one canonical article per top cluster
    representatives = []
    for cid in top_clusters:
        cluster_arts = [a for a in weekly_articles
                        if a.get('cluster_id', a['id']) == cid]
        canonical = min(cluster_arts, key=lambda a: a['tier'])
        representatives.append(canonical)

    # Build weekly context text
    context = "\n\n".join(
        f"[{a['published_at'].strftime('%a %b %d')}] {a['title']} ({a['source']})\n"
        f"{a.get('full_text') or a.get('summary', '')[:500]}"
        for a in representatives
    )

    prompt = f"""You are the chief editorial AI for the OCI executive intelligence briefing system.

Audience: {audience_profile['name']}, {audience_profile['title']}

Below are the major stories that appeared across this week's daily briefings. Your job is to synthesize the week into a strategic executive narrative — not just a list, but an analysis of what the week's signals mean in aggregate.

THIS WEEK'S MAJOR STORIES:
{context}

Respond ONLY with valid JSON:
{{
  "week_headline": "10-word theme that defined this week for OCI",
  "key_threads": [
    {{"thread": "Name of recurring theme", "summary": "What happened across the week on this thread", "trajectory": "accelerating|stable|decelerating"}}
  ],
  "week_oci_implication": "3-4 sentences. The net strategic picture for OCI from this week's developments. What should leadership be watching going into next week?",
  "stories_to_watch": ["Story 1 to monitor next week", "Story 2"]
}}"""

    return json.loads(call_claude(prompt, model=SONNET_MODEL, timeout=120))
```

---

## 11. What Deep Dive Looks Like for OCI Executives Specifically

The four current audience profiles each have distinct needs that deep-dive capabilities serve differently:

### Karan Batta — SVP, OCI Product (Financial/Competitive Focus)

Deep dive features most valuable to Karan:
1. **Cluster synthesis with source count** — "5 outlets covered AWS Graviton5; here is the synthesized picture" saves time and improves signal quality
2. **Competitor financial context** — when an AWS or Azure announcement appears, automatic retrieval of their last earnings call statements on capex/pricing to frame the new announcement
3. **Deal tracking threads** — when a major cloud deal is announced, follow-up on HN/Reddit to surface practitioner reactions about deal implications ("Is this deal actually significant or a press release?")
4. **OCI price position monitoring** — flag when competitor price changes are announced and provide automatic context on OCI's relative pricing in that segment

The deep brief for Karan should feel like a sell-side analyst report: numbers, comparisons, competitive positioning, financial implications — not just what happened but what it costs and who gains.

### Nathan Thomas — SVP, OCI Product (Ecosystem/Partner Focus)

Deep dive features most valuable to Nathan:
1. **Thread following for partnership announcements** — when Azure/SAP or Google/ServiceNow announce a partnership, follow the thread to find analyst commentary, prior Oracle positioning in that segment, and relevant OCI partnership angles
2. **Multi-cloud dynamics synthesis** — cluster all multi-cloud stories from the week and synthesize the evolving landscape narrative
3. **ISV/GSI signal tracking** — for articles mentioning system integrators (Accenture, Deloitte, etc.) or ISVs, extract the partnership implications automatically

### Greg Pavlik — EVP, Data & AI (Technical Executive)

Deep dive features most valuable to Greg:
1. **GitHub repo signal injection** — every AI model release or OSS tool article should include star velocity, fork count, open issues
2. **HN practitioner reactions** — most important for Greg; engineers' benchmark criticisms, architectural objections, and adoption signals are core intelligence
3. **Benchmark context** — when an LLM benchmark score is cited, automatic context of the benchmark history ("GPT-4 scored X on this benchmark in 2023; Claude 3 Opus scored Y; today's announcement claims Z")
4. **arXiv paper following** — when a research paper is cited in a news article, automatically fetch the abstract and key findings from arXiv

The deep brief for Greg should feel like a curated engineering reading list with editorial synthesis — technical depth, concrete numbers, practitioner reality-checks.

### Mahesh Thiagarajan — EVP, Security & Developer Platform

Deep dive features most valuable to Mahesh:
1. **CVE/security thread following** — when a vulnerability is announced, immediately track the GitHub advisory, CISA bulletin, and HN security discussion
2. **Regulatory follow-up** — when compliance/regulatory news appears (EU AI Act, CISA advisories), follow the thread for implementation guidance and competitor statements
3. **Datacenter/power trend analysis** — weekly synthesis of power constraints, grid announcements, and datacenter capacity news with geographic mapping
4. **Developer sentiment signals** — for developer platform announcements, HN and Reddit practitioner reactions are critical intelligence

---

## 12. Recommended Phasing

### Phase 1 — Foundation (Weeks 1-2, ~12 hours implementation)

These items have the highest ROI and lowest dependencies. They can be implemented before the persistent storage P0 item.

| Task | File(s) Changed | Effort |
|------|----------------|--------|
| Add trafilatura + Jina Reader fallback | New `briefing/enrich.py`, `main.py`, `requirements.txt` | 3h |
| Update LLM prompts to use full_text | `briefing/llm.py` | 1h |
| Add SBERT story clustering | `briefing/process.py`, `requirements.txt` | 3h |
| Add cluster synthesis prompt | `briefing/llm.py` | 2h |
| Render "synthesized from N sources" indicator | `briefing/render.py` | 1h |
| Add HN thread lookup + comment summarization | New `briefing/community.py`, `briefing/llm.py` | 2h |

**Expected outcome:** Briefings become substantively richer. Stories stop repeating across slots. Practitioner reactions appear for AI/OSS stories. LLM has full article text to work with.

### Phase 2 — Depth and Context (Weeks 3-6, requires persistent storage)

These items require the SQLite/PostgreSQL storage from GAP_ANALYSIS.md P0 item 3.2.

| Task | File(s) Changed | Effort |
|------|----------------|--------|
| Trend tags (NEW/DEVELOPING/FOLLOW-UP) | `briefing/process.py`, `briefing/render.py`, database | 4h |
| OCI competitor timeline context | New `briefing/context.py`, `briefing/llm.py` | 6h |
| Exa search integration for top-5 stories | New `briefing/research.py`, `briefing/llm.py` | 4h |
| GitHub repo signal for OSS articles | `briefing/community.py` | 3h |
| Weekly synthesis briefing | New `main_weekly.py`, `briefing/llm.py` | 5h |

### Phase 3 — Advanced Research Agent (Post-Phase 2)

| Task | Effort | Notes |
|------|--------|-------|
| On-demand "Investigate" async endpoint | 8h | Requires async server (not just serve.py) |
| Vector archive over all prior briefings | 12h | Qdrant or PgVector + embedding pipeline |
| Bloomberg-style Q&A over OCI corpus | 16h | Requires vector archive + RAG plumbing |
| arXiv paper integration for research stories | 4h | arXiv API is free and well-documented |

---

## Key Sources

This research drew on the following sources:

- [Trafilatura evaluation benchmark — Scrapinghub](https://github.com/scrapinghub/article-extraction-benchmark)
- [Trafilatura Python usage documentation](https://trafilatura.readthedocs.io/en/latest/usage-python.html)
- [Evaluating text extraction tools — Adrien Barbaresi](https://adrien.barbaresi.eu/blog/evaluating-text-extraction-python.html)
- [Comparative analysis of open-source news crawlers](https://htdocs.dev/posts/comparative-analysis-of-open-source-news-crawlers/)
- [Exa vs. Tavily comparison — Exa.ai](https://exa.ai/versus/tavily)
- [Exa vs. Tavily — Data4AI](https://data4ai.com/blog/tool-comparisons/exa-ai-vs-tavily/)
- [Beyond Tavily: AI Search APIs in 2025](https://websearchapi.ai/blog/tavily-alternatives)
- [Jina Reader API](https://jina.ai/reader/)
- [Jina AI vs. Firecrawl comparison — Apify](https://blog.apify.com/jina-ai-vs-firecrawl/)
- [SBERT clustering documentation](https://sbert.net/examples/sentence_transformer/applications/clustering/README.html)
- [Ultimate guide to text similarity — NewsCatcher](https://www.newscatcherapi.com/blog/ultimate-guide-to-text-similarity-with-python)
- [LLM-enhanced news clustering — arXiv](https://arxiv.org/pdf/2406.10552)
- [Axios Smart Brevity methodology](https://www.axioshq.com/smart-brevity)
- [Axios Smart Brevity longform — CJR](https://www.cjr.org/criticism/axios-smart-brevity-longform.php)
- [BloombergGPT — Bloomberg Press](https://www.bloomberg.com/company/press/bloomberggpt-50-billion-parameter-llm-tuned-finance/)
- [Bloomberg AI Document Insights](https://www.bloomberg.com/company/press/bloomberg-accelerates-financial-analysis-with-gen-ai-document-insights/)
- [Elicit AI for scientific research](https://elicit.com/)
- [Elicit vs. Consensus comparison](https://paperguide.ai/blog/elicit-vs-consensus/)
- [LangChain vs. LlamaIndex 2025](https://latenode.com/blog/platform-comparisons-alternatives/automation-platform-comparisons/langchain-vs-llamaindex-2025-complete-rag-framework-comparison)
- [Claude Research capabilities — Anthropic](https://www.anthropic.com/news/research)
- [Hacker News API](https://news.ycombinator.com/item?id=32540883)
- [HN Algolia search API](https://hn.algolia.com/)
