# Research: Newsletter Ingestion for AI Daily Briefing Pipeline

**Date**: 2026-03-11
**Project**: OCI AI Daily Executive Briefing
**Purpose**: Evaluate replacing raw RSS feed scraping with curated newsletter ingestion to improve signal quality

---

## Executive Summary

Ingesting 5–10 high-quality curated AI newsletters produces materially better briefings than scraping 50+ raw RSS feeds. The curation work is already done by experts; the pipeline's job becomes synthesis, not discovery. Most top AI newsletters expose valid RSS feeds today — zero new infrastructure required. Email ingestion via webhook services adds coverage for newsletters without RSS, at low cost.

**Recommended stack (in priority order):**
1. RSS feeds from curated AI newsletters (free, immediate)
2. Hacker News filtered feed via hnrss.org (free, no auth)
3. arXiv cs.AI/cs.LG RSS (free, weekday updates)
4. Email-to-webhook via Cloudmailin for newsletters without RSS (free tier: 10k emails/month)
5. Beehiiv API (requires API key per newsletter — only worth it for Beehiiv-hosted newsletters you control)

---

## Part 1: Newsletter Sources and Programmatic Access

### 1.1 Confirmed Working RSS Feeds for AI Newsletters

These feeds were verified active as of 2026-03-11:

| Newsletter | RSS Feed URL | Platform | Cadence | Content Focus |
|---|---|---|---|---|
| **Import AI** (Jack Clark) | `https://importai.substack.com/feed` | Substack | Weekly | Research papers, AI safety, geopolitics |
| **Last Week in AI** (Andrey Kurenkov) | `https://lastweekin.ai/feed` | Substack (custom domain) | Weekly | News roundup, research, policy |
| **AINews by smol.ai** | `https://news.smol.ai/rss.xml` | Custom | Weekdays | Twitter/Reddit/Discord aggregation (Andrej Karpathy: "best AI newsletter atm") |
| **One Useful Thing** (Ethan Mollick) | `https://www.oneusefulthing.org/feed` | Substack | Weekly | Practical AI use, management, research |
| **Interconnects AI** (Nathan Lambert) | `https://www.interconnects.ai/feed` | Substack | ~3x/week | Open models, RLHF, LLM architecture |
| **Exponential View** (Azeem Azhar) | `https://www.exponentialview.co/feed` | Substack | Weekly | AI economics, policy, enterprise adoption |
| **AI Tidbits** | `https://aitidbits.ai/feed` | Substack | Weekly | AI coding tools, developer workflows |
| **The AI Edge** | `https://newsletter.theaiedge.io/feed` | Custom | Irregular | LLM frameworks, applied ML |
| **Simon Willison's Blog** | `https://simonwillison.net/atom/everything/` | Custom | Daily (multiple/day) | LLMs, tools, practical AI engineering |
| **Stratechery** (Ben Thompson) | `https://stratechery.com/feed/` | Custom | Daily | Tech strategy, AI business; partial paywall |

**Substack RSS pattern**: Every Substack newsletter exposes a feed at `https://{publication}.substack.com/feed` — this is a reliable, undocumented-but-stable convention. Newsletters on custom domains (like `lastweekin.ai`) redirect through Substack infrastructure.

### 1.2 High-Value Newsletters Without Confirmed RSS

| Newsletter | Platform | Access Options |
|---|---|---|
| **TLDR AI** | Custom (Next.js) | Web scrape `/api/latest/ai` endpoint (HTML/RSC, not JSON); email subscription; no official RSS found |
| **The Batch** (deeplearning.ai) | Custom | No RSS found; web archive at `deeplearning.ai/the-batch/`; email subscription |
| **The Rundown AI** | Beehiiv | Standard Beehiiv RSS (`/feed`) returned 404; may require Beehiiv API key |
| **Ben's Bites** | Beehiiv | `bensbites.beehiiv.com/feed` returned 404; check `bensbites.co/feed` |
| **Morning Brew** | Custom | No public RSS; email-only |
| **AI Breakfast** | Beehiiv | `aibreakfast.beehiiv.com/feed` returned 404 |
| **Superhuman AI** | Beehiiv | Confirmed: `"rss_feeds":[]` — RSS explicitly disabled |

**Key insight on Beehiiv**: Beehiiv newsletters do not uniformly expose RSS. Some publishers disable it. The Beehiiv API (`developers.beehiiv.com`) offers a `posts:read` scope that returns post metadata, but **the actual newsletter body content** is not clearly available — the API is primarily for newsletter operators managing their own publications, not for readers ingesting third-party content.

