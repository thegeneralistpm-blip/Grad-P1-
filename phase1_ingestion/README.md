# Phase 1 — Data Ingestion Layer
## AI-Powered Review Discovery Engine | Spotify Growth Team

---

## What This Is

This directory contains the complete **Phase 1 implementation** of the AI-Powered Review Discovery Engine. It is a production-ready data ingestion system that:

1. **Collects** user reviews and discussions from 5 platforms (App Store, Play Store, Reddit, X/Twitter, Spotify Community Forum)
2. **Normalizes** all reviews into a single, consistent schema
3. **Anonymizes** all author data (SHA-256 hashing) before any data touches the database
4. **Stores** cleaned reviews in PostgreSQL for processing by Phase 2
5. **Orchestrates** all pipelines via n8n CRON workflows

---

## Project Structure

```
phase1_ingestion/
├── docker-compose.yml          # Spins up all 4 services
├── Dockerfile                  # FastAPI ingestion service image
├── .env.example                # Required environment variables
├── requirements.txt            # Python dependencies
│
├── database/
│   └── schema.sql              # PostgreSQL schema (auto-applied on startup)
│
├── scrapers/                   # One scraper per platform
│   ├── base_scraper.py         # Abstract base: compliance → normalize → write
│   ├── reddit_scraper.py       # PRAW-based Reddit scraper
│   ├── appstore_scraper.py     # App Store scraper (7 country stores)
│   ├── playstore_scraper.py    # Play Store scraper (7 markets × 2 sort orders)
│   ├── twitter_scraper.py      # X API v2 via Tweepy
│   └── spotify_forum_scraper.py # BeautifulSoup + requests
│
├── pipeline/                   # Data processing modules
│   ├── normalizer.py           # Maps raw platform data → RawReview dataclass
│   ├── pii_handler.py          # SHA-256 hashing, GDPR detection, text scrubbing
│   └── db_writer.py            # PostgreSQL writes, audit logging, compliance gate
│
├── api/
│   └── main.py                 # FastAPI service — HTTP interface for n8n
│
└── n8n/workflows/
    ├── reddit_ingestion.json   # 4-hour CRON for Reddit + Twitter
    └── appstore_ingestion.json # 2AM daily CRON for App Store + Play Store + Forum
```

---

## Quick Start

### Prerequisites
- Docker Desktop installed and running
- API credentials for Reddit and/or Twitter (see `.env.example`)

### Step 1 — Copy and configure environment variables
```bash
cp .env.example .env
# Edit .env with your API credentials
```

### Step 2 — Start all services
```bash
docker-compose up -d
```

This will start:
| Service | URL | Description |
|---|---|---|
| **FastAPI API** | http://localhost:8000 | Ingestion service |
| **API Docs** | http://localhost:8000/docs | Interactive Swagger UI |
| **n8n UI** | http://localhost:5678 | Workflow orchestration |
| **PostgreSQL** | localhost:5432 | Raw review database |
| **Redis** | localhost:6379 | Processing queue |

### Step 3 — Approve data sources (Legal gate)
Before any ingestion can run, each source must be approved in the database:
```sql
-- Run in your PostgreSQL client after getting Legal sign-off
UPDATE source_compliance
SET is_approved = TRUE, approved_by = 'legal-team@spotify.com', approved_at = NOW()
WHERE source_platform = 'reddit';
```

### Step 4 — Load n8n workflows
1. Open n8n at http://localhost:5678
2. Go to **Settings → Import Workflow**
3. Import both files from `n8n/workflows/`
4. Activate both workflows

### Step 5 — Verify ingestion
```bash
# Check the API is healthy
curl http://localhost:8000/health

# Trigger a test Reddit scrape manually
curl -X POST http://localhost:8000/ingest/reddit

# Check ingestion run results
curl http://localhost:8000/status/runs

# Check review counts in DB
curl http://localhost:8000/status/reviews
```

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Service health check |
| `POST` | `/ingest/{platform}` | Trigger a scraper run |
| `GET` | `/status/runs` | List recent ingestion runs |
| `GET` | `/status/compliance` | View source compliance registry |
| `GET` | `/status/reviews` | Review counts by platform & status |
| `GET` | `/docs` | Interactive API documentation (Swagger) |

**Available platforms:** `reddit`, `reddit_seed`, `app_store`, `play_store`, `twitter`, `spotify_community`

---

## Ingestion Schedule

| Source | Frequency | n8n Workflow |
|---|---|---|
| Reddit | Every 4 hours | `reddit_ingestion.json` |
| Twitter / X | Every 4 hours | `reddit_ingestion.json` (shared) |
| App Store | Daily at 2AM UTC | `appstore_ingestion.json` |
| Play Store | Daily at 2AM UTC | `appstore_ingestion.json` (shared) |
| Spotify Community | Daily at 2AM UTC | `appstore_ingestion.json` (shared) |

---

## Data Flow

```
n8n CRON Trigger
      │
      ▼
POST /ingest/{platform}  (FastAPI)
      │
      ▼
Compliance Gate Check  (source_compliance table)
      │
      ▼
Scraper.fetch()  ──→  Raw dict from source API/scraper
      │
      ▼
normalize(platform, raw_dict)  ──→  RawReview dataclass
      │  (includes PII hashing, GDPR tagging)
      ▼
write_reviews_batch()  ──→  PostgreSQL raw_reviews table
      │  (ON CONFLICT DO NOTHING — idempotent)
      ▼
complete_ingestion_run()  ──→  ingestion_runs audit log
```

---

## Compliance & Privacy

- **Author handles** are **never stored**. They are SHA-256 hashed before the record is created.
- **GDPR regions** (EU/EEA/CH/GB) are automatically tagged. Data from these regions expires after 90 days.
- **Each source** requires explicit approval in the `source_compliance` table before ingestion starts.
- **PII in review text** (emails, phone numbers, @mentions) is scrubbed with regex patterns before storage.

---

## What Phase 2 Consumes

Phase 2 (Processing & Storage Layer) will query:
```sql
SELECT * FROM raw_reviews WHERE processing_status = 'pending' LIMIT 1000;
```
And update each record to `processing_status = 'processed'` after it completes the cleaning, deduplication, embedding generation, and vector store insertion pipeline.
