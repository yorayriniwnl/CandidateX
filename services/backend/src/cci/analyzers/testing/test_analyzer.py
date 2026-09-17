"""Static test topology and test artifact analyzer.

INVARIANT: Candidate test suites are NEVER executed.
No test runners, no sub-processes, no assertions executed.
All analysis is strictly static AST/regex inspection of test suites.
"""

import ast
import re

from cci.domain.contracts import EvidenceInput
from cci.domain.enums import CapabilityKey, SourceFamily

EXTRACTOR_VERSION = "1.0.0"


def analyze_python_test_file(
    content: str,
    file_path: str,
    repo_url: str,
    commit_sha: str,
    extractor_version: str = EXTRACTOR_VERSION,
) -> list[EvidenceInput]:
    """Inspects Python test files (pytest/unittest) for test cases, fixtures, mocks, and property testing."""
    evidence: list[EvidenceInput] = []

    try:
        tree = ast.parse(content, filename=file_path)
    except SyntaxError:
        return _regex_fallback_python_test(
            content, file_path, repo_url, commit_sha, extractor_version
        )

    test_funcs = []
    fixtures = []
    parameterized = []
    has_hypothesis = False
    has_mocks = False

    for node in ast.walk(tree):
        # 1. Imports check
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            mod_names = [alias.name for alias in node.names]
            if isinstance(node, ast.ImportFrom) and node.module:
                mod_names.append(node.module)
            mod_str = " ".join(mod_names).lower()
            if "hypothesis" in mod_str:
                has_hypothesis = True
            if any(
                m in mod_str
                for m in ("mock", "unittest.mock", "pytest_mock", "responses", "respx")
            ):
                has_mocks = True

        # 2. Function definitions
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            lineno = getattr(node, "lineno", 1)
            # Test functions
            if node.name.startswith("test_") or node.name.endswith("_test"):
                test_funcs.append((lineno, node.name))

            # Decorator inspection
            for d in node.decorator_list:
                d_str = ast.unparse(d)
                if "fixture" in d_str:
                    fixtures.append((lineno, node.name))
                if "parametrize" in d_str:
                    parameterized.append((lineno, node.name))
                if "given(" in d_str:
                    has_hypothesis = True

    # Build structured evidence based on topology
    if test_funcs:
        # A. Basic unit test suite presence
        evidence.append(
            EvidenceInput(
                source_family=SourceFamily.GITHUB,
                source_locator=repo_url,
                immutable_revision=commit_sha,
                artifact_path=file_path,
                symbol_or_line=f"{file_path}: {len(test_funcs)} test cases",
                target_capability=CapabilityKey.TESTING_QUALITY,
                observed_score=72.0,
                is_positive_support=True,
                raw_support_text=f"Python unit test suite containing {len(test_funcs)} test cases in {file_path}",
                extractor_version=extractor_version,
            )
        )

    # B. Test fixtures / lifecycle management
    if fixtures:
        evidence.append(
            EvidenceInput(
                source_family=SourceFamily.GITHUB,
                source_locator=repo_url,
                immutable_revision=commit_sha,
                artifact_path=file_path,
                symbol_or_line=f"{file_path}: {len(fixtures)} fixtures",
                target_capability=CapabilityKey.TESTING_QUALITY,
                observed_score=80.0,
                is_positive_support=True,
                raw_support_text=f"Structured test fixture architecture with {len(fixtures)} reusable fixtures in {file_path}",
                extractor_version=extractor_version,
            )
        )

    # C. Parameterized / Data-driven testing
    if parameterized:
        evidence.append(
            EvidenceInput(
                source_family=SourceFamily.GITHUB,
                source_locator=repo_url,
                immutable_revision=commit_sha,
                artifact_path=file_path,
                symbol_or_line=f"{file_path}: @pytest.mark.parametrize",
                target_capability=CapabilityKey.TESTING_QUALITY,
                observed_score=84.0,
                is_positive_support=True,
                raw_support_text=f"Parameterized data-driven testing verified across {len(parameterized)} test functions in {file_path}",
                extractor_version=extractor_version,
            )
        )

    # D. Mocking & External Boundary Isolation
    if has_mocks or "unittest.mock" in content or "mocker." in content:
        evidence.append(
            EvidenceInput(
                source_family=SourceFamily.GITHUB,
                source_locator=repo_url,
                immutable_revision=commit_sha,
                artifact_path=file_path,
                symbol_or_line=f"{file_path}: Mocking / Stubbing",
                target_capability=CapabilityKey.TESTING_QUALITY,
                observed_score=85.0,
                is_positive_support=True,
                raw_support_text=f"Isolation of external dependencies and subsystem mocking verified in {file_path}",
                extractor_version=extractor_version,
            )
        )

    # E. Advanced Property-Based Testing
    if has_hypothesis:
        evidence.append(
            EvidenceInput(
                source_family=SourceFamily.GITHUB,
                source_locator=repo_url,
                immutable_revision=commit_sha,
                artifact_path=file_path,
                symbol_or_line=f"{file_path}: Hypothesis Property Testing",
                target_capability=CapabilityKey.TESTING_QUALITY,
                observed_score=92.0,
                is_positive_support=True,
                raw_support_text=f"Advanced property-based / generative testing using Hypothesis in {file_path}",
                extractor_version=extractor_version,
            )
        )

    return evidence