### 1.3 Substack API

Substack has no official public API for reading other publishers' content. The RSS feed approach (`/feed`) is the only supported programmatic access. Substack's `sitemap.xml` and `news_sitemap.xml` are available but provide URLs, not content.

### 1.4 Beehiiv API

- Endpoint base: `https://api.beehiiv.com/v2/`
- Auth: API key (Bearer token) or OAuth2 with `posts:read` scope
- Useful endpoints: `GET /publications/{id}/posts`, `GET /publications/{id}/posts/{post_id}`
- **Limitation**: You need to be an admin/owner of the Beehiiv publication to get an API key for it. You cannot use the Beehiiv API to ingest another publisher's newsletter as a reader. For third-party Beehiiv newsletters, RSS (where enabled) or email ingestion is the only path.

### 1.5 Buttondown

Buttondown newsletters expose RSS via `https://buttondown.com/{username}/rss` (or `buttondown.email/{username}/rss`). The platform has a full API, but again, only for newsletter operators, not readers. AI News by smol.ai was previously on Buttondown; it has since moved to `news.smol.ai`.

---

## Part 2: High-Signal Alternative Sources (Non-Newsletter)

### 2.1 Hacker News — Best-in-Class Signal

The HN API (`hacker-news.firebaseio.com/v0/`) has no rate limits, no auth required, and returns structured JSON. For the briefing pipeline, the best approach is **hnrss.org** which wraps the API into filtered RSS feeds:

```
# Front page posts with 50+ points (vetted community signal)
https://hnrss.org/frontpage?points=50

# AI-keyword filtered posts
https://hnrss.org/newest?q=AI+OR+LLM+OR+machine+learning&points=30

# Support RSS, Atom, and JSON Feed formats
https://hnrss.org/frontpage.jsonfeed?points=50
```

**hnrss.org filtering parameters**:
- `points=N` — only posts with >N points
- `comments=N` — only posts with >N comments
- `q=TERM` — keyword search (supports OR)
- `count=N` — number of results (max 100)

The direct HN API is better for custom scoring: fetch `/v0/topstories.json` (returns 500 story IDs), then batch-fetch individual items via `/v0/item/{id}.json` for full metadata (title, URL, score, comment count). A score threshold of 100+ points produces roughly 10–20 stories/day that are genuine community consensus picks.

### 2.2 arXiv RSS Feeds

arXiv publishes daily RSS feeds for each subject classification. Verified working:

```
# Artificial Intelligence (cs.AI)
https://export.arxiv.org/rss/cs.AI

# Machine Learning (cs.LG) — ~50 papers/day, very high volume
https://export.arxiv.org/rss/cs.LG

# Computation and Language / NLP (cs.CL)
https://export.arxiv.org/rss/cs.CL
```

- Updates: Weekdays only (skips Saturday/Sunday)
- Each item: title, abstract, authors, arXiv ID, subject categories
- For an executive briefing, `cs.AI` is more selective; `cs.LG` is very noisy (~50+/day) and will need LLM filtering

### 2.3 Product Hunt API

GraphQL API at `https://api.producthunt.com/v2/api/graphql`. Auth: developer token (non-expiring, free from their dashboard). Use `OAuth Client Only` flow for public read access. Can query top posts by date with category filters. Good signal for new AI tools/products. **Note**: API terms prohibit commercial use without permission — evaluate applicability for internal briefings.

### 2.4 GitHub Trending

No official API. URL pattern: `https://github.com/trending/python?since=daily`. Community tools:
- `https://github.com/huchenme/github-trending-api` — unofficial scraper-based API
- RSSHub route (when self-hosted): `/github/trending/{language}/{since}` — e.g., `/github/trending/python/daily`

### 2.5 Reddit r/MachineLearning and r/LocalLLaMA

Reddit RSS feeds (`reddit.com/r/MachineLearning/.rss`) were not accessible directly (fetch blocked), but the Reddit JSON API works: `https://www.reddit.com/r/MachineLearning/top.json?t=day&limit=25`. No auth required for read-only public posts. Returns structured JSON with post title, URL, score, num_comments, created_utc.

Better subreddits for signal quality:
- `r/MachineLearning` — academic/research focus
- `r/LocalLLaMA` — open model releases, benchmarks, tooling (very active)
- `r/singularity` — broader AI news (more noise)

