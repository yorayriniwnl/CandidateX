import roster from '../data/team-members.json';
import type { CandidateSummary } from './api';

// Shared with scripts/seed_db.py. SDE uses fullstack and SRE uses devops_cloud
// for evaluation; role_label preserves each member's stated specialization.
export const TEAM_MEMBERS = roster;

export const TEAM_CANDIDATES: CandidateSummary[] = TEAM_MEMBERS.map((member) => ({
  id: member.id,
  display_name: member.name,
  primary_email: member.email,
  role: member.role,
  role_label: member.role_label,
  has_completed_dossier: false,
  has_meaningful_conflict: false,
  created_at: '',
}));

function normalizeTeamMember<T extends CandidateSummary>(candidate: T): T {
  const email = candidate.primary_email?.trim().toLowerCase();
  const member = TEAM_MEMBERS.find((item) => item.id === candidate.id || item.email === email);
  if (!member) return candidate;
  return {
    ...candidate,
    display_name: member.name,
    primary_email: member.email,
    role: member.role,
    role_label: member.role_label,
  };
}

// Earlier lists take precedence so saved reviews and live dossiers retain their
// IDs and evaluation data, including when a previous sample used a different ID.
export function mergeCandidateLists<T extends CandidateSummary>(...lists: T[][]): T[] {
  const ids = new Set<string>();
  const emails = new Set<string>();
  const merged: T[] = [];
  for (const candidate of lists.flat()) {
    const normalized = normalizeTeamMember(candidate);
    const email = normalized.primary_email?.trim().toLowerCase();
    const duplicate = ids.has(normalized.id) || (email && emails.has(email));
    ids.add(normalized.id);
    if (email) emails.add(email);
    if (!duplicate) merged.push(normalized);
  }
  return merged;
}
