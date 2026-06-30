"""
rag/synthesizer.py
─────────────────────────────────────────────────────────────────────────────
RAG Synthesizer
Takes a natural language PM query, retrieves relevant reviews, prompts Gemini
to synthesize an executive answer with citations, and validates grounding.
─────────────────────────────────────────────────────────────────────────────
"""

import os
import requests
import json
from query_engine import search_reviews
from context_builder import build_context
from citation_checker import validate_citations

def _synthesize_heuristically(query: str, reviews: list[dict]) -> str:
    """Fallback synthesis when LLM API is unavailable."""
    if not reviews:
        return "No feedback found matching your query."
        
    top = reviews[0]
    return (
        f"Based on {len(reviews)} retrieved reviews, users frequently discuss this topic. "
        f"For example, a review on {top.get('source_platform')} (ID: {top.get('review_id')}) stated: "
        f"\"{top.get('review_text')[:150]}...\". The average urgency around this feedback is "
        f"{round(sum(float(r.get('urgency_score') or 3) for r in reviews)/len(reviews), 1)}/5.0."
    )

def answer_query(query: str) -> dict:
    """Answer a PM natural language query using RAG."""
    reviews = search_reviews(query, top_k=8)
    context = build_context(query, reviews)
    
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("YOUTUBE_API_KEY")
    if not api_key or api_key.startswith("your_") or api_key.startswith("GOCSPX"):
        ans = _synthesize_heuristically(query, reviews)
        return validate_citations(ans, reviews)
        
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    
    prompt = f"""You are an AI Product Intelligence Assistant answering a PM query based strictly on retrieved user feedback.
{context}

Instructions:
1. Provide a direct, actionable answer summarizing the user sentiment and top themes.
2. Cite specific review IDs in parentheses, e.g. (ID: playstore_123).
3. Mention the average urgency score if relevant.

Answer:"""

    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        if resp.status_code == 200:
            ans = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            return validate_citations(ans, reviews)
    except Exception:
        pass
        
    ans = _synthesize_heuristically(query, reviews)
    return validate_citations(ans, reviews)

if __name__ == "__main__":
    # Test execution
    res = answer_query("Why are users frustrated with AI DJ and repeating songs?")
    print("\n======================================================")
    print("                 RAG QUERY RESPONSE")
    print("======================================================")
    print(res["answer"])
    print("\nCited Sources:")
    for c in res["cited_sources"]:
        print(f"  - [{c['platform']}] {c['review_id']}: \"{c['quote'][:60]}...\"")
    print("======================================================")