### 2.6 Lab/Company Blogs with RSS

Verified working RSS feeds from primary AI labs:

```
# OpenAI
https://openai.com/news/rss.xml

# Google Research
https://research.google/blog/rss/

# Microsoft AI Blog (note: last item from 2022 — possibly stale)
https://blogs.microsoft.com/ai/feed/

# Anthropic — no public RSS found; no XML endpoint at /rss.xml or /news/feed
# Monitor: https://www.anthropic.com/news (scraping or check for Atom link in HTML)
```

---

## Part 3: Email Ingestion — For Newsletters Without RSS

For newsletters that are email-only (Morning Brew, TLDR AI, The Batch, Superhuman AI), email ingestion is the reliable fallback.

### 3.1 Cloudmailin (Recommended)

- **How it works**: Cloudmailin gives you an email address with an MX record. Any email sent to it is HTTP POSTed to your webhook URL as JSON (or multipart/raw).
- **Payload**: Full email headers + plain text + HTML body + attachments. HTML body is the newsletter content.
- **Free tier**: First 10,000 emails/month free — sufficient for 5–10 newsletters × 30 days/month.
- **Storage**: Attachments can be routed to S3/Azure/GCS automatically.
- **Integration**: Your pipeline receives a POST to a Flask/FastAPI endpoint, extracts the HTML body, strips boilerplate, and passes to Claude for summarization.
- **Setup**: Configure an MX record or use their provided address; subscribe newsletters using `yourtopic@yourapp.cloudmailin.net`.

**Cloudmailin JSON payload (relevant fields)**:**
```json
{
  "headers": { "from": "...", "subject": "...", "date": "..." },
  "plain": "plain text body",
  "html": "<html>...full newsletter HTML...</html>",
  "envelope": { "from": "...", "to": "..." }
}
```

### 3.2 Mailparser.io

- Focuses on structured data extraction (good for e-commerce, invoices)
- Supports webhook output, JSON/CSV downloads, Zapier integration
- Less suited for unstructured newsletter prose; Cloudmailin is better for raw HTML delivery

### 3.3 Zapier Email Parser

- Creates `@robot.zapier.com` email address
- Extracts specific fields via parsing rules; triggers Zapier workflows
- Works but adds Zapier dependency and per-task costs; overkill for simple HTML capture

### 3.4 Self-Hosted: postfix + Python

For maximum control with zero external dependency, a lightweight approach:
1. Configure an MX record to a VPS
2. Run `postfix` + a `procmail`/`Python` mail handler
3. Parse with Python's `email` library, extract HTML part, write to queue

This is the most flexible but highest-maintenance option.

---

## Part 4: RSSHub — Bridge for Sources Without Native RSS

RSSHub (`rsshub.app`) is an open-source RSS feed generator that creates feeds from sources that don't publish them natively. It's best run self-hosted.

**Relevant routes** (self-hosted instance at `http://localhost:1200`):
```
# GitHub Trending
/github/trending/python/daily
/github/trending/javascript/daily

# Hacker News (alternative to hnrss.org)
/hackernews/best

# Product Hunt
/producthunt/today

# Twitter/X (requires API credentials)
/twitter/user/{username}

# General: Substack newsletters (redundant — native /feed exists)
/substack/{user}
```

**Note**: The public rsshub.app instance returned HTTP 403 during research. Self-hosting via Docker is the reliable path:
```bash
docker run -d -p 1200:1200 diygod/rsshub
```

---

## Part 5: Technical Implementation Options (Ranked)

### Option A — RSS-First Pipeline (Recommended, Lowest Effort)

**Effort**: Low (hours) | **Quality**: High | **Cost**: Free

Replace or supplement raw feeds with these curated newsletter RSS feeds. The Claude LLM scoring layer already exists in the pipeline; it just needs better inputs.

