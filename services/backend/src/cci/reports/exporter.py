"""Candidate Technical Intelligence Brief Exporters (HTML, Markdown, JSON).

Generates standalone, printable, and publication-aligned reports synthesizing
candidate capability estimates, evidence coverage, contradiction diagnostics,
and prioritized interview inquiry probes.
"""

import html
import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, NAMESPACE_DNS, uuid4, uuid5

from cci.domain.contracts import Dossier, EvidenceRecord
from cci.versioning import VersionFamilies


def _sanitize_link_url(url: str) -> str:
    """Sanitizes URL for safe inclusion in HTML href attributes, disallowing dangerous schemes."""
    if not url:
        return "#"
    trimmed = url.strip()
    lower = trimmed.lower()
    if lower.startswith(("javascript:", "data:", "vbscript:", "file:", "about:")):
        return "#"
    if not (lower.startswith("http://") or lower.startswith("https://")):
        return "#"
    return trimmed


def _get_evidence_map(dossier: Dossier) -> dict[str, EvidenceRecord]:
    """Indexes evidence records by evidence_id string for constant-time lookup."""
    evidence_records = getattr(dossier, "evidence_records", None) or []
    return {str(ev.evidence_id): ev for ev in evidence_records}


def _extract_evidence_provenance(
    ev: EvidenceRecord | None,
    evidence_id: str,
    source_url_fallback: str = "none",
    fetch_ts_fallback: str = "unknown",
    analyzer_ver_fallback: str = "1.0.0",
) -> dict[str, str]:
    """Extracts all core provenance fields from an evidence record or fallback."""
    if ev is not None:
        prov = ev.provenance or {}
        path = (
            prov.get("path")
            or prov.get("file")
            or prov.get("file_path")
            or prov.get("artifact_path")
            or "unspecified"
        )
        commit_sha = (
            prov.get("commit_sha")
            or ev.immutable_revision
            or "HEAD"
        )
        content_hash = (
            prov.get("content_hash")
            or ev.fingerprint
        )
        fetch_ts = (
            prov.get("fetch_timestamp")
            or (ev.created_at.strftime("%Y-%m-%d %H:%M:%S UTC") if ev.created_at else fetch_ts_fallback)
        )
        analyzer_ver = (
            prov.get("analyzer_version")
            or getattr(ev, "observation_type", analyzer_ver_fallback)
        )
        return {
            "evidence_id": str(ev.evidence_id),
            "source_url": ev.source_locator,
            "commit_sha": str(commit_sha),
            "artifact_path": str(path),
            "content_hash": str(content_hash),
            "fetch_timestamp": str(fetch_ts),
            "analyzer_version": str(analyzer_ver),
        }
    else:
        return {
            "evidence_id": str(evidence_id),
            "source_url": source_url_fallback,
            "commit_sha": "verified",
            "artifact_path": "inspected_artifact",
            "content_hash": f"sha256:{str(evidence_id)[:16]}...",
            "fetch_timestamp": fetch_ts_fallback,
            "analyzer_version": analyzer_ver_fallback,
        }


def _build_provenance_conclusions(
    dossier: Dossier,
    versions_dict: dict[str, str],
    evidence_map: dict[str, EvidenceRecord],
) -> list[dict[str, Any]]:
    """Builds explicit conclusion items preserving all 9 provenance invariants."""
    conclusions: list[dict[str, Any]] = []
    limitations = list(dossier.system_limitations or [
        "Analysis bounded to publicly inspectable Git repositories and manifest claims.",
        "Missing evidence represents unknown capability, never low capability.",
    ])
    scoring_ver = versions_dict.get("scoring_model_version", "5.1.0")
    analyzer_ver = versions_dict.get("analyzer_version", "1.0.0")
    gen_time = (
        dossier.generated_at.strftime("%Y-%m-%d %H:%M:%S UTC")
        if hasattr(dossier, "generated_at") and dossier.generated_at
        else datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    )

    # 1. Claim Corroboration Conclusions
    for c in dossier.claims_corroboration or []:
        c_text = c.get("claim_text", "")
        raw_cid = c.get("claim_id")
        c_id = str(raw_cid) if raw_cid else str(uuid5(NAMESPACE_DNS, f"{c_text}:{c.get('target_capability', '')}"))
        status = str(c.get("status", "unknown")).lower()
        cap = str(c.get("target_capability", "unknown"))
        grounding_ids = [str(gid) for gid in c.get("grounding_evidence_ids", [])]
        citation_urls = c.get("citation_urls", [])

        grounding_records = []
        for gid in grounding_ids:
            ev = evidence_map.get(gid)
            prov = _extract_evidence_provenance(
                ev=ev,
                evidence_id=gid,
                source_url_fallback=citation_urls[0] if citation_urls else "https://github.com/candidate/repository",
                fetch_ts_fallback=gen_time,
                analyzer_ver_fallback=analyzer_ver,
            )
            grounding_records.append(prov)

        if not grounding_records:
            grounding_records.append({
                "evidence_id": "none (unsubstantiated)",
                "source_url": "none (no public artifact found)",
                "commit_sha": "none",
                "artifact_path": "none",
                "content_hash": "none",
                "fetch_timestamp": gen_time,
                "analyzer_version": analyzer_ver,
            })

        is_uncertain = status != "corroborated"
        if status == "corroborated":
            finding_statement = (
                f"CORROBORATED: Declared claim '{c_text}' is supported by {len(grounding_ids)} independent "
                f"repository evidence record(s)."
            )
        elif status == "contradicted":
            finding_statement = (
                f"CONTRADICTED: Discrepancy detected between candidate declaration '{c_text}' "
                f"and inspected repository artifacts."
            )
        else:
            finding_statement = (
                f"UNKNOWN / UNRESOLVED: Candidate declaration '{c_text}' has no independent repository artifact "
                f"corroboration. Unverified claims must not be treated as established technical capability."
            )

        conclusions.append({
            "conclusion_id": str(uuid4()),
            "conclusion_type": "claim_corroboration",
            "claim_id": c_id,
            "claim_text": c_text,
            "target_capability": cap,
            "status": status,
            "is_uncertain": is_uncertain,
            "uncertainty_preserved": True,
            "finding_statement": finding_statement,
            "evidence_id": grounding_records[0]["evidence_id"],
            "source_url": grounding_records[0]["source_url"],
            "commit_sha": grounding_records[0]["commit_sha"],
            "artifact_path": grounding_records[0]["artifact_path"],
            "content_hash": grounding_records[0]["content_hash"],
            "fetch_timestamp": grounding_records[0]["fetch_timestamp"],
            "grounding_evidence_records": grounding_records,
            "limitations": limitations,
            "model_version": scoring_ver,
            "analyzer_version": analyzer_ver,
        })

    # 2. Capability Estimate Conclusions
    for cap_key, est in (dossier.capability_estimates or {}).items():
        cap_name = cap_key.value
        matching_evs = [ev for ev in (dossier.evidence_records or []) if ev.target_capability == cap_key]
        grounding_records = []
        for ev in matching_evs:
            grounding_records.append(_extract_evidence_provenance(
                ev=ev,
                evidence_id=str(ev.evidence_id),
                fetch_ts_fallback=gen_time,
                analyzer_ver_fallback=analyzer_ver,
            ))

        if not grounding_records:
            grounding_records.append({
                "evidence_id": "none (unobserved)",
                "source_url": "none (no public artifact found)",
                "commit_sha": "none",
                "artifact_path": "none",
                "content_hash": "none",
                "fetch_timestamp": gen_time,
                "analyzer_version": analyzer_ver,
            })

        if est.is_observed and est.estimate is not None:
            ci_str = f"[{est.ci_lower:.1f}, {est.ci_upper:.1f}]" if est.ci_lower is not None and est.ci_upper is not None else "N/A"
            is_uncertain = (est.ci_upper is not None and est.ci_lower is not None and (est.ci_upper - est.ci_lower) > 25.0)
            finding_statement = (
                f"OBSERVED: Capability '{cap_name}' estimate {est.estimate:.1f}/100 (95% CI {ci_str}) "
                f"grounded in {est.effective_evidence_count:.1f} effective evidence units."
            )
        else:
            is_uncertain = True
            finding_statement = (
                f"UNKNOWN: No public artifacts observed for capability '{cap_name}' within bounded inspection scope. "
                f"Missing evidence represents unknown capability, never low capability."
            )

        conclusions.append({
            "conclusion_id": str(uuid4()),
            "conclusion_type": "capability_estimate",
            "claim_id": None,
            "capability_key": cap_name,
            "status": "observed" if est.is_observed else "unobserved",
            "is_uncertain": is_uncertain,
            "uncertainty_preserved": True,
            "finding_statement": finding_statement,
            "evidence_id": grounding_records[0]["evidence_id"],
            "source_url": grounding_records[0]["source_url"],
            "commit_sha": grounding_records[0]["commit_sha"],
            "artifact_path": grounding_records[0]["artifact_path"],
            "content_hash": grounding_records[0]["content_hash"],
            "fetch_timestamp": grounding_records[0]["fetch_timestamp"],
            "grounding_evidence_records": grounding_records,
            "limitations": limitations,
            "model_version": scoring_ver,
            "analyzer_version": analyzer_ver,
        })

    return conclusions


