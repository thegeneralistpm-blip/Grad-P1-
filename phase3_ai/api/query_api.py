"""
api/query_api.py
─────────────────────────────────────────────────────────────────────────────
FastAPI HTTP Endpoint for Phase 3 AI RAG Query Engine
Exposes POST /query to receive PM natural language questions and return
citation-grounded answers.
─────────────────────────────────────────────────────────────────────────────
"""

import os
import sys
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "rag")))
from synthesizer import answer_query

app = FastAPI(
    title="Spotify Review Discovery Engine - AI Query API",
    version="1.0.0",
    description="Natural language Q&A interface powered by RAG and Gemini Pro."
)

class QueryRequest(BaseModel):
    question: str

class CitedSource(BaseModel):
    review_id: str
    platform: str
    url: str | None = None
    quote: str

class QueryResponse(BaseModel):
    answer: str
    is_grounded: bool
    cited_sources: list[CitedSource]

@app.post("/query", response_model=QueryResponse)
def query_reviews(req: QueryRequest):
    """Ask a natural language question about user reviews."""
    if not req.question or len(req.question.strip()) < 3:
        raise HTTPException(status_code=400, detail="Question too short.")
        
    res = answer_query(req.question)
    return res

@app.get("/health")
def health_check():
    return {"status": "ok", "layer": "Phase 3 AI Intelligence"}
