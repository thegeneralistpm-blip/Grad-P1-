"""
scrapers/reddit_scraper.py  (v2 — Public JSON, No API Key Required)
─────────────────────────────────────────────────────────────────────────────
Reddit Scraper using Reddit's public JSON endpoints.
Architecture Ref: Phase 1 § 1.1

NO API KEYS REQUIRED. Reddit exposes its data as public JSON at:
  https://www.reddit.com/r/{subreddit}/new.json
  https://www.reddit.com/r/{subreddit}/top.json?t=week

We simply hit these URLs with a proper User-Agent header like a browser.
Rate limit: ~60 requests per minute (we stay well below this).
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import Iterator

import requests
from loguru import logger

from scrapers.base_scraper import BaseScraper


# ── Configuration ───────────────────────────────────────────────────────────

TARGET_SUBREDDITS = [
    "spotify",
    "truespotify",
    "listentothis",
    "Music",
]

# Reddit requires a descriptive User-Agent to avoid 429 errors
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; SpotifyReviewBot/1.0; research-tool)",
    "Accept": "application/json",
}

POSTS_PER_SUBREDDIT = 50        # Max posts to fetch per subreddit per run
INTER_REQUEST_DELAY = 2.0       # Seconds between requests (be respectful)
LOOKBACK_HOURS = 6              # For 'new' mode — skip posts older than this

# Keywords that signal relevance to music discovery
DISCOVERY_KEYWORDS = [
    "discover", "recommend", "algorithm", "suggestion", "playlist",
    "discover weekly", "daily mix", "ai dj", "radio", "repetitive",
    "same songs", "new music", "find music", "explore", "genre",
    "feedback loop", "echo chamber", "boring", "stuck", "shuffle",
]


class RedditScraper(BaseScraper):
    """
    Scrapes Reddit submissions about Spotify music discovery using
    Reddit's free, public JSON API — no credentials required.
    """

    platform_name = "reddit"

    def __init__(self, mode: str = "new") -> None:
        """
        Args:
            mode: 'new' for recent posts, 'top' for top posts of the week.
        """
        self.mode = mode
        self._session = requests.Session()
        self._session.headers.update(HEADERS)

    def _is_relevant(self, text: str) -> bool:
        """Quick keyword filter for discovery-related content."""
        lower = text.lower()
        return any(kw in lower for kw in DISCOVERY_KEYWORDS)

    def _fetch_subreddit_posts(self, subreddit: str) -> list[dict]:
        """
        Fetch posts from a subreddit using Reddit's public JSON endpoint.

        URL format:
          - New:  https://www.reddit.com/r/{sub}/new.json?limit=50
          - Top:  https://www.reddit.com/r/{sub}/top.json?t=week&limit=50
        """
        if self.mode == "top":
            url = f"https://www.reddit.com/r/{subreddit}/top.json?t=week&limit={POSTS_PER_SUBREDDIT}"
        else:
            url = f"https://www.reddit.com/r/{subreddit}/new.json?limit={POSTS_PER_SUBREDDIT}"

        try:
            response = self._session.get(url, timeout=15)

            # Reddit returns 429 if we're being too aggressive
            if response.status_code == 429:
                logger.warning(f"[Reddit] Rate limited on r/{subreddit}. Waiting 30s...")
                time.sleep(30)
                response = self._session.get(url, timeout=15)

            response.raise_for_status()
            data = response.json()
            posts = data.get("data", {}).get("children", [])
            logger.info(f"[Reddit] Fetched {len(posts)} posts from r/{subreddit}")
            return posts

        except requests.RequestException as exc:
            logger.error(f"[Reddit] Failed to fetch r/{subreddit}: {exc}")
            return []

    def fetch(self) -> Iterator[dict]:
        """
        Yield raw post dicts from Reddit public JSON endpoints.
        """
        cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=LOOKBACK_HOURS)

        for subreddit in TARGET_SUBREDDITS:
            logger.info(f"[Reddit] Scraping r/{subreddit} | mode={self.mode}")
            posts = self._fetch_subreddit_posts(subreddit)

            for post_wrapper in posts:
                post = post_wrapper.get("data", {})

                # Skip posts older than lookback window in 'new' mode
                created_utc = post.get("created_utc", 0)
                post_time = datetime.fromtimestamp(created_utc, tz=timezone.utc)
                if self.mode == "new" and post_time < cutoff:
                    continue

                # Build full text for relevance check
                title = post.get("title", "")
                selftext = post.get("selftext", "")
                full_text = f"{title} {selftext}".strip()

                if not full_text or not self._is_relevant(full_text):
                    continue

                yield {
                    "id": post.get("id", ""),
                    "title": title,
                    "selftext": selftext,
                    "author": post.get("author", "[deleted]"),
                    "score": post.get("score", 0),
                    "num_comments": post.get("num_comments", 0),
                    "created_utc": created_utc,
                    "permalink": post.get("permalink", ""),
                    "url": post.get("url", ""),
                    "subreddit": subreddit,
                }

            # Be respectful — wait between subreddit requests
            time.sleep(INTER_REQUEST_DELAY)
