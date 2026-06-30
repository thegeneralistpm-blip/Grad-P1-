"""
rag/query_engine.py
─────────────────────────────────────────────────────────────────────────────
Retrieval Engine
Searches local SQLite reviews for text matching the query keywords.
Returns top K relevant reviews along with their extracted AI insights.
─────────────────────────────────────────────────────────────────────────────
"""

import os
import sqlite3
import json

DB_PATH = "live_reviews.db"

def search_reviews(query: str, top_k: int = 10) -> list[dict]:
    """Search stored reviews matching query keywords or themes."""
    if not os.path.exists(DB_PATH):
        return []
        
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    keywords = [w.lower() for w in query.split() if len(w) > 3]
    
    cur.execute(
        """
        SELECT r.review_id, r.source_platform, r.source_url, r.review_text, r.upvotes, r.rating,
               i.themes, i.urgency_score, i.sentiment, i.key_quote, i.unmet_need
        FROM raw_reviews r
        LEFT JOIN review_insights i ON r.review_id = i.review_id;
        """
    )
    rows = cur.fetchall()
    conn.close()
    
    scored = []
    for row in rows:
        item = dict(row)
        text_lower = (item.get("review_text") or "").lower()
        themes_lower = (item.get("themes") or "").lower()
        
        score = 0
        for kw in keywords:
            if kw in text_lower:
                score += 2
            if kw in themes_lower:
                score += 3
                
        # Give base score if urgency is high or matches general terms
        if score > 0 or not keywords:
            item["match_score"] = score + (float(item.get("urgency_score") or 0) * 0.5)
            scored.append(item)
            
    scored.sort(key=lambda x: x.get("match_score", 0), reverse=True)
    return scored[:top_k]
