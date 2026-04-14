An executive AI/cloud market briefing that turns noisy signals into role-specific insight, with deduplication across a rolling 7-day memory and follow-up detection for ongoing stories.
## Structure
1. Executive Summary
	1. 3-5 bullets of What matters today
	2. One line implication for OCI
2. Market & Financial Analysis
	1. capex, bookings, margins, data center financing, major earnings comments, demand signals
3. Power & Datacenter
	1. Power availability
	2. Grid/transmission/utility partnerships
	3. new campuses, expansions, delays
	4. site selection, cooling, supply chain, rack density
4. Competitive moves
	1. infra
	2. product announcement
	3. partnerships
	4. multi-cloud/distributed cloud
5. AI Platform & Model News
	1. RLM preorders
	2. Model launches / updates
	3. AI infrastructure demand signals
	4. OSS / tooling / innovations
	5. breaking thoughts
6. Deals
	1. customer wins
	2. large enterprise rollouts
	3. procurement trends
	4. partner channel signals
7. Community Signal
	1. Hacker News
	2. Reddit
	3. GitHub trending / OSS momentum
8. OCI Implications
	1. threat/opportunity
	2. watch item
	3. suggested internal followup

## Audience categories
common core + personalized emphasis: - ingest once, score once, deduplicate once, render differently per audience
### Audience profile schema
1. topics_of_interest
2. negative_topics
3. companies_of_interest
4. geo_focus
5. preferred_tone
6. time_horizon
7. section_weights
8. max_length
9. include_community_signals
10. include_speculative_analysis

**Karan Batta: SVP of OCI, product management**
- Info: leads overall OCI product management. Oracle’s own bio says he leads overall product management for OCI and worked previously on Azure compute, GPUs, and FPGAs.
- Cares about: Financial Analysis
- Weights:
	- Financial Analysis: 35%
	- Compete/infra: 25%
	- Datacenter/power: 15%
	- AI platform News: 15%
	- Deals: 10%
- Tone: concise, high signal, strategic, implication-heavy

**Nathan Thomas: SVP of product management at OCI**
- Info: overseeing product strategy and Oracle’s cloud and multicloud services.
- Cares about: Multi-cloud, AI News, Deals
- Weights:
	- Multi-cloud: 30%
	- AI platform news: 25%
	- Deals: 25%
	- Compete partnerships: 10%
	- Financial: 10%
- Tone: ecosystem-oriented, partner-aware, customer-facing implications
**Media**
**Greg Pavlik: EVP of OCI in Data/AI**
- EVP for AI and Data Management Services, responsible for strategy and delivery across Oracle’s AI-centered portfolio.
- Cares about: Compete, AI New
- Weights: 
	- Compete: 35%
	- AI Platform & Model news: 35%
	- OSS/innovation: 15%
	- Partnerships: 10%
	- Community signal: 5%
- Tone: technical but executive, focuses on capability gaps and opportunities

**Mahesh: EVP of OCI Security & Developer Platform organization**
- EVP of OCI Security and Developer Platform, with a mission around flexible, open, secure platforms.
- Cares about: Power, Data center, AI News, Deals
- Weights:
	- Power: 20%
	- Datacenter: 25%
	- AI platform news: 20%
	- Deals: 20%
	- Security/platform implications: 15%
- Tone: Platform, resilience, secure operations, scale readiness

## Sources and scoring
### Scoring
Every candidate item should get a score before it is shown
For each item:  `final_score = source_credibility + audience_relevance + novelty + momentum + strategic_impact + timeliness - duplication_penalty`

Dimensions:
1. Source credibility:
	1. Reuters / Bloomberg / WSJ / company press release / earnings transcript: high
	2. CloudWars / The Register / niche trade press: medium
	3. Reddit / HN / LinkedIn: low as source of fact, high as signal source
2. Audience relevance: Based on profile weights and entities
	1. Company names
	2. topic taxonomy
	3. keywords
	4. embeddings similarity to audience brief
3. Novelty: How different is it from stories sent in last 7 days?
4. Momentum
	1. multiple reputable outlets covering same event
	2. rising discussion on HN/Reddit/GitHub
5. Strategic impact: does it affect OCI competition, supply, power, multi-cloud, model ecosystem, commercial motion?
6. timeliness
	1. published in last 24h gets boost
	2. 2–7 days still eligible
	3. older than 7 days only if major follow-up

### Sources
1. Tier 1: authoritative / primary, Use these for factual grounding.
	1. company press releases
	2. official blogs
	3. earnings transcripts / SEC filings
	4. investor relations pages
	5. regulator / utility / government documents
	6. official product docs
	7. Oracle / NVIDIA / AMD / Intel blogs and newsroom pages
2. Tier 2: high-quality journalism
	1. Reuters
	2. Bloomberg
	3. WSJ
	4. FT
	5. CNBC
	6. The Information
	7. Major trade press
3. Tier 3: Domain-specific media
	1. CloudWars
	2. The Register
	3. Fierce Network
	4. Data Center Dynamics
	5. SemiAnalysis if accessible
	6. ServerTheHome??
