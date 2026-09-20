"""Unit tests for URL normalization, deduplication, and classification."""

import pytest
from cci.intake.canonicalizer import (
    classify_url,
    deduplicate_urls,
    normalize_url,
)


def test_url_canonicalization_rules():
    """Verify tracking query removal, trailing slash removal, and .git stripping."""
    # Tracking parameters removed
    url1 = "https://github.com/alice/project1/?utm_source=twitter&utm_medium=social&ref=cv"
    norm1 = normalize_url(url1)
    assert norm1 == "https://github.com/alice/project1"

    # Git suffix stripped
    url2 = "https://github.com/alice/project2.git"
    norm2 = normalize_url(url2)
    assert norm2 == "https://github.com/alice/project2"

    # SSH to HTTPS conversion
    url3 = "git@github.com:alice/project3.git"
    norm3 = normalize_url(url3)
    assert norm3 == "https://github.com/alice/project3"


def test_url_deduplication_preserving_order():
    """Duplicate variants of same URL must be deduplicated into single canonical instance."""
    raw_urls = [
        "https://github.com/alice/repo",
        "https://github.com/alice/repo/",
        "https://github.com/alice/repo.git",
        "https://github.com/alice/repo?utm_campaign=resume",
        "https://alice.dev",
        "https://github.com/alice/repo2",
    ]
    deduped = deduplicate_urls(raw_urls)
    assert len(deduped) == 3
    assert deduped == [
        "https://github.com/alice/repo",
        "https://alice.dev",
        "https://github.com/alice/repo2",
    ]


def test_platform_classification():
    """Verify classification categories."""
    assert classify_url("https://github.com/alice") == "github"
    assert classify_url("https://github.com/alice/fastapi-app") == "github"
    assert classify_url("https://www.linkedin.com/in/alice-smith") == "linkedin"
    assert classify_url("https://leetcode.com/alicedev") == "coding_profile"
    assert classify_url("https://www.kaggle.com/alicedev") == "coding_profile"
    assert classify_url("https://www.credly.com/badges/12345") == "credential"
    assert classify_url("https://alice-portfolio.vercel.app") == "deployment"
    assert classify_url("https://alice-api.fly.dev") == "deployment"
    assert classify_url("https://alice-blog.me.dev") == "portfolio"
