# System Architecture: AI-Powered Review Discovery Engine
## Spotify — Growth Team | Internal Intelligence Platform

> **Document Type:** Technical Architecture
> **Version:** 1.0
> **Date:** June 2026
> **Status:** Design Phase
> **Linked To:** `problem_statement.md`

---

## Overview

The AI-Powered Review Discovery Engine is a multi-phase, production-grade AI system designed to ingest millions of qualitative user signals from across the internet, process them through an intelligent AI pipeline, and surface actionable, citation-backed insights to Spotify's Growth and Product teams in minutes — not weeks.

The architecture is built on four foundational principles:

| Principle | Description |
|---|---|
| **Scalability** | Handles tens of thousands of reviews daily without manual intervention. |
| **Trustworthiness** | Every AI-generated insight is grounded in and traceable to a real user quote. No hallucination-only outputs. |
| **Modularity** | Each phase (ingestion, processing, analysis, delivery) is an independently deployable and upgradeable component. |
| **Actionability** | The output is not a dashboard of charts — it is a system that answers specific product questions in natural language. |

---

## High-Level Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                        AI-POWERED REVIEW DISCOVERY ENGINE                        │
│                                                                                  │
│  ┌─────────────────┐    ┌──────────────────┐    ┌────────────────────────────┐  │
│  │  PHASE 1        │    │  PHASE 2         │    │  PHASE 3                   │  │
│  │  DATA           │───▶│  PROCESSING &    │───▶│  AI INTELLIGENCE           │  │
│  │  INGESTION      │    │  STORAGE LAYER   │    │  LAYER                     │  │
│  │                 │    │                  │    │                            │  │
│  │ • App Store API │    │ • Cleaning/Dedup │    │ • Theme Extraction (LLM)   │  │
│  │ • Play Store    │    │ • Embedding Gen  │    │ • Sentiment Scoring        │  │
│  │ • Reddit API    │    │ • Vector DB Store│    │ • Segment Classification   │  │
│  │ • X/Twitter API │    │ • Raw DB Store   │    │ • Urgency Ranking          │  │
│  │ • Spotify Forum │    │                  │    │ • RAG Pipeline             │  │
│  └─────────────────┘    └──────────────────┘    └────────────────────────────┘  │
│                                                             │                    │
│  ┌──────────────────────────────────────────────────────────▼─────────────────┐ │
│  │                          PHASE 4: DELIVERY LAYER                           │ │
│  │                                                                             │ │
│  │   PM Query Interface (Chat UI)  │  Weekly Digest  │  Jira/Confluence Push  │ │
│  └────────────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 1 — Data Ingestion Layer

> **Goal:** Reliably and continuously collect raw user feedback from all target platforms.

### 1.1 Data Sources & Collection Methods

| Source | Method | Tool / API | Frequency |
|---|---|---|---|
| **Apple App Store** | App Store Connect API (via Sensory or custom scraper) | `app-store-scraper` npm / RSS Feed | Daily batch (2AM UTC) |
| **Google Play Store** | Google Play Developer API | `google-play-scraper` | Daily batch (2AM UTC) |
| **Reddit** | Reddit PRAW API | `PRAW` (Python Reddit API Wrapper) | Near real-time (every 4 hours) |
| **X / Twitter** | X API v2 (filtered stream) | `tweepy` + keyword filter | Near real-time |
| **Spotify Community Forums** | Custom web scraper (Khoros/Lithium platform) | `Scrapy` / `BeautifulSoup` | Daily batch |

### 1.2 Ingestion Orchestration

**Tool of Choice: `n8n` (self-hosted) for workflow orchestration**

Rationale: n8n provides a visual, codeless workflow builder that allows non-engineers to monitor and modify ingestion pipelines. It natively integrates with HTTP Request nodes, custom JS functions, and can trigger downstream webhooks into our processing layer.

```
n8n Ingestion Workflow (per source):
┌─────────────┐     ┌──────────────┐     ┌───────────────┐     ┌───────────────────┐
│  CRON       │────▶│  API/Scraper │────▶│  Schema       │────▶│  Raw Data Store   │
│  Trigger    │     │  Node        │     │  Normalization│     │  (PostgreSQL)     │
│  (scheduled)│     │              │     │  & Validation │     │                   │
└─────────────┘     └──────────────┘     └───────────────┘     └───────────────────┘
```

### 1.3 Unified Raw Schema

Every review — regardless of source — is normalized into a single schema before storage:

