"""
download_youtube_comments.py
─────────────────────────────────────────────────────────────────────────────
Advanced YouTube Comment Downloader (API-Key Free)
Uses public search scraping to discover videos, and the
youtube-comment-downloader library to pull comments.

Saves normalized records directly to live_reviews.db.
─────────────────────────────────────────────────────────────────────────────
"""

import sqlite3
import re
import sys
import time
import requests
from datetime import datetime, timezone
from youtube_comment_downloader import YoutubeCommentDownloader

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

DB_PATH = "live_reviews.db"
SEARCH_QUERIES = [
    "spotify ai dj",
    "spotify smart shuffle",
    "spotify discover weekly problem",
    "spotify recommendation algorithm"
]

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

def get_video_ids(query):
    print(f"[*] Searching YouTube for: '{query}'...")
    url = f"https://www.youtube.com/results?search_query={requests.utils.quote(query)}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            # Match 11-char video IDs in watch?v= format
            ids = list(set(re.findall(r'watch\?v=([a-zA-Z0-9_-]{11})', r.text)))
            return ids[:5] # Take top 5 videos per search query
    except Exception as exc:
        print(f"[-] Search failed for query '{query}': {exc}")
    return []

def main():
    print("======================================================")
    print("   ADVANCED API-FREE YOUTUBE COMMENT DOWNLOADER")
    print("======================================================")
    conn = init_db()
    cur = conn.cursor()
    
    downloader = YoutubeCommentDownloader()
    
    # Get unique video IDs across all queries
    video_ids = set()
    for query in SEARCH_QUERIES:
        vids = get_video_ids(query)
        video_ids.update(vids)
        time.sleep(1.0)
        
    print(f"[+] Found {len(video_ids)} unique YouTube videos.")
    
    total_downloaded = 0
    saved_count = 0
    
    for idx, vid_id in enumerate(video_ids, 1):
        vid_url = f"https://www.youtube.com/watch?v={vid_id}"
        print(f"[*] [{idx}/{len(video_ids)}] Fetching comments from: {vid_url}")
        
        try:
            # Fetch generator of comments
            generator = downloader.get_comments(vid_id)
            count = 0
            for comment in generator:
                # Limit comments per video to avoid infinite crawl
                if count >= 20:
                    break
                    
                cid = comment.get("cid")
                text = comment.get("text")
                author = comment.get("author")
                likes = comment.get("votes", 0)
                # Convert votes from string (e.g. "1.2k") or take as int
                try:
                    likes = int(likes)
                except Exception:
                    likes = 0
                    
                pub_time = comment.get("time") # Relative time or timestamp
                
                # We need an ISO timestamp. If not available, use current time.
                pub_date = datetime.now(timezone.utc).isoformat()
                
                if cid and text and len(text.split()) >= 5:
                    cur.execute(
                        """
                        INSERT OR IGNORE INTO raw_reviews 
                        (review_id, source_platform, source_url, review_text, rating, upvotes, published_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?);
                        """,
                        (
                            f"youtube_{cid}",
                            "youtube",
                            vid_url,
                            text,
                            None,
                            likes,
                            pub_date
                        )
                    )
                    if cur.rowcount > 0:
                        saved_count += 1
                    count += 1
                    total_downloaded += 1
            print(f"  [+] Downloaded {count} comments from video.")
            time.sleep(1.0) # Polite delay
        except Exception as exc:
            print(f"  [-] Failed to download comments for {vid_id}: {exc}")
            
    conn.commit()
    conn.close()
    
    print("\n======================================================")
    print(" YOUTUBE DOWNLOAD COMPLETE!")
    print(f" Total comments scraped: {total_downloaded}")
    print(f" New records saved to DB: {saved_count}")
    print("======================================================")

if __name__ == "__main__":
    main()
