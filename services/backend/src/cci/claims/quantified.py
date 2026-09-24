"""Quantified claim extraction and independent artifact verification (Fix 41).

Enforces the core hardening invariants:
1. Every numerical or metric claim on resume/projects becomes a structured QuantifiedClaim:
   - metric
   - value
   - unit
   - context
   - source
   - verification status
   - supporting artifacts
   - limitations
2. Invariant: Do not verify a metric merely because the same number appears on a portfolio.
   Self-published portfolio echoes remain `portfolio_mention_only` and are never verified.
3. Invariant: Look for independent or technical supporting artifacts (e.g. test files,
   benchmark scripts, evaluation outputs, live deployment healthchecks).
4. Candidate code is NEVER executed.
"""

from __future__ import annotations

import re
from typing import Any, Mapping, Sequence
from uuid import NAMESPACE_URL, uuid5

from cci.domain.contracts import QuantifiedClaim


QUANTIFIED_CLAIM_LIMITATIONS: list[str] = [
    "Do not verify a metric merely because the same number appears on a portfolio.",
    "Quantitative claims require independent or technical supporting artifacts (e.g. benchmarks, test files, configs).",
    "Resume metrics are self-reported candidate declarations.",
]


def extract_quantified_claims_from_text(
    text: str,
    source: str = "resume",
    source_location: str | None = None,
) -> list[QuantifiedClaim]:
    """Extracts structured QuantifiedClaim instances from raw text declarations."""
    claims: list[QuantifiedClaim] = []
    seen: set[str] = set()

    # Pattern 1: Percentages (e.g. 95% accuracy, 99.9% uptime, 40% optimization)
    for m in re.finditer(r"\b(\d+(?:\.\d+)?)\s*%\s*([a-zA-Z_-]{3,25})(?!\w)", text, re.IGNORECASE):
        raw = m.group(0).strip()
        if raw.lower() in seen:
            continue
        seen.add(raw.lower())
        val_str, metric = m.group(1), m.group(2).strip().lower()
        val = float(val_str) if "." in val_str else int(val_str)
        cid = str(uuid5(NAMESPACE_URL, f"quant:{metric}:{val}:{raw.lower()}"))
        claims.append(
            QuantifiedClaim(
                claim_id=cid,
                metric=metric,
                value=val,
                unit="%",
                context=raw,
                source=source,
                source_location=source_location,
                verification_status="unverified",
                supporting_artifacts=[],
                limitations=list(QUANTIFIED_CLAIM_LIMITATIONS),
            )
        )

    # Pattern 2: Scale/counts (e.g. 10k users, 5B tokens, 500 tests, 20 deployed projects, 500k transactions)
    for m in re.finditer(
        r"\b(\d+(?:\.\d+)?[kKmMbB]?\+?)\s+(users|customers|queries|requests|req/s|rps|tx/s|transactions|tx|tokens|tests|test cases|deployed projects|projects|microservices|stars|commits)\b",
        text,
        re.IGNORECASE,
    ):
        raw = m.group(0).strip()
        if raw.lower() in seen:
            continue
        seen.add(raw.lower())
        val_str, unit = m.group(1), m.group(2).strip().lower()
        metric = unit.replace(" ", "_")
        cid = str(uuid5(NAMESPACE_URL, f"quant:{metric}:{val_str}:{raw.lower()}"))
        claims.append(
            QuantifiedClaim(
                claim_id=cid,
                metric=metric,
                value=val_str,
                unit=unit,
                context=raw,
                source=source,
                source_location=source_location,
                verification_status="unverified",
                supporting_artifacts=[],
                limitations=list(QUANTIFIED_CLAIM_LIMITATIONS),
            )
        )

    # Pattern 3: Latency/performance (e.g. 5ms latency, 100ms response time)
    for m in re.finditer(
        r"\b(\d+(?:\.\d+)?)\s*(ms|s|seconds)\s+(latency|response time|p99|p95)\b",
        text,
        re.IGNORECASE,
    ):
        raw = m.group(0).strip()
        if raw.lower() in seen:
            continue
        seen.add(raw.lower())
        val_str, unit, metric = m.group(1), m.group(2).strip().lower(), m.group(3).strip().lower()
        val = float(val_str) if "." in val_str else int(val_str)
        cid = str(uuid5(NAMESPACE_URL, f"quant:{metric}:{val}:{raw.lower()}"))
        claims.append(
            QuantifiedClaim(
                claim_id=cid,
                metric=metric.replace(" ", "_"),
                value=val,
                unit=unit,
                context=raw,
                source=source,
                source_location=source_location,
                verification_status="unverified",
                supporting_artifacts=[],
                limitations=list(QUANTIFIED_CLAIM_LIMITATIONS),
            )
        )

    # Pattern 4: Optimization/reduction (e.g. reduced latency by 40%, 40% optimization)
    for m in re.finditer(
        r"\b(reduced|optimized|improved|increased)\s+([a-zA-Z\s]{3,20})\s+by\s+(\d+(?:\.\d+)?(?:%|x)?)(?!\w)",
        text,
        re.IGNORECASE,
    ):
        raw = m.group(0).strip()
        if raw.lower() in seen:
            continue
        seen.add(raw.lower())
        action, target, change = m.group(1).lower(), m.group(2).strip().lower(), m.group(3).strip()
        metric = f"{action}_{target.replace(' ', '_')}"
        cid = str(uuid5(NAMESPACE_URL, f"quant:{metric}:{change}:{raw.lower()}"))
        claims.append(
            QuantifiedClaim(
                claim_id=cid,
                metric=metric,
                value=change,
                unit="%" if change.endswith("%") else "multiplier",
                context=raw,
                source=source,
                source_location=source_location,
                verification_status="unverified",
                supporting_artifacts=[],
                limitations=list(QUANTIFIED_CLAIM_LIMITATIONS),
            )
        )

    return claims


