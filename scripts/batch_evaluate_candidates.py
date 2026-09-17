#!/usr/bin/env python3
"""Candidate Capability Intelligence (CCI) - Batch Candidate Evaluation & Cohort Ranking CLI.

Evaluates an entire cohort of candidate CV materials against a unified Job Description,
synthesizing candidate evidence graphs, capability point estimates, contradiction diagnostics,
and a publication-quality Cohort Leaderboard (HTML, Markdown, JSON).
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


def format_cohort_markdown(
    candidates_data: List[Dict[str, Any]],
    role: CanonicalRole,
    jd_summary: str,
) -> str:
    """Generates a publication-quality Markdown cohort evaluation brief."""
    lines = [
        f"# Cohort Capability Leaderboard: {role.value.replace('_', ' ').title()} Engineering",
        f"**Cohort Size:** {len(candidates_data)} Candidates | **Target Role:** `{role.value}`",
        f"**Generated At:** `{time.strftime('%Y-%m-%d %H:%M:%SZ', time.gmtime())}`",
        "",
        "## Executive Summary & Paper Invariants",
        "- **Decision Support Invariant:** This ranking serves strictly as evaluator decision support for hiring committees. No candidate is autonomously rejected.",
        "- **Static Inspection Invariant:** Candidate repositories were analyzed via static AST parsers and dependency manifests (untrusted code is never executed).",
        "- **Missing Evidence Invariant:** Unobserved capabilities remain `UNKNOWN` and lower Evidence Coverage; they are never penalized with zero.",
        "",
        "## Candidate Cohort Ranking",
        "| Rank | Candidate Name | Role Capability Index (RCI) | Coverage % | Top Strengths | Contradictions | Status |",
        "| :---: | :--- | :---: | :---: | :--- | :---: | :---: |",
    ]

    for idx, c in enumerate(candidates_data, 1):
        rci_str = f"**{c['rci']:.1f}**" if c['rci'] is not None else "*UNKNOWN*"
        cov_str = f"{c['coverage'] * 100.0:.1f}%"
        strengths_str = ", ".join(c['top_strengths']) if c['top_strengths'] else "None observed"
        conflict_str = f"`{c['conflict_count']} Alert(s)`" if c['conflict_count'] > 0 else "0"
        status_str = "SUFFICIENT" if not c['is_insufficient'] else "LOW COVERAGE"

        lines.append(
            f"| **#{idx}** | **{c['name']}** | {rci_str} | {cov_str} | {strengths_str} | {conflict_str} | {status_str} |"
        )

    lines.extend([
        "",
        "## Prioritized Technical Interview Inquiries by Candidate",
        "",
    ])

    for c in candidates_data:
        lines.append(f"### {c['name']} (Rank #{c['rank']} - RCI: {c['rci'] if c['rci'] is not None else 'N/A'})")
        if c.get("top_probe"):
            probe = c["top_probe"]
            lines.append(f"- **Top Information Value Probe:** {probe.get('capability', '').replace('_', ' ').title()} (Priority $I_k$: `{probe.get('priority', 0):.2f}`)")
            if probe.get("question"):
                lines.append(f"  - *Grounded Question:* \"{probe['question']}\"")
        else:
            lines.append("- *No high-priority inquiry probe generated.*")
        lines.append("")

    return "\n".join(lines)


def format_cohort_html(
    candidates_data: List[Dict[str, Any]],
    role: CanonicalRole,
) -> str:
    """Generates an executive, self-contained HTML5 cohort dashboard."""
    rows_html = []
    for c in candidates_data:
        rank = c['rank']
        badge_color = "#6366f1" if rank == 1 else "#3b82f6" if rank == 2 else "#0ea5e9" if rank == 3 else "#475569"
        rci_display = f"{c['rci']:.1f}" if c['rci'] is not None else "UNKNOWN"
        cov_pct = f"{c['coverage'] * 100.0:.1f}%"
        strengths = ", ".join(s.replace('_', ' ').title() for s in c.get('top_strengths', [])) or "None observed"

        conflict_badge = (
            f'<span style="background: rgba(244,63,94,0.15); color: #fda4af; border: 1px solid rgba(244,63,94,0.3); padding: 2px 8px; border-radius: 6px; font-size: 11px;">⚠️ {c["conflict_count"]} Alert(s)</span>'
            if c["conflict_count"] > 0
            else '<span style="color: #64748b; font-size: 11px;">None</span>'
        )

        top_q = html.escape(c.get("top_probe", {}).get("question", "No question recorded."))

        rows_html.append(f"""
        <tr>
            <td style="padding: 12px 16px; text-align: center;">
                <span style="display: inline-block; width: 26px; height: 26px; border-radius: 50%; background: {badge_color}; color: #ffffff; font-weight: 700; font-size: 12px; line-height: 26px; text-align: center;">{rank}</span>
            </td>
            <td style="padding: 12px 16px; font-weight: 600; color: #f8fafc;">
                <div>{html.escape(c['name'])}</div>
                <div style="font-size: 11px; color: #94a3b8; font-family: monospace;">ID: {c['candidate_id'][:8]}...</div>
            </td>
            <td style="padding: 12px 16px; text-align: center;">
                <span style="font-size: 16px; font-weight: 800; color: #818cf8; font-family: monospace;">{rci_display}</span>
                <span style="font-size: 11px; color: #64748b;"> / 100</span>
            </td>
            <td style="padding: 12px 16px; text-align: center;">
                <div style="font-size: 13px; font-weight: 600; color: #38bdf8; font-family: monospace;">{cov_pct}</div>
                <div style="background: #1e293b; border-radius: 9999px; height: 5px; width: 80px; margin: 4px auto 0; overflow: hidden;">
                    <div style="background: #38bdf8; height: 100%; width: {cov_pct};"></div>
                </div>
            </td>
            <td style="padding: 12px 16px; font-size: 12px; color: #cbd5e1;">{html.escape(strengths)}</td>
            <td style="padding: 12px 16px; text-align: center;">{conflict_badge}</td>
            <td style="padding: 12px 16px; font-size: 11px; color: #94a3b8; max-width: 280px;">
                <div style="font-style: italic; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="{top_q}">"{top_q}"</div>
            </td>
            <td style="padding: 12px 16px; text-align: center;">
                <a href="dossier_{c['candidate_id']}.html" style="background: #312e81; color: #c7d2fe; border: 1px solid #4338ca; padding: 4px 10px; border-radius: 6px; text-decoration: none; font-size: 11px; font-weight: 600;">Dossier &rarr;</a>
            </td>
        </tr>
        """)

    body_content = "".join(rows_html)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cohort Leaderboard - {role.value.replace('_', ' ').title()}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #090d16;
            color: #e2e8f0;
            margin: 0;
            padding: 32px 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        .header {{
            border-bottom: 1px solid #1e293b;
            padding-bottom: 24px;
            margin-bottom: 24px;
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
        }}
        .title {{
            font-size: 24px;
            font-weight: 800;
            color: #f8fafc;
            margin: 0 0 6px 0;
        }}
        .subtitle {{
            font-size: 13px;
            color: #94a3b8;
            margin: 0;
        }}
        .badge {{
            background: rgba(99,102,241,0.15);
            color: #a5b4fc;
            border: 1px solid rgba(99,102,241,0.3);
            padding: 4px 12px;
            border-radius: 9999px;
            font-size: 12px;
            font-weight: 600;
        }}
        .card {{
            background: #0f172a;
            border: 1px solid #1e293b;
            border-radius: 16px;
            overflow: hidden;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            text-align: left;
        }}
        th {{
            background: #111c35;
            padding: 14px 16px;
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #94a3b8;
            border-bottom: 1px solid #1e293b;
        }}
        tr:not(:last-child) td {{
            border-bottom: 1px solid #1e293b;
        }}
        tr:hover td {{
            background: rgba(30, 41, 59, 0.4);
        }}
        .footer {{
            margin-top: 24px;
            font-size: 11px;
            color: #64748b;
            display: flex;
            justify-content: space-between;
            border-top: 1px solid #1e293b;
            padding-top: 16px;
        }}
        @media print {{
            body {{ background: #ffffff; color: #000000; padding: 0; }}
            .card {{ border: 1px solid #cccccc; box-shadow: none; }}
            th {{ background: #eeeeee; color: #333333; }}
            tr:not(:last-child) td {{ border-bottom: 1px solid #dddddd; }}
            a {{ color: #000000; text-decoration: underline; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1 class="title">Candidate Cohort Evaluation Leaderboard</h1>
                <p class="subtitle">Target Role: <strong>{role.value.replace('_', ' ').title()}</strong> &bull; Total Candidates: {len(candidates_data)} &bull; Formal Conference Theorems Applied</p>
            </div>
            <div class="badge">Employer Decision Support</div>
        </div>

        <div class="card">
            <table>
                <thead>
                    <tr>
                        <th style="text-align: center; width: 60px;">Rank</th>
                        <th>Candidate</th>
                        <th style="text-align: center;">RCI Score</th>
                        <th style="text-align: center;">Coverage</th>
                        <th>Top Strengths</th>
                        <th style="text-align: center;">Contradictions</th>
                        <th>Top Probe Question</th>
                        <th style="text-align: center;">Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {body_content}
                </tbody>
            </table>
        </div>

        <div class="footer">
            <span>&bull; Invariant: Missing evidence represents UNKNOWN, never 0.0.</span>
            <span>Generated by Candidate Capability Intelligence (CCI) Platform</span>
        </div>
    </div>
</body>
</html>
"""


