"""
pipeline/normalizer.py
─────────────────────────────────────────────────────────────────────────────
Unified Schema Normalizer
Architecture Ref: Phase 1 § 1.3 — Unified Raw Schema

Every review — regardless of source platform — is mapped to the same
RawReview dataclass before being written to PostgreSQL. This ensures
Phase 2 has a consistent, predictable input format regardless of how
many new sources are added over time.
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from pipeline.pii_handler import (
    anonymize_author,
    is_gdpr_region,
    calculate_retention_expiry,
    scrub_pii_from_text,
)


# ── Canonical Review Model ──────────────────────────────────────────────────

@dataclass
class RawReview:
    """
    The unified, platform-agnostic review record.
    This is the single schema that all scrapers must produce.
    Matches the `raw_reviews` PostgreSQL table exactly.
    """
    # Identity (auto-generated)
    review_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Source
    source_platform: str = ""           # 'reddit' | 'app_store' | 'play_store' | 'twitter' | 'spotify_community'
    source_url: Optional[str] = None
    source_post_id: Optional[str] = None  # Original ID on the platform

    # Content
    review_text: str = ""
    review_title: Optional[str] = None
    rating: Optional[int] = None         # 1-5 stars (App Store / Play Store only)
    upvotes: int = 0
    comment_count: int = 0

    # Author (PII-safe: hashed)
    author_hash: str = ""

    # Metadata
    language: str = "en"
    geo_region: Optional[str] = None
    is_gdpr_region: bool = False

    # Timestamps
    published_at: Optional[datetime] = None
    ingested_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))

    # Processing state
    processing_status: str = "pending"
    content_hash: Optional[str] = None
    error_message: Optional[str] = None

    # Compliance
    is_compliant: bool = True
    retention_expires_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        """Serialize to a flat dict suitable for PostgreSQL insertion."""
        return {
            "review_id": self.review_id,
            "source_platform": self.source_platform,
            "source_url": self.source_url,
            "source_post_id": self.source_post_id,
            "review_text": self.review_text,
            "review_title": self.review_title,
            "rating": self.rating,
            "upvotes": self.upvotes,
            "comment_count": self.comment_count,
            "author_hash": self.author_hash,
            "language": self.language,
            "geo_region": self.geo_region,
            "is_gdpr_region": self.is_gdpr_region,
            "published_at": self.published_at,
            "ingested_at": self.ingested_at,
            "processing_status": self.processing_status,
            "content_hash": self.content_hash,
            "error_message": self.error_message,
            "is_compliant": self.is_compliant,
            "retention_expires_at": self.retention_expires_at,
        }


# ── Normalizer Functions (one per source) ──────────────────────────────────

def normalize_reddit(raw: dict) -> RawReview:
    """
    Normalize a raw PRAW submission or comment dict into a RawReview.

    Expected raw keys:
        id, url, title, selftext, body (for comments), author, score,
        num_comments, created_utc, subreddit, permalink
    """
    # Use selftext for posts, body for comments
    text = raw.get("selftext") or raw.get("body") or ""
    title = raw.get("title")

    # Reddit post URL
    permalink = raw.get("permalink", "")
    url = f"https://www.reddit.com{permalink}" if permalink else raw.get("url")

    author_raw = str(raw.get("author") or "[deleted]")
    published_ts = raw.get("created_utc")
    published_at = (
        datetime.fromtimestamp(published_ts, tz=timezone.utc)
        if published_ts else None
    )

    review = RawReview(
        source_platform="reddit",
        source_url=url,
        source_post_id=str(raw.get("id", "")),
        review_text=scrub_pii_from_text(text),
        review_title=title,
        upvotes=int(raw.get("score", 0)),
        comment_count=int(raw.get("num_comments", 0)),
        author_hash=anonymize_author(author_raw),
        published_at=published_at,
    )
    return review


def normalize_app_store(raw: dict) -> RawReview:
    """
    Normalize an App Store review (from app-store-scraper) into a RawReview.

    Expected raw keys:
        id, title, content, score, userName, date, url
    """
    author_raw = str(raw.get("userName") or "[anonymous]")
    date_str = raw.get("date")
    published_at = None
    if date_str:
        try:
            published_at = datetime.fromisoformat(str(date_str))
            if published_at.tzinfo is None:
                published_at = published_at.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            published_at = None

    geo = raw.get("country")

    review = RawReview(
        source_platform="app_store",
        source_url=raw.get("url"),
        source_post_id=str(raw.get("id", "")),
        review_text=scrub_pii_from_text(raw.get("content") or ""),
        review_title=raw.get("title"),
        rating=int(raw["score"]) if raw.get("score") is not None else None,
        author_hash=anonymize_author(author_raw),
        geo_region=geo.upper() if geo else None,
        is_gdpr_region=is_gdpr_region(geo),
        published_at=published_at,
        retention_expires_at=calculate_retention_expiry(published_at, is_gdpr_region(geo)),
    )
    return review


def normalize_play_store(raw: dict) -> RawReview:
    """
    Normalize a Play Store review (from google-play-scraper) into a RawReview.

    Expected raw keys:
        reviewId, content, score, userName, at, thumbsUpCount, replyContent
    """
    author_raw = str(raw.get("userName") or "[anonymous]")
    at = raw.get("at")
    published_at = None
    if isinstance(at, datetime):
        published_at = at if at.tzinfo else at.replace(tzinfo=timezone.utc)
    elif at:
        try:
            published_at = datetime.fromisoformat(str(at))
        except (ValueError, TypeError):
            pass

    review = RawReview(
        source_platform="play_store",
        source_url=None,  # Play Store reviews don't have direct URLs
        source_post_id=raw.get("reviewId"),
        review_text=scrub_pii_from_text(raw.get("content") or ""),
        rating=int(raw["score"]) if raw.get("score") is not None else None,
        upvotes=int(raw.get("thumbsUpCount", 0)),
        author_hash=anonymize_author(author_raw),
        published_at=published_at,
    )
    return review


def normalize_twitter(raw: dict) -> RawReview:
    """
    Normalize a Tweepy tweet dict into a RawReview.

    Expected raw keys:
        id, text, author_id, username, created_at, public_metrics, url
    """
    author_raw = str(raw.get("username") or raw.get("author_id") or "[unknown]")
    created_at = raw.get("created_at")
    published_at = None
    if isinstance(created_at, datetime):
        published_at = created_at if created_at.tzinfo else created_at.replace(tzinfo=timezone.utc)
    elif created_at:
        try:
            published_at = datetime.fromisoformat(str(created_at))
        except (ValueError, TypeError):
            pass

    metrics = raw.get("public_metrics", {})

    review = RawReview(
        source_platform="twitter",
        source_url=raw.get("url"),
        source_post_id=str(raw.get("id", "")),
        review_text=scrub_pii_from_text(raw.get("text") or ""),
        upvotes=int(metrics.get("like_count", 0)),
        comment_count=int(metrics.get("reply_count", 0)),
        author_hash=anonymize_author(author_raw),
        published_at=published_at,
    )
    return review


def normalize_spotify_forum(raw: dict) -> RawReview:
    """
    Normalize a scraped Spotify Community Forum post into a RawReview.

    Expected raw keys:
        post_id, url, title, body, author, kudos_count, replies, published_at
    """
    author_raw = str(raw.get("author") or "[anonymous]")
    published_str = raw.get("published_at")
    published_at = None
    if published_str:
        try:
            published_at = datetime.fromisoformat(str(published_str))
            if published_at.tzinfo is None:
                published_at = published_at.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            pass

    review = RawReview(
        source_platform="spotify_community",
        source_url=raw.get("url"),
        source_post_id=str(raw.get("post_id", "")),
        review_text=scrub_pii_from_text(raw.get("body") or ""),
        review_title=raw.get("title"),
        upvotes=int(raw.get("kudos_count", 0)),
        comment_count=int(raw.get("replies", 0)),
        author_hash=anonymize_author(author_raw),
        published_at=published_at,
    )
    return review


# ── Source Router ───────────────────────────────────────────────────────────

def normalize_youtube(raw: dict) -> RawReview:
    """
    Normalize a YouTube comment dict into a RawReview.

    Expected raw keys:
        id, video_id, video_title, video_url, channel, text,
        author, like_count, reply_count, published_at
    """
    author_raw = str(raw.get("author") or "[anonymous]")
    published_str = raw.get("published_at")
    published_at = None
    if published_str:
        try:
            published_at = datetime.fromisoformat(str(published_str).replace("Z", "+00:00"))
        except (ValueError, TypeError):
            pass

    video_title = raw.get("video_title", "")
    video_url = raw.get("video_url", "")
    comment_id = raw.get("id", "")

    review = RawReview(
        source_platform="youtube",
        source_url=f"{video_url}&lc={comment_id}" if comment_id else video_url,
        source_post_id=comment_id,
        review_text=scrub_pii_from_text(raw.get("text") or ""),
        review_title=video_title,
        upvotes=int(raw.get("like_count", 0)),
        comment_count=int(raw.get("reply_count", 0)),
        author_hash=anonymize_author(author_raw),
        published_at=published_at,
    )
    return review


# ── Source Router ───────────────────────────────────────────────────────────

NORMALIZERS = {
    "reddit": normalize_reddit,
    "app_store": normalize_app_store,
    "play_store": normalize_play_store,
    "twitter": normalize_twitter,
    "spotify_community": normalize_spotify_forum,
    "youtube": normalize_youtube,
}


def normalize(source_platform: str, raw: dict) -> RawReview:
    """
    Route a raw dict to the correct platform-specific normalizer.

    Args:
        source_platform: One of the 5 supported platform identifiers.
        raw: The raw data dict returned by the platform scraper.

    Returns:
        A fully populated RawReview instance.

    Raises:
        ValueError: If the source_platform is not recognized.
    """
    normalizer = NORMALIZERS.get(source_platform)
    if not normalizer:
        raise ValueError(
            f"Unknown source platform: '{source_platform}'. "
            f"Supported: {list(NORMALIZERS.keys())}"
        )
    return normalizer(raw)
