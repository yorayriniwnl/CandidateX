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
        r"\b(pydantic|zod|joi|validate|validator|validation|sanitize|schema)\b",
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


REVIEW_TARGET_PATTERNS: dict[str, dict[str, object]] = {
    "dynamic_code_execution": {
        "severity": "high",
        "patterns": (
            r"\beval\s*\(",
            r"\bexec\s*\(",
            r"\bos\.system\s*\(",
            r"\bsubprocess\.(?:run|Popen|call)\s*\([^\n]*shell\s*=\s*True",
            r"\bchild_process\.(?:exec|execSync)\s*\(",
        ),
        "why": "Dynamic command or code execution deserves manual review for injection and trust-boundary handling.",
    },
    "permissive_cors": {
        "severity": "medium",
        "patterns": (
            r"allow_origins\s*=\s*\[\s*['\"]\*['\"]\s*\]",
            r"access-control-allow-origin['\"]?\s*[:,=]\s*['\"]\*['\"]",
            r"\bcors\s*\(\s*\{\s*origin\s*:\s*['\"]\*['\"]",
        ),
        "why": "Wildcard cross-origin access can be valid for public APIs but should be an explicit deployment decision.",
    },
    "tls_verification_disabled": {
        "severity": "high",
        "patterns": (
            r"verify\s*=\s*False",
            r"rejectUnauthorized\s*:\s*false",
            r"NODE_TLS_REJECT_UNAUTHORIZED\s*=\s*['\"]?0",
        ),
        "why": "Disabling certificate verification weakens transport authenticity and should be justified.",
    },
    "raw_sql_construction": {
        "severity": "medium",
        "patterns": (
            r"(?:execute|query)\s*\(\s*f['\"]",
            r"(?:execute|query)\s*\(\s*['\"][^'\"]*%s[^'\"]*['\"]\s*%",
            r"(?:execute|query)\s*\(\s*['\"][^'\"]*\+\s*[A-Za-z_]",
        ),
        "why": "String-built SQL deserves review for parameterization and injection resistance.",
    },
    "broad_exception_swallow": {
        "severity": "low",
        "patterns": (
            r"except\s+Exception\s*:\s*(?:pass|continue)?",
            r"except\s*:\s*(?:pass|continue)?",
            r"catch\s*\([^)]*\)\s*\{\s*\}",
        ),
        "why": "Broad or empty exception handling can hide operational failures and complicate diagnosis.",
    },
    "debug_or_dev_mode": {
        "severity": "low",
        "patterns": (
            r"\bDEBUG\s*=\s*True\b",
            r"\bdebug\s*:\s*true\b",
            r"\bapp\.run\s*\([^\n]*debug\s*=\s*True",
        ),
        "why": "Development diagnostics should be reviewed before production deployment.",
    },
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



def _review_targets(snapshots: list[dict[str, str]]) -> dict[str, object]:
    findings: list[dict[str, object]] = []
    severity_rank = {"high": 0, "medium": 1, "low": 2}

    for item in snapshots:
        path = item.get("path", "")
        category = item.get("category", "other")
        text = item.get("text", "")[:65_536]
        if not path or category in {"docs", "other"}:
            continue

        lines = text.splitlines()
        for rule, config in REVIEW_TARGET_PATTERNS.items():
            matched_lines: list[int] = []
            patterns = config["patterns"]
            for line_number, line in enumerate(lines, start=1):
                if any(re.search(pattern, line, flags=re.IGNORECASE) for pattern in patterns):
                    matched_lines.append(line_number)
                    if len(matched_lines) >= 6:
                        break
            if matched_lines:
                findings.append(
                    {
                        "rule": rule,
                        "severity": config["severity"],
                        "path": path,
                        "lines": matched_lines,
                        "why_review": config["why"],
                        "status": "review_target",
                    }
                )

        nonempty = sum(1 for line in lines if line.strip())
        if category == "source" and nonempty >= 700:
            findings.append(
                {
                    "rule": "large_source_module",
                    "severity": "low",
                    "path": path,
                    "lines": [],
                    "why_review": (
                        f"The inspected file contains {nonempty} non-empty lines. "
                        "Large modules can be intentional, but are useful architecture review targets."
                    ),
                    "status": "review_target",
                }
            )

        todo_lines = [
            line_number
            for line_number, line in enumerate(lines, start=1)
            if re.search(r"\b(?:TODO|FIXME|HACK)\b", line)
        ][:8]
        if todo_lines:
            findings.append(
                {
                    "rule": "explicit_technical_debt_marker",
                    "severity": "low",
                    "path": path,
                    "lines": todo_lines,
                    "why_review": "Explicit TODO/FIXME/HACK markers identify declared follow-up work in inspected code.",
                    "status": "review_target",
                }
            )

    findings.sort(
        key=lambda item: (
            severity_rank.get(str(item["severity"]), 9),
            str(item["rule"]),
            str(item["path"]),
        )
    )
    by_severity = {
        severity: sum(1 for finding in findings if finding["severity"] == severity)
        for severity in ("high", "medium", "low")
    }
    return {
        "count": len(findings),
        "by_severity": by_severity,
        "findings": findings[:40],
        "interpretation": (
            "Pattern-based manual review targets from the bounded static scan. "
            "They are not confirmed vulnerabilities, do not reduce capability scores, "
            "and require inspection in context."
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
    review_targets = _review_targets(snapshots)
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
        "review_targets": review_targets,
        "interpretation": (
            "Descriptive static fingerprint of the bounded inspected file set. "
            "Observed means a concrete file or configuration signal was found; "
            "not observed is not proof of absence from the complete repository."
        ),
    }
