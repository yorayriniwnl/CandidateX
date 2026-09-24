"""Unit tests for iterative deep scan of oversized repositories (Fix 24).

Verifies that the 12-blob oversize fallback is replaced with an intelligent,
multi-tier iterative deep scan:
1. Manifests
2. Entry points
3. Application routes
4. Database schema
5. Migrations
6. Tests, coverage, and benchmarks
7. CI configuration
8. Docker & containerization
9. Infrastructure & IaC
10. Security & auth policies
11. Architecture documentation
12. Project-specific modules

Then iteratively expands using static imports and project structure.
Invariants:
- Never executes candidate or repository code.
- Preserves bounded resource constraints (SafeRepositoryWorkspace timeout, byte caps).
- Accurately tracks inventory completeness and skip reasons for negative evidence.
"""

import hashlib
from unittest.mock import MagicMock
import pytest

from cci.live.deep_scan import (
    classify_blob_architectural_tier,
    extract_static_import_references,
    iterative_deep_scan_git_blobs,
)
from cci.security.repository_workspace import SafeRepositoryWorkspace


def _git_blob_sha(content: bytes) -> str:
    return hashlib.sha1(f"blob {len(content)}\0".encode() + content).hexdigest()


class MemoryTreeFetcher:
    """Mock Git Tree and Blob fetcher for safe testing."""

    def __init__(self, files: dict[str, bytes], *, truncated: bool = False):
        self.files = files
        self.truncated = truncated
        self.blobs = {path: _git_blob_sha(content) for path, content in files.items()}
        self.requested_blobs: list[str] = []

    def get(self, url: str):
        if "/git/trees/" in url:
            if self.truncated:
                return {"tree": [], "truncated": True}
            items = []
            for path, sha in self.blobs.items():
                items.append({
                    "path": path,
                    "mode": "100644",
                    "type": "blob",
                    "sha": sha,
                    "size": len(self.files[path]),
                })
            return {"tree": items, "truncated": False}

        if "/git/blobs/" in url:
            sha = url.split("/git/blobs/")[-1]
            self.requested_blobs.append(sha)
            for path, b_sha in self.blobs.items():
                if b_sha == sha:
                    import base64
                    return {
                        "sha": sha,
                        "size": len(self.files[path]),
                        "encoding": "base64",
                        "content": base64.b64encode(self.files[path]).decode("ascii"),
                    }
            raise RuntimeError(f"Blob {sha} not found in test mock")

        raise ValueError(f"Unexpected URL: {url}")


def test_classify_blob_architectural_tiers_hierarchy():
    """Verify strictly prioritized ordering across the 12 architectural tiers."""
    tier_manifest, _ = classify_blob_architectural_tier("package.json")
    tier_entry, _ = classify_blob_architectural_tier("main.py")
    tier_routes, _ = classify_blob_architectural_tier("src/api/routes.py")
    tier_schema, _ = classify_blob_architectural_tier("models.py")
    tier_migration, _ = classify_blob_architectural_tier("migrations/001_init.py")
    tier_test, _ = classify_blob_architectural_tier("tests/test_core.py")
    tier_ci, _ = classify_blob_architectural_tier(".github/workflows/ci.yml")
    tier_docker, _ = classify_blob_architectural_tier("Dockerfile")
    tier_infra, _ = classify_blob_architectural_tier("terraform/main.tf")
    tier_security, _ = classify_blob_architectural_tier("security.md")
    tier_docs, _ = classify_blob_architectural_tier("docs/architecture.md")
    tier_module, _ = classify_blob_architectural_tier("src/services/billing.py")
    tier_other, _ = classify_blob_architectural_tier("assets/logo.png")

    assert tier_manifest == 1
    assert tier_entry == 2
    assert tier_routes == 3
    assert tier_schema == 4
    assert tier_migration == 5
    assert tier_test == 6
    assert tier_ci == 7
    assert tier_docker == 8
    assert tier_infra == 9
    assert tier_security == 10
    assert tier_docs == 11
    assert tier_module == 12
    assert tier_other == 13

    # Strictly monotonic order
    assert tier_manifest < tier_entry < tier_routes < tier_schema < tier_migration < tier_test
    assert tier_test < tier_ci < tier_docker < tier_infra < tier_security < tier_docs < tier_module < tier_other


