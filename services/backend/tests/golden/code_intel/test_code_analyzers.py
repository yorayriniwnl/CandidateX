"""Tests for Agent 04 Static Code, Dependency, and Architecture Intelligence."""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

import pytest
from cci.analyzers.code.dependencies import (
    extract_manifest_dependencies,
    dependencies_to_evidence,
)
from cci.analyzers.code.python_analyzer import analyze_python_source
from cci.analyzers.code.multi_language import (
    analyze_typescript_javascript,
    analyze_go_source,
    analyze_java_source,
    analyze_c_cpp_source,
)
from cci.analyzers.documentation.architecture import (
    analyze_readme,
    analyze_adr,
    analyze_openapi_spec,
    analyze_layer_boundaries,
)
from cci.security.repository_workspace import SafeRepositoryWorkspace
from cci.analyzers.repository.indexer import index_repository_artifacts
from cci.analyzers.code.engine import run_code_intelligence
from cci.domain.enums import CapabilityKey, SourceFamily
from tests.golden.code_intel.fixtures import (
    create_golden_fastapi_repo,
    create_golden_polyglot_files,
)


def test_python_ast_analysis():
    py_code = """
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import torch

router = APIRouter()

class UserPayload(BaseModel):
    username: str

def auth_dep():
    return True

@router.get("/users")
async def get_users(user=Depends(auth_dep)):
    try:
        x = torch.tensor([1, 2])
        return {"users": []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
"""
    evidence = analyze_python_source(
        content=py_code,
        file_path="src/api/routes.py",
        repo_url="https://github.com/alice/project",
        commit_sha="abcd1234",
        extractor_version="1.0.0",
    )
    assert len(evidence) > 0
    cap_keys = {e.target_capability for e in evidence}
    assert CapabilityKey.BACKEND_ENGINEERING in cap_keys

    support_texts = [e.raw_support_text for e in evidence]
    assert any("Dependency injection" in t or "auth_dep" in t for t in support_texts)
    assert any("HTTPException" in t for t in support_texts)
    route_observations = [e for e in evidence if "API Route handler" in e.raw_support_text]
    assert len(route_observations) == 1
    assert route_observations[0].evidence_family_id is not None
    assert route_observations[0].observation_type == "route:python_decorator"
    dependency_imports = [
        e for e in evidence if e.observation_type == "dependency:python_import"
    ]
    assert any(e.evidence_family_id is not None for e in dependency_imports)


def test_dependency_manifest_analysis():
    req_txt = """
fastapi==0.110.0
sqlalchemy>=2.0.0
pytest==8.0.0
docker>=6.0.0
torch>=2.0.0
"""
    deps = extract_manifest_dependencies("requirements.txt", req_txt)
    assert any(d.name == "fastapi" for d in deps)
    assert any(d.name == "sqlalchemy" for d in deps)
    assert any(d.name == "torch" for d in deps)

    evidence = dependencies_to_evidence(
        deps=deps,
        repo_url="https://github.com/alice/project",
        file_path="requirements.txt",
        commit_sha="abcd1234",
        extractor_version="1.0.0",
    )
    assert len(evidence) > 0

    # Invariant: Framework presence is not unearned mastery -> score <= 55
    for e in evidence:
        assert e.observed_score <= 55.0
        assert e.source_family == SourceFamily.GITHUB
        assert e.source_locator == "https://github.com/alice/project"
        assert e.immutable_revision == "abcd1234"
        assert e.evidence_family_id is not None
        assert e.observation_type == "dependency:manifest"


