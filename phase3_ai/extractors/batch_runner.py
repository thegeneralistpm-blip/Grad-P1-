"""
extractors/batch_runner.py
─────────────────────────────────────────────────────────────────────────────
Batch Extraction Runner
Reads raw reviews from local database, extracts qualitative insights,
and stores structured theme analysis in `review_insights` table.
─────────────────────────────────────────────────────────────────────────────
"""

import os
import sys
import sqlite3
import json
from datetime import datetime, timezone

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from theme_extractor import extract_insights

DB_PATH = "live_reviews.db"

def init_insights_table(conn):
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS review_insights (
            review_id TEXT PRIMARY KEY,
            themes TEXT,
            sentiment TEXT,
            urgency_score REAL,
            user_segment TEXT,
            key_quote TEXT,
            unmet_need TEXT,
            extracted_at TEXT
        );
        """
    )
    conn.commit()

def run_batch_extraction():
    if not os.path.exists(DB_PATH):
        print(f"[-] Database {DB_PATH} not found. Run download_live_reviews.py first.")
        return 0
        
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    init_insights_table(conn)
    
    cur = conn.cursor()
    # Get reviews that don't have insights yet
    cur.execute(
        """
        SELECT r.* FROM raw_reviews r
        LEFT JOIN review_insights i ON r.review_id = i.review_id
        WHERE i.review_id IS NULL;
        """
    )
    rows = cur.fetchall()
    
    print(f"[*] Starting AI Theme Extraction for {len(rows)} reviews...")
    count = 0
    for row in rows:
        review = dict(row)
        rid = review["review_id"]
        try:
            insights = extract_insights(review)
            cur.execute(
                """
                INSERT OR REPLACE INTO review_insights 
                (review_id, themes, sentiment, urgency_score, user_segment, key_quote, unmet_need, extracted_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    rid,
                    json.dumps(insights.get("themes", [])),
                    insights.get("sentiment", "Neutral"),
                    float(insights.get("urgency_score", 3.0)),
                    insights.get("user_segment", "Unknown"),
                    insights.get("key_quote", ""),
                    insights.get("unmet_need"),
                    datetime.now(timezone.utc).isoformat()
                )
            )
            conn.commit()
            count += 1
            print(f"[+] Extracted insights for {rid}: {insights.get('themes')} (Urgency: {insights.get('urgency_score')})")
        except Exception as exc:
            print(f"[-] Failed extraction for {rid}: {exc}")
            
    conn.close()
    print(f"\n[*] Batch extraction complete! Processed {count} reviews.")
    return count

if __name__ == "__main__":
    run_batch_extraction()
