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

    # Cloud storage detection
    assert classify_url("https://drive.google.com/file/d/12345/view") == "cloud_storage"
    assert classify_url("https://docs.google.com/document/d/12345/edit") == "cloud_storage"
    assert classify_url("https://dropbox.com/s/12345/file.pdf") == "cloud_storage"
    assert classify_url("https://1drv.ms/b/s!12345") == "cloud_storage"
    assert classify_url("https://mycompany.sharepoint.com/sites/doc.pdf") == "cloud_storage"

    # Fallbacks: generic public link is not claimed as project
    assert classify_url("https://example.com/some/article") == "public_link"
    assert classify_url("https://gitlab.com/alice/project") == "project"
    assert classify_url("https://huggingface.co/alice/model") == "project"
    assert classify_url("https://www.npmjs.com/package/my-pkg") == "project"
    assert classify_url("https://bento.me/alicedev") == "portfolio"
    assert classify_url("https://demo.streamlit.app") == "deployment"
    assert classify_url("https://udemy.com/certificate/UC-12345") == "credential"


def test_url_normalization_with_punctuation():
    """Verify that trailing punctuation from sentences/lists is safely stripped."""
    assert normalize_url("https://github.com/alice/repo,") == "https://github.com/alice/repo"
    assert normalize_url("https://github.com/alice/repo.") == "https://github.com/alice/repo"
    assert normalize_url("(https://github.com/alice/repo)") == "https://github.com/alice/repo"
    assert normalize_url("[https://github.com/alice/repo]") == "https://github.com/alice/repo"
    assert normalize_url("https://github.com/alice/repo;") == "https://github.com/alice/repo"
    assert normalize_url("https://github.com/alice/repo!") == "https://github.com/alice/repo"
    assert normalize_url("'https://github.com/alice/repo'") == "https://github.com/alice/repo"


def test_url_normalization_modern_tlds():
    """Verify that scheme-less URLs on modern developer TLDs are normalized to HTTPS."""
    assert normalize_url("huggingface.co/spaces/demo") == "https://huggingface.co/spaces/demo"
    assert normalize_url("alice.tech/portfolio") == "https://alice.tech/portfolio"
    assert normalize_url("mysite.xyz") == "https://mysite.xyz"
    assert normalize_url("notion.so/alice/project") == "https://notion.so/alice/project"
    assert normalize_url("bit.ly/my-portfolio") == "https://bit.ly/my-portfolio"
    assert normalize_url("linktr.ee/alice") == "https://linktr.ee/alice"
    assert normalize_url("dev.to/alice") == "https://dev.to/alice"
    assert normalize_url("npm.im/my-package") == "https://npm.im/my-package"
