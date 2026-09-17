#!/usr/bin/env python3
"""Candidate Capability Intelligence (CCI) — Strong Static & Security Audit Runner.

Executes a deeper suite of static analysis tools:
1. Mypy (--strict) for Backend Types
2. Flake8 for Backend Linting
3. Bandit for Security scanning (Backend)
4. Safety for Python Dependency vulnerabilities
5. NPM Audit for Frontend Vulnerabilities
6. ESLint for Frontend Code Quality
"""

import os
import subprocess
import sys
import time

CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"

def run_command(cmd, cwd=None):
    t0 = time.perf_counter()
    proc = subprocess.Popen(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        shell=(sys.platform == "win32"),
    )
    stdout, stderr = proc.communicate()
    duration = (time.perf_counter() - t0) * 1000
    return proc.returncode, stdout, stderr, duration

def print_result(name, code, stdout, stderr, duration):
    if code == 0:
        print(f"{GREEN}[PASS]{RESET} {BOLD}{name}{RESET} ({duration:.0f}ms)")
    else:
        print(f"{RED}[FAIL]{RESET} {BOLD}{name}{RESET} ({duration:.0f}ms)")
        print(f"{YELLOW}Output:{RESET}\n{stdout}\n{stderr}")
    print("-" * 80)
    return code == 0

def main():
    python_bin = sys.executable
    print("=" * 80)
    print(f"{BOLD}{CYAN}CCI — STRONG SECURITY & STATIC ANALYSIS AUDIT{RESET}")
    print("=" * 80)

    # 1. Mypy
    print("Running Mypy (Strict Type Checking)...")
    code, stdout, stderr, duration = run_command(
        [python_bin, "-m", "mypy", "--strict", "services/backend/src"]
    )
    # Mypy often complains on non-fully typed code, let's capture the result
    mypy_pass = print_result("Backend Typecheck (Mypy)", code, stdout, stderr, duration)

    # 2. Flake8
    print("Running Flake8 (Linting)...")
    code, stdout, stderr, duration = run_command(
        [python_bin, "-m", "flake8", "services/backend/src", "--max-line-length=120", "--ignore=E501"]
    )
    flake8_pass = print_result("Backend Linting (Flake8)", code, stdout, stderr, duration)

    # 3. Bandit
    print("Running Bandit (Security Scan)...")
    code, stdout, stderr, duration = run_command(
        [python_bin, "-m", "bandit", "-r", "services/backend/src", "-ll", "-ii"]
    )
    bandit_pass = print_result("Backend Security Scan (Bandit)", code, stdout, stderr, duration)

    # 4. Safety
    print("Running Safety (Dependency Vulnerabilities)...")
    code, stdout, stderr, duration = run_command(
        [python_bin, "-m", "safety", "check", "--bare"] 
    )
    safety_pass = print_result("Backend Dependencies (Safety)", code, stdout, stderr, duration)

    # 5. NPM Audit
    print("Running NPM Audit (Frontend Dependencies)...")
    code, stdout, stderr, duration = run_command(
        ["npm", "audit", "--audit-level=high"], cwd="apps/web"
    )
    npm_pass = print_result("Frontend Dependencies (NPM Audit)", code, stdout, stderr, duration)

    # 6. ESLint
    print("Running ESLint (Frontend Linting)...")
    code, stdout, stderr, duration = run_command(
        ["npm", "run", "lint"], cwd="apps/web"
    )
    eslint_pass = print_result("Frontend Linting (ESLint)", code, stdout, stderr, duration)

    results = [mypy_pass, flake8_pass, bandit_pass, safety_pass, npm_pass, eslint_pass]
    passed = sum(results)
    total = len(results)

    print("=" * 80)
    if passed == total:
        print(f"{BOLD}{GREEN}[STRONG AUDIT RESULT: 100% PASS] All {passed}/{total} strict checks verified successfully.{RESET}")
        sys.exit(0)
    else:
        print(f"{BOLD}{RED}[STRONG AUDIT RESULT: PARTIAL] {passed}/{total} strict checks passed.{RESET}")
        print("Please fix the reported issues for full compliance.")
        sys.exit(1)

if __name__ == "__main__":
    main()
