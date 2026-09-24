"""Pure, fail-closed evaluators for pinned contradiction observations."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import json
import math
from pathlib import PurePosixPath
import re
import tomllib
from types import MappingProxyType
from typing import Mapping
import unicodedata
import xml.etree.ElementTree as ET

from cci.contradictions.expectations import (
    COVERAGE_TYPE, DEPLOYMENT_TYPE, FRAMEWORK_TYPE, PERFORMANCE_TYPE,
    ObservableClaimExpectation, _PROJECT_ID_PATTERN, normalize_repository_scope,
)
from cci.domain.contracts import EvidenceInput, NegativeEvidenceDetails, NegativeEvidenceScanScope
from cci.domain.enums import SourceFamily
from cci.domain.signal_rules import signal_rule_fields
from cci.live.scan_inventory import (
    IGNORED_COMPONENTS, SCAN_SCOPE_VERSION, RepositoryScanCompleteness, _lcov_is_parseable,
    eligible_categories,
)


MAX_ARTIFACT_BYTES = 128 * 1024
_SHA = re.compile(r"[0-9a-f]{40}", re.I)
_JS_EXTENSIONS = frozenset({".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts"})
_PY_EXTENSIONS = frozenset({".py"})


@dataclass(frozen=True)
class FrameworkUsageRule:
    source_extensions: frozenset[str]
    source_markers: tuple[str, ...]
    manifest_filenames: frozenset[str]
    package_aliases: frozenset[str]
    source_categories: tuple[str, ...]


def _rule(extensions, markers, manifests, aliases, categories):
    return FrameworkUsageRule(frozenset(extensions), tuple(markers), frozenset(manifests),
                              frozenset(aliases), tuple(categories))


# Marker strings describe import specifiers, not arbitrary words in source text.
FRAMEWORK_USAGE_RULES_V1: Mapping[str, FrameworkUsageRule] = MappingProxyType({
    "fastapi": _rule(_PY_EXTENSIONS, ("fastapi",), ("pyproject.toml", "requirements.txt"),
                     ("fastapi",), ("source:python",)),
    "django": _rule(_PY_EXTENSIONS, ("django",), ("pyproject.toml", "requirements.txt"),
                    ("django",), ("source:python",)),
    "flask": _rule(_PY_EXTENSIONS, ("flask",), ("pyproject.toml", "requirements.txt"),
                   ("flask",), ("source:python",)),
    "express": _rule(_JS_EXTENSIONS, ("express",), ("package.json",),
                     ("express",), ("source:javascript", "source:typescript")),
    "nestjs": _rule(_JS_EXTENSIONS, ("@nestjs/",), ("package.json",),
                    ("@nestjs/core",), ("source:javascript", "source:typescript")),
    "react": _rule(_JS_EXTENSIONS, ("react",), ("package.json",),
                   ("react",), ("source:javascript", "source:typescript")),
    "next": _rule(_JS_EXTENSIONS, ("next/", "next"), ("package.json",),
                  ("next",), ("source:javascript", "source:typescript")),
    "vue": _rule(_JS_EXTENSIONS | {".vue"}, ("vue",), ("package.json",),
                 ("vue",), ("source:javascript", "source:typescript", "source:vue")),
    "angular": _rule(_JS_EXTENSIONS, ("@angular/",), ("package.json",),
                     ("@angular/core",), ("source:javascript", "source:typescript")),
    "svelte": _rule(_JS_EXTENSIONS | {".svelte"}, ("svelte",), ("package.json",),
                    ("svelte",), ("source:javascript", "source:typescript", "source:svelte")),
    "gin": _rule((".go",), ("github.com/gin-gonic/gin",), ("go.mod",),
                 ("github.com/gin-gonic/gin",), ("source:go",)),
    "spring-boot": _rule((".java",), ("org.springframework.boot",), ("pom.xml",),
                         ("org.springframework.boot:spring-boot-*",), ("source:java",)),
})


@dataclass(frozen=True)
class DeploymentProjectIdentity:
    """Identity from an authoritative structured verifier, injected by a caller."""

    status: str
    deployment_url: str
    project_identity: str | None = None
    verifier_identity: str | None = None
    verification_revision: str | None = None
    authoritative: bool = False
    fresh: bool = False


def _safe_bytes(content: object) -> bytes | None:
    return content if isinstance(content, bytes) and len(content) <= MAX_ARTIFACT_BYTES else None


def _safe_artifact_paths(artifacts: Mapping[str, bytes]) -> bool:
    return all(isinstance(path, str) and path and "\\" not in path
               and "\x00" not in path and ":" not in path and not path.startswith("/")
               and all(part not in {"", ".", ".."} for part in path.split("/"))
               for path in artifacts)


def _report_paths(artifacts: Mapping[str, bytes], category: str) -> list[str]:
    return sorted(path for path in artifacts if category in eligible_categories(path))


def _complete_report_path(
    artifacts: Mapping[str, bytes], receipt: RepositoryScanCompleteness, category: str,
) -> str | None:
    if not _safe_artifact_paths(artifacts):
        return None
    counts = receipt.categories.get(category)
    if (not receipt.inventory_complete or receipt.scope_version != SCAN_SCOPE_VERSION
            or counts is None or counts.eligible != 1 or counts.inspected != 1
            or counts.skipped_reasons or counts.completeness != 1.0):
        return None
    paths = _report_paths(artifacts, category)
    if len(paths) != 1 or _safe_bytes(artifacts[paths[0]]) is None:
        return None
    return paths[0]


def parse_cobertura_report(content: bytes) -> dict[str, float] | None:
    """Read only finite root coverage rates; never resolve XML entities."""
    if _safe_bytes(content) is None or re.search(rb"<!\s*(?:DOCTYPE|ENTITY)\b", content, re.I):
        return None
    try:
        root = ET.fromstring(content)
    except ET.ParseError:
        return None
    if root.tag != "coverage":
        return None
    result = {}
    for field, metric in (("line-rate", "line_coverage"), ("branch-rate", "branch_coverage")):
        raw = root.get(field)
        if raw is None:
            continue
        try:
            value = float(raw)
        except ValueError:
            return None
        if not math.isfinite(value) or not 0 <= value <= 1:
            return None
        result[metric] = value * 100
    return result or None


def parse_lcov_report(content: bytes) -> dict[str, float] | None:
    """Sum source-record counters while keeping line and branch rates distinct."""
    if _safe_bytes(content) is None:
        return None
    try:
        report = content.decode("utf-8")
    except UnicodeDecodeError:
        return None
    if not _lcov_is_parseable(report):
        return None
    totals = {key: 0 for key in ("LF", "LH", "BRF", "BRH")}
    current: dict[str, int] = {}
    for raw in report.splitlines():
        line = raw.strip()
        if line == "end_of_record":
            if any(current.get(hit, 0) > current.get(found, 0)
                   for hit, found in (("LH", "LF"), ("BRH", "BRF"))):
                return None
            for field in totals:
                totals[field] += current.get(field, 0)
            current = {}
        else:
            field, separator, value = line.partition(":")
            if separator and field in totals:
                if field in current:
                    return None
                current[field] = int(value)
    result = {}
    for found, hit, metric in (("LF", "LH", "line_coverage"),
                               ("BRF", "BRH", "branch_coverage")):
        if totals[found] > 0:
            result[metric] = 100 * totals[hit] / totals[found]
    return result or None


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError(f"invalid JSON constant: {value}")


def _normalize_token(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).split()).casefold()


def parse_benchmark_report(content: bytes) -> list[dict[str, object]] | None:
    """Parse versioned static measurements without running benchmark code."""
    if _safe_bytes(content) is None:
        return None
    try:
        payload = json.loads(content, object_pairs_hook=_unique_object,
                             parse_constant=_reject_constant)
    except (ValueError, UnicodeDecodeError):
        return None
    if not isinstance(payload, dict) or payload.get("schema_version") != "1.0.0":
        return None
    observations = payload.get("observations")
    if not isinstance(observations, list) or not observations:
        return None
    required = {"metric", "value", "unit", "statistic", "workload", "environment"}
    seen = set()
    for item in observations:
        if not isinstance(item, dict) or set(item) != required:
            return None
        if not all(isinstance(item[key], str) and item[key].strip() and len(item[key]) <= 100
                   for key in required - {"value"}):
            return None
        value = item["value"]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        try:
            numeric = float(value)
        except OverflowError:
            return None
        if not math.isfinite(numeric) or numeric < 0:
            return None
        identity = tuple(_normalize_token(item[key]) for key in
                         ("metric", "statistic", "workload", "environment"))
        if identity in seen:
            return None
        seen.add(identity)
    return observations


def _violates(actual: float, comparator: str | None, threshold: float | None) -> bool:
    if threshold is None or not math.isfinite(threshold):
        return False
    return {
        ">=": actual < threshold, ">": actual <= threshold,
        "<=": actual > threshold, "<": actual >= threshold,
    }.get(comparator, False)


def _details(
    expectation: ObservableClaimExpectation, expected: str, actual: str,
    scope: NegativeEvidenceScanScope, explanation: str, completeness: float,
) -> NegativeEvidenceDetails:
    return NegativeEvidenceDetails(
        claim_reference=expectation.claim_reference,
        candidate_type=expectation.candidate_type,
        expected_observation=expected,
        actual_observation=actual,
        scan_scope=scope,
        required_scan_completeness=1.0,
        observed_scan_completeness=completeness,
        explanation=explanation,
    )


def _artifact_scope(repository_scope: str, revision: str, path: str,
                    category: str) -> NegativeEvidenceScanScope:
    return NegativeEvidenceScanScope(
        scope_kind="artifact", repository_scope=repository_scope,
        pinned_revision=revision, artifact_paths=[path], category=category,
        scope_version=SCAN_SCOPE_VERSION,
    )


def evaluate_coverage_below_claim(
    expectation: ObservableClaimExpectation, repository_url: str, commit_sha: str,
    artifacts: Mapping[str, bytes], completeness: RepositoryScanCompleteness,
) -> EvidenceInput | None:
    path = _complete_report_path(artifacts, completeness, "coverage")
    if path is None or expectation.metric_id not in {"line_coverage", "branch_coverage", "coverage"}:
        return None
    content = artifacts[path]
    metrics = parse_cobertura_report(content) if path.casefold().endswith(".xml") else parse_lcov_report(content)
    if metrics is None:
        return None
    metric = expectation.metric_id
    if metric == "coverage":
        if len(metrics) != 1:
            return None
        metric = next(iter(metrics))
    if metric not in metrics:
        return None
    actual = metrics[metric]
    if not _violates(actual, expectation.comparator, expectation.threshold):
        return None
    observation = f"{path} {metric}={actual:.6g}%"
    details = _details(expectation,
                       f"{metric} {expectation.comparator} {expectation.threshold:g}%",
                       observation, _artifact_scope(expectation.repository_scope or "", commit_sha,
                                                    path, "coverage"),
                       "Pinned coverage report value violates the explicit claim threshold.", 1.0)
    return EvidenceInput(
        source_family=SourceFamily.GITHUB, source_locator=repository_url,
        immutable_revision=commit_sha, artifact_path=path,
        target_capability=expectation.target_capability, technical_signal_strength=70.0,
        **signal_rule_fields("candidatex.contradiction.coverage_below_claim"),
        is_positive_support=False, raw_support_text=observation[:512],
        extractor_version="contradiction-v1", negative_evidence_details=details,
    )


_PY_IMPORT = re.compile(r"^\s*(?:from\s+([A-Za-z_][\w.]*)\s+import\b|import\s+([^#]+))", re.M)
_JS_IMPORT = re.compile(
    r"\b(?:import\s+(?:[^;]*?\s+from\s+)?|export\s+[^;]*?\s+from\s+|"
    r"require\s*\(\s*|import\s*\(\s*)['\"]([^'\"]+)['\"]", re.M,
)
_GO_IMPORT = re.compile(r"^\s*import\s*(?:\((.*?)\)|([^\n]+))", re.M | re.S)
_JAVA_IMPORT = re.compile(r"^\s*import\s+(?:static\s+)?([\w.]+)", re.M)
_JSX = re.compile(r"<>|<\s*[A-Za-z][\w.:-]*(?:\s|/?>)")


def _go_import_paths(content: str) -> set[str]:
    paths = set()
    for match in _GO_IMPORT.finditer(content):
        body = match.group(1) if match.group(1) is not None else match.group(2)
        for line in body.splitlines():
            stripped = line.split("//", 1)[0].strip()
            found = re.fullmatch(r'(?:[\w.]+\s+)?["`]([^"`]+)["`]', stripped)
            if found:
                paths.add(found.group(1))
    return paths


def _source_uses_framework(path: str, content: str, technology: str,
                           rule: FrameworkUsageRule) -> tuple[bool, bool]:
    suffix = PurePosixPath(path).suffix.casefold()
    lower_path = path.casefold().replace("\\", "/")
    if technology == "vue" and suffix == ".vue":
        return True, False
    if technology == "svelte" and suffix == ".svelte":
        return True, False
    if technology == "next" and (
        re.search(r"(?:^|/)next\.config\.(?:js|mjs|cjs|ts|mts|cts)$", lower_path)
        or re.search(r"(?:^|/)(?:app|pages)/(?:[^/]+/)*(?:page|route|layout|_app|_document)\.[cm]?[jt]sx?$", lower_path)
    ):
        return True, False
    if suffix == ".py":
        for match in _PY_IMPORT.finditer(content):
            modules = [match.group(1)] if match.group(1) else re.findall(r"(?:^|,)\s*([A-Za-z_][\w.]*)", match.group(2))
            if any(module.split(".", 1)[0] in rule.source_markers for module in modules):
                return True, False
    elif suffix in _JS_EXTENSIONS:
        uncommented = re.sub(r"/\*.*?\*/|^\s*//[^\n]*$", "", content,
                             flags=re.S | re.M)
        for specifier in _JS_IMPORT.findall(uncommented):
            if any(specifier == marker or specifier.startswith(marker)
                   for marker in rule.source_markers):
                return True, False
        if technology == "react" and suffix in {".jsx", ".tsx"} and _JSX.search(content):
            return False, True
    elif suffix == ".go" and technology == "gin":
        if "github.com/gin-gonic/gin" in _go_import_paths(content):
            return True, False
    elif suffix == ".java" and technology == "spring-boot":
        if any(name.startswith("org.springframework.boot.")
               for name in _JAVA_IMPORT.findall(content)):
            return True, False
    return False, False


def _manifest_declares(path: str, content: str,
                       rule: FrameworkUsageRule) -> bool | None:
    name = PurePosixPath(path).name.casefold()
    if name not in rule.manifest_filenames:
        return False
    if name == "package.json":
        try:
            data = json.loads(content, object_pairs_hook=_unique_object)
        except ValueError:
            return None
        if not isinstance(data, dict):
            return None
        dependency_groups = ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies")
        if any(group in data and (not isinstance(data[group], dict)
                                  or any(not isinstance(version, str)
                                         for version in data[group].values()))
               for group in dependency_groups):
            return None
        return any(isinstance(data.get(group), dict) and alias in data[group]
                   for group in dependency_groups
                   for alias in rule.package_aliases)
    if name == "requirements.txt":
        return any(re.match(r"\s*" + re.escape(alias) + r"(?=\s|[<>=!~;\[]|$)", line, re.I)
                   for alias in rule.package_aliases for line in content.splitlines())
    if name == "pyproject.toml":
        try:
            tomllib.loads(content)
        except tomllib.TOMLDecodeError:
            return None
        return any(re.search(r"(?<![\w.-])" + re.escape(alias) + r"(?=\s|[<>=!~;\[]|$)",
                             line, re.I) for alias in rule.package_aliases
                   for line in content.splitlines() if not line.lstrip().startswith("#"))
    if name == "go.mod":
        return _go_mod_declares(content, rule.package_aliases)
    if name == "pom.xml":
        if re.search(rb"<!\s*(?:DOCTYPE|ENTITY)\b", content.encode(), re.I):
            return None
        try:
            root = ET.fromstring(content)
        except ET.ParseError:
            return None
        for node in root.iter():
            if node.tag.rsplit("}", 1)[-1] != "dependency":
                continue
            fields = {child.tag.rsplit("}", 1)[-1]: (child.text or "").strip()
                      for child in node}
            if fields.get("groupId") == "org.springframework.boot" and fields.get("artifactId", "").startswith("spring-boot-"):
                return True
    return False


_GO_VERSION = re.compile(r"v\d+\.\d+\.\d+(?:[-+][\w.-]+)?$")


def _go_mod_declares(content: str, aliases: frozenset[str]) -> bool | None:
    """Validate the module and direct require forms used for dependency context."""
    module_seen = False
    in_require = False
    present = False
    for raw in content.splitlines():
        line = raw.split("//", 1)[0].strip()
        if not line:
            continue
        if in_require and line == ")":
            in_require = False
            continue
        if in_require:
            parts = line.split()
        elif line == "require (":
            in_require = True
            continue
        elif line.startswith("require "):
            parts = line.split()[1:]
        elif line.startswith("module "):
            parts = line.split()
            if module_seen or len(parts) != 2 or not parts[1]:
                return None
            module_seen = True
            continue
        elif re.fullmatch(r"go\s+\d+\.\d+(?:\.\d+)?|toolchain\s+go\d+\.\d+(?:\.\d+)?", line):
            continue
        else:
            return None
        if len(parts) != 2 or not _GO_VERSION.fullmatch(parts[1]):
            return None
        present |= parts[0] in aliases
    return present if module_seen and not in_require else None


def evaluate_framework_usage_absent(
    expectation: ObservableClaimExpectation, repository_url: str, commit_sha: str,
    artifacts: Mapping[str, bytes], completeness: RepositoryScanCompleteness,
) -> EvidenceInput | None:
    technology = (expectation.technology or "").casefold()
    rule = FRAMEWORK_USAGE_RULES_V1.get(technology)
    if (not rule or not _safe_artifact_paths(artifacts) or not completeness.inventory_complete
            or completeness.scope_version != SCAN_SCOPE_VERSION):
        return None
    categories = rule.source_categories + ("manifest",)
    counts = [completeness.categories.get(category) for category in categories]
    if (any(count is None or count.inspected != count.eligible or count.skipped_reasons for count in counts)
            or sum(count.eligible for count in counts) == 0):
        return None
    observed_counts = Counter()
    manifest_present = False
    registered_file_present = False
    for path, raw in artifacts.items():
        suffix = PurePosixPath(path).suffix.casefold()
        name = PurePosixPath(path).name.casefold()
        path_categories = eligible_categories(path)
        is_source = suffix in rule.source_extensions and any(
            category in path_categories for category in rule.source_categories)
        is_manifest = "manifest" in path_categories
        if not is_source and not is_manifest:
            continue
        if is_source or name in rule.manifest_filenames:
            registered_file_present = True
        content = _safe_bytes(raw)
        if content is None:
            return None
        try:
            decoded = content.decode("utf-8")
        except UnicodeDecodeError:
            return None
        observed_counts.update(category for category in categories if category in path_categories)
        if is_source:
            uses, ambiguous = _source_uses_framework(path, decoded, technology, rule)
            if uses or ambiguous:
                return None
        if name in rule.manifest_filenames:
            declaration = _manifest_declares(path, decoded, rule)
            if declaration is None:
                return None
            manifest_present |= declaration
    scoped_eligible = sum(count.eligible for count in counts)
    # A missing selected file must not turn a partial collection into absence.
    if not registered_file_present or any(observed_counts[category] != count.eligible
           for category, count in zip(categories, counts)):
        return None
    observation = (
        f"No {technology} source usage in {scoped_eligible} eligible inspected files; "
        f"extensions={','.join(sorted(rule.source_extensions))}; "
        f"manifests={','.join(sorted(rule.manifest_filenames))}; "
        f"excluded={','.join(sorted(IGNORED_COMPONENTS))}; "
        f"eligible={scoped_eligible}, inspected={sum(count.inspected for count in counts)}, "
        f"skipped={sum(sum(count.skipped_reasons.values()) for count in counts)}; "
        f"manifest dependency present={str(manifest_present).lower()}"
    )
    details = _details(expectation, f"Repository source uses {technology}", observation,
                       NegativeEvidenceScanScope(
                           scope_kind="repository", repository_scope=expectation.repository_scope,
                           pinned_revision=commit_sha, category="framework_usage",
                           scope_version=SCAN_SCOPE_VERSION,
                       ), "Complete registered source and manifest scan found no framework usage.", 1.0)
    return EvidenceInput(
        source_family=SourceFamily.GITHUB, source_locator=repository_url,
        immutable_revision=commit_sha, target_capability=expectation.target_capability,
        technical_signal_strength=55.0,
        **signal_rule_fields("candidatex.contradiction.framework_usage_absent"),
        is_positive_support=False, raw_support_text=observation[:512],
        extractor_version="contradiction-v1", negative_evidence_details=details,
    )


def evaluate_deployment_project_mismatch(
    expectation: ObservableClaimExpectation, identity: DeploymentProjectIdentity | None,
) -> EvidenceInput | None:
    if (identity is None or identity.status != "VERIFIED" or not identity.fresh
            or not identity.authoritative or not identity.verifier_identity
            or not identity.verification_revision or not identity.project_identity
            or not expectation.project_identity or not expectation.deployment_url
            or identity.deployment_url != expectation.deployment_url):
        return None
    actual_project = _normalize_token(identity.project_identity)
    expected_project = _normalize_token(expectation.project_identity)
    if (not _PROJECT_ID_PATTERN.fullmatch(f"project={actual_project}")
            or not _PROJECT_ID_PATTERN.fullmatch(f"project={expected_project}")
            or actual_project == expected_project):
        return None
    observation = f"{identity.deployment_url} project={actual_project}"
    details = _details(expectation, f"project={expectation.project_identity}", observation,
                       NegativeEvidenceScanScope(
                           scope_kind="deployment", deployment_url=identity.deployment_url,
                           verifier_identity=identity.verifier_identity,
                       ), "Fresh authoritative structured project identity differs from the claim.", 1.0)
    return EvidenceInput(
        source_family=SourceFamily.DEPLOYMENT, source_locator=identity.deployment_url,
        immutable_revision=identity.verification_revision,
        target_capability=expectation.target_capability, technical_signal_strength=85.0,
        **signal_rule_fields("candidatex.contradiction.deployment_project_mismatch"),
        is_positive_support=False, raw_support_text=observation[:512],
        extractor_version="contradiction-v1", negative_evidence_details=details,
    )


def evaluate_performance_claim_mismatch(
    expectation: ObservableClaimExpectation, repository_url: str, commit_sha: str,
    artifacts: Mapping[str, bytes], completeness: RepositoryScanCompleteness,
) -> EvidenceInput | None:
    path = _complete_report_path(artifacts, completeness, "benchmark")
    if path is None:
        return None
    observations = parse_benchmark_report(artifacts[path])
    if observations is None:
        return None
    metric_observations = [item for item in observations
                           if _normalize_token(item["metric"]) == expectation.metric_id]
    if any(getattr(expectation, key) is None
           for key in ("statistic", "workload", "environment")) and len(metric_observations) != 1:
        return None
    matches = [item for item in metric_observations
               if all(getattr(expectation, key) is None
                      or _normalize_token(item[key]) == getattr(expectation, key)
                      for key in ("statistic", "workload", "environment"))]
    if len(matches) != 1:
        return None
    item = matches[0]
    actual_unit = _normalize_token(item["unit"])
    expected_unit = (expectation.unit or "").casefold()
    actual = float(item["value"])
    if actual_unit != expected_unit:
        if actual_unit == "s" and expected_unit == "ms":
            actual *= 1000
        elif actual_unit == "ms" and expected_unit == "s":
            actual /= 1000
        else:
            return None
    if not _violates(actual, expectation.comparator, expectation.threshold):
        return None
    observation = (f"{path} {expectation.metric_id}={actual:.6g} {expected_unit} "
                   f"technology={expectation.technology} statistic={item['statistic']} "
                   f"workload={item['workload']} environment={item['environment']}")
    details = _details(expectation,
                       f"{expectation.metric_id} {expectation.comparator} {expectation.threshold:g} {expected_unit}",
                       observation, _artifact_scope(expectation.repository_scope or "", commit_sha,
                                                    path, "benchmark"),
                       "Pinned benchmark report value violates the explicit claim threshold.", 1.0)
    return EvidenceInput(
        source_family=SourceFamily.GITHUB, source_locator=repository_url,
        immutable_revision=commit_sha, artifact_path=path,
        target_capability=expectation.target_capability, technical_signal_strength=70.0,
        **signal_rule_fields("candidatex.contradiction.performance_claim_mismatch"),
        is_positive_support=False, raw_support_text=observation[:512],
        extractor_version="contradiction-v1", negative_evidence_details=details,
    )


def evaluate_repository_candidates(
    expectations: list[ObservableClaimExpectation], repository_url: str, commit_sha: str,
    artifacts: Mapping[str, bytes], completeness: RepositoryScanCompleteness,
) -> list[EvidenceInput]:
    """Evaluate only claims explicitly bound to this uniquely selected repository."""
    try:
        scope = normalize_repository_scope(repository_url)
    except ValueError:
        return []
    if not _SHA.fullmatch(commit_sha):
        return []
    emitted = []
    for expectation in expectations:
        if expectation.repository_scope != scope:
            continue
        if expectation.candidate_type == COVERAGE_TYPE:
            candidate = evaluate_coverage_below_claim(
                expectation, repository_url, commit_sha, artifacts, completeness)
        elif expectation.candidate_type == FRAMEWORK_TYPE:
            candidate = evaluate_framework_usage_absent(
                expectation, repository_url, commit_sha, artifacts, completeness)
        elif expectation.candidate_type == PERFORMANCE_TYPE:
            candidate = evaluate_performance_claim_mismatch(
                expectation, repository_url, commit_sha, artifacts, completeness)
        else:
            candidate = None  # Deployment identity comes only from its structured verifier.
        if candidate is not None:
            emitted.append(candidate)
    return emitted
