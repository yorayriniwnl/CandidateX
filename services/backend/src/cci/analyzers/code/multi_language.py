"""Multi-language structural code analyzer for TypeScript/JS, Go, Java, and C/C++."""

import re
from typing import List
from cci.domain.contracts import EvidenceInput
from cci.domain.enums import CapabilityKey, SourceFamily


def analyze_typescript_javascript(
    content: str,
    file_path: str,
    repo_url: str,
    commit_sha: str,
    extractor_version: str = "1.0.0",
) -> List[EvidenceInput]:
    """Analyzes TypeScript and JavaScript source code for routes, async patterns, and interfaces."""
    evidence: List[EvidenceInput] = []
    lines = content.split("\n")

    for idx, line in enumerate(lines, start=1):
        trimmed = line.strip()

        # 1. Express / Next.js / Router endpoints
        route_match = re.search(r'\b(app|router)\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']', trimmed)
        if route_match:
            router_obj, method, path = route_match.groups()
            evidence.append(
                EvidenceInput(
                    source_family=SourceFamily.GITHUB,
                    source_locator=repo_url,
                    immutable_revision=commit_sha,
                    artifact_path=file_path,
                    symbol_or_line=f"Line {idx}: {router_obj}.{method}('{path}')",
                    target_capability=CapabilityKey.BACKEND_ENGINEERING,
                    observed_score=78.0,
                    is_positive_support=True,
                    raw_support_text=f"API Route handler in {file_path}:\n{trimmed}",
                    extractor_version=extractor_version,
                )
            )

        # 2. Async / Await patterns
        if re.search(r"\basync\s+(function|\([^)]*\)|[a-zA-Z0-9_]+\s*\()", trimmed):
            evidence.append(
                EvidenceInput(
                    source_family=SourceFamily.GITHUB,
                    source_locator=repo_url,
                    immutable_revision=commit_sha,
                    artifact_path=file_path,
                    symbol_or_line=f"Line {idx}: async function",
                    target_capability=CapabilityKey.FRONTEND_ENGINEERING if file_path.endswith((".tsx", ".jsx")) else CapabilityKey.BACKEND_ENGINEERING,
                    observed_score=74.0,
                    is_positive_support=True,
                    raw_support_text=f"Asynchronous function handler:\n{trimmed}",
                    extractor_version=extractor_version,
                )
            )

        # 3. Zod / Schema validation
        if re.search(r"\bz\.object\s*\(", trimmed):
            evidence.append(
                EvidenceInput(
                    source_family=SourceFamily.GITHUB,
                    source_locator=repo_url,
                    immutable_revision=commit_sha,
                    artifact_path=file_path,
                    symbol_or_line=f"Line {idx}: z.object(...)",
                    target_capability=CapabilityKey.SOFTWARE_ARCHITECTURE,
                    observed_score=80.0,
                    is_positive_support=True,
                    raw_support_text=f"Zod schema validation model in {file_path}:\n{trimmed}",
                    extractor_version=extractor_version,
                )
            )

        # 4. Error handling
        if re.search(r"\btry\s*\{", trimmed):
            evidence.append(
                EvidenceInput(
                    source_family=SourceFamily.GITHUB,
                    source_locator=repo_url,
                    immutable_revision=commit_sha,
                    artifact_path=file_path,
                    symbol_or_line=f"Line {idx}: try/catch",
                    target_capability=CapabilityKey.TESTING_QUALITY,
                    observed_score=70.0,
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
) -> List[EvidenceInput]:
    """Analyzes Go source code for HTTP handlers, concurrency, and error handling."""
    evidence: List[EvidenceInput] = []
    lines = content.split("\n")

    for idx, line in enumerate(lines, start=1):
        trimmed = line.strip()

        # 1. HTTP routes (net/http, Gin, Chi)
        if re.search(r'\b(HandleFunc|\.GET|\.POST|\.PUT|\.DELETE)\s*\(\s*["\']([^"\']+)["\']', trimmed):
            evidence.append(
                EvidenceInput(
                    source_family=SourceFamily.GITHUB,
                    source_locator=repo_url,
                    immutable_revision=commit_sha,
                    artifact_path=file_path,
                    symbol_or_line=f"Line {idx}: HTTP Handler",
                    target_capability=CapabilityKey.BACKEND_ENGINEERING,
                    observed_score=82.0,
                    is_positive_support=True,
                    raw_support_text=f"Go HTTP route registration in {file_path}:\n{trimmed}",
                    extractor_version=extractor_version,
                )
            )

        # 2. Goroutines & Concurrency
        if re.search(r"\bgo\s+func\(|\bmake\s*\(\s*chan\b", trimmed):
            evidence.append(
                EvidenceInput(
                    source_family=SourceFamily.GITHUB,
                    source_locator=repo_url,
                    immutable_revision=commit_sha,
                    artifact_path=file_path,
                    symbol_or_line=f"Line {idx}: Concurrency Goroutine/Channel",
                    target_capability=CapabilityKey.BACKEND_ENGINEERING,
                    observed_score=85.0,
                    is_positive_support=True,
                    raw_support_text=f"Concurrent goroutine / channel workflow in {file_path}:\n{trimmed}",
                    extractor_version=extractor_version,
                )
            )

        # 3. Explicit error handling (if err != nil)
        if "if err != nil" in trimmed:
            evidence.append(
                EvidenceInput(
                    source_family=SourceFamily.GITHUB,
                    source_locator=repo_url,
                    immutable_revision=commit_sha,
                    artifact_path=file_path,
                    symbol_or_line=f"Line {idx}: if err != nil",
                    target_capability=CapabilityKey.TESTING_QUALITY,
                    observed_score=72.0,
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
) -> List[EvidenceInput]:
    """Analyzes Java source code for Spring MVC annotations and service boundaries."""
    evidence: List[EvidenceInput] = []
    lines = content.split("\n")

    for idx, line in enumerate(lines, start=1):
        trimmed = line.strip()

        # Spring RestController / Endpoints
        if any(ann in trimmed for ann in ("@GetMapping", "@PostMapping", "@PutMapping", "@DeleteMapping", "@RequestMapping")):
            evidence.append(
                EvidenceInput(
                    source_family=SourceFamily.GITHUB,
                    source_locator=repo_url,
                    immutable_revision=commit_sha,
                    artifact_path=file_path,
                    symbol_or_line=f"Line {idx}: Spring Endpoint",
                    target_capability=CapabilityKey.BACKEND_ENGINEERING,
                    observed_score=80.0,
                    is_positive_support=True,
                    raw_support_text=f"Spring REST endpoint annotation in {file_path}:\n{trimmed}",
                    extractor_version=extractor_version,
                )
            )

        # Architectural service / repository annotations
        if any(ann in trimmed for ann in ("@Service", "@Repository", "@Component")):
            evidence.append(
                EvidenceInput(
                    source_family=SourceFamily.GITHUB,
                    source_locator=repo_url,
                    immutable_revision=commit_sha,
                    artifact_path=file_path,
                    symbol_or_line=f"Line {idx}: Spring Component",
                    target_capability=CapabilityKey.SOFTWARE_ARCHITECTURE,
                    observed_score=80.0,
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
) -> List[EvidenceInput]:
    """Analyzes C/C++ source code for memory management and algorithmic patterns."""
    evidence: List[EvidenceInput] = []
    lines = content.split("\n")

    for idx, line in enumerate(lines, start=1):
        trimmed = line.strip()

        # Smart pointers / RAII
        if any(term in trimmed for term in ("std::unique_ptr", "std::shared_ptr", "std::make_unique", "std::make_shared")):
            evidence.append(
                EvidenceInput(
                    source_family=SourceFamily.GITHUB,
                    source_locator=repo_url,
                    immutable_revision=commit_sha,
                    artifact_path=file_path,
                    symbol_or_line=f"Line {idx}: Modern C++ RAII Smart Pointer",
                    target_capability=CapabilityKey.SOFTWARE_ARCHITECTURE,
                    observed_score=85.0,
                    is_positive_support=True,
                    raw_support_text=f"Modern C++ memory management in {file_path}:\n{trimmed}",
                    extractor_version=extractor_version,
                )
            )

        # Standard algorithms / data structures
        if any(term in trimmed for term in ("std::vector", "std::unordered_map", "std::sort", "std::priority_queue")):
            evidence.append(
                EvidenceInput(
                    source_family=SourceFamily.GITHUB,
                    source_locator=repo_url,
                    immutable_revision=commit_sha,
                    artifact_path=file_path,
                    symbol_or_line=f"Line {idx}: STL Data Structure / Algorithm",
                    target_capability=CapabilityKey.ALGORITHMS_PROBLEM_SOLVING,
                    observed_score=78.0,
                    is_positive_support=True,
                    raw_support_text=f"Standard Template Library algorithm/structure:\n{trimmed}",
                    extractor_version=extractor_version,
                )
            )

    return evidence
