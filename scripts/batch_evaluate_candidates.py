#!/usr/bin/env python3
"""Candidate Capability Intelligence (CCI) - Descriptive Cohort Evaluation CLI.

Evaluates an entire cohort of candidate CV materials against a unified Job Description,
synthesizing candidate evidence graphs, capability point estimates, contradiction diagnostics,
and descriptive evidence comparisons (HTML, Markdown, JSON) without cross-candidate ranking.
"""

import argparse
import html
import json
import os
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid5, NAMESPACE_DNS

# Ensure backend package is importable
REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_SRC = REPO_ROOT / "services" / "backend" / "src"
if str(BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SRC))

from cci.domain.contracts import Dossier
from cci.domain.enums import CanonicalRole, CapabilityKey
from cci.pipeline.orchestrator import execute_analysis_pipeline
from cci.reports.exporter import generate_html_brief


def extract_candidate_name(cv_text: str, fallback_name: str) -> str:
    """Heuristically extracts candidate name from markdown title or header."""
    for line in cv_text.splitlines():
        trimmed = line.strip()
        if trimmed.startswith("# "):
            name = trimmed[2:].strip()
            # Split by dash or pipe if job title attached
            for sep in [" - ", " – ", " — ", " | "]:
                if sep in name:
                    name = name.split(sep)[0].strip()
            cleaned = name.replace("Resume", "").replace("CV", "").strip("-: ")
            if cleaned:
                return cleaned
    return fallback_name


def _markdown_escape(value: Any) -> str:
    """Escapes user-supplied text before embedding it in Markdown reports."""
    return html.escape(" ".join(str(value).split())).replace("|", "\\|")


def _candidate_comparison_data(
    *,
    dossier: Dossier,
    candidate_id: UUID,
    name: str,
    filename: str,
) -> Dict[str, Any]:
    """Builds a descriptive per-candidate summary without a cross-candidate score."""
    context = dossier.observed_index_context
    coverage_profile: Dict[str, Dict[str, Any]] = {}
    observed_dimensions: List[str] = []
    unresolved_capabilities: List[str] = []
    conflict_capabilities: List[str] = []

    for capability in CapabilityKey:
        estimate = dossier.capability_estimates.get(capability)
        conflict = dossier.capability_conflicts.get(capability)
        is_observed = bool(
            estimate is not None
            and estimate.is_observed
            and estimate.estimate is not None
        )
        if is_observed:
            observed_dimensions.append(capability.value)
        else:
            unresolved_capabilities.append(capability.value)
        has_conflict = bool(conflict and conflict.has_meaningful_conflict)
        if has_conflict:
            conflict_capabilities.append(capability.value)

        coverage_profile[capability.value] = {
            "estimate": estimate.estimate if is_observed else None,
            "is_observed": is_observed,
            "coverage": estimate.coverage_k if estimate is not None else 0.0,
            "raw_evidence_count": estimate.raw_evidence_count if estimate is not None else 0,
            "source_cluster_count": estimate.cluster_count if estimate is not None else 0,
            "has_meaningful_conflict": has_conflict,
        }

    interview_verification = sorted(
        set(unresolved_capabilities) | set(conflict_capabilities)
    )
    top_probe: Optional[Dict[str, Any]] = None
    if dossier.interview_probes:
        probe = max(dossier.interview_probes, key=lambda item: item.priority_score)
        matching_question = next(
            (
                question.question_text
                for question in dossier.interview_questions
                if question.target_capability == probe.capability_key
            ),
            None,
        )
        top_probe = {
            "capability": probe.capability_key.value,
            "priority": probe.priority_score,
            "question": matching_question,
        }

    return {
        "candidate_id": str(candidate_id),
        "name": name,
        "filename": filename,
        "coverage": dossier.coverage,
        "is_insufficient": context.is_insufficient_evidence,
        "observed_dimensions": observed_dimensions,
        "coverage_profile": coverage_profile,
        "unresolved_capabilities": unresolved_capabilities,
        "conflict_capabilities": conflict_capabilities,
        "interview_verification_capabilities": interview_verification,
        "evidence_available": {
            "observation_count": len(dossier.evidence_records),
            "unique_source_cluster_count": context.unique_independent_source_cluster_count,
            "source_cluster_counts_by_capability": {
                capability.value: context.independent_source_cluster_counts_by_capability.get(
                    capability, 0
                )
                for capability in CapabilityKey
            },
            "mean_path_attribution_confidence": context.mean_path_attribution_confidence,
            "path_attribution_sample_count": context.path_attribution_sample_count,
            "coverage_sufficiency_threshold": context.coverage_sufficiency_threshold,
        },
        "top_probe": top_probe,
        "dossier": dossier,
    }