def verify_quantified_claim(
    claim: QuantifiedClaim,
    sources: Sequence[Mapping[str, Any]],
) -> QuantifiedClaim:
    """Verifies a QuantifiedClaim against independent technical artifacts and portfolio checks.

    Hardening Rules:
    1. "Do not verify a metric merely because the same number appears on a portfolio."
       If the metric appears in a portfolio source, mark as 'portfolio_mention_only'.
    2. "Look for independent or technical supporting artifact."
       - Tests: test files, pytest configs, test counts
       - Latency/Optimization: benchmark scripts, locustfile, perf configs
       - Accuracy/F1: evaluate.py, test_model.py, metrics.json
       - Deployed projects: actual reachable deployment receipts
       - Uptime: health check endpoints, SLO configs
    """
    context_lower = claim.context.lower()
    value_str = str(claim.value).lower().rstrip("%")
    metric = claim.metric.lower()

    # Collect all artifact paths across repository sources
    all_artifacts: list[str] = []
    github_sources = [s for s in sources if s.get("kind") == "github" or "github.com" in str(s.get("url", "")).lower()]
    for s in github_sources:
        for p in s.get("observed_files", []):
            if p not in all_artifacts:
                all_artifacts.append(p)
        repo_rev = s.get("repository_review", {})
        for t in repo_rev.get("technologies", []):
            p = t.get("path") if isinstance(t, dict) else None
            if p and p not in all_artifacts:
                all_artifacts.append(p)
        for attr in s.get("artifact_attributions", []):
            p = attr.get("artifact_path")
            if p and p not in all_artifacts:
                all_artifacts.append(p)

    # Check portfolio sources
    portfolio_sources = [
        s for s in sources
        if s.get("kind") in ("portfolio", "public_page", "linkedin")
        or any(k in str(s.get("url", "")).lower() for k in ("portfolio", "about", "blog"))
    ]
    portfolio_echo = False
    for ps in portfolio_sources:
        text = f"{ps.get('title', '')} {ps.get('excerpt', '')} {ps.get('body', '')}".lower()
        if value_str in text and (metric in text or claim.unit in text):
            portfolio_echo = True
            break

    supporting_artifacts: list[str] = []
    status = "unverified"
    limitations = list(claim.limitations)

    # Verification by technical category:
    if "test" in metric:
        # Technical supporting artifacts for tests
        test_arts = [p for p in all_artifacts if any(k in p.lower() for k in ("test", "spec", "pytest", "jest"))]
        if test_arts:
            supporting_artifacts.extend(test_arts[:10])
            status = "supported_by_artifacts"
        elif github_sources:
            # Repository was scanned, but zero tests found
            status = "unsupported"
            limitations.append("Repository scan observed zero test files despite numerical test claim.")

    elif "latency" in metric or "speed" in metric or "optimization" in metric:
        # Technical supporting artifacts for performance
        perf_arts = [p for p in all_artifacts if any(k in p.lower() for k in ("benchmark", "locust", "k6", "perf", "profile", "pytest-benchmark"))]
        if perf_arts:
            supporting_artifacts.extend(perf_arts[:5])
            status = "supported_by_artifacts"

    elif "accuracy" in metric or "precision" in metric or "recall" in metric or "f1" in metric:
        # Technical supporting artifacts for ML evaluation
        eval_arts = [p for p in all_artifacts if any(k in p.lower() for k in ("eval", "test_model", "metrics.json", "confusion_matrix", "classification_report"))]
        if eval_arts:
            supporting_artifacts.extend(eval_arts[:5])
            status = "supported_by_artifacts"

    elif "deployed" in metric or "project" in metric:
        # Technical supporting artifacts for deployments
        deploy_sources = [s for s in sources if s.get("kind") == "deployment" and s.get("status") in ("observed", "reachable", "fetched")]
        if deploy_sources:
            for ds in deploy_sources:
                supporting_artifacts.append(ds.get("url", ""))
            status = "supported_by_artifacts"

    elif "uptime" in metric:
        # Technical supporting artifacts for uptime / healthcheck
        health_arts = [p for p in all_artifacts if any(k in p.lower() for k in ("health", "status", "metrics", "prometheus", "alert"))]
        deploy_active = any(s.get("kind") == "deployment" and s.get("status") in ("observed", "reachable") for s in sources)
        if health_arts or deploy_active:
            if health_arts:
                supporting_artifacts.extend(health_arts[:5])
            status = "supported_by_artifacts"

    # Enforce Invariant: Do not verify a metric merely because the same number appears on a portfolio!
    if status == "unverified" and portfolio_echo:
        status = "portfolio_mention_only"
        limitations.append(
            "The same number appears on a public portfolio or personal website. "
            "Self-published portfolio mentions do not establish independent verification."
        )

    return claim.model_copy(
        update={
            "verification_status": status,
            "supporting_artifacts": supporting_artifacts,
            "limitations": limitations,
        }
    )


