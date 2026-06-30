"""
api/main.py
─────────────────────────────────────────────────────────────────────────────
FastAPI Ingestion Service
Architecture Ref: Phase 1 § 1.2 — n8n triggers webhook → this service

This service is the HTTP interface between n8n workflows and the Python
scrapers. n8n CRON nodes call these endpoints on schedule, triggering
the appropriate scraper for each platform.

Endpoints:
  POST /ingest/{platform}          — Trigger a scraper run
  GET  /status/runs                — List recent ingestion runs
  GET  /status/compliance          — View source compliance registry
  GET  /health                     — Health check for Docker / n8n
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Literal

import psycopg2
import psycopg2.extras
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from loguru import logger
from pydantic import BaseModel

from scrapers.reddit_scraper import RedditScraper
from scrapers.appstore_scraper import AppStoreScraper
from scrapers.playstore_scraper import PlayStoreScraper
from scrapers.twitter_scraper import TwitterScraper
from scrapers.spotify_forum_scraper import SpotifyForumScraper
from scrapers.youtube_scraper import YouTubeScraper
from pipeline.db_writer import get_connection_string


# ── Supported Platforms ─────────────────────────────────────────────────────

PlatformName = Literal["reddit", "app_store", "play_store", "twitter", "spotify_community"]

SCRAPER_MAP = {
    "reddit": lambda: RedditScraper(mode="new"),
    "reddit_seed": lambda: RedditScraper(mode="top"),
    "app_store": AppStoreScraper,
    "play_store": PlayStoreScraper,
    "twitter": TwitterScraper,
    "spotify_community": SpotifyForumScraper,
    "youtube": YouTubeScraper,
}


# ── App Lifecycle ───────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run startup checks when the service boots."""
    logger.info("Review Discovery Engine — Ingestion API starting up.")
    logger.info(f"Database: {get_connection_string().split('@')[-1]}")  # Hide credentials in log
    yield
    logger.info("Ingestion API shutting down.")


# ── FastAPI App ─────────────────────────────────────────────────────────────

app = FastAPI(
    title="Spotify Review Discovery Engine — Ingestion API",
    description=(
        "Phase 1 ingestion service. Triggered by n8n CRON workflows. "
        "Scrapes reviews from App Store, Play Store, Reddit, Twitter, and Spotify Community."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


# ── Request / Response Models ────────────────────────────────────────────────

class IngestResponse(BaseModel):
    status: str
    platform: str
    message: str
    job_id: str | None = None


class RunSummary(BaseModel):
    run_id: str
    source_platform: str
    started_at: str
    completed_at: str | None
    status: str
    reviews_fetched: int
    reviews_stored: int
    reviews_skipped: int
    error_message: str | None


# ── Background Job Runner ───────────────────────────────────────────────────

def _run_scraper_background(platform: str) -> None:
    """Execute a scraper run in a background thread."""
    scraper_factory = SCRAPER_MAP.get(platform)
    if not scraper_factory:
        logger.error(f"No scraper found for platform: {platform}")
        return

    scraper = scraper_factory()
    result = scraper.run()
    logger.info(f"Background scrape complete for {platform}: {result}")


# ── Endpoints ───────────────────────────────────────────────────────────────

@app.get("/health", tags=["System"])
def health_check():
    """
    Health check endpoint. Used by Docker healthchecks and n8n to verify the
    service is running before triggering ingestion.
    """
    try:
        conn = psycopg2.connect(get_connection_string())
        conn.close()
        db_status = "connected"
    except Exception as exc:
        db_status = f"error: {exc}"

    return {
        "status": "ok",
        "service": "review-discovery-ingestion-api",
        "version": "1.0.0",
        "database": db_status,
    }


@app.post("/ingest/{platform}", response_model=IngestResponse, tags=["Ingestion"])
async def trigger_ingestion(
    platform: str,
    background_tasks: BackgroundTasks,
):
    """
    Trigger a scraper run for the specified platform.
    The scrape runs in a background task so n8n doesn't time out waiting.

    Called by n8n CRON workflow nodes on schedule:
    - reddit / twitter: every 4 hours
    - app_store / play_store / spotify_community: daily at 2AM UTC

    Args:
        platform: One of: reddit, reddit_seed, app_store, play_store,
                  twitter, spotify_community
    """
    if platform not in SCRAPER_MAP:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Platform '{platform}' not found. "
                f"Available: {list(SCRAPER_MAP.keys())}"
            ),
        )

    logger.info(f"Ingestion triggered for platform: {platform}")
    background_tasks.add_task(_run_scraper_background, platform)

    return IngestResponse(
        status="accepted",
        platform=platform,
        message=f"Ingestion started for '{platform}'. Check /status/runs for progress.",
    )


@app.get("/status/runs", response_model=list[RunSummary], tags=["Monitoring"])
def get_recent_runs(limit: int = 20, platform: str | None = None):
    """
    List the most recent ingestion runs with their outcomes.
    Useful for monitoring from n8n or a dashboard.

    Args:
        limit: Max number of runs to return (default 20).
        platform: Optional filter by platform name.
    """
    try:
        conn = psycopg2.connect(get_connection_string())
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if platform:
                cur.execute(
                    """
                    SELECT run_id, source_platform, started_at, completed_at, status,
                           reviews_fetched, reviews_stored, reviews_skipped, error_message
                    FROM ingestion_runs
                    WHERE source_platform = %s
                    ORDER BY started_at DESC
                    LIMIT %s
                    """,
                    (platform, limit),
                )
            else:
                cur.execute(
                    """
                    SELECT run_id, source_platform, started_at, completed_at, status,
                           reviews_fetched, reviews_stored, reviews_skipped, error_message
                    FROM ingestion_runs
                    ORDER BY started_at DESC
                    LIMIT %s
                    """,
                    (limit,),
                )
            rows = cur.fetchall()
        conn.close()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Database error: {exc}")

    return [
        RunSummary(
            run_id=str(r["run_id"]),
            source_platform=r["source_platform"],
            started_at=str(r["started_at"]),
            completed_at=str(r["completed_at"]) if r["completed_at"] else None,
            status=r["status"],
            reviews_fetched=r["reviews_fetched"] or 0,
            reviews_stored=r["reviews_stored"] or 0,
            reviews_skipped=r["reviews_skipped"] or 0,
            error_message=r["error_message"],
        )
        for r in rows
    ]


@app.get("/status/compliance", tags=["Monitoring"])
def get_compliance_status():
    """
    View the source compliance registry.
    Shows which platforms have been approved by the Legal team for ingestion.
    """
    try:
        conn = psycopg2.connect(get_connection_string())
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM source_compliance ORDER BY source_platform;")
            rows = cur.fetchall()
        conn.close()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Database error: {exc}")

    return [dict(r) for r in rows]


@app.get("/status/reviews", tags=["Monitoring"])
def get_review_counts():
    """
    Return a summary of review counts by platform and processing status.
    """
    try:
        conn = psycopg2.connect(get_connection_string())
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    source_platform,
                    processing_status,
                    COUNT(*) AS count,
                    MIN(published_at) AS oldest,
                    MAX(published_at) AS newest
                FROM raw_reviews
                GROUP BY source_platform, processing_status
                ORDER BY source_platform, processing_status;
                """
            )
            rows = cur.fetchall()
        conn.close()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Database error: {exc}")

    return [dict(r) for r in rows]