**Feed list to add immediately:**
```python
CURATED_NEWSLETTER_FEEDS = [
    # Pre-curated AI newsletters — highest signal
    "https://news.smol.ai/rss.xml",                    # AINews — weekday, community aggregated
    "https://importai.substack.com/feed",               # Import AI — weekly, research-focused
    "https://lastweekin.ai/feed",                       # Last Week in AI — weekly roundup
    "https://www.oneusefulthing.org/feed",              # One Useful Thing — weekly, practical
    "https://www.interconnects.ai/feed",                # Interconnects — open models, RLHF
    "https://www.exponentialview.co/feed",              # Exponential View — weekly, business/policy
    "https://simonwillison.net/atom/everything/",       # Simon Willison — daily, high velocity

    # Filtered community signals
    "https://hnrss.org/frontpage?points=50",            # HN top stories (50+ points)
    "https://hnrss.org/newest?q=AI+OR+LLM+OR+GPT&points=30",  # HN AI keyword filter

    # arXiv (selective — use cs.AI, skip cs.LG due to volume)
    "https://export.arxiv.org/rss/cs.AI",

    # Lab announcements
    "https://openai.com/news/rss.xml",
    "https://research.google/blog/rss/",

    # Tech coverage
    "https://techcrunch.com/category/artificial-intelligence/feed/",
    "https://venturebeat.com/category/ai/feed/",
]
```

### Option B — RSS + Email Ingestion Hybrid

**Effort**: Medium (1–2 days) | **Quality**: Highest | **Cost**: Free (Cloudmailin free tier)

Add Cloudmailin to capture email-only newsletters:
1. Sign up for Cloudmailin; get an inbound email address
2. Subscribe `ai-briefing@yourdomain.cloudmailin.net` to: TLDR AI, The Batch, Morning Brew, Superhuman AI, The Rundown AI
3. Add a `/inbound-email` webhook endpoint to the existing pipeline (Flask/FastAPI)
4. Extract HTML body → strip boilerplate → pass to Claude for structured extraction
5. Merge with RSS items before scoring

**Webhook handler skeleton:**
```python
from flask import Flask, request
from bs4 import BeautifulSoup

app = Flask(__name__)

@app.route('/inbound-email', methods=['POST'])
def handle_email():
    data = request.json
    subject = data['headers'].get('subject', '')
    html_body = data.get('html', '')
    sender = data['envelope']['from']

    # Strip boilerplate (unsubscribe links, tracking pixels, headers/footers)
    soup = BeautifulSoup(html_body, 'html.parser')
    for tag in soup.select('.footer, .unsubscribe, [class*="footer"]'):
        tag.decompose()
    clean_text = soup.get_text(separator='\n', strip=True)

    # Feed into existing Claude scoring pipeline
    ingest_newsletter(source=sender, subject=subject, content=clean_text)
    return {'status': 'ok'}, 200
```

### Option C — Beehiiv API (Limited Value)

**Effort**: Medium | **Quality**: Moderate | **Cost**: Free (API key required per publication)

Only viable if you are the operator of a Beehiiv newsletter, or if a newsletter operator grants you API access. For third-party ingestion, this path is blocked — Beehiiv API keys are for newsletter owners, not readers. The API's `posts:read` scope also does not clearly return full body HTML. **Not recommended for third-party newsletter ingestion.**

### Option D — RSSHub Self-Hosted

**Effort**: Medium | **Quality**: Medium | **Cost**: Free (self-hosted)

Useful primarily for GitHub Trending and Product Hunt where no native RSS exists. Run via Docker alongside the existing pipeline. Not necessary if the priority sources above already cover your needs.

### Option E — Web Scraping (Last Resort)

**Effort**: High | **Quality**: Variable | **Cost**: Low

Use Playwright or requests+BeautifulSoup for sources with no RSS and no email alternative. Fragile, maintenance-heavy, potential ToS issues. Viable targets: TLDR AI archive (`tldr.tech/ai`), The Batch archive (`deeplearning.ai/the-batch/`). Only pursue if the source is critical and no other access method works.

---

## Part 6: Quality vs. Quantity Tradeoff Analysis

### Signal Quality Comparison

| Approach | Sources | Items/Day | Pre-curated? | Noise Level |
|---|---|---|---|---|
| 50 raw RSS feeds | News sites, blogs | 500–2000 | No | Very High |
| 10 curated newsletter feeds | Expert curators | 50–150 | Yes | Low |
| HN frontpage (50+ pts) | Community | 10–25 | Crowd-curated | Low |
| arXiv cs.AI | Papers | 20–40 | Peer-reviewed | Medium (relevance varies) |
| Email ingestion (5 newsletters) | Expert curators | 30–80 | Yes | Low |

**Verdict**: 10 curated newsletter feeds + HN filter outperform 50 raw RSS feeds for executive briefing quality. The curators at smol.ai (AINews) alone read 544 Twitter accounts, 12 subreddits, and 24 Discord servers and distill it to a single daily email — that curation work is free for ingestion via RSS.

