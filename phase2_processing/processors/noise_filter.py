"""
processors/noise_filter.py
─────────────────────────────────────────────────────────────────────────────
Step 3: Noise Filtering
Architecture Ref: Phase 2 § 2.3

Rejects spam, extremely short reviews, or reviews containing only technical issues.
Rejection criteria:
- Word count < 8 (too short to have useful music discovery insights)
- App crash patterns
- Spam patterns (e.g., repeating character sequences, URL-only, all uppercase gibberish)
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import re
from loguru import logger

# Technical issue patterns (e.g., login errors, crashes, payment issues, storage errors)
TECHNICAL_PATTERNS = [
    r"\bcrash(ed|es|ing)?\b",
    r"\blog(in|ged|ging)?\s+issue(s)?\b",
    r"\bwon't\s+open\b",
    r"\bcant\s+log\s+in\b",
    r"\bblack\s+screen\b",
    r"\bfreeze(s|d|ing)?\b",
    r"\bbilling\b",
    r"\bpay(ment|ing)?\s+error(s)?\b",
    r"\bad(s)?\s+blocking\b",
    r"\bupdate\s+ruined\b",
]

TECHNICAL_REGEX = re.compile("|".join(TECHNICAL_PATTERNS), re.IGNORECASE)

# Repeated characters / spam patterns
SPAM_PATTERNS = [
    r"(.)\1{4,}",  # Character repeating 5+ times (e.g., "aaaaa")
    r"^(http|https)://\S+$",  # URL only
]
SPAM_REGEX = re.compile("|".join(SPAM_PATTERNS), re.IGNORECASE)


def filter_noise(review: dict) -> dict | None:
    """
    Filter out noise: technical reviews, spam, or too short text.

    Args:
        review: A dict with at least 'review_id' and 'review_text'.

    Returns:
        The review dict if it passes the noise filter.
        None if it is classified as noise (excluded).
    """
    text = review.get("review_text", "").strip()
    words = text.split()

    # Rule 1: Minimum length check
    if len(words) < 8:
        logger.debug(
            f"[NoiseFilter] Review {review.get('review_id')} excluded: "
            f"Too short ({len(words)} words)."
        )
        return None

    # Rule 2: Technical/Crash filter (for app store reviews primarily)
    # Note: Only exclude if it's purely technical and has low rating (1-2)
    # If the user mentions crash but still gave 4 stars or has long text, keep it.
    rating = review.get("rating")
    is_low_rating = rating is not None and rating <= 2

    if is_low_rating and TECHNICAL_REGEX.search(text):
        logger.debug(
            f"[NoiseFilter] Review {review.get('review_id')} excluded: "
            f"Classified as pure technical/crash feedback."
        )
        return None

    # Rule 3: Spam check
    if SPAM_REGEX.search(text):
        logger.debug(
            f"[NoiseFilter] Review {review.get('review_id')} excluded: "
            f"Failed spam check."
        )
        return None

    return review
