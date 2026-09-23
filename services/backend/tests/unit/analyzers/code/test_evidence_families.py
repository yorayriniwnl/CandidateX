"""Analyzer families correlate modalities that describe the same source fact."""

from cci.analyzers.code.dependencies import (
    dependencies_to_evidence,
    extract_manifest_dependencies,
)
from cci.analyzers.code.multi_language import analyze_typescript_javascript
from cci.analyzers.code.python_analyzer import analyze_python_source
from cci.domain.enums import SourceFamily


REPO_URL = "https://github.com/acme/api"
REVISION = "a" * 40


def test_manifest_and_python_import_share_dependency_family():
    manifest = dependencies_to_evidence(
        extract_manifest_dependencies("requirements.txt", "fastapi==0.115"),
        REPO_URL,
        "requirements.txt",
        REVISION,
    )[0]
    source_observations = analyze_python_source(
        "import fastapi\nfrom fastapi import APIRouter\n",
        "src/app.py",
        REPO_URL,
        REVISION,
    )
    imports = [
        item
        for item in source_observations
        if item.observation_type == "dependency:python_import"
    ]

    assert len(imports) == 2
    assert manifest.evidence_family_id is not None
    assert manifest.evidence_family_id.startswith("ef1:")
    assert manifest.observation_type == "dependency:manifest"
    assert manifest.signal_rule_id == "candidatex.dependencies.manifest_declaration"
    assert manifest.signal_rule_version == "1.0.0"
    assert manifest.technical_signal_strength == 55.0
    assert all(item.evidence_family_id == manifest.evidence_family_id for item in imports)
    assert all(item.signal_rule_id == "candidatex.code.python.dependency_import" for item in imports)
    assert all(item.signal_rule_version == "1.0.0" for item in imports)
    assert all(item.technical_signal_strength == 55.0 for item in imports)
    assert all(item.raw_support_text for item in imports)
    assert manifest.source_family == SourceFamily.GITHUB


def test_python_and_typescript_route_registrations_share_semantic_family():
    python_observations = analyze_python_source(
        "from fastapi import FastAPI\n"
        "app = FastAPI()\n"
        "@app.get('/health')\n"
        "def health_handler():\n"
        "    return {'ok': True}\n",
        "src/app.py",
        REPO_URL,
        REVISION,
    )
    typescript_observations = analyze_typescript_javascript(
        "app.get('/health', health_handler);",
        "src/app.ts",
        REPO_URL,
        REVISION,
    )
    python_route = next(
        item for item in python_observations if "API Route handler" in item.raw_support_text
    )
    typescript_route = next(
        item
        for item in typescript_observations
        if "API Route handler" in item.raw_support_text
    )
    other_path = next(
        item
        for item in analyze_typescript_javascript(
            "app.get('/admin', health_handler);",
            "src/app.ts",
            REPO_URL,
            REVISION,
        )
        if "API Route handler" in item.raw_support_text
    )

    assert python_route.evidence_family_id is not None
    assert python_route.evidence_family_id.startswith("ef1:")
    assert python_route.evidence_family_id == typescript_route.evidence_family_id
    assert python_route.observation_type == "route:python_decorator"
    assert typescript_route.observation_type == "route:typescript_registration"
    assert python_route.signal_rule_id == "candidatex.code.python.api_route"
    assert typescript_route.signal_rule_id == "candidatex.code.typescript.api_route"
    assert python_route.signal_rule_version == typescript_route.signal_rule_version == "1.0.0"
    assert python_route.technical_signal_strength == 80.0
    assert typescript_route.technical_signal_strength == 78.0
    assert python_route.evidence_family_id != other_path.evidence_family_id


def test_unrecognized_python_import_does_not_get_dependency_semantics():
    observations = analyze_python_source(
        "import internal_service\n",
        "src/app.py",
        REPO_URL,
        REVISION,
    )

    assert not [
        item
        for item in observations
        if item.observation_type == "dependency:python_import"
    ]
