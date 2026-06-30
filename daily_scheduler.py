"""
daily_scheduler.py
─────────────────────────────────────────────────────────────────────────────
Daily Review Ingestion Scheduler
Runs all scrapers once per day at a configured time and logs results.

Platforms covered:
  1. Apple App Store (US + India, 10 pages each = ~1000 reviews)
  2. Google Play Store (latest 200 reviews)
  3. YouTube Comments (API-free, 4 search queries)
  4. Spotify Community Forum (Scrapy spider, 3 pages)
  5. Reddit r/spotify (curated fallback until OAuth credentials added)

Usage:
  python daily_scheduler.py              # Runs at 02:00 AM every day
  python daily_scheduler.py --now        # Runs immediately once, then exits
  python daily_scheduler.py --time 06:30 # Runs at 06:30 AM every day

─────────────────────────────────────────────────────────────────────────────
"""

import sys
import time
import argparse
import sqlite3
import subprocess
from datetime import datetime, timezone

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

try:
    import schedule
except ImportError:
    print("[!] 'schedule' library not found. Installing...")
    subprocess.run([sys.executable, "-m", "pip", "install", "schedule", "-q"], check=True)
    import schedule

DB_PATH = "live_reviews.db"

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")

def get_db_counts():
    """Return dict of platform -> count from live_reviews.db."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT source_platform, COUNT(*) FROM raw_reviews GROUP BY source_platform;")
        counts = dict(cur.fetchall())
        conn.close()
        return counts
    except Exception:
        return {}

def run_script(script_path, label):
    """Run a Python script as a subprocess, return (success, new_records_msg)."""
    log(f"[{label}] Starting...")
    before = get_db_counts()
    try:
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True, text=True, timeout=300
        )
        after = get_db_counts()

        # Calculate new records added
        new_total = sum(after.values()) - sum(before.values())
        if result.returncode == 0:
            log(f"[{label}] Done. +{new_total} new records added to DB.")
            return True, new_total
        else:
            log(f"[{label}] ERROR:\n{result.stderr[-500:]}")
            return False, 0
    except subprocess.TimeoutExpired:
        log(f"[{label}] TIMED OUT after 5 minutes.")
        return False, 0
    except Exception as exc:
        log(f"[{label}] EXCEPTION: {exc}")
        return False, 0


# ─────────────────────────────────────────────────────────────────────────────
# Main Ingestion Job
# ─────────────────────────────────────────────────────────────────────────────

def run_daily_ingestion():
    sep = "=" * 60
    log(sep)
    log("  DAILY REVIEW INGESTION JOB — STARTING")
    log(sep)

    before_counts = get_db_counts()
    before_total = sum(before_counts.values())
    log(f"DB total before run: {before_total} reviews")

    results = []

    # 1. Apple App Store
    ok, added = run_script("download_appstore_reviews.py", "Apple App Store")
    results.append(("Apple App Store", ok, added))

    # 2. Google Play Store
    ok, added = run_script("download_live_reviews.py", "Google Play Store")
    results.append(("Google Play Store", ok, added))

    # 3. YouTube Comments (API-free)
    ok, added = run_script("download_youtube_comments.py", "YouTube")
    results.append(("YouTube", ok, added))

    # 4. Spotify Community Forum (Scrapy)
    ok, added = run_script("crawl_spotify_community.py", "Spotify Community")
    results.append(("Spotify Community", ok, added))

    # 5. Reddit + legacy supplemental (Apple/YouTube fallback)
    ok, added = run_script("download_missing_reviews.py", "Reddit (supplemental)")
    results.append(("Reddit (supplemental)", ok, added))

    # ── Summary ────────────────────────────────────────────────────────────
    after_counts = get_db_counts()
    after_total = sum(after_counts.values())

    log(sep)
    log("  DAILY INGESTION SUMMARY")
    log(sep)
    print(f"  {'Platform':<25} {'Status':<10} {'New Records'}")
    print(f"  {'-'*25} {'-'*10} {'-'*12}")
    for platform, ok, added in results:
        status = "OK" if ok else "FAILED"
        print(f"  {platform:<25} {status:<10} +{added}")
    print()
    log(f"DB total after run: {after_total} reviews (+{after_total - before_total} new)")

    print()
    print(f"  {'Platform':<25} {'Total in DB':>12}")
    print(f"  {'-'*25} {'-'*12}")
    for platform, count in sorted(after_counts.items()):
        print(f"  {platform:<25} {count:>12}")

    log(sep)
    log("  DAILY INGESTION JOB — COMPLETE")
    log(sep)


# ─────────────────────────────────────────────────────────────────────────────
# Scheduler Entry Point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Daily Review Ingestion Scheduler")
    parser.add_argument("--now",  action="store_true", help="Run once immediately and exit")
    parser.add_argument("--time", default="02:00",     help="Time to run daily (HH:MM, 24-hour, default: 02:00)")
    args = parser.parse_args()

    if args.now:
        log("Running in --now mode (single execution)...")
        run_daily_ingestion()
        return

    # Schedule the job
    run_time = args.time
    log(f"Scheduler started. Job will run daily at {run_time}.")
    log("Press CTRL+C to stop.")
    schedule.every().day.at(run_time).do(run_daily_ingestion)

    # Also run immediately on first startup
    log("Running initial ingestion on startup...")
    run_daily_ingestion()

    while True:
        schedule.run_pending()
        time.sleep(30) # Check every 30 seconds


if __name__ == "__main__":
    main()
