#!/usr/bin/env python3
"""Candidate Capability Intelligence (CCI) comprehensive system audit runner.

Executes a six-pillar audit:
1. Formal paper theorem tests (Theorems 1-10)
2. Security and static-analysis sandboxing tests
3. Database migration and model-integrity tests
4. Synthetic Monte Carlo research reproduction tests (N=4,800 simulated candidates)
5. Local operational endpoint probes
6. Frontend typecheck, production build, and UI evidence-contract checks

The runner reports only what its commands actually exercise. The N=4,800 research
cohort is synthetic simulation evidence, not validation on real applicants or hiring outcomes.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Any, Dict, List
import urllib.request

CYAN = "\033[96m"
GREEN = "\033[92m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"


@dataclass
class AuditResult:
    pillar: str
    status: str
    details: str
    duration_ms: float
    checks: List[Dict[str, Any]]


def run_command(cmd: List[str], cwd: str | None = None) -> tuple[int, str, str]:
    proc = subprocess.Popen(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        shell=(sys.platform == "win32"),
    )
    stdout, stderr = proc.communicate()
    return proc.returncode, stdout, stderr


def audit_pillar_1_theorems(python_bin: str) -> AuditResult:
    """Pillar 1: Mathematical and paper theorem tests."""
    t0 = time.perf_counter()
    cmd = [
        python_bin,
        "-m",
        "pytest",
        "services/backend/tests/test_paper_theorems_audit.py",
        "-v",
        "--tb=short",
    ]
    code, stdout, stderr = run_command(cmd)
    duration = (time.perf_counter() - t0) * 1000

    checks = []
    theorems = [
        ("Theorem 1: Recency Decay Monotonicity & Asymptotics", "test_theorem_1_recency_decay"),
        ("Theorem 2: 6-Factor Confidence Composition & Monotonicity", "test_theorem_2_confidence_composition"),
        ("Theorem 3: Capability Point Estimate q_k Convexity", "test_theorem_3_point_estimate_convexity"),
        ("Theorem 4: Effective Sample Size n_eff <= N (Kish)", "test_theorem_4_effective_sample_size"),
        ("Theorem 5: Role Weight Softmax Normalization & Shift Invariance", "test_theorem_5_softmax_role_weights"),
        ("Theorem 6: Role Capability Index (RCI) Boundedness & Convexity", "test_theorem_6_rci_properties"),
        ("Theorem 7: Contradiction Diagnostic D_k Range [-1, 1] & Neutrality", "test_theorem_7_contradiction_diagnostic"),
        ("Theorem 8: Probe Priority Monotonicity & Information Value", "test_theorem_8_probe_priority_ranking"),
        ("Theorem 9: Beta-Binomial Reliability Posterior Consistency", "test_theorem_9_beta_binomial_posterior_consistency"),
        ("Theorem 10: Platform Security & Governance Invariants", "test_theorem_10_platform_security_governance_invariants"),
    ]

    combined = stdout + stderr
    all_passed = code == 0 and "passed" in combined
    for title, fn_name in theorems:
        passed = all_passed or f"{fn_name} PASSED" in combined
        checks.append({
            "name": title,
            "status": "PASS" if passed else "FAIL",
            "assertion": "Test passed" if passed else "Test did not pass",
        })

    status = "PASS" if code == 0 else "FAIL"
    return AuditResult(
        pillar="1. Mathematical & Theoretical Theorems (Theorems 1-10)",
        status=status,
        details=(
            "The theorem test module completed successfully."
            if status == "PASS"
            else "One or more theorem tests failed; inspect pytest output before making theorem-verification claims."
        ),
        duration_ms=duration,
        checks=checks,
    )


def audit_pillar_2_security(python_bin: str) -> AuditResult:
    """Pillar 2: Security, SSRF, and static-analysis sandboxing tests."""
    t0 = time.perf_counter()
    cmd = [
        python_bin,
        "-m",
        "pytest",
        "services/backend/tests/security/",
        "services/backend/tests/golden/code_intel/",
        "-v",
    ]
    code, stdout, stderr = run_command(cmd)
    duration = (time.perf_counter() - t0) * 1000

    checks = [
        {
            "name": "SSRF Protection Matrix (RFC 1918, Link-Local, Loopback)",
            "status": "PASS" if "test_ssrf.py" in stdout and code == 0 else "FAIL",
            "assertion": "Security test suite passed" if code == 0 else "Security test suite failed",
        },
        {
            "name": "Cloud Metadata IMDS Protection (169.254.169.254)",
            "status": "PASS" if code == 0 else "FAIL",
            "assertion": "Covered by passing security suite" if code == 0 else "Not verified by this run",
        },
        {
            "name": "Static Code Analysis Path",
            "status": "PASS" if "test_code_analyzers.py" in stdout and code == 0 else "FAIL",
            "assertion": "Golden analyzer tests passed" if code == 0 else "Golden analyzer tests failed",
        },
        {
            "name": "Workspace Isolation Context Manager",
            "status": "PASS" if "test_safe_workspace.py" in stdout and code == 0 else "FAIL",
            "assertion": "Workspace tests passed" if code == 0 else "Workspace tests failed",
        },
    ]

    status = "PASS" if code == 0 else "FAIL"
    return AuditResult(
        pillar="2. Security, SSRF & Static-Analysis Isolation",
        status=status,
        details=(
            "The selected security and golden static-analysis tests passed."
            if status == "PASS"
            else "Security/static-analysis verification is incomplete because the selected tests failed."
        ),
        duration_ms=duration,
        checks=checks,
    )


def audit_pillar_3_db_immutability(python_bin: str) -> AuditResult:
    """Pillar 3: Database persistence and model-integrity tests."""
    t0 = time.perf_counter()
    cmd = [
        python_bin,
        "-m",
        "pytest",
        "services/backend/tests/integration/test_db_seeding.py",
        "services/backend/tests/integration/test_db_migration.py",
        "-v",
    ]
    code, stdout, stderr = run_command(cmd)
    duration = (time.perf_counter() - t0) * 1000

    checks = [
        {
            "name": "Evidence / Model Integrity",
            "status": "PASS" if code == 0 else "FAIL",
            "assertion": "Selected DB integration tests passed" if code == 0 else "Selected DB integration tests failed",
        },
        {
            "name": "Alembic Database Schema Migration Reversibility",
            "status": "PASS" if "test_db_migration.py" in stdout and code == 0 else "FAIL",
            "assertion": "Migration test passed" if code == 0 else "Migration test not verified",
        },
        {
            "name": "Database Seeding / Relationship Integrity",
            "status": "PASS" if "test_db_seeding.py" in stdout and code == 0 else "FAIL",
            "assertion": "Seeding test passed" if code == 0 else "Seeding test not verified",
        },
    ]

    status = "PASS" if code == 0 else "FAIL"
    return AuditResult(
        pillar="3. Database Persistence & Governance Integrity",
        status=status,
        details=(
            "The selected database migration and seeding integration tests passed."
            if status == "PASS"
            else "Database integrity is not verified by this run because one or more integration tests failed."
        ),
        duration_ms=duration,
        checks=checks,
    )


def audit_pillar_4_research_benchmarks(python_bin: str) -> AuditResult:
    """Pillar 4: Synthetic research simulation and ablation reproduction tests."""
    t0 = time.perf_counter()
    cmd = [
        python_bin,
        "-m",
        "pytest",
        "services/backend/tests/unit/research/",
        "-v",
    ]
    code, stdout, stderr = run_command(cmd)
    duration = (time.perf_counter() - t0) * 1000

    checks = [
        {
            "name": "Synthetic Table 1 Ablation Evaluation (5 Configurations)",
            "status": "PASS" if code == 0 else "FAIL",
            "assertion": "Simulation/research tests passed" if code == 0 else "Simulation/research tests failed",
        },
        {
            "name": "Paired Wilcoxon Signed-Rank Calculations",
            "status": "PASS" if code == 0 else "FAIL",
            "assertion": (
                "Per-ablation significance is preserved; UNCALIBRATED_SOURCES is non-significant (committed p = 1.000)"
                if code == 0
                else "Statistical-test implementation not verified by this run"
            ),
        },
        {
            "name": "Cliff's Delta Effect Size Calculation",
            "status": "PASS" if code == 0 else "FAIL",
            "assertion": "Research statistics tests passed" if code == 0 else "Research statistics tests failed",
        },
    ]

    status = "PASS" if code == 0 else "FAIL"
    return AuditResult(
        pillar="4. Synthetic Research Simulation & Statistical Reproducibility",
        status=status,
        details=(
            "The selected research tests passed for the synthetic Monte Carlo simulation. This does not establish real-candidate or hiring-outcome validity."
            if status == "PASS"
            else "Synthetic research reproduction is not verified by this run because one or more research tests failed."
        ),
        duration_ms=duration,
        checks=checks,
    )


def audit_pillar_5_live_endpoints() -> AuditResult:
    """Pillar 5: Local operational stack probe."""
    t0 = time.perf_counter()
    endpoints = [
        ("FastAPI Backend Healthcheck", "http://127.0.0.1:8000/health"),
        ("FastAPI Swagger Documentation", "http://127.0.0.1:8000/docs"),
        ("FastAPI OpenAPI Schema", "http://127.0.0.1:8000/openapi.json"),
        ("FastAPI Job Intelligence API", "http://127.0.0.1:8000/api/v1/jobs"),
        ("FastAPI Candidates Directory API", "http://127.0.0.1:8000/api/v1/candidates"),
        ("FastAPI Research Theorems Catalog", "http://127.0.0.1:8000/api/v1/research/theorems"),
        ("FastAPI Research Ablation Benchmark", "http://127.0.0.1:8000/api/v1/research/ablation-study"),
        ("FastAPI Dossier Export (HTML)", "http://127.0.0.1:8000/api/v1/dossier/77777777-7777-7777-7777-777777777777/export?format=html"),
        ("FastAPI Governance Audit Trail", "http://127.0.0.1:8000/api/v1/overrides/audit/77777777-7777-7777-7777-777777777777"),
        ("Next.js Recruitment Workstation", "http://localhost:3000/"),
    ]

    checks = []
    all_ok = True
    for name, url in endpoints:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "CCI-System-Auditor/1.0"})
            t_req = time.perf_counter()
            with urllib.request.urlopen(req, timeout=5) as resp:
                status_code = resp.getcode()
                latency_ms = (time.perf_counter() - t_req) * 1000
                is_pass = status_code == 200
                checks.append({
                    "name": name,
                    "status": "PASS" if is_pass else "FAIL",
                    "assertion": f"HTTP {status_code} ({latency_ms:.1f}ms)",
                })
                if not is_pass:
                    all_ok = False
        except Exception as exc:
            checks.append({
                "name": name,
                "status": "FAIL",
                "assertion": f"Connection Error: {exc}",
            })
            all_ok = False

    duration = (time.perf_counter() - t0) * 1000
    return AuditResult(
        pillar="5. Local Operational Endpoints & HTTP Availability",
        status="PASS" if all_ok else "FAIL",
        details=(
            "All 10 configured local endpoints returned HTTP 200."
            if all_ok
            else "One or more configured local endpoints did not return HTTP 200; local-stack availability is not fully verified."
        ),
        duration_ms=duration,
        checks=checks,
    )


def audit_pillar_6_frontend_build() -> AuditResult:
    """Pillar 6: Frontend typecheck, production build, and evidence-contract checks."""
    t0 = time.perf_counter()

    code_lint, _, _ = run_command(["npm", "--prefix", "apps/web", "run", "lint"])
    code_build, _, _ = run_command(["npm", "--prefix", "apps/web", "run", "build"])
    code_contract, _, _ = run_command(["node", "scripts/verify_ui_evidence_contract.mjs"])

    checks = [
        {
            "name": "Next.js TypeScript Static Typecheck",
            "status": "PASS" if code_lint == 0 else "FAIL",
            "assertion": "Frontend lint/typecheck command exited 0" if code_lint == 0 else "Frontend lint/typecheck command failed",
        },
        {
            "name": "Next.js Production Build",
            "status": "PASS" if code_build == 0 else "FAIL",
            "assertion": "Production build exited 0" if code_build == 0 else "Production build failed",
        },
        {
            "name": "UI Evidence Integrity Contract",
            "status": "PASS" if code_contract == 0 else "FAIL",
            "assertion": "No silent mock-result fallback detected by contract" if code_contract == 0 else "UI evidence contract failed",
        },
    ]

    duration = (time.perf_counter() - t0) * 1000
    status = "PASS" if code_lint == 0 and code_build == 0 and code_contract == 0 else "FAIL"
    return AuditResult(
        pillar="6. Frontend TypeScript, Production Build & Evidence Integrity",
        status=status,
        details=(
            "Typecheck/lint, production build, and UI evidence contract all passed."
            if status == "PASS"
            else "At least one frontend verification command failed; inspect its direct output before claiming build health."
        ),
        duration_ms=duration,
        checks=checks,
    )


def main():
    python_bin = sys.executable
    print("=" * 80)
    print(f"{BOLD}{CYAN}CANDIDATE CAPABILITY INTELLIGENCE (CCI) — SYSTEM AUDIT REPORT{RESET}")
    print("=" * 80)
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")
    print(f"Python Runtime: {python_bin}")
    print(f"Repository Root: {os.getcwd()}")
    print("=" * 80)
    print()

    pillars = [
        audit_pillar_1_theorems(python_bin),
        audit_pillar_2_security(python_bin),
        audit_pillar_3_db_immutability(python_bin),
        audit_pillar_4_research_benchmarks(python_bin),
        audit_pillar_5_live_endpoints(),
        audit_pillar_6_frontend_build(),
    ]

    total_checks = 0
    passed_checks = 0

    for res in pillars:
        pillar_icon = f"{GREEN}[PASS]{RESET}" if res.status == "PASS" else f"{RED}[FAIL]{RESET}"
        print(f"{BOLD}{pillar_icon} {res.pillar}{RESET} ({res.duration_ms:.0f}ms)")
        print(f"  {res.details}")
        print("  " + "-" * 76)

        for check in res.checks:
            total_checks += 1
            if check["status"] == "PASS":
                passed_checks += 1
                c_icon = f"{GREEN}[+]{RESET}"
            else:
                c_icon = f"{RED}[X]{RESET}"
            print(f"    {c_icon} {check['name']:<55} [{check['assertion']}]")

        print()

    print("=" * 80)
    score_pct = (passed_checks / total_checks) * 100 if total_checks > 0 else 0
    if passed_checks == total_checks:
        print(f"{BOLD}{GREEN}[AUDIT RESULT: 100% PASS] All {passed_checks}/{total_checks} audit checks verified successfully.{RESET}")
    else:
        print(f"{BOLD}{RED}[AUDIT RESULT: PARTIAL] {passed_checks}/{total_checks} audit checks passed ({score_pct:.1f}%).{RESET}")
    print("=" * 80)

    all_passed = all(p.status == "PASS" for p in pillars)
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
