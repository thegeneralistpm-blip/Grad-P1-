"""
scrapers/twitter_scraper.py
─────────────────────────────────────────────────────────────────────────────
X / Twitter Scraper (via Tweepy v4, X API v2)
Architecture Ref: Phase 1 § 1.1 — Near real-time (every 4 hours)

Uses the X API v2 Recent Search endpoint to find public tweets containing
Spotify discovery-related keywords and hashtags.
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone
from typing import Iterator

import tweepy
from loguru import logger

from scrapers.base_scraper import BaseScraper


# ── Configuration ───────────────────────────────────────────────────────────

# X API v2 search query — targets Spotify-related discovery discussions
# Excludes retweets, replies, and low-quality posts
SEARCH_QUERY = (
    "(spotify recommendation OR spotify discover OR spotify algorithm "
    "OR spotify playlist OR \"discover weekly\" OR \"spotify ai dj\" "
    "OR \"spotify same songs\" OR \"spotify repetitive\") "
    "lang:en -is:retweet -is:reply"
)

MAX_RESULTS_PER_PAGE = 100   # X API v2 max per page (100 for Academic, 10 for basic)
MAX_TWEETS = 500             # Total tweets to fetch per run
LOOKBACK_HOURS = 4           # Search window (matches CRON schedule)
REQUEST_DELAY = 1.0          # Seconds between API requests


class TwitterScraper(BaseScraper):
    """
    Fetches recent tweets about Spotify music discovery from X (Twitter).
    Uses X API v2 Bearer Token (App-only auth) — read-only.
    """

    platform_name = "twitter"

    def __init__(self) -> None:
        self._client = self._init_client()

    def _init_client(self) -> tweepy.Client:
        """Initialize a Tweepy v2 client using the Bearer Token."""
        bearer_token = os.environ.get("TWITTER_BEARER_TOKEN")
        if not bearer_token:
            raise EnvironmentError(
                "TWITTER_BEARER_TOKEN must be set in environment variables. "
                "Get your token from https://developer.twitter.com/"
            )
        return tweepy.Client(
            bearer_token=bearer_token,
            wait_on_rate_limit=True,  # Automatically handle rate limit waits
        )

    def fetch(self) -> Iterator[dict]:
        """
        Yield raw tweet dicts from the X API v2 Recent Search endpoint.
        """
        start_time = datetime.now(tz=timezone.utc) - timedelta(hours=LOOKBACK_HOURS)
        tweet_count = 0

        logger.info(
            f"[Twitter] Searching tweets since {start_time.isoformat()} | "
            f"query: {SEARCH_QUERY[:80]}..."
        )

        try:
            # Use Tweepy Paginator to handle pagination transparently
            for tweet in tweepy.Paginator(
                self._client.search_recent_tweets,
                query=SEARCH_QUERY,
                start_time=start_time,
                max_results=MAX_RESULTS_PER_PAGE,
                tweet_fields=["id", "text", "author_id", "created_at", "public_metrics", "lang"],
                expansions=["author_id"],
                user_fields=["username"],
            ).flatten(limit=MAX_TWEETS):

                if tweet_count >= MAX_TWEETS:
                    break

                # Build a flat dict matching our normalizer's expected keys
                yield {
                    "id": tweet.id,
                    "text": tweet.text,
                    "author_id": tweet.author_id,
                    "username": f"user_{tweet.author_id}",  # anonymized by normalizer anyway
                    "created_at": tweet.created_at,
                    "public_metrics": tweet.public_metrics or {},
                    "url": f"https://twitter.com/i/web/status/{tweet.id}",
                }

                tweet_count += 1
                time.sleep(REQUEST_DELAY)

            logger.info(f"[Twitter] Fetched {tweet_count} tweets.")

        except tweepy.TweepyException as exc:
            logger.error(f"[Twitter] API error: {exc}", exc_info=True)
            raise