```json
{
  "review_id":        "uuid-v4",
  "source_platform":  "reddit | app_store | play_store | twitter | spotify_community",
  "source_url":       "https://...",
  "author_handle":    "[ANONYMIZED]",
  "review_text":      "Discover Weekly has become useless...",
  "rating":           null,
  "upvotes":          142,
  "timestamp":        "2026-06-15T10:23:00Z",
  "language":         "en",
  "ingested_at":      "2026-06-16T02:00:00Z",
  "is_processed":     false
}
```

### 1.4 PII & Compliance Handling
- **Author anonymization:** All `author_handle` fields are hashed (SHA-256) before storage. Raw handles are never persisted.
- **Geographic filters:** GDPR-regulated data (EU users) is tagged and subject to stricter retention policies (90-day rolling window).
- **Legal sign-off gate:** No pipeline goes live without Legal team approval on the `is_compliant: true` flag per source.

---

## Phase 2 — Processing & Storage Layer

> **Goal:** Clean, deduplicate, enrich, and store reviews in a format ready for AI analysis.

### 2.1 Data Cleaning Pipeline

**Tool: Python (FastAPI microservice) triggered by n8n webhook**

Steps run in sequence:

```
Step 1: DEDUPLICATION
   └── Hash review_text (MD5). Reject if hash already exists in DB.

Step 2: LANGUAGE DETECTION
   └── Use `langdetect` library. Route non-English to language queue (v2.0 scope).

Step 3: NOISE FILTERING (Rule-based)
   └── Reject reviews matching patterns:
       • "app crashed / won't open / 1 star" (technical issues)
       • Review length < 20 words (too short for thematic extraction)
       • Spam patterns (all caps, repeated characters, URLs only)

Step 4: RELEVANCE SCORING (AI-assisted)
   └── Claude/GPT mini-model classifies: Is this review about music discovery/recommendations?
       Score: [0.0 - 1.0]. Threshold: ≥ 0.6 to proceed.

Step 5: ENRICHMENT
   └── Append metadata: word_count, platform_weight, review_age_days
```

### 2.2 Embedding Generation

**Tool: OpenAI `text-embedding-3-small` or `sentence-transformers` (local, GDPR-safe)**

Each cleaned review is converted to a high-dimensional vector embedding that captures its semantic meaning. These embeddings power the RAG (Retrieval-Augmented Generation) system in Phase 3.

```
Review Text → Embedding Model → 1536-dimensional vector → Vector DB
```

### 2.3 Storage Architecture (Dual Database)

| Store | Technology | Purpose | Retention |
|---|---|---|---|
| **Raw Review Store** | PostgreSQL (RDS) | Full text, metadata, audit trail | 24 months |
| **Vector Store** | Pinecone (Serverless) | Semantic search, RAG retrieval | 12 months |
| **Processing Queue** | Redis (ElastiCache) | Async job queue between pipeline stages | Ephemeral |
| **Insights Cache** | Redis | Cache common PM queries for fast response | 24 hours TTL |

---

## Phase 3 — AI Intelligence Layer

> **Goal:** Extract structured insights, themes, sentiment, and answers from the processed review corpus.

This is the core of the engine. It consists of three interconnected AI sub-systems.

---

### Sub-System A: Thematic Extraction Engine

**Technology:** Claude 3.5 Sonnet (primary) + GPT-4o (secondary/validation)

**Method:** Structured LLM prompting with a fixed taxonomy + dynamic cluster detection.

#### Fixed Theme Taxonomy (v1.0)

```
Discovery & Recommendation
├── Algorithm Repetitiveness
├── Echo Chamber / Feedback Loop
├── Discover Weekly Quality
├── AI DJ Frustration
├── Lack of Novelty Control
└── Contaminated Listening Profile

User Intent & Behavior
├── Mood-Based Listening
├── Active vs. Passive Discovery
├── Nostalgic vs. New Music Desire
└── Cross-Genre Discovery Need

Feature Gaps
├── "Not Interested" / Feedback Controls
├── Novelty Slider (requested feature)
├── Forget / Profile Reset Feature
└── Better Seeding for Radio

Competitive Signals
├── YouTube Music Mentioned (positive)
├── Apple Music Mentioned (positive)
└── Switching Intent Expressed
```

#### Extraction Prompt Architecture

```
SYSTEM PROMPT:
You are a senior product analyst at Spotify. You analyze user reviews
and extract structured insight. You NEVER fabricate. Every claim you
make must be traceable to a direct quote from the provided text.

USER PROMPT:
Given the following user review:
"""
{review_text}
"""

Extract the following as a JSON object:
{
  "themes": ["<from taxonomy above>"],
  "custom_theme": "<if no taxonomy match, describe in 3-5 words>",
  "sentiment": "positive | negative | neutral | mixed",
  "urgency_score": 1-5,
  "user_segment_signal": "power_user | passive_listener | genre_hopper | unclear",
  "key_quote": "<the single most impactful sentence from this review>",
  "unmet_need": "<one sentence: what does this user actually want?>"
}
```

