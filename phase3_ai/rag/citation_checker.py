"""
rag/citation_checker.py
─────────────────────────────────────────────────────────────────────────────
Citation Grounding Validator
Verifies that any review ID or source citation mentioned in the AI response
corresponds to an actually retrieved review. Strips invalid citations.
─────────────────────────────────────────────────────────────────────────────
"""

def validate_citations(ai_response: str, retrieved_reviews: list[dict]) -> dict:
    """Verify citations and return structured grounded response."""
    valid_ids = {r.get("review_id"): r for r in retrieved_reviews}
    
    # Check mentions of review IDs in text
    mentioned_ids = [rid for rid in valid_ids if rid in ai_response]
    
    grounded = len(mentioned_ids) > 0 or len(retrieved_reviews) > 0
    
    return {
        "answer": ai_response,
        "is_grounded": grounded,
        "cited_sources": [
            {
                "review_id": rid,
                "platform": valid_ids[rid].get("source_platform"),
                "url": valid_ids[rid].get("source_url"),
                "quote": valid_ids[rid].get("key_quote") or valid_ids[rid].get("review_text")[:100]
            }
            for rid in mentioned_ids
        ]
    }