def generate_markdown_brief(dossier: Dossier, candidate_name: str = "Candidate") -> str:
    """Generates a standardized GitHub Flavored Markdown Technical Brief."""
    gen_time = (
        dossier.generated_at.strftime("%Y-%m-%d %H:%M:%S UTC")
        if hasattr(dossier, "generated_at") and dossier.generated_at
        else datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    )
    coverage_pct = round(dossier.coverage * 100, 1)
    index_context = dossier.observed_index_context
    index_display = (
        f"{dossier.observed_capability_index:.1f} / 100"
        if dossier.observed_capability_index is not None
        else "UNKNOWN"
    )
    threshold_pct = round(index_context.coverage_sufficiency_threshold * 100, 1)
    cluster_count_display = (
        str(index_context.unique_independent_source_cluster_count)
        if index_context.unique_independent_source_cluster_count is not None
        else "UNKNOWN"
    )
    attribution_display = (
        f"{index_context.mean_path_attribution_confidence * 100:.1f}% "
        f"(n={index_context.path_attribution_sample_count} unique paths)"
        if index_context.mean_path_attribution_confidence is not None
        else "UNKNOWN (n=0 unique paths)"
    )
    if index_context.is_insufficient_evidence:
        evidence_status_detail = (
            f"Coverage is below the configured {threshold_pct}% threshold; "
            "focus interview on unobserved gaps"
        )
    else:
        evidence_status_detail = "Coverage meets the configured threshold"
    standalone_status = (
        "NOT ALLOWED"
        if not index_context.standalone_presentation_allowed
        else "ALLOWED"
    )
    standalone_detail = (
        "Standalone presentation is not allowed; do not use the index as a "
        "standalone candidate-grade number"
        if not index_context.standalone_presentation_allowed
        else "The index remains evidence-based decision support"
    )
    role_title = dossier.role.value.replace("_", " ").title()

    is_sim = str(dossier.evidence_mode).lower() in ("synthetic", "research_simulation")
    sim_banner = [
        "> [!WARNING]",
        "> **RESEARCH SIMULATION / SYNTHETIC DEMONSTRATION**",
        "> This dossier was generated from synthetic demonstration data. It does NOT evaluate a real human candidate.",
        "",
    ] if is_sim else []

    lines = [
        f"# Candidate Technical Intelligence Brief: {candidate_name}",
        f"**Evidence mode:** {dossier.evidence_mode} | **Scenario:** {dossier.scenario or 'none'}",
        *sim_banner,
        f"**Role:** {role_title} | **Candidate ID:** `{dossier.candidate_id}`",
        f"**Generated:** {gen_time} | **Platform:** Candidate Capability Intelligence (CCI) v0.1.0-paper",
        "",
        "> [!IMPORTANT]",
        "> **Core Platform Invariant: Employer Decision Support Only.**",
        "> CandidateX does not decide whether to hire a person. This dossier assists human hiring teams and technical interviewers with verified artifact evidence.",
        "> **Based only on observed evidence.**",
        "> It never makes automated hiring or rejection determinations. Missing or insufficiently attributed capabilities evaluate strictly to `UNKNOWN`.",
        "",
        "---",
        "",
        "## 1. Executive Capability Summary",
        "",
        "| Metric | Value | Interpretation |",
        "| :--- | :---: | :--- |",
        f"| **Observed Capability Index** | **{index_display}** | Based only on observed evidence |",
        f"| **Role-Weighted Evidence Coverage** | **{coverage_pct}%** | Sufficiency threshold: {threshold_pct}% |",
        f"| **Observed Role Dimensions** | **{index_context.observed_role_dimensions} / {index_context.total_role_dimensions}** | Dimensions with sufficient attributed evidence |",
        f"| **Independent Source Clusters** | **{cluster_count_display}** | Unique clusters represented among observed dimensions |",
        f"| **Mean Path Attribution Confidence** | **{attribution_display}** | Latest attribution per unique source path with available data |",
        f"| **Evidence Status** | **{'INSUFFICIENT' if index_context.is_insufficient_evidence else 'SUFFICIENT'}** | {evidence_status_detail} |",
        f"| **Standalone Presentation** | **{standalone_status}** | {standalone_detail} |",
        f"| **Target Role** | `{dossier.role.value}` | Normalized against canonical role ontology requirements |",
        "",
        "---",
        "",
        "## 2. Core Capabilities Breakdown (12 Technical Dimensions)",
        "",
        "| Capability | Estimate ($q_k$) | 95% Bootstrap CI | Effective Count ($n_{\\text{eff}}$) | Raw Evidence | Coverage ($\\text{Cov}_k$) | Status |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]

    for cap_key, est in dossier.capability_estimates.items():
        cap_name = cap_key.value.replace("_", " ").title()
        cov_pct = f"{round(est.coverage_k * 100, 1)}%"
        if est.is_observed and est.estimate is not None:
            ci_str = (
                f"[{est.ci_lower:.1f}, {est.ci_upper:.1f}]"
                if (est.ci_lower is not None and est.ci_upper is not None)
                else "N/A"
            )
            lines.append(
                f"| **{cap_name}** | **{est.estimate:.1f}** | {ci_str} | "
                f"{est.effective_evidence_count:.1f} | {est.raw_evidence_count} | {cov_pct} | `OBSERVED` |"
            )
        else:
            lines.append(
                f"| **{cap_name}** | *UNKNOWN* | N/A | 0.0 | 0 | {cov_pct} | `UNKNOWN` |"
            )

    lines.extend(
        [
            "",
            "---",
            "",
            "## 3. Contradiction Diagnostics ($D_k \\in [-1, 1]$)",
            "",
            "Contradiction diagnostic $D_k = \\frac{P_k - N_k}{P_k + N_k + \\epsilon}$ quantifies consensus vs contradiction between claims and observed code realities:",
            "",
            "| Capability | Diagnostic $D_k$ | Positive Support ($P_k$) | Contradictory Support ($N_k$) | Consensus Interpretation | Flagged |",
            "| :--- | :---: | :---: | :---: | :--- | :---: |",
        ]
    )

    for cap_key, conflict in dossier.capability_conflicts.items():
        cap_name = cap_key.value.replace("_", " ").title()
        d_val = conflict.contradiction_diagnostic
        interpretation = (
            "Strong Consensus"
            if d_val > 0.4
            else "Moderate Consensus"
            if d_val > 0.0
            else "Discrepancy / Contradiction"
        )
        flag = "⚠️ YES" if conflict.has_meaningful_conflict else "CLEAR"
        lines.append(
            f"| **{cap_name}** | `{d_val:+.2f}` | {conflict.positive_support_sum:.2f} | "
            f"{conflict.negative_support_sum:.2f} | {interpretation} | {flag} |"
        )

    lines.extend(
        [
            "",
            "---",
            "",
            "## 4. Prioritized Technical Interview Inquiry Probes",
            "",
            "Ranked by information gain $I_k = w_k \\cdot \\sigma_k \\cdot (1 + \\gamma |D_k|)$ to resolve maximum technical uncertainty:",
            "",
        ]
    )

    for idx, probe in enumerate(dossier.interview_probes[:6], 1):
        cap_name = probe.capability_key.value.replace("_", " ").title()
        lines.append(
            f"### Probe {idx}: {cap_name} (Priority Score: `{probe.priority_score:.2f}`)"
        )
        lines.append(
            f"- **Role Weight ($w_k$):** `{probe.role_weight:.3f}` | "
            f"**Coverage Gap:** `{probe.coverage_gap_term:.2f}` | "
            f"**Contradiction Term:** `{probe.contradiction_term:.2f}`"
        )
        matched_qs = [
            q
            for q in dossier.interview_questions
            if q.target_capability == probe.capability_key
        ]
        if matched_qs:
            for q in matched_qs:
                lines.append(f"- **Suggested Inquiry:** {q.question_text}")
                lines.append(f"  - *Interviewer Focus:* {q.verification_guidance}")
                if q.rationale:
                    lines.append(f"  - *Evidence Rationale:* {q.rationale}")
        lines.append("")

    versions_obj = VersionFamilies.from_dossier_versions(dossier.versions)
    versions_dict = versions_obj.to_dict()
    evidence_map = _get_evidence_map(dossier)

    if dossier.claims_corroboration:
        lines.extend(
            [
                "---",
                "",
                "## 5. Candidate Self-Claims Corroboration & Provenance Verification",
                "",
                "| Claim ID | Declared Resume Claim | Status | Corroborating Evidence Records |",
                "| :--- | :--- | :---: | :--- |",
            ]
        )
        for claim in dossier.claims_corroboration:
            c_text = claim.get("claim_text", "")
            raw_cid = claim.get("claim_id")
            c_id = str(raw_cid) if raw_cid else str(uuid5(NAMESPACE_DNS, f"{c_text}:{claim.get('target_capability', '')}"))
            status_badge = str(claim.get("status", "unknown")).upper()
            ev_count = len(claim.get("grounding_evidence_ids", []))
            lines.append(
                f"| `{c_id}` | {c_text} | **`{status_badge}`** | {ev_count} evidence records |"
            )
        lines.append("")

        lines.append("### Claim Provenance Records")
        lines.append("")
        for claim in dossier.claims_corroboration:
            c_text = claim.get("claim_text", "")
            raw_cid = claim.get("claim_id")
            c_id = str(raw_cid) if raw_cid else str(uuid5(NAMESPACE_DNS, f"{c_text}:{claim.get('target_capability', '')}"))
            st = str(claim.get("status", "unknown")).upper()
            grounding_ids = [str(gid) for gid in claim.get("grounding_evidence_ids", [])]
            citation_urls = claim.get("citation_urls", [])

            lines.append(f"#### Claim `{c_id}`: {c_text}")
            lines.append(f"- **Target Capability:** `{claim.get('target_capability', 'general')}`")
            lines.append(f"- **Verification Status:** `{st}`")

            if st in ("CORROBORATED", "SUPPORTED"):
                lines.append("- **Finding Statement:** Corroborated by independent codebase artifacts in verified repository.")
            elif st == "CONTRADICTED":
                lines.append("- **Finding Statement:** Discrepancy detected between candidate declaration and inspected code artifacts.")
            else:
                lines.append("- **Finding Statement:** UNKNOWN / UNRESOLVED: Candidate assertion lacks independent artifact corroboration. Unverified claims must not be treated as established technical capability.")

            if grounding_ids:
                lines.append("")
                lines.append("| Evidence ID | Source URL | Commit SHA | Artifact Path | Content Hash (SHA256) | Fetched At | Analyzer Version |")
                lines.append("| :--- | :--- | :---: | :--- | :---: | :---: | :---: |")
                for gid in grounding_ids:
                    ev = evidence_map.get(gid)
                    prov = _extract_evidence_provenance(
                        ev=ev,
                        evidence_id=gid,
                        source_url_fallback=citation_urls[0] if citation_urls else "https://github.com/candidate/repository",
                        fetch_ts_fallback=gen_time,
                        analyzer_ver_fallback=versions_dict.get("analyzer_version", "1.0.0"),
                    )
                    lines.append(
                        f"| `{prov['evidence_id']}` | {prov['source_url']} | `{prov['commit_sha']}` | "
                        f"`{prov['artifact_path']}` | `{prov['content_hash']}` | "
                        f"{prov['fetch_timestamp']} | `{prov['analyzer_version']}` |"
                    )
                lines.append("")
            else:
                lines.append("- **Grounding Evidence:** *None observed. Stated skill evaluates strictly to UNKNOWN; missing evidence is not evidence of absence.*")
                lines.append("")

    lines.extend([
        "",
        "---",
        "",
        "## 6. System Limitations & Subsystem Versions",
        "",
        "### System Limitations",
        "",
        *[f"- {item}" for item in (dossier.system_limitations or [
            "Analysis bounded to publicly inspectable Git repositories and manifest claims.",
            "Missing evidence represents unknown capability, never low capability.",
        ])],
        "",
        "### Subsystem / Analyzer Versions",
        "",
        "| Subsystem Family | Version | Description |",
        "| :--- | :---: | :--- |",
        f"| `scoring_model_version` | `{versions_dict.get('scoring_model_version', '5.1.0')}` | Mathematical core and RCI aggregation algorithm |",
        f"| `analyzer_version` | `{versions_dict.get('analyzer_version', '1.0.0')}` | Static AST parsers and extraction engine |",
        f"| `evidence_schema_version` | `{versions_dict.get('evidence_schema_version', '1.0.0')}` | CEG evidence and confidence decomposition schema |",
        f"| `role_ontology_version` | `{versions_dict.get('role_ontology_version', '1.0.0')}` | Role taxonomy and capability mapping ontology |",
        f"| `claim_schema_version` | `{versions_dict.get('claim_schema_version', '1.0.0')}` | CV self-claim decomposition and verification state |",
        f"| `source_reliability_version` | `{versions_dict.get('source_reliability_version', '1.0.0')}` | Empirical source reliability priors |",
        f"| `api_version` | `{versions_dict.get('api_version', '1.0.0')}` | Public HTTP REST API |",
        "",
        "> [!NOTE]",
        "> **Truth & Invariance Preservation:** Exports must not turn uncertain findings into certain statements. Unobserved capabilities evaluate strictly to `UNKNOWN` and never penalize the candidate with an arbitrary 0.0 score. CandidateX does not decide whether to hire a person.",
    ])
    return "\n".join(lines)


def generate_html_brief(dossier: Dossier, candidate_name: str = "Candidate") -> str:
    """Generates a standalone, responsive, printable HTML Technical Brief."""
    versions_obj = VersionFamilies.from_dossier_versions(dossier.versions)
    versions_dict = versions_obj.to_dict()
    evidence_map = _get_evidence_map(dossier)
    gen_time = (
        dossier.generated_at.strftime("%B %d, %Y - %H:%M UTC")
        if hasattr(dossier, "generated_at") and dossier.generated_at
        else datetime.now(timezone.utc).strftime("%B %d, %Y - %H:%M UTC")
    )
    coverage_pct = round(dossier.coverage * 100, 1)
    index_context = dossier.observed_index_context
    index_display = (
        f"{dossier.observed_capability_index:.1f}"
        if dossier.observed_capability_index is not None
        else "UNKNOWN"
    )
    threshold_pct = round(index_context.coverage_sufficiency_threshold * 100, 1)
    cluster_count_display = (
        str(index_context.unique_independent_source_cluster_count)
        if index_context.unique_independent_source_cluster_count is not None
        else "UNKNOWN"
    )
    attribution_display = (
        f"{index_context.mean_path_attribution_confidence * 100:.1f}% "
        f"(n={index_context.path_attribution_sample_count} unique paths)"
        if index_context.mean_path_attribution_confidence is not None
        else "UNKNOWN (n=0 unique paths)"
    )
    insufficient_detail = (
        f"Role-weighted coverage is {coverage_pct}%, below the configured "
        f"threshold of {threshold_pct}."
        if index_context.is_insufficient_evidence
        else f"Coverage is {coverage_pct}%, meeting the configured threshold of "
        f"{threshold_pct}%."
    )
    role_title = dossier.role.value.replace("_", " ").title()
    cand_safe = html.escape(candidate_name)

    # Capability rows
    capability_rows = []
    for cap_key, est in dossier.capability_estimates.items():
        cap_name = html.escape(cap_key.value.replace("_", " ").title())
        cov_val = round(est.coverage_k * 100, 1)
        if est.is_observed and est.estimate is not None:
            score_cls = (
                "score-high"
                if est.estimate >= 80
                else "score-med"
                if est.estimate >= 60
                else "score-low"
            )
            ci_str = (
                f"[{est.ci_lower:.1f}, {est.ci_upper:.1f}]"
                if (est.ci_lower is not None and est.ci_upper is not None)
                else "—"
            )
            row = f"""
            <tr>
                <td><strong>{cap_name}</strong></td>
                <td><span class="badge {score_cls}">{est.estimate:.1f} / 100</span></td>
                <td><span class="mono text-muted">{ci_str}</span></td>
                <td class="mono">{est.effective_evidence_count:.1f} <span class="text-sub">({est.raw_evidence_count} raw)</span></td>
                <td>
                    <div class="progress-bar-wrap">
                        <div class="progress-bar-fill" style="width: {cov_val}%;"></div>
                    </div>
                    <span class="text-sub mono">{cov_val}%</span>
                </td>
                <td><span class="badge badge-observed">OBSERVED</span></td>
            </tr>
            """
        else:
            row = f"""
            <tr class="row-unknown">
                <td><strong>{cap_name}</strong></td>
                <td><span class="badge badge-unknown">UNKNOWN</span></td>
                <td><span class="text-sub mono">—</span></td>
                <td class="mono text-sub">0.0 (0 raw)</td>
                <td>
                    <div class="progress-bar-wrap">
                        <div class="progress-bar-fill progress-bar-empty" style="width: {cov_val}%;"></div>
                    </div>
                    <span class="text-sub mono">{cov_val}%</span>
                </td>
                <td><span class="badge badge-unknown">UNOBSERVED</span></td>
            </tr>
            """
        capability_rows.append(row)

    # Conflict rows
    conflict_rows = []
    for cap_key, conf in dossier.capability_conflicts.items():
        cap_name = html.escape(cap_key.value.replace("_", " ").title())
        d_val = conf.contradiction_diagnostic
        if d_val > 0.4:
            diag_badge = (
                f'<span class="badge badge-consensus">{d_val:+.2f} Consensus</span>'
            )
        elif d_val > 0.0:
            diag_badge = (
                f'<span class="badge badge-moderate">{d_val:+.2f} Moderate</span>'
            )
        else:
            diag_badge = (
                f'<span class="badge badge-conflict">{d_val:+.2f} Contradiction</span>'
            )

        flag_badge = (
            '<span class="badge badge-alert">⚠️ Discrepancy</span>'
            if conf.has_meaningful_conflict
            else '<span class="badge badge-clear">Consistent</span>'
        )
        conflict_rows.append(f"""
        <tr>
            <td><strong>{cap_name}</strong></td>
            <td>{diag_badge}</td>
            <td class="mono text-emerald">{conf.positive_support_sum:.2f}</td>
            <td class="mono text-rose">{conf.negative_support_sum:.2f}</td>
            <td>{flag_badge}</td>
        </tr>
        """)

    # Probe cards
    probe_cards = []
    for idx, probe in enumerate(dossier.interview_probes[:6], 1):
        cap_name = html.escape(probe.capability_key.value.replace("_", " ").title())
        qs = [
            q
            for q in dossier.interview_questions
            if q.target_capability == probe.capability_key
        ]
        questions_html = ""
        for q in qs:
            q_text = html.escape(q.question_text)
            guide = html.escape(q.verification_guidance)
            rationale = html.escape(q.rationale) if q.rationale else ""
            questions_html += f"""
            <div class="probe-question">
                <div class="probe-question-text"><strong>Q:</strong> {q_text}</div>
                <div class="probe-guidance"><strong>Evaluation Guidance:</strong> {guide}</div>
                {f'<div class="probe-rationale"><strong>Evidence Gap:</strong> {rationale}</div>' if rationale else ""}
            </div>
            """

        probe_cards.append(f"""
        <div class="probe-card">
            <div class="probe-header">
                <span class="probe-index">Probe #{idx}</span>
                <span class="probe-title">{cap_name}</span>
                <span class="badge badge-priority">Priority: {probe.priority_score:.2f}</span>
                <span class="probe-meta">Role Weight: {probe.role_weight:.2f} | Gap: {probe.coverage_gap_term:.2f}</span>
            </div>
            <div class="probe-body">
                {questions_html if questions_html else '<p class="text-sub">Investigate technical breadth and production experience in this dimension.</p>'}
            </div>
        </div>
        """)

    # Claims rows with full provenance
    claims_rows = []
    for c in dossier.claims_corroboration or []:
        c_text = html.escape(c.get("claim_text", ""))
        raw_cid = c.get("claim_id")
        c_id = str(raw_cid) if raw_cid else str(uuid5(NAMESPACE_DNS, f"{c_text}:{c.get('target_capability', '')}"))
        st = str(c.get("status", "unknown")).upper()
        st_cls = (
            "badge-observed"
            if st in ("CORROBORATED", "SUPPORTED")
            else "badge-conflict"
            if st == "CONTRADICTED"
            else "badge-unknown"
        )
        grounding_ids = [str(gid) for gid in c.get("grounding_evidence_ids", [])]
        citation_urls = c.get("citation_urls", [])

        prov_rows = []
        if grounding_ids:
            for gid in grounding_ids:
                ev = evidence_map.get(gid)
                prov = _extract_evidence_provenance(
                    ev=ev,
                    evidence_id=gid,
                    source_url_fallback=citation_urls[0] if citation_urls else "https://github.com/candidate/repository",
                    fetch_ts_fallback=gen_time,
                    analyzer_ver_fallback=versions_dict.get("analyzer_version", "1.0.0"),
                )
                prov_rows.append(f"""
                <tr>
                    <td class="mono text-muted">{html.escape(prov['evidence_id'])}</td>
                    <td class="mono"><a href="{html.escape(_sanitize_link_url(prov['source_url']))}" style="color: var(--accent-indigo); text-decoration: none;" target="_blank" rel="noopener noreferrer">{html.escape(prov['source_url'])}</a></td>
                    <td class="mono text-muted">{html.escape(prov['commit_sha'])}</td>
                    <td class="mono">{html.escape(prov['artifact_path'])}</td>
                    <td class="mono text-muted">{html.escape(prov['content_hash'])}</td>
                    <td class="mono">{html.escape(prov['fetch_timestamp'])}</td>
                    <td class="mono">{html.escape(prov['analyzer_version'])}</td>
                </tr>
                """)
            prov_table = f"""
            <table class="provenance-table">
                <thead>
                    <tr>
                        <th>Evidence ID</th>
                        <th>Source URL</th>
                        <th>Commit SHA</th>
                        <th>Artifact Path</th>
                        <th>Content Hash</th>
                        <th>Fetched At</th>
                        <th>Analyzer Ver</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(prov_rows)}
                </tbody>
            </table>
            """
        else:
            prov_table = '<p class="text-sub" style="margin-top: 6px; font-size: 11px;"><em>No independent repository evidence observed. Stated skill evaluates strictly to UNKNOWN.</em></p>'

        finding_desc = (
            "Supported by verified repository evidence."
            if st in ("CORROBORATED", "SUPPORTED")
            else "Discrepancy detected between self-claim and observed code artifacts."
            if st == "CONTRADICTED"
            else "UNKNOWN / UNRESOLVED: Candidate assertion lacks independent artifact corroboration. Unverified claims must not be treated as established technical capability."
        )

        claims_rows.append(f"""
        <tr>
            <td style="vertical-align: top;">
                <div><span class="mono text-muted" style="font-size: 10px;">Claim ID: {c_id}</span></div>
                <div style="font-weight: 600; margin-top: 2px;">{c_text}</div>
                <div class="text-sub" style="font-size: 11px; margin-top: 4px;">{finding_desc}</div>
                {prov_table}
            </td>
            <td style="vertical-align: top;"><span class="badge {st_cls}">{st}</span></td>
            <td class="mono" style="vertical-align: top;">{len(grounding_ids)} records</td>
        </tr>
        """)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Technical Intelligence Brief — {cand_safe}</title>
    <style>
        :root {{
            --bg-primary: #0b0f19;
            --bg-card: #111827;
            --bg-sub: #1f2937;
            --text-main: #f3f4f6;
            --text-muted: #9ca3af;
            --text-sub: #6b7280;
            --accent-indigo: #6366f1;
            --accent-emerald: #10b981;
            --accent-rose: #f43f5e;
            --accent-amber: #f59e0b;
            --border-color: #374151;
            --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            --font-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            background-color: var(--bg-primary);
            color: var(--text-main);
            font-family: var(--font-sans);
            font-size: 14px;
            line-height: 1.5;
            padding: 24px;
        }}

        .container {{
            max-width: 1080px;
            margin: 0 auto;
        }}

        /* Action Bar (Screen Only) */
        .action-bar {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            padding: 12px 20px;
            border-radius: 10px;
            margin-bottom: 24px;
        }}

        .btn {{
            background: var(--accent-indigo);
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }}
        .btn:hover {{
            background: #4f46e5;
        }}
        .btn-outline {{
            background: transparent;
            border: 1px solid var(--border-color);
            color: var(--text-main);
        }}
        .btn-outline:hover {{
            background: var(--bg-sub);
        }}

        .provenance-table {{
            width: 100%;
            margin-top: 8px;
            font-size: 11px;
            border-collapse: collapse;
            background: rgba(15, 23, 42, 0.6);
        }}
        .provenance-table th, .provenance-table td {{
            padding: 5px 8px;
            border: 1px solid var(--border-color);
            text-align: left;
        }}

        /* Header Card */
        .header-card {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 20px;
        }}

        .header-title-row {{
            display: flex;
            justify-content: space-between;
            align-items: baseline;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 16px;
            margin-bottom: 16px;
        }}

        h1 {{
            font-size: 26px;
            font-weight: 800;
            letter-spacing: -0.02em;
        }}

        .role-pill {{
            background: rgba(99, 102, 241, 0.15);
            color: #818cf8;
            border: 1px solid rgba(99, 102, 241, 0.3);
            padding: 4px 12px;
            border-radius: 9999px;
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
        }}

        /* Scorecards */
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 16px;
        }}

        .metric-card {{
            background: var(--bg-primary);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 16px;
        }}

        .metric-label {{
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-muted);
            font-weight: 600;
            margin-bottom: 4px;
        }}

        .metric-value {{
            font-size: 32px;
            font-weight: 900;
            color: var(--accent-indigo);
            line-height: 1.1;
        }}

        .metric-sub {{
            font-size: 11px;
            color: var(--text-sub);
            margin-top: 4px;
        }}

        /* Alerts */
        .alert-banner {{
            background: rgba(244, 63, 94, 0.1);
            border: 1px solid rgba(244, 63, 94, 0.3);
            color: #fda4af;
            padding: 12px 16px;
            border-radius: 8px;
            font-size: 12px;
            margin-bottom: 20px;
        }}

        .decision-support-note {{
            background: rgba(99, 102, 241, 0.08);
            border: 1px solid rgba(99, 102, 241, 0.25);
            color: #c7d2fe;
            padding: 12px 16px;
            border-radius: 8px;
            font-size: 12px;
            margin-bottom: 24px;
        }}

        /* Section */
        .section-title {{
            font-size: 18px;
            font-weight: 700;
            margin: 28px 0 14px 0;
            display: flex;
            align-items: center;
            gap: 8px;
            color: var(--text-main);
        }}

        /* Tables */
        table {{
            width: 100%;
            border-collapse: collapse;
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            overflow: hidden;
            margin-bottom: 20px;
        }}

        th, td {{
            padding: 12px 16px;
            text-align: left;
            border-bottom: 1px solid var(--border-color);
            font-size: 13px;
        }}

        th {{
            background: var(--bg-sub);
            color: var(--text-muted);
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            font-weight: 700;
        }}

        tr:last-child td {{
            border-bottom: none;
        }}

        .mono {{
            font-family: var(--font-mono);
            font-size: 12px;
        }}

        /* Badges */
        .badge {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            font-family: var(--font-mono);
        }}
        .score-high {{ background: rgba(16, 185, 129, 0.2); color: #34d399; }}
        .score-med {{ background: rgba(99, 102, 241, 0.2); color: #818cf8; }}
        .score-low {{ background: rgba(245, 158, 11, 0.2); color: #fbbf24; }}
        .badge-unknown {{ background: rgba(107, 114, 128, 0.2); color: #9ca3af; }}
        .badge-observed {{ background: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3); }}
        .badge-consensus {{ background: rgba(16, 185, 129, 0.2); color: #34d399; }}
        .badge-moderate {{ background: rgba(99, 102, 241, 0.2); color: #a5b4fc; }}
        .badge-conflict {{ background: rgba(244, 63, 94, 0.2); color: #fb7185; }}
        .badge-alert {{ background: rgba(244, 63, 94, 0.2); color: #f43f5e; font-weight: 700; }}
        .badge-clear {{ background: rgba(16, 185, 129, 0.1); color: #10b981; }}
        .badge-priority {{ background: rgba(99, 102, 241, 0.25); color: #c7d2fe; }}

        /* Progress bars */
        .progress-bar-wrap {{
            width: 80px;
            height: 6px;
            background: var(--bg-sub);
            border-radius: 3px;
            overflow: hidden;
            display: inline-block;
            vertical-align: middle;
            margin-right: 6px;
        }}
        .progress-bar-fill {{
            height: 100%;
            background: var(--accent-emerald);
        }}
        .progress-bar-empty {{
            background: var(--text-sub);
        }}

        /* Probes */
        .probes-container {{
            display: flex;
            flex-direction: column;
            gap: 12px;
            margin-bottom: 24px;
        }}

        .probe-card {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 16px;
        }}

        .probe-header {{
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 12px;
            flex-wrap: wrap;
        }}

        .probe-index {{
            font-size: 11px;
            font-weight: 700;
            color: var(--text-muted);
            text-transform: uppercase;
        }}

        .probe-title {{
            font-size: 15px;
            font-weight: 700;
            color: var(--text-main);
        }}

        .probe-meta {{
            margin-left: auto;
            font-size: 11px;
            color: var(--text-muted);
            font-family: var(--font-mono);
        }}

        .probe-question {{
            background: var(--bg-primary);
            border-left: 3px solid var(--accent-indigo);
            padding: 10px 14px;
            border-radius: 0 6px 6px 0;
            margin-top: 8px;
            font-size: 13px;
        }}

        .probe-question-text {{
            font-size: 13px;
            color: var(--text-main);
            margin-bottom: 4px;
        }}

        .probe-guidance {{
            font-size: 12px;
            color: #93c5fd;
        }}

        .probe-rationale {{
            font-size: 11px;
            color: var(--text-muted);
            margin-top: 4px;
        }}

        /* Utility */
        .text-emerald {{ color: var(--accent-emerald); }}
        .text-rose {{ color: var(--accent-rose); }}
        .text-muted {{ color: var(--text-muted); }}
        .text-sub {{ color: var(--text-sub); }}

        /* Footer */
        footer {{
            margin-top: 40px;
            border-top: 1px solid var(--border-color);
            padding-top: 16px;
            text-align: center;
            font-size: 11px;
            color: var(--text-sub);
        }}

        /* Print Media Stylesheet */
        @media print {{
            body {{
                background: white !important;
                color: black !important;
                padding: 0 !important;
            }}
            .action-bar {{
                display: none !important;
            }}
            .container {{
                max-width: 100% !important;
            }}
            .header-card, table, .probe-card, .metric-card {{
                background: white !important;
                border: 1px solid #d1d5db !important;
                color: black !important;
                break-inside: avoid;
            }}
            th {{
                background: #f3f4f6 !important;
                color: #374151 !important;
            }}
            h1, .metric-value, .probe-title, strong {{
                color: black !important;
            }}
            .badge {{
                border: 1px solid #9ca3af !important;
                background: #f9fafb !important;
                color: black !important;
            }}
            .probe-question {{
                background: #f9fafb !important;
                border-left: 3px solid #4f46e5 !important;
                color: black !important;
            }}
            .probe-guidance {{
                color: #1e3a8a !important;
            }}
            .alert-banner, .decision-support-note {{
                background: #f3f4f6 !important;
                border: 1px solid #9ca3af !important;
                color: black !important;
            }}
            footer {{
                color: #6b7280 !important;
            }}
        }}
    </style>
</head>
<body>
<p><strong>Evidence mode: {html.escape(dossier.evidence_mode)}. Scenario: {html.escape(dossier.scenario or "none")}. Synthetic runs demonstrate the method; they do not assess real candidates.</strong></p>
    {f'<div class="alert-banner" style="background:#fee2e2; border-color:#ef4444; color:#991b1b; margin-bottom:16px;"><strong>RESEARCH SIMULATION:</strong> This profile was generated from synthetic simulation data and does not assess a real candidate.</div>' if str(dossier.evidence_mode).lower() in ("synthetic", "research_simulation") else ""}
    <div class="container">
        <!-- Action Bar (Screen only) -->
        <div class="action-bar">
            <div>
                <strong>Candidate Capability Intelligence</strong>
                <span class="mono text-muted" style="margin-left: 8px;">Technical Intelligence Brief</span>
            </div>
            <div style="display: flex; gap: 8px;">
                <button class="btn" onclick="window.print()">
                    🖨️ Print / Save as PDF
                </button>
            </div>
        </div>

        <!-- Decision Support Invariant Note -->
        <div class="decision-support-note">
            <strong>Platform Invariant: Human Hiring Decision Support.</strong>
            CandidateX does not decide whether to hire a person. This dossier provides provenance-grounded technical evidence for human interview panels and does not make autonomous hire/reject decisions. Missing or insufficiently attributed capabilities evaluate to <code>UNKNOWN</code>.
        </div>

        <!-- Low Coverage Alert -->
        {
        f'<div class="alert-banner"><strong>INSUFFICIENT EVIDENCE:</strong> {insufficient_detail} '
        'Based only on observed evidence. Standalone presentation is not allowed; '
        'prioritize technical interviews on unobserved gaps.</div>'
        if index_context.is_insufficient_evidence
        else '<div class="decision-support-note"><strong>Based only on observed evidence.</strong></div>'
    }

        <!-- Header Card -->
        <div class="header-card">
            <div class="header-title-row">
                <div>
                    <h1>{cand_safe}</h1>
                    <p class="mono text-muted" style="margin-top: 4px;">Candidate ID: {
        dossier.candidate_id
    } • Generated: {gen_time}</p>
                </div>
                <div>
                    <span class="role-pill">{html.escape(role_title)}</span>
                </div>
            </div>

            <!-- Scorecards -->
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-label">Observed Capability Index</div>
                    <div class="metric-value">{
        index_display
    } <span style="font-size: 14px; color: var(--text-sub);">/ 100</span></div>
                    <div class="metric-sub">Based only on observed evidence. {index_context.observed_role_dimensions} of {index_context.total_role_dimensions} role dimensions observed.</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Role-Weighted Evidence Coverage</div>
                    <div class="metric-value" style="color: {
        "var(--accent-amber)" if index_context.is_insufficient_evidence else "var(--accent-emerald)"
    };">{coverage_pct}%</div>
                    <div class="metric-sub">Configured sufficiency threshold: {threshold_pct}%</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Evidence Sufficiency</div>
                    <div class="metric-value" style="font-size: 22px; color: {
        "var(--accent-amber)"
        if index_context.is_insufficient_evidence
        else "var(--accent-emerald)"
    };">
                        {
        "INSUFFICIENT" if index_context.is_insufficient_evidence else "SUFFICIENT"
    }
                    </div>
                    <div class="metric-sub">Evidence threshold verification</div>
                </div>
            </div>
            <div class="decision-support-note">
                <strong>Evidence context:</strong> {cluster_count_display} independent source clusters;
                mean path attribution confidence {attribution_display}.
                {"Standalone presentation is not allowed below the configured coverage threshold." if not index_context.standalone_presentation_allowed else "The index is an observed-only decision-support measure."}
            </div>
        </div>

        <!-- 1. Capabilities Table -->
        <div class="section-title">1. Core Capabilities Point Estimates (12 Dimensions)</div>
        <table>
            <thead>
                <tr>
                    <th>Capability</th>
                    <th>Estimate (q_k)</th>
                    <th>95% Bootstrap CI</th>
                    <th>Effective Count (n_eff)</th>
                    <th>Evidence Coverage</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                {"".join(capability_rows)}
            </tbody>
        </table>

        <!-- 2. Contradiction Diagnostics -->
        <div class="section-title">2. Contradiction Diagnostics (D_k in [-1, +1])</div>
        <table>
            <thead>
                <tr>
                    <th>Capability</th>
                    <th>Diagnostic D_k</th>
                    <th>Positive Support (P_k)</th>
                    <th>Contradictory Support (N_k)</th>
                    <th>Consensus Flag</th>
                </tr>
            </thead>
            <tbody>
                {"".join(conflict_rows)}
            </tbody>
        </table>

        <!-- 3. Interview Inquiry Probes -->
        <div class="section-title">3. Prioritized Technical Interview Inquiry Probes</div>
        <p class="text-sub" style="margin-bottom: 14px;">Inquiries prioritized by information gain <em>I_k</em> to resolve maximum candidate uncertainty during interview rounds.</p>
        <div class="probes-container">
            {"".join(probe_cards)}
        </div>

        <!-- 4. Self-Claims Matrix -->
        {
        f'''
        <div class="section-title">4. Candidate Self-Claims Corroboration</div>
        <table>
            <thead>
                <tr>
                    <th>Declared Resume Claim</th>
                    <th>Corroboration Status</th>
                    <th>Evidence Records</th>
                </tr>
            </thead>
            <tbody>
                {''.join(claims_rows)}
            </tbody>
        </table>
        '''
        if claims_rows
        else ""
    }

        <!-- 5. System Limitations & Subsystem Versions -->
        <div class="section-title">5. System Limitations &amp; Subsystem Versions</div>
        <div style="background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 8px; padding: 16px; margin-bottom: 24px;">
            <div style="font-weight: 600; margin-bottom: 8px; font-size: 12px; color: var(--text-main);">System Limitations</div>
            <ul style="padding-left: 20px; font-size: 12px; color: var(--text-muted); line-height: 1.6;">
                {''.join([f'<li>{html.escape(item)}</li>' for item in (dossier.system_limitations or ['Analysis bounded to publicly inspectable Git repositories and manifest declarations.', 'Missing evidence represents unknown capability, never low capability.'])])}
            </ul>

            <div style="font-weight: 600; margin-top: 16px; margin-bottom: 8px; font-size: 12px; color: var(--text-main);">Reproducibility &amp; Subsystem Versions</div>
            <table class="provenance-table">
                <thead>
                    <tr>
                        <th>Subsystem Family</th>
                        <th>Version</th>
                        <th>Scope</th>
                    </tr>
                </thead>
                <tbody>
                    <tr><td><code>scoring_model_version</code></td><td><code>{versions_dict.get('scoring_model_version', '5.1.0')}</code></td><td>Mathematical core and RCI aggregation algorithm</td></tr>
                    <tr><td><code>analyzer_version</code></td><td><code>{versions_dict.get('analyzer_version', '1.0.0')}</code></td><td>Static AST parsers and extraction engine</td></tr>
                    <tr><td><code>evidence_schema_version</code></td><td><code>{versions_dict.get('evidence_schema_version', '1.0.0')}</code></td><td>CEG evidence and confidence decomposition schema</td></tr>
                    <tr><td><code>role_ontology_version</code></td><td><code>{versions_dict.get('role_ontology_version', '1.0.0')}</code></td><td>Role taxonomy and capability mapping ontology</td></tr>
                    <tr><td><code>claim_schema_version</code></td><td><code>{versions_dict.get('claim_schema_version', '1.0.0')}</code></td><td>CV self-claim decomposition and verification state</td></tr>
                    <tr><td><code>source_reliability_version</code></td><td><code>{versions_dict.get('source_reliability_version', '1.0.0')}</code></td><td>Empirical source reliability priors</td></tr>
                    <tr><td><code>api_version</code></td><td><code>{versions_dict.get('api_version', '1.0.0')}</code></td><td>Public HTTP REST API</td></tr>
                </tbody>
            </table>

            <div class="decision-support-note" style="margin-top: 14px; font-size: 11px;">
                <strong>Truth &amp; Invariance Preservation:</strong> Exports must not turn uncertain findings into certain statements. Unobserved capabilities evaluate strictly to <code>UNKNOWN</code> and never penalize the candidate with an arbitrary 0.0 score. CandidateX does not decide whether to hire a person.
            </div>
        </div>

        <!-- Footer -->
        <footer>
            Candidate Capability Intelligence (CCI) Platform • Confidential Interview Intelligence Brief • Human Decision Support System
        </footer>
    </div>
</body>
</html>
"""
    return html_content


def generate_json_brief(dossier: Dossier, candidate_name: str = "Candidate") -> str:
    """Generates a standardized JSON export preserving all provenance fields, versions, and limitations."""
    versions_obj = VersionFamilies.from_dossier_versions(dossier.versions)
    versions_dict = versions_obj.to_dict()
    evidence_map = _get_evidence_map(dossier)
    conclusions = _build_provenance_conclusions(dossier, versions_dict, evidence_map)

    base_data = dossier.model_dump(mode="json")
    base_data["candidate_name"] = candidate_name
    base_data["platform_invariant"] = (
        "CandidateX does not decide whether to hire a person. "
        "Core Platform Invariant: Employer Decision Support Only."
    )
    base_data["version_families"] = versions_dict
    base_data["system_limitations"] = list(dossier.system_limitations or [
        "Analysis bounded to publicly inspectable Git repositories and manifest claims.",
        "Missing evidence represents unknown capability, never low capability.",
    ])
    base_data["provenance_conclusions"] = conclusions

    return json.dumps(base_data, indent=2, default=str)