### Latency Considerations

| Source | Typical Delivery Time | RSS/Webhook Delay |
|---|---|---|
| Hacker News | Real-time (minutes) | ~5 min (polling) |
| TLDR AI | Daily at ~6am ET | Email, same day |
| AINews (smol.ai) | Daily, weekdays | RSS, same day |
| Import AI | Mondays | RSS, same day |
| Last Week in AI | Mondays | RSS, same day |
| arXiv | Weekday mornings ~4am UTC | RSS, same day |
| The Batch | Wednesdays | Email, same day |
| OpenAI/Google blog | As-published | RSS, ~1hr |

For a daily briefing pipeline, a **morning run at 7–8am local time** captures all newsletters from the prior day plus overnight HN. Weekly newsletters (Import AI, Last Week in AI) add depth to Monday briefings. The latency difference between RSS (near-real-time) and email ingestion (same-day) is acceptable for an executive briefing.

---

## Part 7: Recommended Implementation Plan

### Phase 1 — Immediate (Day 1): Replace raw feeds with curated feeds

Update `config/` feed list. Add the 14 RSS feeds from Option A above. Remove or deprioritize low-signal raw feeds (generic tech news RSS, company PR feeds, unfiltered arXiv cs.LG).

Expected outcome: 60–70% reduction in items processed by Claude, higher relevance per item, lower LLM cost.

### Phase 2 — Short-term (Week 1): Add HN and Reddit signals

- Integrate `https://hnrss.org/frontpage?points=50` with the existing RSS fetcher
- Add Reddit JSON API calls for `r/MachineLearning` and `r/LocalLLaMA` top posts (no auth needed for read-only)
- Add metadata tags (source type: `newsletter`, `community`, `research`, `lab`) to aid Claude's scoring prompt

### Phase 3 — Medium-term (Week 2–4): Email ingestion for high-value email-only sources

- Set up Cloudmailin (free tier)
- Subscribe to TLDR AI, The Batch (deeplearning.ai), The Rundown AI
- Add `/inbound-email` webhook handler to the existing pipeline
- HTML stripping via BeautifulSoup before passing to Claude

### Phase 4 — Optional: GitHub Trending

- Self-host RSSHub via Docker for `/github/trending/python/daily`
- Add as a weekend signal source for "what the AI engineering community is building"

---

## Appendix: Quick Reference Feed URLs

### Verified Working (2026-03-11)

```
# Curated AI Newsletters
https://news.smol.ai/rss.xml
https://importai.substack.com/feed
https://lastweekin.ai/feed
https://www.oneusefulthing.org/feed
https://www.interconnects.ai/feed
https://www.exponentialview.co/feed
https://simonwillison.net/atom/everything/
https://aitidbits.ai/feed
https://newsletter.theaiedge.io/feed

# Community Signals
https://hnrss.org/frontpage?points=50
https://hnrss.org/newest?q=AI+OR+LLM+OR+machine+learning&points=30
https://www.reddit.com/r/MachineLearning/top.json?t=day&limit=25  # JSON, not RSS

# Research
https://export.arxiv.org/rss/cs.AI
https://export.arxiv.org/rss/cs.CL

# Lab Announcements
https://openai.com/news/rss.xml
https://research.google/blog/rss/

# Tech News (AI-filtered)
https://techcrunch.com/category/artificial-intelligence/feed/
https://venturebeat.com/category/ai/feed/

# HN Direct API (for custom scoring)
https://hacker-news.firebaseio.com/v0/topstories.json
https://hacker-news.firebaseio.com/v0/item/{id}.json
```

### Email Ingestion Services

| Service | Free Tier | Best For |
|---|---|---|
| Cloudmailin | 10,000 emails/month | Full HTML delivery to webhook; recommended |
| Mailparser.io | Limited free trial | Structured field extraction |
| Zapier Email Parser | Free (with Zapier limits) | If already using Zapier |

### Substack RSS Pattern

Every Substack newsletter: `https://{subdomain}.substack.com/feed`
Custom domain Substack: `https://{custom-domain}/feed` (usually works)

### Beehiiv API (For Operated Newsletters Only)

- Base URL: `https://api.beehiiv.com/v2/`
- Auth: `Authorization: Bearer {API_KEY}`
- Posts: `GET /publications/{pub_id}/posts`
- Docs: `https://developers.beehiiv.com/`

---

*Research conducted 2026-03-11. RSS feed availability may change; verify periodically.*
