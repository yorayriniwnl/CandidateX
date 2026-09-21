export type Surface = 'home' | 'live';
export type SurfaceStatus = 'live';

export const NAVIGATION_ITEMS = [
  { key: 'home', label: 'Home', href: '/', shortLabel: 'Home' },
  { key: 'live', label: 'Live Evidence', href: '/analyze', shortLabel: 'Live' },
] as const;

export type NavigationItem = (typeof NAVIGATION_ITEMS)[number];

export const SURFACE_COPY: Record<Surface, { label: string; descriptor: string }> = {
  home: { label: 'Command center', descriptor: 'Candidate capability intelligence' },
  live: { label: 'Live Evidence', descriptor: 'Resume to interview' },
};

export const STATUS_COPY: Record<SurfaceStatus, { label: string; detail: string }> = {
  live: { label: 'Live workflow', detail: 'Uses supplied candidate evidence' },
};
