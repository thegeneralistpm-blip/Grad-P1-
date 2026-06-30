"""
processors/language_detector.py
─────────────────────────────────────────────────────────────────────────────
Step 2: Language Detection
Architecture Ref: Phase 2 § 2.2

Detects the language of each review using the `langdetect` library.
English reviews proceed; non-English reviews are tagged and excluded
from v1.0 processing (routed to a future multilingual queue in v2.0).
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

from langdetect import detect, DetectorFactory, LangDetectException
from loguru import logger

# Make langdetect deterministic (same text → same result every time)
DetectorFactory.seed = 42

# Languages supported in v1.0
SUPPORTED_LANGUAGES = {"en"}

# Minimum text length for reliable detection
MIN_DETECTION_LENGTH = 20


def detect_language(review: dict) -> dict | None:
    """
    Detect the language of the review text.

    Args:
        review: A dict with at least 'review_id' and 'review_text'.

    Returns:
        The review dict with 'detected_language' added if English.
        None if non-English (excluded from v1.0 pipeline).
    """
    text = review.get("review_text", "")

    # Very short texts are unreliable for detection — assume English
    if len(text.strip()) < MIN_DETECTION_LENGTH:
        review["detected_language"] = "en"
        return review

    try:
        lang = detect(text)
    except LangDetectException:
        # If detection fails entirely, let it through (assume English)
        logger.warning(
            f"[LangDetect] Could not detect language for review "
            f"{review.get('review_id')}. Defaulting to 'en'."
        )
        review["detected_language"] = "en"
        return review

    review["detected_language"] = lang

    if lang not in SUPPORTED_LANGUAGES:
        logger.debug(
            f"[LangDetect] Non-English review detected: lang='{lang}' | "
            f"review_id={review.get('review_id')} | Excluding from v1.0."
        )
        return None

    return review
