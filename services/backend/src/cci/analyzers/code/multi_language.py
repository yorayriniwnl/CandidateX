"""Multi-language structural code analyzer for TypeScript/JS, Go, Java, and C/C++."""

import re

from cci.domain.contracts import EvidenceInput
from cci.domain.evidence_families import build_evidence_family_identity
from cci.domain.enums import CapabilityKey, SourceFamily
from cci.domain.signal_rules import signal_rule_fields


def analyze_typescript_javascript(
    content: str,
    file_path: str,
    repo_url: str,
    commit_sha: str,
    extractor_version: str = "1.0.0",
) -> list[EvidenceInput]:
    """Analyzes TypeScript and JavaScript source code for routes, async patterns, and interfaces."""
    evidence: list[EvidenceInput] = []
    lines = content.split("\n")

    for idx, line in enumerate(lines, start=1):
        trimmed = line.strip()

        # 1. Express / Next.js / Router endpoints
        route_match = re.search(
            r'\b(app|router)\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']',
            trimmed,
        )
        if route_match:
            router_obj, method, path = route_match.groups()
            route_suffix = trimmed[route_match.end() :]
            named_function = re.match(
                r"\s*,\s*(?:async\s+)?function\s+([A-Za-z_$][\w$]*)",
                route_suffix,
            )
            handler_reference = re.match(
                r"\s*,\s*([A-Za-z_$][\w$]*)\s*(?=,|\))",
                route_suffix,
            )
            source_construct = (
                named_function.group(1)
                if named_function
                else handler_reference.group(1)
                if handler_reference
                else "inline_handler"
                if "=>" in route_suffix
                else "route_registration"
            )
            identity = build_evidence_family_identity(
                source_family=SourceFamily.GITHUB,
                cluster_id=repo_url,
                capability=CapabilityKey.BACKEND_ENGINEERING,
                fact_domain="route",
                subject=f"{method.upper()}|{path}|{source_construct}",
            )
            evidence.append(
                EvidenceInput(
                    **signal_rule_fields("candidatex.code.typescript.api_route"),
                    source_family=SourceFamily.GITHUB,
                    source_locator=repo_url,
                    immutable_revision=commit_sha,
                    artifact_path=file_path,
                    symbol_or_line=f"Line {idx}: {router_obj}.{method}('{path}')",
                    target_capability=CapabilityKey.BACKEND_ENGINEERING,
                    technical_signal_strength=78.0,
                    is_positive_support=True,
                    raw_support_text=f"API Route handler in {file_path}:\n{trimmed}",
                    extractor_version=extractor_version,
                    evidence_family_id=identity.evidence_family_id,
                    observation_type="route:typescript_registration",
                    evidence_family_basis=identity.basis,
                )
            )

        # 2. Async / Await patterns
        if re.search(r"\basync\s+(function|\([^)]*\)|[a-zA-Z0-9_]+\s*\()", trimmed):
            evidence.append(
                EvidenceInput(
                    **signal_rule_fields("candidatex.code.typescript.async_handler"),
                    source_family=SourceFamily.GITHUB,
                    source_locator=repo_url,
                    immutable_revision=commit_sha,
                    artifact_path=file_path,
                    symbol_or_line=f"Line {idx}: async function",
                    target_capability=CapabilityKey.FRONTEND_ENGINEERING
                    if file_path.endswith((".tsx", ".jsx"))
                    else CapabilityKey.BACKEND_ENGINEERING,
                    technical_signal_strength=74.0,
                    is_positive_support=True,
                    raw_support_text=f"Asynchronous function handler:\n{trimmed}",
                    extractor_version=extractor_version,
                )
            )

        # 3. Zod / Schema validation
        if re.search(r"\bz\.object\s*\(", trimmed):
            evidence.append(
                EvidenceInput(
                    **signal_rule_fields("candidatex.code.typescript.zod_schema"),
                    source_family=SourceFamily.GITHUB,
                    source_locator=repo_url,
                    immutable_revision=commit_sha,
                    artifact_path=file_path,
                    symbol_or_line=f"Line {idx}: z.object(...)",
                    target_capability=CapabilityKey.SOFTWARE_ARCHITECTURE,
                    technical_signal_strength=80.0,
                    is_positive_support=True,
                    raw_support_text=f"Zod schema validation model in {file_path}:\n{trimmed}",
                    extractor_version=extractor_version,
                )
            )

        # 4. Error handling
        if re.search(r"\btry\s*\{", trimmed):
            evidence.append(
                EvidenceInput(
                    **signal_rule_fields("candidatex.code.typescript.try_catch"),
                    source_family=SourceFamily.GITHUB,
                    source_locator=repo_url,
                    immutable_revision=commit_sha,
                    artifact_path=file_path,
                    symbol_or_line=f"Line {idx}: try/catch",
                    target_capability=CapabilityKey.TESTING_QUALITY,
                    technical_signal_strength=70.0,
                    is_positive_support=True,
                    raw_support_text=f"Structured error handling block:\n{trimmed}",
                    extractor_version=extractor_version,
                )
            )

    return evidence


