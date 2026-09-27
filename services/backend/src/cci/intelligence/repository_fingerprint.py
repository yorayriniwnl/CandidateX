"""Repository-level engineering fingerprint built only from inspected static artifacts.

The fingerprint is descriptive. It records which engineering practices are visible in the
bounded scan and where they occur. It is not a candidate score and absence is never treated
as proof that a practice is missing from the full repository.
"""

from __future__ import annotations

from collections import defaultdict
import re
from typing import Iterable


PRACTICE_PATTERNS: dict[str, tuple[str, ...]] = {
    "input_validation": (
        r"\b(pydantic|zod|joi|validator|validation|sanitize|schema)\b",
    ),
    "authentication_authorization": (
        r"\b(oauth|jwt|authentication|authorization|permission|rbac|acl)\b",
    ),
    "resilience": (
        r"\b(retry|backoff|timeout|circuit breaker|fallback|dead letter)\b",
    ),
    "observability": (
        r"\b(opentelemetry|prometheus|metric|telemetry|tracing|structured log|logger)\b",
    ),
    "concurrency_async": (
        r"\b(async|await|goroutine|channel|semaphore|mutex|worker pool|background task)\b",
    ),
    "caching_messaging": (
        r"\b(redis|cache|kafka|rabbitmq|queue|pubsub|message broker)\b",
    ),
    "database_integrity": (
        r"\b(transaction|migration|foreign key|unique constraint|rollback|isolation)\b",
    ),
    "api_contracts": (
        r"\b(openapi|swagger|graphql|grpc|request model|response model)\b",
    ),
    "testing_discipline": (
        r"\b(pytest|jest|vitest|playwright|cypress|unittest|mock|fixture|assert)\b",
    ),
    "delivery_automation": (
        r"\b(github actions|gitlab-ci|jenkins|continuous integration|ci/cd)\b",
    ),
    "containerization_infrastructure": (
        r"\b(docker|kubernetes|terraform|helm|container|infrastructure as code)\b",
    ),
    "configuration_hygiene": (
        r"\b(environment variable|settings|config|secret|feature flag)\b",
    ),
}

ARCHITECTURE_SEGMENTS = {
    "api",
    "domain",
    "service",
    "services",
    "repository",
    "repositories",
    "adapter",
    "adapters",
    "controller",
    "controllers",
    "model",
    "models",
    "schema",
    "schemas",
    "worker",
    "workers",
    "queue",
    "queues",
    "middleware",
    "security",
    "auth",
    "database",
    "db",
    "infra",
    "infrastructure",
    "tests",
}


def _matches(patterns: tuple[str, ...], text: str) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def build_repository_fingerprint(
    snapshots: Iterable[dict[str, str]],
) -> dict[str, object]:
    """Build a bounded engineering-practice map from already-inspected files."""

    practice_paths: dict[str, list[str]] = defaultdict(list)
    boundary_paths: dict[str, list[str]] = defaultdict(list)
    hotspots: list[dict[str, object]] = []
    scanned = 0

    for item in snapshots:
        path = item.get("path", "")
        category = item.get("category", "other")
        text = item.get("text", "")[:65_536]
        if not path:
            continue
        scanned += 1
        combined = f"{path}\n{text}"
        families: list[str] = []

        for practice, patterns in PRACTICE_PATTERNS.items():
            if _matches(patterns, combined):
                if path not in practice_paths[practice]:
                    practice_paths[practice].append(path)
                families.append(practice)

        # Category-level evidence is exact and avoids depending only on textual terms.
        category_practice = {
            "tests": "testing_discipline",
            "ci": "delivery_automation",
            "infra": "containerization_infrastructure",
            "openapi": "api_contracts",
            "database": "database_integrity",
        }.get(category)
        if category_practice:
            if path not in practice_paths[category_practice]:
                practice_paths[category_practice].append(path)
            if category_practice not in families:
                families.append(category_practice)

        parts = [part.lower() for part in re.split(r"[/\\]+", path)]
        for part in parts:
            if part in ARCHITECTURE_SEGMENTS and path not in boundary_paths[part]:
                boundary_paths[part].append(path)

        if families:
            hotspots.append(
                {
                    "path": path,
                    "signal_family_count": len(set(families)),
                    "signal_families": sorted(set(families)),
                }
            )

    observed = [
        {
            "name": name,
            "status": "observed_in_scan",
            "paths": paths[:8],
            "occurrence_files": len(paths),
        }
        for name, paths in sorted(practice_paths.items())
        if paths
    ]
    missing = [
        name for name in PRACTICE_PATTERNS if not practice_paths.get(name)
    ]
    boundaries = [
        {"name": name, "paths": paths[:8], "occurrence_files": len(paths)}
        for name, paths in sorted(boundary_paths.items())
        if paths
    ]
    hotspots.sort(key=lambda item: (-int(item["signal_family_count"]), str(item["path"])))

    observed_count = len(observed)
    possible_count = len(PRACTICE_PATTERNS)
    return {
        "files_considered": scanned,
        "practice_breadth": {
            "observed": observed_count,
            "possible": possible_count,
            "ratio": round(observed_count / possible_count, 3) if possible_count else 0.0,
        },
        "observed_practices": observed,
        "not_observed_in_bounded_scan": missing,
        "architecture_boundaries": boundaries,
        "signal_hotspots": hotspots[:12],
        "interpretation": (
            "Descriptive static fingerprint of the bounded inspected file set. "
            "Observed means a concrete file or configuration signal was found; "
            "not observed is not proof of absence from the complete repository."
        ),
    }
