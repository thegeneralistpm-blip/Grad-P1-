# Problem Statement: AI-Powered Review Discovery Engine

> **Product Team:** Growth Team (Internal Tools)
> **Platform:** Spotify
> **Version:** 1.0
> **Date:** June 2026
> **Status:** Active Project

---

## 1. Background & Context

The Growth Team at Spotify relies heavily on quantitative data (skip rates, session lengths, completion rates) to evaluate the performance of our recommendation systems. However, quantitative data only tells us *what* users are doing, not *why* they are doing it. 

To understand the *why*, we need qualitative data from user reviews, community forums, and social media. Currently, millions of users are leaving valuable feedback about their struggles with music discovery across various platforms (App Store, Google Play Store, Reddit, X/Twitter, and Spotify Community forums). 

## 2. Problem Statement

> **The Growth Team currently lacks a centralized, scalable, and automated system to aggregate, process, and analyze qualitative user feedback across multiple external platforms. This fragmentation prevents product managers and engineers from identifying emerging pain points, unearthing root causes behind user frustration with recommendations, and prioritizing product interventions effectively.**

Without an intelligent system to process this massive volume of unstructured text, we are effectively flying blind on user sentiment, leaving critical insights buried in noise and delaying our response to user dissatisfaction.

---

## 3. Evidence & Current State Challenges

- **Data Fragmentation:** User feedback is scattered across at least 5 distinct primary platforms, requiring manual scraping or ad-hoc analysis.
- **Volume & Noise:** The sheer volume of daily reviews makes human review impossible. A significant portion of reviews are spam, non-actionable complaints (e.g., "app crashed"), or unrelated to recommendations.
- **Lack of Nuance:** Traditional sentiment analysis (Positive/Negative/Neutral) is insufficient. We need to extract specific themes such as "algorithm repetition," "desire for novelty," or "frustration with Discover Weekly."
- **Delayed Feedback Loops:** Because qualitative analysis is currently a manual, high-effort process, insights are often outdated by the time they reach the product development cycle.

---

## 4. Root Cause Analysis

Why hasn't this been solved yet?

```
Root Cause Tree
│
├── [Technical] High volume of unstructured qualitative data
│       └── Traditional databases and querying tools cannot extract thematic meaning from free-text.
│
├── [Operational] Disparate data sources
│       └── APIs and scraping requirements differ wildly between Reddit, App Stores, and Forums.
│
├── [Tooling] Insufficient NLP infrastructure for product teams
│       └── Existing internal tools are built for quantitative telemetry, not semantic analysis.
│
└── [Process] Ad-hoc qualitative research
        └── User Research teams conduct deep but narrow studies, missing the broad, continuous pulse of the community.
```

---

## 5. Who Is Affected?

- **Product Managers (Growth & Discovery Teams):** Cannot easily identify user pain points or validate hypotheses without waiting for slow, manual qualitative research cycles.
- **Data Science & Algorithm Teams:** Lack the contextual "why" behind anomalous quantitative metrics (e.g., sudden spikes in skip rates on specific playlists).
- **User Research (UXR):** Spend excessive time manually coding and categorizing feedback instead of conducting high-value strategic research.

---

## 6. Business Impact

| Impact Area | Description |
|---|---|
| **Slower Time-to-Market** | It takes too long to identify and validate user pain points regarding discovery, delaying necessary product interventions. |
| **Misaligned Priorities** | Without clear thematic data, we risk optimizing the algorithm for metrics that run counter to actual user desires (e.g., optimizing for low skip-rates when users actually want high novelty). |
| **Resource Drain** | Manual aggregation and thematic coding of reviews is an inefficient use of UXR and PM time. |
| **Missed Churn Signals** | Emerging frustration trends that could predict churn are missed entirely until they surface in NPS surveys — months too late. |
| **Competitive Blindspot** | Without systematic community listening, we cannot detect when users are migrating to YouTube Music or Apple Music due to unresolved discovery friction. |
| **Reduced AI/Algorithm Accountability** | Engineering teams cannot correlate algorithm updates with specific changes in qualitative user sentiment without this feedback loop. |

---

## 7. Key Research Questions the Engine Must Answer

The AI-Powered Review Discovery Engine is specifically designed to answer the following product-critical questions at scale:

| # | Research Question | Why It Matters |
|---|---|---|
| 1 | Why do users struggle to discover new music despite having access to algorithmic playlists? | Pinpoints the specific gap between feature intent and user experience. |
| 2 | What are the most common, recurring frustrations with Spotify's recommendation features? | Enables prioritization of algorithm improvements by frequency and severity. |
| 3 | What listening behaviors and goals are users actively trying to achieve? | Uncovers unmet Jobs-to-be-Done that the current product does not serve. |
| 4 | What causes users to repeatedly listen to the same content, even when they dislike it? | Identifies lock-in mechanisms in the current UX and algorithm design. |
| 5 | Which user segments experience fundamentally different discovery challenges? | Enables targeted, segment-specific product interventions. |
| 6 | What unmet needs emerge consistently and at high volume across all feedback sources? | Surfaces the highest-impact opportunities for new feature development. |
| 7 | How does qualitative sentiment change after major algorithm or feature updates? | Creates a feedback loop between engineering releases and user reaction. |

---

## 8. Scope & Boundaries

