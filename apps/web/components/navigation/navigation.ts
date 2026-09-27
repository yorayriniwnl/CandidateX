export type Surface = 'home' | 'live' | 'candidates' | 'workspace' | 'research';
export type SurfaceStatus = 'live';

export const NAVIGATION_ITEMS = [
  { key: 'home', label: 'Home', href: '/', shortLabel: 'Home' },
  { key: 'live', label: 'Live Evidence', href: '/analyze', shortLabel: 'Live' },
  { key: 'candidates', label: 'Candidates', href: '/hr', shortLabel: 'Candidates' },
  { key: 'workspace', label: 'Workspace', href: '/workspace', shortLabel: 'Workspace' },
  { key: 'research', label: 'Research', href: '/research-demo', shortLabel: 'Research' },
] as const;

export type NavigationItem = (typeof NAVIGATION_ITEMS)[number];

export const SURFACE_COPY: Record<Surface, { label: string; descriptor: string }> = {
  home: { label: 'Command center', descriptor: 'Candidate capability intelligence' },
  live: { label: 'Live Evidence', descriptor: 'Resume to interview' },
  candidates: { label: 'Candidates', descriptor: 'Your hiring workspace' },
  workspace: { label: 'Workspace', descriptor: 'Research prototype' },
  research: { label: 'Research', descriptor: 'Inside the intelligence' },
};

export const STATUS_COPY: Record<SurfaceStatus, { label: string; detail: string }> = {
  live: { label: 'Live workflow', detail: 'Uses supplied candidate evidence' },
};