def run_batch_evaluation(
    cv_paths: List[Path],
    jd_text: str,
    role: CanonicalRole = CanonicalRole.BACKEND,
    output_dir: Optional[Path] = None,
    min_coverage: float = 0.0,
) -> Dict[str, Any]:
    """Executes batch evaluation over a list of candidate CV files."""
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

        # Determine top strengths (highest observed capabilities)
        observed_caps = [
            (k, est.estimate)
            for k, est in dossier.capability_estimates.items()
            if est.is_observed and est.estimate is not None
        ]
        observed_caps.sort(key=lambda x: x[1], reverse=True)
        top_strengths = [k.value for k, _ in observed_caps[:2]]

        # Contradiction count
        conflict_count = sum(
            1 for c in dossier.capability_conflicts.values() if c.has_meaningful_conflict
        )

        # Top inquiry probe
        top_probe: Optional[Dict[str, Any]] = None
        if dossier.interview_probes:
            p = dossier.interview_probes[0]
            matching_q = next(
                (q.question_text for q in dossier.interview_questions if q.target_capability == p.capability_key),
                None
            )
            top_probe = {
                "capability": p.capability_key.value,
                "priority": p.priority_score,
                "question": matching_q,
            }

        candidates_results.append({
            "candidate_id": str(cand_id),
            "name": cand_name,
            "filename": cv_path.name,
            "rci": dossier.rci,
            "coverage": dossier.coverage,
            "is_insufficient": dossier.is_insufficient_evidence,
            "top_strengths": top_strengths,
            "conflict_count": conflict_count,
            "top_probe": top_probe,
            "dossier": dossier,
        })

    # Filter by minimum coverage if specified
    if min_coverage > 0.0:
        candidates_results = [c for c in candidates_results if c["coverage"] >= min_coverage]

    # Sort descending by RCI (None scores sorted last)
    candidates_results.sort(
        key=lambda x: (x["rci"] is not None, x["rci"] or 0.0, x["coverage"]),
        reverse=True,
    )

    # Assign rank numbers
    for idx, c in enumerate(candidates_results, 1):
        c["rank"] = idx

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

        # 2. Save cohort leaderboard JSON
        cohort_summary = {
            "target_role": role.value,
            "cohort_size": len(candidates_results),
            "evaluated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "candidates": [
                {
                    "rank": c["rank"],
                    "candidate_id": c["candidate_id"],
                    "name": c["name"],
                    "rci": c["rci"],
                    "coverage": c["coverage"],
                    "conflict_count": c["conflict_count"],
                    "top_strengths": c["top_strengths"],
                    "top_probe": c["top_probe"],
                }
                for c in candidates_results
            ],
        }

        with open(output_dir / "cohort_ranking.json", "w", encoding="utf-8") as f:
            json.dump(cohort_summary, f, indent=2)

        # 3. Save cohort leaderboard Markdown
        md_content = format_cohort_markdown(candidates_results, role, jd_text[:200])
        with open(output_dir / "cohort_ranking.md", "w", encoding="utf-8") as f:
            f.write(md_content)

        # 4. Save cohort leaderboard HTML
        html_content = format_cohort_html(candidates_results, role)
        with open(output_dir / "cohort_ranking.html", "w", encoding="utf-8") as f:
            f.write(html_content)

    return {
        "role": role.value,
        "count": len(candidates_results),
        "candidates": candidates_results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="CCI Batch Candidate Evaluation & Cohort Ranking CLI"
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
        help="Output directory for cohort leaderboard and dossiers (default: reports/cohort)",
    )
    parser.add_argument(
        "--min-coverage",
        type=float,
        default=0.0,
        help="Minimum coverage threshold (0.0 - 1.0)",
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
        min_coverage=args.min_coverage,
    )
    duration = time.time() - t0

    print(f"\n[+] Batch Evaluation completed in {duration:.2f}s across {result['count']} candidate(s).")
    print("\nCOHORT LEADERBOARD RANKING:")
    print("-" * 80)
    print(f"{'Rank':<6} {'Candidate Name':<24} {'RCI':<8} {'Coverage':<10} {'Contradictions':<14} {'Top Strengths'}")
    print("-" * 80)

    for c in result["candidates"]:
        rci_val = f"{c['rci']:.1f}" if c['rci'] is not None else "UNKNOWN"
        cov_val = f"{c['coverage'] * 100.0:.1f}%"
        strengths = ", ".join(c['top_strengths']) or "N/A"
        print(f"#{c['rank']:<5} {c['name']:<24} {rci_val:<8} {cov_val:<10} {c['conflict_count']:<14} {strengths}")

    print("-" * 80)
    print(f"[+] Output Leaderboard HTML: {out_dir / 'cohort_ranking.html'}")
    print(f"[+] Output Leaderboard MD:   {out_dir / 'cohort_ranking.md'}")
    print(f"[+] Output Leaderboard JSON: {out_dir / 'cohort_ranking.json'}")
    print("=" * 80)


if __name__ == "__main__":
    main()
