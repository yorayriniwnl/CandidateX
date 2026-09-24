"""Content-addressable caching, conditional HTTP reuse, and cross-tenant authorization isolation (Fix 37).

Provides content-addressable and key-addressable caching for immutable artifacts:
- GitHub: repo + commit SHA
- Public page: canonical URL + content hash/ETag/Last-Modified
- Artifacts: SHA-256
- Preserves original fetched-at timestamps across hits
- Strictly enforces tenant boundaries: private/authenticated assets are namespaced
  by tenant_id, preventing cross-tenant authorization leaks.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import threading
import time
from typing import Any, Mapping
from uuid import UUID


@dataclass
class CachedPublicPage:
    """Cached public web page representation."""

    canonical_url: str
    content_sha256: str
    content_bytes: bytes
    content_type: str = "text/html"
    etag: str | None = None
    last_modified: str | None = None
    fetched_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    receipt: dict[str, Any] = field(default_factory=dict)
    discovered_links: list[str] = field(default_factory=list)
    tenant_id: str | None = None
    expires_at: float = 0.0


@dataclass
class CachedGitHubArchive:
    """Cached immutable GitHub repository archive for a specific commit SHA."""

    repo: str
    commit_sha: str
    content_bytes: bytes
    content_sha256: str
    fetched_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    tenant_id: str | None = None
    expires_at: float = 0.0


@dataclass
class CachedArtifact:
    """Content-addressable artifact indexed strictly by SHA-256."""

    sha256: str
    data: Any
    content_type: str = "application/octet-stream"
    fetched_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    tenant_id: str | None = None
    expires_at: float = 0.0


class ContentCache:
    """Thread-safe content-addressable cache with multi-tenant authorization isolation."""

    def __init__(self, default_ttl_seconds: float = 86400.0):  # 24-hour default retention
        self.default_ttl = default_ttl_seconds
        self._lock = threading.Lock()
        self._cache: dict[str, Any] = {}
        self._expires: dict[str, float] = {}

    def _format_tenant(self, tenant_id: str | UUID | None) -> str | None:
        if tenant_id is None:
            return None
        return str(tenant_id).strip()

    def _scoped_key(
        self,
        namespace: str,
        identifier: str,
        *,
        tenant_id: str | UUID | None = None,
        is_private: bool = False,
    ) -> str:
        tid = self._format_tenant(tenant_id)
        if is_private or tid is not None:
            if not tid:
                raise ValueError("Tenant ID is required for tenant-scoped or private cache operations.")
            return f"tenant:{tid}:{namespace}:{identifier.lower()}"
        return f"public:{namespace}:{identifier.lower()}"

    # -------------------------------------------------------------------------
    # Generic Key-Value Interface (compatibility with abuse.py ContentCache)
    # -------------------------------------------------------------------------

    def get(self, key: str) -> Any | None:
        now = time.monotonic()
        with self._lock:
            if key not in self._cache:
                return None
            exp = self._expires.get(key, 0.0)
            if now > exp:
                self._delete_key_locked(key)
                return None
            return self._cache[key]

    def set(self, key: str, value: Any, ttl_seconds: float | None = None) -> None:
        ttl = self.default_ttl if ttl_seconds is None else ttl_seconds
        exp = time.monotonic() + ttl
        with self._lock:
            self._cache[key] = value
            self._expires[key] = exp

    def _delete_key_locked(self, key: str) -> None:
        self._cache.pop(key, None)
        self._expires.pop(key, None)

    # -------------------------------------------------------------------------
    # 1. GitHub: repo + commit SHA
    # -------------------------------------------------------------------------

    def get_github(
        self,
        repo: str,
        commit_sha: str,
        *,
        tenant_id: str | UUID | None = None,
    ) -> CachedGitHubArchive | None:
        """Retrieves cached GitHub archive for repo + commit SHA.

        Enforces multi-tenant isolation:
        - If tenant_id provided, checks tenant-specific cache first, then public cache.
        - If no tenant_id, checks ONLY public cache (cannot access private tenant entries).
        """
        now = time.monotonic()
        norm_repo = repo.strip().lower()
        norm_sha = commit_sha.strip().lower()
        identifier = f"{norm_repo}:{norm_sha}"

        with self._lock:
            tid = self._format_tenant(tenant_id)
            if tid:
                tenant_key = f"tenant:{tid}:github:{identifier}"
                entry = self._cache.get(tenant_key)
                if entry is not None:
                    if now > self._expires.get(tenant_key, 0.0):
                        self._delete_key_locked(tenant_key)
                    else:
                        return entry

            # Fall back to public cache
            public_key = f"public:github:{identifier}"
            entry = self._cache.get(public_key)
            if entry is not None:
                if now > self._expires.get(public_key, 0.0):
                    self._delete_key_locked(public_key)
                    return None
                return entry

        return None

    def put_github(
        self,
        repo: str,
        commit_sha: str,
        content_bytes: bytes,
        *,
        fetched_at: str | None = None,
        tenant_id: str | UUID | None = None,
        is_private: bool = False,
        ttl_seconds: float | None = None,
    ) -> CachedGitHubArchive:
        """Stores GitHub archive indexed by repo + commit SHA."""
        norm_repo = repo.strip().lower()
        norm_sha = commit_sha.strip().lower()
        identifier = f"{norm_repo}:{norm_sha}"
        key = self._scoped_key("github", identifier, tenant_id=tenant_id, is_private=is_private)
        now_iso = fetched_at or datetime.now(timezone.utc).isoformat()
        ttl = self.default_ttl if ttl_seconds is None else ttl_seconds
        exp = time.monotonic() + ttl

        sha256 = hashlib.sha256(content_bytes).hexdigest()
        entry = CachedGitHubArchive(
            repo=norm_repo,
            commit_sha=norm_sha,
            content_bytes=content_bytes,
            content_sha256=sha256,
            fetched_at=now_iso,
            tenant_id=self._format_tenant(tenant_id),
            expires_at=exp,
        )

        with self._lock:
            self._cache[key] = entry
            self._expires[key] = exp

        return entry

    # -------------------------------------------------------------------------
    # 2. Public Page: Canonical URL + Content Hash / ETag / Last-Modified
    # -------------------------------------------------------------------------

    def get_public_page(
        self,
        canonical_url: str,
        *,
        tenant_id: str | UUID | None = None,
    ) -> CachedPublicPage | None:
        """Retrieves cached public page by canonical URL."""
        now = time.monotonic()
        identifier = canonical_url.strip().lower()

        with self._lock:
            tid = self._format_tenant(tenant_id)
            if tid:
                tenant_key = f"tenant:{tid}:page:{identifier}"
                entry = self._cache.get(tenant_key)
                if entry is not None:
                    if now > self._expires.get(tenant_key, 0.0):
                        self._delete_key_locked(tenant_key)
                    else:
                        return entry

            public_key = f"public:page:{identifier}"
            entry = self._cache.get(public_key)
            if entry is not None:
                if now > self._expires.get(public_key, 0.0):
                    self._delete_key_locked(public_key)
                    return None
                return entry

        return None

    def put_public_page(
        self,
        canonical_url: str,
        content_bytes: bytes,
        receipt: Mapping[str, Any],
        *,
        etag: str | None = None,
        last_modified: str | None = None,
        content_type: str = "text/html",
        discovered_links: list[str] | None = None,
        fetched_at: str | None = None,
        tenant_id: str | UUID | None = None,
        is_private: bool = False,
        ttl_seconds: float | None = None,
    ) -> CachedPublicPage:
        """Stores public page indexed by canonical URL and content hash."""
        identifier = canonical_url.strip().lower()
        key = self._scoped_key("page", identifier, tenant_id=tenant_id, is_private=is_private)
        now_iso = fetched_at or datetime.now(timezone.utc).isoformat()
        ttl = self.default_ttl if ttl_seconds is None else ttl_seconds
        exp = time.monotonic() + ttl

        sha256 = hashlib.sha256(content_bytes).hexdigest()
        entry = CachedPublicPage(
            canonical_url=canonical_url,
            content_sha256=sha256,
            content_bytes=content_bytes,
            content_type=content_type,
            etag=etag,
            last_modified=last_modified,
            fetched_at=now_iso,
            receipt=dict(receipt),
            discovered_links=list(discovered_links or []),
            tenant_id=self._format_tenant(tenant_id),
            expires_at=exp,
        )

        with self._lock:
            self._cache[key] = entry
            self._expires[key] = exp

        return entry

    def get_conditional_headers(
        self,
        canonical_url: str,
        *,
        tenant_id: str | UUID | None = None,
    ) -> dict[str, str]:
        """Returns conditional validation headers (If-None-Match, If-Modified-Since) if cached."""
        cached = self.get_public_page(canonical_url, tenant_id=tenant_id)
        if not cached:
            return {}
        headers: dict[str, str] = {}
        if cached.etag:
            headers["If-None-Match"] = cached.etag
        if cached.last_modified:
            headers["If-Modified-Since"] = cached.last_modified
        return headers

    # -------------------------------------------------------------------------
    # 3. Artifacts: SHA-256
    # -------------------------------------------------------------------------

    def get_artifact(
        self,
        sha256: str,
        *,
        tenant_id: str | UUID | None = None,
    ) -> CachedArtifact | None:
        """Retrieves content-addressable artifact by SHA-256."""
        now = time.monotonic()
        identifier = sha256.strip().lower()

        with self._lock:
            tid = self._format_tenant(tenant_id)
            if tid:
                tenant_key = f"tenant:{tid}:artifact:{identifier}"
                entry = self._cache.get(tenant_key)
                if entry is not None:
                    if now > self._expires.get(tenant_key, 0.0):
                        self._delete_key_locked(tenant_key)
                    else:
                        return entry

            public_key = f"public:artifact:{identifier}"
            entry = self._cache.get(public_key)
            if entry is not None:
                if now > self._expires.get(public_key, 0.0):
                    self._delete_key_locked(public_key)
                    return None
                return entry

        return None

    def put_artifact(
        self,
        sha256: str,
        data: Any,
        content_type: str = "application/octet-stream",
        *,
        fetched_at: str | None = None,
        tenant_id: str | UUID | None = None,
        is_private: bool = False,
        ttl_seconds: float | None = None,
    ) -> CachedArtifact:
        """Stores content-addressable artifact indexed strictly by SHA-256."""
        identifier = sha256.strip().lower()
        key = self._scoped_key("artifact", identifier, tenant_id=tenant_id, is_private=is_private)
        now_iso = fetched_at or datetime.now(timezone.utc).isoformat()
        ttl = self.default_ttl if ttl_seconds is None else ttl_seconds
        exp = time.monotonic() + ttl

        entry = CachedArtifact(
            sha256=identifier,
            data=data,
            content_type=content_type,
            fetched_at=now_iso,
            tenant_id=self._format_tenant(tenant_id),
            expires_at=exp,
        )

        with self._lock:
            self._cache[key] = entry
            self._expires[key] = exp

        return entry

    # -------------------------------------------------------------------------
    # Maintenance & Retention
    # -------------------------------------------------------------------------

    def clear(self) -> None:
        """Clears all cached entries across all tenants and namespaces."""
        with self._lock:
            self._cache.clear()
            self._expires.clear()

    def evict_expired(self) -> int:
        """Evicts all expired entries across all tenants."""
        now = time.monotonic()
        count = 0
        with self._lock:
            expired_keys = [k for k, exp in self._expires.items() if now > exp]
            for k in expired_keys:
                self._delete_key_locked(k)
                count += 1
        return count


# Process-wide content cache singleton
_GLOBAL_CACHE = ContentCache()


def get_content_cache() -> ContentCache:
    """Returns the process-wide content cache singleton."""
    return _GLOBAL_CACHE
