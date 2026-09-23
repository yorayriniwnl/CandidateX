"""Deterministic, transient expectations for observable resume claims."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
import unicodedata
from urllib.parse import urlsplit

from cci.analyzers.code.dependencies import DEPENDENCY_CAPABILITY_MAP
from cci.domain.enums import CapabilityKey
from cci.live.contracts import ResumeIntake


COVERAGE_TYPE = "candidatex.contradiction.coverage_below_claim"
FRAMEWORK_TYPE = "candidatex.contradiction.framework_usage_absent"
DEPLOYMENT_TYPE = "candidatex.contradiction.deployment_project_mismatch"
PERFORMANCE_TYPE = "candidatex.contradiction.performance_claim_mismatch"

_COMPARATORS = {
    "at least": ">=", "no less than": ">=", ">=": ">=", ">": ">",
    "at most": "<=", "no more than": "<=", "<=": "<=", "<": "<",
    "under": "<", "below": "<",
}
_COMPARATOR_PATTERN = r"no less than|no more than|at least|at most|under|below|>=|<=|>|<"
_REPOSITORY_PATTERN = re.compile(r"(?<![\w./-])([a-z0-9][a-z0-9-]{0,38})/([a-z0-9][a-z0-9_.-]{0,99})(?![\w./-])", re.I)
_GITHUB_URL_PATTERN = re.compile(r"https://(?:www\.)?github\.com/[a-z0-9-]+/[a-z0-9_.-]+(?:/[^\s]*)?", re.I)
_URL_PATTERN = re.compile(r"https://[^\s<>]+", re.I)
_COVERAGE_PATTERN = re.compile(
    rf"(?<!\w)(?P<comparator>at least|no less than|>=|>)\s*"
    r"(?P<number>\d+(?:\.\d+)?)\s*%\s*"
    r"(?P<kind>test coverage|line coverage|branch coverage|coverage)\b", re.I,
)
_PERFORMANCE_PATTERN = re.compile(
    rf"(?<!\w)(?P<metric>[a-z][a-z0-9_.-]*)\s+"
    rf"(?P<comparator>{_COMPARATOR_PATTERN})\s+"
    r"(?P<number>\d+(?:\.\d+)?)\s+(?P<unit>[a-z][a-z0-9%/_.-]*)\s+"
    r"technology=(?P<technology>[a-z][a-z0-9_.-]*)"
    r"(?P<context>(?:\s+(?:statistic|workload|environment)=[a-z][a-z0-9_.-]*)*)",
    re.I,
)
_CONTEXT_PATTERN = re.compile(r"(statistic|workload|environment)=([a-z][a-z0-9_.-]*)", re.I)
_PROJECT_ID_PATTERN = re.compile(r"(?<!\w)project=([a-z][a-z0-9_.-]*)\b", re.I)
_USE_PATTERN = re.compile(r"\b(?:use|using|used|built with)\s+([a-z][a-z0-9_.-]*)\b", re.I)


def _normalize(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).split()).casefold()


def normalize_repository_scope(value: str) -> str:
    """Canonical owner/name, discarding URL revision paths."""
    clean = _normalize(value)
    if clean.startswith("https://"):
        parsed = urlsplit(clean)
        if parsed.netloc not in {"github.com", "www.github.com"}:
            raise ValueError("Repository URL must be on GitHub")
        parts = parsed.path.strip("/").split("/")
        if len(parts) < 2:
            raise ValueError("Repository scope requires owner/name")
        clean = "/".join(parts[:2])
    clean = clean.removesuffix(".git")
    if not _REPOSITORY_PATTERN.fullmatch(clean):
        raise ValueError("Repository scope requires owner/name")
    return clean


def make_claim_reference(
    claim_text: str,
    target_capability: CapabilityKey,
    candidate_type: str,
    repository_scope: str | None = None,
) -> str:
    scope = normalize_repository_scope(repository_scope) if repository_scope else ""
    payload = "\0".join((
        "candidatex.claim-reference.v1", _normalize(claim_text),
        target_capability.value, candidate_type, scope,
    )).encode("utf-8")
    return "cr1:" + hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class ObservableClaimExpectation:
    claim_text: str
    claim_reference: str
    candidate_type: str
    target_capability: CapabilityKey
    repository_scope: str | None = None
    deployment_url: str | None = None
    metric_id: str | None = None
    comparator: str | None = None
    threshold: float | None = None
    unit: str | None = None
    technology: str | None = None
    project_identity: str | None = None
    statistic: str | None = None
    workload: str | None = None
    environment: str | None = None


def _expectation(text: str, kind: str, capability: CapabilityKey, scope: str | None, **fields: object) -> ObservableClaimExpectation:
    return ObservableClaimExpectation(
        claim_text=text,
        claim_reference=make_claim_reference(text, capability, kind, scope),
        candidate_type=kind,
        target_capability=capability,
        repository_scope=scope,
        **fields,
    )


def parse_observable_claim(
    text: str,
    *,
    repository_scope: str | None = None,
    deployment_url: str | None = None,
) -> list[ObservableClaimExpectation]:
    """Parse exactly one supported assertion; ambiguity remains unparsed."""
    normalized = _normalize(text)
    if not normalized:
        return []
    try:
        scope = normalize_repository_scope(repository_scope) if repository_scope else None
    except ValueError:
        return []
    matches: list[ObservableClaimExpectation] = []

    coverage = list(_COVERAGE_PATTERN.finditer(normalized))
    if scope and len(coverage) == 1 and len(re.findall(r"\d+(?:\.\d+)?", normalized)) == 1:
        match = coverage[0]
        kind = match.group("kind")
        metric = "line_coverage" if kind == "line coverage" else "branch_coverage" if kind == "branch coverage" else "coverage"
        matches.append(_expectation(text, COVERAGE_TYPE, CapabilityKey.TESTING_QUALITY, scope,
                                    metric_id=metric, comparator=_COMPARATORS[match.group("comparator")],
                                    threshold=float(match.group("number")), unit="%"))

    performance = _PERFORMANCE_PATTERN.fullmatch(normalized)
    if scope and performance:
        match = performance
        technology = match.group("technology")
        capability = DEPENDENCY_CAPABILITY_MAP.get(technology)
        contexts = _CONTEXT_PATTERN.findall(match.group("context"))
        if capability and len({key for key, _ in contexts}) == len(contexts):
            context = dict(contexts)
            matches.append(_expectation(text, PERFORMANCE_TYPE, capability, scope,
                                        metric_id=match.group("metric"),
                                        comparator=_COMPARATORS[match.group("comparator")],
                                        threshold=float(match.group("number")), unit=match.group("unit"),
                                        technology=technology, **context))

    used = list(_USE_PATTERN.finditer(normalized))
    if scope and len(used) == 1:
        technology = used[0].group(1)
        capability = DEPENDENCY_CAPABILITY_MAP.get(technology)
        if capability:
            other_tokens = [token for token in DEPENDENCY_CAPABILITY_MAP
                            if token != technology and re.search(rf"(?<![\w.-]){re.escape(token)}(?![\w.-])", normalized)]
            if not other_tokens:
                matches.append(_expectation(text, FRAMEWORK_TYPE, capability, scope, technology=technology))

    identities = _PROJECT_ID_PATTERN.findall(normalized)
    if deployment_url and len(identities) == 1 and normalized.count(_normalize(deployment_url)) == 1:
        matches.append(_expectation(text, DEPLOYMENT_TYPE, CapabilityKey.DEVOPS_CLOUD, None,
                                    deployment_url=deployment_url, project_identity=identities[0]))

    return matches if len(matches) == 1 else []


def _project_repositories(text: str) -> set[str]:
    urls = _GITHUB_URL_PATTERN.findall(text)
    stripped = _GITHUB_URL_PATTERN.sub(" ", text)
    scopes = set()
    bare_scopes = [
        match.group(0) for match in _REPOSITORY_PATTERN.finditer(stripped)
        if not re.search(r"\d+(?:\.\d+)?\s+$", stripped[:match.start()])
    ]
    for value in [url.rstrip(".,;") for url in urls] + bare_scopes:
        try:
            scope = normalize_repository_scope(value)
        except ValueError:
            continue
        if scope not in {"req/s", "ops/s", "mb/s", "gb/s"}:
            scopes.add(scope)
    return scopes


def build_observable_claim_expectations(intake: ResumeIntake) -> list[ObservableClaimExpectation]:
    """Gather supported declarations without borrowing scope from other claims."""
    results: list[ObservableClaimExpectation] = []
    for project in intake.manifest.project_claims:
        title, description = (str(project.get(key, "")).strip() for key in ("title", "description"))
        project_text = " ".join(part for part in (title, description) if part)
        repositories = _project_repositories(project_text)
        scope = next(iter(repositories)) if len(repositories) == 1 else None
        urls = {_normalize(url.rstrip(".,;")) for url in _URL_PATTERN.findall(project_text)}
        selected = [url for url in intake.manifest.deployment_urls if _normalize(url) in urls]
        deployment = selected[0] if len(selected) == 1 else None
        parsed = []
        for claim_text in (title, description):
            if claim_text:
                parsed.extend(parse_observable_claim(
                    claim_text, repository_scope=scope if len(repositories) == 1 else None,
                    deployment_url=deployment if deployment and _normalize(deployment) in _normalize(claim_text) else None,
                ))
        if deployment and not any(item.candidate_type == DEPLOYMENT_TYPE for item in parsed):
            parsed.extend(parse_observable_claim(project_text, deployment_url=deployment))
        if len(parsed) == 1 and len(repositories) <= 1:
            results.extend(parsed)
    # Skills and experience declarations have no attached project scope or selected URL.
    for text in intake.manifest.claimed_skills:
        results.extend(parse_observable_claim(text))
    for experience in intake.manifest.experience_claims:
        results.extend(parse_observable_claim(str(experience.get("text", ""))))
    return results
