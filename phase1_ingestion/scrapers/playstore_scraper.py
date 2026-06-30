"""
scrapers/playstore_scraper.py
─────────────────────────────────────────────────────────────────────────────
Google Play Store Scraper
Architecture Ref: Phase 1 § 1.1 — Daily batch (2AM UTC)

Uses the `google-play-scraper` library to fetch Spotify reviews from the
Android Play Store across priority markets.
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import os
import time
from typing import Iterator

from google_play_scraper import Sort, reviews
from loguru import logger

from scrapers.base_scraper import BaseScraper


# ── Configuration ───────────────────────────────────────────────────────────

SPOTIFY_PACKAGE_ID = os.environ.get("PLAYSTORE_APP_ID", "com.spotify.music")

# (lang, country_code, geo_region_for_GDPR)
TARGET_MARKETS = [
    ("en", "us", None),     # United States
    ("en", "gb", "GB"),     # United Kingdom (GDPR)
    ("en", "in", "IN"),     # India
    ("en", "au", None),     # Australia
    ("en", "ca", None),     # Canada
    ("de", "de", "DE"),     # Germany (GDPR)
    ("pt", "br", None),     # Brazil
]

REVIEWS_PER_MARKET = 200    # Max reviews per market per run
INTER_MARKET_DELAY = 2.0    # Seconds between market requests


class PlayStoreScraper(BaseScraper):
    """
    Scrapes Spotify Play Store reviews across multiple Android markets.
    Configured to run daily at 2AM UTC via n8n CRON trigger.

    Fetches both 'most_relevant' and 'newest' reviews to ensure coverage
    of both trending and recent feedback.
    """

    platform_name = "play_store"

    def fetch(self) -> Iterator[dict]:
        """
        Yield raw Play Store review dicts for each target market.
        """
        for lang, country, geo_region in TARGET_MARKETS:
            for sort_order, sort_label in [
                (Sort.NEWEST, "newest"),
                (Sort.MOST_RELEVANT, "most_relevant"),
            ]:
                logger.info(
                    f"[PlayStore] Fetching {sort_label} reviews | "
                    f"country={country.upper()} | lang={lang}"
                )

                try:
                    result, _ = reviews(
                        SPOTIFY_PACKAGE_ID,
                        lang=lang,
                        country=country,
                        sort=sort_order,
                        count=REVIEWS_PER_MARKET,
                        filter_score_with=None,  # Fetch all star ratings
                    )

                    logger.info(
                        f"[PlayStore] Fetched {len(result)} {sort_label} reviews "
                        f"from {country.upper()}"
                    )

                    for review in result:
                        # Inject geo context for downstream GDPR handling
                        review["geo_region"] = geo_region or country.upper()
                        yield review

                    time.sleep(INTER_MARKET_DELAY)

                except Exception as exc:
                    logger.error(
                        f"[PlayStore] Failed for country={country}, sort={sort_label}: {exc}",
                        exc_info=True,
                    )
                    continue
