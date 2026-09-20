# Signal Observatory Experience Design

## Status

Approved in conversation on 2026-09-21. This document defines the visual and information-architecture rebuild for the CandidateX web frontend.

## Goal

Give CandidateX one coherent, high-impact frontend that makes every existing surface understandable from a new homepage, while preserving the live analysis, workspace, hiring, and research functionality already present in the app.

## User outcome

A first-time visitor should immediately understand that CandidateX is a research-informed technical hiring decision-support system. From the root route they should be able to choose the correct mode without guessing what a page is for:

- **Live Evidence** (`/analyze`) is for uploading a real resume and reviewing supplied public evidence.
- **Evaluation Workspace** (`/workspace`) is for the internal candidate directory, pipeline, dossier, comparison, and methodology tools.
- **Hiring View** (`/hr`) is a lighter candidate-review surface for hiring teams and is explicitly presented as a sample workspace when no live data is available.
- **Research Lab** (`/research-demo`) is an interactive synthetic demonstration of the scoring and interview-probe mechanisms.

## Design direction

The product is presented as a “Signal Observatory”: a dark, editorial command center where evidence is traced into interview decisions. The canvas is near-black rather than flat black, with a low-contrast grid, sparse noise, and slow ambient aurora. Violet is the primary intelligence accent; cyan marks sources and flow; acid-lime marks verified/healthy states; amber and rose remain reserved for uncertainty and conflicts.

The interface should feel cinematic on first contact but disciplined once a user starts a workflow. Large typography, asymmetric composition, luminous borders, and deliberate motion create the wow factor. Every decorative effect has a static fallback and must not compromise text contrast, keyboard access, or mobile layout.

## Scope

### In scope

1. Replace the root redirect with a purpose-built homepage that navigates to all four product surfaces.
2. Add one reusable application header for public-facing routes: brand, surface label, route navigation, live-analysis CTA, and a mobile menu.
3. Normalize route labels, headings, metadata, CTA copy, status labels, and explanatory notices so the surfaces no longer read like unrelated products.
4. Refresh the global visual tokens, background treatment, focus states, cards, buttons, and responsive spacing to support the Signal Observatory direction.
5. Give the workspace and hiring surfaces explicit context and easy escape routes back to the command center.
6. Add automated route/navigation coverage plus responsive overflow checks for the new shell and homepage.
7. Keep all existing data contracts, API calls, forms, dossier logic, research calculations, and export behavior intact.

### Out of scope

- Replacing the live-analysis or research backends.
- Changing scoring math, evidence semantics, security constraints, or hiring governance language.
- Adding authentication, persistence, billing, or new external integrations.
- Removing any existing route or workflow.
- Introducing a new UI framework or a new runtime dependency.

## Information architecture

### Global navigation

Public-facing pages use a shared top bar with:

- a clickable CandidateX mark linking to `/`;
- a compact surface label, such as “Live Evidence” or “Research Lab”;
- links to Home, Live Evidence, Workspace, Hiring View, and Research Lab;
- a high-emphasis “Start an analysis” action linking to `/analyze`;
- a small status chip explaining whether the page is Live, Sample, or Synthetic;
- a keyboard-accessible mobile menu below the compact breakpoint.

The workspace keeps its dense left navigation because it is an application-within-the-application. Its top/brand region must use the same mark, colors, type scale, and destination names, and must include a clear link back to `/`. The workspace content should not be wrapped in a second full-height public header that reduces usable space.

### Homepage structure

The homepage is a full-width command center with the following order:

1. **Hero / signal statement** — brand eyebrow, large headline explaining the product, concise governance-aware description, and primary/secondary CTAs.
2. **Signal constellation** — a decorative but semantic-free visual showing Candidate → Evidence → Capability → Interview; the same information is repeated in accessible text beside it.
3. **Mode selector** — four route cards with distinct accent colors, clear “what this is for” copy, and one CTA each. Live Evidence is the featured card.
4. **Operating loop** — three or four steps showing upload/context, trace evidence, and prepare the conversation; link the final step back to Live Evidence.
5. **Trust strip** — short statements for “human decision support”, “missing evidence stays unknown”, and “candidate code is never executed”.
6. **Footer** — compact navigation, limitation language, and a return-to-home affordance.

### Route framing

Each public-facing route receives a short page framing treatment near the top, using the shared surface label and a one-line purpose statement. The existing feature-rich body stays in place, but the initial viewport must answer “what is this page?” before asking the user to interact.

## Component architecture

### Shared components

Create a focused navigation module under `apps/web/components/navigation/`:

- `PlatformHeader.tsx` — client component using the current pathname to mark the active destination, manage the mobile menu, and expose the shared navigation links.
- `SurfaceBadge.tsx` — small presentational status badge for Live, Sample, and Synthetic contexts.