4. Tier 4: Community/sentiment/weak signals
	1. Hacker News
	2. Reddit
	3. Github trending
	4. LinkedIn Posts
	5. Stackoverflow
	6. TechCrunch

Concrete source map by section
1. Financial Analysis
	1. earnings transcripts
	2. investor relations
	3. Reuters/Bloomberg/WSJ
	4. SEC filings
	5. major analyst commentary if accessible
2. Power
	1. utility press releases
	2. regulatory filings
	3. energy/news trade press
	4. hyperscaler energy partnership announcements
3. Datacenter
	1. Data Center Dynamics
	2. company site announcements
	3. local permitting / zoning / economic development sources
	4. Reuters/Bloomberg for major financing / expansions
4. Compete
	1. vendor blogs
	2. product launch pages
	3. partner press releases
	4. cloud trade press
	5. earnings commentary
5. AI Platform & Model News
	1. OpenAI / Anthropic / Google / Meta / xAI / Mistral / Cohere official blogs
	2. Hugging Face / GitHub trending
	3. reputable AI press
	4. research blog posts
6. Deals
	1. customer press releases
	2. vendor case studies
	3. earnings calls
	4. partner announcements
7. Community Signal
	1. HN Algolia
	2. Reddit API
	3. GitHub trending / stars velocity

## Implementation
Content UX: visually appealing, uses bit.ly, Trackmy? Send by email
Save html as object storage
has a repo, triggers iteration
Deliver every morning by email (P0)

### Search Engine
- **RSS + direct source polling** for the most important sources
- **web/news search API** for discovery and fill-in
- **HN/Reddit APIs** for community signal
- **email/newsletter parser** for private newsletters

### Memory System
**hybrid memory stack**:
1. **Postgres** for canonical truth
2. **Vector search** for semantic similarity (Qdrant?)
3. **Keyword/full-text search** for precise matching
4. **RAG-style retrieval** only when generating summaries or checking novelty

Very important: No repetitive news in 7 days unless there is a follow-up

Each incoming article gets mapped to:
- story_id
- event_type
- entities
- published_at
- source
- headline_embedding
- summary_embedding
- fact_signature

**Step 1: normalize** 
- extract companies, products, execs, regions, dates, numbers, event verbs (launched, partnered, raised, expanded, delayed, sued, announced, shipped)
**Step 2: cluster into a canonical story**
- For example, “OpenAI and Oracle expand AI data center”, “Oracle/OpenAI Abilene site grows”, “Texas AI campus financing talks shift” All should map into one evolving story cluster if they describe the same core event.
Step 3: compare with sent items from last 7 days
- For each new item, compare against previously delivered story clusters: embedding similarity, entity overlap, event-type overlap, same location / same deal / same product
- If above threshold, mark as `candidate_duplicate`.
Step 4: detect whether it is a true follow-up
- Include again only if it adds materially new information
- Examples of valid follow-up signals:
	- new numbers
	- official confirmation / denial
	- financing closed
	- timeline changed
	- customer named
	- launch date set
	- geographic expansion
	- deal value revealed
	- partner list expanded
	- outage resolved or worsened
Step 5: render as follow-up, not as a brand-new story
- Tag it like: update, follow-up, new detail on previously covered story

Ruleset:
- suppress if same story cluster, no materially new facts, within 7 days
- allow if: same cluster but new fact delta score exceeds threshold

Datamodel for fact delta:
- `capacity_mw`
- `customer_name`
- `deal_size`
- `model_name`
- `partner_name`
- `region`
- `date`
- `status`
If new article changes one of those or adds new structured facts, it qualifies as a follow-up.

### Delivery and personalization architecture
**Ingestion**
- RSS feeds
- source crawlers
- newsletter email parser
- HN/Reddit fetchers
- vendor pages

**Normalization**
- extract text
- clean boilerplate
- canonical URL
- publisher/source metadata
- timestamps
- entities/topics

**Story intelligence layer**
- clustering
- deduplication
- fact extraction
- novelty detection
- source credibility scoring

**Audience ranking**  
For each audience:
- apply section weights
- apply company/topic preference
- build top N items per section

**LLM generation**  
Generate:
- headline
- 2–4 sentence summary
- “why this matters to OCI”
- optional “watch item”

**Rendering**
- HTML email
- web archive page / object storage copy
- optional Slack/Chat format later

**Telemetry**
- unique tracked links
- email open and click events
- section-level performance
- story-level performance

### Customized delivery by audience
2 stage renderer that can be shared across audience:
**Stage 1: common editorial bundle**
Create a daily canonical bundle of maybe 20–40 ranked story objects.
**Stage 2: audience-specific selection**
For each audience:
- choose top 8–15 items
- vary order
- vary section prominence
- vary commentary style
- vary length

### Feedback and analytics
**Email metrics**
- delivered
- bounced
- opened
- unique opens
- clicks
- unique clicks
- CTR
- click-to-open rate

