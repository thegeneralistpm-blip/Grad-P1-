"""
download_appstore_reviews.py
─────────────────────────────────────────────────────────────────────────────
Advanced Apple App Store Review Scraper
Scrapes Apple's legacy RSS customer reviews feed across US and IN markets.
Uses correct case-sensitive query parameters and mobile User-Agent to
bypass the 1-page rate limit.

Saves normalized records directly to live_reviews.db.
─────────────────────────────────────────────────────────────────────────────
"""

import sqlite3
import sys
import time
import requests
from datetime import datetime, timezone

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

DB_PATH = "live_reviews.db"
APP_ID = 324684580

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS raw_reviews (
            review_id TEXT PRIMARY KEY,
            source_platform TEXT,
            source_url TEXT,
            review_text TEXT,
            rating INTEGER,
            upvotes INTEGER,
            published_at TEXT,
            processing_status TEXT DEFAULT 'pending'
        );
        """
    )
    conn.commit()
    return conn

def main():
    print("======================================================")
    print("      ADVANCED APPLE APP STORE REVIEW SCRAPER")
    print("======================================================")
    conn = init_db()
    cur = conn.cursor()

    countries = ["us", "in"]
    total_downloaded = 0
    saved_count = 0
    
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
        )
    }

    for country in countries:
        print(f"\n[*] Scraping App Store reviews from market: '{country.upper()}'...")
        for page in range(1, 11):
            url = (
                f"https://itunes.apple.com/{country}/rss/customerreviews"
                f"/page={page}/id={APP_ID}/sortby=mostRecent/json"
            )
            try:
                resp = requests.get(url, headers=headers, timeout=15)
                if resp.status_code != 200:
                    print(f"  [-] Page {page}: HTTP {resp.status_code} — stopping.")
                    break
                
                data = resp.json()
                entries = data.get("feed", {}).get("entry", [])
                if not entries:
                    print(f"  [-] Page {page}: No entries returned — stopping.")
                    break

                page_count = 0
                for e in entries:
                    # Skip application metadata entries
                    label = e.get("id", {}).get("label", "")
                    if not label or label == str(APP_ID):
                        continue

                    review_id = label
                    title = e.get("title", {}).get("label", "")
                    content = e.get("content", {}).get("label", "")
                    rating_raw = e.get("im:rating", {}).get("label", "3")
                    
                    try:
                        rating = int(rating_raw)
                    except Exception:
                        rating = 3

                    dt_str = e.get("updated", {}).get("label", "")
                    try:
                        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                    except Exception:
                        dt = datetime.now(timezone.utc)

                    text = f"{title}. {content}".strip()
                    if len(text) < 10:
                        continue

                    # Insert review with unique ID
                    cur.execute(
                        """
                        INSERT OR IGNORE INTO raw_reviews 
                        (review_id, source_platform, source_url, review_text, rating, upvotes, published_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?);
                        """,
                        (
                            f"appstore_{review_id}",
                            "app_store",
                            f"https://apps.apple.com/{country}/app/spotify/id{APP_ID}",
                            text,
                            rating,
                            0,
                            dt.isoformat()
                        )
                    )
                    if cur.rowcount > 0:
                        saved_count += 1
                    page_count += 1
                    total_downloaded += 1

                print(f"  [+] Page {page}: Fetched {page_count} reviews (running total: {total_downloaded})")
                time.sleep(0.5) # Polite delay

            except Exception as exc:
                print(f"  [-] Page {page} failed: {exc}")
                break

    conn.commit()
    conn.close()
    
    print("\n======================================================")
    print(" APP STORE DOWNLOAD COMPLETE!")
    print(f" Total reviews fetched: {total_downloaded}")
    print(f" New unique records saved to DB: {saved_count}")
    print("======================================================")

if __name__ == "__main__":
    main()
