"""Repository-level engineering fingerprint built only from inspected static artifacts.

The fingerprint is descriptive. It records which engineering practices are visible in the
bounded scan and where they occur. It is not a candidate score and absence is never treated
as proof that a practice is missing from the full repository.
"""

from __future__ import annotations

from collections import defaultdict
import posixpath
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



_SOURCE_EXTENSIONS = (".py", ".ts", ".tsx", ".js", ".jsx")


def _resolve_relative_reference(source_path: str, reference: str, available: set[str]) -> str | None:
    source_dir = posixpath.dirname(source_path)
    reference = reference.split("?", 1)[0].split("#", 1)[0]

    if reference.startswith("."):
        if source_path.endswith(".py"):
            match = re.match(r"^(\.+)(.*)$", reference)
            if not match:
                return None
            dots, tail = match.groups()
            base = source_dir
            for _ in range(max(0, len(dots) - 1)):
                base = posixpath.dirname(base)
            relative = tail.lstrip(".").replace(".", "/")
            stem = posixpath.normpath(posixpath.join(base, relative))
        else:
            stem = posixpath.normpath(posixpath.join(source_dir, reference))
    else:
        return None

    candidates = [stem]
    candidates.extend(stem + ext for ext in _SOURCE_EXTENSIONS)
    candidates.extend(posixpath.join(stem, "index" + ext) for ext in _SOURCE_EXTENSIONS)
    for candidate in candidates:
        normalized = candidate.lstrip("./")
        if normalized in available:
            return normalized
    return None


def _extract_local_references(path: str, text: str) -> list[str]:
    references: list[str] = []
    if path.endswith(".py"):
        for match in re.finditer(r"^\s*from\s+([.][A-Za-z0-9_.]*)\s+import\s+", text, flags=re.MULTILINE):
            references.append(match.group(1))
    elif path.endswith((".ts", ".tsx", ".js", ".jsx")):
        patterns = (
            r"(?:import|export)\s+(?:[\s\S]*?\s+from\s+)?['\"](\.{1,2}/[^'\"]+)['\"]",
            r"require\(\s*['\"](\.{1,2}/[^'\"]+)['\"]\s*\)",
            r"import\(\s*['\"](\.{1,2}/[^'\"]+)['\"]\s*\)",
        )
        for pattern in patterns:
            references.extend(match.group(1) for match in re.finditer(pattern, text))
    return references


def _find_cycles(adjacency: dict[str, set[str]], limit: int = 20) -> list[list[str]]:
    cycles: list[list[str]] = []
    seen_cycles: set[tuple[str, ...]] = set()
    state: dict[str, int] = {}
    stack: list[str] = []

    def canonical_cycle(nodes: list[str]) -> tuple[str, ...]:
        ring = nodes[:-1] if len(nodes) > 1 and nodes[0] == nodes[-1] else nodes
        if not ring:
            return tuple()
        rotations = [tuple(ring[i:] + ring[:i]) for i in range(len(ring))]
        reverse = list(reversed(ring))
        rotations.extend(tuple(reverse[i:] + reverse[:i]) for i in range(len(reverse)))
        return min(rotations)

    def visit(node: str) -> None:
        if len(cycles) >= limit:
            return
        state[node] = 1
        stack.append(node)
        for target in adjacency.get(node, set()):
            if state.get(target, 0) == 0:
                visit(target)
            elif state.get(target) == 1 and target in stack:
                idx = stack.index(target)
                raw = stack[idx:] + [target]
                key = canonical_cycle(raw)
                if key and key not in seen_cycles:
                    seen_cycles.add(key)
                    cycles.append(raw)
        stack.pop()
        state[node] = 2

    for node in adjacency:
        if state.get(node, 0) == 0:
            visit(node)
        if len(cycles) >= limit:
            break
    return cycles


def _module_topology(snapshots: list[dict[str, str]]) -> dict[str, object]:
    sources = {
        item.get("path", ""): item.get("text", "")[:65_536]
        for item in snapshots
        if item.get("category") == "source" and item.get("path", "").endswith(_SOURCE_EXTENSIONS)
    }
    available = set(sources)
    adjacency: dict[str, set[str]] = {path: set() for path in sources}

    for path, text in sources.items():
        for reference in _extract_local_references(path, text):
            target = _resolve_relative_reference(path, reference, available)
            if target and target != path:
                adjacency[path].add(target)

    incoming: dict[str, int] = {path: 0 for path in sources}
    edge_count = 0
    cross_directory_edges = 0
    for source, targets in adjacency.items():
        for target in targets:
            incoming[target] += 1
            edge_count += 1
            if source.split("/", 1)[0] != target.split("/", 1)[0]:
                cross_directory_edges += 1

    # Undirected connected components are useful for spotting disconnected subsystems.
    undirected: dict[str, set[str]] = {path: set() for path in sources}
    for source, targets in adjacency.items():
        for target in targets:
            undirected[source].add(target)
            undirected[target].add(source)

    components = 0
    visited: set[str] = set()
    for node in undirected:
        if node in visited:
            continue
        components += 1
        queue = [node]
        visited.add(node)
        while queue:
            current = queue.pop()
            for neighbor in undirected[current]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

    fan_out = sorted(
        ({"path": path, "edges": len(targets)} for path, targets in adjacency.items() if targets),
        key=lambda item: (-int(item["edges"]), str(item["path"])),
    )
    fan_in = sorted(
        ({"path": path, "edges": count} for path, count in incoming.items() if count),
        key=lambda item: (-int(item["edges"]), str(item["path"])),
    )
    cycles = _find_cycles(adjacency)

    return {
        "nodes": len(sources),
        "edges": edge_count,
        "connected_components": components,
        "cross_directory_edges": cross_directory_edges,
        "cycles_detected": len(cycles),
        "cycles": cycles,
        "highest_fan_out": fan_out[:8],
        "highest_fan_in": fan_in[:8],
        "limitations": (
            "Topology covers only inspected Python/TypeScript/JavaScript relative imports. "
            "Dynamic imports, aliases, generated code, package-level resolution and unscanned files may be absent."
        ),
    }


def build_repository_fingerprint(
    snapshots: Iterable[dict[str, str]],
) -> dict[str, object]:
    """Build a bounded engineering-practice map from already-inspected files."""

    snapshots = list(snapshots)
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
    topology = _module_topology(snapshots)
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
        "module_topology": topology,
        "interpretation": (
            "Descriptive static fingerprint of the bounded inspected file set. "
            "Observed means a concrete file or configuration signal was found; "
            "not observed is not proof of absence from the complete repository."
        ),
    }
