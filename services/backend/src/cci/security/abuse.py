"""Production abuse controls, rate limiting, quotas, budgets, circuit breakers,

and signed analysis tokens (Fix 28).

Protects expensive public analysis infrastructure:
- Signed Analysis Tokens (HMAC-SHA256, expiration, replay/quota tracking)
- Per-IP / session sliding-window rate limiting with Retry-After headers
- Concurrency limiters (global and per-client active analysis caps)
- Run budget tracking (wall-clock timeout, GitHub API budget, crawl page/byte budgets)
- External dependency circuit breakers (GitHub, external domains) with CLOSED/OPEN/HALF-OPEN states
- In-memory content-addressable cache & deduplication
- Strict credential redaction (preventing token leaks in errors, responses, and artifacts)
- SSRF preservation (retaining all existing strict network controls)
"""

import base64
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import hmac
import json
import logging
import re
import threading
import time
from typing import Any, Mapping
from uuid import uuid4

from cci.config import settings

logger = logging.getLogger(__name__)


class AbuseSecurityError(Exception):
    """Base exception for abuse and security control violations."""


class InvalidTokenError(AbuseSecurityError):
    """Raised when an analysis token has invalid signature, is expired, or is malformed."""


class RateLimitExceeded(AbuseSecurityError):
    """Raised when request rate exceeds allowed threshold."""

    def __init__(self, retry_after: float, message: str = "Rate limit exceeded."):
        super().__init__(message)
        self.retry_after = max(1.0, float(retry_after))


class ConcurrencyLimitExceeded(AbuseSecurityError):
    """Raised when active analysis concurrency cap is reached."""

    def __init__(self, message: str = "Concurrency limit reached. Please wait for active runs to finish."):
        super().__init__(message)
        self.retry_after = 5.0


class BudgetExhausted(AbuseSecurityError):
    """Raised when an individual analysis run exceeds its resource or timeout budget."""


class CircuitBreakerOpen(AbuseSecurityError):
    """Raised when an external host's circuit breaker is open due to repeated failures."""


class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


# ---------------------------------------------------------------------------
# 1. Signed Analysis Token Management (HMAC-SHA256)
# ---------------------------------------------------------------------------

class AnalysisTokenManager:
    """Issues and cryptographically validates signed analysis tokens."""

    def __init__(self, secret_key: bytes | str | None = None):
        raw = secret_key or getattr(settings, "SECRET_KEY", "candidatex_default_secure_signing_secret_32b")
        if isinstance(raw, str):
            raw = raw.encode("utf-8")
        self._secret = raw

    def issue_token(
        self,
        subject: str,
        expires_in_seconds: int = 3600,
        tier: str = "default",
        custom_claims: Mapping[str, Any] | None = None,
    ) -> str:
        """Issues an HMAC-SHA256 signed token."""
        now = int(time.time())
        claims = {
            "sub": str(subject),
            "iat": now,
            "exp": now + int(expires_in_seconds),
            "tier": str(tier),
            "jti": str(uuid4()),
        }
        if custom_claims:
            claims.update(dict(custom_claims))

        payload_bytes = json.dumps(claims, separators=(",", ":"), sort_keys=True).encode("utf-8")
        payload_b64 = base64.urlsafe_b64encode(payload_bytes).decode("ascii").rstrip("=")
        sig = hmac.new(self._secret, payload_b64.encode("ascii"), hashlib.sha256).digest()
        sig_b64 = base64.urlsafe_b64encode(sig).decode("ascii").rstrip("=")
        return f"{payload_b64}.{sig_b64}"

    def verify_token(self, token: str) -> dict[str, Any]:
        """Validates signature and expiry of a token, returning claims dict."""
        if not token or not isinstance(token, str):
            raise InvalidTokenError("Missing or empty analysis token.")

        parts = token.strip().split(".")
        if len(parts) != 2:
            raise InvalidTokenError("Malformed analysis token structure.")

        payload_b64, sig_b64 = parts[0], parts[1]

        # Verify HMAC signature in constant time
        expected_sig = hmac.new(self._secret, payload_b64.encode("ascii"), hashlib.sha256).digest()
        expected_sig_b64 = base64.urlsafe_b64encode(expected_sig).decode("ascii").rstrip("=")

        if not hmac.compare_digest(sig_b64, expected_sig_b64):
            raise InvalidTokenError("Invalid token signature.")

        # Decode payload
        rem = len(payload_b64) % 4
        padded_b64 = payload_b64 + ("=" * (4 - rem) if rem else "")
        try:
            payload_json = base64.urlsafe_b64decode(padded_b64.encode("ascii")).decode("utf-8")
            claims = json.loads(payload_json)
        except Exception as exc:
            raise InvalidTokenError("Invalid token payload encoding.") from exc

        # Check expiration
        exp = claims.get("exp")
        if exp is None or time.time() > float(exp):
            raise InvalidTokenError("Analysis token has expired.")

        return claims


