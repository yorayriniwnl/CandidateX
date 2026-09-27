from cci.intelligence.evidence_quality import assess_evidence_quality
from cci.intelligence.repository_fingerprint import build_repository_fingerprint


def test_implementation_context_outranks_manifest_declaration():
    implementation = assess_evidence_quality(
        artifact_category="source",
        artifact_path="src/api.py",
        symbol_or_line="Line 42: async handler",
        raw_support_text='@app.post("/jobs")\nasync def create_job(payload: JobRequest):\n    return await service.create(payload)',
        context_text="""
from fastapi import FastAPI
from pydantic import BaseModel
import logging

class JobRequest(BaseModel):
    name: str

@app.post("/jobs")
async def create_job(payload: JobRequest):
    try:
        return await service.create(payload)
    except TimeoutError:
        logging.exception("create_job timeout")
        raise
""",
    )
    declaration = assess_evidence_quality(
        artifact_category="manifests",
        artifact_path="requirements.txt",
        symbol_or_line="requirements.txt",
        raw_support_text="fastapi==0.115.0",
        context_text="fastapi==0.115.0\npydantic==2.8.0\n",
    )

    assert implementation.depth_specificity > declaration.depth_specificity
    assert implementation.verification_level > declaration.verification_level
    assert implementation.quality_band in {"substantive", "rich_context"}
    assert "api_contract" in implementation.signal_families
    assert "validation_contract" in implementation.signal_families


def test_documentation_is_capped_below_runtime_proof():
    assessment = assess_evidence_quality(
        artifact_category="docs",
        artifact_path="README.md",
        symbol_or_line="Architecture",
        raw_support_text="Uses retries, JWT auth, tracing, Docker and Kubernetes.",
        context_text="Architecture documentation with retry, timeout, JWT, tracing and Docker.",
    )
    assert assessment.depth_specificity <= 0.58
    assert assessment.verification_level <= 0.56


def test_repository_fingerprint_maps_practices_and_boundaries():
    fingerprint = build_repository_fingerprint(
        [
            {
                "path": "src/api/routes.py",
                "category": "source",
                "text": "async def create():\n    validate(payload)\n    logger.info('create')\n",
            },
            {
                "path": "src/security/auth.py",
                "category": "source",
                "text": "JWT authentication authorization permission",
            },
            {
                "path": "tests/test_routes.py",
                "category": "tests",
                "text": "def test_route():\n    assert client.get('/').status_code == 200",
            },
            {
                "path": ".github/workflows/ci.yml",
                "category": "ci",
                "text": "pytest",
            },
            {
                "path": "Dockerfile",
                "category": "infra",
                "text": "FROM python:3.11-slim",
            },
        ]
    )

    practices = {item["name"] for item in fingerprint["observed_practices"]}
    boundaries = {item["name"] for item in fingerprint["architecture_boundaries"]}

    assert "input_validation" in practices
    assert "authentication_authorization" in practices
    assert "observability" in practices
    assert "testing_discipline" in practices
    assert "delivery_automation" in practices
    assert "containerization_infrastructure" in practices
    assert {"api", "security", "tests"}.issubset(boundaries)
    assert fingerprint["practice_breadth"]["observed"] >= 6
    assert fingerprint["signal_hotspots"]


def test_module_topology_resolves_relative_imports_and_cycles():
    fingerprint = build_repository_fingerprint(
        [
            {
                "path": "src/a.py",
                "category": "source",
                "text": "from .b import run\n\ndef start():\n    return run()\n",
            },
            {
                "path": "src/b.py",
                "category": "source",
                "text": "from .a import start\n\ndef run():\n    return start\n",
            },
            {
                "path": "web/client.ts",
                "category": "source",
                "text": "import { api } from './api';\nexport const run = () => api();",
            },
            {
                "path": "web/api.ts",
                "category": "source",
                "text": "export const api = () => 1;",
            },
        ]
    )

    topology = fingerprint["module_topology"]
    assert topology["nodes"] == 4
    assert topology["edges"] == 3
    assert topology["cycles_detected"] == 1
    assert topology["highest_fan_in"]
    assert topology["highest_fan_out"]


def test_review_targets_are_descriptive_and_bounded():
    fingerprint = build_repository_fingerprint(
        [
            {
                "path": "src/security.py",
                "category": "source",
                "text": "result = eval(user_input)\nrequests.get(url, verify=False)\n",
            },
            {
                "path": "src/db.py",
                "category": "source",
                "text": 'cursor.execute(f"SELECT * FROM users WHERE id={user_id}")\n',
            },
            {
                "path": "README.md",
                "category": "docs",
                "text": "eval(user_input) is mentioned only in documentation",
            },
        ]
    )

    targets = fingerprint["review_targets"]
    rules = {finding["rule"] for finding in targets["findings"]}
    assert "dynamic_code_execution" in rules
    assert "tls_verification_disabled" in rules
    assert "raw_sql_construction" in rules
    assert targets["by_severity"]["high"] >= 2
    assert all(finding["path"] != "README.md" for finding in targets["findings"])
    assert "not confirmed vulnerabilities" in targets["interpretation"]
