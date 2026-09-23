"""Static DevOps, Container, CI/CD, and Infrastructure-as-Code analyzer.

INVARIANT: Candidate infrastructure, Docker builds, and CI pipelines are NEVER executed.
No containers are launched, no remote infrastructure is contacted.
All analysis is strictly static inspection of configuration artifacts.
"""

import re

import yaml
from cci.domain.contracts import EvidenceInput
from cci.domain.enums import CapabilityKey, SourceFamily
from cci.domain.signal_rules import signal_rule_fields

EXTRACTOR_VERSION = "1.0.0"


def analyze_dockerfile(
    content: str,
    file_path: str,
    repo_url: str,
    commit_sha: str,
    extractor_version: str = EXTRACTOR_VERSION,
) -> list[EvidenceInput]:
    """Inspects Dockerfiles for multi-stage builds, non-root users, healthchecks, and layer caching."""
    evidence: list[EvidenceInput] = []

    from_stages = re.findall(
        r"^FROM\s+([^\s]+)(?:\s+AS\s+([a-zA-Z0-9_-]+))?",
        content,
        re.IGNORECASE | re.MULTILINE,
    )
    is_multistage = len(from_stages) > 1 or any(stage[1] for stage in from_stages)
    has_copy_from = bool(
        re.search(r"^COPY\s+--from=", content, re.IGNORECASE | re.MULTILINE)
    )
    has_nonroot_user = bool(
        re.search(
            r"^USER\s+(?!root\b)([a-zA-Z0-9_-]+)", content, re.IGNORECASE | re.MULTILINE
        )
    )
    has_healthcheck = bool(
        re.search(r"^HEALTHCHECK\s+", content, re.IGNORECASE | re.MULTILINE)
    )

    # Base Dockerfile evaluation
    score = 72.0
    features = []
    if is_multistage or has_copy_from:
        score += 12.0
        features.append("Multi-stage build optimization")
    if has_nonroot_user:
        score += 6.0
        features.append("Least-privilege non-root execution (USER)")
    if has_healthcheck:
        score += 4.0
        features.append("Container healthcheck probe (HEALTHCHECK)")

    evidence.append(
        EvidenceInput(
            **signal_rule_fields("candidatex.infra.dockerfile"),
            source_family=SourceFamily.GITHUB,
            source_locator=repo_url,
            immutable_revision=commit_sha,
            artifact_path=file_path,
            symbol_or_line=f"{file_path} ({'Multi-stage' if is_multistage else 'Single-stage'})",
            target_capability=CapabilityKey.DEVOPS_CLOUD,
            technical_signal_strength=min(score, 92.0),
            is_positive_support=True,
            raw_support_text=f"Container configuration in {file_path}: {'; '.join(features) if features else 'Standard container image definition'}",
            extractor_version=extractor_version,
        )
    )

    return evidence


def analyze_docker_compose(
    content: str,
    file_path: str,
    repo_url: str,
    commit_sha: str,
    extractor_version: str = EXTRACTOR_VERSION,
) -> list[EvidenceInput]:
    """Inspects docker-compose files for multi-service architectures, networks, volumes, and healthchecks."""
    evidence: list[EvidenceInput] = []

    try:
        data = yaml.safe_load(content)
    except Exception:
        data = None

    if isinstance(data, dict) and "services" in data:
        services = data.get("services", {})
        service_count = len(services) if isinstance(services, dict) else 0
        has_volumes = "volumes" in data or any(
            "volumes" in svc for svc in services.values() if isinstance(svc, dict)
        )
        has_networks = "networks" in data or any(
            "networks" in svc for svc in services.values() if isinstance(svc, dict)
        )
        has_healthchecks = any(
            "healthcheck" in svc for svc in services.values() if isinstance(svc, dict)
        )

        score = 74.0
        features = [
            f"{service_count} orchestrated services ({', '.join(list(services.keys())[:4])})"
        ]
        if has_networks:
            score += 5.0
            features.append("custom network topology")
        if has_volumes:
            score += 4.0
            features.append("persistent volumes")
        if has_healthchecks:
            score += 5.0
            features.append("service healthchecks")

        evidence.append(
            EvidenceInput(
                **signal_rule_fields("candidatex.infra.docker_compose"),
                source_family=SourceFamily.GITHUB,
                source_locator=repo_url,
                immutable_revision=commit_sha,
                artifact_path=file_path,
                symbol_or_line=f"{file_path}: {service_count} services",
                target_capability=CapabilityKey.DEVOPS_CLOUD,
                technical_signal_strength=min(score, 90.0),
                is_positive_support=True,
                raw_support_text=f"Docker Compose orchestration in {file_path}: {'; '.join(features)}",
                extractor_version=extractor_version,
            )
        )

    return evidence