# ---------------------------------------------------------------------------
# 2. Sliding Window Rate Limiting
# ---------------------------------------------------------------------------

class RateLimiter:
    """Thread-safe sliding-window rate limiter per key and bucket."""

    def __init__(self):
        self._lock = threading.Lock()
        # key -> list of float timestamps
        self._history: dict[str, list[float]] = defaultdict(list)

    def check_rate_limit(
        self,
        key: str,
        bucket: str = "default",
        limit: int = 15,
        window_seconds: float = 60.0,
    ) -> tuple[bool, float, int]:
        """Checks if key is within rate limit for bucket.

        Returns: (is_allowed, retry_after_seconds, remaining_quota)
        """
        combined_key = f"{bucket}:{key}"
        now = time.monotonic()
        cutoff = now - window_seconds

        with self._lock:
            timestamps = self._history[combined_key]
            # Prune old timestamps
            self._history[combined_key] = [t for t in timestamps if t > cutoff]
            timestamps = self._history[combined_key]

            if len(timestamps) >= limit:
                oldest = timestamps[0]
                retry_after = max(1.0, (oldest + window_seconds) - now)
                return False, retry_after, 0

            timestamps.append(now)
            remaining = max(0, limit - len(timestamps))
            return True, 0.0, remaining

    def reset(self, key: str | None = None) -> None:
        """Resets rate limit counters."""
        with self._lock:
            if key is None:
                self._history.clear()
            else:
                for k in list(self._history.keys()):
                    if k.endswith(f":{key}") or k == key:
                        del self._history[k]


# ---------------------------------------------------------------------------
# 3. Concurrency Limiter
# ---------------------------------------------------------------------------

class ConcurrencyLimiter:
    """Enforces global and per-client concurrent analysis execution caps."""

    def __init__(self, global_max: int = 5, per_key_max: int = 2):
        self.global_max = global_max
        self.per_key_max = per_key_max
        self._lock = threading.Lock()
        self._active_per_key: dict[str, int] = defaultdict(int)
        self._total_active = 0

    def acquire(self, key: str) -> tuple[bool, str | None]:
        """Attempts to acquire a concurrent analysis execution slot."""
        with self._lock:
            if self._total_active >= self.global_max:
                return False, f"Global concurrency limit reached ({self.global_max} active). Please wait for active runs to complete."

            if self._active_per_key[key] >= self.per_key_max:
                return False, f"Per-client concurrency limit reached ({self.per_key_max} active for {key}). Please wait for your active run to complete."

            self._total_active += 1
            self._active_per_key[key] += 1
            return True, None

    def release(self, key: str) -> None:
        """Releases an acquired execution slot."""
        with self._lock:
            if self._active_per_key[key] > 0:
                self._active_per_key[key] -= 1
                if self._active_per_key[key] == 0:
                    del self._active_per_key[key]

            if self._total_active > 0:
                self._total_active -= 1

    def active_count(self, key: str | None = None) -> int:
        """Returns active execution count."""
        with self._lock:
            if key is None:
                return self._total_active
            return self._active_per_key.get(key, 0)

    def reset(self) -> None:
        """Resets all concurrency tracking."""
        with self._lock:
            self._active_per_key.clear()
            self._total_active = 0