def format_cohort_markdown(
    candidates_data: List[Dict[str, Any]],
    role: CanonicalRole,
    jd_summary: str,
) -> str:
    """Generates a descriptive evidence comparison without candidate ordering."""
    jd_summary = _markdown_escape(jd_summary)[:240]
    lines = [
        f"# Cohort Evidence Comparison: {role.value.replace('_', ' ').title()} Engineering",
        f"**Cohort Size:** {len(candidates_data)} Candidates | **Target Role:** `{role.value}`",
        f"**Generated At:** `{time.strftime('%Y-%m-%d %H:%M:%SZ', time.gmtime())}`",
        "",
        "## Decision Support Invariants",
        "- This report describes evidence and interview gaps; it offers no ordered recommendation or hiring decision.",
        "- **Static Inspection Invariant:** Candidate repositories were analyzed via static AST parsers and dependency manifests (untrusted code is never executed).",
        "- **Missing Evidence Invariant:** Unobserved capabilities remain `UNKNOWN`; they are never assigned zero proficiency.",
        "- **Observed-only Invariant:** Any observed capability estimate is based only on observed evidence and must be read with its coverage context.",
        "",
        f"**Job Description Summary:** {jd_summary or 'Not provided'}",
        "",
        "## Cohort Evidence Overview",
        "| Candidate | Role-Weighted Coverage | Observed Dimensions | Evidence Available | Conflicts | Unresolved Areas |",
        "| :--- | :---: | :---: | :--- | :--- | :--- |",
    ]

    for candidate in candidates_data:
        coverage = f"{candidate['coverage'] * 100.0:.1f}%"
        status = "INSUFFICIENT" if candidate["is_insufficient"] else "SUFFICIENT"
        evidence = candidate["evidence_available"]
        clusters = evidence["unique_source_cluster_count"]
        cluster_display = "UNKNOWN" if clusters is None else str(clusters)
        conflicts = ", ".join(candidate["conflict_capabilities"]) or "None recorded"
        unresolved = ", ".join(candidate["unresolved_capabilities"]) or "None recorded"
        lines.append(
            f"| **{_markdown_escape(candidate['name'])}** | {coverage} ({status}) | "
            f"{len(candidate['observed_dimensions'])} / {len(candidate['coverage_profile'])} | "
            f"{evidence['observation_count']} observations; {cluster_display} source clusters | "
            f"{conflicts} | {unresolved} |"
        )

    lines.extend(["", "## Candidate Evidence Profiles", ""])
    for candidate in candidates_data:
        evidence = candidate["evidence_available"]
        threshold_pct = evidence["coverage_sufficiency_threshold"] * 100.0
        path_confidence = evidence["mean_path_attribution_confidence"]
        path_confidence_display = (
            f"{path_confidence * 100.0:.1f}% "
            f"(n={evidence['path_attribution_sample_count']} unique paths)"
            if path_confidence is not None
            else f"UNKNOWN (n={evidence['path_attribution_sample_count']} unique paths)"
        )
        cluster_count = evidence["unique_source_cluster_count"]
        cluster_display = "UNKNOWN" if cluster_count is None else str(cluster_count)
        lines.extend([
            f"### {_markdown_escape(candidate['name'])}",
            f"**Role-Weighted Evidence Coverage:** {candidate['coverage'] * 100.0:.1f}% "
            f"(configured threshold {threshold_pct:.1f}%)",
            f"**Observed Dimensions:** {', '.join(candidate['observed_dimensions']) or 'None'}",
            f"**Evidence Available:** {evidence['observation_count']} observations; "
            f"{cluster_display} unique source clusters; mean path-attribution confidence "
            f"{path_confidence_display}.",
            "",
            "#### Coverage Profile",
            "| Role Dimension | Estimate | Coverage | Evidence Records | Source Clusters | Conflict |",
            "| :--- | :---: | :---: | :---: | :---: | :---: |",
        ])
        for capability, profile in candidate["coverage_profile"].items():
            estimate = (
                f"{profile['estimate']:.1f}"
                if profile["estimate"] is not None
                else "UNKNOWN"
            )
            conflict = "Yes" if profile["has_meaningful_conflict"] else "No"
            lines.append(
                f"| {capability.replace('_', ' ').title()} | {estimate} | "
                f"{profile['coverage'] * 100.0:.1f}% | {profile['raw_evidence_count']} | "
                f"{profile['source_cluster_count']} | {conflict} |"
            )

        for heading, key, empty_message in (
            ("Unresolved Areas", "unresolved_capabilities", "No unobserved dimensions recorded."),
            (
                "Dimensions Requiring Interview Verification",
                "interview_verification_capabilities",
                "No unobserved or conflicted dimensions flagged; retain human-led verification.",
            ),
            (
                "Contradiction Diagnostics",
                "conflict_capabilities",
                "No meaningful contradictions recorded.",
            ),
        ):
            lines.extend(["", f"#### {heading}"])
            values = candidate[key]
            lines.extend(
                [f"- {value.replace('_', ' ').title()}" for value in values]
                or [f"- {empty_message}"]
            )

        probe = candidate.get("top_probe")
        if probe:
            lines.append(
                f"- **Interview Inquiry:** {probe['capability'].replace('_', ' ').title()} "
                f"(priority `{probe['priority']:.2f}`)"
            )
            if probe.get("question"):
                lines.append(
                    f"  - *Grounded Question:* \"{_markdown_escape(probe['question'])}\""
                )
        lines.append("")

    return "\n".join(lines)


