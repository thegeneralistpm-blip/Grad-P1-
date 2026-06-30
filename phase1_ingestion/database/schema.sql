-- ============================================================
-- AI-Powered Review Discovery Engine — Phase 1
-- PostgreSQL Database Schema
-- ============================================================

-- Enable UUID generation extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── ENUM Types ───────────────────────────────────────────────
CREATE TYPE source_platform AS ENUM (
    'reddit',
    'app_store',
    'play_store',
    'twitter',
    'spotify_community',
    'youtube'
);

CREATE TYPE processing_status AS ENUM (
    'pending',      -- Newly ingested, awaiting Phase 2 processing
    'processing',   -- Currently being processed
    'processed',    -- Successfully processed by Phase 2
    'failed',       -- Processing failed (see error_message)
    'excluded'      -- Filtered out by compliance or relevance checks
);

-- ── Main Reviews Table ───────────────────────────────────────
CREATE TABLE IF NOT EXISTS raw_reviews (
    -- Identity
    review_id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Source
    source_platform     source_platform NOT NULL,
    source_url          TEXT,
    source_post_id      TEXT,               -- Original ID on the platform (e.g., Reddit post ID)

    -- Content
    review_text         TEXT NOT NULL,
    review_title        TEXT,               -- For Reddit post titles, forum thread titles
    rating              SMALLINT CHECK (rating BETWEEN 1 AND 5),  -- App store ratings (1-5)
    upvotes             INTEGER DEFAULT 0,
    comment_count       INTEGER DEFAULT 0,

    -- Author (PII-anonymized)
    author_hash         TEXT NOT NULL,      -- SHA-256 hash of original author handle

    -- Metadata
    language            CHAR(5) DEFAULT 'en',
    geo_region          TEXT,               -- Country/region code if detectable (e.g., 'US', 'IN')
    is_gdpr_region      BOOLEAN DEFAULT FALSE,  -- TRUE for EU regions

    -- Timestamps
    published_at        TIMESTAMPTZ,        -- When the review was originally posted
    ingested_at         TIMESTAMPTZ DEFAULT NOW(),

    -- Processing State (Phase 2 pipeline)
    processing_status   processing_status DEFAULT 'pending',
    content_hash        TEXT UNIQUE,        -- MD5 of review_text (for deduplication in Phase 2)
    error_message       TEXT,               -- Populated if processing_status = 'failed'

    -- Compliance
    is_compliant        BOOLEAN DEFAULT TRUE,
    retention_expires_at TIMESTAMPTZ        -- For GDPR: 90-day rolling window for EU users
);

-- ── Ingestion Run Log ────────────────────────────────────────
-- Tracks each scraper run for monitoring and debugging
CREATE TABLE IF NOT EXISTS ingestion_runs (
    run_id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_platform     source_platform NOT NULL,
    started_at          TIMESTAMPTZ DEFAULT NOW(),
    completed_at        TIMESTAMPTZ,
    status              TEXT DEFAULT 'running',   -- 'running' | 'success' | 'partial' | 'failed'
    reviews_fetched     INTEGER DEFAULT 0,
    reviews_stored      INTEGER DEFAULT 0,
    reviews_skipped     INTEGER DEFAULT 0,        -- Duplicates or compliance-excluded
    error_message       TEXT,
    metadata            JSONB                     -- Extra context (e.g., subreddit names, date range)
);

-- ── Source Compliance Registry ───────────────────────────────
-- Legal team approves each data source before it goes live
CREATE TABLE IF NOT EXISTS source_compliance (
    source_platform     source_platform PRIMARY KEY,
    is_approved         BOOLEAN DEFAULT FALSE,
    approved_by         TEXT,
    approved_at         TIMESTAMPTZ,
    notes               TEXT,
    api_tos_url         TEXT,
    last_reviewed_at    TIMESTAMPTZ
);

-- Seed with initial compliance records (all pending approval)
INSERT INTO source_compliance (source_platform, is_approved, notes)
VALUES
    ('reddit',              TRUE,  'Public JSON API — no key required, read-only public data'),
    ('app_store',           TRUE,  'Public reviews — no authentication required'),
    ('play_store',          TRUE,  'Public reviews — no authentication required'),
    ('twitter',             FALSE, 'Requires paid API — excluded from v1.0'),
    ('spotify_community',   TRUE,  'Publicly accessible forum — read-only scraping'),
    ('youtube',             FALSE, 'Pending: add YOUTUBE_API_KEY to .env to enable')
ON CONFLICT DO NOTHING;

-- ── Indexes ──────────────────────────────────────────────────
-- Speed up common query patterns

-- Find all unprocessed reviews (Phase 2 picks these up)
CREATE INDEX idx_reviews_pending
    ON raw_reviews (processing_status)
    WHERE processing_status = 'pending';

-- Filter reviews by platform and date range
CREATE INDEX idx_reviews_platform_date
    ON raw_reviews (source_platform, published_at DESC);

-- GDPR retention enforcement queries
CREATE INDEX idx_reviews_gdpr
    ON raw_reviews (is_gdpr_region, retention_expires_at)
    WHERE is_gdpr_region = TRUE;

-- Ingestion run monitoring
CREATE INDEX idx_ingestion_runs_platform
    ON ingestion_runs (source_platform, started_at DESC);

-- ── Comments ─────────────────────────────────────────────────
COMMENT ON TABLE raw_reviews IS
    'Phase 1 output: all raw user reviews ingested from external platforms, PII-anonymized.';

COMMENT ON TABLE ingestion_runs IS
    'Audit log of every scraper run. Used for monitoring, alerting, and debugging.';

COMMENT ON TABLE source_compliance IS
    'Legal compliance registry. Each source must be approved before its pipeline goes live.';

COMMENT ON COLUMN raw_reviews.author_hash IS
    'SHA-256 hash of the original author handle. Raw handles are NEVER stored.';

COMMENT ON COLUMN raw_reviews.content_hash IS
    'MD5 hash of review_text. Used in Phase 2 for deduplication. Set during processing.';
