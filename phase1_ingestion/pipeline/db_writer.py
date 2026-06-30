"""
pipeline/db_writer.py
─────────────────────────────────────────────────────────────────────────────
PostgreSQL Writer
Architecture Ref: Phase 1 § 1.2 — Ingestion Orchestration → Raw Data Store

Handles all writes to the PostgreSQL raw_reviews and ingestion_runs tables.
Uses ON CONFLICT DO NOTHING to make writes idempotent (safe to retry).
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import os
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Generator

import psycopg2
import psycopg2.extras
from loguru import logger

from pipeline.normalizer import RawReview


# ── Connection ──────────────────────────────────────────────────────────────

def get_connection_string() -> str:
    """Read the DATABASE_URL from environment variables."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise EnvironmentError(
            "DATABASE_URL environment variable is not set. "
            "Example: postgresql://user:password@localhost:5432/reviews_db"
        )
    return url


@contextmanager
def get_db_connection() -> Generator[psycopg2.extensions.connection, None, None]:
    """
    Context manager for PostgreSQL connections.
    Automatically commits on success, rolls back on exception.
    """
    conn = psycopg2.connect(get_connection_string())
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ── Review Writer ───────────────────────────────────────────────────────────

INSERT_REVIEW_SQL = """
INSERT INTO raw_reviews (
    review_id, source_platform, source_url, source_post_id,
    review_text, review_title, rating, upvotes, comment_count,
    author_hash, language, geo_region, is_gdpr_region,
    published_at, ingested_at, processing_status, is_compliant,
    retention_expires_at
)
VALUES (
    %(review_id)s, %(source_platform)s, %(source_url)s, %(source_post_id)s,
    %(review_text)s, %(review_title)s, %(rating)s, %(upvotes)s, %(comment_count)s,
    %(author_hash)s, %(language)s, %(geo_region)s, %(is_gdpr_region)s,
    %(published_at)s, %(ingested_at)s, %(processing_status)s, %(is_compliant)s,
    %(retention_expires_at)s
)
ON CONFLICT (review_id) DO NOTHING
RETURNING review_id;
"""


def write_review(review: RawReview) -> bool:
    """
    Write a single RawReview to the database.

    Returns:
        True if the review was inserted, False if it was a duplicate (skipped).
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(INSERT_REVIEW_SQL, review.to_dict())
            result = cur.fetchone()
            inserted = result is not None
            if inserted:
                logger.debug(f"Inserted review {review.review_id} from {review.source_platform}")
            else:
                logger.debug(f"Skipped duplicate review {review.review_id}")
            return inserted


def write_reviews_batch(reviews: list[RawReview]) -> dict[str, int]:
    """
    Write a batch of RawReviews using executemany for efficiency.

    Returns:
        A summary dict: {'total': N, 'inserted': N, 'skipped': N}
    """
    if not reviews:
        return {"total": 0, "inserted": 0, "skipped": 0}

    records = [r.to_dict() for r in reviews]
    inserted_count = 0

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            for record in records:
                cur.execute(INSERT_REVIEW_SQL, record)
                if cur.fetchone():
                    inserted_count += 1

    skipped = len(reviews) - inserted_count
    logger.info(
        f"Batch write complete: {inserted_count} inserted, {skipped} skipped "
        f"(duplicates) out of {len(reviews)} total."
    )
    return {"total": len(reviews), "inserted": inserted_count, "skipped": skipped}


# ── Ingestion Run Logger ─────────────────────────────────────────────────────

START_RUN_SQL = """
INSERT INTO ingestion_runs (run_id, source_platform, started_at, status, metadata)
VALUES (%(run_id)s, %(source_platform)s, %(started_at)s, 'running', %(metadata)s)
RETURNING run_id;
"""

COMPLETE_RUN_SQL = """
UPDATE ingestion_runs
SET
    completed_at = %(completed_at)s,
    status = %(status)s,
    reviews_fetched = %(reviews_fetched)s,
    reviews_stored = %(reviews_stored)s,
    reviews_skipped = %(reviews_skipped)s,
    error_message = %(error_message)s
WHERE run_id = %(run_id)s;
"""


def start_ingestion_run(source_platform: str, metadata: dict | None = None) -> str:
    """
    Log the start of a scraper run. Returns the run_id for tracking.
    """
    run_id = str(uuid.uuid4())
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(START_RUN_SQL, {
                "run_id": run_id,
                "source_platform": source_platform,
                "started_at": datetime.now(tz=timezone.utc),
                "metadata": psycopg2.extras.Json(metadata or {}),
            })
    logger.info(f"Started ingestion run {run_id} for platform: {source_platform}")
    return run_id


def complete_ingestion_run(
    run_id: str,
    status: str,
    reviews_fetched: int = 0,
    reviews_stored: int = 0,
    reviews_skipped: int = 0,
    error_message: str | None = None,
) -> None:
    """
    Update the ingestion run record with the final outcome.

    Args:
        run_id: The UUID returned by start_ingestion_run.
        status: 'success' | 'partial' | 'failed'
        reviews_fetched: Total reviews retrieved from source.
        reviews_stored: Reviews successfully written to DB.
        reviews_skipped: Duplicates or compliance-excluded reviews.
        error_message: Error description if status is 'failed' or 'partial'.
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(COMPLETE_RUN_SQL, {
                "run_id": run_id,
                "completed_at": datetime.now(tz=timezone.utc),
                "status": status,
                "reviews_fetched": reviews_fetched,
                "reviews_stored": reviews_stored,
                "reviews_skipped": reviews_skipped,
                "error_message": error_message,
            })
    logger.info(
        f"Completed run {run_id} | status={status} | "
        f"fetched={reviews_fetched}, stored={reviews_stored}, skipped={reviews_skipped}"
    )


# ── Compliance Reader ────────────────────────────────────────────────────────

def get_approved_sources() -> set[str]:
    """
    Query the source_compliance table and return the set of approved platforms.
    Used by each scraper as a gate before ingestion begins.
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT source_platform FROM source_compliance WHERE is_approved = TRUE;")
            rows = cur.fetchall()
    approved = {row[0] for row in rows}
    logger.debug(f"Approved sources for ingestion: {approved}")
    return approved
