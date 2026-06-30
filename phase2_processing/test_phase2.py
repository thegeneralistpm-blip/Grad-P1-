"""
test_phase2.py
─────────────────────────────────────────────────────────────────────────────
Phase 2 Test Suite
This script creates a local mock SQLite database, seeds it with various
types of reviews (duplicates, non-English, spam, irrelevant, and highly
relevant music discovery complaints), runs them through the Phase 2 pipeline,
and prints a detailed visual report of the outcomes.
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import os
import sys
import sqlite3
import json
from datetime import datetime, timezone
from loguru import logger

# Add paths to imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from processors.deduplicator import compute_content_hash
from processors.language_detector import detect_language
from processors.noise_filter import filter_noise
from processors.relevance_scorer import calculate_relevance
from processors.enricher import enrich_review
from processors.embedder import generate_embedding

# Mock database file
MOCK_DB_FILE = "mock_reviews.db"

# ── Mock Data ──────────────────────────────────────────────────────────────
MOCK_REVIEWS = [
    {
        "review_id": "r1-valid-complaint",
        "source_platform": "reddit",
        "review_text": "Discover weekly has been repeating the same 5 songs for the last 3 weeks. The algorithm is stuck in a feedback loop and I am tired of hearing the same content over and over.",
        "upvotes": 150,
        "rating": None,
        "published_at": (datetime.now(tz=timezone.utc)).isoformat()
    },
    {
        "review_id": "r2-duplicate",
        "source_platform": "reddit",
        "review_text": "Discover weekly has been repeating the same 5 songs for the last 3 weeks. The algorithm is stuck in a feedback loop and I am tired of hearing the same content over and over.",
        "upvotes": 2,
        "rating": None,
        "published_at": (datetime.now(tz=timezone.utc)).isoformat()
    },
    {
        "review_id": "r3-spanish",
        "source_platform": "app_store",
        "review_text": "Me encanta esta aplicación para escuchar música todo el día. Muy recomendada para todos mis amigos y familia.",
        "upvotes": 0,
        "rating": 5,
        "published_at": (datetime.now(tz=timezone.utc)).isoformat()
    },
    {
        "review_id": "r4-too-short",
        "source_platform": "play_store",
        "review_text": "Great app!",
        "upvotes": 0,
        "rating": 5,
        "published_at": (datetime.now(tz=timezone.utc)).isoformat()
    },
    {
        "review_id": "r5-technical-crash",
        "source_platform": "app_store",
        "review_text": "The app keeps freezing and crashing on launch since the last update. Please fix this bug immediately.",
        "upvotes": 10,
        "rating": 1,
        "published_at": (datetime.now(tz=timezone.utc)).isoformat()
    },
    {
        "review_id": "r6-irrelevant-but-long",
        "source_platform": "reddit",
        "review_text": "I really think Spotify needs to redesign their UI. The local files section is hard to find, and managing offline downloads on my SD card is a huge headache. They should focus on clean design.",
        "upvotes": 45,
        "rating": None,
        "published_at": (datetime.now(tz=timezone.utc)).isoformat()
    },
    {
        "review_id": "r7-high-value-ai-dj",
        "source_platform": "play_store",
        "review_text": "The AI DJ feature is so repetitive. It plays the same three artists every time I start it. I skip them but the recommendations don't adapt. We need a novelty slider to control how much new music is played.",
        "upvotes": 25,
        "rating": 2,
        "published_at": (datetime.now(tz=timezone.utc)).isoformat()
    }
]


def setup_mock_db():
    """Create and seed the mock SQLite database."""
    if os.path.exists(MOCK_DB_FILE):
        os.remove(MOCK_DB_FILE)

    conn = sqlite3.connect(MOCK_DB_FILE)
    cur = conn.cursor()

    # Create simplified raw_reviews table matching postgres
    cur.execute(
        """
        CREATE TABLE raw_reviews (
            review_id TEXT PRIMARY KEY,
            source_platform TEXT,
            review_text TEXT,
            upvotes INTEGER,
            rating INTEGER,
            published_at TEXT,
            processing_status TEXT DEFAULT 'pending',
            content_hash TEXT,
            error_message TEXT
        );
        """
    )

    # Create fallback vector embeddings table
    cur.execute(
        """
        CREATE TABLE raw_reviews_embeddings (
            review_id TEXT PRIMARY KEY,
            embedding TEXT,
            dimensions INTEGER,
            metadata TEXT
        );
        """
    )

    # Seed data
    for r in MOCK_REVIEWS:
        cur.execute(
            """
            INSERT INTO raw_reviews (review_id, source_platform, review_text, upvotes, rating, published_at)
            VALUES (?, ?, ?, ?, ?, ?);
            """,
            (r["review_id"], r["source_platform"], r["review_text"], r["upvotes"], r["rating"], r["published_at"])
        )

    conn.commit()
    conn.close()
    logger.info(f"[Test] Seeded mock database '{MOCK_DB_FILE}' with {len(MOCK_REVIEWS)} reviews.")


def run_pipeline():
    """Run the seeded data through the Phase 2 processors."""
    conn = sqlite3.connect(MOCK_DB_FILE)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT * FROM raw_reviews WHERE processing_status = 'pending';")
    rows = cur.fetchall()

    logger.info(f"[Test] Starting processing loop for {len(rows)} pending reviews...")

    # We simulate deduplicator local cache to test deduplication step in SQLite
    seen_hashes = {}

    for row in rows:
        review = dict(row)
        review_id = review["review_id"]
        text = review["review_text"]

        logger.info(f"\n--- Processing Review: {review_id} ---")
        logger.info(f"Text: \"{text[:90]}...\"")

        try:
            # 1. Deduplicate
            content_hash = compute_content_hash(text)
            if content_hash in seen_hashes:
                logger.warning(f"❌ Duplicate detected (matches {seen_hashes[content_hash]})")
                cur.execute(
                    "UPDATE raw_reviews SET processing_status = 'excluded', error_message = 'Duplicate content', content_hash = ? WHERE review_id = ?;",
                    (content_hash, review_id)
                )
                conn.commit()
                continue
            
            seen_hashes[content_hash] = review_id
            review["content_hash"] = content_hash
            cur.execute("UPDATE raw_reviews SET content_hash = ? WHERE review_id = ?;", (content_hash, review_id))
            conn.commit()
            logger.info("✅ Step 1 (Dedup): Unique content verified.")

            # 2. Language Detection
            lang_check = detect_language(review)
            if not lang_check:
                logger.warning("❌ Step 2 (Language): Excluded (Non-English).")
                cur.execute(
                    "UPDATE raw_reviews SET processing_status = 'excluded', error_message = 'Non-English language' WHERE review_id = ?;",
                    (review_id,)
                )
                conn.commit()
                continue
            logger.info("✅ Step 2 (Language): English language verified.")

            # 3. Noise Filter
            noise_check = filter_noise(review)
            if not noise_check:
                logger.warning("❌ Step 3 (Noise): Excluded (Spam/Crash/Too Short).")
                cur.execute(
                    "UPDATE raw_reviews SET processing_status = 'excluded', error_message = 'Classified as noise' WHERE review_id = ?;",
                    (review_id,)
                )
                conn.commit()
                continue
            logger.info("✅ Step 3 (Noise): Review meets quality criteria.")

            # 4. Relevance Scorer
            relevance_check = calculate_relevance(review)
            if not relevance_check:
                logger.warning(f"❌ Step 4 (Relevance): Excluded (Relevance score {review['relevance_score']} < 0.6).")
                cur.execute(
                    "UPDATE raw_reviews SET processing_status = 'excluded', error_message = 'Low relevance' WHERE review_id = ?;",
                    (review_id,)
                )
                conn.commit()
                continue
            logger.info(f"✅ Step 4 (Relevance): Relevance verified (Score: {review['relevance_score']}).")

            # 5. Enrichment
            enriched = enrich_review(review)
            logger.info(
                f"✅ Step 5 (Enrichment): Added metadata. "
                f"Word count: {enriched['word_count']}, Platform weight: {enriched['platform_weight']}, Age: {enriched['review_age_days']} days."
            )

            # 6. Embedding Generation
            embedding, dims = generate_embedding(text)
            logger.info(f"✅ Step 6 (Embedding): Generated embedding ({dims} dimensions). Vector sample: {embedding[:3]}...")

            # 7. Index in local mock table
            metadata_str = json.dumps({
                "review_id": review_id,
                "source_platform": enriched["source_platform"],
                "rating": enriched["rating"],
                "upvotes": enriched["upvotes"],
                "word_count": enriched["word_count"],
                "platform_weight": enriched["platform_weight"],
                "review_text": text
            })
            
            cur.execute(
                "INSERT OR REPLACE INTO raw_reviews_embeddings (review_id, embedding, dimensions, metadata) VALUES (?, ?, ?, ?);",
                (review_id, json.dumps(embedding), dims, metadata_str)
            )
            
            # Set to processed
            cur.execute("UPDATE raw_reviews SET processing_status = 'processed' WHERE review_id = ?;", (review_id,))
            conn.commit()
            logger.info("✅ Step 7 (Indexing): Successfully stored in vector fallback database.")

        except Exception as exc:
            logger.error(f"💥 Failed processing {review_id}: {exc}")
            cur.execute("UPDATE raw_reviews SET processing_status = 'failed', error_message = ? WHERE review_id = ?;", (str(exc), review_id))
            conn.commit()

    conn.close()


def print_results():
    """Print the final states of all processed reviews."""
    conn = sqlite3.connect(MOCK_DB_FILE)
    cur = conn.cursor()

    cur.execute("SELECT review_id, processing_status, error_message FROM raw_reviews;")
    reviews = cur.fetchall()

    cur.execute("SELECT COUNT(*) FROM raw_reviews_embeddings;")
    embeddings_count = cur.fetchone()[0]

    print("\n" + "="*60)
    print("                PHASE 2 PIPELINE TEST RESULTS")
    print("="*60)
    print(f"Total reviews in DB: {len(reviews)}")
    print(f"Indexed embeddings in DB: {embeddings_count}\n")
    
    print(f"{'Review ID':<25} | {'Status':<12} | {'Reason / Error Message':<30}")
    print("-" * 75)
    for rid, status, err in reviews:
        err_msg = err if err else "Passed Successfully"
        print(f"{rid:<25} | {status:<12} | {err_msg:<30}")
    print("="*60)

    conn.close()


if __name__ == "__main__":
    setup_mock_db()
    run_pipeline()
    print_results()
