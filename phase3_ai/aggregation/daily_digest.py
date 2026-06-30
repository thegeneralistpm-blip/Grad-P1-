"""
aggregation/daily_digest.py
─────────────────────────────────────────────────────────────────────────────
Daily Aggregation & Digest Generator
Calculates top rising themes, average urgency scores, platform breakdown,
and writes structured summaries to `daily_digests` table.
─────────────────────────────────────────────────────────────────────────────
"""

import os
import sqlite3
import json
from collections import Counter
from datetime import datetime, timezone

DB_PATH = "live_reviews.db"

def init_digest_table(conn):
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS daily_digests (
            digest_date TEXT PRIMARY KEY,
            top_themes TEXT,
            urgency_avg REAL,
            total_reviews INTEGER,
            platform_breakdown TEXT,
            generated_at TEXT
        );
        """
    )
    conn.commit()

def generate_digest():
    if not os.path.exists(DB_PATH):
        print("[!] Database not found.")
        return None
        
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    init_digest_table(conn)
    cur = conn.cursor()
    
    # Join raw_reviews and review_insights
    cur.execute(
        """
        SELECT r.source_platform, i.themes, i.urgency_score, i.sentiment 
        FROM review_insights i
        JOIN raw_reviews r ON i.review_id = r.review_id;
        """
    )
    rows = cur.fetchall()
    if not rows:
        print("[!] No extracted insights available to aggregate.")
        conn.close()
        return None
        
    theme_counter = Counter()
    platform_counter = Counter()
    total_urgency = 0.0
    
    for row in rows:
        platform_counter[row["source_platform"]] += 1
        total_urgency += float(row["urgency_score"] or 3.0)
        try:
            themes = json.loads(row["themes"] or "[]")
            for t in themes:
                theme_counter[t] += 1
        except Exception:
            pass
            
    top_themes = [{"theme": t, "count": c} for t, c in theme_counter.most_common(5)]
    avg_urgency = round(total_urgency / len(rows), 2)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    digest_data = {
        "digest_date": today,
        "top_themes": top_themes,
        "urgency_avg": avg_urgency,
        "total_reviews": len(rows),
        "platform_breakdown": dict(platform_counter)
    }
    
    cur.execute(
        """
        INSERT OR REPLACE INTO daily_digests 
        (digest_date, top_themes, urgency_avg, total_reviews, platform_breakdown, generated_at)
        VALUES (?, ?, ?, ?, ?, ?);
        """,
        (
            today,
            json.dumps(top_themes),
            avg_urgency,
            len(rows),
            json.dumps(dict(platform_counter)),
            datetime.now(timezone.utc).isoformat()
        )
    )
    conn.commit()
    conn.close()
    
    print("======================================================")
    print(f"[*] Daily Digest Generated for {today}")
    print(f"[*] Total Reviews Analyzed: {len(rows)}")
    print(f"[*] Average Urgency Score:  {avg_urgency} / 5.0")
    print("[*] Top Identified Themes:")
    for item in top_themes:
        print(f"    - {item['theme']} ({item['count']} mentions)")
    print("======================================================")
    return digest_data

if __name__ == "__main__":
    generate_digest()
