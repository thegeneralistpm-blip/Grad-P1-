"""
pipeline_runner.py
─────────────────────────────────────────────────────────────────────────────
Phase 2 Orchestrator
Architecture Ref: Phase 2 § 2.8

Pulls pending raw reviews from PostgreSQL, processes them through the 7-step
pipeline, generates vector embeddings, indexes them, and updates statuses.
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import os
import sys
import time
import psycopg2
import psycopg2.extras
from loguru import logger

# Add the current directory and its parent to the path to resolve imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from processors.deduplicator import deduplicate
from processors.language_detector import detect_language
from processors.noise_filter import filter_noise
from processors.relevance_scorer import calculate_relevance
from processors.enricher import enrich_review
from processors.embedder import generate_embedding
from storage.vector_writer import VectorDBWriter

BATCH_SIZE = 100
SLEEP_INTERVAL = 10  # Seconds to wait if no reviews are pending


def get_db_connection():
    """Create a database connection using the DATABASE_URL environment variable."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        # Check parent folder config or default to standard development host
        db_user = os.environ.get("POSTGRES_USER", "review_engine")
        db_password = os.environ.get("POSTGRES_PASSWORD", "ReviewEngine2026!")
        db_name = os.environ.get("POSTGRES_DB", "reviews_db")
        url = f"postgresql://{db_user}:{db_password}@localhost:5432/{db_name}"
    
    return psycopg2.connect(url)


def process_batch(conn, vector_writer) -> int:
    """
    Fetch a batch of pending reviews and run them through the processing pipeline.

    Returns:
        The number of reviews processed.
    """
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        # Fetch pending reviews
        cur.execute(
            """
            SELECT review_id, source_platform, source_url, source_post_id,
                   review_text, review_title, rating, upvotes, comment_count,
                   author_hash, language, geo_region, is_gdpr_region,
                   published_at, ingested_at
            FROM raw_reviews
            WHERE processing_status = 'pending'
            LIMIT %s;
            """,
            (BATCH_SIZE,)
        )
        batch = cur.fetchall()

    if not batch:
        return 0

    logger.info(f"[Pipeline] Processing batch of {len(batch)} reviews...")
    processed_count = 0

    for raw_row in batch:
        review = dict(raw_row)
        review_id = review["review_id"]
        
        try:
            # Update status to processing
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE raw_reviews SET processing_status = 'processing' WHERE review_id = %s;",
                    (review_id,)
                )
            conn.commit()

            # Step 1: Deduplicate (handles status update if duplicate)
            cleaned_review = deduplicate(review, conn)
            if not cleaned_review:
                continue

            # Step 2: Language Detection
            cleaned_review = detect_language(cleaned_review)
            if not cleaned_review:
                # Mark as excluded (non-English)
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE raw_reviews
                        SET processing_status = 'excluded',
                            error_message = 'Non-English language detected'
                        WHERE review_id = %s;
                        """,
                        (review_id,)
                    )
                conn.commit()
                continue

            # Step 3: Noise Filtering
            cleaned_review = filter_noise(cleaned_review)
            if not cleaned_review:
                # Mark as excluded (noise/technical/spam)
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE raw_reviews
                        SET processing_status = 'excluded',
                            error_message = 'Classified as noise/technical/spam'
                        WHERE review_id = %s;
                        """,
                        (review_id,)
                    )
                conn.commit()
                continue

            # Step 4: Relevance Scoring
            cleaned_review = calculate_relevance(cleaned_review)
            if not cleaned_review:
                # Mark as excluded (irrelevant)
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE raw_reviews
                        SET processing_status = 'excluded',
                            error_message = 'Low relevance to music discovery'
                        WHERE review_id = %s;
                        """,
                        (review_id,)
                    )
                conn.commit()
                continue

            # Step 5: Enrichment
            cleaned_review = enrich_review(cleaned_review)

            # Step 6: Generate Embedding
            embedding, dims = generate_embedding(cleaned_review["review_text"])

            # Step 7: Index in Vector Store
            metadata = {
                "review_id": review_id,
                "source_platform": cleaned_review["source_platform"],
                "rating": cleaned_review["rating"],
                "upvotes": cleaned_review["upvotes"],
                "word_count": cleaned_review["word_count"],
                "platform_weight": cleaned_review["platform_weight"],
                "review_age_days": cleaned_review["review_age_days"],
                "review_text": cleaned_review["review_text"]
            }
            
            indexed = vector_writer.upsert(
                review_id=review_id,
                vector=embedding,
                dimensions=dims,
                metadata=metadata
            )

            if not indexed:
                raise RuntimeError("Failed to index review embedding in vector store.")

            # Update status to processed
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE raw_reviews
                    SET processing_status = 'processed',
                        error_message = NULL
                    WHERE review_id = %s;
                    """,
                    (review_id,)
                )
            conn.commit()
            processed_count += 1
            logger.info(f"[Pipeline] Successfully processed review {review_id}")

        except Exception as exc:
            logger.error(f"[Pipeline] Error processing review {review_id}: {exc}")
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE raw_reviews
                        SET processing_status = 'failed',
                            error_message = %s
                        WHERE review_id = %s;
                        """,
                        (str(exc), review_id)
                    )
                conn.commit()
            except Exception as db_exc:
                logger.error(f"[Pipeline] Database rollback/status update failed: {db_exc}")
                conn.rollback()

    return processed_count


def main():
    """Main execution loop for Phase 2 daemon."""
    logger.info("[Pipeline] Starting Phase 2 Processing Engine...")
    
    # Wait for Database connectivity
    conn = None
    retries = 5
    while retries > 0:
        try:
            conn = get_db_connection()
            logger.info("[Pipeline] Database connected successfully.")
            break
        except Exception as exc:
            logger.warning(f"[Pipeline] Database connection failed: {exc}. Retrying in 5s...")
            retries -= 1
            time.sleep(5)
            
    if not conn:
        logger.error("[Pipeline] Could not connect to Database. Exiting.")
        sys.exit(1)

    # Initialize Vector Store Writer
    vector_writer = VectorDBWriter(conn)

    try:
        while True:
            processed = process_batch(conn, vector_writer)
            if processed == 0:
                logger.debug(f"[Pipeline] No pending reviews. Sleeping for {SLEEP_INTERVAL}s...")
                time.sleep(SLEEP_INTERVAL)
            else:
                logger.info(f"[Pipeline] Batch processed: {processed} reviews successfully indexed.")
    except KeyboardInterrupt:
        logger.info("[Pipeline] Shutdown signal received. Exiting gracefully.")
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    main()