---

### Sub-System B: Aggregation & Pattern Detection

After individual reviews are tagged, this sub-system runs **batch aggregation jobs** (daily at 4AM UTC) to detect macro-level patterns:

```
Aggregation Jobs:
┌────────────────────────────────────────────────────────────────┐
│  1. Theme Frequency Ranking (last 7d / 30d / 90d)             │
│  2. Urgency Score Distribution (are complaints escalating?)    │
│  3. Segment Breakdown (which users complain most about what?)  │
│  4. Platform Sentiment Comparison (Reddit vs App Store diff?)  │
│  5. Post-Release Delta (did sentiment change after update?)    │
└────────────────────────────────────────────────────────────────┘
```

Output: A structured JSON summary stored in PostgreSQL as a `daily_digest` record.

---

### Sub-System C: RAG Query Engine (Natural Language Q&A)

> This is the PM-facing interface that answers specific product questions.

**Technology Stack:** LangChain + Pinecone + Claude 3.5 Sonnet

**Flow:**

```
PM Question (natural language)
        │
        ▼
┌───────────────────┐
│  QUERY EMBEDDING  │  ── Convert question to vector embedding
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│  VECTOR SEARCH    │  ── Retrieve top-K most semantically relevant reviews
│  (Pinecone)       │     from the vector store (K=30 by default)
└─────────┬─────────┘
          │
          ▼
┌────────────────────────────────────────────────────────────────────┐
│  CONTEXT ASSEMBLY (LangChain)                                      │
│  ── Combine: retrieved reviews + daily_digest summary + metadata   │
└─────────────────────────────────┬──────────────────────────────────┘
                                  │
                                  ▼
                     ┌────────────────────────┐
                     │  LLM SYNTHESIS         │
                     │  (Claude 3.5 Sonnet)   │
                     │                        │
                     │  Generates answer with:│
                     │  • Summary paragraph   │
                     │  • Top 3-5 themes      │
                     │  • Direct user quotes  │
                     │  • Urgency level       │
                     │  • Recommended action  │
                     └────────────────────────┘
```

**Example Interaction:**

```
PM Question: "Why are users frustrated with the AI DJ this week?"

Engine Response:
┌─────────────────────────────────────────────────────────────────────┐
│ INSIGHT SUMMARY (June 22–29, 2026)                                  │
│                                                                     │
│ Users are primarily frustrated with the AI DJ because it rapidly   │
│ exhausts their favorite songs within 2–3 sessions and then begins  │
│ repeating them. The second most common complaint is that it        │
│ ignores explicit skip feedback, continuing to surface the skipped  │
│ songs in future sessions.                                          │
│                                                                     │
│ TOP THEMES: Algorithm Repetitiveness (78%), Skip Ignored (54%)     │
│ URGENCY: 4.1 / 5.0 (Elevated)                                      │
│                                                                     │
│ REPRESENTATIVE QUOTES:                                              │
│ "The AI DJ played the same Kendrick song 4 times in one week"      │
│   — Reddit r/spotify, 847 upvotes                                   │
│ "I skipped it 3 times. It came back 3 times. What's the point?"    │
│   — App Store Review, 1-star, June 24                              │
│                                                                     │
│ RECOMMENDED ACTION: Investigate skip-signal weighting in AI DJ     │
│ recommendation loop. Consider a hard 7-day cooldown on skipped     │
│ tracks.                                                             │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Phase 4 — Delivery & Integration Layer

> **Goal:** Surface insights where product teams already live and work.

### 4.1 PM Query Interface (Chat UI)

- A lightweight **web application** (Next.js + Tailwind) accessible internally via SSO (Okta).
- PMs type natural language questions. The RAG engine responds in real time.
- Each response includes **source citations** (platform, date, upvote count) that PMs can click to verify.
- **Saved Queries:** PMs can bookmark recurring queries for weekly tracking.

### 4.2 Automated Weekly Digest

- Every Monday at 8AM, an automated digest is generated and delivered via:
  - **Slack:** Posted to `#growth-pm-insights` channel
  - **Email:** Sent to all Growth Team stakeholders
  - **Confluence:** Automatically creates a new page under `Product Intelligence > Weekly Reviews`

**Digest Structure:**
```
📊 Spotify Review Intelligence | Week of June 23–29, 2026

Top Rising Theme:    "AI DJ Repetitiveness" ▲ 34% WoW
Top Urgency Issue:   "Skip Feedback Ignored" — Urgency 4.1/5.0
New Unmet Need:      "Genre-lock escape mode" (first detected this week)
Competitive Signal:  YouTube Music mentioned positively in 12% of reviews

[Full Report in Confluence →]
```