def extract_and_verify_all_quantified_claims(
    intake_or_manifest: Any,
    sources: Sequence[Mapping[str, Any]] = (),
) -> list[QuantifiedClaim]:
    """Extracts all quantitative claims from candidate intake and verifies each against technical artifacts."""
    raw_claims: list[QuantifiedClaim] = []

    # Get sections and project claims
    manifest = getattr(intake_or_manifest, "manifest", intake_or_manifest)
    review = getattr(intake_or_manifest, "resume_review", None)
    sections = getattr(review, "sections", {}) if review else {}

    # 1. From structured project claims
    project_claims = getattr(manifest, "project_claims", [])
    if isinstance(project_claims, Sequence):
        for i, proj in enumerate(project_claims):
            if isinstance(proj, Mapping):
                text = f"{proj.get('title', '')} {proj.get('description', '')}"
                loc = f"projects#{i}"
                raw_claims.extend(extract_quantified_claims_from_text(text, source="project_claim", source_location=loc))

    # 2. From resume sections (experience, summary, achievements, etc.)
    if isinstance(sections, Mapping):
        for sec_name, lines in sections.items():
            for i, line in enumerate(lines):
                loc = f"{sec_name}#{i}"
                raw_claims.extend(extract_quantified_claims_from_text(line, source=sec_name, source_location=loc))

    # Deduplicate by metric and value
    deduped: list[QuantifiedClaim] = []
    seen_keys: set[tuple[str, str]] = set()
    for c in raw_claims:
        key = (c.metric.lower(), str(c.value).lower())
        if key not in seen_keys:
            seen_keys.add(key)
            deduped.append(c)

    # Verify each claim against technical artifacts and portfolio echo rules
    return [verify_quantified_claim(c, sources) for c in deduped]
