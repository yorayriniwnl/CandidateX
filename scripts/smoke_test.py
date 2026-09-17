#!/usr/bin/env python3
"""Candidate Capability Intelligence (CCI) - Operational Smoke Test Script.

Validates end-to-end system availability, healthchecks, API endpoints,
and web dashboard connectivity across the Docker Compose or local stack.
"""

import argparse
import json
import sys
import time
from typing import Any, Dict
import urllib.error
import urllib.request


def check_http_endpoint(name: str, url: str, timeout: int = 5) -> Dict[str, Any]:
    """Performs an HTTP GET request to verify service responsiveness."""
    print(f"[*] Checking {name} at {url} ...", end=" ", flush=True)
    t0 = time.time()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "CCI-SmokeTest/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            latency = (time.time() - t0) * 1000.0
            status_code = response.status
            body = response.read().decode("utf-8")
            print(f"[OK] ({status_code}) in {latency:.1f}ms")
            return {
                "name": name,
                "url": url,
                "status": "UP",
                "status_code": status_code,
                "latency_ms": round(latency, 2),
                "body_preview": body[:120] if body else "",
            }
    except urllib.error.HTTPError as e:
        latency = (time.time() - t0) * 1000.0
        print(f"[HTTP {e.code}] in {latency:.1f}ms")
        return {
            "name": name,
            "url": url,
            "status": "HTTP_ERROR",
            "status_code": e.code,
            "latency_ms": round(latency, 2),
        }
    except Exception as e:
        print(f"[FAILED] {e}")
        return {
            "name": name,
            "url": url,
            "status": "UNREACHABLE",
            "error": str(e),
        }


def run_smoke_tests(backend_url: str, frontend_url: str) -> bool:
    print("=" * 80)
    print("CANDIDATE CAPABILITY INTELLIGENCE (CCI) - SYSTEM SMOKE TEST")
    print("=" * 80)

    checks = [
        ("FastAPI Backend Healthcheck", f"{backend_url.rstrip('/')}/health"),
        ("FastAPI Swagger Docs", f"{backend_url.rstrip('/')}/docs"),
        ("FastAPI OpenAPI Schema", f"{backend_url.rstrip('/')}/openapi.json"),
        ("FastAPI Jobs API", f"{backend_url.rstrip('/')}/api/v1/jobs"),
        ("FastAPI Candidates API", f"{backend_url.rstrip('/')}/api/v1/candidates"),
        ("FastAPI Research Theorems Catalog", f"{backend_url.rstrip('/')}/api/v1/research/theorems"),
        ("FastAPI Research Ablation Study", f"{backend_url.rstrip('/')}/api/v1/research/ablation-study"),
        ("Next.js Web Dashboard", f"{frontend_url.rstrip('/')}/"),
    ]

    results = []
    all_healthy = True

    for name, url in checks:
        res = check_http_endpoint(name, url)
        results.append(res)
        if res["status"] != "UP":
            all_healthy = False

    # If Candidates API is healthy, probe dynamic candidate dossier export
    try:
        cand_list_req = urllib.request.Request(f"{backend_url.rstrip('/')}/api/v1/candidates", headers={"User-Agent": "CCI-SmokeTest/1.0"})
        with urllib.request.urlopen(cand_list_req, timeout=5) as resp:
            cands = json.loads(resp.read().decode("utf-8"))
            if cands and len(cands) > 0:
                first_cand = cands[0]
                export_res = check_http_endpoint(
                    "FastAPI Dossier Export (HTML)",
                    f"{backend_url.rstrip('/')}/api/v1/dossier/{first_cand['id']}/export?format=html",
                )
                results.append(export_res)
                if export_res["status"] != "UP":
                    all_healthy = False

                audit_res = check_http_endpoint(
                    "FastAPI Candidate Audit Trail",
                    f"{backend_url.rstrip('/')}/api/v1/overrides/audit/{first_cand['id']}",
                )
                results.append(audit_res)
                if audit_res["status"] != "UP":
                    all_healthy = False
    except Exception:
        pass

    print("=" * 80)
    if all_healthy:
        print("[SUCCESS] All CCI stack services are healthy and responsive.")
    else:
        print("[NOTICE] Some endpoints were unreachable or returned non-200.")
        print("Note: To run against live services, start the stack first via:")
        print("      docker-compose up -d")
        print("      or launch backend and web services locally.")
    print("=" * 80)

    return all_healthy


def main() -> None:
    parser = argparse.ArgumentParser(description="CCI End-to-End Operational Smoke Test")
    parser.add_argument(
        "--backend-url",
        type=str,
        default="http://localhost:8000",
        help="Base URL for FastAPI backend (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--frontend-url",
        type=str,
        default="http://localhost:3000",
        help="Base URL for Next.js web frontend (default: http://localhost:3000)",
    )

    args = parser.parse_args()
    success = run_smoke_tests(args.backend_url, args.frontend_url)
    # Exit with code 0 if flags or dry test; exit 1 if target endpoints failed when explicitly probed
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
