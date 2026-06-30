"""
api/main.py
─────────────────────────────────────────────────────────────────────────────
Delivery Layer FastAPI Backend Server
Serves static frontend files and routes API calls for:
- RAG user review querying
- Weekly summary report
- Slack & Email integration previews
- Auto-drafted Jira ticket approvals
─────────────────────────────────────────────────────────────────────────────
"""

import os
import sys
import json
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

# Append parent and Phase 3 directories to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "phase3_ai", "rag")))

from phase3_ai.rag.synthesizer import answer_query

app = FastAPI(
    title="Spotify Review Discovery Engine - PM Dashboard API",
    version="1.0.0"
)

# API Schemas
class QueryRequest(BaseModel):
    question: str

class JiraActionRequest(BaseModel):
    ticket_id: str

@app.post("/api/query")
def api_query_engine(req: QueryRequest):
    """Answer PM Q&A query using RAG and citations."""
    if not req.question or len(req.question.strip()) < 3:
        raise HTTPException(status_code=400, detail="Query too short.")
    try:
        res = answer_query(req.question)
        return res
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.get("/api/digest")
def get_weekly_digest():
    """Fetch the compiled weekly summary digest."""
    path = "weekly_digest.json"
    if not os.path.exists(path):
        # Trigger generation if missing
        try:
            from phase4_delivery.digest.weekly_digest import generate_weekly_digest
            generate_weekly_digest()
        except Exception:
            pass
            
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Weekly digest not found. Run compiler first.")
        
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

@app.get("/api/slack-preview")
def get_slack_payload():
    """Fetch the compiled Slack block preview payload."""
    path = "slack_payload.json"
    if not os.path.exists(path):
        try:
            from phase4_delivery.integrations.slack_bot import generate_slack_digest
            generate_slack_digest()
        except Exception:
            pass
            
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Slack payload not found.")
        
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

@app.get("/api/email-preview", response_class=HTMLResponse)
def get_email_preview():
    """Fetch the HTML email formatted preview template."""
    path = "weekly_email_preview.html"
    if not os.path.exists(path):
        try:
            from phase4_delivery.integrations.email_sender import generate_email_preview
            generate_email_preview()
        except Exception:
            pass
            
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Email preview template not found.")
        
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

@app.get("/api/jira-tickets")
def get_jira_drafts():
    """Fetch the auto-drafted Jira backlog tickets."""
    path = "jira_drafts.json"
    if not os.path.exists(path):
        try:
            from phase4_delivery.integrations.jira_drafter import draft_jira_tickets
            draft_jira_tickets(min_urgency=3.0, min_mentions=2)
        except Exception:
            pass
            
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Jira drafts not found.")
        
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

@app.post("/api/jira-tickets/create")
def push_jira_ticket(req: JiraActionRequest):
    """Simulate pushing the approved Jira ticket to production backlog."""
    path = "jira_drafts.json"
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Jira drafts not found.")
        
    with open(path, "r", encoding="utf-8") as f:
        drafts = json.load(f)
        
    found = False
    for d in drafts:
        if d["ticket_id"] == req.ticket_id:
            d["status"] = "SUBMITTED"
            d["pushed_at"] = os.popen('date').read().strip() or "now"
            found = True
            break
            
    if not found:
        raise HTTPException(status_code=404, detail=f"Ticket ID {req.ticket_id} not found in drafts.")
        
    with open(path, "w", encoding="utf-8") as f:
        json.dump(drafts, f, indent=2)
        
    return {"status": "success", "ticket_id": req.ticket_id, "message": "Ticket successfully submitted to Jira backlog!"}

@app.get("/health")
def health_check():
    return {"status": "ok", "layer": "Phase 4 Delivery API"}

# Mount frontend files at /
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
else:
    print(f"[!] Warning: Frontend directory '{frontend_dir}' not found. UI files should be written here.")
