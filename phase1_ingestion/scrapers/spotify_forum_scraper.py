"""
scrapers/spotify_forum_scraper.py
─────────────────────────────────────────────────────────────────────────────
Spotify Community Forum Scraper (BeautifulSoup)
Architecture Ref: Phase 1 § 1.1 — Daily batch

Scrapes the Spotify Community Forum (community.spotify.com) which runs on
the Khoros/Lithium platform. Targets the "Music" and "Playlist" categories
for discovery-related discussions.
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Iterator
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from loguru import logger

from scrapers.base_scraper import BaseScraper


# ── Configuration ───────────────────────────────────────────────────────────

BASE_URL = os.environ.get(
    "SPOTIFY_FORUM_BASE_URL",
    "https://community.spotify.com"
)

# Forum category paths to scrape
TARGET_CATEGORIES = [
    "/t5/Music/bd-p/Music",
    "/t5/Ongoing-Issues/bd-p/ongoing",
    "/t5/Closed-Ideas/bd-p/closed-ideas",
]

POSTS_PER_CATEGORY = 50     # Max posts to scrape per category
INTER_REQUEST_DELAY = 1.5   # Seconds between requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; SpotifyReviewBot/1.0; "
        "+https://spotify.com/privacy)"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# Discovery-related keywords for relevance filtering
DISCOVERY_KEYWORDS = [
    "discover", "recommend", "algorithm", "playlist", "suggestion",
    "new music", "find", "repetitive", "same", "boring", "explore",
]


class SpotifyForumScraper(BaseScraper):
    """
    Scrapes Spotify Community Forum posts about music discovery and recommendations.
    Falls back gracefully on any parsing errors, ensuring partial results are
    still saved rather than failing the entire run.
    """

    platform_name = "spotify_community"

    def __init__(self) -> None:
        self._session = requests.Session()
        self._session.headers.update(HEADERS)

    def _is_relevant(self, text: str) -> bool:
        """Quick relevance check against discovery keywords."""
        lower = text.lower()
        return any(kw in lower for kw in DISCOVERY_KEYWORDS)

    def _parse_post_list(self, html: str, category_url: str) -> list[str]:
        """
        Parse the category listing page and extract individual post URLs.

        Returns:
            List of absolute post URLs.
        """
        soup = BeautifulSoup(html, "lxml")
        post_links = []

        # Lithium/Khoros forum structure — post titles are in <a> tags with
        # class 'lia-link-navigation' inside message list items
        for link in soup.select("a.page-link.lia-link-navigation.lia-custom-event"):
            href = link.get("href")
            if href:
                post_links.append(urljoin(BASE_URL, href))

        # Fallback: broader selector
        if not post_links:
            for link in soup.select(".message-subject a, .lia-message-subject a"):
                href = link.get("href")
                if href:
                    post_links.append(urljoin(BASE_URL, href))

        return post_links[:POSTS_PER_CATEGORY]

    def _parse_post(self, url: str) -> dict | None:
        """
        Scrape a single forum post and extract its content.

        Returns:
            A dict matching the spotify_community normalizer schema, or None if parsing fails.
        """
        try:
            resp = self._session.get(url, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as exc:
            logger.warning(f"[SpotifyForum] Failed to fetch post {url}: {exc}")
            return None

        soup = BeautifulSoup(resp.text, "lxml")

        # Extract post body (Lithium platform selectors)
        body_el = soup.select_one(".lia-message-body-content, .post-body")
        body = body_el.get_text(separator=" ", strip=True) if body_el else ""

        if not body or not self._is_relevant(body):
            return None

        # Extract title
        title_el = soup.select_one("h1.lia-message-subject, .page-header h1")
        title = title_el.get_text(strip=True) if title_el else None

        # Extract author
        author_el = soup.select_one(".UserName, .lia-user-name a")
        author = author_el.get_text(strip=True) if author_el else "[anonymous]"

        # Extract kudos (upvotes equivalent)
        kudos_el = soup.select_one(".kudo-count, .KudoCountWrapper")
        kudos = 0
        if kudos_el:
            try:
                kudos = int(kudos_el.get_text(strip=True).replace(",", ""))
            except ValueError:
                kudos = 0

        # Extract reply count
        replies_el = soup.select_one(".reply-count, .lia-replies-count")
        replies = 0
        if replies_el:
            try:
                replies = int(replies_el.get_text(strip=True).replace(",", ""))
            except ValueError:
                replies = 0

        # Extract post ID from URL (Lithium uses /td-p/{id} pattern)
        post_id = url.split("/td-p/")[-1].split("/")[0] if "/td-p/" in url else url

        # Extract published date
        date_el = soup.select_one("time.local-date, .post-date time")
        published_at = None
        if date_el:
            dt_str = date_el.get("datetime") or date_el.get_text(strip=True)
            try:
                published_at = datetime.fromisoformat(dt_str)
                if published_at.tzinfo is None:
                    published_at = published_at.replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                pass

        return {
            "post_id": post_id,
            "url": url,
            "title": title,
            "body": body,
            "author": author,
            "kudos_count": kudos,
            "replies": replies,
            "published_at": published_at.isoformat() if published_at else None,
        }

    def fetch(self) -> Iterator[dict]:
        """
        Yield raw forum post dicts from Spotify Community Forum.
        """
        for category_path in TARGET_CATEGORIES:
            category_url = urljoin(BASE_URL, category_path)
            logger.info(f"[SpotifyForum] Fetching category: {category_url}")

            try:
                resp = self._session.get(category_url, timeout=15)
                resp.raise_for_status()

                post_urls = self._parse_post_list(resp.text, category_url)
                logger.info(
                    f"[SpotifyForum] Found {len(post_urls)} posts in {category_path}"
                )

                for post_url in post_urls:
                    post_data = self._parse_post(post_url)
                    if post_data:
                        yield post_data
                    time.sleep(INTER_REQUEST_DELAY)

            except requests.RequestException as exc:
                logger.error(
                    f"[SpotifyForum] Failed to fetch category {category_path}: {exc}",
                    exc_info=True,
                )
                continue
