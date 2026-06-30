"""
scrape_all.py
─────────────────────────────────────────────────────────────────────────────
Lightweight orchestrator for GitHub Actions.
Runs all scrapers in sequence, prints a summary table, and exits with 
code 0 on success or 1 on any failure.

This is called by the GitHub Actions workflow:
  python scrape_all.py

Database (live_reviews.db) is committed back to the repo after each run.
─────────────────────────────────────────────────────────────────────────────
"""

import sys
import sqlite3
import subprocess
from datetime import datetime, timezone

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

DB_PATH = "live_reviews.db"


def log(msg):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"[{ts}] {msg}", flush=True)


def get_db_counts():
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT source_platform, COUNT(*) FROM raw_reviews GROUP BY source_platform;")
        counts = dict(cur.fetchall())
        conn.close()
        return counts
    except Exception:
        return {}


def run_script(script, label):
    log(f"--- {label} ---")
    before = sum(get_db_counts().values())
    try:
        result = subprocess.run(
            [sys.executable, script],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=300
        )
        after = sum(get_db_counts().values())
        added = after - before
        if result.returncode == 0:
            log(f"[OK] {label}: +{added} new records")
            # Print last 5 lines of output for visibility in Actions logs
            lines = result.stdout.strip().splitlines()
            for line in lines[-5:]:
                print(f"    {line}")
            return True, added
        else:
            log(f"[FAIL] {label} exited with code {result.returncode}")
            print(result.stderr[-1000:])
            return False, 0
    except subprocess.TimeoutExpired:
        log(f"[TIMEOUT] {label} exceeded 5 minutes")
        return False, 0
    except Exception as exc:
        log(f"[ERROR] {label}: {exc}")
        return False, 0


def main():
    sep = "=" * 60
    log(sep)
    log("  GITHUB ACTIONS — DAILY REVIEW INGESTION")
    log(f"  Run date: {datetime.now(timezone.utc).strftime('%A, %d %B %Y')}")
    log(sep)

    before_total = sum(get_db_counts().values())
    log(f"DB total before run: {before_total} reviews")
    print()

    scrapers = [
        ("download_appstore_reviews.py",   "Apple App Store (US + IN)"),
        ("download_live_reviews.py",        "Google Play Store"),
        ("download_youtube_comments.py",    "YouTube Comments"),
        ("crawl_spotify_community.py",      "Spotify Community"),
        ("download_missing_reviews.py",     "Reddit (supplemental)"),
    ]

    results = []
    any_failed = False
    for script, label in scrapers:
        ok, added = run_script(script, label)
        results.append((label, ok, added))
        if not ok:
            any_failed = True
        print()

    # ── Summary ──────────────────────────────────────────────────────────────
    after_counts = get_db_counts()
    after_total = sum(after_counts.values())

    print()
    log(sep)
    log("  INGESTION SUMMARY")
    log(sep)
    print(f"  {'Platform':<30} {'Status':<8} {'New Records'}")
    print(f"  {'-'*30} {'-'*8} {'-'*11}")
    for label, ok, added in results:
        status = "OK   " if ok else "FAIL "
        print(f"  {label:<30} {status}    +{added}")

    print()
    log(f"Total reviews in DB after run: {after_total}  (+{after_total - before_total} new)")
    print()
    print(f"  {'Platform':<30} {'Total':>10}")
    print(f"  {'-'*30} {'-'*10}")
    for platform, count in sorted(after_counts.items()):
        print(f"  {platform:<30} {count:>10}")

    log(sep)
    log("  DONE")
    log(sep)

    sys.exit(1 if any_failed else 0)


if __name__ == "__main__":
    main()
