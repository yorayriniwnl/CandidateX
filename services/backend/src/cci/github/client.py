"""Bounded, rate-limit aware GitHub API client strictly operating on supplied URLs."""

import re
from typing import Any, Dict, List, Optional
import httpx

from cci.config import settings


class GitHubRateLimitError(Exception):
    """Raised when GitHub API rate limit is exceeded."""
    pass


class BoundedGitHubClient:
    """Bounded GitHub client strictly prohibited from executing search or identity discovery.
    
    INVARIANTS:
    1. Only accesses supplied owner/repo or user account URLs.
    2. Zero search endpoints are exposed or used.
    3. Handles rate limits, ETags, and bounded timeouts.
    """

    def __init__(
        self,
        token: Optional[str] = None,
        base_url: str = "https://api.github.com",
        timeout_seconds: float = 15.0,
        transport: Optional[httpx.BaseTransport] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.token = token or settings.GITHUB_TOKEN
        self.timeout = timeout_seconds
        self.transport = transport

        self.etag_cache: Dict[str, str] = {}
        self.response_cache: Dict[str, Any] = {}

    def _get_headers(self, url: str) -> Dict[str, str]:
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "CandidateCapabilityIntelligence/1.0",
        }
        if self.token:
            headers["Authorization"] = f"token {self.token}"
        if url in self.etag_cache:
            headers["If-None-Match"] = self.etag_cache[url]
        return headers

    def _request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
        # Enforce search endpoint ban
        if "/search" in endpoint:
            raise ValueError("Forbidden: Candidate identity discovery via search is strictly prohibited.")

        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers(url)

        with httpx.Client(transport=self.transport, timeout=self.timeout) as client:
            resp = client.get(url, headers=headers, params=params)

            if resp.status_code == 304:
                return self.response_cache.get(url, {})

            if resp.status_code == 403 and "rate limit" in resp.text.lower():
                raise GitHubRateLimitError("GitHub API rate limit exceeded.")

            resp.raise_for_status()

            etag = resp.headers.get("ETag")
            if etag:
                self.etag_cache[url] = etag

            data = resp.json()
            self.response_cache[url] = data
            return data

    def get_repository_metadata(self, owner: str, repo: str) -> Dict[str, Any]:
        """Fetches repository metadata for supplied owner and repository name."""
        return self._request(f"/repos/{owner}/{repo}")

    def list_user_repositories(self, username: str) -> List[Dict[str, Any]]:
        """Lists public repositories belonging strictly to candidate-supplied username."""
        return self._request(f"/users/{username}/repos", params={"sort": "updated", "per_page": 50})

    def get_languages(self, owner: str, repo: str) -> Dict[str, int]:
        """Fetches language byte breakdown."""
        return self._request(f"/repos/{owner}/{repo}/languages")

    def get_contributors(self, owner: str, repo: str) -> List[Dict[str, Any]]:
        """Fetches contributor commit statistics."""
        return self._request(f"/repos/{owner}/{repo}/contributors", params={"per_page": 30})

    def get_commits(self, owner: str, repo: str, author: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetches recent commits."""
        params = {"per_page": min(limit, 100)}
        if author:
            params["author"] = author
        return self._request(f"/repos/{owner}/{repo}/commits", params=params)

    def get_pull_requests(self, owner: str, repo: str, state: str = "all", limit: int = 50) -> List[Dict[str, Any]]:
        """Fetches pull requests."""
        return self._request(f"/repos/{owner}/{repo}/pulls", params={"state": state, "per_page": min(limit, 100)})

    def get_issues(self, owner: str, repo: str, state: str = "all", limit: int = 50) -> List[Dict[str, Any]]:
        """Fetches issues."""
        return self._request(f"/repos/{owner}/{repo}/issues", params={"state": state, "per_page": min(limit, 100)})

    def get_releases(self, owner: str, repo: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Fetches releases."""
        return self._request(f"/repos/{owner}/{repo}/releases", params={"per_page": min(limit, 50)})
