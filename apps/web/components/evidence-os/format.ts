import type { CapabilityKey, CanonicalRole } from '../../types/cci';

export function words(value: string): string {
  return value.replaceAll('_', ' ').replace(/\s+/g, ' ').trim();
}

export function titleWords(value: string): string {
  return words(value).replace(/\b[a-z]/g, character => character.toUpperCase());
}

export function roleName(role: CanonicalRole): string {
  return titleWords(role);
}

export function capabilityName(capability: CapabilityKey | string): string {
  const aliases: Partial<Record<CapabilityKey, string>> = {
    devops_cloud: 'DevOps & cloud',
    machine_learning: 'Machine learning',
    algorithms_problem_solving: 'Algorithms & problem solving',
    testing_quality: 'Testing & quality',
    documentation_communication: 'Documentation & communication',
  };
  return aliases[capability as CapabilityKey] ?? titleWords(capability);
}

export function percent(value: number | null | undefined, digits = 1): string {
  return value == null ? 'UNKNOWN' : `${(value * 100).toFixed(digits)}%`;
}

export function score(value: number | null | undefined, digits = 1): string {
  return value == null ? 'UNKNOWN' : value.toFixed(digits);
}

export function humanStatus(value: string): string {
  return words(value).toLowerCase();
}

export function dateTime(value?: string): string {
  if (!value) return 'Not returned';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(date);
}