def analyze_go_source(
    content: str,
    file_path: str,
    repo_url: str,
    commit_sha: str,
    extractor_version: str = "1.0.0",
) -> list[EvidenceInput]:
    """Analyzes Go source code for HTTP handlers, concurrency, and error handling."""
    evidence: list[EvidenceInput] = []
    lines = content.split("\n")

    for idx, line in enumerate(lines, start=1):
        trimmed = line.strip()

        # 1. HTTP routes (net/http, Gin, Chi)
        if re.search(
            r'\b(HandleFunc|\.GET|\.POST|\.PUT|\.DELETE)\s*\(\s*["\']([^"\']+)["\']',
            trimmed,
        ):
            evidence.append(
                EvidenceInput(
                    **signal_rule_fields("candidatex.code.go.http_route"),
                    source_family=SourceFamily.GITHUB,
                    source_locator=repo_url,
                    immutable_revision=commit_sha,
                    artifact_path=file_path,
                    symbol_or_line=f"Line {idx}: HTTP Handler",
                    target_capability=CapabilityKey.BACKEND_ENGINEERING,
                    technical_signal_strength=82.0,
                    is_positive_support=True,
                    raw_support_text=f"Go HTTP route registration in {file_path}:\n{trimmed}",
                    extractor_version=extractor_version,
                )
            )

        # 2. Goroutines & Concurrency
        if re.search(r"\bgo\s+func\(|\bmake\s*\(\s*chan\b", trimmed):
            evidence.append(
                EvidenceInput(
                    **signal_rule_fields("candidatex.code.go.goroutine_channel"),
                    source_family=SourceFamily.GITHUB,
                    source_locator=repo_url,
                    immutable_revision=commit_sha,
                    artifact_path=file_path,
                    symbol_or_line=f"Line {idx}: Concurrency Goroutine/Channel",
                    target_capability=CapabilityKey.BACKEND_ENGINEERING,
                    technical_signal_strength=85.0,
                    is_positive_support=True,
                    raw_support_text=f"Concurrent goroutine / channel workflow in {file_path}:\n{trimmed}",
                    extractor_version=extractor_version,
                )
            )

        # 3. Explicit error handling (if err != nil)
        if "if err != nil" in trimmed:
            evidence.append(
                EvidenceInput(
                    **signal_rule_fields("candidatex.code.go.error_guard"),
                    source_family=SourceFamily.GITHUB,
                    source_locator=repo_url,
                    immutable_revision=commit_sha,
                    artifact_path=file_path,
                    symbol_or_line=f"Line {idx}: if err != nil",
                    target_capability=CapabilityKey.TESTING_QUALITY,
                    technical_signal_strength=72.0,
                    is_positive_support=True,
                    raw_support_text=f"Explicit error propagation check:\n{trimmed}",
                    extractor_version=extractor_version,
                )
            )

    return evidence


