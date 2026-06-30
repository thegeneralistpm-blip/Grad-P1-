"""
extractors/theme_extractor.py
─────────────────────────────────────────────────────────────────────────────
Theme Extraction Service
Calls Google Gemini API to extract structured themes, sentiment, urgency, and quotes.
Includes a robust heuristic fallback extractor for zero-dependency local execution.
─────────────────────────────────────────────────────────────────────────────
"""

import os
import json
import requests

def _extract_heuristically(review: dict) -> dict:
    """Fallback rule-based extraction when LLM API is unavailable."""
    text = review.get("review_text", "").lower()
    rating = review.get("rating")
    
    themes = []
    if "repeat" in text or "same song" in text or "repetitive" in text:
        themes.append("Algorithm Repetitiveness")
    if "ai dj" in text or "dj" in text:
        themes.append("AI DJ Commentary / Repetitiveness")
    if "shuffle" in text:
        themes.append("Smart Shuffle Issues")
    if "skip" in text:
        themes.append("Explicit Skip Ignored")
    if "apple music" in text or "youtube music" in text or "tiktok" in text:
        themes.append("Competitive Signals")
    if not themes:
        themes.append("Discover Weekly / Release Radar Quality")
        
    # Sentiment & Urgency
    if rating is not None and rating <= 2:
        sentiment = "Negative" if rating == 2 else "Critical"
        urgency = 4.2 if rating == 2 else 4.8
    elif rating == 3:
        sentiment = "Neutral"
        urgency = 2.5
    else:
        sentiment = "Negative" if any(w in text for w in ["annoying", "hate", "broken", "worst", "tired"]) else "Positive"
        urgency = 3.8 if sentiment == "Negative" else 1.5
        
    return {
        "themes": themes,
        "sentiment": sentiment,
        "urgency_score": round(urgency, 1),
        "user_segment": "Power Listener" if len(text.split()) > 30 else "Casual User",
        "key_quote": review.get("review_text", "")[:120] + ("..." if len(review.get("review_text", "")) > 120 else ""),
        "unmet_need": "Better control over algorithm repetition and shuffle variety." if urgency >= 3.5 else None
    }

def extract_insights(review: dict) -> dict:
    """Extract qualitative insights from a review using Gemini API or heuristic fallback."""
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("YOUTUBE_API_KEY")
    if not api_key or api_key.startswith("your_") or api_key.startswith("GOCSPX"):
        return _extract_heuristically(review)
        
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    
    prompt = f"""Analyze this Spotify review and extract JSON with keys: themes (list of strings), sentiment (string), urgency_score (float 1.0-5.0), user_segment (string), key_quote (string), unmet_need (string or null).
Review Text: "{review.get('review_text')}"
Platform: {review.get('source_platform')}"""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"}
    }
    
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        if resp.status_code == 200:
            res_text = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            return json.loads(res_text)
    except Exception:
        pass
        
    return _extract_heuristically(review)