def _regex_fallback_python_test(
    content: str,
    file_path: str,
    repo_url: str,
    commit_sha: str,
    extractor_version: str,
) -> list[EvidenceInput]:
    """Fallback regex extractor for Python test files when AST parse encounters syntax issues."""
    evidence: list[EvidenceInput] = []
    test_funcs = re.findall(r"\bdef\s+(test_[a-zA-Z0-9_]+)\s*\(", content)
    if test_funcs:
        evidence.append(
            EvidenceInput(
                source_family=SourceFamily.GITHUB,
                source_locator=repo_url,
                immutable_revision=commit_sha,
                artifact_path=file_path,
                symbol_or_line=f"{file_path}: {len(test_funcs)} test cases",
                target_capability=CapabilityKey.TESTING_QUALITY,
                observed_score=70.0,
                is_positive_support=True,
                raw_support_text=f"Python test functions identified: {', '.join(test_funcs[:5])}",
                extractor_version=extractor_version,
            )
        )
    return evidence


def analyze_js_ts_test_file(
    content: str,
    file_path: str,
    repo_url: str,
    commit_sha: str,
    extractor_version: str = EXTRACTOR_VERSION,
) -> list[EvidenceInput]:
    """Inspects JavaScript/TypeScript test files (Jest, Vitest, Mocha) for test suites, mocks, and fixtures."""
    evidence: list[EvidenceInput] = []

    it_tests = re.findall(r"\b(it|test)\s*\(\s*['\"`]", content)
    has_mocks = bool(
        re.search(r"\b(jest\.mock|vi\.mock|jest\.fn|vi\.fn|sinon\.stub)\b", content)
    )
    has_lifecycle = bool(
        re.search(r"\b(beforeEach|afterEach|beforeAll|afterAll)\b", content)
    )
    has_supertest = bool(re.search(r"\b(request\(app\)|supertest)\b", content))

    if it_tests:
        evidence.append(
            EvidenceInput(
                source_family=SourceFamily.GITHUB,
                source_locator=repo_url,
                immutable_revision=commit_sha,
                artifact_path=file_path,
                symbol_or_line=f"{file_path}: {len(it_tests)} test cases",
                target_capability=CapabilityKey.TESTING_QUALITY,
                observed_score=72.0,
                is_positive_support=True,
                raw_support_text=f"TypeScript/JavaScript test cases ({len(it_tests)} specifications) in {file_path}",
                extractor_version=extractor_version,
            )
        )

    if has_lifecycle:
        evidence.append(
            EvidenceInput(
                source_family=SourceFamily.GITHUB,
                source_locator=repo_url,
                immutable_revision=commit_sha,
                artifact_path=file_path,
                symbol_or_line=f"{file_path}: Test Lifecycle Hooks",
                target_capability=CapabilityKey.TESTING_QUALITY,
                observed_score=78.0,
                is_positive_support=True,
                raw_support_text=f"Test suite setup/teardown lifecycle management (beforeEach/afterEach) in {file_path}",
                extractor_version=extractor_version,
            )
        )

    if has_mocks:
        evidence.append(
            EvidenceInput(
                source_family=SourceFamily.GITHUB,
                source_locator=repo_url,
                immutable_revision=commit_sha,
                artifact_path=file_path,
                symbol_or_line=f"{file_path}: Jest/Vitest Mocks",
                target_capability=CapabilityKey.TESTING_QUALITY,
                observed_score=84.0,
                is_positive_support=True,
                raw_support_text=f"Mocking and isolation of dependencies (jest.mock / vi.mock) in {file_path}",
                extractor_version=extractor_version,
            )
        )

    if has_supertest:
        evidence.append(
            EvidenceInput(
                source_family=SourceFamily.GITHUB,
                source_locator=repo_url,
                immutable_revision=commit_sha,
                artifact_path=file_path,
                symbol_or_line=f"{file_path}: Integration Supertest",
                target_capability=CapabilityKey.TESTING_QUALITY,
                observed_score=86.0,
                is_positive_support=True,
                raw_support_text=f"End-to-end HTTP integration testing (Supertest) in {file_path}",
                extractor_version=extractor_version,
            )
        )

    return evidence


def analyze_go_test_file(
    content: str,
    file_path: str,
    repo_url: str,
    commit_sha: str,
    extractor_version: str = EXTRACTOR_VERSION,
) -> list[EvidenceInput]:
    """Inspects Go test files for Test functions, subtests (t.Run), and table-driven tests."""
    evidence: list[EvidenceInput] = []

    test_funcs = re.findall(
        r"\bfunc\s+(Test[a-zA-Z0-9_]+)\s*\(\s*([a-zA-Z0-9_]+\s*\*testing\.T)\s*\)",
        content,
    )
    has_subtests = "t.Run(" in content
    has_table_tests = bool(
        re.search(
            r"tests\s*:=\s*\[\]struct\s*\{|testCases\s*:=\s*\[\]struct\s*\{", content
        )
    )

    if test_funcs:
        score = 84.0 if has_table_tests else (80.0 if has_subtests else 74.0)
        desc = (
            "Table-driven Go test suite"
            if has_table_tests
            else ("Go subtest suite (t.Run)" if has_subtests else "Go test suite")
        )
        evidence.append(
            EvidenceInput(
                source_family=SourceFamily.GITHUB,
                source_locator=repo_url,
                immutable_revision=commit_sha,
                artifact_path=file_path,
                symbol_or_line=f"{file_path}: {len(test_funcs)} test functions",
                target_capability=CapabilityKey.TESTING_QUALITY,
                observed_score=score,
                is_positive_support=True,
                raw_support_text=f"{desc} containing {len(test_funcs)} test functions: {', '.join(f[0] for f in test_funcs[:4])}",
                extractor_version=extractor_version,
            )
        )

    return evidence