### In Scope
- **Data Sources:** Apple App Store (iOS), Google Play Store (Android), Reddit (r/spotify, r/truespotify, r/listentothis), Spotify Community Forums, and X/Twitter (public posts).
- **Languages:** English (v1.0). Multilingual support (Hindi, Portuguese, Spanish) planned for v2.0.
- **Geography:** Global, with the ability to filter by market (US, India, Brazil, UK).
- **Time Window:** Rolling 12-month lookback with real-time ingestion for new reviews.
- **Topics:** Focused exclusively on Music Discovery, Recommendations, Algorithm Behavior, and Playlist Generation.

### Out of Scope
- Internal employee feedback or support tickets.
- Podcast, audiobook, or video content feedback.
- Reviews related to pricing, billing, or technical app crashes.
- Any user-identifiable PII (names, emails, account IDs).

---

## 9. Constraints & Risks

> [!WARNING]
> These risks must be mitigated before or during the build phase.

| Risk | Category | Mitigation Strategy |
|---|---|---|
| **GDPR / CCPA Compliance** | Legal / Privacy | Process only publicly available data; anonymize all user handles before storage; engage Legal for sign-off. |
| **API Rate Limits & ToS** | Technical | Reddit and App Store APIs enforce strict rate limits. Use respectful crawling intervals; cache responses; explore official data partnerships. |
| **LLM Hallucination** | AI Quality | All AI-generated summaries must be grounded in and traceable to direct source quotes. Implement citation-backed outputs only. |
| **Survivorship Bias in Reviews** | Data Quality | Reviews skew toward extreme sentiment (very happy or very angry users). Balance thematic analysis with volume-weighting and platform diversity. |
| **Data Freshness & Staleness** | Operational | Define an SLA for ingestion frequency (e.g., daily batch or near-real-time) to ensure insights are not acting on outdated feedback. |

---

## 10. Desired Outcome

We need to build an **AI-Powered Review Discovery Engine**. A successfully deployed system will achieve the following measurable outcomes:

1. **Automated Aggregation:** Ingest continuous streams of reviews/discussions from App Store, Play Store, Reddit (r/spotify, r/truespotify), and Spotify Community.
2. **Thematic Extraction:** Automatically tag and categorize feedback into predefined and emergent themes (e.g., "Repetitiveness," "Lack of Control," "Nostalgia vs. Novelty").
3. **Sentiment & Urgency Scoring:** Accurately gauge the severity of specific complaints to prioritize engineering tickets.
4. **Natural Language Querying:** Allow PMs to ask the system questions like, *"Why are users frustrated with the AI DJ this week?"* and receive synthesized answers backed by direct quotes.
5. **Reduced Time-to-Insight:** Decrease the time it takes to synthesize qualitative feedback from weeks to minutes.

---

## 11. Success Metrics (KPIs)

The engine's success will be evaluated against these concrete, measurable targets:

| KPI | Baseline (Current) | Target (Post-Launch) |
|---|---|---|
| **Time-to-Insight** (qualitative synthesis) | ~2–3 weeks (manual) | < 10 minutes (automated) |
| **Review Coverage** (% of public reviews analyzed) | < 5% (ad-hoc sampling) | > 90% (continuous ingestion) |
| **Thematic Accuracy** (vs. human coder) | N/A | ≥ 85% agreement rate |
| **PM Adoption Rate** | 0 (no tool exists) | ≥ 70% of Growth Team PMs using weekly |
| **Actionable Insights Generated per Sprint** | ~1–2 (manual UXR) | ≥ 5 per two-week sprint |

---

## 12. Open Questions for System Architecture

Before finalizing the technical implementation plan, we need to answer:

- [ ] Which AI-native stack (e.g., Claude, OpenAI, RAG architecture, n8n, Zapier) is best suited for our data privacy constraints and volume?
- [ ] How will we handle rate limits and API access for scraping Reddit and App Store data continuously?
- [ ] What vector database will we use to store embedded reviews for semantic search (e.g., Pinecone, Weaviate, ChromaDB)?
- [ ] How will this engine integrate with our existing PM tools (Jira, Confluence) to surface insights automatically?
- [ ] Should theme taxonomies be fixed/predefined or allowed to emerge dynamically from the data (unsupervised clustering)?
- [ ] What is the acceptable hallucination rate threshold for AI-generated summaries before human review is required?

---

## 13. Next Steps

| Phase | Action | Owner | Timeline |
|---|---|---|---|
| **Problem Validation** | Confirm scope, research questions, and KPIs with all stakeholders | Growth PM | Week 1 |
| **Legal & Compliance Review** | Get sign-off on data sources and PII handling strategy | Legal + Privacy | Week 1 |
| **Architecture Design** | Evaluate LLMs, RAG frameworks, vector DBs, and ingestion tools | Engineering Lead | Week 2 |
| **Data Ingestion Pilot** | Build pipelines for Reddit and App Store API; validate data quality | Data Engineering | Week 3 |
| **AI Processing Pilot** | Implement prompt engineering and thematic extraction with Claude/GPT | AI Engineer | Week 4 |
| **Dashboard/UI V1** | Build a simple natural language query interface for PMs | Full Stack Dev | Week 5 |
| **KPI Baseline Measurement** | Measure time-to-insight and coverage before go-live for comparison | Data Science | Week 5 |
| **Beta Testing & Iteration** | Beta test with Growth Team PMs; collect usability feedback | PM + UXR | Week 6 |
| **Full Launch** | Onboard all Growth Team PMs; establish weekly insight cadence | PM | Week 7 |

---

*This document is a living artifact. It will be updated as technical decisions are made, stakeholder feedback is incorporated, and the project evolves.*

---
**Document Owner:** Growth Team, Product Management
**Stakeholders:** Engineering, Data Science, UX Research, Legal & Privacy, Marketing
