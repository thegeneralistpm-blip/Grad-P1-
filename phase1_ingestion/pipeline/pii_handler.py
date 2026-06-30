"""
pipeline/pii_handler.py
─────────────────────────────────────────────────────────────────────────────
PII Anonymization Module
Architecture Ref: Phase 1 § 1.4 — PII & Compliance Handling

All author handles are hashed with SHA-256 before any data reaches the
database. Raw user identifiers are NEVER persisted. This module is the
single source of truth for all anonymization logic.
─────────────────────────────────────────────────────────────────────────────
"""

import hashlib
import re
from datetime import datetime, timedelta, timezone

from loguru import logger


# ── Constants ──────────────────────────────────────────────────────────────
GDPR_REGIONS = {
    "AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "ES", "FI",
    "FR", "GR", "HR", "HU", "IE", "IT", "LT", "LU", "LV", "MT",
    "NL", "PL", "PT", "RO", "SE", "SI", "SK",  # EU member states
    "GB", "NO", "IS", "LI",                     # EEA additions
    "CH",                                         # Switzerland (adequacy decision)
}

GDPR_RETENTION_DAYS = 90  # Rolling window for GDPR-regulated data


# ── Author Anonymization ────────────────────────────────────────────────────

def anonymize_author(raw_handle: str) -> str:
    """
    Hash an author handle using SHA-256.
    This is a one-way transformation — the original handle cannot be recovered.

    Args:
        raw_handle: The raw username/handle from the source platform.

    Returns:
        A 64-character hex SHA-256 digest of the lowercased handle.

    Example:
        >>> anonymize_author("MusicLover42")
        "a3f9c12d..." (64-char hex string)
    """
    if not raw_handle or not raw_handle.strip():
        # Handle missing or empty usernames (e.g., deleted accounts)
        return hashlib.sha256(b"[deleted]").hexdigest()

    normalized = raw_handle.strip().lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


# ── GDPR Region Detection ───────────────────────────────────────────────────

def is_gdpr_region(country_code: str | None) -> bool:
    """
    Determine if a country code falls under GDPR jurisdiction.

    Args:
        country_code: ISO 3166-1 alpha-2 country code (e.g., "DE", "US").

    Returns:
        True if the country is subject to GDPR, False otherwise.
    """
    if not country_code:
        return False
    return country_code.upper().strip() in GDPR_REGIONS


def calculate_retention_expiry(
    published_at: datetime | None,
    gdpr: bool = False,
) -> datetime | None:
    """
    Calculate when a review record should expire for retention compliance.

    - GDPR regions: 90-day rolling window from ingestion date.
    - Non-GDPR: 24 months (handled at DB level, not computed here).

    Args:
        published_at: The original publication datetime of the review.
        gdpr: Whether this record is subject to GDPR.

    Returns:
        Expiry datetime for GDPR records; None for non-GDPR records.
    """
    if not gdpr:
        return None

    base = published_at or datetime.now(tz=timezone.utc)
    return base + timedelta(days=GDPR_RETENTION_DAYS)


# ── Text Scrubbing ──────────────────────────────────────────────────────────

# Patterns for PII that might appear in review text (best-effort, not exhaustive)
_PII_PATTERNS = [
    (re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE), "[EMAIL]"),
    (re.compile(r"\b\+?[\d\s\-().]{10,15}\b"), "[PHONE]"),
    (re.compile(r"\b(?:u/|@)[\w_-]{3,20}\b"), "[USERNAME]"),  # Reddit u/ and @ handles
]


def scrub_pii_from_text(text: str) -> str:
    """
    Apply best-effort PII scrubbing to review text.
    Replaces emails, phone numbers, and @mentions with placeholders.

    Note: This is not 100% exhaustive — it is a safety net, not a guarantee.
    The primary PII protection is author handle hashing at the metadata level.

    Args:
        text: Raw review text.

    Returns:
        Text with common PII patterns replaced by safe placeholders.
    """
    scrubbed = text
    for pattern, replacement in _PII_PATTERNS:
        scrubbed = pattern.sub(replacement, scrubbed)

    if scrubbed != text:
        logger.debug("PII pattern detected and scrubbed from review text.")

    return scrubbed


# ── Compliance Check ────────────────────────────────────────────────────────

def check_source_compliance(
    source_platform: str,
    approved_sources: set[str],
) -> bool:
    """
    Gate: Is this data source cleared for ingestion by the Legal team?

    Args:
        source_platform: The platform identifier (e.g., 'reddit').
        approved_sources: Set of platforms approved in the source_compliance table.

    Returns:
        True if the source is approved, False otherwise.
    """
    is_approved = source_platform in approved_sources
    if not is_approved:
        logger.warning(
            f"Source '{source_platform}' is NOT approved for ingestion. "
            f"Skipping. Check the source_compliance table."
        )
    return is_approved
