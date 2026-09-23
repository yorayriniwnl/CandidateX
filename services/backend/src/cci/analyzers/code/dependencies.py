"""Dependency manifest parsers converting package specifications into provenance-linked EvidenceInput."""

import re
from dataclasses import dataclass

import defusedxml.ElementTree as ET
import tomllib
from cci.domain.contracts import EvidenceInput
from cci.domain.evidence_families import build_evidence_family_identity
from cci.domain.enums import CapabilityKey, SourceFamily
from cci.domain.signal_rules import signal_rule_fields

DEPENDENCY_CAPABILITY_MAP: dict[str, CapabilityKey] = {
    # Backend
    "fastapi": CapabilityKey.BACKEND_ENGINEERING,
    "django": CapabilityKey.BACKEND_ENGINEERING,
    "flask": CapabilityKey.BACKEND_ENGINEERING,
    "express": CapabilityKey.BACKEND_ENGINEERING,
    "nestjs": CapabilityKey.BACKEND_ENGINEERING,
    "gin": CapabilityKey.BACKEND_ENGINEERING,
    "spring-boot": CapabilityKey.BACKEND_ENGINEERING,
    "grpc": CapabilityKey.BACKEND_ENGINEERING,
    "uvicorn": CapabilityKey.BACKEND_ENGINEERING,
    # Frontend
    "react": CapabilityKey.FRONTEND_ENGINEERING,
    "next": CapabilityKey.FRONTEND_ENGINEERING,
    "vue": CapabilityKey.FRONTEND_ENGINEERING,
    "angular": CapabilityKey.FRONTEND_ENGINEERING,
    "svelte": CapabilityKey.FRONTEND_ENGINEERING,
    "tailwindcss": CapabilityKey.FRONTEND_ENGINEERING,
    # Database
    "sqlalchemy": CapabilityKey.DATABASE_ENGINEERING,
    "prisma": CapabilityKey.DATABASE_ENGINEERING,
    "pg": CapabilityKey.DATABASE_ENGINEERING,
    "psycopg2": CapabilityKey.DATABASE_ENGINEERING,
    "asyncpg": CapabilityKey.DATABASE_ENGINEERING,
    "typeorm": CapabilityKey.DATABASE_ENGINEERING,
    "mongoose": CapabilityKey.DATABASE_ENGINEERING,
    "redis": CapabilityKey.DATABASE_ENGINEERING,
    # DevOps / Cloud
    "boto3": CapabilityKey.DEVOPS_CLOUD,
    "pulumi": CapabilityKey.DEVOPS_CLOUD,
    "kubernetes": CapabilityKey.DEVOPS_CLOUD,
    # Machine Learning
    "torch": CapabilityKey.MACHINE_LEARNING,
    "tensorflow": CapabilityKey.MACHINE_LEARNING,
    "scikit-learn": CapabilityKey.MACHINE_LEARNING,
    "transformers": CapabilityKey.MACHINE_LEARNING,
    # Data Engineering
    "pyspark": CapabilityKey.DATA_ENGINEERING,
    "kafka-python": CapabilityKey.DATA_ENGINEERING,
    "dbt-core": CapabilityKey.DATA_ENGINEERING,
    "apache-airflow": CapabilityKey.DATA_ENGINEERING,
    # Testing
    "pytest": CapabilityKey.TESTING_QUALITY,
    "jest": CapabilityKey.TESTING_QUALITY,
    "vitest": CapabilityKey.TESTING_QUALITY,
    "playwright": CapabilityKey.TESTING_QUALITY,
    "cypress": CapabilityKey.TESTING_QUALITY,
    "junit": CapabilityKey.TESTING_QUALITY,
}


@dataclass(frozen=True)
class ParsedDependency:
    name: str
    version: str | None
    is_dev: bool
    line_number: int
    raw_line: str


def parse_package_json(content: str) -> list[ParsedDependency]:
    """Parses package.json dependencies and devDependencies with line numbers."""
    deps: list[ParsedDependency] = []
    lines = content.split("\n")

    current_section = None
    for idx, line in enumerate(lines, start=1):
        if '"dependencies"' in line:
            current_section = "prod"
            continue
        elif '"devDependencies"' in line:
            current_section = "dev"
            continue
        elif "}" in line and current_section:
            current_section = None
            continue

        if current_section:
            match = re.search(r'"([^"]+)":\s*"([^"]+)"', line)
            if match:
                pkg_name, pkg_ver = match.groups()
                deps.append(
                    ParsedDependency(
                        name=pkg_name.lower(),
                        version=pkg_ver,
                        is_dev=(current_section == "dev"),
                        line_number=idx,
                        raw_line=line.strip(),
                    )
                )
    return deps


def parse_requirements_txt(content: str) -> list[ParsedDependency]:
    """Parses requirements.txt line by line."""
    deps: list[ParsedDependency] = []
    lines = content.split("\n")

    for idx, line in enumerate(lines, start=1):
        cleaned = line.strip()
        if not cleaned or cleaned.startswith("#") or cleaned.startswith("-"):
            continue

        match = re.match(r"^([a-zA-Z0-9_.-]+)(?:([<>=!~]+.*))?$", cleaned)
        if match:
            pkg_name = match.group(1).lower()
            pkg_ver = match.group(2)
            deps.append(
                ParsedDependency(
                    name=pkg_name,
                    version=pkg_ver,
                    is_dev=False,
                    line_number=idx,
                    raw_line=cleaned,
                )
            )
    return deps


