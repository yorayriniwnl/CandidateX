# CandidateX homepage redesign

The homepage now centers on an interactive, procedural Three.js sculpture: articulated titanium rings, a refractive glass core, animated energy, and evidence streams. Studio reflections are generated locally, with no downloaded 3D assets or texture requests.

The page includes a revised hero, four selectable engine stages, a keyboard-accessible claim → artifact → interview example, product principles, and a closing invitation. Creator and supervisor credits are retained in the footer.

## Preview

- Development: http://127.0.0.1:3000
- Production preview started for this review: http://127.0.0.1:3109
- `hero-1440.png` and `hero-390.png`: opening screens.
- `home-1440.png`, `home-1024.png`, `home-390.png`, `home-320.png`: complete pages.
- `source-example.png` and `interview-example.png`: interactive demonstration states.
- `home-motion.webm`: recorded animation and stage selection.
- `reduced-motion.png`: still composition.
- `before/`: original homepage source files saved before editing.

## Validation

- `pnpm --filter web build`: passed, including TypeScript and static page generation.
- `pnpm --filter web test:home`: 7 tests passed.
- `node apps/web/visual-home-redesign.cjs`: four viewport captures, no horizontal overflow or browser errors. Full report in `visual-report.json`.

Checks cover animation, pause/resume without drift, reduced-motion preference changes, stage selection while paused, keyboard navigation, mobile navigation, missing WebGL, and context loss.

The scene loads on intersection, suspends when offscreen or in a hidden tab, caps pixel density, and lowers render resolution after sustained slow frames. Mobile animation is capped at 30 fps; desktop uses a 60 fps scheduling target. These are rendering policies, not device-independent frame-rate guarantees. A static SVG keeps the illustration available without WebGL.
