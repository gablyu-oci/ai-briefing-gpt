# Gap Analysis: AI Daily Executive Briefing

**Date:** 2026-04-08 (updated)
**Previous assessment:** 2026-03-11
**Codebase assessed:** main branch, post-Phase 2 embedding dedup implementation

---

## 1. P0 Feature Gap Table

| P0 Feature | Status | Notes |
|---|---|---|
| **Ingestion pipeline** | **Implemented** | 31 RSS sources (6 Tier 1, 13 Tier 2, 8 Tier 3, 4 Tier 4). Full article text extraction via Trafilatura + httpx. Concurrent fetching (10 workers). Reddit community signals added. |
| **Normalization** | **Implemented** | SpaCy NER (en_core_web_sm) for entity extraction. Keyword-based section tagging. Full-text extraction for richer embeddings. |
| **7-day deduplication** | **Implemented** | 5-stage in-run Jaccard pipeline + embedding-based cross-day dedup. nomic-embed-text-v1.5 (256d Matryoshka). 7-day rolling cluster window in SQLite. Fact-delta scoring (6 signals). Follow-up detection. Suppression logging. In-memory cluster propagation fixes duplicate clusters. |
| **Scoring engine** | **Implemented** | 4 core dimensions (credibility, timeliness, section_relevance, keyword_bonus). Split scoring: pre-score before dedup, full audience score after classification. 7-dimension engine exists in app/scoring/engine.py but main.py uses the 4-dimension version. |
| **Audience profiles** | Partial | 4 executives defined with name, title, tone, section_weights, accent_color. Missing: topics_of_interest, negative_topics, companies_of_interest, geo_focus, time_horizon, max_length. |
| **Profile schema validation** | Missing | No validation at load time. |
| **8 briefing sections** | Partial | 12 section keys defined. PRD canonical 8-section structure not enforced. No per-audience length budgets. |
| **LLM generation** | **Implemented** | Haiku classification + Sonnet summarization + executive summaries. Caching. Retry with backoff. Uses full_text when available. 15 concurrent workers. |
| **Confidence tags** | Partial | Uses high/medium/low. PRD specifies confirmed/credible_report/weak_signal/follow_up. |
| **Source labels** | **Implemented** | Source name, tier badge, date, link all rendered. |
| **Editorial rules enforcement** | Missing | 0 of 9 rules programmatically enforced. |
| **HTML email delivery** | Missing | Stub only. No Postmark integration. |
| **Web archive copy** | **Implemented** | Static HTML to output/YYYY-MM-DD/. Served via nginx at ainews.oci-incubations.com. |
| **Tracked links** | Missing | No click tracking infrastructure. |
| **Suppression log** | **Implemented** | Cross-day suppressions logged to suppression_log table with reason, similarity score, matched cluster ID. Viewable in admin dashboard. |
| **Daily cron schedule** | **Implemented** | Cron at 5:00 AM UTC via scripts/daily_run.sh. Systemd services for auto-start. |
| **Basic feedback controls** | Missing | No feedback UI in rendered output. |
| **Email metrics** | Missing | No open/click tracking. |

---

## 2. Summary Scorecard

| Category | Count |
|---|---|
| **Fully implemented** | 10 |
| **Partially implemented** | 3 |
| **Missing** | 4 |
| **Total** | 17 |

**Fully implemented:** Ingestion, Normalization, 7-day dedup, Scoring, LLM generation, Source labels, Web archive, Suppression log, Daily cron, Full-text extraction

**Partially implemented:** Audience profiles (missing extended fields), Confidence tags (wrong vocabulary), Briefing sections (12 vs canonical 8)

**Missing:** Email delivery, Tracked links, Feedback controls, Editorial rules enforcement

---

## 3. What Changed Since March 11 Assessment

| Item | March 11 | April 8 |
|---|---|---|
| RSS sources | 15 | **31** (added Tier 1 business news, security, Reddit) |
| Dedup | Jaccard only, in-memory, no cross-day | **Embedding-based cross-day dedup with 7-day rolling window** |
| Embedding model | None | **nomic-embed-text-v1.5 (256d Matryoshka, 8K context)** |
| NER | Regex only | **SpaCy en_core_web_sm** |
| Full text | RSS summary only (1500 chars) | **Trafilatura extraction (5000 chars)** |
| Fact-delta | None | **6-signal scoring (time, numbers, entities, quotes, verbs)** |
| Database persistence | In-memory only | **SQLite with articles, clusters, suppressions** |
| Admin dashboard | Basic 5 endpoints | **8 tabs: Articles (filter/sort), Sources, Clusters, Dedup Stats, Rankings, Clusters 3D** |
| 3D visualization | None | **UMAP + HDBSCAN + Plotly.js interactive scatter plot** |
| Cron | None | **Daily 5 AM UTC** |
| Hosting | Manual | **nginx + systemd at ainews.oci-incubations.com** |
| Scoring | Before dedup | **Pre-score → dedup → classify → full score (saves LLM calls)** |
| Pipeline steps | 7 | **9** |

---

## 4. Remaining Work (Priority Order)

### High Priority
1. **Email delivery via Postmark** — briefings generated but not emailed
2. **Confidence tag vocabulary** — change high/medium/low to confirmed/credible_report/weak_signal/follow_up
3. **Audience profile enrichment** — add topics_of_interest, companies_of_interest, geo_focus to scoring

### Medium Priority
4. **Editorial rules enforcement** — validation gate before rendering
5. **Feedback controls** — thumbs up/down per story in rendered output
6. **Tracked links** — per-audience click tracking URLs

### Lower Priority
7. **Profile schema validation** — load-time checks
8. **Canonical 8-section structure** — enforce PRD section taxonomy
9. **Email metrics** — open/click/CTR via Postmark webhooks

---

*Updated 2026-04-08. Previous analysis at commit 1a627b7 (2026-03-11).*