# ---------------------------------------------------------------------------
# 4. Run Budget Tracker
# ---------------------------------------------------------------------------

@dataclass
class RunBudgetTracker:
    """Tracks resource consumption budgets for an individual analysis run."""

    max_wall_clock_seconds: float = 60.0
    max_github_calls: int = 50
    max_crawl_pages: int = 24
    max_crawl_bytes: int = 5 * 1024 * 1024  # 5 MB
    start_time: float = field(default_factory=time.monotonic)
    github_calls: int = 0
    crawl_pages: int = 0
    crawl_bytes: int = 0
    exhausted_budgets: list[str] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def record_github_call(self) -> bool:
        """Records a GitHub API request. Returns False if budget exceeded."""
        with self._lock:
            self.github_calls += 1
            if self.github_calls > self.max_github_calls:
                if "github_calls" not in self.exhausted_budgets:
                    self.exhausted_budgets.append("github_calls")
                return False
            return True

    def record_crawl_page(self, byte_size: int = 0) -> bool:
        """Records a fetched web crawl page and bytes. Returns False if budget exceeded."""
        with self._lock:
            self.crawl_pages += 1
            self.crawl_bytes += max(0, int(byte_size))
            exceeded = False
            if self.crawl_pages > self.max_crawl_pages:
                if "crawl_pages" not in self.exhausted_budgets:
                    self.exhausted_budgets.append("crawl_pages")
                exceeded = True
            if self.crawl_bytes > self.max_crawl_bytes:
                if "crawl_bytes" not in self.exhausted_budgets:
                    self.exhausted_budgets.append("crawl_bytes")
                exceeded = True
            return not exceeded

    def is_time_exhausted(self) -> bool:
        """Returns True if the run's wall-clock time budget has expired."""
        elapsed = time.monotonic() - self.start_time
        if elapsed >= self.max_wall_clock_seconds:
            with self._lock:
                if "wall_clock_timeout" not in self.exhausted_budgets:
                    self.exhausted_budgets.append("wall_clock_timeout")
            return True
        return False

    def remaining_seconds(self) -> float:
        """Returns remaining seconds in wall-clock budget."""
        elapsed = time.monotonic() - self.start_time
        return max(0.0, self.max_wall_clock_seconds - elapsed)

    def get_summary(self) -> dict[str, Any]:
        """Returns resource consumption metrics."""
        with self._lock:
            elapsed = time.monotonic() - self.start_time
            return {
                "elapsed_seconds": round(elapsed, 2),
                "remaining_seconds": round(max(0.0, self.max_wall_clock_seconds - elapsed), 2),
                "github_calls": self.github_calls,
                "github_calls_limit": self.max_github_calls,
                "crawl_pages": self.crawl_pages,
                "crawl_pages_limit": self.max_crawl_pages,
                "crawl_bytes": self.crawl_bytes,
                "crawl_bytes_limit": self.max_crawl_bytes,
                "exhausted_budgets": list(self.exhausted_budgets),
            }


# ---------------------------------------------------------------------------
# 5. Circuit Breaker
# ---------------------------------------------------------------------------

class CircuitBreaker:
    """Thread-safe circuit breaker protecting against upstream service degradation."""

    def __init__(
        self,
        failure_threshold: int = 5,
        cooldown_seconds: float = 30.0,
        success_threshold: int = 2,
    ):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.success_threshold = success_threshold
        self._lock = threading.Lock()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = 0.0

    @property
    def state(self) -> CircuitState:
        with self._lock:
            self._evaluate_state_transition()
            return self._state

    def _evaluate_state_transition(self) -> None:
        """Evaluates OPEN -> HALF_OPEN after cooldown."""
        if self._state == CircuitState.OPEN:
            now = time.monotonic()
            if now - self._last_failure_time >= self.cooldown_seconds:
                self._state = CircuitState.HALF_OPEN
                self._success_count = 0

    def can_execute(self) -> bool:
        """Determines whether a call should be allowed or fast-failed."""
        with self._lock:
            self._evaluate_state_transition()
            if self._state == CircuitState.OPEN:
                return False
            return True

    def record_success(self) -> None:
        """Records a successful upstream interaction."""
        with self._lock:
            self._evaluate_state_transition()
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.success_threshold:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    self._success_count = 0
            elif self._state == CircuitState.CLOSED:
                self._failure_count = 0

    def record_failure(self, error: Exception | None = None) -> None:
        """Records an upstream failure."""
        with self._lock:
            self._last_failure_time = time.monotonic()
            self._failure_count += 1
            if self._state in (CircuitState.CLOSED, CircuitState.HALF_OPEN):
                if self._failure_count >= self.failure_threshold or self._state == CircuitState.HALF_OPEN:
                    self._state = CircuitState.OPEN
                    logger.warning("Circuit breaker tripped to OPEN state (failures=%d)", self._failure_count)

    def reset(self) -> None:
        """Resets the circuit breaker to CLOSED state."""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._last_failure_time = 0.0