Create a focused home module under `apps/web/components/home/`:

- `SignalConstellation.tsx` — decorative signal-flow visual with accessible hidden labels and responsive layout.
- `ExperienceCard.tsx` — typed destination card with icon, route, purpose, accent, and CTA.

Keep homepage composition in `apps/web/app/page.tsx` and style-only homepage rules in `apps/web/app/home.module.css`. Avoid pushing backend or page-specific state into shared components.

### Shared shell contract

`PlatformHeader` accepts:

```ts
type Surface = 'home' | 'live' | 'workspace' | 'hiring' | 'research';
type PlatformHeaderProps = {
  surface: Surface;
  status?: 'live' | 'sample' | 'synthetic';
};
```

It renders valid links for every destination, uses `aria-current="page"` on the active link, labels the mobile toggle, closes the menu after navigation, and preserves visible focus rings.

### Route integration

- `/analyze`: replace its bespoke top navigation with `PlatformHeader surface="live" status="live"`; preserve the upload, review, analysis, export, and evidence-inspector states.
- `/research-demo`: replace its bespoke top navigation with `PlatformHeader surface="research" status="synthetic"`; preserve all existing test IDs and interactions.
- `/hr`: use `PlatformHeader surface="hiring" status="sample"` and keep `HRDashboard` unchanged except for any copy needed to make the sample state clear.
- `/workspace`: keep its local tab/sidebar behavior, but update its brand region and top command bar to match the shared destination names and add an explicit link back to `/`. Add responsive rules so the sidebar does not force horizontal scrolling on narrow viewports.
- `/`: render the new homepage and do not redirect.

## Visual system

### Tokens

Extend the existing CSS token layer rather than introducing a second styling system. Add named tokens for:

- ink/background levels;
- violet intelligence accent;
- cyan source accent;
- lime verified accent;
- amber uncertainty accent;
- rose conflict accent;
- text hierarchy and focus ring;
- grid/noise/aurora opacity.

Use semantic classes for the new surfaces and keep existing utility class names working for legacy components.

### Typography

Keep the loaded Inter and JetBrains Mono fonts. Use the display scale sparingly: one strong homepage headline, compact uppercase mono eyebrows, and clear page-level headings. Avoid all-caps paragraphs or long monospace blocks outside data/provenance contexts.

### Motion

Use CSS and existing Framer Motion primitives only. Motion should include route/card reveal, hover lift, signal pulse, and mobile menu transitions. Honor `prefers-reduced-motion: reduce` by disabling non-essential animation and leaving all content visible.

## Data, errors, and states

- Homepage navigation is static and must work when the backend is unavailable.
- Route status badges are explanatory labels, not live health checks. Do not imply that the page has verified a backend unless it actually does.
- Existing backend error messages and empty states remain visible. Restyle them for the new tokens rather than hiding them.
- The homepage must not fabricate candidates, scores, or research results. It may show static illustrative labels only when they are clearly decorative or described as examples.
- The existing governance copy remains visible on the workspace, live-analysis, and research surfaces, with shorter versions on the homepage.

## Accessibility and responsive behavior

- Every navigation item is a real link or an intentional button; no click-only `div`s.
- Active destinations expose `aria-current="page"`.
- Mobile navigation is keyboard reachable, has an accessible name, closes on selection, and does not trap focus.
- Decorative canvas elements are `aria-hidden="true"`; the accessible copy explains the same product flow.
- Interactive cards have visible focus and hover states, with a minimum target size of 44px where practical.
- At 390px viewport width, the homepage, public headers, live-analysis intake, research controls, hiring view, and workspace must not create horizontal overflow.
- Tables and evidence blocks may scroll within their own containers when content is intrinsically wide.

## Verification criteria

The implementation is ready when:

1. `/` loads the command-center homepage without redirecting and exposes links to all four destinations.
2. Every homepage destination card and header destination navigates to the intended route.
3. `/analyze`, `/hr`, and `/research-demo` show the shared public header with the correct surface/status label.
4. `/workspace` retains its working tab navigation and has a visible route back to `/` without horizontal overflow at 390px.
5. Existing live-analysis and research-demo Playwright behavior remains intact, including their test IDs and export flows.
6. TypeScript compilation and the full web test suite pass.
7. A browser smoke check confirms non-empty content, no framework error overlay, no console errors caused by this work, and usable key interactive elements on the homepage and at least one destination route.

## Decisions

- The existing route set remains; clarity comes from framing and navigation, not route deletion.
- The root route becomes a true homepage instead of silently entering the live-analysis flow.
- Live Evidence is the primary CTA because it is the product’s real user workflow; the other surfaces are clearly secondary modes.
- The visual system is bold and atmospheric, but the evidence and governance language remain precise and restrained.