def test_polyglot_source_analysis():
    # TypeScript
    ts_code = """
import express from 'express';
import { z } from 'zod';
const app = express();
const schema = z.object({ id: z.number() });
app.get('/api', async (req, res) => {
    try { res.json({ ok: true }); } catch (e) { res.status(500).send(); }
});
"""
    ts_evidence = analyze_typescript_javascript(
        ts_code, "server.ts", "https://github.com/test", "sha1", "1.0.0"
    )
    assert any(e.target_capability == CapabilityKey.BACKEND_ENGINEERING for e in ts_evidence)
    assert any(e.target_capability == CapabilityKey.SOFTWARE_ARCHITECTURE for e in ts_evidence)

    # Go
    go_code = """
package main
import "net/http"
func main() {
    ch := make(chan int)
    go func() { ch <- 1 }()
    <-ch
    http.HandleFunc("/", nil)
}
"""
    go_evidence = analyze_go_source(
        go_code, "main.go", "https://github.com/test", "sha1", "1.0.0"
    )
    assert any(e.target_capability == CapabilityKey.BACKEND_ENGINEERING for e in go_evidence)

    # Java
    java_code = """
@RestController
@RequestMapping("/api")
public class AppController {
    @GetMapping("/data")
    public String data() { return "ok"; }
}
"""
    java_evidence = analyze_java_source(
        java_code, "AppController.java", "https://github.com/test", "sha1", "1.0.0"
    )
    assert any(e.target_capability == CapabilityKey.BACKEND_ENGINEERING for e in java_evidence)

    # C++
    cpp_code = """
#include <memory>
#include <vector>
void run() {
    auto p = std::make_unique<int>(5);
    std::vector<int> v;
}
"""
    cpp_evidence = analyze_c_cpp_source(
        cpp_code, "main.cpp", "https://github.com/test", "sha1", "1.0.0"
    )
    assert any(e.target_capability == CapabilityKey.SOFTWARE_ARCHITECTURE for e in cpp_evidence)
    assert any(e.target_capability == CapabilityKey.ALGORITHMS_PROBLEM_SOLVING for e in cpp_evidence)


@pytest.mark.parametrize(
    ("analyzer", "source", "file_path", "expected"),
    [
        (
            analyze_python_source,
            "import fastapi\n"
            "class User(BaseModel):\n    pass\n"
            "class Model(Module):\n    pass\n"
            "class UserService:\n    pass\n"
            "@app.get('/users')\n"
            "async def get_users(user=Depends(get_current_user)):\n"
            "    try:\n        return user\n    except Exception:\n        raise\n",
            "src/app.py",
            {
                "candidatex.code.python.dependency_import": (55.0, "dependency:python_import"),
                "candidatex.code.python.async_function": (75.0, "legacy_unknown"),
                "candidatex.code.python.api_route": (80.0, "route:python_decorator"),
                "candidatex.code.python.dependency_injection": (82.0, "legacy_unknown"),
                "candidatex.code.python.auth_guard": (85.0, "legacy_unknown"),
                "candidatex.code.python.pydantic_schema": (78.0, "legacy_unknown"),
                "candidatex.code.python.ml_class": (85.0, "legacy_unknown"),
                "candidatex.code.python.architecture_class": (80.0, "legacy_unknown"),
                "candidatex.code.python.try_except": (72.0, "legacy_unknown"),
            },
        ),
        (
            analyze_typescript_javascript,
            "const schema = z.object({});\n"
            "app.get('/users', async (req, res) => {\n"
            "try { res.json({}); } catch (e) {}\n",
            "server.ts",
            {
                "candidatex.code.typescript.api_route": (78.0, "route:typescript_registration"),
                "candidatex.code.typescript.async_handler": (74.0, "legacy_unknown"),
                "candidatex.code.typescript.zod_schema": (80.0, "legacy_unknown"),
                "candidatex.code.typescript.try_catch": (70.0, "legacy_unknown"),
            },
        ),
        (
            analyze_go_source,
            'http.HandleFunc("/users", handler)\n'
            "go func() {}()\n"
            "if err != nil { return err }\n",
            "main.go",
            {
                "candidatex.code.go.http_route": (82.0, "legacy_unknown"),
                "candidatex.code.go.goroutine_channel": (85.0, "legacy_unknown"),
                "candidatex.code.go.error_guard": (72.0, "legacy_unknown"),
            },
        ),
        (
            analyze_java_source,
            '@GetMapping("/users")\n@Service\n',
            "Controller.java",
            {
                "candidatex.code.java.spring_endpoint": (80.0, "legacy_unknown"),
                "candidatex.code.java.spring_component": (80.0, "legacy_unknown"),
            },
        ),
        (
            analyze_c_cpp_source,
            "auto p = std::make_unique<int>(5);\nstd::vector<int> values;\n",
            "main.cpp",
            {
                "candidatex.code.cpp.smart_pointer_raii": (85.0, "legacy_unknown"),
                "candidatex.code.cpp.stl_algorithm_structure": (78.0, "legacy_unknown"),
            },
        ),
    ],
)
def test_code_analyzers_emit_versioned_rule_metadata(analyzer, source, file_path, expected):
    observations = analyzer(source, file_path, "https://github.com/test", "sha1", "1.0.0")

    assert len(observations) == len(expected)
    assert {item.signal_rule_id for item in observations} == set(expected)
    for observation in observations:
        strength, observation_type = expected[observation.signal_rule_id]
        assert observation.signal_rule_version == "1.0.0"
        assert observation.technical_signal_strength == strength
        assert observation.observation_type == observation_type


