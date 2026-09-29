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

export function normalizeTeamMember<T extends CandidateSummary>(candidate: T): T {
  const email = candidate.primary_email?.trim().toLowerCase();
  const name = candidate.display_name?.trim().toLowerCase();
  const member = TEAM_MEMBERS.find((item) => {
    if (item.id === candidate.id) return true;
    if (email && item.email.toLowerCase() === email) return true;
    if (name && (item.name.toLowerCase() === name || name.includes(item.name.toLowerCase()))) return true;
    return false;
  });
  if (!member) {
    return {
      ...candidate,
      primary_email: candidate.primary_email ? candidate.primary_email.trim().toLowerCase() : candidate.primary_email,
    };
  }
  return {
    ...candidate,
    display_name: member.name,
    primary_email: member.email,
    role: candidate.role || member.role,
    role_label: member.role_label,
  };
}

// Earlier lists take precedence so saved reviews and live dossiers retain their
// IDs and evaluation data, including when a previous sample used a different ID.
// Deduplication covers ID, primary email, and candidate display name to prevent repetition.
export function mergeCandidateLists<T extends CandidateSummary>(...lists: T[][]): T[] {
  const seenIds = new Set<string>();
  const seenEmails = new Set<string>();
  const seenNames = new Set<string>();
  const merged: T[] = [];

  for (const candidate of lists.flat()) {
    if (!candidate) continue;
    const normalized = normalizeTeamMember(candidate);
    const email = normalized.primary_email?.trim().toLowerCase();
    const name = normalized.display_name?.trim().toLowerCase();
    const id = normalized.id;

    const duplicate =
      (id && seenIds.has(id)) ||
      (email && seenEmails.has(email)) ||
      (name && seenNames.has(name));

    if (!duplicate) {
      if (id) seenIds.add(id);
      if (email) seenEmails.add(email);
      if (name) seenNames.add(name);
      merged.push(normalized);
    } else {
      // Find existing entry and merge evaluation data if incoming has it
      const existingIdx = merged.findIndex((m) => {
        const mEmail = m.primary_email?.trim().toLowerCase();
        const mName = m.display_name?.trim().toLowerCase();
        return (id && m.id === id) || (email && mEmail === email) || (name && mName === name);
      });
      if (existingIdx !== -1) {
        const existing = merged[existingIdx];
        if (!existing.has_completed_dossier && normalized.has_completed_dossier) {
          merged[existingIdx] = {
            ...existing,
            ...normalized,
            display_name: existing.display_name,
            primary_email: existing.primary_email || normalized.primary_email,
            role_label: existing.role_label || normalized.role_label,
          };
        } else if (normalized.rci != null && (existing.rci == null || (normalized.rci > 0 && existing.rci <= 0))) {
          merged[existingIdx] = {
            ...existing,
            ...normalized,
            display_name: existing.display_name,
            primary_email: existing.primary_email || normalized.primary_email,
            role_label: existing.role_label || normalized.role_label,
          };
        }
      }
    }
  }
  return merged;
}
