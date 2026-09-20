"""Candidate sources and scan depth classification package."""

from cci.sources.classifier import (
    RepositoryClassification,
    classify_repository_scan_depth,
)

__all__ = [
    "RepositoryClassification",
    "classify_repository_scan_depth",
]
