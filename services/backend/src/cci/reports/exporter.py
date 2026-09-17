"""Candidate technical intelligence brief exporters.

All public report copy follows the submitted CCI paper, including Eq. (11) for
interview-probe prioritization. Reports are decision-support artifacts, not hiring
recommendations.
"""

from __future__ import annotations

from datetime import datetime, timezone
import html

from cci.domain.contracts import Dossier


PROBE_FORMULA_TEXT = "I_k = w_k[alpha(1-Cov_k) + beta*CIwidth_k + gamma*Conf_k]"
PROBE_FORMULA_LATEX = (
    r"I_k = w_k[\alpha(1-\mathrm{Cov}_k) + "
    r"\beta\,\mathrm{CIwidth}_k + \gamma\,\mathrm{Conf}_k]"
)


def _generated_time(dossier: Dossier) -> str:
    generated_at = getattr(dossier, "generated_at", None)
    if generated_at is not None:
        return generated_at.strftime("%Y-%m-%d %H:%M:%S UTC")
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def generate_markdown_brief(dossier: Dossier, candidate_name: str = "Candidate") -> str:
    """Generate a portable Markdown interviewer dossier."""
    coverage_pct = dossier.coverage * 100.0
    rci_display = f"{dossier.rci:.1f} / 100" if dossier.rci is not None else "UNKNOWN"
    role_title = dossier.role.value.replace("_", " ").title()

    lines = [
        f"# Candidate Technical Intelligence Brief: {candidate_name}",
        "",
        f"**Role:** {role_title}  ",
        f"**Candidate ID:** `{dossier.candidate_id}`  ",
        f"**Generated:** {_generated_time(dossier)}",
        "",
        "> **Decision Support Only.** CCI supports human technical interviewers and never makes an autonomous hire/reject decision. Missing evidence is UNKNOWN rather than zero capability.",
        "",
        "## 1. Executive Capability Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| **Role Capability Index (RCI)** | **{rci_display}** |",
        f"| **Evidence Coverage** | **{coverage_pct:.1f}%** |",
        f"| **Evidence Status** | **{'INSUFFICIENT EVIDENCE' if dossier.is_insufficient_evidence else 'EVIDENCE SUFFICIENT'}** |",
        "",
        "## 2. Core Capabilities Breakdown",
        "",
        "| Capability | Estimate | 95% CI | Effective Evidence | Raw Evidence | Coverage | Status |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]

    for cap_key, estimate in dossier.capability_estimates.items():
        cap_name = cap_key.value.replace("_", " ").title()
        cov = estimate.coverage_k * 100.0
        if estimate.is_observed and estimate.estimate is not None:
            ci = (
                f"[{estimate.ci_lower:.1f}, {estimate.ci_upper:.1f}]"
                if estimate.ci_lower is not None and estimate.ci_upper is not None
                else "N/A"
            )
            lines.append(
                f"| **{cap_name}** | **{estimate.estimate:.1f}** | {ci} | "
                f"{estimate.effective_evidence_count:.1f} | {estimate.raw_evidence_count} | "
                f"{cov:.1f}% | OBSERVED |"
            )
        else:
            lines.append(
                f"| **{cap_name}** | *UNKNOWN* | N/A | 0.0 | 0 | {cov:.1f}% | UNKNOWN |"
            )

    lines.extend(
        [
            "",
            "## 3. Contradiction Diagnostics",
            "",
            r"$D_k = (P_k-N_k)/(P_k+N_k+\epsilon)$ is surfaced as an interviewer verification diagnostic rather than an automatic rejection rule.",
            "",
            "| Capability | D_k | Positive Support | Contradictory Support | Flag |",
            "|---|---:|---:|---:|---|",
        ]
    )

    for cap_key, conflict in dossier.capability_conflicts.items():
        cap_name = cap_key.value.replace("_", " ").title()
        flag = "VERIFY" if conflict.has_meaningful_conflict else "CLEAR"
        lines.append(
            f"| **{cap_name}** | {conflict.contradiction_diagnostic:+.2f} | "
            f"{conflict.positive_support_sum:.2f} | {conflict.negative_support_sum:.2f} | {flag} |"
        )

    lines.extend(
        [
            "",
            "## 4. Prioritized Technical Interview Inquiry Probes",
            "",
            f"Ranked using paper Eq. (11): ${PROBE_FORMULA_LATEX}$.",
            "",
        ]
    )

    for index, probe in enumerate(dossier.interview_probes[:6], 1):
        cap_name = probe.capability_key.value.replace("_", " ").title()
        lines.append(
            f"### Probe {index}: {cap_name} (priority `{probe.priority_score:.3f}`)"
        )
        lines.append(
            f"Role weight `{probe.role_weight:.3f}` · coverage gap `{probe.coverage_gap_term:.3f}` · "
            f"uncertainty `{probe.uncertainty_term:.3f}` · contradiction `{probe.contradiction_term:.3f}`"
        )
        for question in dossier.interview_questions:
            if question.target_capability == probe.capability_key:
                lines.append(f"- **Suggested Inquiry:** {question.question_text}")
                lines.append(f"  - **Evaluation Guidance:** {question.verification_guidance}")
                if question.rationale:
                    lines.append(f"  - **Evidence Rationale:** {question.rationale}")
        lines.append("")

    if dossier.claims_corroboration:
        lines.extend(
            [
                "## 5. Candidate Self-Claims Corroboration",
                "",
                "| Declared Claim | Status | Grounding Evidence |",
                "|---|---|---:|",
            ]
        )
        for claim in dossier.claims_corroboration:
            lines.append(
                f"| {claim.get('claim_text', '')} | **{str(claim.get('status', 'unknown')).upper()}** | "
                f"{len(claim.get('grounding_evidence_ids', []))} records |"
            )

    lines.extend(
        [
            "",
            "---",
            "*Research prototype. Evidence Coverage, provenance and uncertainty must be reviewed alongside RCI.*",
        ]
    )
    return "\n".join(lines)


def generate_html_brief(dossier: Dossier, candidate_name: str = "Candidate") -> str:
    """Generate a standalone printable HTML interviewer dossier."""
    candidate = html.escape(candidate_name)
    role = html.escape(dossier.role.value.replace("_", " ").title())
    rci = f"{dossier.rci:.1f}" if dossier.rci is not None else "UNKNOWN"
    coverage = dossier.coverage * 100.0

    capability_rows: list[str] = []
    for cap_key, estimate in dossier.capability_estimates.items():
        cap_name = html.escape(cap_key.value.replace("_", " ").title())
        if estimate.is_observed and estimate.estimate is not None:
            score = f"{estimate.estimate:.1f}"
            ci = (
                f"[{estimate.ci_lower:.1f}, {estimate.ci_upper:.1f}]"
                if estimate.ci_lower is not None and estimate.ci_upper is not None
                else "N/A"
            )
            status = "OBSERVED"
        else:
            score, ci, status = "UNKNOWN", "N/A", "UNKNOWN"
        capability_rows.append(
            "<tr>"
            f"<td><strong>{cap_name}</strong></td>"
            f"<td>{score}</td><td>{ci}</td>"
            f"<td>{estimate.effective_evidence_count:.1f}</td>"
            f"<td>{estimate.raw_evidence_count}</td>"
            f"<td>{estimate.coverage_k * 100.0:.1f}%</td>"
            f"<td>{status}</td>"
            "</tr>"
        )

    probe_cards: list[str] = []
    for index, probe in enumerate(dossier.interview_probes[:6], 1):
        cap_name = html.escape(probe.capability_key.value.replace("_", " ").title())
        question_blocks = []
        for question in dossier.interview_questions:
            if question.target_capability != probe.capability_key:
                continue
            question_blocks.append(
                '<div class="probe-question">'
                f"<p><strong>Q:</strong> {html.escape(question.question_text)}</p>"
                f"<p><strong>Evaluation Guidance:</strong> {html.escape(question.verification_guidance)}</p>"
                + (
                    f"<p><strong>Evidence Rationale:</strong> {html.escape(question.rationale)}</p>"
                    if question.rationale
                    else ""
                )
                + "</div>"
            )
        probe_cards.append(
            '<section class="probe-card">'
            f"<h3>Probe #{index}: {cap_name}</h3>"
            f"<p><strong>Priority:</strong> {probe.priority_score:.3f} · "
            f"Role weight {probe.role_weight:.3f} · Coverage gap {probe.coverage_gap_term:.3f} · "
            f"Uncertainty {probe.uncertainty_term:.3f} · Contradiction {probe.contradiction_term:.3f}</p>"
            + "".join(question_blocks)
            + "</section>"
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>CCI Technical Brief · {candidate}</title>
<style>
:root {{ color-scheme: dark; font-family: Inter, ui-sans-serif, system-ui, sans-serif; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: #080c14; color: #eef2ff; line-height: 1.5; }}
main {{ max-width: 1100px; margin: 0 auto; padding: 32px; }}
header,.card,.probe-card {{ background: #111827; border: 1px solid #28344a; border-radius: 14px; padding: 20px; margin-bottom: 18px; }}
.meta {{ color: #a7b0c0; }}
.notice {{ background: #312e81; border-left: 4px solid #818cf8; padding: 14px; border-radius: 8px; }}
.metrics {{ display: grid; grid-template-columns: repeat(2,minmax(0,1fr)); gap: 12px; margin-top: 16px; }}
.metric {{ background: #0b1220; padding: 14px; border-radius: 10px; }}
table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
th,td {{ padding: 10px; border-bottom: 1px solid #253047; text-align: left; }}
th {{ color: #c7d2fe; }}
.probe-question {{ background: #0b1220; border-radius: 8px; padding: 10px 12px; margin-top: 10px; }}
.formula {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; overflow-wrap: anywhere; }}
button {{ border: 0; border-radius: 8px; padding: 10px 14px; background: #4f46e5; color: white; cursor: pointer; }}
@media (max-width: 720px) {{ main {{ padding: 16px; }} .metrics {{ grid-template-columns: 1fr; }} table {{ display: block; overflow-x: auto; }} }}
@media print {{
  :root {{ color-scheme: light; }}
  body {{ background: white; color: #111827; }}
  main {{ max-width: none; padding: 0; }}
  header,.card,.probe-card {{ background: white; border-color: #d1d5db; break-inside: avoid; }}
  .notice,.metric,.probe-question {{ background: #f3f4f6; }}
  button {{ display: none; }}
}}
</style>
</head>
<body>
<main>
<button onclick="window.print()">Print Brief</button>
<header>
<h1>Candidate Technical Intelligence Brief: {candidate}</h1>
<p class="meta">Target role: {role} · Generated: {html.escape(_generated_time(dossier))}</p>
<div class="notice"><strong>Decision Support Only.</strong> CCI does not make autonomous hiring decisions. Missing evidence is UNKNOWN, not zero capability.</div>
<div class="metrics">
<div class="metric"><strong>Role Capability Index (RCI)</strong><br>{rci} / 100</div>
<div class="metric"><strong>Evidence Coverage</strong><br>{coverage:.1f}%</div>
</div>
</header>
<section class="card">
<h2>Capability Evidence</h2>
<table><thead><tr><th>Capability</th><th>Estimate</th><th>95% CI</th><th>n_eff</th><th>Raw</th><th>Coverage</th><th>Status</th></tr></thead>
<tbody>{''.join(capability_rows)}</tbody></table>
</section>
<section class="card">
<h2>Prioritized Technical Interview Inquiry Probes</h2>
<p>Paper Eq. (11): <span class="formula">{html.escape(PROBE_FORMULA_TEXT)}</span></p>
</section>
{''.join(probe_cards)}
<footer class="meta">Research prototype. Review provenance, Evidence Coverage and uncertainty alongside RCI.</footer>
</main>
</body>
</html>"""
