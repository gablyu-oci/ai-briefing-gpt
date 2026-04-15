# Gap Analysis: AI Daily Executive Briefing

**Date:** 2026-04-14
**Previous assessment:** 2026-04-08
**Codebase assessed:** Codex live copy (`ai-daily-briefing-codex`)

---

## 1. P0 Feature Gap Table

| P0 Feature | Status | Notes |
|---|---|---|
| **Ingestion pipeline** | **Implemented** | 31 RSS sources, full article extraction via Trafilatura + httpx, daily scheduled ingest into SQLite. |
| **Normalization** | **Implemented** | SpaCy NER, keyword-based section tagging, full-text extraction for richer embeddings. |
| **7-day deduplication** | **Implemented** | Daily in-batch embedding dedup plus weekly 7-day embedding dedup over stored articles. Manual full pipeline still retains fact-delta logic. |
| **Scoring engine** | **Implemented** | 4 core dimensions in the scheduled flow (credibility, timeliness, section relevance, keyword bonus). 7-dimension engine exists separately but is not the live default. |
| **Audience profiles** | Partial | 4 executives defined with name, title, tone, section weights, and accent color. Extended schema fields remain incomplete. |
| **Profile schema validation** | Missing | No strict validation layer at load time. |
| **8 briefing sections** | Partial | 12 section keys exist. PRD canonical 8-section structure is not enforced. |
| **LLM generation** | **Implemented** | Codex / Oracle Code Assist classification, summarization, executive summaries, and daily importance filtering. Caching, retry, and concurrency limits are in place. |
| **Confidence tags** | Partial | Uses `high` / `medium` / `low`. PRD wants `confirmed` / `credible_report` / `weak_signal` / `follow_up`. |
| **Source labels** | **Implemented** | Source name, tier badge, date, and original link are rendered. |
| **Editorial rules enforcement** | Missing | Hard rules are still editorial conventions, not code-enforced gates. |
| **HTML email delivery** | Partial | Weekly pipeline sends HTML email via Gmail-compatible SMTP. Missing: daily delivery, click tracking, open tracking, bounce analytics. |
| **Web archive copy** | **Implemented** | Static HTML at `output/YYYY-MM-DD/`, served live via nginx/systemd. |
| **Tracked links** | Missing | No click-tracking infrastructure yet. |
| **Suppression log** | **Implemented** | Suppressions and cluster matches are persisted and visible in the admin UI. |
| **Daily cron schedule** | **Implemented** | Daily ingest at 05:00 UTC and weekly full digest/email every Monday at 06:00 UTC via `scripts/daily_run.sh`. |
| **Basic feedback controls** | Missing | No thumbs up/down or structured feedback controls in the output. |
| **Email metrics** | Missing | No provider event ingestion or tracking logs for open/click/CTR. |

---

## 2. Summary Scorecard

| Category | Count |
|---|---|
| **Fully implemented** | 9 |
| **Partially implemented** | 4 |
| **Missing** | 5 |
| **Total** | 18 |

**Fully implemented:** Ingestion, normalization, 7-day dedup, scoring, LLM generation, source labels, web archive, suppression log, daily/weekly scheduling

**Partially implemented:** Audience profiles, confidence tags, briefing sections, HTML email delivery

**Missing:** Profile schema validation, editorial rules enforcement, tracked links, feedback controls, email metrics

---

## 3. What Changed Since April 8

| Item | April 8 | April 14 |
|---|---|---|
| LLM backend | Codex conversion in progress | **Codex / Oracle Code Assist is the live backend for all scheduled runs** |
| Daily job | Lightweight ingest only | **Daily ingest now includes a Codex importance filter before DB persistence** |
| Weekly delivery | HTML generation only | **Weekly pipeline now sends HTML email via Gmail-compatible SMTP** |
| Public site | Older Claude copy still serving | **Codex copy now serves `ainews.oci-incubations.com` and `/admin`** |
| Cron | Original Claude project scheduled | **Only the Codex copy remains scheduled** |

---

## 4. Remaining Work (Priority Order)

### High Priority

1. **Daily rendered digest and/or daily email** — current daily cron only ingests important articles into SQLite
2. **Confidence tag vocabulary** — change `high` / `medium` / `low` to `confirmed` / `credible_report` / `weak_signal` / `follow_up`
3. **Audience profile enrichment** — add topics of interest, companies of interest, and geo focus to scoring

### Medium Priority

4. **Editorial rules enforcement** — validation gate before rendering
5. **Feedback controls** — thumbs up/down or structured feedback per story
6. **Tracked links + email events** — per-audience click tracking plus open/click/bounce capture

### Lower Priority

7. **Profile schema validation** — load-time checks
8. **Canonical 8-section structure** — enforce PRD section taxonomy
9. **Internal-source ingestion** — Slack, Jira, customer reports, and other non-RSS sources

---

*Updated 2026-04-14 for the live Codex deployment.*
