"""
scrapers/appstore_scraper.py
─────────────────────────────────────────────────────────────────────────────
Apple App Store Scraper
Architecture Ref: Phase 1 § 1.1 — Daily batch (2AM UTC)

Uses the `app-store-scraper` library to fetch Spotify reviews from the
iOS App Store. Supports multiple country stores for geographic coverage.
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import os
import time
from typing import Iterator

from app_store_scraper import AppStore
from loguru import logger

from scrapers.base_scraper import BaseScraper


# ── Configuration ───────────────────────────────────────────────────────────

SPOTIFY_APP_ID = os.environ.get("APPSTORE_APP_ID", "324684580")

# Countries to scrape — prioritized markets for Spotify
TARGET_COUNTRIES = [
    ("us", None),       # United States
    ("gb", "GB"),       # United Kingdom (GDPR)
    ("in", "IN"),       # India
    ("au", None),       # Australia
    ("ca", None),       # Canada
    ("de", "DE"),       # Germany (GDPR)
    ("br", None),       # Brazil
]

REVIEWS_PER_COUNTRY = 200   # Max reviews to fetch per country per run
INTER_COUNTRY_DELAY = 2.0   # Seconds between country requests (rate limiting)


class AppStoreScraper(BaseScraper):
    """
    Scrapes Spotify App Store reviews across multiple country stores.
    Configured to run daily at 2AM UTC via n8n CRON trigger.
    """

    platform_name = "app_store"

    def fetch(self) -> Iterator[dict]:
        """
        Yield raw review dicts from the App Store for each target country.
        """
        for country_code, geo_region in TARGET_COUNTRIES:
            logger.info(
                f"[AppStore] Fetching reviews | country={country_code.upper()} "
                f"| app_id={SPOTIFY_APP_ID}"
            )

            try:
                app = AppStore(
                    country=country_code,
                    app_name="spotify",
                    app_id=SPOTIFY_APP_ID,
                )
                app.review(how_many=REVIEWS_PER_COUNTRY)

                reviews = app.reviews
                logger.info(
                    f"[AppStore] Fetched {len(reviews)} reviews from {country_code.upper()}"
                )

                for review in reviews:
                    # Inject geo context for downstream PII/GDPR handling
                    review["country"] = geo_region or country_code.upper()
                    yield review

                # Rate limiting: be respectful to Apple's servers
                time.sleep(INTER_COUNTRY_DELAY)

            except Exception as exc:
                logger.error(
                    f"[AppStore] Failed for country={country_code}: {exc}",
                    exc_info=True,
                )
                # Continue to next country — don't fail the entire run
                continue