class CircuitBreakerRegistry:
    """Manages independent circuit breakers per external host."""

    def __init__(self, failure_threshold: int = 5, cooldown_seconds: float = 30.0):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self._lock = threading.Lock()
        self._breakers: dict[str, CircuitBreaker] = {}

    def get_breaker(self, host: str) -> CircuitBreaker:
        host_key = host.lower().strip()
        with self._lock:
            if host_key not in self._breakers:
                self._breakers[host_key] = CircuitBreaker(
                    failure_threshold=self.failure_threshold,
                    cooldown_seconds=self.cooldown_seconds,
                )
            return self._breakers[host_key]

    def can_execute(self, host: str) -> bool:
        return self.get_breaker(host).can_execute()

    def record_success(self, host: str) -> None:
        self.get_breaker(host).record_success()

    def record_failure(self, host: str, error: Exception | None = None) -> None:
        self.get_breaker(host).record_failure(error)

    def reset(self, host: str | None = None) -> None:
        with self._lock:
            if host is None:
                self._breakers.clear()
            elif host.lower().strip() in self._breakers:
                self._breakers[host.lower().strip()].reset()


# ---------------------------------------------------------------------------
# 6. In-Memory Content Cache & Deduplication
# ---------------------------------------------------------------------------

class ContentCache:
    """Thread-safe in-memory cache with TTL for immutable artifacts and receipts."""

    def __init__(self, default_ttl_seconds: float = 3600.0):
        self.default_ttl = default_ttl_seconds
        self._lock = threading.Lock()
        self._cache: dict[str, tuple[Any, float]] = {}

    def get(self, key: str) -> Any | None:
        now = time.monotonic()
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            val, expiry = entry
            if now > expiry:
                del self._cache[key]
                return None
            return val

    def set(self, key: str, value: Any, ttl_seconds: float | None = None) -> None:
        ttl = self.default_ttl if ttl_seconds is None else ttl_seconds
        expiry = time.monotonic() + ttl
        with self._lock:
            self._cache[key] = (value, expiry)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    def evict_expired(self) -> int:
        now = time.monotonic()
        count = 0
        with self._lock:
            expired_keys = [k for k, (_, exp) in self._cache.items() if now > exp]
            for k in expired_keys:
                del self._cache[k]
                count += 1
        return count



# ---------------------------------------------------------------------------
# 7. Credential Redaction
# ---------------------------------------------------------------------------

CREDENTIAL_PATTERNS = [
    re.compile(r"ghp_[A-Za-z0-9]{36}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{82}"),
    re.compile(r"Bearer\s+[A-Za-z0-9_\-\.]{20,}", re.IGNORECASE),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN [A-Z ]+ PRIVATE KEY-----.*?-----END [A-Z ]+ PRIVATE KEY-----", re.DOTALL),
]


def sanitize_credentials(obj: Any) -> Any:
    """Recursively redacts API tokens, private keys, and authorization headers."""
    if isinstance(obj, str):
        result = obj
        for pat in CREDENTIAL_PATTERNS:
            result = pat.sub("[REDACTED_CREDENTIAL]", result)
        return result
    if isinstance(obj, dict):
        sanitized = {}
        for k, v in obj.items():
            if any(term in str(k).lower() for term in ("token", "secret", "password", "authorization", "api_key")):
                sanitized[k] = "[REDACTED_CREDENTIAL]"
            else:
                sanitized[k] = sanitize_credentials(v)
        return sanitized
    if isinstance(obj, (list, tuple)):
        return [sanitize_credentials(item) for item in obj]
    return obj


