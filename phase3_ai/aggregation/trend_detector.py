"""
aggregation/trend_detector.py
─────────────────────────────────────────────────────────────────────────────
Trend & Alert Detector
Monitors review insights for rising themes, emerging unmet needs,
and high urgency alerts requiring Jira ticket drafts.
─────────────────────────────────────────────────────────────────────────────
"""

import os
import sqlite3
import json

DB_PATH = "live_reviews.db"

def detect_trends():
    if not os.path.exists(DB_PATH):
        return {}
        
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Check high urgency reviews
    cur.execute(
        """
        SELECT r.review_id, r.source_platform, r.review_text, i.themes, i.urgency_score, i.key_quote
        FROM review_insights i
        JOIN raw_reviews r ON i.review_id = r.review_id
        WHERE i.urgency_score >= 4.0;
        """
    )
    high_urgency = [dict(row) for row in cur.fetchall()]
    
    # Check unmet needs
    cur.execute(
        """
        SELECT r.source_platform, i.unmet_need, i.urgency_score
        FROM review_insights i
        JOIN raw_reviews r ON i.review_id = r.review_id
        WHERE i.unmet_need IS NOT NULL AND i.unmet_need != 'null' AND i.unmet_need != '';
        """
    )
    unmet_needs = [dict(row) for row in cur.fetchall()]
    
    conn.close()
    
    print("======================================================")
    print("           EMERGING TRENDS & ALERTS REPORT")
    print("======================================================")
    print(f"[*] High Urgency Alerts Detected (Score >= 4.0): {len(high_urgency)}")
    for item in high_urgency[:3]:
        print(f"    [!] [{item['source_platform'].upper()}] Urgency {item['urgency_score']}: \"{item['key_quote'][:70]}...\"")
        
    print(f"\n[*] Extracted Unmet Needs / Feature Requests: {len(unmet_needs)}")
    for item in unmet_needs[:3]:
        print(f"    [*] \"{item['unmet_need']}\"")
    print("======================================================")
    
    return {"high_urgency_count": len(high_urgency), "unmet_needs_count": len(unmet_needs)}

if __name__ == "__main__":
    detect_trends()
