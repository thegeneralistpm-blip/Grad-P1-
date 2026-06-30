"""
processors/deduplicator.py
─────────────────────────────────────────────────────────────────────────────
Step 1: Deduplication
Architecture Ref: Phase 2 § 2.1

Hashes review_text with MD5 to detect and reject duplicate content.
Updates the content_hash column in raw_reviews for future lookups.
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import hashlib
from loguru import logger


def compute_content_hash(text: str) -> str:
    """
    Compute an MD5 hash of the review text for deduplication.
    Normalizes whitespace and lowercases before hashing to catch
    near-identical reviews with minor formatting differences.
    """
    normalized = " ".join(text.strip().lower().split())
    return hashlib.md5(normalized.encode("utf-8")).hexdigest()


def deduplicate(review: dict, db_conn) -> dict | None:
    """
    Check if this review's content already exists in the database.

    Args:
        review: A dict with at least 'review_id' and 'review_text'.
        db_conn: A psycopg2 connection object.

    Returns:
        The review dict with 'content_hash' added if unique.
        None if a duplicate was found.
    """
    text = review.get("review_text", "")
    if not text or not text.strip():
        logger.debug(f"[Dedup] Skipping empty review {review.get('review_id')}")
        return None

    content_hash = compute_content_hash(text)

    with db_conn.cursor() as cur:
        # Check if this hash already exists
        cur.execute(
            "SELECT review_id FROM raw_reviews WHERE content_hash = %s LIMIT 1;",
            (content_hash,)
        )
        existing = cur.fetchone()

        if existing:
            # Mark the current review as excluded
            cur.execute(
                """
                UPDATE raw_reviews
                SET processing_status = 'excluded',
                    error_message = 'Duplicate content (matches review_id: %s)',
                    content_hash = %s
                WHERE review_id = %s;
                """,
                (str(existing[0]), content_hash, review["review_id"])
            )
            db_conn.commit()
            logger.debug(
                f"[Dedup] Duplicate found: {review['review_id']} "
                f"matches existing {existing[0]}"
            )
            return None

        # Set the hash for this unique review
        cur.execute(
            "UPDATE raw_reviews SET content_hash = %s WHERE review_id = %s;",
            (content_hash, review["review_id"])
        )
        db_conn.commit()

    review["content_hash"] = content_hash
    return review
