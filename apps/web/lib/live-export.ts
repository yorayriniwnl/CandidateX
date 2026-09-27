'use client';

import type { LiveResult } from './live-analysis';
import type { ExportFormat, ExportScope } from './api';
import { downloadDossier } from './api';
import { capabilityName } from '../components/evidence-os/format';

function escapeHtml(str: string): string {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function escapeCsvCell(val: unknown): string {
  if (val === null || val === undefined) return '""';
  const str = String(val).replace(/"/g, '""');
  return `"${str}"`;
}

function triggerDownload(content: string, filename: string, mimeType: string) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function generateLiveReportMarkdown(result: LiveResult): string {
  const dossier = result.dossier;
  const name = result.intake.manifest.display_name;
  const estimates = Object.values(dossier.capability_estimates);

  let md = `# Candidate Technical Intelligence Report: ${name}\n\n`;
  md += `**Target Role:** ${dossier.role.replace(/_/g, ' ')}\n`;
  md += `**Role Capability Index (RCI):** ${dossier.rci !== null ? dossier.rci.toFixed(1) : 'UNKNOWN / SPARSE EVIDENCE'} / 100\n`;
  md += `**Role Coverage:** ${(dossier.coverage * 100).toFixed(1)}%\n`;
  md += `**Analysis Run ID:** \`${dossier.analysis_run_id}\`\n`;
  md += `**Generated At:** ${dossier.generated_at}\n\n`;
  md += `---\n\n`;

  md += `## 1. Capability Breakdown\n\n`;
  md += `| Capability | Estimate | 95% Confidence Interval | Role Weight | Evidence Records | Status |\n`;
  md += `|---|---|---|---|---|---|\n`;
  for (const est of estimates) {
    const capName = capabilityName(est.capability_key);
    const estVal = est.is_observed && est.estimate !== null ? `${est.estimate.toFixed(1)}/100` : 'UNKNOWN';
    const ci = est.ci_lower !== null && est.ci_upper !== null ? `[${est.ci_lower.toFixed(1)}, ${est.ci_upper.toFixed(1)}]` : 'N/A';
    const weight = dossier.role_weights?.[est.capability_key] !== undefined ? `${(dossier.role_weights[est.capability_key] * 100).toFixed(0)}%` : 'N/A';
    const status = !est.is_observed ? 'Unknown' : 'Observed';
    md += `| **${capName}** | ${estVal} | ${ci} | ${weight} | ${est.raw_evidence_count} | ${status} |\n`;
  }
  md += `\n---\n\n`;

  md += `## 2. Interview Probes & Follow-Up Questions\n\n`;
  if (dossier.interview_questions.length === 0) {
    md += `_No targeted interview questions generated for this candidate._\n\n`;
  } else {
    dossier.interview_questions.forEach((q, idx) => {
      md += `### Probe ${idx + 1}: ${capabilityName(q.target_capability)}\n`;
      md += `> **Question:** ${q.question_text}\n\n`;
      md += `* **Rationale:** ${q.rationale}\n`;
      md += `* **Verification Guidance:** ${q.verification_guidance}\n\n`;
    });
  }
  md += `---\n\n`;

  md += `## 3. Resume & Claims Corroboration Matrix\n\n`;
  if (dossier.claims_corroboration.length === 0) {
    md += `_No claims evaluated._\n\n`;
  } else {
    md += `| Target Capability | Claim Declaration | Verification Status |\n`;
    md += `|---|---|---|\n`;
    for (const claim of dossier.claims_corroboration) {
      md += `| ${capabilityName(claim.target_capability)} | ${claim.claim_text} | **${claim.status.toUpperCase()}** |\n`;
    }
    md += `\n`;
  }

  return md;
}

export function generateLiveAuditMarkdown(result: LiveResult): string {
  const dossier = result.dossier;
  const name = result.intake.manifest.display_name;

  let md = `# Candidate Governance & Full Audit Trail: ${name}\n\n`;
  md += `**Analysis Run ID:** \`${dossier.analysis_run_id}\`\n`;
  md += `**Candidate Request ID:** \`${dossier.candidate_id}\`\n`;
  md += `**Generated Timestamp:** ${dossier.generated_at}\n`;
  md += `**Evidence Mode:** ${dossier.evidence_mode ?? 'live'}\n`;
  md += `**Storage Scope:** ${result.intake.storage ?? 'session'}\n\n`;
  md += `---\n\n`;

  md += `## Subsystem Component Versions\n\n`;
  if (Object.keys(dossier.versions || {}).length === 0) {
    md += `_No component versions returned._\n\n`;
  } else {
    md += `| Component Subsystem | Version Specification |\n|---|---|\n`;
    for (const [comp, ver] of Object.entries(dossier.versions)) {
      md += `| ${comp} | \`${ver}\` |\n`;
    }
    md += `\n`;
  }

  md += `## System Limitations & Governance Invariants\n\n`;
  if (!dossier.system_limitations || dossier.system_limitations.length === 0) {
    md += `_Standard invariants apply: Static observation only, no implicit mastery assertion._\n\n`;
  } else {
    for (const lim of dossier.system_limitations) {
      md += `- ${lim}\n`;
    }
    md += `\n`;
  }
  md += `---\n\n`;

  md += `## Grounding Evidence Ledger (${dossier.evidence_records.length} records)\n\n`;
  if (dossier.evidence_records.length === 0) {
    md += `_No evidence records present in this run._\n\n`;
  } else {
    md += `| Evidence ID | Target Capability | Polarity | Support | Confidence | Source Artifact | Observation |\n`;
    md += `|---|---|---|---|---|---|---|\n`;
    for (const rec of dossier.evidence_records) {
      const pol = rec.is_positive_support ? 'Supporting' : 'Contradicting';
      const path = rec.provenance?.artifact_path || 'Unknown';
      const obs = (rec.provenance?.raw_support_text || '').replace(/\n/g, ' ').slice(0, 100);
      md += `| \`${rec.evidence_id.slice(0, 12)}\` | ${capabilityName(rec.target_capability)} | ${pol} | ${rec.support_score.toFixed(2)} | ${rec.confidence.toFixed(2)} | \`${path}\` | ${obs} |\n`;
    }
    md += `\n`;
  }

  return md;
}

export function generateLiveAuditCsv(result: LiveResult): string {
  const dossier = result.dossier;
  const headers = [
    'Evidence ID',
    'Candidate ID',
    'Target Capability',
    'Polarity',
    'Support Score',
    'Confidence',
    'Cluster ID',
    'Artifact Path',
    'Line Start',
    'Line End',
    'Raw Observation Text',
  ];

  const rows = (dossier.evidence_records || []).map(e => [
    escapeCsvCell(e.evidence_id),
    escapeCsvCell(dossier.candidate_id),
    escapeCsvCell(e.target_capability),
    escapeCsvCell(e.is_positive_support ? 'SUPPORTING' : 'CONTRADICTING'),
    escapeCsvCell(e.support_score),
    escapeCsvCell(e.confidence),
    escapeCsvCell(e.cluster_id || ''),
    escapeCsvCell(e.provenance?.artifact_path || ''),
    escapeCsvCell((e.provenance as any)?.line_start ?? ''),
    escapeCsvCell((e.provenance as any)?.line_end ?? ''),
    escapeCsvCell(e.provenance?.raw_support_text || ''),
  ]);

  return [headers.map(escapeCsvCell).join(','), ...rows.map(r => r.join(','))].join('\n');
}

export function generateLiveReportHtml(result: LiveResult): string {
  const dossier = result.dossier;
  const name = escapeHtml(result.intake.manifest.display_name);
  const role = escapeHtml(dossier.role.replace(/_/g, ' '));
  const rci = dossier.rci !== null ? dossier.rci.toFixed(1) : 'UNKNOWN';
  const cov = (dossier.coverage * 100).toFixed(0);

  const estimatesRows = Object.values(dossier.capability_estimates)
    .map(est => {
      const capName = escapeHtml(capabilityName(est.capability_key));
      const score = est.is_observed && est.estimate !== null ? `${est.estimate.toFixed(1)}/100` : 'UNKNOWN';
      const ci = est.ci_lower !== null && est.ci_upper !== null ? `${est.ci_lower.toFixed(0)} - ${est.ci_upper.toFixed(0)}` : 'N/A';
      const weight = dossier.role_weights?.[est.capability_key] !== undefined ? `${(dossier.role_weights[est.capability_key] * 100).toFixed(0)}%` : 'N/A';
      return `<tr>
        <td style="padding:10px 14px;border-bottom:1px solid #332644;font-weight:600;">${capName}</td>
        <td style="padding:10px 14px;border-bottom:1px solid #332644;color:#a78bfa;">${score}</td>
        <td style="padding:10px 14px;border-bottom:1px solid #332644;color:#94a3b8;">${ci}</td>
        <td style="padding:10px 14px;border-bottom:1px solid #332644;color:#cbd5e1;">${weight}</td>
        <td style="padding:10px 14px;border-bottom:1px solid #332644;color:#94a3b8;">${est.raw_evidence_count}</td>
      </tr>`;
    })
    .join('');

  const questionsHtml = (dossier.interview_questions || [])
    .map((q, i) => `
      <div style="background:#1e142b;border:1px solid #3f2e56;border-radius:8px;padding:16px;margin-bottom:12px;">
        <div style="font-size:10px;text-transform:uppercase;color:#a78bfa;font-weight:600;letter-spacing:0.08em;margin-bottom:4px;">
          Probe ${i + 1} &bull; ${escapeHtml(capabilityName(q.target_capability))}
        </div>
        <div style="font-size:14px;font-weight:500;color:#f1f5f9;margin-bottom:8px;">${escapeHtml(q.question_text)}</div>
        <div style="font-size:12px;color:#94a3b8;line-height:1.5;"><strong>Why ask:</strong> ${escapeHtml(q.rationale)}</div>
        <div style="font-size:12px;color:#94a3b8;line-height:1.5;margin-top:4px;"><strong>Verification:</strong> ${escapeHtml(q.verification_guidance)}</div>
      </div>
    `)
    .join('');

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>${name} - Technical Intelligence Report</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0c0814; color: #ede4f5; margin: 0; padding: 40px 20px; line-height: 1.5; }
    .container { max-width: 900px; margin: 0 auto; }
    .header { border-bottom: 2px solid #38244f; padding-bottom: 24px; margin-bottom: 30px; display: flex; justify-content: space-between; align-items: flex-end; }
    h1 { margin: 0 0 6px; font-size: 32px; color: #fff; }
    .meta { color: #a594b8; font-size: 13px; }
    .scores { display: flex; gap: 20px; margin-bottom: 30px; }
    .card { background: #160f24; border: 1px solid #382650; border-radius: 10px; padding: 18px 24px; flex: 1; }
    .card-title { font-size: 11px; text-transform: uppercase; color: #a594b8; letter-spacing: 0.1em; }
    .card-value { font-size: 32px; font-weight: 700; color: #d8b4fe; margin-top: 4px; }
    table { width: 100%; border-collapse: collapse; background: #160f24; border: 1px solid #382650; border-radius: 10px; overflow: hidden; margin-bottom: 30px; font-size: 13px; }
    th { background: #221438; text-align: left; padding: 12px 14px; font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em; color: #c4b5fd; border-bottom: 1px solid #3f2c59; }
    h2 { font-size: 18px; color: #e2e8f0; margin: 30px 0 14px; }
    @media print { body { background: #fff; color: #000; padding: 0; } .card, table { border-color: #ccc; background: #fff; } th { background: #eee; color: #000; } }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div>
        <div style="font-size:10px;text-transform:uppercase;color:#c084fc;letter-spacing:0.12em;font-weight:600;margin-bottom:6px;">Candidate Intelligence &bull; Technical Dossier</div>
        <h1>${name}</h1>
        <div class="meta">Target Role: <strong>${role}</strong> &bull; Run ID: <code>${escapeHtml(dossier.analysis_run_id)}</code></div>
      </div>
      <div style="text-align:right;">
        <div class="meta">Generated: ${escapeHtml(new Date(dossier.generated_at).toLocaleString())}</div>
      </div>
    </div>
    <div class="scores">
      <div class="card">
        <div class="card-title">Role Capability Index</div>
        <div class="card-value">${rci} <span style="font-size:14px;color:#a594b8;">/ 100</span></div>
      </div>
      <div class="card">
        <div class="card-title">Evidence Coverage</div>
        <div class="card-value">${cov}%</div>
      </div>
      <div class="card">
        <div class="card-title">Evidence Records</div>
        <div class="card-value">${dossier.evidence_records.length}</div>
      </div>
    </div>
    <h2>01 / Capability Matrix</h2>
    <table>
      <thead>
        <tr><th>Capability</th><th>Estimate</th><th>95% Interval</th><th>Role Importance</th><th>Evidence Count</th></tr>
      </thead>
      <tbody>${estimatesRows}</tbody>
    </table>
    <h2>02 / Targeted Interview Follow-Up Plan</h2>
    <div>${questionsHtml || '<p style="color:#94a3b8;">No questions available.</p>'}</div>
  </div>
</body>
</html>`;
}

export function generateLiveAuditHtml(result: LiveResult): string {
  const dossier = result.dossier;
  const name = escapeHtml(result.intake.manifest.display_name);

  const versionsRows = Object.entries(dossier.versions || {})
    .map(([k, v]) => `<tr><td style="padding:8px 12px;border-bottom:1px solid #332644;font-weight:600;">${escapeHtml(k)}</td><td style="padding:8px 12px;border-bottom:1px solid #332644;color:#a78bfa;font-family:monospace;">${escapeHtml(v)}</td></tr>`)
    .join('');

  const limitationsList = (dossier.system_limitations || [])
    .map(lim => `<li style="margin-bottom:6px;">${escapeHtml(lim)}</li>`)
    .join('');

  const evidenceRows = (dossier.evidence_records || [])
    .map(e => `
      <tr>
        <td style="padding:8px 12px;border-bottom:1px solid #332644;font-family:monospace;font-size:11px;">${escapeHtml(e.evidence_id.slice(0, 10))}</td>
        <td style="padding:8px 12px;border-bottom:1px solid #332644;">${escapeHtml(capabilityName(e.target_capability))}</td>
        <td style="padding:8px 12px;border-bottom:1px solid #332644;color:${e.is_positive_support ? '#34d399' : '#f87171'};font-weight:600;">${e.is_positive_support ? 'SUPPORT' : 'CONTRADICT'}</td>
        <td style="padding:8px 12px;border-bottom:1px solid #332644;">${e.confidence.toFixed(2)}</td>
        <td style="padding:8px 12px;border-bottom:1px solid #332644;font-family:monospace;font-size:11px;max-width:200px;overflow:hidden;text-overflow:ellipsis;">${escapeHtml(e.provenance?.artifact_path || 'Unknown')}</td>
        <td style="padding:8px 12px;border-bottom:1px solid #332644;font-size:11px;color:#94a3b8;max-width:280px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${escapeHtml(e.provenance?.raw_support_text || '')}</td>
      </tr>
    `)
    .join('');

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>${name} - Governance Audit Trail</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0c0814; color: #ede4f5; margin: 0; padding: 40px 20px; line-height: 1.5; }
    .container { max-width: 1000px; margin: 0 auto; }
    .header { border-bottom: 2px solid #38244f; padding-bottom: 20px; margin-bottom: 24px; }
    h1 { margin: 0 0 6px; font-size: 28px; color: #fff; }
    .meta { color: #a594b8; font-size: 12px; font-family: monospace; }
    table { width: 100%; border-collapse: collapse; background: #160f24; border: 1px solid #382650; border-radius: 8px; overflow: hidden; margin-bottom: 24px; font-size: 12px; }
    th { background: #221438; text-align: left; padding: 10px 12px; font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em; color: #c4b5fd; border-bottom: 1px solid #3f2c59; }
    h2 { font-size: 16px; color: #e2e8f0; margin: 24px 0 12px; }
    .box { background: #160f24; border: 1px solid #382650; border-radius: 8px; padding: 16px; margin-bottom: 24px; font-size: 13px; color: #cbd5e1; }
    @media print { body { background: #fff; color: #000; padding: 0; } table, .box { border-color: #ccc; background: #fff; color: #000; } th { background: #eee; color: #000; } }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div style="font-size:10px;text-transform:uppercase;color:#34d399;letter-spacing:0.12em;font-weight:600;margin-bottom:6px;">Governance &bull; Immutable Audit Ledger</div>
      <h1>Candidate Full Audit: ${name}</h1>
      <div class="meta">Run ID: ${escapeHtml(dossier.analysis_run_id)} &bull; Candidate ID: ${escapeHtml(dossier.candidate_id)} &bull; ${escapeHtml(new Date(dossier.generated_at).toUTCString())}</div>
    </div>
    <h2>Subsystem Versions</h2>
    <table><thead><tr><th>Component</th><th>Version</th></tr></thead><tbody>${versionsRows || '<tr><td colspan="2" style="padding:10px;">None returned</td></tr>'}</tbody></table>
    <h2>System Limitations & Governance Boundaries</h2>
    <div class="box"><ul style="margin:0;padding-left:20px;">${limitationsList || '<li>Standard invariants apply.</li>'}</ul></div>
    <h2>Grounding Evidence Ledger (${dossier.evidence_records.length} records)</h2>
    <table><thead><tr><th>ID</th><th>Capability</th><th>Polarity</th><th>Conf</th><th>Source Artifact</th><th>Observation</th></tr></thead><tbody>${evidenceRows}</tbody></table>
  </div>
</body>
</html>`;
}

export function generateCombinedLiveHtml(result: LiveResult): string {
  const reportHtml = generateLiveReportHtml(result);
  const auditHtml = generateLiveAuditHtml(result);

  // Extract container contents
  const reportMatch = reportHtml.match(/<div class="container">([\s\S]*?)<\/div>\s*<\/body>/);
  const auditMatch = auditHtml.match(/<div class="container">([\s\S]*?)<\/div>\s*<\/body>/);

  const reportBody = reportMatch ? reportMatch[1] : '';
  const auditBody = auditMatch ? auditMatch[1] : '';

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>${escapeHtml(result.intake.manifest.display_name)} - Technical Intelligence Report & Full Audit</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0c0814; color: #ede4f5; margin: 0; padding: 40px 20px; line-height: 1.5; }
    .container { max-width: 1000px; margin: 0 auto; }
    .header { border-bottom: 2px solid #38244f; padding-bottom: 24px; margin-bottom: 30px; display: flex; justify-content: space-between; align-items: flex-end; }
    h1 { margin: 0 0 6px; font-size: 32px; color: #fff; }
    .meta { color: #a594b8; font-size: 13px; }
    .scores { display: flex; gap: 20px; margin-bottom: 30px; }
    .card { background: #160f24; border: 1px solid #382650; border-radius: 10px; padding: 18px 24px; flex: 1; }
    .card-title { font-size: 11px; text-transform: uppercase; color: #a594b8; letter-spacing: 0.1em; }
    .card-value { font-size: 32px; font-weight: 700; color: #d8b4fe; margin-top: 4px; }
    table { width: 100%; border-collapse: collapse; background: #160f24; border: 1px solid #382650; border-radius: 8px; overflow: hidden; margin-bottom: 26px; font-size: 12px; }
    th { background: #221438; text-align: left; padding: 10px 12px; font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em; color: #c4b5fd; border-bottom: 1px solid #3f2c59; }
    h2 { font-size: 18px; color: #e2e8f0; margin: 30px 0 14px; }
    .box { background: #160f24; border: 1px solid #382650; border-radius: 8px; padding: 16px; margin-bottom: 24px; font-size: 13px; color: #cbd5e1; }
    .section-divider { margin: 60px 0; border: 0; border-top: 2px dashed #4e366d; }
    @media print { body { background: #fff; color: #000; padding: 0; } .card, table, .box { border-color: #ccc; background: #fff; color: #000; } th { background: #eee; color: #000; } .section-divider { page-break-after: always; } }
  </style>
</head>
<body>
  <div class="container">
    <div style="text-align:center;padding:12px;background:#1a102b;border:1px solid #4a306d;border-radius:8px;margin-bottom:28px;">
      <span style="font-size:11px;text-transform:uppercase;letter-spacing:0.12em;color:#c084fc;font-weight:600;">CandidateX Complete Intelligence Package &bull; Report + Immutable Audit Ledger</span>
    </div>
    ${reportBody}
    <hr class="section-divider" />
    ${auditBody}
  </div>
</body>
</html>`;
}

/**
 * High-level export dispatcher for live evaluation.
 * Attempts direct backend export and seamlessly falls back to client-side generation.
 */
export async function exportLiveEvaluation(
  result: LiveResult,
  format: ExportFormat,
  scope: ExportScope
): Promise<void> {
  const candidateName = result.intake.manifest.display_name || 'candidate';
  const cleanName = candidateName.toLowerCase().replace(/[^a-z0-9]/g, '_');
  const scopeSuffix =
    scope === 'audit'
      ? 'full_audit'
      : scope === 'full'
      ? 'report_and_full_audit'
      : 'technical_report';
  const ext = format === 'markdown' ? 'md' : format;
  const filename = `${cleanName}_${scopeSuffix}.${ext}`;

  // 1. Attempt backend direct export
  try {
    await downloadDossier(result.dossier.candidate_id, format, candidateName, scope);
    return;
  } catch (err) {
    console.warn('Backend export endpoint returned error, generating export client-side:', err);
  }

  // 2. Client-side fallback generator
  if (format === 'json') {
    let jsonContent = '';
    if (scope === 'report') {
      jsonContent = JSON.stringify(result.dossier, null, 2);
    } else if (scope === 'audit') {
      jsonContent = JSON.stringify(
        {
          analysis_run_id: result.dossier.analysis_run_id,
          candidate_id: result.dossier.candidate_id,
          generated_at: result.dossier.generated_at,
          evidence_mode: result.dossier.evidence_mode,
          versions: result.dossier.versions,
          system_limitations: result.dossier.system_limitations,
          evidence_records: result.dossier.evidence_records,
        },
        null,
        2
      );
    } else {
      jsonContent = JSON.stringify(result, null, 2);
    }
    triggerDownload(jsonContent, filename, 'application/json');
    return;
  }

  if (format === 'csv') {
    const csvContent = generateLiveAuditCsv(result);
    triggerDownload(csvContent, filename, 'text/csv');
    return;
  }

  if (format === 'markdown') {
    let md = '';
    if (scope === 'report') {
      md = generateLiveReportMarkdown(result);
    } else if (scope === 'audit') {
      md = generateLiveAuditMarkdown(result);
    } else {
      md = `${generateLiveReportMarkdown(result)}\n\n---\n\n${generateLiveAuditMarkdown(result)}`;
    }
    triggerDownload(md, filename, 'text/markdown');
    return;
  }

  if (format === 'html') {
    let html = '';
    if (scope === 'report') {
      html = generateLiveReportHtml(result);
    } else if (scope === 'audit') {
      html = generateLiveAuditHtml(result);
    } else {
      html = generateCombinedLiveHtml(result);
    }
    triggerDownload(html, filename, 'text/html');
    return;
  }
}