def analyze_java_source(
    content: str,
    file_path: str,
    repo_url: str,
    commit_sha: str,
    extractor_version: str = "1.0.0",
) -> list[EvidenceInput]:
    """Analyzes Java source code for Spring MVC annotations and service boundaries."""
    evidence: list[EvidenceInput] = []
    lines = content.split("\n")

    for idx, line in enumerate(lines, start=1):
        trimmed = line.strip()

        # Spring RestController / Endpoints
        if any(
            ann in trimmed
            for ann in (
                "@GetMapping",
                "@PostMapping",
                "@PutMapping",
                "@DeleteMapping",
                "@RequestMapping",
            )
        ):
            evidence.append(
                EvidenceInput(
                    **signal_rule_fields("candidatex.code.java.spring_endpoint"),
                    source_family=SourceFamily.GITHUB,
                    source_locator=repo_url,
                    immutable_revision=commit_sha,
                    artifact_path=file_path,
                    symbol_or_line=f"Line {idx}: Spring Endpoint",
                    target_capability=CapabilityKey.BACKEND_ENGINEERING,
                    technical_signal_strength=80.0,
                    is_positive_support=True,
                    raw_support_text=f"Spring REST endpoint annotation in {file_path}:\n{trimmed}",
                    extractor_version=extractor_version,
                )
            )

        # Architectural service / repository annotations
        if any(ann in trimmed for ann in ("@Service", "@Repository", "@Component")):
            evidence.append(
                EvidenceInput(
                    **signal_rule_fields("candidatex.code.java.spring_component"),
                    source_family=SourceFamily.GITHUB,
                    source_locator=repo_url,
                    immutable_revision=commit_sha,
                    artifact_path=file_path,
                    symbol_or_line=f"Line {idx}: Spring Component",
                    target_capability=CapabilityKey.SOFTWARE_ARCHITECTURE,
                    technical_signal_strength=80.0,
                    is_positive_support=True,
                    raw_support_text=f"Layered Spring component annotation in {file_path}:\n{trimmed}",
                    extractor_version=extractor_version,
                )
            )

    return evidence


def analyze_c_cpp_source(
    content: str,
    file_path: str,
    repo_url: str,
    commit_sha: str,
    extractor_version: str = "1.0.0",
) -> list[EvidenceInput]:
    """Analyzes C/C++ source code for memory management and algorithmic patterns."""
    evidence: list[EvidenceInput] = []
    lines = content.split("\n")

    for idx, line in enumerate(lines, start=1):
        trimmed = line.strip()

        # Smart pointers / RAII
        if any(
            term in trimmed
            for term in (
                "std::unique_ptr",
                "std::shared_ptr",
                "std::make_unique",
                "std::make_shared",
            )
        ):
            evidence.append(
                EvidenceInput(
                    **signal_rule_fields("candidatex.code.cpp.smart_pointer_raii"),
                    source_family=SourceFamily.GITHUB,
                    source_locator=repo_url,
                    immutable_revision=commit_sha,
                    artifact_path=file_path,
                    symbol_or_line=f"Line {idx}: Modern C++ RAII Smart Pointer",
                    target_capability=CapabilityKey.SOFTWARE_ARCHITECTURE,
                    technical_signal_strength=85.0,
                    is_positive_support=True,
                    raw_support_text=f"Modern C++ memory management in {file_path}:\n{trimmed}",
                    extractor_version=extractor_version,
                )
            )

        # Standard algorithms / data structures
        if any(
            term in trimmed
            for term in (
                "std::vector",
                "std::unordered_map",
                "std::sort",
                "std::priority_queue",
            )
        ):
            evidence.append(
                EvidenceInput(
                    **signal_rule_fields("candidatex.code.cpp.stl_algorithm_structure"),
                    source_family=SourceFamily.GITHUB,
                    source_locator=repo_url,
                    immutable_revision=commit_sha,
                    artifact_path=file_path,
                    symbol_or_line=f"Line {idx}: STL Data Structure / Algorithm",
                    target_capability=CapabilityKey.ALGORITHMS_PROBLEM_SOLVING,
                    technical_signal_strength=78.0,
                    is_positive_support=True,
                    raw_support_text=f"Standard Template Library algorithm/structure:\n{trimmed}",
                    extractor_version=extractor_version,
                )
            )

    return evidence