### 4.3 Jira Integration (Auto-Ticket Drafting)

When a theme's urgency score crosses a threshold (≥ 4.0/5.0) and volume exceeds 50 mentions in 7 days, the system automatically **drafts a Jira ticket** in the Growth backlog:

```json
{
  "summary": "[AI Engine] High urgency: Skip feedback ignored by AI DJ",
  "description": "Detected 127 user mentions in 7 days. Urgency: 4.1/5. See full report: [link]",
  "labels": ["user-sentiment", "discovery-engine", "auto-generated"],
  "priority": "High",
  "reporter": "Review Discovery Engine Bot"
}
```

---

## Technology Stack Summary

| Layer | Component | Technology Choice | Rationale |
|---|---|---|---|
| **Orchestration** | Workflow Automation | `n8n` (self-hosted) | Visual pipelines, easy monitoring, no per-task pricing |
| **Ingestion** | API Clients | `PRAW`, `tweepy`, custom scrapers | Best-in-class libraries for each platform |
| **Processing** | Cleaning Service | Python / FastAPI | Fast, async-capable microservice |
| **Embedding** | Embedding Model | `text-embedding-3-small` (OpenAI) | Best cost-quality ratio for semantic search |
| **Vector Store** | Vector Database | Pinecone (Serverless) | Managed, scalable, low-latency retrieval |
| **Raw Store** | Relational DB | PostgreSQL (AWS RDS) | Reliable, ACID-compliant, SQL-queryable |
| **Queue** | Async Processing | Redis (ElastiCache) | Fast in-memory queue between pipeline steps |
| **AI Backbone** | LLM for Analysis | Claude 3.5 Sonnet | Best-in-class for structured extraction + long context |
| **RAG Framework** | Query Orchestration | LangChain | Mature, well-documented RAG toolchain |
| **Frontend** | PM Query Interface | Next.js + Vercel | Fast to ship, SSR-capable, SSO-ready |
| **Delivery** | Notifications | Slack API + SendGrid | Meets PMs where they already work |
| **Ticketing** | Auto-Drafts | Jira REST API | Closes the loop from insight to action |

---

## Phase Rollout Roadmap

```
WEEK 1-2  │ Phase 1 Live
           │ ├── n8n pipelines active for Reddit + App Store
           │ └── Raw PostgreSQL schema populated, PII anonymized
           │
WEEK 3     │ Phase 2 Live
           │ ├── Cleaning & noise-filtering microservice deployed
           │ └── Embeddings generated; Pinecone index populated
           │
WEEK 4     │ Phase 3A Live (Thematic Extraction)
           │ ├── Claude extraction running on all new reviews
           │ └── Daily aggregation jobs running
           │
WEEK 5     │ Phase 3C Live (RAG Query Engine)
           │ ├── LangChain RAG pipeline connected to Pinecone + Claude
           │ └── Internal alpha testing with 2 PMs
           │
WEEK 6     │ Phase 4 Live
           │ ├── Next.js PM query UI deployed (internal SSO)
           │ ├── Weekly Slack digest automated
           │ └── Jira auto-ticket drafting active
           │
WEEK 7     │ Beta Launch
           │ ├── All Growth Team PMs onboarded
           │ └── KPI measurement vs. baseline begins
           │
WEEK 10    │ Full Production
           │ ├── X/Twitter + Spotify Community pipelines added
           │ └── v2.0 planning: multilingual support, Hindi + Portuguese
```

---

## Risk Mitigation (Architecture Level)

| Risk | Mitigation |
|---|---|
| **LLM Hallucination** | All outputs require citation grounding. RAG architecture ensures answers are anchored to real reviews. |
| **API Rate Limits** | Exponential backoff + request queuing in Redis. Separate rate-limit budgets per source. |
| **Data Volume Spikes** | Serverless Pinecone + auto-scaling RDS handles traffic spikes gracefully. |
| **Model Cost Overrun** | Claude called only on relevance-filtered reviews (≥0.6 score). Estimated 60% cost reduction vs. processing all reviews. |
| **Single Point of Failure** | n8n pipelines are stateless; each stage writes to DB before passing forward. Any stage can restart without data loss. |

---

*This architecture document is maintained by the Growth Team Engineering Lead and updated at each phase completion.*

**Document Owner:** Engineering Lead, Growth Team
**Stakeholders:** Data Engineering, AI/ML, PM, UXR, Legal & Privacy
