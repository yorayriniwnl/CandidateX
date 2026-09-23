# CandidateX Frontend Motion Polish Implementation Plan

> **For agentic workers:** Use the superpowers:executing-plans skill to implement this plan task by task.

**Goal:** Add smooth, restrained motion to the CandidateX landing page and live analysis journey while preserving the current content, evidence semantics, and workflows.

**Architecture:** Keep server-rendered pages server-rendered and use the existing CSS Modules for short, one-shot entrance and interaction motion. Use Framer Motion's existing reduced-motion hook only in the `/research-demo` client page, where the library is already in use. Avoid continuous decorative loops and new dependencies.

**Tech Stack:** Next.js 16.3.5 App Router, React 19, CSS Modules, Framer Motion 13.4.0.

**Spec:** `docs/superpowers/specs/2026-09-23-candidatex-evidence-os.md`, with the user-requested motion brief: “Smooth and clean,” based on the existing `/`, `/analyze`, dossier, and `/research-demo` experience.

## Global Constraints

- Keep backend code, CCI scoring, dossier values, and evidence semantics unchanged.
- Add no package dependencies and no motion that blocks or delays interaction.
- Animate only `opacity` and `transform` for the new entrance effects.
- Respect `prefers-reduced-motion`; render every section fully visible when motion is reduced.
- Keep animation one-shot and brief; do not introduce an always-running decorative loop.
- Preserve the existing EvidenceGraph3D render loop, WebGL fallback, and reduced-motion behavior.

## Review Focus

- Reduced-motion preference: content appears immediately and user-triggered transitions do not translate or scale the page.
- First paint before hydration: server-rendered content remains readable and visible.
- Small viewports: staggered elements do not change layout dimensions or cause horizontal overflow.
- Wizard step changes: each newly selected stage animates without delaying input or changing step state.
- Dossier and graph: the dossier still scrolls to the selected section and the graph fallback remains visible.

---

### Task 1: Honor reduced motion in the research demo's existing transitions

**Files:**
- Modify: `apps/web/app/research-demo/page.tsx`

**Interfaces:**
- The existing client page already imports Framer Motion; use its `useReducedMotion` hook without adding a new client boundary to the static routes.

- [x] Import and call `useReducedMotion` at the top level of `ResearchDemonstration`.
- [x] Use the hook to skip entrance and exit motion when the preference is enabled.
- [x] Keep `app/layout.tsx` a Server Component and leave its static home/analyze route bundle without Framer Motion code.
- [x] Keep the existing global CSS reduced-motion rules; they govern CSS-based motion on `/` and `/analyze`.


### Task 2: Give the landing page a restrained entrance sequence

**Files:**
- Modify: `apps/web/app/landing.module.css`

**Interfaces:**
- Use the existing `heroCopy`, `flow`, `flowNode`, `connector`, `graphGlyph`, and action classes; no markup or route behavior changes are needed.

- [x] Add short ease-out entrances; keep landing copy and actions visible while they rise, and limit text staggering to 90 ms.
- [x] Stagger the evidence-flow illustration with brief, one-shot delays.
- [x] Animate the connector once with a horizontal scale and give the evidence nodes a small one-shot fade/translate entrance.
- [x] Refine action hover and pressed transitions while preserving the existing focus outlines.
- [x] Add a reduced-motion override that disables all new transforms and animations while leaving content visible.
- [x] Add no looping float, pulse, parallax, autoplay, or layout animation.

### Task 3: Smooth the live analysis and dossier transitions

**Files:**
- Modify: `apps/web/components/evidence-os/evidence-os.module.css`

**Interfaces:**
- Use the existing `pageHeading`, `stepPanel`, `dossierShell`, `dossierContent`, `sectionNav`, and button classes; leave the React step state and section navigation functions unchanged.

- [x] Give the initial analysis heading a short fade-and-rise entrance.
- [x] Animate a newly mounted wizard `stepPanel` with a brief opacity/translate transition so stage changes feel connected.
- [x] Fade the dossier into place after an analysis completes and lightly stagger its existing content blocks.
- [x] Add restrained hover/focus feedback to dossier section links and buttons using transform/opacity only.
- [x] Preserve the existing `scrollIntoView` reduced-motion branch and all CSS fallbacks for the WebGL graph.
- [x] Add reduced-motion overrides that remove movement and reveal all content immediately.

### Task 4: Unify the research demo's existing result motion

**Files:**
- Modify: `apps/web/app/research-demo/page.tsx`

**Interfaces:**
- Keep the existing empty/result `AnimatePresence` state flow and result refs; only set explicit short transitions so this page shares the new timing and route-local reduced-motion policy.

- [x] Set matching ease-out transitions on the current empty and result panel entrance/exit animations.
- [x] Keep the existing result scroll behavior, input state, request lifecycle, and graph rendering unchanged.

### Task 5: Review and commit the motion pass

**Files:**
- Review: `apps/web/app/page.tsx`, `apps/web/app/analyze/page.tsx`, `apps/web/app/research-demo/page.tsx`, and the touched CSS/TSX files.

- [ ] Review the landing page and analysis wizard at desktop and mobile sizes with normal motion and reduced motion enabled. The local preview is live, but the browser-control service could not load its request-header policy during this review.
- [ ] Confirm no new always-running animation, hidden content, layout shift, or horizontal overflow is introduced.
- [x] Run `pnpm --filter web typecheck`, `pnpm --filter web build`, and `git diff --check`.
- [x] Commit the plan and implementation together with a scoped message, then push `codex/candidatex-evidence-os` to `origin` so the existing PR updates.

## Research Notes

- Motion's React documentation supports coordinated enter/exit transitions and a reduced-motion hook for local policy: [Motion accessibility](https://motion.dev/docs/react-accessibility), [useReducedMotion](https://motion.dev/docs/react-use-reduced-motion).
- Browser-friendly movement should prefer `transform` and `opacity`; avoid animating layout and paint-heavy properties: [web.dev animation guide](https://web.dev/articles/animations-guide).
- WCAG guidance calls for controls for continuous automatic movement and recommends respecting reduced-motion preferences for nonessential interaction animation: [W3C Pause, Stop, Hide](https://www.w3.org/WAI/WCAG22/Understanding/pause-stop-hide), [W3C Animation from Interactions](https://www.w3.org/WAI/WCAG21/Understanding/animation-from-interactions).
