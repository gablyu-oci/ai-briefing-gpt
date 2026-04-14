# AI Executive Daily Briefing — Technology Research Document

**Project:** AI-Powered Executive Intelligence Briefing for OCI Leadership
**Prepared:** 2026-03-10
**Scope:** Full-stack technology research covering ingestion, deduplication, ranking, generation, delivery, and analytics on OCI infrastructure.

---

## Table of Contents

1. [News & RSS Ingestion](#1-news--rss-ingestion)
2. [Community Signal APIs](#2-community-signal-apis)
3. [Vector Database for 7-Day Memory & Deduplication](#3-vector-database-for-7-day-memory--deduplication)
4. [Embedding Models](#4-embedding-models)
5. [Email Delivery Platform](#5-email-delivery-platform)
6. [Link Tracking & Analytics](#6-link-tracking--analytics)
7. [LLM Orchestration](#7-llm-orchestration)
8. [Scheduling & Orchestration](#8-scheduling--orchestration)
9. [Object Storage for HTML Archive](#9-object-storage-for-html-archive)
10. [Recommended Full Stack](#10-recommended-full-stack)

---

## 1. News & RSS Ingestion

### 1.1 Python RSS Libraries

#### feedparser (v6.x)
The de-facto standard for RSS/Atom parsing in Python. Handles malformed XML gracefully, supports RSS 0.9x through 2.0, Atom 0.3 and 1.0, and dozens of namespace extensions (Dublin Core, iTunes, Media RSS). Actively maintained, no hard dependencies.

- **Pros:** Battle-tested, lenient parser, handles encoding issues automatically, supports ETags and `Last-Modified` HTTP headers for conditional polling (avoids re-downloading unchanged feeds), parses publication dates into normalized `time.struct_time`.
- **Cons:** Synchronous only — must be wrapped in `asyncio.to_thread` or run in a thread pool for concurrent fetching. No built-in retry logic or rate limiting.
- **Usage pattern for this project:**
  ```python
  import feedparser, httpx
  feed = feedparser.parse("https://feeds.reuters.com/reuters/technologyNews")
  for entry in feed.entries:
      title = entry.title
      published = entry.published_parsed   # time.struct_time UTC
      link = entry.link
      summary = entry.get("summary", "")
  ```
- **Conditional GET support:** Pass stored ETag/Last-Modified in subsequent calls:
  ```python
  feed = feedparser.parse(url, etag=stored_etag, modified=stored_modified)
  if feed.status == 304:
      pass  # nothing new
  ```

#### atoma (v0.0.2)
A strict, typed RSS/Atom parser that raises exceptions on invalid feeds rather than silently degrading. Returns dataclasses instead of dict-like objects.

- **Pros:** Typed output, cleaner API for well-formed feeds.
- **Cons:** Much smaller community, no lenient mode (will break on many real-world feeds from trade press sites), last meaningful commit activity was 2021. **Not recommended** — feedparser's leniency is a feature when ingesting dozens of heterogeneous feeds.

#### aiohttp + feedparser (recommended async pattern)
For high-concurrency ingestion of 50–100+ feeds simultaneously:
```python
import asyncio, aiohttp, feedparser

async def fetch_feed(session, url, etag=None):
    headers = {"If-None-Match": etag} if etag else {}
    async with session.get(url, headers=headers, timeout=10) as resp:
        if resp.status == 304:
            return None
        content = await resp.text()
        return feedparser.parse(content)

async def ingest_all(feed_urls):
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_feed(session, url) for url in feed_urls]
        return await asyncio.gather(*tasks, return_exceptions=True)
```

#### Recommendation
Use **feedparser** as the core RSS parsing library. Wrap all HTTP fetching with **httpx** (async-native, better timeout and retry handling) or **aiohttp**. Store ETag and Last-Modified per feed in Postgres to minimize unnecessary bandwidth and rate-limit exposure.

---

### 1.2 News APIs

#### NewsAPI.org
- **Coverage:** Aggregates ~150,000 news sources globally. Searches article headlines, descriptions, and content.
- **Endpoints:**
  - `GET https://newsapi.org/v2/top-headlines?q=oracle+cloud&apiKey=KEY`
  - `GET https://newsapi.org/v2/everything?q=OCI+AI&from=2026-03-09&sortBy=publishedAt&apiKey=KEY`
- **Rate limits:** Developer (free): 100 requests/day, articles older than 1 month unavailable. Business plan (~$449/month): 250,000 requests/month, full historical access.
- **Cost:** Free tier inadequate for production; Business plan required (~$449/month). [PAID]
- **Reliability:** Generally reliable but article body content is truncated to 200 characters on all plans except the top Enterprise tier. Good for discovery, not full-text ingestion.
- **Verdict:** Useful as a discovery layer for breaking news. Use with keyword sets per briefing section (e.g., `"oracle cloud" OR "OCI"`, `"nvidia datacenter"`, `"openai infrastructure"`).

#### Bing News Search API (Azure Cognitive Services)
- **Coverage:** Broad English-language news, powered by Microsoft's web index. Returns full article snippets (up to ~200 words), source URLs, publication dates.
- **Endpoints:** `https://api.bing.microsoft.com/v7.0/news/search?q=oracle+OCI+AI&freshness=Day&count=100`
- **Rate limits:** S1 tier: 1,000 transactions/month free; S2: 3 calls/second, 1M/month at $3.50/1,000 calls.
- **Cost:** At 20 queries/day × 30 days = 600 calls/month → ~$2.10/month at S2 pricing. [PAID — low cost]
- **Reliability:** Very high. Microsoft production infrastructure.
- **Verdict:** Strong value for discovery. The `freshness=Day` filter ensures only same-day results. Combine with `category=ScienceAndTechnology`.

#### GDELT Project
- **Coverage:** Monitors print, broadcast, and web news media in 100+ languages. Updated every 15 minutes. Free and open.
- **Endpoints:**
  - Full-text search API: `https://api.gdeltproject.org/api/v2/doc/doc?query=oracle+cloud&mode=artlist&maxrecords=75&format=json`
  - TV News API for broadcast monitoring
- **Rate limits:** Officially none stated, but aggressive polling triggers blocks. Recommend ≤1 request/minute per query.
- **Cost:** Free. [FREE]
- **Reliability:** Very high volume but lower precision — includes many foreign-language and low-credibility sources. Requires significant filtering by domain.
- **Verdict:** Excellent for detecting story momentum across many outlets simultaneously — useful for the "momentum" scoring dimension. Use as a signal enrichment source, not primary ingestion.

#### Google News RSS
- **Coverage:** Curated news from Google News across all major publishers.
- **Endpoints:** `https://news.google.com/rss/search?q=oracle+cloud&hl=en-US&gl=US&ceid=US:en`
- **Rate limits:** Unofficial; no documented API. Google does not support this as a formal API. Aggressive polling may result in IP blocks or CAPTCHAs.
- **Cost:** Free. [FREE — with risk]
- **Reliability:** Prone to anti-scraping measures. Google News URLs often redirect to a consent page. Articles are not full-text; only headline + snippet.
- **Verdict:** Usable as a free supplemental source for 10–15 priority keyword topics. Use sparingly, with a polite polling interval of ≥30 minutes. Do not rely on it as a primary source. Always normalize the redirect URLs.

#### Summary Comparison Table

| API | Coverage | Rate Limit | Cost/Month | Full Text | Reliability |
|---|---|---|---|---|---|
| NewsAPI.org | 150K sources | 250K req/mo (Business) | ~$449 | No (truncated) | High |
| Bing News Search | MS web index | 1M req/mo (S2) | ~$2–10 | Snippet | Very High |
| GDELT | 100+ languages | Soft limit | Free | URL only | High volume, low precision |
| Google News RSS | Google curated | Unofficial | Free | Snippet | Moderate (anti-scrape risk) |

**Recommended combination:** Direct RSS feeds (primary) + Bing News Search API (discovery layer) + GDELT (momentum signal). Skip NewsAPI.org due to cost-to-value ratio at this scale.

---

### 1.3 Direct Web Crawlers / Scrapers

For Tier 1 sources (company newsrooms, investor relations, regulatory filings) that do not provide RSS feeds, direct crawling is necessary.

#### httpx + BeautifulSoup (bs4)
- **Best for:** Lightweight, targeted crawling of known, stable HTML pages. Examples: Oracle newsroom, NVIDIA blog, Anthropic news, SEC EDGAR filing listings.
- **Pattern:**
  ```python
  import httpx
  from bs4 import BeautifulSoup

  async def scrape_oracle_newsroom():
      async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
          r = await client.get("https://www.oracle.com/news/",
                               headers={"User-Agent": "OCI-Briefing-Bot/1.0"})
          soup = BeautifulSoup(r.text, "lxml")
          articles = soup.select("article.news-item")
          return [{"title": a.h2.text, "url": a.a["href"]} for a in articles]
  ```
- **Pros:** Fast, async-native with httpx, minimal overhead, easy to schedule.
- **Cons:** Breaks when the target site redesigns. Requires per-site CSS selector maintenance.

#### Playwright (Python)
- **Best for:** JavaScript-rendered sites where the content is loaded via client-side JS and does not appear in the initial HTML response. Examples: some investor relations pages, LinkedIn (if needed), sites behind Cloudflare with JS challenge pages.
- **Pattern:**
  ```python
  from playwright.async_api import async_playwright

  async def scrape_js_page(url):
      async with async_playwright() as p:
          browser = await p.chromium.launch(headless=True)
          page = await browser.new_page()
          await page.goto(url, wait_until="networkidle")
          content = await page.content()
          await browser.close()
          return content
  ```
- **Pros:** Handles virtually any web page including SPA/React/Vue apps.
- **Cons:** Heavyweight — each browser instance consumes ~100–200MB RAM. Slow startup (~2s per launch). Use sparingly; should not be the default. On OCI Compute, install with `playwright install chromium`.
- **When to use:** Reserve for 3–5 critical JS-only sources. Cache results aggressively.

#### Scrapy
- **Best for:** Large-scale crawling of many pages from a single domain (e.g., crawling all posts from a blog archive, following pagination). Has built-in middleware for rate limiting, retries, robots.txt compliance, and item pipelines.
- **Pros:** Industrial-strength, battle-tested, excellent middleware ecosystem, built-in Tor/proxy rotation support.
- **Cons:** Overkill for targeted single-page scraping. Twisted-based async model has a learning curve. Harder to integrate into a simple pipeline script.
- **When to use:** If future scope requires crawling deep site archives (e.g., building initial corpus from 6 months of Data Center Dynamics articles). Not needed at initial scale.

#### Recommendation
Use **httpx + BeautifulSoup** for all static-HTML sources (covers ~80% of Tier 1 sources). Use **Playwright** only for the handful of JS-rendered sources. Skip Scrapy at initial scale.

---

### 1.4 Newsletter Email Parsing

Several high-value sources (e.g., SemiAnalysis, The Information, private analyst newsletters) are delivered only via email and have no RSS feed or accessible website.

#### Architecture: Inbound Email Parsing via Postmark Inbound

1. Set up a dedicated receiving address: `newsletters@briefing.internal` (or a subdomain of a domain you control).
2. Subscribe to newsletters using this address.
3. Configure Postmark Inbound webhook: Postmark parses incoming MIME messages and POSTs structured JSON to your endpoint.
4. The JSON payload includes: `From`, `Subject`, `TextBody`, `HtmlBody`, `Attachments`, `Headers`, and a parsed `MailboxHash`.

**Postmark Inbound webhook payload (abbreviated):**
```json
{
  "From": "newsletter@semianalysis.com",
  "Subject": "SemiAnalysis: NVIDIA B200 supply chain update",
  "TextBody": "This week...",
  "HtmlBody": "<html>...</html>",
  "Date": "Tue, 10 Mar 2026 06:15:00 +0000"
}
```

5. Parse `HtmlBody` with BeautifulSoup; strip headers/footers; extract article blocks.
6. Ingest extracted text into the same normalization pipeline as RSS content.

#### Alternative: Mailparser / Zapier Email Parser
Third-party services that receive email and extract structured data via rules. Easier to set up but introduces an external dependency and costs $~39/month. Not recommended when Postmark Inbound is already in the stack.

#### Alternative: Gmail API + Google Cloud Pub/Sub
If newsletters are already accumulating in a Gmail account, the Gmail API (`users.messages.list`, `users.messages.get`) can fetch and parse them. Push notifications via Pub/Sub can trigger near-real-time processing. Viable if the team already uses Google Workspace.

#### Recommendation
Use **Postmark Inbound** (included with the Postmark account recommended in Section 5). Configure a receiving subdomain, subscribe newsletters to that address, and POST parsed content into the ingestion pipeline. This requires no additional cost beyond the Postmark account.

---

### 1.5 Vendor Blog Monitoring Strategy

Critical Tier 1 sources — these must be polled reliably every run.

#### Sources and Feed URLs

| Vendor | Feed URL | Format |
|---|---|---|
| Oracle Newsroom | `https://www.oracle.com/news/rss/` | RSS |
| Oracle Cloud Blog | `https://blogs.oracle.com/cloud-infrastructure/rss` | RSS |
| NVIDIA Blog | `https://blogs.nvidia.com/feed/` | RSS |
| AWS News Blog | `https://aws.amazon.com/blogs/aws/feed/` | RSS |
| AWS Architecture | `https://aws.amazon.com/blogs/architecture/feed/` | RSS |
| Azure Blog | `https://azure.microsoft.com/en-us/blog/feed/` | RSS |
| Google Cloud Blog | `https://cloud.google.com/blog/rss.xml` | RSS |
| Google DeepMind | `https://deepmind.google/blog/rss.xml` | RSS |
| OpenAI Blog | `https://openai.com/blog/rss.xml` | RSS |
| Anthropic News | `https://www.anthropic.com/news/rss.xml` | RSS |
| Meta AI Blog | `https://ai.meta.com/blog/rss/` | RSS |
| Mistral AI Blog | Scrape: `https://mistral.ai/news/` | HTML |
| Cohere Blog | `https://cohere.com/blog/feed` | RSS |
| Hugging Face Blog | `https://huggingface.co/blog/feed.xml` | Atom |
| AMD Blog | Scrape: `https://community.amd.com/t5/news/bg-p/News` | HTML |
| Intel Newsroom | `https://www.intel.com/content/www/us/en/newsroom/news.rss` | RSS |
| Data Center Dynamics | `https://www.datacenterdynamics.com/en/rss/` | RSS |
| The Register | `https://www.theregister.com/headlines.atom` | Atom |
| CloudWars | Scrape or newsletter | HTML |

#### Monitoring Strategy
- Poll all RSS feeds every **60 minutes** during the 18:00–05:00 UTC window (content publication window for US/EU sources).
- For non-RSS sources (AMD, Mistral, CloudWars), use httpx + BeautifulSoup with a hash-based change detector: store an MD5 of the article listing HTML and re-parse only when it changes.
- Set a descriptive `User-Agent` header: `OCI-Briefing-Bot/1.0 (+https://oracle.com; contact@oracle.com)` to avoid blocks and be transparent.
- Store per-feed metadata in Postgres: `last_polled_at`, `etag`, `last_modified`, `consecutive_error_count`, `is_active`.

---

## 2. Community Signal APIs

Community sources (Tier 4) are explicitly treated as **signal sources, not fact sources**. Their value is in measuring momentum, identifying emerging narratives, and surfacing practitioner sentiment that precedes mainstream press coverage.

### 2.1 HN Algolia Search API

Hacker News data is indexed in real-time by Algolia and available via a free, documented, rate-limit-friendly API. No authentication required.

**Base URL:** `http://hn.algolia.com/api/v1/`

**Key Endpoints:**

```
# Stories from the last 24h matching a keyword, sorted by score
GET https://hn.algolia.com/api/v1/search?query=oracle+cloud&tags=story&numericFilters=created_at_i>UNIX_TIMESTAMP,points>10

# Latest stories (sorted by date, not score)
GET https://hn.algolia.com/api/v1/search_by_date?query=AI+infrastructure&tags=story&numericFilters=created_at_i>UNIX_TIMESTAMP

# Get a specific item (story + all comments)
GET https://hn.algolia.com/api/v1/items/ITEM_ID
```

**Pagination:** Use `page=N` and `hitsPerPage=50` (max 50). Algolia returns `nbHits` total count.

**Rate limits:** No officially published rate limit; community consensus is ~10,000 requests/hour before throttling. For daily briefing purposes, 100–200 requests per run is well within limits.

**Useful numeric filters:**
- `points>25` — filters for stories with meaningful community engagement
- `num_comments>10` — filters for stories generating discussion
- `created_at_i>UNIX_TIMESTAMP` — restrict to last 24h: `int(time.time()) - 86400`

**Filtering strategy for this project:**
```python
import time, httpx

QUERIES = [
    "oracle cloud OCI", "nvidia gpu datacenter", "openai anthropic",
    "AI infrastructure", "cloud computing earnings", "data center power"
]

async def fetch_hn_stories(query, min_points=15, hours_back=24):
    since = int(time.time()) - (hours_back * 3600)
    url = "https://hn.algolia.com/api/v1/search"
    params = {
        "query": query,
        "tags": "story",
        "numericFilters": f"created_at_i>{since},points>{min_points}",
        "hitsPerPage": 50
    }
    async with httpx.AsyncClient() as client:
        r = await client.get(url, params=params)
        return r.json()["hits"]
```

**Weighting:** An HN story with >100 points and >30 comments gets a `momentum_signal = high`. Weight as a signal amplifier on top of a Tier 1/2 story covering the same entity. An HN story with <25 points should only appear in the "Community Signal" section and never elevate a story to the executive summary.

---

### 2.2 Reddit API (PRAW)

Reddit's official Python client. **[PAID for commercial use — requires app registration]**

**Authentication:** Register an app at `https://www.reddit.com/prefs/apps`. Use `script` type for server-side access. OAuth2 client credentials flow.

```python
import praw

reddit = praw.Reddit(
    client_id="YOUR_CLIENT_ID",
    client_secret="YOUR_CLIENT_SECRET",
    user_agent="OCI-Briefing-Bot/1.0 by u/your_reddit_account"
)
```

**Rate limits:** 100 requests per minute per OAuth token. Sufficient for daily batch runs.

**Relevant subreddits:**
| Subreddit | Signal type |
|---|---|
| r/MachineLearning | Research, model releases, academic signal |
| r/LocalLLaMA | Open-source model adoption, OSS momentum |
| r/CloudComputing | Enterprise practitioner sentiment |
| r/aws, r/googlecloud, r/AZURE | Competitor product signal |
| r/networking | Infrastructure/interconnect signal |
| r/sysadmin | Practitioner frustration signals |
| r/datascience | AI tooling adoption |
| r/StockMarket, r/investing | Financial community signal on tech earnings |

**Useful PRAW patterns:**
```python
# Top posts in the last 24h
subreddit = reddit.subreddit("MachineLearning")
for post in subreddit.top(time_filter="day", limit=25):
    if post.score > 50:
        process_post(post.title, post.url, post.score, post.num_comments)

# Search across multiple subreddits
for post in reddit.subreddit("MachineLearning+LocalLLaMA+CloudComputing").search(
    "oracle OR OCI OR NVIDIA", sort="new", time_filter="day", limit=50
):
    process_post(...)
```

**Post scoring for this project:**
- `upvote_ratio > 0.85` and `score > 100`: strong positive signal
- Award count: meaningful proxy for "this matters to practitioners"
- Comment count relative to upvotes: high comment/upvote ratio often indicates controversy, not just interest

**Weighting:** Reddit is a sentiment and weak-signal layer. Use r/MachineLearning and r/LocalLLaMA posts as early indicators for open-source model releases that may not yet appear in press. Flag any post with >500 upvotes and a direct link to a GitHub repo or paper as a potential "OSS momentum" item for Greg Pavlik's briefing.

---

### 2.3 GitHub Trending

GitHub has no official trending API. The `https://github.com/trending` page is JavaScript-rendered, but the underlying data can be obtained via two approaches:

#### Option A: Scrape github.com/trending (recommended)
The trending page has a stable enough HTML structure for simple scraping. Use httpx + BeautifulSoup:

```python
async def fetch_github_trending(language="", since="daily"):
    url = f"https://github.com/trending/{language}?since={since}"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; OCI-Briefing-Bot/1.0)"}
    async with httpx.AsyncClient() as client:
        r = await client.get(url, headers=headers)
    soup = BeautifulSoup(r.text, "lxml")
    repos = []
    for article in soup.select("article.Box-row"):
        repo_path = article.h2.a["href"].strip("/")
        description = article.p.text.strip() if article.p else ""
        stars_today = article.select_one("span.d-inline-block.float-sm-right")
        repos.append({
            "repo": repo_path,
            "description": description,
            "stars_today": stars_today.text.strip() if stars_today else "0"
        })
    return repos
```

Fetch for: `since=daily` in languages `python`, `typescript`, `rust`, `go`, and the unfiltered all-languages view.

#### Option B: GitHub REST API — stars velocity proxy
No trending endpoint, but you can compute trending manually:
```
GET https://api.github.com/search/repositories?q=topic:llm+created:>2026-03-01&sort=stars&order=desc
```
Rate limit: 30 requests/minute (unauthenticated), 60 requests/minute (authenticated). [FREE with GitHub account]

#### Weighting
GitHub trending repos are the strongest early signal for OSS model releases and tooling adoption — often appearing on trending 24–48h before mainstream press coverage. A repo with >500 stars/day appearing in the AI/ML category is a strong "AI Platform & Model News" signal. Include in Greg Pavlik's briefing under "OSS/innovation" section.

---

### 2.4 Signal vs. Fact Source Treatment

| Source | Use as Fact? | Use as Signal? | Effect on Score |
|---|---|---|---|
| HN story (>100 pts) | No | Yes — momentum | +0.1 to `momentum` score of matching Tier 1/2 story |
| HN story (<25 pts) | No | Weak | No score effect; Community Signal section only |
| Reddit post (>500 ups) | No | Yes — sentiment | +0.05 to `momentum`; note in "Community Signal" |
| GitHub trending repo | No | Yes — OSS signal | Creates standalone "OSS Momentum" item in AI section |
| GitHub trending repo (>1000 stars/day) | No | Strong — breaking | May surface as "watch item" even without press coverage |

Editorial rule: No community post becomes a headline story without corroboration from a Tier 1 or Tier 2 source.

---

## 3. Vector Database for 7-Day Memory & Deduplication

The memory system needs to:
1. Store embeddings for all ingested articles for the last 7 days (~1,500–5,000 vectors at typical volume).
2. Perform approximate nearest-neighbor (ANN) search at ingestion time to detect semantic duplicates.
3. Support metadata filtering (by date, source tier, section, story_cluster_id) alongside vector search.
4. Be deployable on OCI.

### 3.1 pgvector (PostgreSQL Extension)

pgvector adds a `vector` column type and HNSW/IVFFlat indexes to PostgreSQL. Since the project already needs Postgres for canonical truth (articles, story clusters, sent history, audience profiles), pgvector eliminates a separate service.

**Setup on OCI:**
- OCI Database with PostgreSQL is GA and supports pgvector as of PostgreSQL 15+.
- Alternatively, install PostgreSQL 16 + pgvector on OCI Compute: `sudo apt install postgresql-16-pgvector`.

**Schema example:**
```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE article_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    article_id UUID REFERENCES articles(id),
    embedding vector(1536),  -- for text-embedding-3-small
    published_at TIMESTAMPTZ NOT NULL,
    story_cluster_id UUID,
    section TEXT
);

CREATE INDEX ON article_embeddings USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

**7-day similarity query:**
```sql
SELECT article_id, 1 - (embedding <=> $1::vector) AS similarity
FROM article_embeddings
WHERE published_at > NOW() - INTERVAL '7 days'
ORDER BY embedding <=> $1::vector
LIMIT 10;
```

**Pros:**
- Single service — no additional infrastructure. Postgres already runs for everything else.
- ACID transactions: deduplication check and insert happen atomically.
- Metadata filtering is native SQL — no special hybrid search syntax.
- Cost: free extension, no extra OCI service.
- pgvector HNSW index performs well for the scale here (<10,000 vectors, well within the sweet spot).

**Cons:**
- Not designed for vector-first workloads. At very large scale (millions of vectors), dedicated vector DBs outperform.
- HNSW index in pgvector is not as tunable as Qdrant's implementation.
- Similarity search scans the full index in memory — RAM must accommodate the index.

**At this project's scale:** 7 days × ~500 articles/day × 1536 floats × 4 bytes = ~21 MB of raw vector data. Trivially small. pgvector is an excellent fit.

---

### 3.2 Qdrant

A dedicated vector database written in Rust. Supports HNSW with payload filtering, collections, and a REST/gRPC API. Available as a self-hosted Docker image or managed cloud service.

**Deployment on OCI:** Run as a Docker container on the OCI Compute instance:
```bash
docker run -d --name qdrant -p 6333:6333 -p 6334:6334 \
  -v /data/qdrant:/qdrant/storage qdrant/qdrant:latest
```

**Python client:**
```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, Range

client = QdrantClient(host="localhost", port=6333)

# Search with date filter
results = client.search(
    collection_name="articles",
    query_vector=embedding,
    query_filter=Filter(
        must=[FieldCondition(key="published_ts", range=Range(gte=seven_days_ago_ts))]
    ),
    limit=10
)
```

**Pros:**
- Extremely fast ANN search with filtered queries (Qdrant is designed for hybrid vector + payload filter).
- Rich payload support: store any JSON metadata alongside each vector.
- Built-in sparse vector support (for keyword-based hybrid search) since v1.7.
- Rust-based: very low memory overhead per vector, excellent performance under load.

**Cons:**
- An additional service to operate (Docker container, storage volume management, backups).
- Adds operational complexity for marginal benefit at this scale.
- Self-hosted on OCI Compute: you manage upgrades, backups, and persistence.
- Qdrant Cloud: managed option, free tier (1GB), paid tiers from ~$25/month. [PAID]

**At this project's scale:** Qdrant is technically superior but operationally more complex than pgvector for a 500-articles/day use case.

---

### 3.3 Pinecone

Fully managed vector database as a service.

- **Serverless plan:** Free up to 2GB storage; beyond that, $0.096/GB-month storage + $2/million read units.
- **Pod-based:** Starts at ~$70/month for a p1.x1 pod.
- **API:** REST and Python SDK. Simple to integrate.
- **Cons:** External service dependency. Data leaves your control (relevant for executive-level content). No OCI native integration. At this project's scale, the free serverless tier would suffice, but the data residency and third-party dependency concerns outweigh the convenience.

**Verdict:** Not recommended for this use case. pgvector keeps everything in OCI and eliminates a third-party dependency.

---

### 3.4 Recommendation

**Use pgvector on the same PostgreSQL instance used for the canonical data store.**

Rationale:
- At <10,000 active vectors (7-day window), pgvector HNSW performance is indistinguishable from Qdrant.
- Eliminates a separate service, simplifying deployment and operations.
- Keeps all data on OCI — no external vector DB dependency.
- Atomic deduplication: check similarity and insert in a single transaction.
- Zero additional cost.

If the system eventually scales to processing >50,000 articles/day or needs vector search with complex payload filtering at sub-10ms latency, migrate to Qdrant at that point.

---

## 4. Embedding Models

Embeddings are used for:
1. **Deduplication:** Is this new article semantically similar to one sent in the last 7 days?
2. **Story clustering:** Does this article belong to an existing story cluster?
3. **Audience relevance scoring:** How similar is this article to a given audience's interest profile?

Requirements: Fast, low-cost, high quality on short texts (headlines + 2-sentence summaries), deployable with low latency.

### 4.1 OpenAI text-embedding-3-small

- **Dimensions:** 1536 (default) or configurable to 512/256 via the `dimensions` parameter (Matryoshka representation).
- **Context window:** 8,191 tokens.
- **Cost:** $0.02 per 1M tokens. [PAID]
- **Latency:** ~50–150ms per API call (single embedding). Supports batch up to 2048 inputs per call.
- **Quality:** Excellent for English-language news content. MTEB benchmark: 62.3 (outperforms all models in its price class).
- **Usage:**
  ```python
  from openai import AsyncOpenAI
  client = AsyncOpenAI()

  async def embed_batch(texts: list[str]) -> list[list[float]]:
      response = await client.embeddings.create(
          model="text-embedding-3-small",
          input=texts,
          dimensions=512  # reduce storage while preserving quality
      )
      return [d.embedding for d in response.data]
  ```
- **Cost at scale:** 40 articles/day × 365 days = 14,600 articles/year. Each article: ~100 tokens (headline + summary). Total: ~1.46M tokens/year = **$0.029/year**. Negligible.

### 4.2 OpenAI text-embedding-3-large

- **Dimensions:** 3072.
- **Cost:** $0.13 per 1M tokens — 6.5x more expensive than small.
- **Quality:** Better on complex multilingual tasks. MTEB: 64.6.
- **Verdict:** Overkill for English-language headline deduplication. The quality delta over `text-embedding-3-small` does not justify 6.5x cost increase for this use case.

### 4.3 Anthropic / Claude Embeddings

As of the research date (March 2026), Anthropic does not offer a standalone embedding model API. Claude models are generative only. For embedding needs in an Anthropic-centric stack, you must use an external embedding provider. This may change — monitor `https://docs.anthropic.com/` for embedding API announcements.

### 4.4 Open-Source: sentence-transformers

- **Library:** `sentence-transformers` (HuggingFace). Models run locally, no API cost.
- **Recommended model:** `BAAI/bge-small-en-v1.5` (384 dimensions, 22M params, 42MB download)
  - MTEB English score: 62.17 — competitive with `text-embedding-3-small`.
  - Inference time: ~5ms per text on CPU, <1ms on GPU.
- **Alternative:** `BAAI/bge-large-en-v1.5` (1024 dimensions, 335M params) — MTEB: 63.55, slower.
- **Alternative:** `intfloat/e5-small-v2` — slightly lower quality, very fast.

```python
from sentence_transformers import SentenceTransformer
model = SentenceTransformer("BAAI/bge-small-en-v1.5")

def embed_batch(texts: list[str]) -> list[list[float]]:
    return model.encode(texts, normalize_embeddings=True).tolist()
```

- **Pros:** Zero API cost, no external dependency, runs on OCI Compute, full data sovereignty.
- **Cons:** Requires OCI Compute instance with enough RAM (~1–2GB for `bge-small`). Cold start if running serverless. CPU inference adds ~50–200ms per batch of 40 articles.
- **On OCI Compute (VM.Standard.E4.Flex, 2 OCPU, 16GB RAM):** BGE-small runs comfortably; inference for 40 articles ≈ 200–500ms total. Acceptable.

### 4.5 Recommendation

**Use `BAAI/bge-small-en-v1.5` (sentence-transformers) as the primary embedding model.**

Rationale:
- MTEB quality is on par with OpenAI `text-embedding-3-small` for English news.
- Zero recurring API cost. At ~14,600 articles/year, even OpenAI's cost is negligible ($0.03), but local embedding eliminates external API latency, eliminates a dependency, and keeps all article content on-premises.
- Runs on CPU in an acceptable time window for a batch job (5am daily run).
- If embedding quality proves insufficient for deduplication accuracy, upgrade to `bge-large-en-v1.5` or switch to OpenAI `text-embedding-3-small` — the interface is identical.

Store embeddings at **512 dimensions** (even for BGE, use PCA/truncation via `sentence-transformers` or pgvector's `halfvec` type for storage efficiency).

---

## 5. Email Delivery Platform

Requirements:
- Send 4 HTML emails per day (one per audience profile).
- Track opens and link clicks per email.
- Expose click/open data via API for analytics integration.
- High deliverability (these are C-suite recipients; landing in spam is unacceptable).
- Template support for rendering the HTML briefing.
- Handle inbound email parsing for newsletter ingestion (see Section 1.4).

### 5.1 Postmark

A transactional email service focused on deliverability. Used by thousands of SaaS companies for critical email.

- **Deliverability:** Industry-leading. Postmark maintains a separate IP pool for transactional vs. bulk email. SPF, DKIM, DMARC fully supported. Average delivery time: <10 seconds.
- **Open tracking:** Pixel-based. Configured per message stream. API: `GET https://api.postmarkapp.com/messages/outbound/opens?count=50&offset=0` returns open events with timestamp, user agent, geo.
- **Click tracking:** Postmark wraps all links in messages with a redirect URL, tracking clicks. API: `GET https://api.postmarkapp.com/messages/outbound/clicks?count=50&offset=0`.
- **Template support:** Postmark Templates API allows storing and rendering Mustache/Handlebars templates server-side. Alternatively, render HTML in your pipeline and send via the API's `HtmlBody` parameter — recommended for this project (your renderer has full control).
- **Inbound parsing:** Postmark Inbound is a mature product — parses incoming email to a webhook (see Section 1.4). Included with the account.
- **Pricing:**
  - 100 emails/month free.
  - 1,000 emails/month: $15/month.
  - 10,000/month: $50/month.
  - At 4 emails/day × 30 days = 120 emails/month → **$15/month**. [PAID]
- **API example:**
  ```python
  import httpx

  async def send_briefing(to_email, subject, html_body):
      async with httpx.AsyncClient() as client:
          r = await client.post(
              "https://api.postmarkapp.com/email",
              headers={"X-Postmark-Server-Token": "YOUR_TOKEN"},
              json={
                  "From": "briefing@yourdomain.com",
                  "To": to_email,
                  "Subject": subject,
                  "HtmlBody": html_body,
                  "TrackOpens": True,
                  "TrackLinks": "HtmlAndText",
                  "MessageStream": "outbound"
              }
          )
  ```
- **Verdict:** Best-in-class for this use case.

### 5.2 SendGrid (Twilio)

- **Deliverability:** High but historically inconsistent due to shared IP pool abuse by other customers.
- **Open/click tracking:** Supported. Event Webhook POSTs events to your endpoint in real-time. Also has an email analytics dashboard.
- **Template support:** Dynamic transactional templates with Handlebars.
- **Pricing:**
  - Free: 100 emails/day (3,000/month). At 4/day, the **free tier is sufficient**.
  - Essentials 50K: $19.95/month.
- **Inbound parsing:** SendGrid Inbound Parse webhook — similar to Postmark Inbound.
- **Cons:** Free tier IPs are shared and have had deliverability issues. For C-suite recipients, this is unacceptable. Paid plans provide dedicated IPs.
- **Verdict:** Free tier is attractive but deliverability risk is too high for executive recipients. Requires paid plan for dedicated IPs, at which point Postmark is preferred.

### 5.3 AWS SES (Simple Email Service)

- **Deliverability:** Solid when properly warmed up. Must manage IP warm-up yourself for dedicated IPs, or use shared IPs with strong domain reputation.
- **Open/click tracking:** Via Configuration Sets + SNS/SQS event destinations. More complex to set up than Postmark/SendGrid.
- **Pricing:** $0.10 per 1,000 emails. At 120 emails/month: **$0.012/month** — essentially free.
- **Cons:** Not OCI-native. Heavier configuration burden. No native inbound parsing equivalent to Postmark Inbound. Requires SQS/Lambda for event processing.
- **Verdict:** Extremely cost-effective at scale, but the operational overhead and lack of inbound email parsing make it less attractive at initial scale.

### 5.4 OCI Email Delivery

OCI's native SMTP relay service.

- **Deliverability:** Adequate for general use. Supports DKIM. Less established reputation than Postmark/SendGrid's dedicated infrastructure.
- **Open/click tracking:** None built-in. You would need to implement tracking pixels and redirect links yourself.
- **Inbound:** Not supported — OCI Email Delivery is outbound-only.
- **Pricing:** Free for first 100 emails/day per tenancy. Beyond that: $0.085/1,000 emails.
- **Cons:** No analytics, no inbound parsing, lower deliverability reputation than specialized services. Would require building all tracking infrastructure from scratch.
- **Verdict:** Not viable for this use case due to missing tracking capabilities. Use as a fallback relay only.

### 5.5 Recommendation

**Use Postmark** as the primary email delivery service.

Rationale:
- Best-in-class deliverability for transactional email — critical for C-suite recipients.
- Open and click tracking APIs are mature and well-documented — directly answers the analytics requirements.
- Inbound parsing for newsletter ingestion is included at no additional cost.
- $15/month for 120 emails/month is negligible.
- Single vendor for both outbound and inbound email simplifies the stack.

---

## 6. Link Tracking & Analytics

Every story link in the briefing must be uniquely tracked to answer: which exec clicked which story in which section on which day. The briefing also needs to capture email opens (handled by Postmark — see Section 5).

### 6.1 Bitly API

- **Function:** URL shortening + click tracking + UTM parameter support.
- **Endpoints:**
  - Create link: `POST https://api-ssl.bitly.com/v4/shorten`
  - Get link clicks: `GET https://api-ssl.bitly.com/v4/bitlinks/{bitlink_id}/clicks`
- **Cost:**
  - Free: 1,000 branded links/month, basic analytics.
  - Core: $35/month — custom domains, 3,000 links/month, click-by-country/device.
  - Growth: $200/month — full API access, unlimited links.
- **Pros:** Widely recognized, short URLs look clean in email, API is straightforward.
- **Cons:** At 40 stories × 4 audiences = 160 unique links/day × 30 days = 4,800 links/month. Requires Core plan at minimum ($35/month). [PAID] Data lives on Bitly's servers. Click analytics are aggregated, not per-recipient (Bitly does not know which of your 4 recipients clicked).
- **Verdict:** Bitly does not support per-recipient link tracking without hacking the system (creating one link per recipient per story = 160 links/day × 4 = 640/day, exceeding all reasonable plan limits). Not the right tool for this use case.

### 6.2 Custom Redirect Service (Self-Hosted on OCI) — Recommended

Build a lightweight redirect microservice hosted on OCI that generates unique per-audience, per-story tracking URLs and logs all clicks.

**Architecture:**
- FastAPI application on OCI Compute (same VM as the main pipeline, or a separate small instance).
- Each story link is replaced with: `https://track.yourdomain.com/r/{token}`
- `token` is a short UUID or hash encoding: `{story_id}_{audience_id}_{date}_{section}_{position}`.
- On click: log the event to Postgres, then 302-redirect to the canonical article URL.

**Database schema:**
```sql
CREATE TABLE tracking_links (
    token VARCHAR(32) PRIMARY KEY,
    story_id UUID REFERENCES stories(id),
    audience_id VARCHAR(50),
    briefing_date DATE,
    section TEXT,
    position_in_section INT,
    canonical_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE click_events (
    id SERIAL PRIMARY KEY,
    token VARCHAR(32) REFERENCES tracking_links(token),
    clicked_at TIMESTAMPTZ DEFAULT NOW(),
    user_agent TEXT,
    ip_hash TEXT  -- hashed for privacy
);
```

**FastAPI redirect handler:**
```python
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
import asyncpg

app = FastAPI()

@app.get("/r/{token}")
async def redirect(token: str, request: Request):
    async with db_pool.acquire() as conn:
        link = await conn.fetchrow(
            "SELECT canonical_url FROM tracking_links WHERE token=$1", token
        )
        if link:
            await conn.execute(
                "INSERT INTO click_events (token, user_agent, ip_hash) VALUES ($1, $2, $3)",
                token, request.headers.get("user-agent"), hash_ip(request.client.host)
            )
            return RedirectResponse(url=link["canonical_url"], status_code=302)
    return {"error": "link not found"}, 404
```

**Link generation at render time:**
```python
import secrets

def create_tracking_url(story_id, audience_id, briefing_date, section, position, canonical_url):
    token = secrets.token_urlsafe(12)
    # INSERT INTO tracking_links ...
    return f"https://track.yourdomain.com/r/{token}"
```

- **Cost:** Runs on existing OCI Compute. OCI Load Balancer: ~$10/month if needed (at 4 recipients, not needed initially — just expose via nginx). OCI Compute already running: no incremental cost.
- **Pros:** Full per-recipient, per-story, per-section tracking. Data stays on OCI. Complete control over analytics. Can add "More like this" / "Less like this" feedback buttons as additional GET parameters.
- **Cons:** Must maintain the redirect service. Need a custom domain with SSL cert (OCI Certificate Service, free for OCI Load Balancer).

### 6.3 UTM Parameters with GA4

Append UTM parameters to all story URLs:
`https://article.com/story?utm_source=oci-briefing&utm_medium=email&utm_campaign=2026-03-10&utm_content=karan-batta_competitive_story-123`

- **Pros:** Free. Works with any GA4 property. No infrastructure required.
- **Cons:** UTM parameters are visible to the destination site (minor privacy/competitive concern). GA4 reports are aggregate — cannot easily answer "did Karan click this story?" without complex custom dimensions. Only tracks users who have GA4 on the destination site. **Cannot track clicks on Oracle/NVIDIA/press release URLs that don't use GA4.**
- **Verdict:** Too limited for per-audience analytics. Cannot answer the core question of which exec engages with which content.

### 6.4 Recommendation

**Build a custom redirect service on OCI Compute** with PostgreSQL storage for click events.

Rationale:
- Only approach that delivers true per-audience, per-story, per-section click analytics.
- Data stays on OCI — appropriate for executive-level content.
- Minimal incremental infrastructure (FastAPI + nginx on existing OCI Compute).
- Enables "More like this" / "Less like this" feedback buttons with no additional infrastructure (just additional GET parameters).
- Use UTM parameters as a secondary layer on redirected URLs for downstream destination-site analytics where relevant.

Combine with Postmark's open tracking (pixel-based, per-recipient) for a complete picture: open + click + section + story + position.

---

## 7. LLM Orchestration

The LLM layer handles:
1. **Scoring/classification:** Is this story relevant to OCI? Which section does it belong to? What is the strategic impact? (~cheap, high volume)
2. **Summary generation:** Generate 2–4 sentence summary per story per audience. (moderate cost)
3. **OCI Implication generation:** "Why this matters to OCI." (moderate cost)
4. **Executive summary bullets:** Generate the top 3–5 bullets for each audience. (higher quality needed)

### 7.1 Claude claude-opus-4-6 with Extended Thinking

As of March 2026, Claude claude-opus-4-6 is Anthropic's most capable model, with extended thinking (adaptive reasoning) for complex tasks.

- **API:** `anthropic.messages.create(model="claude-opus-4-6", thinking={"type": "enabled", "budget_tokens": 5000})`
- **Strengths:** Superior reasoning on ambiguous strategic questions (e.g., "Is this a threat or opportunity for OCI?"), nuanced multi-audience personalization, best quality for executive summary bullets.
- **Cost (input):** ~$15/M input tokens. (output): ~$75/M output tokens. [PAID — premium]
- **Thinking tokens:** Budget at 2,000–5,000 tokens for strategic analysis tasks. Thinking tokens are counted as output tokens.
- **Best use in this pipeline:**
  - Generating "OCI Implication" for top 5 stories per day.
  - Generating the Executive Summary section (3–5 bullets) per audience.
  - Follow-up delta analysis: "Does this article add materially new information to the existing cluster?"
- **Not recommended for:** Batch classification of 40+ articles (use Claude Haiku).

### 7.2 Claude claude-haiku-4-5

Fast, cost-effective Claude model for high-volume, lower-complexity tasks.

- **Cost:** ~$0.80/M input, ~$4.00/M output tokens. [PAID — economical]
- **Latency:** ~1–3 seconds per call. Well-suited for batch processing.
- **Best use in this pipeline:**
  - Article classification: which section does this belong to? (Financial, Power, Datacenter, etc.)
  - Relevance scoring: 1–10 relevance score per audience profile per article.
  - Story deduplication decision: is this a true follow-up or a duplicate?
  - Individual article summaries (2–4 sentences) for body sections (Sections 2–7 of the briefing).
  - Entity extraction: companies, executives, locations, numbers.

### 7.3 Prompt Design Patterns for Multi-Audience Generation

**Pattern: Generate once, personalize via prompt injection**

Rather than generating N independent summaries per article (one per audience), use a two-stage approach:

**Stage 1 — Canonical summary (Haiku):** Generate one neutral, factual 3-sentence summary of the article covering: what happened, who is involved, key numbers.

**Stage 2 — Audience personalization (Haiku or Opus):** Given the canonical summary + audience profile, generate the personalized version.

```python
CANONICAL_PROMPT = """
You are a technology news analyst. Given the article below, generate:
1. A factual 2-3 sentence summary (neutral tone, no opinion)
2. Key entities: companies, people, locations, numbers, dates
3. Event type: one of [launch, partnership, funding, expansion, outage, regulatory, earnings, research, acquisition]
4. Strategic relevance tags: [AI_infra, cloud_compete, datacenter_power, AI_models, deals, financial, OSS]

Article:
TITLE: {title}
SOURCE: {source}
BODY: {body}

Respond in JSON.
"""

AUDIENCE_PROMPT = """
You are writing a briefing for {audience_name}, {audience_title} at Oracle.
Their focus areas: {topics_of_interest}
Their tone preference: {preferred_tone}

Given this canonical story summary:
{canonical_summary}

Write:
1. A {max_length}-word briefing item with the appropriate emphasis for this executive
2. One sentence on "Why this matters for OCI"
3. Confidence tag: confirmed | credible_report | weak_signal | follow_up

Keep it concise, strategic, and implication-focused.
"""
```

**Pattern: Batch classification with structured output**

Use Haiku's structured output (JSON mode) to classify all 40 articles in a single prompt:

```python
BATCH_SCORE_PROMPT = """
You will score {n} news articles for relevance to an OCI executive briefing.

For each article, output JSON with:
- section: one of [financial, power_datacenter, competitive, ai_models, deals, community_signal, suppress]
- relevance_score: 0.0-1.0 (how relevant to cloud infrastructure and AI markets)
- strategic_impact: low | medium | high | critical
- suppress_reason: if section=suppress, explain why

Articles:
{articles_json}
"""
```

### 7.4 Cost Estimation

**Assumptions:**
- 40 articles/day ingested, scored, summarized.
- 4 audience profiles.
- Pipeline runs once daily.

**Step-by-step cost breakdown:**

| Task | Model | Input tokens | Output tokens | Cost/day |
|---|---|---|---|---|
| Canonical summary × 40 articles | Haiku | 40 × 500 = 20,000 | 40 × 200 = 8,000 | $0.016 + $0.032 = **$0.048** |
| Batch scoring × 40 articles | Haiku | 1 × 8,000 = 8,000 | 1 × 2,000 = 2,000 | $0.006 + $0.008 = **$0.014** |
| Audience summaries × 40 × 4 | Haiku | 160 × 400 = 64,000 | 160 × 150 = 24,000 | $0.051 + $0.096 = **$0.147** |
| OCI Implication × 10 key stories | Opus | 10 × 800 = 8,000 | 10 × 200 = 2,000 | $0.120 + $0.150 = **$0.270** |
| Executive Summary bullets × 4 | Opus | 4 × 3,000 = 12,000 | 4 × 500 = 2,000 | $0.180 + $0.150 = **$0.330** |
| Follow-up delta analysis × 10 | Haiku | 10 × 600 = 6,000 | 10 × 100 = 1,000 | $0.005 + $0.004 = **$0.009** |
| **TOTAL** | | | | **~$0.82/day** |

**Monthly cost estimate: ~$25/month for LLM API calls.**
**Annual: ~$300/year.**

This is a conservative estimate. With prompt caching (Anthropic supports prompt caching for repeated system prompts), costs can be reduced by 30–50% on the audience personalization step.

---

## 8. Scheduling & Orchestration

The pipeline must:
1. Run daily at ~05:00 local time (before executives arrive).
2. Execute in a defined sequence: ingest → normalize → deduplicate → score → rank → generate → render → send → archive.
3. Have retry logic for transient failures (API timeouts, etc.).
4. Alert on failure before the send step (so a human can intervene if needed).
5. Track pipeline run history (what ran, what failed, what was sent).

### 8.1 Simple Cron on OCI Compute

Run the pipeline as a Python script triggered by the OS cron daemon on an OCI Compute instance.

```cron
# /etc/cron.d/briefing
0 5 * * * ubuntu /home/ubuntu/briefing/venv/bin/python /home/ubuntu/briefing/run_pipeline.py >> /var/log/briefing/pipeline.log 2>&1
```

- **Pros:** Zero additional infrastructure. Dead simple. The OCI Compute instance is already running (for the redirect service, Postgres, etc.). Full Python ecosystem available. Easy to debug locally.
- **Cons:** No built-in retry logic (must implement in the script). No failure alerting without additional setup. No visual pipeline monitoring. If the instance is down or rebooting, the job is skipped silently.
- **Retry pattern in Python:**
  ```python
  import tenacity

  @tenacity.retry(
      stop=tenacity.stop_after_attempt(3),
      wait=tenacity.wait_exponential(multiplier=2, min=10, max=120),
      reraise=True
  )
  async def ingest_feed_with_retry(url):
      return await ingest_feed(url)
  ```
- **Failure alerting:** Use OCI Notifications + OCI Monitoring, or simply send a Postmark/SMTP alert email on unhandled exception:
  ```python
  import sys
  try:
      asyncio.run(run_pipeline())
  except Exception as e:
      send_alert_email(f"Briefing pipeline failed: {e}")
      sys.exit(1)
  ```

### 8.2 OCI Functions + OCI Scheduler

OCI Functions is a serverless compute service (Oracle's FaaS, based on Fn Project). OCI Scheduler triggers functions on a cron schedule.

- **Pros:** No always-on VM for the pipeline itself. Auto-scaling. OCI-native — integrates with OCI Logging, OCI Monitoring, OCI Vault for secrets.
- **Cons:**
  - 5-minute max function execution timeout — the full pipeline (ingestion + LLM calls + rendering) will exceed 5 minutes. **This is a hard blocker.** The Extended Runs feature allows up to 120 minutes but is not available in all OCI regions.
  - Cold start latency (seconds to minutes for a Python function with ML dependencies).
  - Complex dependency management: embedding model (~400MB), Playwright, etc. must be packaged into a Docker image.
  - Debugging is significantly harder than a local Python script.
  - OCI Functions pricing: first 2M invocations/month free, then $0.20/million. Cost is negligible.
- **Hybrid approach:** Use OCI Scheduler to trigger a webhook on the OCI Compute VM (which starts the pipeline as a subprocess). This gives you the scheduling convenience of OCI Scheduler without the FaaS execution constraints.
- **Verdict:** Not recommended as primary orchestration for a long-running pipeline. The 5-minute timeout is prohibitive.

### 8.3 GitHub Actions Scheduled Workflows

```yaml
# .github/workflows/daily-briefing.yml
on:
  schedule:
    - cron: '0 5 * * *'  # 05:00 UTC daily
  workflow_dispatch:  # Manual trigger

jobs:
  run-briefing:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: '3.12'}
      - run: pip install -r requirements.txt
      - run: python run_pipeline.py
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          POSTMARK_API_KEY: ${{ secrets.POSTMARK_API_KEY }}
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
```

- **Pros:** Free for public repos and generous for private repos (2,000 minutes/month on free plan). Built-in retry via `retry` action step. Native failure notifications via GitHub notifications. Version-controlled pipeline definition. Easy to trigger manually.
- **Cons:** Pipeline has internet-accessible runner (GitHub-hosted) making database connections — requires either a public OCI Postgres endpoint (security concern) or SSH tunnel / VPN setup. Scheduled jobs on GitHub Actions can be delayed by 15–30 minutes during high-load periods — not acceptable for a 5am briefing with an executive expecting it by 6am. Embeddings/ML model downloads from HuggingFace on every run (slow, ~400MB).
- **Verdict:** Viable as a secondary/backup mechanism and for non-time-critical tasks (e.g., weekly analytics reports). The scheduler jitter is a real risk for the primary daily briefing.

### 8.4 Recommendation

**Use cron on OCI Compute as the primary scheduler**, with structured pipeline code that includes retry logic, step-by-step logging, and failure alerting.

Enhance the cron approach with:

1. **Structured pipeline runner with step tracking:**
   ```python
   # Each pipeline step records start/end/status in Postgres
   # pipeline_runs table: run_id, step, status, started_at, completed_at, error
   ```

2. **OCI Notifications for failure alerting:**
   - Create an OCI Notifications topic.
   - Subscribe the engineering email/Slack webhook to the topic.
   - On pipeline failure, publish to the topic via OCI SDK.

3. **Pre-send health check:**
   - If the pipeline fails after the ingestion step but before sending, the system should send a "Briefing unavailable today" notification to recipients rather than silently failing.

4. **Manual trigger endpoint:**
   - Expose a `/admin/trigger-pipeline` endpoint on the FastAPI redirect service (auth-protected) to manually re-run the pipeline without SSH access.

5. **GitHub Actions as backup:** Keep a GitHub Actions workflow that can be manually triggered (`workflow_dispatch`) to re-run the pipeline in case the OCI Compute instance has issues.

---

## 9. Object Storage for HTML Archive

Every briefing run produces 4 HTML files (one per audience). These should be archived for:
- Historical reference (executives may want to read last Tuesday's briefing).
- Debugging (verify exactly what was sent if an executive questions a story).
- Future ML training data (click behavior correlated with specific HTML content).

### 9.1 OCI Object Storage

OCI Object Storage is the native, S3-compatible object store on OCI. Every OCI tenancy includes access.

**Bucket setup:**
```bash
# Via OCI CLI
oci os bucket create \
  --compartment-id <compartment-ocid> \
  --name "ai-briefing-archive" \
  --versioning Enabled \
  --public-access-type NoPublicAccess
```

**URL structure (recommended):**
```
oci://ai-briefing-archive/briefings/{YYYY}/{MM}/{DD}/{audience_id}/index.html
```

**Example:**
```
oci://ai-briefing-archive/briefings/2026/03/10/karan-batta/index.html
oci://ai-briefing-archive/briefings/2026/03/10/nathan-thomas/index.html
```

**Python upload (using oci-sdk):**
```python
import oci

object_storage = oci.object_storage.ObjectStorageClient(config)
namespace = object_storage.get_namespace().data

def archive_briefing(audience_id: str, date: str, html_content: str):
    object_name = f"briefings/{date.replace('-', '/')}/{audience_id}/index.html"
    object_storage.put_object(
        namespace_name=namespace,
        bucket_name="ai-briefing-archive",
        object_name=object_name,
        put_object_body=html_content.encode("utf-8"),
        content_type="text/html; charset=utf-8",
    )
```

**Access patterns:**

Option A — Pre-Authenticated Requests (PARs): Generate time-limited, signed URLs that allow unauthenticated access to a specific object. Ideal for sending an "view in browser" link in the email.
```python
par_details = oci.object_storage.models.CreatePreauthenticatedRequestDetails(
    name=f"briefing-{date}-{audience_id}",
    access_type="ObjectRead",
    time_expires=datetime.utcnow() + timedelta(days=30),
    object_name=object_name
)
par = object_storage.create_preauthenticated_request(namespace, "ai-briefing-archive", par_details)
view_in_browser_url = f"https://objectstorage.{region}.oraclecloud.com{par.data.access_uri}"
```

Option B — OCI CDN (Content Delivery Network): Attach an OCI CDN distribution to the bucket for fast, clean URLs. Adds ~$0.0085/GB data transfer. At this volume (kilobytes/day), negligible.

Option C — Private access via OCI Compute: The redirect/admin FastAPI service can serve archived HTML files by fetching from Object Storage on demand (with authentication). This is the cleanest approach: `/archive/2026-03-10/karan-batta` serves the archived HTML with proper auth.

**Lifecycle policy:** Automatically delete objects older than 90 days (or 365 days if long-term record retention is desired):
```json
{
  "items": [{
    "name": "delete-old-briefings",
    "action": "DELETE",
    "timeAmount": 90,
    "timeUnit": "DAYS",
    "isEnabled": true,
    "objectNameFilter": {"inclusionPrefixes": ["briefings/"]}
  }]
}
```

**Cost:**
- OCI Object Storage: first 10GB free in the Always Free tier. At ~10KB per HTML file × 4 audiences × 365 days = ~14.6MB/year. Effectively **free** within the Always Free tier.
- Data transfer: negligible at this volume.

---

## 10. Recommended Full Stack

### 10.1 Final Stack

| Layer | Component | Rationale |
|---|---|---|
| **RSS Ingestion** | feedparser + httpx (async) | Best library for heterogeneous feeds; async-native HTTP |
| **News Discovery** | Bing News Search API | Low cost (~$2–10/month), high reliability, freshness filter |
| **Momentum Signal** | GDELT API (free) | Detects multi-outlet coverage; free |
| **Community Signal** | HN Algolia API (free) + PRAW (Reddit) | Best documented community APIs |
| **GitHub Trending** | httpx + BeautifulSoup scraper | No official API; simple scraping works |
| **Vendor Blogs** | feedparser + httpx + BeautifulSoup | Combination of RSS + targeted scraping |
| **Newsletter Ingest** | Postmark Inbound webhook | Included with Postmark; parses MIME to JSON |
| **Embedding Model** | BAAI/bge-small-en-v1.5 (sentence-transformers) | On-OCI, zero API cost, MTEB-competitive quality |
| **Vector / Dedup DB** | pgvector on PostgreSQL 16 | Single service, eliminates separate vector DB, fits scale |
| **Canonical DB** | PostgreSQL 16 (OCI Database for PostgreSQL or self-hosted) | All canonical data: articles, clusters, sent history, tracking |
| **LLM — Classification / Summaries** | Claude claude-haiku-4-5 | Fast, cheap, sufficient for structured classification and body summaries |
| **LLM — Strategic Analysis / Exec Summary** | Claude claude-opus-4-6 + extended thinking | Best quality for OCI implications and executive bullets |
| **Email Delivery** | Postmark | Best deliverability, open/click APIs, inbound parsing |
| **Link Tracking** | Custom FastAPI redirect service on OCI Compute | Full per-audience, per-story analytics; data on OCI |
| **Scheduling** | cron on OCI Compute | Simple, reliable, no timeout constraints |
| **HTML Archive** | OCI Object Storage | Native OCI, Always Free tier, lifecycle policies, PARs for view-in-browser |
| **Alert / Monitoring** | OCI Notifications + Postmark (failure email) | Native OCI alerts + simple email fallback |
| **OCI Compute** | VM.Standard.E4.Flex (2 OCPU / 16GB RAM) | Runs Postgres + pgvector + FastAPI + BGE model + pipeline |

### 10.2 Estimated Monthly Cost at Initial Scale (4 Recipients)

| Item | Cost/Month |
|---|---|
| OCI Compute (VM.Standard.E4.Flex, 1 OCPU / 6GB RAM — Always Free eligible) | **$0** (Always Free) |
| OCI Object Storage (~14.6MB/year HTML archive) | **$0** (Always Free tier) |
| OCI Database for PostgreSQL (or self-hosted on Compute) | **$0** (use Compute VM) |
| Postmark (1,000 emails/month plan) | **$15** |
| Bing News Search API (~600 calls/month at S2) | **~$2** |
| Claude API (Haiku + Opus ~$0.82/day) | **~$25** |
| GDELT | **$0** (free) |
| HN Algolia API | **$0** (free) |
| Reddit API (PRAW) | **$0** (free with app registration) |
| sentence-transformers / BGE model | **$0** (self-hosted) |
| OCI Notifications | **$0** (first 1M/month free) |
| Domain + SSL (OCI Certificate Service) | **~$12/year = $1/month** |
| **TOTAL** | **~$43/month** |

At this scale, the dominant costs are Postmark ($15) and Claude API ($25). The OCI infrastructure is essentially free within OCI Always Free limits.

### 10.3 Migration Path at Increased Scale

| Trigger | Action |
|---|---|
| >20 recipients | Upgrade Postmark plan ($50/month for 10K emails). Costs remain linear. |
| >500 articles/day ingested | Upgrade OCI Compute to 4 OCPU / 32GB for embedding throughput. Consider async worker queue (OCI Queue or Redis). |
| >50,000 vector embeddings active | Migrate from pgvector to Qdrant (Docker on upgraded Compute). Interface change is minimal. |
| >100 recipients | Add OCI Load Balancer in front of redirect service. Evaluate OCI CDN for HTML archive. |
| Expanding to new audience regions | Add language-specific embedding models (multilingual-e5 for non-English content). |
| LLM costs exceed $200/month | Implement prompt caching aggressively. Move body summaries to Claude claude-haiku-4-5. Cache OCI Implication templates for recurring story types. |
| Regulatory requirement for data isolation | Move to OCI Database for PostgreSQL (dedicated, fully managed, in-region). Estimated cost: ~$200–400/month for production-grade managed instance. |

### 10.4 Infrastructure Diagram (Logical)

```
[Cron: 05:00 daily]
      |
      v
[Ingestion Layer]
  feedparser + httpx --> RSS feeds (40+ sources)
  Bing News Search API --> discovery layer
  GDELT API --> momentum signal
  HN Algolia API --> community signal
  PRAW (Reddit) --> community signal
  GitHub trending scraper --> OSS signal
  Postmark Inbound --> newsletter email parser
      |
      v
[Normalization]
  Entity extraction (Haiku)
  Canonical URL deduplication
  Source credibility tagging
  Timestamp normalization
      |
      v
[Story Intelligence Layer]
  BGE-small embedding --> pgvector ANN search (7-day window)
  Duplicate detection (cosine similarity > 0.85 threshold)
  Story cluster assignment
  Follow-up delta analysis (Haiku)
  Novelty scoring
      |
      v
[Audience Ranking]
  Section weight application per audience profile
  Company/topic relevance scoring
  Final composite score: credibility + relevance + novelty + momentum + impact + timeliness - duplication_penalty
  Top 15-20 items per audience selected
      |
      v
[LLM Generation]
  Canonical summaries (Haiku)
  Audience-personalized summaries (Haiku)
  OCI Implications for top stories (Opus)
  Executive summary bullets (Opus + extended thinking)
      |
      v
[Rendering]
  HTML email template rendering
  Tracking URL injection (FastAPI redirect service)
  "View in browser" PAR URL generation
      |
      +---> [Postmark] --> email delivery (4 recipients)
      |
      +---> [OCI Object Storage] --> HTML archive
      |
      +---> [PostgreSQL] --> sent_items, pipeline_run_log
      |
      v
[Analytics] (ongoing)
  Postmark webhook --> open events --> Postgres
  FastAPI redirect --> click events --> Postgres
  Weekly analytics summary (optional Haiku-generated)
```

---

## Appendix: Key API Endpoints Reference

| Service | Endpoint | Auth |
|---|---|---|
| HN Algolia | `https://hn.algolia.com/api/v1/search` | None |
| GDELT | `https://api.gdeltproject.org/api/v2/doc/doc` | None |
| Bing News | `https://api.bing.microsoft.com/v7.0/news/search` | `Ocp-Apim-Subscription-Key` header |
| NewsAPI.org | `https://newsapi.org/v2/everything` | `apiKey` query param |
| Postmark send | `https://api.postmarkapp.com/email` | `X-Postmark-Server-Token` header |
| Postmark opens | `https://api.postmarkapp.com/messages/outbound/opens` | `X-Postmark-Account-Token` header |
| Postmark clicks | `https://api.postmarkapp.com/messages/outbound/clicks` | `X-Postmark-Account-Token` header |
| Anthropic (Haiku/Opus) | `https://api.anthropic.com/v1/messages` | `x-api-key` header |
| OpenAI Embeddings | `https://api.openai.com/v1/embeddings` | `Authorization: Bearer` header |
| Bitly shorten | `https://api-ssl.bitly.com/v4/shorten` | `Authorization: Bearer` header |
| Reddit OAuth | `https://www.reddit.com/api/v1/access_token` | Basic auth (client_id:secret) |
| GitHub Search | `https://api.github.com/search/repositories` | Optional: `Authorization: token` |

---

*All costs cited reflect publicly available pricing as of March 2026. Verify current pricing before committing to any paid service. Services marked [PAID] require a billing relationship.*
