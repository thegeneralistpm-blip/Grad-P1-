"""
processors/relevance_scorer.py
─────────────────────────────────────────────────────────────────────────────
Step 4: Relevance Scoring
Architecture Ref: Phase 2 § 2.4

Scores the review's relevance to music discovery & recommendation on a [0.0 - 1.0] scale.
If a generative AI API key (Gemini or OpenAI) is present, it uses LLM inference.
Otherwise, it falls back to a robust keyword-density and heuristic relevance scorer.
Threshold: ≥ 0.6 is required to proceed.
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import os
import json
import requests
from loguru import logger

# Keywords that indicate relevance to music discovery or recommendation
RELEVANCE_KEYWORDS = {
    "discover": 1.5, "recommend": 1.5, "algorithm": 2.0, "suggestion": 1.2,
    "playlist": 0.8, "weekly": 1.5, "daily": 1.0, "ai dj": 2.0, "dj": 1.0,
    "radio": 1.2, "repetitive": 1.8, "same song": 1.8, "new music": 1.5,
    "find music": 1.5, "explore": 1.2, "genre": 1.0, "shuffle": 1.2,
    "feedback loop": 2.0, "echo chamber": 2.0, "stuck": 1.2, "repeat": 1.2,
    "novelty": 2.0, "fresh": 1.0, "tired": 0.8, "loop": 1.0, "variety": 1.2
}


def _score_heuristically(text: str) -> float:
    """
    Fallback heuristic scorer based on keyword matching and weights.
    Returns a score between 0.0 and 1.0.
    """
    lower_text = text.lower()
    score = 0.0
    matched_weight = 0.0

    for word, weight in RELEVANCE_KEYWORDS.items():
        if word in lower_text:
            matched_weight += weight
            # Additional score boost for multiple occurrences of high-value words
            count = lower_text.count(word)
            score += min(count, 3) * weight * 0.1

    # Base score on total weights matched
    # Normalizing so that matching 2 strong keywords gets a score of ~0.6+
    normalized_base = min(matched_weight / 3.5, 0.9)
    final_score = min(normalized_base + score, 1.0)
    return round(final_score, 2)


def _score_via_gemini(text: str, api_key: str) -> float | None:
    """
    Call Google Gemini API (gemini-2.5-flash) to evaluate relevance.
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    
    prompt = (
        "Analyze the following user review for a music streaming app. "
        "Determine if the review is discussing music discovery, recommendation systems, "
        "algorithmic playlists (like Discover Weekly, Daily Mix, AI DJ), getting stuck in "
        "repetitive loops of the same songs, or finding new artists.\n\n"
        "Return a JSON object with a single key 'relevance_score' containing a decimal float between 0.0 and 1.0. "
        "0.0 means completely unrelated (e.g. login bugs, payment errors, audio quality, UI issues).\n"
        "1.0 means highly related (e.g. explicitly complaining or praising how the app recommends new music).\n\n"
        "Do not include markdown or backticks. Return raw JSON.\n\n"
        f"Review: \"{text}\""
    )

    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "responseMimeType": "application/json"
        }
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            result = response.json()
            text_response = result["candidates"][0]["content"]["parts"][0]["text"].strip()
            data = json.loads(text_response)
            return float(data.get("relevance_score", 0.0))
        else:
            logger.warning(f"[RelevanceScorer] Gemini API failed with status {response.status_code}: {response.text}")
    except Exception as exc:
        logger.warning(f"[RelevanceScorer] Gemini API call error: {exc}")
    
    return None


def calculate_relevance(review: dict) -> dict | None:
    """
    Evaluate if the review is relevant to music discovery & recommendation.

    Args:
        review: A dict with at least 'review_id' and 'review_text'.

    Returns:
        The review dict with 'relevance_score' added if score ≥ 0.6.
        None if excluded (score < 0.6).
    """
    text = review.get("review_text", "")
    gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("YOUTUBE_API_KEY") # Sometimes they use the same Google API Key
    
    score = None
    
    # Try LLM first if key is available
    if gemini_key and not gemini_key.startswith("your_") and not gemini_key.startswith("GOCSPX"):
        logger.debug(f"[RelevanceScorer] Using Gemini API for review {review.get('review_id')}")
        score = _score_via_gemini(text, gemini_key)

    # Fallback to heuristic
    if score is None:
        logger.debug(f"[RelevanceScorer] Using heuristic scorer for review {review.get('review_id')}")
        score = _score_heuristically(text)

    review["relevance_score"] = score
    logger.debug(f"[RelevanceScorer] Review {review.get('review_id')} scored {score}")

    if score < 0.6:
        logger.debug(f"[RelevanceScorer] Review {review.get('review_id')} excluded (score {score} < 0.6)")
        return None

    return review
