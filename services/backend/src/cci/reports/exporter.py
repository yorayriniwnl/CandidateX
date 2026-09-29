"""Candidate Technical Intelligence Brief Exporters (HTML, Markdown, JSON).

Generates standalone, printable, and publication-aligned reports synthesizing
candidate capability estimates, evidence coverage, contradiction diagnostics,
and prioritized interview inquiry probes.
"""

import html
from datetime import datetime, timezone
from typing import Any

from cci.domain.contracts import Dossier


def generate_markdown_brief(dossier: Dossier, candidate_name: str = "Candidate") -> str:
    """Generates a standardized GitHub Flavored Markdown Technical Brief."""
    gen_time = (
        dossier.generated_at.strftime("%Y-%m-%d %H:%M:%S UTC")
        if hasattr(dossier, "generated_at") and dossier.generated_at
        else datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    )
    coverage_pct = round(dossier.coverage * 100, 1)
    rci_display = f"{dossier.rci:.1f} / 100" if dossier.rci is not None else "UNKNOWN"
    role_title = dossier.role.value.replace("_", " ").title()

    lines = [
        f"# Candidate Technical Intelligence Brief: {candidate_name}",
        f"**Evidence mode:** {dossier.evidence_mode} | **Scenario:** {dossier.scenario or 'none'}",
        f"**Role:** {role_title} | **Candidate ID:** `{dossier.candidate_id}`",
        f"**Generated:** {gen_time} | **Platform:** Candidate Capability Intelligence (CCI) v0.1.0-paper",
        "",
        "> [!IMPORTANT]",
        "> **Core Platform Invariant: Employer Decision Support Only.**",
        "> This dossier assists human hiring teams and technical interviewers with empirically grounded evidence.",
        "> It never makes automated hiring or rejection determinations. Unobserved capabilities evaluate strictly to `UNKNOWN`.",
        "",
        "---",
        "",
        "## 1. Executive Capability Summary",
        "",
        "| Metric | Value | Interpretation |",
        "| :--- | :---: | :--- |",
        f"| **Role Capability Index (RCI)** | **{rci_display}** | Capability across observed technical dimensions |",
        f"| **Evidence Coverage** | **{coverage_pct}%** | Percentage of job-critical capabilities backed by direct evidence |",
        f"| **Evidence Status** | **{'INSUFFICIENT' if dossier.is_insufficient_evidence else 'ROBUST'}** | {'Coverage below threshold; focus interview on unobserved gaps' if dossier.is_insufficient_evidence else 'Sufficient empirical grounding observed'} |",
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

    if dossier.claims_corroboration:
        lines.extend(
            [
                "---",
                "",
                "## 5. Candidate Self-Claims Corroboration",
                "",
                "| Declared Resume Claim | Status | Corroborating Evidence Records |",
                "| :--- | :---: | :--- |",
            ]
        )
        for claim in dossier.claims_corroboration:
            c_text = claim.get("claim_text", "")
            status_badge = str(claim.get("status", "unknown")).upper()
            ev_count = len(claim.get("grounding_evidence_ids", []))
            lines.append(
                f"| {c_text} | **`{status_badge}`** | {ev_count} empirical records |"
            )
        lines.append("")

    lines.extend(["", "## Limitations", *[f"- {item}" for item in dossier.system_limitations]])
    return "\n".join(lines)


def generate_html_brief(dossier: Dossier, candidate_name: str = "Candidate") -> str:
    """Generates a standalone, responsive, printable HTML Technical Brief."""
    gen_time = (
        dossier.generated_at.strftime("%B %d, %Y - %H:%M UTC")
        if hasattr(dossier, "generated_at") and dossier.generated_at
        else datetime.now(timezone.utc).strftime("%B %d, %Y - %H:%M UTC")
    )
    coverage_pct = round(dossier.coverage * 100, 1)
    rci_display = f"{dossier.rci:.1f}" if dossier.rci is not None else "UNKNOWN"
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

    # Claims rows
    claims_rows = []
    for c in dossier.claims_corroboration:
        c_text = html.escape(c.get("claim_text", ""))
        st = str(c.get("status", "unknown")).upper()
        st_cls = (
            "badge-observed"
            if st == "SUPPORTED"
            else "badge-conflict"
            if st == "CONTRADICTED"
            else "badge-unknown"
        )
        ev_count = len(c.get("grounding_evidence_ids", []))
        claims_rows.append(f"""
        <tr>
            <td>{c_text}</td>
            <td><span class="badge {st_cls}">{st}</span></td>
            <td class="mono">{ev_count} records</td>
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
            This dossier provides mathematically validated, provenance-grounded capability signals to assist human interview panels. Unobserved capabilities evaluate to <code>UNKNOWN</code>.
        </div>

        <!-- Low Coverage Alert -->
        {
        '<div class="alert-banner"><strong>Low Evidence Coverage Alert:</strong> Direct evidence coverage is below 30% ('
        + str(coverage_pct)
        + "%). The candidate capability index reflects only observed dimensions; prioritize technical interviews on unobserved gaps.</div>"
        if (dossier.coverage < 0.30 or dossier.is_insufficient_evidence)
        else ""
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
                    <div class="metric-label">Role Capability Index (RCI)</div>
                    <div class="metric-value">{
        rci_display
    } <span style="font-size: 14px; color: var(--text-sub);">/ 100</span></div>
                    <div class="metric-sub">Observed technical dimensions</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Evidence Coverage</div>
                    <div class="metric-value" style="color: {
        "var(--accent-amber)" if dossier.coverage < 0.30 else "var(--accent-emerald)"
    };">{coverage_pct}%</div>
                    <div class="metric-sub">Role requirement satisfaction</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Empirical Status</div>
                    <div class="metric-value" style="font-size: 22px; color: {
        "var(--accent-amber)"
        if dossier.is_insufficient_evidence
        else "var(--accent-emerald)"
    };">
                        {
        "INSUFFICIENT" if dossier.is_insufficient_evidence else "ROBUST"
    }
                    </div>
                    <div class="metric-sub">Evidence threshold verification</div>
                </div>
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
                    <th>Empirical Records</th>
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

        <!-- Footer -->
        <footer>
            Candidate Capability Intelligence (CCI) Platform • Confidential Interview Intelligence Brief • Human Decision Support System
        </footer>
    </div>
</body>
</html>
"""
    return html_content


def _normalize_event(event: Any) -> dict[str, Any]:
    """Normalizes an audit event whether it is a dict, Pydantic model, or ORM object."""
    if isinstance(event, dict):
        return event
    if hasattr(event, "model_dump"):
        return event.model_dump()
    if hasattr(event, "__dict__"):
        return {k: v for k, v in event.__dict__.items() if not k.startswith("_")}
    return {}


def _prop(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _extract_evidence_fields(rec: Any) -> dict[str, Any]:
    prov = _prop(rec, "provenance") or {}
    decomp = _prop(rec, "confidence_decomposition") or {}
    ev_id = str(_prop(rec, "evidence_id", ""))
    target_cap = _prop(rec, "target_capability")
    cap_val = _prop(target_cap, "value", str(target_cap)) if target_cap else "unknown"
    is_pos = bool(_prop(rec, "is_positive_support", True))
    conf = float(_prop(rec, "confidence", 0.0) or 0.0)
    supp = float(_prop(rec, "support_score", 0.0) or 0.0)

    art = _prop(prov, "artifact_path") or ""
    line_start = _prop(prov, "line_start")
    line_end = _prop(prov, "line_end")
    raw_support = _prop(prov, "raw_support_text") or ""
    commit_or_hash = _prop(prov, "commit_or_file_hash") or ""

    source_rel = float(_prop(decomp, "source_reliability", 1.0) or 1.0)
    struct_int = float(_prop(decomp, "structural_integrity", 1.0) or 1.0)
    recency = float(_prop(decomp, "recency_weight", 1.0) or 1.0)
    depth = float(_prop(decomp, "semantic_depth", 1.0) or 1.0)
    verif = float(_prop(decomp, "verification_multiplier", 1.0) or 1.0)

    return {
        "evidence_id": ev_id,
        "capability": cap_val,
        "is_positive": is_pos,
        "confidence": conf,
        "support_score": supp,
        "artifact_path": art,
        "line_start": line_start,
        "line_end": line_end,
        "raw_support_text": raw_support,
        "commit_or_hash": commit_or_hash,
        "source_reliability": source_rel,
        "structural_integrity": struct_int,
        "recency_weight": recency,
        "semantic_depth": depth,
        "verification_multiplier": verif,
    }


def _extract_conflict_fields(conf: Any) -> tuple[float, float, float, bool]:
    diag = float(_prop(conf, "contradiction_diagnostic", 0.0) or 0.0)
    pos = float(_prop(conf, "positive_support_sum", 0.0) or 0.0)
    neg = float(_prop(conf, "negative_support_sum", 0.0) or 0.0)
    has_conf = bool(_prop(conf, "has_meaningful_conflict", False))
    return diag, pos, neg, has_conf



def generate_audit_markdown(
    dossier: Dossier,
    audit_events: list[Any] | None = None,
    candidate_name: str = "Candidate",
) -> str:
    """Generates a comprehensive Markdown Full Audit & Governance Log."""
    gen_time = (
        dossier.generated_at.strftime("%Y-%m-%d %H:%M:%S UTC")
        if hasattr(dossier, "generated_at") and dossier.generated_at
        else datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    )
    events = [_normalize_event(e) for e in (audit_events or [])]

    lines = [
        f"# Candidate Full Audit & Governance Log: {candidate_name}",
        f"**Candidate ID:** `{dossier.candidate_id}` | **Analysis Run ID:** `{dossier.analysis_run_id}`",
        f"**Generated:** {gen_time} | **Evidence Mode:** `{dossier.evidence_mode}`",
        f"**Platform:** Candidate Capability Intelligence (CCI) v0.1.0-audit",
        "",
        "> [!IMPORTANT]",
        "> **Platform Invariant: Cryptographic Audit Trail & Human Decision Support.**",
        "> All capability adjustments, justifications, interviewer scorecards, and raw artifact traces are recorded immutably.",
        "> Static inspection guarantees zero untrusted code execution. Unobserved capabilities evaluate strictly to `UNKNOWN`.",
        "",
        "---",
        "",
        "## 1. Runtime Provenance & System Subsystem Versions",
        "",
        f"- **Dossier ID:** `{dossier.dossier_id}`",
        f"- **Target Role:** `{dossier.role.value}`",
        f"- **Scenario:** `{dossier.scenario or 'standard'}`",
        f"- **Sufficiency Status:** `{'INSUFFICIENT' if dossier.is_insufficient_evidence else 'ROBUST'}` (Coverage: {dossier.coverage * 100:.1f}%)",
        "",
        "### Subsystem Component Versions",
        "",
        "| Subsystem Component | Version / Identifier |",
        "| :--- | :--- |",
    ]

    for comp, ver in dossier.versions.items():
        lines.append(f"| **{comp.replace('_', ' ').title()}** | `{ver}` |")

    lines.extend(
        [
            "",
            "### Formal System Limitations",
            "",
        ]
    )
    for lim in dossier.system_limitations:
        lines.append(f"- {lim}")

    lines.extend(
        [
            "",
            "---",
            "",
            "## 2. Immutable Governance Audit Trail",
            "",
            f"Total recorded governance events: **{len(events)}**",
            "",
        ]
    )

    if not events:
        lines.append("*No override or interview feedback events recorded yet for this candidate.*")
    else:
        lines.extend(
            [
                "| Timestamp | Event Type | Actor / ID | Summary / Justification | Key Impact / Recommendation |",
                "| :--- | :---: | :--- | :--- | :--- |",
            ]
        )
        for ev in events:
            ev_id = str(ev.get("id", ""))[:8]
            ev_type = ev.get("event_type", "unknown")
            created = ev.get("created_at", "")[:19].replace("T", " ")
            details = ev.get("details", {}) or {}

            if ev_type == "recruiter_weight_override":
                type_label = "Role Weight Override"
                justification = details.get("justification", "No justification provided")
                prev_rci = f"{details.get('previous_rci'):.1f}" if details.get("previous_rci") is not None else "N/A"
                new_rci = f"{details.get('rescored_rci'):.1f}" if details.get("rescored_rci") is not None else "N/A"
                impact = f"RCI: {prev_rci} → {new_rci}"
                actor = str(ev.get("user_id") or "Recruiter")[:8]
                lines.append(f"| {created} | `{type_label}` | `{actor}` (`{ev_id}`) | {justification} | {impact} |")
            elif ev_type == "interviewer_probe_feedback":
                type_label = "Interviewer Scorecard"
                interviewer = details.get("interviewer_name", "Interviewer")
                rec = details.get("overall_recommendation", "N/A").upper().replace("_", " ")
                evals_count = len(details.get("probe_evaluations", [])) or details.get("evaluations_count", 0)
                notes = details.get("overall_notes") or f"{evals_count} probes evaluated"
                lines.append(f"| {created} | `{type_label}` | {interviewer} (`{ev_id}`) | {notes} | **{rec}** |")
            else:
                lines.append(f"| {created} | `{ev_type}` | `{ev_id}` | Governance Event | Recorded |")

    lines.extend(
        [
            "",
            "---",
            "",
            "## 3. Grounding Evidence Ledger & Verification Traces",
            "",
            f"Total empirical evidence records: **{len(dossier.evidence_records)}**",
            "",
            "| ID | Capability | Polarity | Confidence | Support | Artifact Source | Location / Line |",
            "| :--- | :--- | :---: | :---: | :---: | :--- | :--- |",
        ]
    )

    for rec in dossier.evidence_records:
        f = _extract_evidence_fields(rec)
        rec_id = f["evidence_id"][:8]
        cap = f["capability"].replace("_", " ").title()
        polarity = "POSITIVE" if f["is_positive"] else "NEGATIVE"
        conf = f"{f['confidence']:.2f}"
        supp = f"{f['support_score']:.2f}"
        art = f["artifact_path"] or "N/A"
        loc = (
            f"L{f['line_start']}-L{f['line_end']}"
            if f["line_start"]
            else "Repository Root"
        )
        lines.append(f"| `{rec_id}` | {cap} | `{polarity}` | `{conf}` | `{supp}` | `{art}` | `{loc}` |")

    lines.extend(
        [
            "",
            "### Detailed Evidence Provenance & Confidence Decomposition",
            "",
        ]
    )

    for idx, rec in enumerate(dossier.evidence_records[:20], 1):
        f = _extract_evidence_fields(rec)
        rec_id = f["evidence_id"]
        cap = f["capability"].replace("_", " ").title()
        polarity = "Supporting" if f["is_positive"] else "Contradicting"
        lines.extend(
            [
                f"#### Record {idx}: `{rec_id[:12]}` — {cap} ({polarity})",
                f"- **Artifact Path:** `{f['artifact_path']}`",
                f"- **File/Commit Hash:** `{f['commit_or_hash'] or 'untracked'}`",
                f"- **Confidence:** `{f['confidence']:.3f}` | **Support Score:** `{f['support_score']:.3f}`",
                f"- **Decomposition:** Source Reliability: `{f['source_reliability']:.2f}` | Integrity: `{f['structural_integrity']:.2f}` | Recency: `{f['recency_weight']:.2f}` | Depth: `{f['semantic_depth']:.2f}` | Verification: `{f['verification_multiplier']:.2f}`",
            ]
        )
        if f["raw_support_text"]:
            cleaned_support = f["raw_support_text"].strip().replace("\n", " ")
            lines.append(f"- **Verbatim Observation:** *\"{cleaned_support[:300]}\"*")
        lines.append("")

    if len(dossier.evidence_records) > 20:
        lines.append(f"*... and {len(dossier.evidence_records) - 20} additional evidence records archived in full JSON export.*")
        lines.append("")

    lines.extend(
        [
            "---",
            "",
            "## 4. Contradiction Diagnostics & Discrepancy Audit",
            "",
            "| Capability | Diagnostic $D_k$ | Positive Support ($P_k$) | Contradictory Support ($N_k$) | Status |",
            "| :--- | :---: | :---: | :---: | :--- |",
        ]
    )

    for cap_key, conflict in dossier.capability_conflicts.items():
        cap_name = _prop(cap_key, "value", str(cap_key)).replace("_", " ").title()
        diag, pos, neg, has_conf = _extract_conflict_fields(conflict)
        flag = "DISCREPANCY FLAGGED" if has_conf else "CONSISTENT"
        lines.append(
            f"| **{cap_name}** | `{diag:+.2f}` | "
            f"{pos:.2f} | {neg:.2f} | `{flag}` |"
        )

    lines.extend(["", "---", "", "## 5. Declared Claims Corroboration Audit", ""])
    if not dossier.claims_corroboration:
        lines.append("*No candidate self-claims were submitted or extracted.*")
    else:
        lines.extend(
            [
                "| Declared Resume Claim | Status | Corroborating Records |",
                "| :--- | :---: | :--- |",
            ]
        )
        for cl in dossier.claims_corroboration:
            c_text = cl.get("claim_text", "")
            st = str(cl.get("status", "unknown")).upper()
            grounded = len(cl.get("grounding_evidence_ids", []))
            lines.append(f"| {c_text} | `{st}` | {grounded} record(s) |")

    lines.extend(
        [
            "",
            "---",
            "*Generated by Candidate Capability Intelligence (CCI) Platform — Comprehensive Governance & Audit Engine.*",
        ]
    )
    return "\n".join(lines)


def generate_audit_html(
    dossier: Dossier,
    audit_events: list[Any] | None = None,
    candidate_name: str = "Candidate",
) -> str:
    """Generates a standalone, printable HTML Full Audit & Governance Log."""
    gen_time = (
        dossier.generated_at.strftime("%B %d, %Y - %H:%M UTC")
        if hasattr(dossier, "generated_at") and dossier.generated_at
        else datetime.now(timezone.utc).strftime("%B %d, %Y - %H:%M UTC")
    )
    cand_safe = html.escape(candidate_name)
    events = [_normalize_event(e) for e in (audit_events or [])]

    # Events rows
    event_rows = []
    for ev in events:
        ev_id = html.escape(str(ev.get("id", ""))[:8])
        ev_type = ev.get("event_type", "unknown")
        created = html.escape(ev.get("created_at", "")[:19].replace("T", " "))
        details = ev.get("details", {}) or {}

        if ev_type == "recruiter_weight_override":
            justification = html.escape(str(details.get("justification", "—")))
            prev_rci = f"{details.get('previous_rci'):.1f}" if details.get("previous_rci") is not None else "N/A"
            new_rci = f"{details.get('rescored_rci'):.1f}" if details.get("rescored_rci") is not None else "N/A"
            actor = html.escape(str(ev.get("user_id") or "Recruiter")[:8])
            event_rows.append(f"""
            <tr>
                <td class="mono">{created}</td>
                <td><span class="badge badge-warning">WEIGHT OVERRIDE</span></td>
                <td class="mono">{actor} ({ev_id})</td>
                <td>{justification}</td>
                <td class="mono">RCI: {prev_rci} → {new_rci}</td>
            </tr>
            """)
        elif ev_type == "interviewer_probe_feedback":
            interviewer = html.escape(str(details.get("interviewer_name", "Interviewer")))
            rec = html.escape(str(details.get("overall_recommendation", "N/A")).upper().replace("_", " "))
            evals_count = len(details.get("probe_evaluations", [])) or details.get("evaluations_count", 0)
            notes = html.escape(str(details.get("overall_notes") or f"{evals_count} probes evaluated"))
            rec_badge = "badge-observed" if "HIRE" in rec and "NO" not in rec else "badge-conflict"
            event_rows.append(f"""
            <tr>
                <td class="mono">{created}</td>
                <td><span class="badge badge-info">SCORECARD</span></td>
                <td class="mono">{interviewer} ({ev_id})</td>
                <td>{notes}</td>
                <td><span class="badge {rec_badge}">{rec}</span></td>
            </tr>
            """)
        else:
            event_rows.append(f"""
            <tr>
                <td class="mono">{created}</td>
                <td><span class="badge badge-unknown">{html.escape(ev_type)}</span></td>
                <td class="mono">{ev_id}</td>
                <td>Governance event</td>
                <td>Recorded</td>
            </tr>
            """)

    if not event_rows:
        event_rows.append("""
        <tr>
            <td colspan="5" style="text-align: center; color: var(--text-muted); padding: 18px;">
                No override or interview feedback events recorded yet for this candidate.
            </td>
        </tr>
        """)

    # Evidence rows
    evidence_rows = []
    for rec in dossier.evidence_records:
        f = _extract_evidence_fields(rec)
        rec_id = html.escape(f["evidence_id"][:8])
        cap = html.escape(f["capability"].replace("_", " ").title())
        is_pos = f["is_positive"]
        polarity_badge = (
            '<span class="badge badge-observed">SUPPORTING</span>'
            if is_pos
            else '<span class="badge badge-conflict">CONTRADICTING</span>'
        )
        art = html.escape(f["artifact_path"] or "—")
        loc = (
            f"L{f['line_start']}-L{f['line_end']}"
            if f["line_start"]
            else "Root"
        )
        evidence_rows.append(f"""
        <tr>
            <td class="mono">{rec_id}</td>
            <td><strong>{cap}</strong></td>
            <td>{polarity_badge}</td>
            <td class="mono">{f['confidence']:.2f}</td>
            <td class="mono">{f['support_score']:.2f}</td>
            <td class="mono" style="max-width: 280px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="{art}">{art}</td>
            <td class="mono text-muted">{loc}</td>
            <td class="mono text-sub" style="font-size: 11px;">R:{f['source_reliability']:.1f} I:{f['structural_integrity']:.1f} D:{f['semantic_depth']:.1f}</td>
        </tr>
        """)

    # Conflict rows
    conflict_rows = []
    for cap_key, conf in dossier.capability_conflicts.items():
        cap_name = html.escape(_prop(cap_key, "value", str(cap_key)).replace("_", " ").title())
        diag, pos, neg, has_conf = _extract_conflict_fields(conf)
        flag_badge = (
            '<span class="badge badge-alert">⚠️ Flagged</span>'
            if has_conf
            else '<span class="badge badge-clear">Consistent</span>'
        )
        conflict_rows.append(f"""
        <tr>
            <td><strong>{cap_name}</strong></td>
            <td class="mono">{diag:+.2f}</td>
            <td class="mono text-emerald">{pos:.2f}</td>
            <td class="mono text-rose">{neg:.2f}</td>
            <td>{flag_badge}</td>
        </tr>
        """)

    # Version items
    version_items = "".join(
        f'<div class="metric-card"><div class="metric-label">{html.escape(k.replace("_", " ").title())}</div><div class="mono" style="font-size: 13px; color: var(--accent-indigo);">{html.escape(str(v))}</div></div>'
        for k, v in dossier.versions.items()
    )

    # Limitations items
    limitations_items = "".join(
        f"<li>{html.escape(lim)}</li>" for lim in dossier.system_limitations
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Full Audit & Governance Log — {cand_safe}</title>
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
            --accent-sky: #0ea5e9;
            --border-color: #374151;
            --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            --font-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background-color: var(--bg-primary);
            color: var(--text-main);
            font-family: var(--font-sans);
            font-size: 13px;
            line-height: 1.5;
            padding: 24px;
        }}
        .container {{ max-width: 1100px; margin: 0 auto; }}
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
        .header-card {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 24px;
        }}
        .header-title-row {{
            display: flex;
            justify-content: space-between;
            align-items: baseline;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 16px;
            margin-bottom: 16px;
        }}
        h1 {{ font-size: 24px; font-weight: 800; }}
        .badge {{
            display: inline-block;
            padding: 3px 8px;
            border-radius: 9999px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
        }}
        .badge-warning {{ background: rgba(245, 158, 11, 0.15); color: var(--accent-amber); border: 1px solid rgba(245, 158, 11, 0.3); }}
        .badge-info {{ background: rgba(14, 165, 233, 0.15); color: var(--accent-sky); border: 1px solid rgba(14, 165, 233, 0.3); }}
        .badge-observed {{ background: rgba(16, 185, 129, 0.15); color: var(--accent-emerald); border: 1px solid rgba(16, 185, 129, 0.3); }}
        .badge-conflict {{ background: rgba(244, 63, 94, 0.15); color: var(--accent-rose); border: 1px solid rgba(244, 63, 94, 0.3); }}
        .badge-unknown {{ background: rgba(107, 114, 128, 0.15); color: var(--text-muted); border: 1px solid var(--border-color); }}
        .badge-alert {{ background: rgba(244, 63, 94, 0.2); color: #fda4af; font-weight: 700; }}
        .badge-clear {{ background: rgba(16, 185, 129, 0.1); color: #6ee7b7; }}
        .section-title {{
            font-size: 16px;
            font-weight: 700;
            margin: 28px 0 12px 0;
            padding-bottom: 8px;
            border-bottom: 1px solid var(--border-color);
            color: var(--text-main);
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 12px;
            margin-bottom: 16px;
        }}
        .metric-card {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 12px;
        }}
        .metric-label {{
            font-size: 10px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-muted);
            margin-bottom: 4px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            overflow: hidden;
            margin-bottom: 24px;
        }}
        th, td {{
            padding: 10px 14px;
            text-align: left;
            border-bottom: 1px solid var(--border-color);
        }}
        th {{
            background: var(--bg-sub);
            font-weight: 600;
            color: var(--text-muted);
            font-size: 11px;
            text-transform: uppercase;
        }}
        .mono {{ font-family: var(--font-mono); font-size: 12px; }}
        .text-muted {{ color: var(--text-muted); }}
        .text-sub {{ color: var(--text-sub); }}
        .text-emerald {{ color: var(--accent-emerald); }}
        .text-rose {{ color: var(--accent-rose); }}
        ul.limitations-list {{
            list-style: disc;
            padding-left: 20px;
            color: var(--text-muted);
            line-height: 1.8;
            margin-bottom: 20px;
        }}
        footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid var(--border-color);
            color: var(--text-sub);
            font-size: 11px;
            text-align: center;
        }}
        @media print {{
            body {{ background: white !important; color: black !important; padding: 0 !important; }}
            .action-bar {{ display: none !important; }}
            .header-card, .metric-card, table {{
                background: white !important;
                border: 1px solid #ccc !important;
                color: black !important;
            }}
            th {{ background: #f3f4f6 !important; color: black !important; }}
            td {{ color: black !important; }}
            .badge {{ border: 1px solid #999 !important; color: black !important; background: transparent !important; }}
            footer {{ color: #666 !important; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="action-bar">
            <div>
                <strong>Candidate Capability Intelligence</strong>
                <span class="mono text-muted" style="margin-left: 8px;">Full Audit & Governance Log</span>
            </div>
            <button class="btn" onclick="window.print()">🖨️ Print / Save as PDF</button>
        </div>

        <div class="header-card">
            <div class="header-title-row">
                <div>
                    <h1>Full Audit Log: {cand_safe}</h1>
                    <p class="mono text-muted" style="margin-top: 4px;">Candidate ID: {dossier.candidate_id} • Run: {dossier.analysis_run_id} • Generated: {gen_time}</p>
                </div>
                <div>
                    <span class="badge badge-observed">APPEND-ONLY AUDIT LOG</span>
                </div>
            </div>

            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-label">Target Role</div>
                    <div class="mono" style="font-weight: 700; color: var(--text-main);">{html.escape(dossier.role.value)}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Evidence Mode</div>
                    <div class="mono" style="color: var(--accent-sky);">{html.escape(dossier.evidence_mode)}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Governance Events</div>
                    <div class="mono" style="font-size: 16px; font-weight: 700;">{len(events)}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Grounding Evidence</div>
                    <div class="mono" style="font-size: 16px; font-weight: 700;">{len(dossier.evidence_records)}</div>
                </div>
            </div>
        </div>

        <div class="section-title">1. Subsystem Versions & Runtime Provenance</div>
        <div class="metrics-grid">
            {version_items}
        </div>

        <div class="section-title">2. System Limitations & Formal Invariants</div>
        <ul class="limitations-list">
            {limitations_items}
        </ul>

        <div class="section-title">3. Immutable Governance Audit Trail</div>
        <table>
            <thead>
                <tr>
                    <th>Timestamp</th>
                    <th>Event Type</th>
                    <th>Actor / ID</th>
                    <th>Summary / Justification</th>
                    <th>Impact / Recommendation</th>
                </tr>
            </thead>
            <tbody>
                {"".join(event_rows)}
            </tbody>
        </table>

        <div class="section-title">4. Grounding Evidence Ledger (All Records)</div>
        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Capability</th>
                    <th>Polarity</th>
                    <th>Conf</th>
                    <th>Supp</th>
                    <th>Artifact Path</th>
                    <th>Location</th>
                    <th>Decomposition</th>
                </tr>
            </thead>
            <tbody>
                {"".join(evidence_rows)}
            </tbody>
        </table>

        <div class="section-title">5. Contradiction Diagnostics Audit</div>
        <table>
            <thead>
                <tr>
                    <th>Capability</th>
                    <th>Diagnostic D_k</th>
                    <th>Positive (P_k)</th>
                    <th>Contradictory (N_k)</th>
                    <th>Discrepancy Status</th>
                </tr>
            </thead>
            <tbody>
                {"".join(conflict_rows)}
            </tbody>
        </table>

        <footer>
            Candidate Capability Intelligence (CCI) Platform • Cryptographic Audit Trail & Governance Log • Confidential
        </footer>
    </div>
</body>
</html>
"""


def generate_audit_json(
    dossier: Dossier,
    audit_events: list[Any] | None = None,
    candidate_name: str = "Candidate",
) -> str:
    """Generates a complete JSON Full Audit package."""
    events = [_normalize_event(e) for e in (audit_events or [])]
    data = {
        "candidate_id": str(dossier.candidate_id),
        "candidate_name": candidate_name,
        "analysis_run_id": str(dossier.analysis_run_id),
        "dossier_id": str(dossier.dossier_id),
        "generated_at": dossier.generated_at.isoformat() if dossier.generated_at else None,
        "evidence_mode": dossier.evidence_mode,
        "scenario": dossier.scenario,
        "role": dossier.role.value,
        "coverage": dossier.coverage,
        "is_insufficient_evidence": dossier.is_insufficient_evidence,
        "rci": dossier.rci,
        "versions": dossier.versions,
        "system_limitations": dossier.system_limitations,
        "audit_events": events,
        "evidence_records": [
            rec.model_dump(mode="json") if hasattr(rec, "model_dump") else rec
            for rec in dossier.evidence_records
        ],
        "capability_conflicts": {
            k.value: conf.model_dump(mode="json") if hasattr(conf, "model_dump") else conf
            for k, conf in dossier.capability_conflicts.items()
        },
        "claims_corroboration": dossier.claims_corroboration,
        "override_history": dossier.override_history,
    }
    import json
    return json.dumps(data, indent=2, default=str)


def generate_audit_csv(
    audit_events: list[Any] | None = None,
    dossier: Dossier | None = None,
) -> str:
    """Generates an RFC 4180 CSV export of governance events and evidence records."""
    import csv
    import io

    output = io.StringIO()
    writer = csv.writer(output)

    # 1. Audit events table
    writer.writerow(["# CANDIDATE GOVERNANCE AUDIT TRAIL"])
    writer.writerow([
        "Event ID",
        "Timestamp",
        "Event Type",
        "Actor / ID",
        "Justification / Notes",
        "Previous RCI",
        "Rescored RCI",
        "Overall Recommendation",
    ])
    for ev in (audit_events or []):
        norm = _normalize_event(ev)
        details = norm.get("details", {}) or {}
        writer.writerow([
            norm.get("id", ""),
            norm.get("created_at", ""),
            norm.get("event_type", ""),
            norm.get("user_id") or details.get("interviewer_name") or "",
            details.get("justification") or details.get("overall_notes") or "",
            details.get("previous_rci", ""),
            details.get("rescored_rci", ""),
            details.get("overall_recommendation", ""),
        ])

    if dossier and dossier.evidence_records:
        writer.writerow([])
        writer.writerow(["# GROUNDING EVIDENCE LEDGER"])
        writer.writerow([
            "Evidence ID",
            "Target Capability",
            "Polarity",
            "Confidence",
            "Support Score",
            "Artifact Path",
            "Line Start",
            "Line End",
            "Source Reliability",
            "Structural Integrity",
            "Semantic Depth",
            "Raw Support Text",
        ])
        for rec in dossier.evidence_records:
            f = _extract_evidence_fields(rec)
            writer.writerow([
                f["evidence_id"],
                f["capability"],
                "POSITIVE" if f["is_positive"] else "NEGATIVE",
                f"{f['confidence']:.3f}",
                f"{f['support_score']:.3f}",
                f["artifact_path"],
                f["line_start"] or "",
                f["line_end"] or "",
                f"{f['source_reliability']:.2f}",
                f"{f['structural_integrity']:.2f}",
                f"{f['semantic_depth']:.2f}",
                (f["raw_support_text"] or "").replace("\n", " ")[:200],
            ])

    return output.getvalue()


def generate_combined_report_and_audit_markdown(
    dossier: Dossier,
    audit_events: list[Any] | None = None,
    candidate_name: str = "Candidate",
) -> str:
    """Generates a combined Technical Intelligence Report and Full Audit Markdown package."""
    report_md = generate_markdown_brief(dossier, candidate_name)
    audit_md = generate_audit_markdown(dossier, audit_events, candidate_name)
    return (
        f"{report_md}\n\n"
        f"---\n\n"
        f"# PART II: COMPLETE GOVERNANCE & PROVENANCE AUDIT\n\n"
        f"{audit_md}\n"
    )


def generate_combined_report_and_audit_html(
    dossier: Dossier,
    audit_events: list[Any] | None = None,
    candidate_name: str = "Candidate",
) -> str:
    """Generates a unified printable HTML bundle containing both Report and Full Audit."""
    # Build complete HTML by appending audit sections inside the report container
    audit_html_full = generate_audit_html(dossier, audit_events, candidate_name)
    # Extract inner container of audit HTML to integrate into report
    container_start = audit_html_full.find('<div class="container">')
    container_end = audit_html_full.rfind('</div>')
    audit_inner = (
        audit_html_full[container_start + len('<div class="container">'):container_end]
        if container_start != -1 and container_end != -1
        else ""
    )

    report_html = generate_html_brief(dossier, candidate_name)
    insertion_point = report_html.rfind('<footer>')
    if insertion_point != -1 and audit_inner:
        combined = (
            report_html[:insertion_point]
            + '<div style="margin-top: 60px; padding-top: 30px; border-top: 3px double var(--border-color);">'
            + '<h2 style="font-size: 20px; font-weight: 800; margin-bottom: 20px; color: var(--accent-indigo);">PART II: FULL AUDIT & GOVERNANCE LOG</h2>'
            + audit_inner
            + '</div>'
            + report_html[insertion_point:]
        )
        return combined
    return report_html


def generate_combined_report_and_audit_json(
    dossier: Dossier,
    audit_events: list[Any] | None = None,
    candidate_name: str = "Candidate",
) -> str:
    """Generates a unified JSON bundle containing both Report dossier and Full Audit."""
    import json
    events = [_normalize_event(e) for e in (audit_events or [])]
    dossier_data = dossier.model_dump(mode="json")
    data = {
        "candidate_id": str(dossier.candidate_id),
        "candidate_name": candidate_name,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "report": dossier_data,
        "full_audit": {
            "analysis_run_id": str(dossier.analysis_run_id),
            "generated_at": dossier.generated_at.isoformat() if dossier.generated_at else None,
            "evidence_mode": dossier.evidence_mode,
            "versions": dossier.versions,
            "system_limitations": dossier.system_limitations,
            "audit_events": events,
            "evidence_records_count": len(dossier.evidence_records),
            "evidence_records": [
                rec.model_dump(mode="json") if hasattr(rec, "model_dump") else rec
                for rec in dossier.evidence_records
            ],
            "capability_conflicts": {
                k.value: conf.model_dump(mode="json") if hasattr(conf, "model_dump") else conf
                for k, conf in dossier.capability_conflicts.items()
            },
            "claims_corroboration": dossier.claims_corroboration,
            "override_history": dossier.override_history,
        },
    }
    return json.dumps(data, indent=2, default=str)