def format_cohort_html(
    candidates_data: List[Dict[str, Any]],
    role: CanonicalRole,
) -> str:
    """Generates a self-contained descriptive cohort evidence report."""
    overview_rows: List[str] = []
    profile_sections: List[str] = []
    for candidate in candidates_data:
        evidence = candidate["evidence_available"]
        clusters = evidence["unique_source_cluster_count"]
        unresolved = ", ".join(
            value.replace("_", " ").title()
            for value in candidate["unresolved_capabilities"]
        ) or "None recorded"
        conflicts = ", ".join(
            value.replace("_", " ").title()
            for value in candidate["conflict_capabilities"]
        ) or "None recorded"
        overview_rows.append(
            "<tr>"
            f"<td>{html.escape(candidate['name'])}<br><small>ID: {candidate['candidate_id'][:8]}...</small></td>"
            f"<td>{candidate['coverage'] * 100.0:.1f}% "
            f"({'INSUFFICIENT' if candidate['is_insufficient'] else 'SUFFICIENT'}); "
            f"threshold {evidence['coverage_sufficiency_threshold'] * 100.0:.1f}%</td>"
            f"<td>{len(candidate['observed_dimensions'])} / {len(candidate['coverage_profile'])}</td>"
            f"<td>{evidence['observation_count']} observations; "
            f"{clusters if clusters is not None else 'UNKNOWN'} source clusters</td>"
            f"<td>{html.escape(unresolved)}</td>"
            f"<td>{html.escape(conflicts)}</td>"
            f"<td><a href=\"dossier_{candidate['candidate_id']}.html\">Open dossier</a></td>"
            "</tr>"
        )

        observed = ", ".join(
            value.replace("_", " ").title()
            for value in candidate["observed_dimensions"]
        ) or "None"
        verification = ", ".join(
            value.replace("_", " ").title()
            for value in candidate["interview_verification_capabilities"]
        ) or "None flagged"
        path_confidence = evidence["mean_path_attribution_confidence"]
        path_display = (
            f"{path_confidence * 100.0:.1f}% "
            f"(n={evidence['path_attribution_sample_count']} unique paths)"
            if path_confidence is not None
            else f"UNKNOWN (n={evidence['path_attribution_sample_count']} unique paths)"
        )
        profile_rows = []
        for capability, profile in candidate["coverage_profile"].items():
            estimate = (
                f"{profile['estimate']:.1f}"
                if profile["estimate"] is not None
                else "UNKNOWN"
            )
            profile_rows.append(
                "<tr>"
                f"<td>{html.escape(capability.replace('_', ' ').title())}</td>"
                f"<td>{estimate}</td>"
                f"<td>{profile['coverage'] * 100.0:.1f}%</td>"
                f"<td>{profile['raw_evidence_count']}</td>"
                f"<td>{profile['source_cluster_count']}</td>"
                f"<td>{'Yes' if profile['has_meaningful_conflict'] else 'No'}</td>"
                "</tr>"
            )
        probe = candidate.get("top_probe")
        if probe and probe.get("question"):
            inquiry_html = (
                f"<p><strong>Interview Inquiry:</strong> "
                f"{html.escape(probe['capability'].replace('_', ' ').title())} "
                f"(priority {probe['priority']:.2f})</p>"
                f"<p>{html.escape(probe['question'])}</p>"
            )
        else:
            inquiry_html = "<p>No interview inquiry was generated.</p>"
        cluster_display = "UNKNOWN" if clusters is None else str(clusters)
        profile_sections.append(
            "<section class=\"candidate-profile\">"
            f"<h2>{html.escape(candidate['name'])}</h2>"
            f"<p><strong>Observed dimensions:</strong> {html.escape(observed)}</p>"
            f"<p><strong>Dimensions Requiring Interview Verification:</strong> "
            f"{html.escape(verification)}</p>"
            f"<p><strong>Unresolved Areas:</strong> {html.escape(unresolved)}</p>"
            f"<p><strong>Contradiction Diagnostics:</strong> {html.escape(conflicts)}</p>"
            f"<p><strong>Evidence Available:</strong> {evidence['observation_count']} observations; "
            f"{cluster_display} unique source clusters; mean path-attribution confidence {path_display}.</p>"
            "<table><thead><tr><th>Role Dimension</th><th>Estimate</th><th>Coverage</th>"
            "<th>Evidence Records</th><th>Source Clusters</th><th>Conflict</th></tr></thead>"
            f"<tbody>{''.join(profile_rows)}</tbody></table>"
            f"{inquiry_html}"
            f"<p><a href=\"dossier_{candidate['candidate_id']}.html\">Open candidate dossier</a></p>"
            "</section>"
        )

    row_html = "".join(overview_rows)
    profile_html = "".join(profile_sections)
    role_name = html.escape(role.value.replace("_", " ").title())
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cohort Evidence Comparison - {role_name}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #090d16; color: #e2e8f0; margin: 0; padding: 32px 20px; }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        .header {{ border-bottom: 1px solid #1e293b; padding-bottom: 24px; margin-bottom: 24px; }}
        .title {{ font-size: 24px; color: #f8fafc; margin: 0 0 6px; }}
        .subtitle, small {{ color: #94a3b8; }}
        .notice, .candidate-profile {{ background: #0f172a; border: 1px solid #1e293b; border-radius: 16px; padding: 20px; margin: 18px 0; }}
        .card {{ background: #0f172a; border: 1px solid #1e293b; border-radius: 16px; overflow-x: auto; }}
        table {{ width: 100%; border-collapse: collapse; text-align: left; }}
        th {{ background: #111c35; padding: 14px 16px; font-size: 11px; text-transform: uppercase; color: #94a3b8; border-bottom: 1px solid #1e293b; }}
        td {{ padding: 12px 16px; border-bottom: 1px solid #1e293b; vertical-align: top; }}
        .candidate-profile h2 {{ color: #f8fafc; margin-top: 0; }}
        .candidate-profile p {{ color: #cbd5e1; font-size: 13px; }}
        a {{ color: #c7d2fe; }}
        @media print {{ body {{ background: #fff; color: #000; padding: 0; }} .card, .candidate-profile, .notice {{ border: 1px solid #ccc; box-shadow: none; }} th {{ background: #eee; color: #333; }} }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 class="title">Candidate Cohort Evidence Comparison</h1>
            <p class="subtitle">Target Role: <strong>{role_name}</strong> &bull; Total Candidates: {len(candidates_data)}</p>
        </div>
        <div class="notice"><strong>Employer Decision Support.</strong> This report describes evidence and interview gaps. Based only on observed evidence. Missing evidence remains UNKNOWN.</div>
        <div class="card">
            <table>
                <thead><tr><th>Candidate</th><th>Role-Weighted Coverage</th><th>Observed Dimensions</th><th>Evidence Available</th><th>Unresolved Areas</th><th>Conflicts</th><th>Actions</th></tr></thead>
                <tbody>{row_html}</tbody>
            </table>
        </div>
        <h2>Candidate Evidence Profiles</h2>
        {profile_html}
        <div class="subtitle">Generated by Candidate Capability Intelligence (CCI). This report provides descriptive evidence for human interview panels.</div>
    </div>
</body>
</html>
"""


def run_batch_evaluation(
    cv_paths: List[Path],
    jd_text: str,
    role: CanonicalRole = CanonicalRole.BACKEND,
    output_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Evaluates CVs in input order and summarizes their evidence without ranking."""
    if not cv_paths:
        raise ValueError("No CV file paths provided for batch evaluation.")

    candidates_results: List[Dict[str, Any]] = []

    for cv_path in cv_paths:
        with open(cv_path, "r", encoding="utf-8") as f:
            cv_text = f.read()

        filename = cv_path.stem
        cand_name = extract_candidate_name(cv_text, filename.replace("_", " ").title())
        cand_id = uuid5(NAMESPACE_DNS, f"cci-candidate-{filename}")

        # Run 10-stage pipeline
        state = execute_analysis_pipeline(
            candidate_id=cand_id,
            role=role,
            jd_text=jd_text,
            cv_text=cv_text,
        )

        if state.status.value != "completed" or state.dossier is None:
            continue

        dossier: Dossier = state.dossier
        candidates_results.append(
            _candidate_comparison_data(
                dossier=dossier,
                candidate_id=cand_id,
                name=cand_name,
                filename=cv_path.name,
            )
        )

    # If output directory specified, save individual and aggregate reports
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # 1. Save individual dossier artifacts
        for c in candidates_results:
            d = c["dossier"]
            cid = c["candidate_id"]
            cname = c["name"]

            with open(output_dir / f"dossier_{cid}.json", "w", encoding="utf-8") as f:
                json.dump(d.model_dump(mode="json"), f, indent=2)

            with open(output_dir / f"dossier_{cid}.html", "w", encoding="utf-8") as f:
                f.write(generate_html_brief(d, candidate_name=cname))

        serializable_candidates = [
            {key: value for key, value in candidate.items() if key != "dossier"}
            for candidate in candidates_results
        ]
        cohort_summary = {
            "target_role": role.value,
            "cohort_size": len(candidates_results),
            "evaluated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "comparison_basis": "Descriptive evidence and coverage only; no cross-candidate score ordering.",
            "candidates": serializable_candidates,
        }

        with open(output_dir / "cohort_comparison.json", "w", encoding="utf-8") as f:
            json.dump(cohort_summary, f, indent=2)

        # 3. Save descriptive cohort Markdown
        md_content = format_cohort_markdown(candidates_results, role, jd_text[:200])
        with open(output_dir / "cohort_comparison.md", "w", encoding="utf-8") as f:
            f.write(md_content)

        # 4. Save descriptive cohort HTML
        html_content = format_cohort_html(candidates_results, role)
        with open(output_dir / "cohort_comparison.html", "w", encoding="utf-8") as f:
            f.write(html_content)

    return {
        "role": role.value,
        "count": len(candidates_results),
        "candidates": candidates_results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="CCI descriptive batch candidate evidence comparison CLI"
    )
    parser.add_argument(
        "--cv-dir",
        type=str,
        required=True,
        help="Directory containing candidate CV files (.md, .txt)",
    )
    parser.add_argument(
        "--jd",
        type=str,
        required=True,
        help="Path to Job Description file",
    )
    parser.add_argument(
        "--role",
        type=str,
        default="backend",
        choices=[r.value for r in CanonicalRole],
        help="Target canonical role profile (default: backend)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="reports/cohort",
        help="Output directory for cohort comparisons and dossiers (default: reports/cohort)",
    )

    args = parser.parse_args()

    cv_dir = Path(args.cv_dir)
    if not cv_dir.exists() or not cv_dir.is_dir():
        print(f"[!] Invalid CV directory: {cv_dir}")
        sys.exit(1)

    jd_path = Path(args.jd)
    if not jd_path.exists() or not jd_path.is_file():
        print(f"[!] Invalid Job Description file: {jd_path}")
        sys.exit(1)

    with open(jd_path, "r", encoding="utf-8") as f:
        jd_text = f.read()

    cv_files = sorted(
        [
            p
            for p in cv_dir.iterdir()
            if p.is_file()
            and p.suffix.lower() in [".md", ".txt"]
            and not any(neg in p.name.lower() for neg in ["_jd", "job_description", "jd."])
        ]
    )

    if not cv_files:
        print(f"[!] No valid CV files found in {cv_dir}")
        sys.exit(1)

    role = CanonicalRole(args.role)
    out_dir = Path(args.output_dir)

    print("=" * 80)
    print("CANDIDATE CAPABILITY INTELLIGENCE: BATCH COHORT EVALUATION")
    print(f"Cohort Directory: {cv_dir} ({len(cv_files)} CVs found)")
    print(f"Target Role:      {role.value}")
    print(f"Output Directory: {out_dir}")
    print("=" * 80)

    t0 = time.time()
    result = run_batch_evaluation(
        cv_paths=cv_files,
        jd_text=jd_text,
        role=role,
        output_dir=out_dir,
    )
    duration = time.time() - t0

    print(f"\n[+] Batch Evaluation completed in {duration:.2f}s across {result['count']} candidate(s).")
    print("\nCOHORT EVIDENCE COMPARISON:")
    print("-" * 80)
    print(f"{'Candidate Name':<24} {'Coverage':<12} {'Observed':<12} {'Unresolved':<12} {'Conflicts'}")
    print("-" * 80)

    for c in result["candidates"]:
        cov_val = f"{c['coverage'] * 100.0:.1f}%"
        observed = f"{len(c['observed_dimensions'])}/{len(c['coverage_profile'])}"
        unresolved = str(len(c["unresolved_capabilities"]))
        conflicts = str(len(c["conflict_capabilities"]))
        print(f"{c['name']:<24} {cov_val:<12} {observed:<12} {unresolved:<12} {conflicts}")

    print("-" * 80)
    print(f"[+] Output Comparison HTML: {out_dir / 'cohort_comparison.html'}")
    print(f"[+] Output Comparison MD:   {out_dir / 'cohort_comparison.md'}")
    print(f"[+] Output Comparison JSON: {out_dir / 'cohort_comparison.json'}")
    print("=" * 80)


if __name__ == "__main__":
    main()
