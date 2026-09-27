import type { LiveResult } from './live-analysis';

export interface ResultClaim {
  id: string;
  claim: string;
  status: string;
  explanation: string;
  ids: string[];
  paths: string[];
  count: number;
}

export function needsClaimVerification(status: string): boolean {
  return !['supported', 'corroborated', 'repository_support'].includes(status);
}

/** Shared display ledger; unassessed declarations stay unverified, with no rescoring. */
export function resultClaims(result: LiveResult): ResultClaim[] {
  const normalize = (text: string) => text.trim().toLowerCase();
  const assessedSkills = new Set([
    ...result.dossier.claims_corroboration.map(claim => normalize(claim.claim_text)),
    ...result.analysis.skills.map(skill => normalize(skill.skill)),
  ]);
  const corroboratedClaims = new Set(result.dossier.claims_corroboration.map(claim => normalize(claim.claim_text)));

  return [
    ...result.dossier.claims_corroboration.map(claim => ({
      id: claim.claim_id, claim: claim.claim_text, status: claim.status,
      explanation: claim.explanation, ids: claim.grounding_evidence_ids,
      paths: claim.citation_urls, count: claim.grounding_evidence_ids.length,
    })),
    ...result.analysis.skills.filter(skill => !corroboratedClaims.has(normalize(skill.skill))).map((skill, index) => ({
      id: `skill-${index}`, claim: skill.skill + (skill.learning ? ' · Currently learning' : ''),
      status: skill.status, explanation: skill.explanation, ids: [],
      paths: skill.evidence.map(evidence => evidence.url), count: skill.evidence_count,
    })),
    ...result.intake.manifest.claimed_skills.filter(skill => !assessedSkills.has(normalize(skill))).map((skill, index) => ({
      id: `declaration-${index}`, claim: skill, status: 'unverified',
      explanation: 'Declared in the résumé. No claim assessment was returned for this skill.',
      ids: [], paths: [], count: 0,
    })),
    ...result.analysis.credentials.map((credential, index) => ({
      id: `credential-${index}`, claim: credential.claim, status: credential.status,
      explanation: credential.explanation, ids: [],
      paths: credential.matching_pages.map(page => page.url), count: credential.matching_pages.length,
    })),
    ...result.analysis.quantified_claims_to_verify.map((claim, index) => ({
      id: `quantity-${index}`, claim, status: 'unverified',
      explanation: 'This numeric claim was extracted for follow-up. No independent verification was returned.',
      ids: [], paths: [], count: 0,
    })),
  ];
}
