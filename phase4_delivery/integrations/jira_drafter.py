"""
integrations/jira_drafter.py
─────────────────────────────────────────────────────────────────────────────
Jira Auto-Ticket Drafter
Identifies high-urgency user complaints (urgency >= 4.0) and volume spikes,
generating draft Jira tickets in the Growth Backlog. Saves to `jira_drafts.json`.
─────────────────────────────────────────────────────────────────────────────
"""

import os
import sqlite3
import json
from datetime import datetime, timezone

DB_PATH = "live_reviews.db"
OUTPUT_DRAFTS_PATH = "jira_drafts.json"

def draft_jira_tickets(min_urgency=4.0, min_mentions=2):
    """Scan database for qualifying complaints and output Jira ticket drafts."""
    if not os.path.exists(DB_PATH):
        print(f"[-] Database {DB_PATH} not found.")
        return []

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Query all processed insights
    cur.execute(
        """
        SELECT r.review_id, r.source_platform, r.review_text, i.themes, i.urgency_score, i.key_quote, i.unmet_need
        FROM review_insights i
        JOIN raw_reviews r ON i.review_id = r.review_id;
        """
    )
    rows = cur.fetchall()
    conn.close()

    # Group by theme
    theme_data = {}
    for row in rows:
        try:
            themes = json.loads(row["themes"] or "[]")
        except Exception:
            continue

        for theme in themes:
            if theme not in theme_data:
                theme_data[theme] = {
                    "mentions": 0,
                    "total_urgency": 0.0,
                    "quotes": [],
                    "unmet_needs": []
                }
            td = theme_data[theme]
            td["mentions"] += 1
            td["total_urgency"] += float(row["urgency_score"] or 3.0)
            if row["key_quote"]:
                td["quotes"].append(row["key_quote"])
            if row["unmet_need"]:
                td["unmet_needs"].append(row["unmet_need"])

    drafts = []
    for theme, data in theme_data.items():
        avg_urgency = data["total_urgency"] / data["mentions"]
        
        # Check thresholds
        if avg_urgency >= min_urgency and data["mentions"] >= min_mentions:
            rep_quote = data["quotes"][0] if data["quotes"] else "N/A"
            unmet = data["unmet_needs"][0] if data["unmet_needs"] else "Better user experience control."
            
            priority = "Critical" if avg_urgency >= 4.5 else "High"
            
            draft = {
                "ticket_id": f"GROWTH-{len(drafts) + 101}",
                "summary": f"[AI Engine] High urgency: {theme}",
                "description": (
                    f"The Spotify Review Discovery Engine detected a high-urgency issue regarding '{theme}'.\n\n"
                    f"• Mentions in last 7 days: {data['mentions']}\n"
                    f"• Average Urgency: {round(avg_urgency, 2)} / 5.0\n"
                    f"• Primary Unmet Need: {unmet}\n"
                    f"• Representative User Quote: \"{rep_quote}\"\n\n"
                    f"Please investigate algorithms and weights associated with this theme."
                ),
                "labels": ["user-sentiment", "discovery-engine", "auto-generated"],
                "priority": priority,
                "reporter": "Review Discovery Engine Bot",
                "status": "DRAFT",
                "theme": theme,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            drafts.append(draft)

    # Write drafts to JSON
    with open(OUTPUT_DRAFTS_PATH, "w", encoding="utf-8") as f:
        json.dump(drafts, f, indent=2)

    print("======================================================")
    print(f"[*] Jira Auto-Ticket Drafter Complete")
    print(f"[*] Scanned database, created {len(drafts)} draft ticket(s)")
    print(f"[*] Drafts exported to: {OUTPUT_DRAFTS_PATH}")
    print("======================================================")
    return drafts

if __name__ == "__main__":
    draft_jira_tickets(min_urgency=3.0, min_mentions=2)