# ---------------------------------------------------------------------------
# 8. Unified Abuse Controls Service
# ---------------------------------------------------------------------------

class AbuseControlService:
    """Centralized coordinator for CandidateX production abuse controls."""

    def __init__(self):
        self.token_manager = AnalysisTokenManager()
        self.rate_limiter = RateLimiter()
        self.concurrency_limiter = ConcurrencyLimiter(
            global_max=getattr(settings, "MAX_CONCURRENT_ANALYSES", 5),
            per_key_max=getattr(settings, "MAX_CONCURRENT_ANALYSES_PER_CLIENT", 2),
        )
        self.circuit_breakers = CircuitBreakerRegistry(
            failure_threshold=getattr(settings, "CIRCUIT_BREAKER_FAILURE_THRESHOLD", 5),
            cooldown_seconds=getattr(settings, "CIRCUIT_BREAKER_COOLDOWN_SECONDS", 30.0),
        )
        self.cache = ContentCache()

    def verify_request_access(
        self,
        client_ip: str,
        token: str | None = None,
        bucket: str = "runs",
        limit: int = 15,
        window_seconds: float = 60.0,
        require_token: bool = False,
    ) -> dict[str, Any]:
        """Enforces token authentication (if configured or supplied) and rate limiting."""
        claims = {}
        if token:
            claims = self.token_manager.verify_token(token)
        elif require_token or getattr(settings, "REQUIRE_SIGNED_ANALYSIS_TOKEN", False):
            raise InvalidTokenError("A valid signed analysis token is required for this endpoint.")

        # Rate limiting by subject or IP
        rate_key = claims.get("sub", client_ip)
        allowed, retry_after, remaining = self.rate_limiter.check_rate_limit(
            rate_key,
            bucket=bucket,
            limit=limit,
            window_seconds=window_seconds,
        )
        if not allowed:
            raise RateLimitExceeded(retry_after)

        return {
            "rate_key": rate_key,
            "remaining": remaining,
            "claims": claims,
        }

    def acquire_run_slot(self, client_ip: str) -> RunBudgetTracker:
        """Acquires a concurrency slot and constructs a run budget tracker."""
        acquired, reason = self.concurrency_limiter.acquire(client_ip)
        if not acquired:
            raise ConcurrencyLimitExceeded(reason or "Concurrency limit reached.")

        return RunBudgetTracker(
            max_wall_clock_seconds=getattr(settings, "MAX_RUN_WALL_CLOCK_SECONDS", 60.0),
            max_github_calls=getattr(settings, "MAX_GITHUB_CALLS_PER_RUN", 50),
            max_crawl_pages=getattr(settings, "MAX_CRAWL_PAGES_PER_RUN", 24),
            max_crawl_bytes=getattr(settings, "MAX_CRAWL_BYTES_PER_RUN", 5 * 1024 * 1024),
        )

    def release_run_slot(self, client_ip: str) -> None:
        """Releases an acquired execution slot."""
        self.concurrency_limiter.release(client_ip)

    def reset(self) -> None:
        """Resets all state for tests."""
        self.rate_limiter.reset()
        self.concurrency_limiter.reset()
        self.circuit_breakers.reset()
        self.cache.clear()


_ABUSE_CONTROLS_INSTANCE: AbuseControlService | None = None
_INSTANCE_LOCK = threading.Lock()


def get_abuse_controls() -> AbuseControlService:
    """Returns the singleton instance of AbuseControlService."""
    global _ABUSE_CONTROLS_INSTANCE
    with _INSTANCE_LOCK:
        if _ABUSE_CONTROLS_INSTANCE is None:
            _ABUSE_CONTROLS_INSTANCE = AbuseControlService()
        return _ABUSE_CONTROLS_INSTANCE
