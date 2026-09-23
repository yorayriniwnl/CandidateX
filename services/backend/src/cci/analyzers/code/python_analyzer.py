"""AST-based static code analyzer for Python repositories."""

import ast

from cci.domain.contracts import EvidenceInput
from cci.domain.evidence_families import (
    build_evidence_family_identity,
    normalize_family_subject,
)
from cci.domain.enums import CapabilityKey, SourceFamily
from cci.analyzers.code.dependencies import DEPENDENCY_CAPABILITY_MAP


class PythonStructuralVisitor(ast.NodeVisitor):
    """Inspects Python AST for architectural and technical patterns."""

    def __init__(
        self,
        source_lines: list[str],
        file_path: str,
        repo_url: str,
        commit_sha: str,
        extractor_version: str,
    ) -> None:
        self.source_lines = source_lines
        self.file_path = file_path
        self.repo_url = repo_url
        self.commit_sha = commit_sha
        self.extractor_version = extractor_version
        self.evidence: list[EvidenceInput] = []

    def _get_snippet(self, node: ast.AST, max_lines: int = 5) -> str:
        """Retrieves raw source lines corresponding to an AST node."""
        start_line = getattr(node, "lineno", 1) - 1
        end_line = getattr(node, "end_lineno", start_line + 1)
        slice_end = min(start_line + max_lines, end_line)
        return "\n".join(self.source_lines[start_line:slice_end])

    def _append_dependency_import(
        self,
        module_name: str,
        node: ast.Import | ast.ImportFrom,
    ) -> None:
        """Emits a bounded observation for a recognized external dependency import."""
        package_name = normalize_family_subject(
            "dependency",
            module_name.split(".", 1)[0],
        )
        capability = DEPENDENCY_CAPABILITY_MAP.get(package_name)
        if capability is None:
            return

        identity = build_evidence_family_identity(
            source_family=SourceFamily.GITHUB,
            cluster_id=self.repo_url,
            capability=capability,
            fact_domain="dependency",
            subject=package_name,
        )
        lineno = getattr(node, "lineno", 1)
        self.evidence.append(
            EvidenceInput(
                source_family=SourceFamily.GITHUB,
                source_locator=self.repo_url,
                immutable_revision=self.commit_sha,
                artifact_path=self.file_path,
                symbol_or_line=f"Line {lineno}: import {module_name}",
                target_capability=capability,
                observed_score=55.0,
                is_positive_support=True,
                raw_support_text=(
                    f"Python import of recognized dependency '{package_name}':\n"
                    f"{self._get_snippet(node)}"
                ),
                extractor_version=self.extractor_version,
                evidence_family_id=identity.evidence_family_id,
                observation_type="dependency:python_import",
                evidence_family_basis=identity.basis,
            )
        )

    def visit_Import(self, node: ast.Import) -> None:
        """Records recognized dependencies imported with an import statement."""
        for imported in node.names:
            self._append_dependency_import(imported.name, node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Records recognized dependencies imported with a from statement."""
        if node.level == 0 and node.module:
            self._append_dependency_import(node.module, node)

    def _is_route_decorator(self, decorator: ast.AST) -> str | None:
        """Checks if decorator is an API route (e.g., @app.get, @router.post, @app.route)."""
        if isinstance(decorator, ast.Call):
            func = decorator.func
            if isinstance(func, ast.Attribute):
                if func.attr.lower() in (
                    "get",
                    "post",
                    "put",
                    "delete",
                    "patch",
                    "route",
                ):
                    return func.attr.upper()
        elif isinstance(decorator, ast.Attribute):
            if decorator.attr.lower() in ("get", "post", "put", "delete", "patch"):
                return decorator.attr.upper()
        return None

    def _route_decorator_path(self, decorator: ast.AST) -> str | None:
        """Returns only literal route paths; dynamic paths use fallback identity."""
        if not isinstance(decorator, ast.Call):
            return None
        for argument in decorator.args[:1]:
            if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
                return argument.value
        for keyword in decorator.keywords:
            if keyword.arg in {"path", "rule"} and isinstance(
                keyword.value, ast.Constant
            ):
                if isinstance(keyword.value.value, str):
                    return keyword.value.value
        return None

    def _has_auth_param_or_decorator(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> bool:
        """Detects authentication / authorization dependencies."""
        # Check decorators
        for d in node.decorator_list:
            d_str = ast.unparse(d).lower()
            if any(
                term in d_str
                for term in ("auth", "login_required", "roles", "permissions")
            ):
                return True
        # Check function parameters for Depends(get_current_user) or Security
        for arg in node.args.args:
            # Check default values
            pass
        for default in node.args.defaults:
            def_str = ast.unparse(default).lower()
            if any(
                term in def_str
                for term in ("auth", "current_user", "security", "token")
            ):
                return True
        return False

    def _has_dependency_injection(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> bool:
        """Detects FastAPI / DI patterns using Depends(...)."""
        for default in node.args.defaults:
            def_str = ast.unparse(default)
            if "Depends(" in def_str:
                return True
        return False

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Analyze asynchronous function definitions."""
        lineno = getattr(node, "lineno", 1)
        snippet = self._get_snippet(node)

        # 1. Async pattern evidence
        self.evidence.append(
            EvidenceInput(
                source_family=SourceFamily.GITHUB,
                source_locator=self.repo_url,
                immutable_revision=self.commit_sha,
                artifact_path=self.file_path,
                symbol_or_line=f"Line {lineno}: async def {node.name}",
                target_capability=CapabilityKey.BACKEND_ENGINEERING,
                observed_score=75.0,
                is_positive_support=True,
                raw_support_text=f"Asynchronous function definition '{node.name}':\n{snippet}",
                extractor_version=self.extractor_version,
            )
        )

        # Check route decorators, DI, and Auth
        self._analyze_function_common(node, _is_async=True)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Analyze synchronous function definitions."""
        self._analyze_function_common(node, _is_async=False)
        self.generic_visit(node)

    def _analyze_function_common(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef, _is_async: bool
    ) -> None:
        lineno = getattr(node, "lineno", 1)
        snippet = self._get_snippet(node)

        # Check route decorators
        for d in node.decorator_list:
            http_method = self._is_route_decorator(d)
            if http_method:
                route_path = self._route_decorator_path(d)
                identity = (
                    build_evidence_family_identity(
                        source_family=SourceFamily.GITHUB,
                        cluster_id=self.repo_url,
                        capability=CapabilityKey.BACKEND_ENGINEERING,
                        fact_domain="route",
                        subject=f"{http_method}|{route_path}|{node.name}",
                    )
                    if route_path is not None
                    else None
                )
                self.evidence.append(
                    EvidenceInput(
                        source_family=SourceFamily.GITHUB,
                        source_locator=self.repo_url,
                        immutable_revision=self.commit_sha,
                        artifact_path=self.file_path,
                        symbol_or_line=f"Line {lineno}: @{http_method} {node.name}",
                        target_capability=CapabilityKey.BACKEND_ENGINEERING,
                        observed_score=80.0,
                        is_positive_support=True,
                        raw_support_text=f"API Route handler '{node.name}' ({http_method}):\n{snippet}",
                        extractor_version=self.extractor_version,
                        evidence_family_id=(
                            identity.evidence_family_id if identity is not None else None
                        ),
                        observation_type="route:python_decorator",
                        evidence_family_basis=(
                            identity.basis if identity is not None else {}
                        ),
                    )
                )

        # Check Dependency Injection
        if self._has_dependency_injection(node):
            self.evidence.append(
                EvidenceInput(
                    source_family=SourceFamily.GITHUB,
                    source_locator=self.repo_url,
                    immutable_revision=self.commit_sha,
                    artifact_path=self.file_path,
                    symbol_or_line=f"Line {lineno}: {node.name}(...Depends)",
                    target_capability=CapabilityKey.SOFTWARE_ARCHITECTURE,
                    observed_score=82.0,
                    is_positive_support=True,
                    raw_support_text=f"Dependency Injection pattern in '{node.name}':\n{snippet}",
                    extractor_version=self.extractor_version,
                )
            )

        # Check Authentication / Security
        if self._has_auth_param_or_decorator(node):
            self.evidence.append(
                EvidenceInput(
                    source_family=SourceFamily.GITHUB,
                    source_locator=self.repo_url,
                    immutable_revision=self.commit_sha,
                    artifact_path=self.file_path,
                    symbol_or_line=f"Line {lineno}: {node.name}(auth)",
                    target_capability=CapabilityKey.SECURITY,
                    observed_score=85.0,
                    is_positive_support=True,
                    raw_support_text=f"Authentication/Authorization guard in '{node.name}':\n{snippet}",
                    extractor_version=self.extractor_version,
                )
            )

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Analyze class hierarchies, models, services, and ML architectures."""
        lineno = getattr(node, "lineno", 1)
        snippet = self._get_snippet(node)
        base_names = [ast.unparse(b) for b in node.bases]
        base_names_lower = [b.lower() for b in base_names]

        # 1. Pydantic validation / serialization models
        if any("basemodel" in b or "schema" in b for b in base_names_lower):
            self.evidence.append(
                EvidenceInput(
                    source_family=SourceFamily.GITHUB,
                    source_locator=self.repo_url,
                    immutable_revision=self.commit_sha,
                    artifact_path=self.file_path,
                    symbol_or_line=f"Line {lineno}: class {node.name}(BaseModel)",
                    target_capability=CapabilityKey.BACKEND_ENGINEERING,
                    observed_score=78.0,
                    is_positive_support=True,
                    raw_support_text=f"Pydantic schema validation model '{node.name}':\n{snippet}",
                    extractor_version=self.extractor_version,
                )
            )

        # 2. PyTorch / ML Model architecture
        if any(
            "module" in b or "dataset" in b or "baseestimator" in b
            for b in base_names_lower
        ):
            self.evidence.append(
                EvidenceInput(
                    source_family=SourceFamily.GITHUB,
                    source_locator=self.repo_url,
                    immutable_revision=self.commit_sha,
                    artifact_path=self.file_path,
                    symbol_or_line=f"Line {lineno}: class {node.name}({', '.join(base_names)})",
                    target_capability=CapabilityKey.MACHINE_LEARNING,
                    observed_score=85.0,
                    is_positive_support=True,
                    raw_support_text=f"Machine Learning model/dataset class '{node.name}':\n{snippet}",
                    extractor_version=self.extractor_version,
                )
            )

        # 3. Service / Repository architectural boundaries
        if any(
            node.name.endswith(suffix)
            for suffix in ("Service", "Repository", "Controller", "Handler")
        ):
            self.evidence.append(
                EvidenceInput(
                    source_family=SourceFamily.GITHUB,
                    source_locator=self.repo_url,
                    immutable_revision=self.commit_sha,
                    artifact_path=self.file_path,
                    symbol_or_line=f"Line {lineno}: class {node.name}",
                    target_capability=CapabilityKey.SOFTWARE_ARCHITECTURE,
                    observed_score=80.0,
                    is_positive_support=True,
                    raw_support_text=f"Layered architectural component '{node.name}':\n{snippet}",
                    extractor_version=self.extractor_version,
                )
            )

        self.generic_visit(node)

    def visit_Try(self, node: ast.Try) -> None:
        """Analyze structured error handling and exception management."""
        lineno = getattr(node, "lineno", 1)
        snippet = self._get_snippet(node, max_lines=8)

        self.evidence.append(
            EvidenceInput(
                source_family=SourceFamily.GITHUB,
                source_locator=self.repo_url,
                immutable_revision=self.commit_sha,
                artifact_path=self.file_path,
                symbol_or_line=f"Line {lineno}: try/except",
                target_capability=CapabilityKey.TESTING_QUALITY,
                observed_score=72.0,
                is_positive_support=True,
                raw_support_text=f"Structured error handling block:\n{snippet}",
                extractor_version=self.extractor_version,
            )
        )
        self.generic_visit(node)


def analyze_python_source(
    content: str,
    file_path: str,
    repo_url: str,
    commit_sha: str,
    extractor_version: str = "1.0.0",
) -> list[EvidenceInput]:
    """Parses Python source code into AST and extracts provenance-linked evidence."""
    try:
        tree = ast.parse(content, filename=file_path)
    except SyntaxError:
        # Invalid syntax or partial file
        return []

    lines = content.split("\n")
    visitor = PythonStructuralVisitor(
        lines, file_path, repo_url, commit_sha, extractor_version
    )
    visitor.visit(tree)
    return visitor.evidence
