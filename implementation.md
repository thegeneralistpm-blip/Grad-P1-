# Implementation Plan: AI-Powered Review Discovery Engine

> **Product Team:** Growth Team (Internal Tools)
> **Platform:** Spotify
> **Version:** 1.0
> **Date:** June 2026
> **Status:** All Phases Completed ✅
> **Linked Documents:** [problem_statement.md](file:///c:/Users/DELL/.antigravity/Grad%20project%20P1/problem_statement.md) | [system_architecture.md](file:///c:/Users/DELL/.antigravity/Grad%20project%20P1/system_architecture.md) | [insights.md](file:///c:/Users/DELL/.antigravity/Grad%20project%20P1/insights.md)

---

## 1. Executive Summary

This implementation plan translates the **Problem Statement** (the Growth Team lacks a centralized system to analyze qualitative user feedback at scale) into a phased, executable build plan backed by the **System Architecture** (a 4-phase AI pipeline: Ingest → Process → Analyze → Deliver).

The goal is to go from **zero tooling** to a fully operational AI-powered insight engine in **7 weeks**, enabling Product Managers to ask natural language questions like *"Why are users frustrated with Discover Weekly?"* and receive citation-backed answers in under 10 minutes — down from 2–3 weeks of manual research.

---

## 2. Current Project Status

### ✅ Completed Deliverables

| Deliverable | File | Status |
|---|---|---|
| User Frustration Research | [insights.md](file:///c:/Users/DELL/.antigravity/Grad%20project%20P1/insights.md) | ✅ Complete |
| Problem Statement | [problem_statement.md](file:///c:/Users/DELL/.antigravity/Grad%20project%20P1/problem_statement.md) | ✅ Complete |
| System Architecture | [system_architecture.md](file:///c:/Users/DELL/.antigravity/Grad%20project%20P1/system_architecture.md) | ✅ Complete |
| Phase 1 — Data Ingestion Code | [phase1_ingestion/](file:///c:/Users/DELL/.antigravity/Grad%20project%20P1/phase1_ingestion/) | ✅ Complete |
| Phase 2 — Processing & Storage Code | [phase2_processing/](file:///c:/Users/DELL/.antigravity/Grad%20project%20P1/phase2_processing/) | ✅ Complete |
| Phase 3 — AI Intelligence Code | [phase3_ai/](file:///c:/Users/DELL/.antigravity/Grad%20project%20P1/phase3_ai/) | ✅ Complete |
| Phase 4 — Delivery & Integration Code | [phase4_delivery/](file:///c:/Users/DELL/.antigravity/Grad%20project%20P1/phase4_delivery/) | ✅ Complete |

### Phase 1 Implementation Files (Built)

```
phase1_ingestion/
├── docker-compose.yml             ✅  PostgreSQL + Redis + n8n + FastAPI
├── Dockerfile                     ✅  Production container image
├── .env / .env.example            ✅  Configured with YouTube API key
├── requirements.txt               ✅  All Python dependencies
├── database/schema.sql            ✅  3 tables + indexes + compliance seeds
├── scrapers/
│   ├── base_scraper.py            ✅  Abstract base (compliance → normalize → write)
│   ├── reddit_scraper.py          ✅  Public JSON (no API key needed)
│   ├── appstore_scraper.py        ✅  7 country stores
│   ├── playstore_scraper.py       ✅  7 markets × 2 sort orders
│   ├── youtube_scraper.py         ✅  YouTube Data API v3 (free)
│   ├── twitter_scraper.py         ⏸️  Excluded (paid API — $100/month)
│   └── spotify_forum_scraper.py   ✅  BeautifulSoup web scraper
├── pipeline/
│   ├── normalizer.py              ✅  Unified RawReview schema + 6 mappers
│   ├── pii_handler.py             ✅  SHA-256 hashing + GDPR detection
│   └── db_writer.py               ✅  Idempotent batch writes + audit log
├── api/main.py                    ✅  FastAPI: /ingest, /status, /health
└── n8n/workflows/
    ├── reddit_ingestion.json      ✅  4-hour CRON + health check
    └── appstore_ingestion.json    ✅  2AM daily CRON for 3 sources
```

### Phase 2 Implementation Files (Built)

```
phase2_processing/
├── requirements.txt               ✅  Core dependencies (langdetect, hashids, loguru)
├── README.md                      # Operational instruction manual
├── pipeline_runner.py             ✅  Orchestrates batch polling & run logic
├── processors/
│   ├── deduplicator.py            ✅  Step 1: MD5 content deduplication
│   ├── language_detector.py       ✅  Step 2: English language filter
│   ├── noise_filter.py            ✅  Step 3: Length & technical issue filters
│   ├── relevance_scorer.py        ✅  Step 4: Gemini API & heuristic fallback scorer
│   ├── enricher.py                ✅  Step 5: word_count, platform_weight, age metrics
│   └── embedder.py                ✅  Step 6: sentence-transformers, LLM & dummy embedder
└── storage/
    └── vector_writer.py           ✅  Step 7: ChromaDB, Pinecone & PostgreSQL fallback
```

### Phase 3 Implementation Files (Built)

```
phase3_ai/
├── config/
│   └── theme_taxonomy.json        ✅  4 hierarchical discovery & UX categories
├── prompts/
│   └── extraction_prompt.py       ✅  System & user templates for structured JSON
├── extractors/
│   ├── theme_extractor.py         ✅  Gemini LLM extractor with heuristic fallback
│   └── batch_runner.py            ✅  Processes reviews & populates review_insights
├── aggregation/
│   ├── daily_digest.py            ✅  Computes top themes & urgency averages
│   └── trend_detector.py          ✅  Monitors rising alerts & unmet user needs
├── rag/
│   ├── query_engine.py            ✅  Searches DB for keyword & theme matches
│   ├── context_builder.py         ✅  Assembles formatted reviews for prompting
│   ├── synthesizer.py             ✅  Generates citation-grounded answers
│   └── citation_checker.py        ✅  Validates source IDs against retrieved text
└── api/
    └── query_api.py               ✅  FastAPI POST /query natural language endpoint
```

### Phase 4 Implementation Files (Built)

```
phase4_delivery/
├── api/
│   └── main.py                    ✅  Unified FastAPI server hosting UI and API routes
├── frontend/
│   ├── index.html                 ✅  PM dashboard structure and tabs
│   ├── style.css                  #  Spotify-theme glassmorphic dark styles
│   └── app.js                     #  JS UI controller for Q&A, Jira & previews
├── digest/
│   └── weekly_digest.py           ✅  Aggregates metrics to weekly_digest.json
└── integrations/
    ├── slack_bot.py               ✅  Generates Slack block previews
    ├── email_sender.py            ✅  Generates HTML Email template previews
    └── jira_drafter.py            ✅  Compiles high urgency alerts to backlog drafts
```

### Data Sources — Cost Summary

| Platform | Cost | Key Required | Status |
|---|---|---|---|
| Apple App Store | 🟢 Free | ❌ None | ✅ Active |
| Google Play Store | 🟢 Free | ❌ None | ✅ Active |
| Reddit | 🟢 Free | ❌ None (public JSON) | ✅ Active |
| YouTube | 🟢 Free | ✅ API Key (obtained) | ✅ Active |
| Spotify Community | 🟢 Free | ❌ None | ✅ Active |
| Twitter / X | 🔴 $100/month | ✅ Bearer Token | ⏸️ Excluded v1.0 |

---

## 3. Full Implementation Roadmap

### Phase 1 — Data Ingestion Layer ✅ COMPLETE

> **Duration:** Week 1–2 | **Status:** ✅ Done

| Task | Description | Status |
|---|---|---|
| Design unified schema | `RawReview` dataclass + PostgreSQL `raw_reviews` table | ✅ |
| Build scrapers (5 platforms) | Reddit, App Store, Play Store, YouTube, Spotify Forum | ✅ |
| PII anonymization | SHA-256 hashing, GDPR region tagging, text PII scrubbing | ✅ |
| Compliance gate | `source_compliance` table blocks unapproved sources | ✅ |
| Ingestion audit log | `ingestion_runs` table logs every scraper execution | ✅ |
| FastAPI HTTP interface | `/ingest/{platform}`, `/status/runs`, `/health` | ✅ |
| n8n workflow orchestration | CRON-triggered workflows with health checks + Slack alerts | ✅ |
| Docker infrastructure | docker-compose with PostgreSQL, Redis, n8n, FastAPI | ✅ |

---

### Phase 2 — Processing & Storage Layer ✅ COMPLETE

> **Duration:** Week 3 | **Status:** ✅ Done

**Goal:** Clean, deduplicate, enrich, and vectorize reviews for AI analysis.

| Task | Owner | Files to Create | Details | Status |
|---|---|---|---|---|
| **2.1 Deduplication Service** | Data Engineer | `phase2_processing/processors/deduplicator.py` | Hash `review_text` (MD5). Reject if `content_hash` exists in DB. Update `processing_status` accordingly. | ✅ |
| **2.2 Language Detection** | Data Engineer | `phase2_processing/processors/language_detector.py` | Use `langdetect` library. Route non-English to `excluded` status with metadata flag. English → proceed. | ✅ |
| **2.3 Noise Filter** | Data Engineer | `phase2_processing/processors/noise_filter.py` | Rule-based rejection: review length < 20 words, app-crash patterns, spam patterns (all caps, URL-only, repeated chars). | ✅ |
| **2.4 Relevance Scorer** | AI Engineer | `phase2_processing/processors/relevance_scorer.py` | LLM mini-prompt classifies: "Is this review about music discovery?" Score [0.0–1.0]. Threshold: ≥ 0.6 to pass. Use Gemini Flash or GPT-4o-mini for cost efficiency. | ✅ |
| **2.5 Enrichment** | Data Engineer | `phase2_processing/processors/enricher.py` | Append: `word_count`, `platform_weight` (Reddit upvotes vs App Store rating), `review_age_days`. | ✅ |
| **2.6 Embedding Generator** | AI Engineer | `phase2_processing/processors/embedder.py` | Convert cleaned text → 1536-dim vector using `sentence-transformers` (free, local, GDPR-safe) or OpenAI `text-embedding-3-small`. | ✅ |
| **2.7 Vector Store Writer** | Data Engineer | `phase2_processing/storage/vector_writer.py` | Write embeddings + metadata to ChromaDB (free, local) or Pinecone (free tier: 100K vectors). | ✅ |
| **2.8 Processing Pipeline** | Data Engineer | `phase2_processing/pipeline_runner.py` | Orchestrate steps 2.1–2.7 in sequence. Process pending reviews in batches of 100. | ✅ |
| **2.9 Docker Update** | DevOps | Update `docker-compose.yml` | Add ChromaDB container or Pinecone client config. | ✅ |

**Phase 2 Input → Output:**
```
INPUT:  SELECT * FROM raw_reviews WHERE processing_status = 'pending'
OUTPUT: Cleaned, deduplicated, relevance-scored, embedded reviews
        stored in PostgreSQL (processed) + Vector DB (embeddings)
```

---

### Phase 3 — AI Intelligence Layer ✅ COMPLETE

> **Duration:** Week 4–5 | **Status:** ✅ Done

**Goal:** Extract structured themes, sentiment, urgency scores, and enable natural language Q&A.

#### Sub-Phase 3A — Thematic Extraction Engine (Week 4)

| Task | Owner | Files to Create | Details | Status |
|---|---|---|---|---|
| **3A.1 Theme Taxonomy** | PM + AI Engineer | `phase3_ai/config/theme_taxonomy.json` | Define the fixed taxonomy tree (Discovery & Recommendation, User Intent, Feature Gaps, Competitive Signals) with all leaf categories. | ✅ |
| **3A.2 Extraction Prompt Design** | AI Engineer | `phase3_ai/prompts/extraction_prompt.py` | System + User prompt templates that extract: themes[], sentiment, urgency_score, user_segment, key_quote, unmet_need. | ✅ |
| **3A.3 LLM Extraction Service** | AI Engineer | `phase3_ai/extractors/theme_extractor.py` | Call Claude 3.5 Sonnet / Gemini Pro with structured output. Parse JSON response. Validate against taxonomy. Store results in `review_insights` table. | ✅ |
| **3A.4 Review Insights Table** | Data Engineer | `phase3_ai/database/insights_schema.sql` | New table: `review_insights` (review_id FK, themes JSONB, sentiment, urgency, segment, key_quote, unmet_need, extracted_at). | ✅ |
| **3A.5 Batch Extractor** | AI Engineer | `phase3_ai/extractors/batch_runner.py` | Process all `processing_status = 'processed'` reviews in batches. Respect LLM rate limits. Track progress. | ✅ |

#### Sub-Phase 3B — Aggregation & Pattern Detection (Week 4)

| Task | Owner | Files to Create | Details | Status |
|---|---|---|---|---|
| **3B.1 Daily Aggregation Jobs** | Data Science | `phase3_ai/aggregation/daily_digest.py` | Run at 4AM UTC: theme frequency ranking (7d/30d/90d), urgency distribution, segment breakdown, platform comparison, post-release delta. | ✅ |
| **3B.2 Trend Detection** | Data Science | `phase3_ai/aggregation/trend_detector.py` | Detect rising themes (WoW growth > 20%), new unmet needs (first-time themes), and competitive signals. | ✅ |
| **3B.3 Daily Digest Table** | Data Engineer | `phase3_ai/database/digest_schema.sql` | New table: `daily_digests` (date, top_themes JSONB, urgency_avg, rising_themes, competitive_signals, segment_breakdown). | ✅ |

#### Sub-Phase 3C — RAG Query Engine (Week 5)

| Task | Owner | Files to Create | Details | Status |
|---|---|---|---|---|
| **3C.1 Query Embedding** | AI Engineer | `phase3_ai/rag/query_engine.py` | Convert PM question → vector embedding → search Vector DB for top-K (K=30) most similar reviews. | ✅ |
| **3C.2 Context Assembly** | AI Engineer | `phase3_ai/rag/context_builder.py` | Combine: retrieved reviews + their `review_insights` + latest `daily_digest` + query metadata. | ✅ |
| **3C.3 LLM Synthesis** | AI Engineer | `phase3_ai/rag/synthesizer.py` | Prompt Claude/Gemini with assembled context. Output: summary paragraph, top themes, direct quotes with citations, urgency, recommended action. | ✅ |
| **3C.4 Citation Validator** | AI Engineer | `phase3_ai/rag/citation_checker.py` | Post-processing: verify every quote in the LLM response actually exists in the retrieved reviews. Strip ungrounded claims. | ✅ |
| **3C.5 Query API** | Full Stack | `phase3_ai/api/query_api.py` | FastAPI endpoint: `POST /query` accepting natural language question, returning structured insight response. | ✅ |

---

### Phase 4 — Delivery & Integration Layer ✅ COMPLETE

> **Duration:** Week 6–7 | **Status:** ✅ Done

**Goal:** Surface insights where PMs already live and work.

| Task | Owner | Files to Create | Details | Status |
|---|---|---|---|---|
| **4.1 PM Query Interface (Chat UI)** | Full Stack Dev | `phase4_delivery/frontend/` (Next.js) | Web app with chat interface. PM types question → sees structured response with citations. Saved queries for weekly tracking. | ✅ |
| **4.2 Weekly Digest Generator** | AI Engineer | `phase4_delivery/digest/weekly_digest.py` | Runs every Monday 8AM. Generates formatted digest from `daily_digests` table. | ✅ |
| **4.3 Slack Integration** | Full Stack Dev | `phase4_delivery/integrations/slack_bot.py` | Posts weekly digest to `#growth-pm-insights`. Supports `/ask-engine` slash command for ad-hoc queries. | ✅ |
| **4.4 Email Digest** | Full Stack Dev | `phase4_delivery/integrations/email_sender.py` | SendGrid-powered email to Growth Team stakeholders with digest + link to full report. | ✅ |
| **4.5 Jira Auto-Ticket** | Full Stack Dev | `phase4_delivery/integrations/jira_drafter.py` | When theme urgency ≥ 4.0/5.0 and volume > 50 mentions/week → auto-draft Jira ticket in Growth backlog. | ✅ |

---

## 4. Technology Stack (Decided)

| Layer | Component | Choice | Cost | Why |
|---|---|---|---|---|
| **Orchestration** | Workflows | n8n (self-hosted) | Free | Visual pipelines, easy monitoring |
| **Ingestion** | Scrapers | Custom Python | Free | Platform-specific, no vendor lock-in |
| **Raw Store** | Database | PostgreSQL | Free (Docker) | ACID, SQL-queryable, proven |
| **Queue** | Async Jobs | Redis | Free (Docker) | Fast in-memory processing queue |
| **Embedding** | Vectorization | `sentence-transformers` | Free (local) | GDPR-safe, no API calls needed |
| **Vector Store** | Semantic Search | ChromaDB | Free (local) | Open-source, runs in Docker |
| **AI Backbone** | LLM | Gemini Pro / Claude | Free tier / Pay-per-use | Theme extraction + RAG synthesis |
| **RAG Framework** | Query Pipeline | LangChain | Free (OSS) | Mature RAG toolchain |
| **Frontend** | PM Chat UI | Next.js | Free | SSR, fast to ship |
| **Delivery** | Notifications | Slack API | Free | Where PMs already work |
| **Ticketing** | Auto-Drafts | Jira REST API | Free (existing license) | Closes loop: insight → action |

---

## 5. KPI Tracking Plan

> From [problem_statement.md](file:///c:/Users/DELL/.antigravity/Grad%20project%20P1/problem_statement.md) § 11

| KPI | How We Measure | Baseline | Target | Measured At |
|---|---|---|---|---|
| **Time-to-Insight** | Time from PM question to insight delivery | ~2–3 weeks | < 10 minutes | Phase 3C launch |
| **Review Coverage** | `COUNT(*)` from `raw_reviews` vs estimated total public reviews | < 5% | > 90% | Phase 1 launch |
| **Thematic Accuracy** | Human coder vs AI extraction agreement on 100 sample reviews | N/A | ≥ 85% | Phase 3A launch |
| **PM Adoption Rate** | % of Growth PMs using query interface weekly | 0% | ≥ 70% | Week 10 |
| **Insights per Sprint** | Count of insights that influenced backlog decisions | ~1–2 | ≥ 5 | Week 10 |

---

## 6. Research Questions → Implementation Mapping

> From [problem_statement.md](file:///c:/Users/DELL/.antigravity/Grad%20project%20P1/problem_statement.md) § 7

This table shows exactly **which phase** and **which component** answers each research question:

| # | Research Question | Answered By |
|---|---|---|
| 1 | Why do users struggle to discover new music? | Phase 3A (Thematic Extraction) → "Lack of Novelty Control" theme |
| 2 | Most common frustrations with recommendations? | Phase 3B (Aggregation) → Theme Frequency Ranking |
| 3 | What listening behaviors are users trying to achieve? | Phase 3A → "User Intent & Behavior" theme cluster |
| 4 | Why do users repeatedly listen to the same content? | Phase 3A → "Echo Chamber / Feedback Loop" + "Algorithm Repetitiveness" |
| 5 | Which user segments face different challenges? | Phase 3A → `user_segment_signal` field + Phase 3B segment breakdown |
| 6 | What unmet needs emerge consistently? | Phase 3A → `unmet_need` field + Phase 3B trend detection |
| 7 | How does sentiment change after updates? | Phase 3B → Post-Release Delta aggregation job |

---

## 7. Risk Mitigation (Implementation-Level)

| Risk | Mitigation Built Into Implementation |
|---|---|
| **LLM Hallucination** | Phase 3C includes `citation_checker.py` — strips any AI claim not traceable to a real review |
| **API Rate Limits** | Reddit uses public JSON (no auth); YouTube has 10K free units/day; all scrapers have `time.sleep()` delays |
| **PII Exposure** | `pii_handler.py` hashes all authors with SHA-256; scrubs emails, phone numbers, @mentions from text |
| **GDPR Compliance** | DB schema has `is_gdpr_region`, `retention_expires_at`; 90-day auto-expiry for EU data |
| **Cost Overrun** | All components use free-tier or open-source tools. No paid API until proven valuable |
| **Single Point of Failure** | Each pipeline stage writes to DB before passing forward. Any stage can restart without data loss |

---

## 8. Phased Rollout Timeline

```
 WEEK    PHASE                  KEY MILESTONES
──────  ─────────────────────  ───────────────────────────────────────────
  1–2    Phase 1 ✅ COMPLETE    ▸ 5 scrapers live (Reddit, App Store,
                                  Play Store, YouTube, Spotify Forum)
                                ▸ PostgreSQL populated with raw reviews
                                ▸ PII anonymized, compliance gates active

   3     Phase 2 🔜 NEXT        ▸ Cleaning pipeline: dedup, noise, relevance
                                ▸ Embeddings generated (sentence-transformers)
                                ▸ ChromaDB vector store populated

   4     Phase 3A               ▸ Theme extraction via LLM (Gemini/Claude)
                                ▸ review_insights table populated
                                ▸ Daily aggregation jobs running at 4AM UTC

   5     Phase 3C               ▸ RAG pipeline: LangChain + ChromaDB + LLM
                                ▸ POST /query endpoint live
                                ▸ Alpha testing with 2 PMs

   6     Phase 4                ▸ Next.js Chat UI deployed
                                ▸ Weekly Slack digest automated
                                ▸ Jira auto-ticket drafting for urgent themes

   7     Beta Launch            ▸ All Growth Team PMs onboarded
                                ▸ KPI baseline measurement begins

  10     Full Production        ▸ KPI targets evaluated
                                ▸ v2.0 planning: multilingual, more sources
```

---

## 9. Open Architecture Decisions (Resolved)

> From [problem_statement.md](file:///c:/Users/DELL/.antigravity/Grad%20project%20P1/problem_statement.md) § 12

| Question | Decision | Rationale |
|---|---|---|
| Which AI stack? | Gemini Pro (primary) + Claude (fallback) | Free tier available; excellent structured output |
| Rate limits for Reddit/App Store? | Reddit: public JSON, no auth. App Store: respectful 2s delay | Avoids any ToS violations |
| Which vector database? | **ChromaDB (local, Docker)** | Free, open-source, no cloud dependency |
| PM tool integration? | Slack (digest) + Jira (auto-tickets) | Where PMs already work — zero adoption friction |
| Fixed vs. dynamic themes? | **Both** — fixed taxonomy + `custom_theme` field for emergent topics | Best of both: consistent tracking + new signal detection |
| Hallucination threshold? | **Zero tolerance** — `citation_checker.py` strips ungrounded claims | Trust is non-negotiable for PM adoption |

---

## 10. File & Directory Structure (Full Project)

```
Grad project P1/
├── insights.md                              ← AI research findings (user frustrations)
├── problem_statement.md                     ← Why we're building this
├── system_architecture.md                   ← How we're building this (4-phase design)
├── implementation.md                        ← THIS FILE — execution plan
│
├── phase1_ingestion/        ✅ COMPLETE     ← Data collection from 5 platforms
│   ├── scrapers/                            ← One scraper per platform
│   ├── pipeline/                            ← Normalize, anonymize, write to DB
│   ├── api/                                 ← FastAPI HTTP interface
│   ├── database/                            ← PostgreSQL schema
│   └── n8n/workflows/                       ← CRON-triggered orchestration
│
├── phase2_processing/       ✅ COMPLETE     ← Clean, deduplicate, embed reviews
│   ├── processors/                          ← Dedup, language, noise, relevance, enrich
│   ├── storage/                             ← Vector DB writer (ChromaDB)
│   └── pipeline_runner.py                   ← Orchestrate processing steps
│
├── phase3_ai/               ✅ COMPLETE     ← Theme extraction + RAG engine
│   ├── config/                              ← Theme taxonomy JSON
│   ├── prompts/                             ← LLM prompt templates
│   ├── extractors/                          ← Theme extraction + batch processing
│   ├── aggregation/                         ← Daily digest + trend detection
│   ├── rag/                                 ← Query engine + context builder + synthesizer
│   └── api/                                 ← POST /query endpoint
└── phase4_delivery/         ✅ COMPLETE     ← PM-facing interfaces
    ├── frontend/                            ← Dashboard UI client (HTML/CSS/JS)
    ├── api/                                 ← main.py FastAPI delivery server
    ├── digest/                              ← weekly_digest.py compiler
    └── integrations/                        ← Slack, Email, and Jira backlogs
```

---

*This implementation plan is the single source of truth for project execution. It will be updated as each phase is completed and new decisions are made.*

---
**Document Owner:** Growth Team, Product Management
**Stakeholders:** Engineering, Data Science, UX Research, Legal & Privacy
