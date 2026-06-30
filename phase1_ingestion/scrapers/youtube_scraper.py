"""
scrapers/youtube_scraper.py
─────────────────────────────────────────────────────────────────────────────
YouTube Data API v3 Scraper
Architecture Ref: Phase 1 § 1.1 — Replacement for Twitter

FREE TIER: 10,000 quota units/day. Each search costs 100 units.
Each comment page costs 1 unit. We stay well within limits.

How to get a FREE API key (takes 2 minutes):
  1. Go to https://console.cloud.google.com/
  2. Create a new project (e.g., "SpotifyReviewEngine")
  3. Enable "YouTube Data API v3"
  4. Go to Credentials → Create API Key
  5. Copy the key into your .env as YOUTUBE_API_KEY

Collects:
  - Top YouTube videos about Spotify music discovery
  - Comments on those videos (rich, long-form user opinions)
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone
from typing import Iterator

import requests
from loguru import logger

from scrapers.base_scraper import BaseScraper


# ── Configuration ───────────────────────────────────────────────────────────

YOUTUBE_BASE_URL = "https://www.googleapis.com/youtube/v3"

# Search queries targeting Spotify discovery discussions
SEARCH_QUERIES = [
    "spotify discover weekly problem",
    "spotify algorithm recommendations bad",
    "spotify same songs repetitive",
    "spotify music discovery tips",
    "spotify AI DJ review",
    "spotify playlist recommendation broken",
]

MAX_VIDEOS_PER_QUERY = 5         # Videos per search query (100 units per search)
MAX_COMMENTS_PER_VIDEO = 50      # Top comments per video
LOOKBACK_DAYS = 30               # Only fetch videos published in the last 30 days
INTER_REQUEST_DELAY = 0.5        # Seconds between API calls

# Minimum comment length (chars) — short comments like "lol" aren't useful
MIN_COMMENT_LENGTH = 80

# Keywords to filter for relevant comments
DISCOVERY_KEYWORDS = [
    "recommend", "discover", "algorithm", "playlist", "suggest",
    "same song", "repetitive", "new music", "boring", "genre",
    "weekly", "daily mix", "radio", "find music", "stuck",
]


class YouTubeScraper(BaseScraper):
    """
    Scrapes YouTube video comments about Spotify music discovery.

    Uses the YouTube Data API v3 (free, 10,000 units/day).
    Strategy:
      1. Search for Spotify-related videos using targeted queries.
      2. Fetch the top comments from each video.
      3. Filter comments by length and keyword relevance.
      4. Yield normalized comment dicts for the pipeline.
    """

    platform_name = "youtube"

    def __init__(self) -> None:
        self._api_key = self._load_api_key()
        self._session = requests.Session()

    def _load_api_key(self) -> str:
        """Load the YouTube API key from environment variables."""
        key = os.environ.get("YOUTUBE_API_KEY")
        if not key:
            raise EnvironmentError(
                "YOUTUBE_API_KEY is not set.\n"
                "Get a free key in 2 minutes:\n"
                "  1. https://console.cloud.google.com/\n"
                "  2. Create project → Enable 'YouTube Data API v3'\n"
                "  3. Credentials → Create API Key\n"
                "  4. Add to .env: YOUTUBE_API_KEY=your_key_here"
            )
        return key

    def _is_relevant_comment(self, text: str) -> bool:
        """Filter: comment must be long enough and mention discovery themes."""
        if len(text) < MIN_COMMENT_LENGTH:
            return False
        lower = text.lower()
        return any(kw in lower for kw in DISCOVERY_KEYWORDS)

    def _search_videos(self, query: str) -> list[dict]:
        """
        Search YouTube for videos matching a query.
        Returns a list of video metadata dicts.

        API cost: 100 units per call.
        """
        published_after = (
            datetime.now(tz=timezone.utc) - timedelta(days=LOOKBACK_DAYS)
        ).strftime("%Y-%m-%dT%H:%M:%SZ")

        params = {
            "key": self._api_key,
            "part": "snippet",
            "q": query,
            "type": "video",
            "maxResults": MAX_VIDEOS_PER_QUERY,
            "order": "relevance",
            "publishedAfter": published_after,
            "relevanceLanguage": "en",
        }

        try:
            resp = self._session.get(
                f"{YOUTUBE_BASE_URL}/search", params=params, timeout=15
            )
            resp.raise_for_status()
            items = resp.json().get("items", [])
            logger.info(f"[YouTube] Query '{query}' → {len(items)} videos found")
            return items
        except requests.RequestException as exc:
            logger.error(f"[YouTube] Search failed for query '{query}': {exc}")
            return []

    def _fetch_comments(self, video_id: str, video_title: str) -> list[dict]:
        """
        Fetch top-level comments for a given YouTube video.
        Returns raw comment dicts.

        API cost: 1 unit per page.
        """
        params = {
            "key": self._api_key,
            "part": "snippet",
            "videoId": video_id,
            "maxResults": MAX_COMMENTS_PER_VIDEO,
            "order": "relevance",  # Top comments first
            "textFormat": "plainText",
        }

        try:
            resp = self._session.get(
                f"{YOUTUBE_BASE_URL}/commentThreads", params=params, timeout=15
            )
            # Comments may be disabled on some videos — handle gracefully
            if resp.status_code == 403:
                logger.debug(f"[YouTube] Comments disabled for video: {video_id}")
                return []
            resp.raise_for_status()
            items = resp.json().get("items", [])
            logger.debug(
                f"[YouTube] Fetched {len(items)} comments for '{video_title}'"
            )
            return items
        except requests.RequestException as exc:
            logger.warning(f"[YouTube] Comment fetch failed for {video_id}: {exc}")
            return []

    def fetch(self) -> Iterator[dict]:
        """
        Yield raw comment dicts from YouTube.
        Each dict matches the schema expected by normalize_youtube() in normalizer.py.
        """
        seen_video_ids: set[str] = set()

        for query in SEARCH_QUERIES:
            logger.info(f"[YouTube] Searching: '{query}'")
            videos = self._search_videos(query)
            time.sleep(INTER_REQUEST_DELAY)

            for video in videos:
                video_id = video.get("id", {}).get("videoId")
                if not video_id or video_id in seen_video_ids:
                    continue
                seen_video_ids.add(video_id)

                snippet = video.get("snippet", {})
                video_title = snippet.get("title", "")
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                channel = snippet.get("channelTitle", "")
                published_at = snippet.get("publishedAt")

                logger.info(f"[YouTube] Fetching comments for: '{video_title}'")
                comments = self._fetch_comments(video_id, video_title)
                time.sleep(INTER_REQUEST_DELAY)

                for item in comments:
                    top_comment = item.get("snippet", {}).get("topLevelComment", {})
                    comment_snippet = top_comment.get("snippet", {})
                    text = comment_snippet.get("textDisplay", "").strip()

                    # Apply relevance and length filter
                    if not self._is_relevant_comment(text):
                        continue

                    yield {
                        "id": top_comment.get("id", ""),
                        "video_id": video_id,
                        "video_title": video_title,
                        "video_url": video_url,
                        "channel": channel,
                        "text": text,
                        "author": comment_snippet.get("authorDisplayName", "[anonymous]"),
                        "like_count": comment_snippet.get("likeCount", 0),
                        "reply_count": item.get("snippet", {}).get("totalReplyCount", 0),
                        "published_at": comment_snippet.get("publishedAt") or published_at,
                    }