def test_manifest_dependencies_emit_versioned_rule_metadata():
    dependencies = extract_manifest_dependencies("requirements.txt", "fastapi==0.115")
    observations = dependencies_to_evidence(
        dependencies, "https://github.com/test", "requirements.txt", "sha1", "1.0.0"
    )

    assert len(observations) == 1
    observation = observations[0]
    assert observation.signal_rule_id == "candidatex.dependencies.manifest_declaration"
    assert observation.signal_rule_version == "1.0.0"
    assert observation.technical_signal_strength == 55.0
    assert observation.observation_type == "dependency:manifest"


def test_documentation_and_architecture_analysis():
    readme_content = """
# Project Alpha
## Getting Started
Run `pip install .`
## Architecture
```mermaid
graph TD
    Client --> API
    API --> DB
```
"""
    readme_ev = analyze_readme(
        readme_content, "README.md", "https://github.com/test", "sha1", "1.0.0"
    )
    assert len(readme_ev) > 0
    assert any(e.target_capability == CapabilityKey.DOCUMENTATION_COMMUNICATION for e in readme_ev)
    assert any(e.target_capability == CapabilityKey.SOFTWARE_ARCHITECTURE for e in readme_ev)

    adr_content = """
# 1. Choose Postgres
## Context
Relational requirements.
## Decision
Postgres.
## Consequences
Easy migrations.
"""
    adr_ev = analyze_adr(
        adr_content, "docs/adr/0001.md", "https://github.com/test", "sha1", "1.0.0"
    )
    assert len(adr_ev) > 0
    assert any(e.target_capability == CapabilityKey.SOFTWARE_ARCHITECTURE for e in adr_ev)

    paths = ["src/domain/user.py", "src/services/user_service.py", "src/api/routes.py", "src/db/repo.py"]
    boundary_ev = analyze_layer_boundaries(
        paths, "https://github.com/test", "sha1", "1.0.0"
    )
    assert len(boundary_ev) > 0
    assert boundary_ev[0].target_capability == CapabilityKey.SOFTWARE_ARCHITECTURE


def test_full_code_intelligence_engine():
    with SafeRepositoryWorkspace() as ws:
        create_golden_fastapi_repo(ws.root)
        create_golden_polyglot_files(ws.root)

        metadata, artifacts = index_repository_artifacts(
            workspace=ws,
            repo_url="https://github.com/candidate/golden-service",
            commit_sha="c0ffee1234",
        )
        assert len(artifacts) > 0

        evidence = run_code_intelligence(
            workspace_root=ws.root,
            repo_url="https://github.com/candidate/golden-service",
            commit_sha="c0ffee1234",
            artifacts=artifacts,
        )

        assert len(evidence) >= 8

        for ev in evidence:
            assert ev.source_locator == "https://github.com/candidate/golden-service"
            assert ev.immutable_revision == "c0ffee1234"
            assert 0.0 <= ev.observed_score <= 100.0
            assert ev.artifact_path is not None
            assert ev.extractor_version == "1.0.0"
