"""
scrapers/base_scraper.py
─────────────────────────────────────────────────────────────────────────────
Abstract Base Scraper
Architecture Ref: Phase 1 § 1.1 — Data Sources & Collection Methods

Every platform-specific scraper must extend BaseScraper and implement
the `fetch()` method. This ensures a consistent interface across all
5 data sources and makes it trivial to add new sources in the future.
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterator

from loguru import logger

from pipeline.normalizer import RawReview
from pipeline.db_writer import (
    start_ingestion_run,
    complete_ingestion_run,
    write_reviews_batch,
    get_approved_sources,
)
from pipeline.pii_handler import check_source_compliance


class BaseScraper(ABC):
    """
    Abstract base class that all platform scrapers must inherit from.

    Subclasses implement:
        - `platform_name` (str): The platform identifier.
        - `fetch()` (Iterator[dict]): Yields raw dicts from the source API/scraper.

    The base class handles:
        - Compliance gating (Legal sign-off check)
        - Normalization via the platform's registered normalizer
        - Batch DB writing with idempotency
        - Ingestion run audit logging
        - Error handling and partial-success tracking
    """

    BATCH_SIZE = 100  # Number of reviews to accumulate before writing to DB

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Return the platform identifier (must match source_platform enum in DB)."""
        ...

    @abstractmethod
    def fetch(self) -> Iterator[dict]:
        """
        Yield raw review dicts from the source platform.
        Each dict will be passed to the corresponding normalizer function.
        """
        ...

    def run(self) -> dict[str, int]:
        """
        Execute the full ingestion pipeline for this scraper:
        1. Check compliance gate.
        2. Start an audit run record.
        3. Fetch reviews → normalize → write in batches.
        4. Complete the audit run record.

        Returns:
            Summary dict: {'fetched': N, 'stored': N, 'skipped': N}
        """
        # ── Step 1: Compliance Gate ─────────────────────────────────────────
        approved_sources = get_approved_sources()
        if not check_source_compliance(self.platform_name, approved_sources):
            logger.warning(
                f"[{self.platform_name}] Ingestion BLOCKED — not approved in source_compliance table. "
                f"Request Legal team to approve this source before retrying."
            )
            return {"fetched": 0, "stored": 0, "skipped": 0}

        # ── Step 2: Start Audit Run ─────────────────────────────────────────
        run_id = start_ingestion_run(
            source_platform=self.platform_name,
            metadata={"scraper_class": self.__class__.__name__},
        )

        fetched, stored, skipped = 0, 0, 0
        batch: list[RawReview] = []
        final_status = "success"
        error_msg = None

        try:
            # ── Step 3: Fetch → Normalize → Batch Write ─────────────────────
            from pipeline.normalizer import normalize  # avoid circular at module level

            for raw_dict in self.fetch():
                try:
                    review = normalize(self.platform_name, raw_dict)
                    batch.append(review)
                    fetched += 1

                    if len(batch) >= self.BATCH_SIZE:
                        result = write_reviews_batch(batch)
                        stored += result["inserted"]
                        skipped += result["skipped"]
                        batch.clear()

                except Exception as item_exc:
                    logger.warning(
                        f"[{self.platform_name}] Failed to normalize/write one review: {item_exc}"
                    )
                    skipped += 1

            # Flush remaining batch
            if batch:
                result = write_reviews_batch(batch)
                stored += result["inserted"]
                skipped += result["skipped"]

        except Exception as run_exc:
            logger.error(f"[{self.platform_name}] Ingestion run failed: {run_exc}", exc_info=True)
            final_status = "failed"
            error_msg = str(run_exc)

        # ── Step 4: Complete Audit Run ──────────────────────────────────────
        complete_ingestion_run(
            run_id=run_id,
            status=final_status,
            reviews_fetched=fetched,
            reviews_stored=stored,
            reviews_skipped=skipped,
            error_message=error_msg,
        )

        logger.info(
            f"[{self.platform_name}] Run complete | "
            f"fetched={fetched} stored={stored} skipped={skipped}"
        )
        return {"fetched": fetched, "stored": stored, "skipped": skipped}