**Content metrics**
- top clicked section
- top clicked story
- reading depth proxy
- repeated clicks on same topic
- no-click streak by user

**Personalization metrics**
- topic click affinity by user
- source affinity
- preferred article length
- preferred time of delivery

**Explicit feedback**  
Add tiny controls in the email:
- “More like this”
- “Less like this”
- “Too repetitive”
- “Useful”
- “Not useful”

Even a simple thumbs up/down per story is powerful.
Bitly supports link-level analytics and tracking links with UTM parameters.  
Postmark supports both open tracking and click tracking for outbound emails, and its APIs expose open/click event data you can query later.

Best implementation pattern

Every story link should be:
1. a unique per-audience tracking URL
2. with campaign params
3. redirected to the canonical article

Store:
- audience
- newsletter date
- section
- story_id
- source
- position in email

That lets you answer:
- what section gets read by whom
- which topics matter by exec
- whether personalization is improving over time

### Hard code editorial rules
- Every item needs a source label
- No community post becomes a top story without stronger validation
- No duplicate story in 7 days unless fact delta exists
- Every story gets an “OCI implication”
- Every audience has a max word count
- One major story can appear across audiences, but wording must differ
- Use confidence tags internally
    - confirmed
    - credible report
    - weak signal
    - follow-up
- Avoid overfitting to social buzz
- Prefer primary sources over rewritten commentary
- Track what was suppressed, not just what was sent
## UX Design 

Newsletter templates
potential exmaples of newsletter templates I found (feel free to experiment a lot here):  
- [https://www.google.com/imgres?q=newsletter%20templates&imgurl=https%3A%2F%2Ft4.ftcdn[…]h=360&hcb=2&ved=2ahUKEwiK8tjOgoqTAxWNITQIHag8DPYQnPAOegQIKhAB](https://www.google.com/imgres?q=newsletter%20templates&imgurl=https%3A%2F%2Ft4.ftcdn.net%2Fjpg%2F05%2F17%2F55%2F95%2F360_F_517559520_tCZR6h1o4bTH21DAKvU74Sd8dbX4ZYsW.jpg&imgrefurl=https%3A%2F%2Fstock.adobe.com%2Fsearch%3Fk%3Dnewsletter%2Btemplate&docid=QjwFU-CZQy_l2M&tbnid=kj7G6c89iI4SZM&vet=12ahUKEwiK8tjOgoqTAxWNITQIHag8DPYQnPAOegQIKhAB..i&w=702&h=360&hcb=2&ved=2ahUKEwiK8tjOgoqTAxWNITQIHag8DPYQnPAOegQIKhAB)
- [https://www.google.com/imgres?q=tech%20newsletter%20templates&imgurl=https%3A%2F%2Fi[…]h=330&hcb=2&ved=2ahUKEwionZ37goqTAxWUHjQIHd4NIzAQnPAOegQIKxAB](https://www.google.com/imgres?q=tech%20newsletter%20templates&imgurl=https%3A%2F%2Fimages.smiletemplates.com%2Fuploads%2Fscreenshots%2F9%2F0000009572%2Fnewsletter-templates-b.jpg&imgrefurl=https%3A%2F%2Fwww.smiletemplates.com%2Ftechnology%2Fnewsletter-templates%2F0.html&docid=aJ4A8sfbTtngbM&tbnid=ha_2hbv49SE88M&vet=12ahUKEwionZ37goqTAxWUHjQIHd4NIzAQnPAOegQIKxAB..i&w=274&h=330&hcb=2&ved=2ahUKEwionZ37goqTAxWUHjQIHd4NIzAQnPAOegQIKxAB)
- [https://www.google.com/imgres?q=tech%20newsletter%20templates&imgurl=https%3A%2F%2Fa[…]=1188&hcb=2&ved=2ahUKEwionZ37goqTAxWUHjQIHd4NIzAQnPAOegQIKBAB](https://www.google.com/imgres?q=tech%20newsletter%20templates&imgurl=https%3A%2F%2Fassets.visme.co%2Ftemplates%2Fbanners%2Fthumbnails%2Fi_Apple-iPhone-Technology-Newsletter_full.jpg&imgrefurl=https%3A%2F%2Fwww.visme.co%2Ftemplates%2Fnewsletters%2Fapple-iphone-technology-newsletter-templates-1425287002%2F&docid=be2eKS7TYYC9lM&tbnid=t7K-z5sucYni2M&vet=12ahUKEwionZ37goqTAxWUHjQIHd4NIzAQnPAOegQIKBAB..i&w=840&h=1188&hcb=2&ved=2ahUKEwionZ37goqTAxWUHjQIHd4NIzAQnPAOegQIKBAB)
- 
## Questions
1. Search engine?
2. How to deliver customized content based on audience
3. What are the sources, need credibility
4. Implemented with Claude Code + cronjob or OpenClaw (preferrably claude code takes most of the token usage b/c paid by company)
5. How to get user feedback? need some data tracking, like Click through rate, impression, etc. 
6. How to implement the No repetitive news in 7 days unless new info?