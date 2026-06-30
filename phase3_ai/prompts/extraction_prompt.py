"""
prompts/extraction_prompt.py
─────────────────────────────────────────────────────────────────────────────
LLM Prompt Templates for Phase 3A Thematic Extraction
─────────────────────────────────────────────────────────────────────────────
"""

SYSTEM_PROMPT = """You are an expert AI Product Analyst for the Spotify Growth Team.
Your job is to analyze qualitative user reviews and extract structured product insights.

You must follow the provided Theme Taxonomy strictly. Do NOT hallucinate new primary themes unless it represents a completely novel Unmet Need.

Output valid JSON matching the exact schema requested."""

USER_PROMPT_TEMPLATE = """Analyze the following user review for Spotify:

Platform: {platform}
Rating: {rating}
Upvotes/Likes: {upvotes}
Review Text: "{review_text}"

Extract the following fields in strict JSON format:
1. "themes": Array of matching leaf themes from the taxonomy (e.g. ["Algorithm Repetitiveness", "Explicit Skip Ignored"]).
2. "sentiment": String ("Positive", "Neutral", "Negative", "Critical").
3. "urgency_score": Float between 1.0 (low priority praise/nitpick) and 5.0 (critical core feature failure or churn risk).
4. "user_segment": String inferred from context (e.g. "Power Listener", "Casual User", "Commuter", "Playlist Creator", "Unknown").
5. "key_quote": Exact verbatim quote from the text that best illustrates the main feedback.
6. "unmet_need": Brief 1-sentence description of any underlying unmet need or requested feature (or null).

Return ONLY raw valid JSON without markdown wrapping or code blocks."""
