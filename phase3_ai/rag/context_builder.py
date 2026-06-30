"""
rag/context_builder.py
─────────────────────────────────────────────────────────────────────────────
Context Builder for RAG
Formats retrieved reviews and summary stats into a clean LLM context block.
─────────────────────────────────────────────────────────────────────────────
"""

import json

def build_context(query: str, retrieved_reviews: list[dict]) -> str:
    """Format retrieved reviews into a structured prompt context."""
    if not retrieved_reviews:
        return "No relevant reviews found matching the query."
        
    context_lines = [f"User Query: \"{query}\"\n", "--- RETRIEVED USER REVIEWS ---"]
    
    for idx, r in enumerate(retrieved_reviews, 1):
        rid = r.get("review_id")
        plat = r.get("source_platform", "unknown").upper()
        upv = r.get("upvotes", 0)
        urg = r.get("urgency_score", 3.0)
        text = r.get("review_text", "").replace("\n", " ")
        themes = r.get("themes", "[]")
        
        line = f"[{idx}] (ID: {rid} | Platform: {plat} | Upvotes: {upv} | Urgency: {urg}/5.0 | Themes: {themes})\nText: \"{text}\"\n"
        context_lines.append(line)
        
    return "\n".join(context_lines)
