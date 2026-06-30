"""
processors/enricher.py
─────────────────────────────────────────────────────────────────────────────
Step 5: Enrichment
Architecture Ref: Phase 2 § 2.5

Appends useful analytical metadata to the review dict:
- word_count: Length of review text.
- platform_weight: Calculated weight of the feedback based on ratings and engagement.
- review_age_days: Age of the review relative to the processing time.
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from loguru import logger


def enrich_review(review: dict) -> dict:
    """
    Enrich the review dictionary with additional analytical metrics.

    Args:
        review: A dict with fields like 'review_text', 'published_at', 'source_platform', 'upvotes', 'rating'.

    Returns:
        The enriched review dict.
    """
    text = review.get("review_text", "")
    review["word_count"] = len(text.split())

    # 1. Calculate Review Age in Days
    published_at = review.get("published_at")
    if published_at:
        try:
            # Handle string conversions or datetime objects
            if isinstance(published_at, str):
                pub_dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
            else:
                pub_dt = published_at

            # Ensure timezones match
            if pub_dt.tzinfo is None:
                pub_dt = pub_dt.replace(tzinfo=timezone.utc)
            
            now = datetime.now(timezone.utc)
            delta = now - pub_dt
            review["review_age_days"] = max(0, delta.days)
        except Exception as exc:
            logger.warning(f"[Enricher] Age calculation failed for review {review.get('review_id')}: {exc}")
            review["review_age_days"] = 0
    else:
        review["review_age_days"] = 0

    # 2. Calculate Platform Weight (Influence/Significance score)
    # Rationale:
    # - A review with 1,000 Reddit upvotes is more significant than a review with 0 upvotes.
    # - 1-star App Store reviews indicate higher frustration, thus higher priority.
    source = review.get("source_platform", "")
    upvotes = int(review.get("upvotes") or 0)
    rating = review.get("rating")

    # Base weight by platform characteristics
    base_weight = 1.0
    engagement_factor = math.log1p(upvotes)  # log(1 + upvotes) to damp high counts

    if source in ("reddit", "youtube"):
        # Driven primarily by upvotes/likes
        platform_weight = base_weight + (engagement_factor * 1.5)
    elif source in ("app_store", "play_store"):
        # Driven by star rating (lower stars = higher urgency, except 5 stars which are praise)
        rating_factor = 1.0
        if rating is not None:
            if rating == 1:
                rating_factor = 2.0  # Critical issue
            elif rating == 2:
                rating_factor = 1.5
            elif rating == 5:
                rating_factor = 1.2  # Strong positive signal
        platform_weight = (base_weight * rating_factor) + (engagement_factor * 0.5)
    else:
        platform_weight = base_weight + (engagement_factor * 1.0)

    review["platform_weight"] = round(platform_weight, 2)
    
    logger.debug(
        f"[Enricher] Enriched {review.get('review_id')} | "
        f"words={review['word_count']} age_days={review['review_age_days']} weight={review['platform_weight']}"
    )

    return review