def test_extract_static_import_references_multi_language():
    """Verify static import extraction for Python, JS/TS, Go, and Rust without execution."""
    py_code = b"""
import os
import sys
from app.services import payment
from .models import OrderItem
"""
    refs_py = extract_static_import_references("app/handlers/order.py", py_code)
    assert any("payment.py" in r for r in refs_py)
    assert any("models.py" in r or "models" in r for r in refs_py)

    ts_code = b"""
import React from 'react';
import { Button } from './components/button';
const auth = require('./services/auth');
"""
    refs_ts = extract_static_import_references("src/pages/index.tsx", ts_code)
    assert any("components/button" in r for r in refs_ts)
    assert any("services/auth" in r for r in refs_ts)

    go_code = b"""
package main
import (
    "fmt"
    "acme/pkg/storage"
)
"""
    refs_go = extract_static_import_references("main.go", go_code)
    assert "storage.go" in refs_go

    rs_code = b"""
mod network;
use crate::config;
"""
    refs_rs = extract_static_import_references("src/main.rs", rs_code)
    assert "network.rs" in refs_rs
    assert "config.rs" in refs_rs


def test_iterative_deep_scan_prioritizes_higher_architectural_tiers():
    """Verify that when file cap is reached, higher tiers are scanned first."""
    files: dict[str, bytes] = {
        "package.json": b'{"name": "test-repo", "version": "1.0.0"}',
        "main.py": b'print("starting app")',
        "src/api/routes.py": b'# API endpoints',
        "src/models.py": b'# Data models',
        "Dockerfile": b'FROM python:3.11\nCMD ["python", "main.py"]',
    }
    # Add 25 generic modules
    for i in range(25):
        files[f"src/util_{i:02d}.py"] = f"# Utility module {i}\n".encode()

    fetcher = MemoryTreeFetcher(files)
    with SafeRepositoryWorkspace() as workspace:
        # Cap at 10 blobs
        omitted, receipt = iterative_deep_scan_git_blobs(fetcher, "org", "repo", "a" * 40, workspace, max_blobs=10)
        scanned_files = [f.relative_path.replace("\\", "/") for f in workspace.scan_files()]

    # All top architectural tiers must have been inspected
    assert "package.json" in scanned_files
    assert "main.py" in scanned_files
    assert "src/api/routes.py" in scanned_files
    assert "src/models.py" in scanned_files
    assert "Dockerfile" in scanned_files

    # Total stored should be capped at 10
    assert len(scanned_files) == 10
    assert omitted == len(files) - 10
    source_cat = receipt.categories["source"]
    assert source_cat.skipped_reasons.get("file_cap", 0) > 0


def test_iterative_deep_scan_dynamic_import_expansion():
    """Verify that inspected blobs dynamically promote referenced modules into scan queue."""
    files: dict[str, bytes] = {
        "main.py": b'from src.core_engine import run_pipeline\nrun_pipeline()\n',
        "Dockerfile": b'FROM alpine\n',
    }
    # Add 15 generic modules that would normally fill a small cap ahead of core_engine alphabetically
    for i in range(15):
        files[f"src/aaa_mod_{i:02d}.py"] = f"# Module {i}\n".encode()

    # The imported target
    files["src/core_engine.py"] = b'def run_pipeline(): return 42\n'

    fetcher = MemoryTreeFetcher(files)
    with SafeRepositoryWorkspace() as workspace:
        # Small cap of 5 blobs
        omitted, receipt = iterative_deep_scan_git_blobs(fetcher, "org", "repo", "b" * 40, workspace, max_blobs=5)
        scanned_files = [f.relative_path.replace("\\", "/") for f in workspace.scan_files()]

    assert "main.py" in scanned_files
    # src/core_engine.py must be dynamically promoted and inspected despite many aaa_mod_* files
    assert "src/core_engine.py" in scanned_files
    assert len(scanned_files) == 5


def test_iterative_deep_scan_handles_unsafe_paths_and_symlinks():
    """Verify that unsafe paths (traversals) are rejected and invalidate inventory completeness."""
    files: dict[str, bytes] = {
        "main.py": b'print("hello")',
        "../escape.py": b'malicious',
        "C:\\windows\\system.py": b'malicious',
    }
    fetcher = MemoryTreeFetcher(files)
    with SafeRepositoryWorkspace() as workspace:
        omitted, receipt = iterative_deep_scan_git_blobs(fetcher, "org", "repo", "c" * 40, workspace, max_blobs=10)
        scanned_files = [f.relative_path.replace("\\", "/") for f in workspace.scan_files()]

    assert receipt.inventory_complete is False
    source_cat = receipt.categories["source"]
    assert source_cat.skipped_reasons.get("unsafe_symlink", 0) >= 1
    assert "main.py" in scanned_files
    assert not any("escape" in f or "system" in f for f in scanned_files)
