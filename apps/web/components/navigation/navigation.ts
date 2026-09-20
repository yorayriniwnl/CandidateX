export type Surface = 'home' | 'live' | 'workspace' | 'hiring' | 'research';
export type SurfaceStatus = 'live' | 'sample' | 'synthetic';

export const NAVIGATION_ITEMS = [
  { key: 'home', label: 'Home', href: '/', shortLabel: 'Home' },
  { key: 'live', label: 'Live Evidence', href: '/analyze', shortLabel: 'Live' },
  { key: 'workspace', label: 'Workspace', href: '/workspace', shortLabel: 'Workspace' },
  { key: 'hiring', label: 'Hiring View', href: '/hr', shortLabel: 'Hiring' },
  { key: 'research', label: 'Research Lab', href: '/research-demo', shortLabel: 'Research' },
] as const;

export type NavigationItem = (typeof NAVIGATION_ITEMS)[number];

export const SURFACE_COPY: Record<Surface, { label: string; descriptor: string }> = {
  home: { label: 'Command center', descriptor: 'Candidate capability intelligence' },
  live: { label: 'Live Evidence', descriptor: 'Resume to interview' },
  workspace: { label: 'Evaluation Workspace', descriptor: 'Directory, dossiers, comparison' },
  hiring: { label: 'Hiring View', descriptor: 'Fast candidate review' },
  research: { label: 'Research Lab', descriptor: 'Synthetic scoring demonstration' },
};

export const STATUS_COPY: Record<SurfaceStatus, { label: string; detail: string }> = {
  live: { label: 'Live workflow', detail: 'Uses supplied candidate evidence' },
  sample: { label: 'Sample workspace', detail: 'Local review surface' },
  synthetic: { label: 'Synthetic only', detail: 'No real candidate is assessed' },
};