def parse_pyproject_toml(content: str) -> list[ParsedDependency]:
    """Parses pyproject.toml dependencies."""
    deps: list[ParsedDependency] = []
    lines = content.split("\n")

    try:
        data = tomllib.loads(content)
    except Exception:
        return deps

    declared_pkgs = set()
    # Check [project.dependencies]
    project = data.get("project", {})
    for dep_str in project.get("dependencies", []):
        m = re.match(r"^([a-zA-Z0-9_.-]+)", dep_str)
        if m:
            declared_pkgs.add(m.group(1).lower())

    # Check [tool.poetry.dependencies]
    tool_poetry = data.get("tool", {}).get("poetry", {}).get("dependencies", {})
    for k in tool_poetry.keys():
        if k.lower() != "python":
            declared_pkgs.add(k.lower())

    # Find line numbers in content
    for idx, line in enumerate(lines, start=1):
        for pkg in declared_pkgs:
            if re.search(r"\b" + re.escape(pkg) + r"\b", line, re.IGNORECASE):
                deps.append(
                    ParsedDependency(
                        name=pkg,
                        version=None,
                        is_dev=False,
                        line_number=idx,
                        raw_line=line.strip(),
                    )
                )
                break
    return deps


def parse_go_mod(content: str) -> list[ParsedDependency]:
    """Parses go.mod require directives."""
    deps: list[ParsedDependency] = []
    lines = content.split("\n")

    in_require = False
    for idx, line in enumerate(lines, start=1):
        trimmed = line.strip()
        if trimmed.startswith("require ("):
            in_require = True
            continue
        elif in_require and trimmed == ")":
            in_require = False
            continue

        if in_require or trimmed.startswith("require "):
            cleaned = trimmed.removeprefix("require ").strip()
            parts = cleaned.split()
            if parts:
                mod_name = parts[0]
                mod_ver = parts[1] if len(parts) > 1 else None
                deps.append(
                    ParsedDependency(
                        name=mod_name.lower(),
                        version=mod_ver,
                        is_dev=False,
                        line_number=idx,
                        raw_line=trimmed,
                    )
                )
    return deps


def parse_pom_xml(content: str) -> list[ParsedDependency]:
    """Parses Maven pom.xml dependencies."""
    deps: list[ParsedDependency] = []
    try:
        root = ET.fromstring(content)
        # Strip XML namespaces for simplified query
        for elem in root.iter():
            if "}" in elem.tag:
                elem.tag = elem.tag.split("}", 1)[1]

        for dep in root.findall(".//dependency"):
            artifact = dep.find("artifactId")
            version = dep.find("version")

            name = artifact.text if artifact is not None and artifact.text else ""
            ver = version.text if version is not None else None

            if name:
                deps.append(
                    ParsedDependency(
                        name=name.lower(),
                        version=ver,
                        is_dev=False,
                        line_number=1,
                        raw_line=f"<artifactId>{name}</artifactId>",
                    )
                )
    except Exception:
        pass
    return deps


def extract_manifest_dependencies(
    file_path: str, content: str
) -> list[ParsedDependency]:
    """Dispatches manifest parsing based on file path name."""
    norm_path = file_path.replace("\\", "/").lower()
    fname = norm_path.split("/")[-1]

    if fname == "package.json":
        return parse_package_json(content)
    elif fname == "requirements.txt" or fname.endswith(".requirements.txt"):
        return parse_requirements_txt(content)
    elif fname == "pyproject.toml":
        return parse_pyproject_toml(content)
    elif fname == "go.mod":
        return parse_go_mod(content)
    elif fname == "pom.xml":
        return parse_pom_xml(content)
    return []


def dependencies_to_evidence(
    deps: list[ParsedDependency],
    repo_url: str,
    file_path: str,
    commit_sha: str,
    extractor_version: str = "1.0.0",
) -> list[EvidenceInput]:
    """Converts parsed dependencies into EvidenceInput candidates.

    INVARIANT: Does NOT convert mere framework presence into unearned capability mastery.
    Assigns moderate baseline support score (55.0) reflecting dependency declaration.
    """
    evidence_list: list[EvidenceInput] = []

    for dep in deps:
        # Match against known capability mapping
        target_cap = None
        for key, cap in DEPENDENCY_CAPABILITY_MAP.items():
            if key in dep.name:
                target_cap = cap
                break

        if target_cap:
            identity = build_evidence_family_identity(
                source_family=SourceFamily.GITHUB,
                cluster_id=repo_url,
                capability=target_cap,
                fact_domain="dependency",
                subject=dep.name,
            )
            evidence_list.append(
                EvidenceInput(
                    **signal_rule_fields("candidatex.dependencies.manifest_declaration"),
                    source_family=SourceFamily.GITHUB,
                    source_locator=repo_url,
                    immutable_revision=commit_sha,
                    artifact_path=file_path,
                    symbol_or_line=f"Line {dep.line_number}: {dep.name}",
                    target_capability=target_cap,
                    technical_signal_strength=55.0,  # Baseline declaration score
                    is_positive_support=True,
                    raw_support_text=f"Declared dependency '{dep.name}' (version: {dep.version or 'unpinned'}) in {file_path}:\n{dep.raw_line}",
                    extractor_version=extractor_version,
                    evidence_family_id=identity.evidence_family_id,
                    observation_type="dependency:manifest",
                    evidence_family_basis=identity.basis,
                )
            )

    return evidence_list