def analyze_ci_workflow(
    content: str,
    file_path: str,
    repo_url: str,
    commit_sha: str,
    extractor_version: str = EXTRACTOR_VERSION,
) -> list[EvidenceInput]:
    """Inspects GitHub Actions, GitLab CI, or other workflow definitions for testing, matrix, and caching."""
    evidence: list[EvidenceInput] = []

    try:
        data = yaml.safe_load(content)
    except Exception:
        data = None

    if isinstance(data, dict) and ("jobs" in data or "stages" in data):
        jobs = data.get("jobs", {})
        job_names = list(jobs.keys()) if isinstance(jobs, dict) else []
        content_lower = content.lower()

        has_test_job = (
            any(
                term in j.lower()
                for j in job_names
                for term in ("test", "pytest", "unit", "spec", "check")
            )
            or "pytest" in content_lower
            or "npm test" in content_lower
            or "go test" in content_lower
        )
        has_matrix = "strategy:" in content_lower and "matrix:" in content_lower
        has_cache = "actions/cache" in content or "cache:" in content_lower
        has_deploy = (
            any(
                term in j.lower()
                for j in job_names
                for term in ("deploy", "release", "publish")
            )
            or "deploy" in content_lower
        )

        score = 75.0
        features = []
        if has_test_job:
            score += 6.0
            features.append("automated test execution")
        if has_matrix:
            score += 7.0
            features.append("matrix build environments")
        if has_cache:
            score += 4.0
            features.append("dependency caching")
        if has_deploy:
            score += 5.0
            features.append("automated deployment pipeline")

        evidence.append(
            EvidenceInput(
                **signal_rule_fields("candidatex.infra.ci_workflow"),
                source_family=SourceFamily.GITHUB,
                source_locator=repo_url,
                immutable_revision=commit_sha,
                artifact_path=file_path,
                symbol_or_line=f"{file_path}: CI Pipeline",
                target_capability=CapabilityKey.DEVOPS_CLOUD,
                technical_signal_strength=min(score, 94.0),
                is_positive_support=True,
                raw_support_text=f"Automated CI/CD workflow in {file_path} featuring: {'; '.join(features) if features else 'basic pipeline jobs'}",
                extractor_version=extractor_version,
            )
        )

    return evidence


def analyze_kubernetes_manifest(
    content: str,
    file_path: str,
    repo_url: str,
    commit_sha: str,
    extractor_version: str = EXTRACTOR_VERSION,
) -> list[EvidenceInput]:
    """Inspects Kubernetes manifests for Deployments, resource limits, and health probes."""
    evidence: list[EvidenceInput] = []

    try:
        docs = list(yaml.safe_load_all(content))
    except Exception:
        docs = []

    kinds = []
    has_limits = False
    has_probes = False

    for doc in docs:
        if isinstance(doc, dict) and "kind" in doc:
            kinds.append(doc["kind"])
            doc_str = str(doc).lower()
            if "limits" in doc_str and ("cpu" in doc_str or "memory" in doc_str):
                has_limits = True
            if "livenessprobe" in doc_str or "readinessprobe" in doc_str:
                has_probes = True

    if kinds:
        score = 80.0
        features = [f"Kubernetes resources: {', '.join(kinds[:4])}"]
        if has_limits:
            score += 7.0
            features.append("CPU/Memory resource bounds")
        if has_probes:
            score += 5.0
            features.append("Liveness/Readiness probes")

        evidence.append(
            EvidenceInput(
                **signal_rule_fields("candidatex.infra.kubernetes_manifest"),
                source_family=SourceFamily.GITHUB,
                source_locator=repo_url,
                immutable_revision=commit_sha,
                artifact_path=file_path,
                symbol_or_line=f"{file_path}: {len(kinds)} K8s resources",
                target_capability=CapabilityKey.DEVOPS_CLOUD,
                technical_signal_strength=min(score, 92.0),
                is_positive_support=True,
                raw_support_text=f"Kubernetes infrastructure manifests in {file_path}: {'; '.join(features)}",
                extractor_version=extractor_version,
            )
        )

    return evidence


def analyze_terraform_hcl(
    content: str,
    file_path: str,
    repo_url: str,
    commit_sha: str,
    extractor_version: str = EXTRACTOR_VERSION,
) -> list[EvidenceInput]:
    """Inspects Terraform HCL files for infrastructure resource declarations and module definitions."""
    evidence: list[EvidenceInput] = []

    resources = re.findall(r'\bresource\s+"([^"]+)"\s+"([^"]+)"', content)
    modules = re.findall(r'\bmodule\s+"([^"]+)"', content)

    if resources or modules:
        score = 82.0
        features = []
        if resources:
            score += 4.0
            features.append(
                f"{len(resources)} cloud resources ({', '.join(r[0] for r in resources[:3])})"
            )
        if modules:
            score += 5.0
            features.append(f"{len(modules)} reusable infrastructure modules")

        evidence.append(
            EvidenceInput(
                **signal_rule_fields("candidatex.infra.terraform_hcl"),
                source_family=SourceFamily.GITHUB,
                source_locator=repo_url,
                immutable_revision=commit_sha,
                artifact_path=file_path,
                symbol_or_line=f"{file_path}: Terraform IaC",
                target_capability=CapabilityKey.DEVOPS_CLOUD,
                technical_signal_strength=min(score, 92.0),
                is_positive_support=True,
                raw_support_text=f"Declarative Terraform Infrastructure-as-Code in {file_path}: {'; '.join(features)}",
                extractor_version=extractor_version,
            )
        )

    return evidence
