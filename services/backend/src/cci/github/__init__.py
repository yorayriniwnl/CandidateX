"""GitHub client package exports."""

from cci.github.client import (
    BoundedGitHubClient,
    GitHubRateLimitError,
)

__all__ = [
    "BoundedGitHubClient",
    "GitHubRateLimitError",
]
