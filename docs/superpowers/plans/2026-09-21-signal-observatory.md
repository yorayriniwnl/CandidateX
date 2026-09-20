# Signal Observatory Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the root redirect with a cinematic command center, add a reusable route-aware public header, and normalize all existing CandidateX surfaces into one clear responsive visual system.

**Architecture:** Keep the existing Next.js App Router routes and all feature/data logic. Add a small client-side navigation layer for route awareness and mobile menu state, compose the homepage from typed static destination data, and integrate the same header into the public-facing routes while preserving the dense workspace sidebar. Extend the existing CSS token layer instead of adding a styling dependency.

**Tech Stack:** Next.js 16 App Router, React 19, TypeScript, Tailwind CSS, CSS Modules, Framer Motion, lucide-react, Playwright.

**Spec:** `docs/superpowers/specs/2026-09-21-signal-observatory-design.md`

## Global Constraints

- The existing route set remains; clarity comes from framing and navigation, not route deletion.
- The root route becomes a true homepage instead of silently entering the live-analysis flow.
- Live Evidence is the primary CTA because it is the product’s real user workflow; the other surfaces are clearly secondary modes.
- The visual system is bold and atmospheric, but the evidence and governance language remain precise and restrained.
- Keep all existing data contracts, API calls, forms, dossier logic, research calculations, and export behavior intact.
- Do not add a new UI framework or runtime dependency.
- At 390px viewport width, the homepage, public headers, live-analysis intake, research controls, hiring view, and workspace must not create horizontal overflow.
- This source snapshot has no `.git` directory; use file/diff inspections and the ledger as checkpoints instead of commits.

## Review Focus

- A user lands on `/` while the backend is unavailable: the command center must still render static navigation and never block on health checks.
- A user opens the public header on a 390px viewport: the menu must be reachable, close after a selection, and keep the document within the viewport.
- A user opens `/workspace` on a narrow viewport: the dense local navigation must not create permanent horizontal overflow or hide the return-home route.
- A user visits `/research-demo`: synthetic context must remain explicit and existing test IDs/interactions must still work.
- A user visits `/hr`: the page must be clearly identified as a sample hiring view, not presented as live candidate data.

---

### Task 1: Add the shared route model and public header

**Files:**
- Create: `apps/web/components/navigation/navigation.ts`
- Create: `apps/web/components/navigation/SurfaceBadge.tsx`
- Create: `apps/web/components/navigation/PlatformHeader.tsx`
- Test: `apps/web/tests/homepage.spec.ts`

**Interfaces:**
- Produces `Surface`, `SurfaceStatus`, `NAVIGATION_ITEMS`, and `PlatformHeaderProps` for the homepage and existing route integrations.
- `PlatformHeader` renders a real link for each destination, `aria-current="page"` for the active destination, an accessible mobile menu toggle, and a primary link to `/analyze`.

- [ ] **Step 1: Write the failing route/header tests**

Add `apps/web/tests/homepage.spec.ts` with these behaviors before creating the production components:

```ts
import { test, expect } from '@playwright/test';

test('the root route is a command center for every product surface', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole('heading', { name: /candidate intelligence/i })).toBeVisible();

  for (const destination of [
    ['Live Evidence', '/analyze'],
    ['Evaluation Workspace', '/workspace'],
    ['Hiring View', '/hr'],
    ['Research Lab', '/research-demo'],
  ] as const) {
    await expect(page.getByRole('link', { name: new RegExp(destination[0], 'i') }).first()).toHaveAttribute('href', destination[1]);
  }
});

test('the public header exposes active navigation and the analysis CTA', async ({ page }) => {
  await page.goto('/analyze');
  await expect(page.getByRole('link', { name: 'Home', exact: true })).toHaveAttribute('href', '/');
  await expect(page.getByRole('link', { name: 'Live Evidence', exact: true })).toHaveAttribute('aria-current', 'page');
  await expect(page.getByRole('link', { name: /Start an analysis/i }).first()).toHaveAttribute('href', '/analyze');
});
```

- [ ] **Step 2: Run the new tests and verify the intended red state**

Run from `apps/web` after ensuring a production build exists:

```powershell
pnpm build
pnpm exec playwright test tests/homepage.spec.ts
```

Expected: the first test fails because `/` still redirects to `/analyze`, and the second test fails because the shared header does not exist.

- [ ] **Step 3: Implement the route model and surface badge**

Create `navigation.ts` with the exact route model used by every new navigation surface:

```ts
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
```

Implement `SurfaceBadge` as a small semantic `span` that uses the status label and detail in an accessible tooltip-style `title` attribute. It must not imply backend health.

- [ ] **Step 4: Implement `PlatformHeader`**

`PlatformHeader` must use `usePathname`, `useState`, and `useEffect` only for menu state. It should render the CandidateX mark, surface descriptor, desktop navigation, status badge, analysis CTA, and a mobile menu button with `aria-expanded`, `aria-controls="platform-navigation"`, and `aria-label="Toggle navigation"`. Close the mobile menu in a `useEffect` whenever `pathname` changes.

Use `Link` for all route navigation. The active item matches the current pathname exactly for `/` and by prefix for non-root routes. Apply `aria-current="page"` only to the active link.

- [ ] **Step 5: Run the targeted tests and confirm green**

Run:

```powershell
pnpm build
pnpm exec playwright test tests/homepage.spec.ts
```

Expected: the suite still fails only because the root page and public routes have not yet been integrated with the header; the production code should typecheck and render the new header when imported.

Checkpoint: record the test output and changed-file inventory in the ledger. No commit is possible because the snapshot has no Git metadata.

### Task 2: Build the command-center homepage and Signal Observatory visual system

**Files:**
- Modify: `apps/web/app/page.tsx`
- Create: `apps/web/app/home.module.css`
- Create: `apps/web/components/home/SignalConstellation.tsx`
- Create: `apps/web/components/home/ExperienceCard.tsx`
- Modify: `apps/web/app/globals.css`
- Modify: `apps/web/app/layout.tsx`
- Test: `apps/web/tests/homepage.spec.ts`

**Interfaces:**
- Consumes `NAVIGATION_ITEMS`, `SURFACE_COPY`, and `PlatformHeader` from Task 1.
- Produces a static, backend-independent homepage with four typed destination cards and a semantic fallback for the decorative constellation.

- [ ] **Step 1: Extend the failing homepage test for content, mobile behavior, and accessible flow**

Append to `apps/web/tests/homepage.spec.ts`:

```ts
test('the command center stays usable on mobile and explains the operating loop', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  await expect(page.getByText(/bring context/i)).toBeVisible();
  await expect(page.getByText(/trace the signal/i)).toBeVisible();
  await expect(page.getByText(/prepare the conversation/i)).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);

  const menu = page.getByRole('button', { name: /toggle navigation/i });
  await expect(menu).toHaveAttribute('aria-expanded', 'false');
  await menu.click();
  await expect(menu).toHaveAttribute('aria-expanded', 'true');
  await page.getByRole('link', { name: 'Research Lab', exact: true }).last().click();
  await expect(page).toHaveURL(/\/research-demo$/);
});
```

- [ ] **Step 2: Run the new test and verify the red state**

Run:

```powershell
pnpm build
pnpm exec playwright test tests/homepage.spec.ts
```

Expected: the new test fails because the current root route has no command-center operating loop, cards, mobile menu, or constellation.

- [ ] **Step 3: Implement the homepage data and composition**

Create `ExperienceCard` with typed props for `title`, `eyebrow`, `description`, `href`, `icon`, `accent`, `tag`, and `featured`. The card must be a full-card link with a visible arrow, focus ring, and `data-testid="experience-card-<key>"`.

Create `SignalConstellation` using a responsive `<div>` structure with four labeled nodes and connecting lines. Mark the visual wrapper `aria-hidden="true"` and render a visually-hidden text equivalent: “Candidate claims move through public evidence into capabilities and focused interview questions.” Do not use canvas, external images, or fabricated score values.

Replace the redirect-only `apps/web/app/page.tsx` with:

- `PlatformHeader surface="home"`;
- hero eyebrow “Candidate Capability Intelligence”;
- headline containing “Candidate intelligence, with receipts.”;
- description that states the product supports human interviewers and does not make autonomous hiring decisions;
- primary link “Start with live evidence” to `/analyze`;
- secondary link “Explore the method” to `/research-demo`;
- constellation block;
- four experience cards in order Live Evidence, Evaluation Workspace, Hiring View, Research Lab;
- three operating-loop items with the exact phrases “Bring context”, “Trace the signal”, and “Prepare the conversation”;
- three trust statements for human decision support, missing evidence remaining unknown, and static candidate-code analysis;
- concise footer links and limitation text.

The page must never fetch health or candidate data.

- [ ] **Step 4: Add the shared visual treatment**

Extend `globals.css` with named tokens and utilities for the ink levels, intelligence violet, source cyan, verified lime, uncertainty amber, conflict rose, focus ring, aurora opacity, grid background, and noise fallback. Add reduced-motion rules for the new pulse/float classes.

Create `home.module.css` for the homepage composition: fluid container, asymmetric hero, responsive constellation, featured card gradient, card hover/focus glow, loop timeline, trust strip, and mobile stacking. Keep contrast readable over the background and avoid fixed widths that exceed 390px.

Update `layout.tsx` metadata description to describe the four product modes and keep the dark color scheme. Add a `noise-texture` class to the body if the texture remains purely decorative.

- [ ] **Step 5: Run the homepage tests and typecheck**

Run:

```powershell
pnpm build
pnpm exec playwright test tests/homepage.spec.ts
pnpm lint
```

Expected: all homepage tests pass, the production build exits 0, and TypeScript reports no errors.

Checkpoint: record the output and changed-file inventory in the ledger.

### Task 3: Normalize the public route headers and route framing

**Files:**
- Modify: `apps/web/app/analyze/page.tsx`
- Modify: `apps/web/app/analyze/shared.module.css`
- Modify: `apps/web/app/research-demo/page.tsx`
- Modify: `apps/web/app/hr/page.tsx`
- Modify: `apps/web/components/hr/HRDashboard.tsx`
- Modify: `apps/web/tests/homepage.spec.ts`

**Interfaces:**
- Consumes the shared `PlatformHeader` and `SurfaceBadge` contract from Task 1.
- Preserves all existing live-analysis and research-demo element IDs, labels used by Playwright, API calls, state machines, and export behavior.

- [ ] **Step 1: Add failing route-framing assertions**

Append to `apps/web/tests/homepage.spec.ts`:

```ts
test('public routes state what they are and keep a path back to the command center', async ({ page }) => {
  const routes = [
    ['/analyze', /Live Evidence/i, /Live workflow/i],
    ['/research-demo', /Research Lab/i, /Synthetic only/i],
    ['/hr', /Hiring View/i, /Sample workspace/i],
  ] as const;

  for (const [route, surface, status] of routes) {
    await page.goto(route);
    await expect(page.getByRole('link', { name: 'Home', exact: true })).toHaveAttribute('href', '/');
    await expect(page.getByText(surface).first()).toBeVisible();
    await expect(page.getByText(status).first()).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  }
});
```

- [ ] **Step 2: Run the route tests and observe the red state**

Run:

```powershell
pnpm build
pnpm exec playwright test tests/homepage.spec.ts
```

Expected: route framing assertions fail because each route currently has a different header and status vocabulary.

- [ ] **Step 3: Integrate `PlatformHeader` into live analysis**

In `apps/web/app/analyze/page.tsx`, replace the bespoke `<nav>` with `<PlatformHeader surface="live" status="live" />`. Keep the existing page content and labels used by upload/error/evidence tests. Add a small route-framing intro only if it does not duplicate the existing hero; the initial hero must name “Live Evidence” and keep the resume → public evidence → technical interview concept.

Update `shared.module.css` so the page container has the same grid/noise background and focus treatment as the homepage while retaining the existing form layout.

- [ ] **Step 4: Integrate `PlatformHeader` into Research Lab**

In `apps/web/app/research-demo/page.tsx`, replace the custom top nav with `<PlatformHeader surface="research" status="synthetic" />`. Preserve the existing research links by moving “The method” and “Experiments” into the page body if they are currently header anchors. Keep the existing heading “From evidence to interview.” and every existing `data-testid` / accessible label.

- [ ] **Step 5: Integrate `PlatformHeader` into Hiring View**

In `apps/web/app/hr/page.tsx`, replace the two-link top bar with `<PlatformHeader surface="hiring" status="sample" />`. Add a short notice near the HR dashboard title that says “Sample review surface — local drafts stay separate from live evidence.” without changing the dashboard’s candidate behavior.

- [ ] **Step 6: Run public route regression coverage**

Run:

```powershell
pnpm build
pnpm exec playwright test tests/homepage.spec.ts tests/research-demo.spec.ts tests/live-analysis.spec.ts
pnpm lint
```

Expected: route framing and the pre-existing research/live behavior pass, with no TypeScript errors or changed export behavior.

Checkpoint: record the output and changed-file inventory in the ledger.

### Task 4: Bring the dense workspace into the same system and fix narrow layouts

**Files:**
- Modify: `apps/web/app/workspace/page.tsx`
- Modify: `apps/web/app/globals.css`
- Modify: `apps/web/tests/homepage.spec.ts`

**Interfaces:**
- Consumes the shared navigation route model from Task 1 but keeps the existing local tab navigation and backend state.
- Produces a workspace with a visible return-home link, consistent brand/status copy, and no permanent horizontal overflow at 390px.

- [ ] **Step 1: Add failing workspace assertions**

Append to `apps/web/tests/homepage.spec.ts`:

```ts
test('workspace keeps its dense tools but provides a shared escape route on mobile', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/workspace');
  await expect(page.getByRole('link', { name: /CandidateX/i }).first()).toHaveAttribute('href', '/');
  await expect(page.getByText(/Evaluation Workspace/i).first()).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});
```

- [ ] **Step 2: Run the workspace test and observe the red state**

Run:

```powershell
pnpm build
pnpm exec playwright test tests/homepage.spec.ts
```

Expected: the assertion fails because the workspace brand is not a link to `/`, the surface label is not “Evaluation Workspace”, or the fixed sidebar causes overflow.

- [ ] **Step 3: Update workspace brand and command bar**

Keep the existing candidate directory, evaluation wizard, dossier, comparison, research tab, health check, modal, and tab state intact. Change only the shell copy and links:

- make the CandidateX mark a `Link` to `/`;
- add “Evaluation Workspace” and “Directory · dossiers · comparison” to the brand region;
- add a small “Command center” link to `/` in the top command bar;
- keep “Research Lab” links pointing to `/research-demo`;
- keep the existing API status badge and governance notice.

Add `aria-current`-like styling to the active local tab without changing the tab button behavior.

- [ ] **Step 4: Add responsive workspace rules**

Add a stable class to the workspace root/sidebar/main elements and use CSS media queries below 860px to collapse the sidebar to a compact rail or transform it off-canvas, reduce main horizontal padding, and keep table/content overflow inside bounded containers. Preserve an accessible “Collapse” button and do not hide the only route navigation.

- [ ] **Step 5: Run the full existing web suite**

Run:

```powershell
pnpm build
pnpm exec playwright test
pnpm lint
```

Expected: the full existing suite plus the homepage suite pass with 0 test failures and 0 TypeScript errors.

Checkpoint: record the output and changed-file inventory in the ledger.

### Task 5: Perform visual/browser verification and final quality pass

**Files:**
- Modify: any source file required to fix a verified Critical or Important issue found during review.
- Test: `apps/web/tests/homepage.spec.ts` and the existing Playwright suite.

**Interfaces:**
- Consumes all route, shell, and visual contracts from Tasks 1–4.
- Produces the final evidence package: typecheck, build, tests, and browser smoke observations.

- [ ] **Step 1: Run a fresh production build and complete Playwright suite**

Run:

```powershell
pnpm build
pnpm exec playwright test
pnpm lint
```

Expected: all commands exit 0; read the complete summaries and record test counts.

- [ ] **Step 2: Run the browser smoke check**

With the production server running at `http://127.0.0.1:3108`, inspect `/`, `/analyze`, `/workspace`, `/hr`, and `/research-demo` using the available browser tooling. Confirm each page has meaningful content, no framework error overlay, no page-level console errors caused by the changes, and the homepage visual hierarchy is legible at desktop and 390px widths. The repository does not have the `agent-browser` CLI, so use the available in-app browser/Playwright surface and record that substitution.

- [ ] **Step 3: Apply one fix pass for verified Important issues**

For each verified functional or accessibility issue, add a focused Playwright assertion before the fix, run it to confirm red, apply the smallest fix, and rerun the focused test followed by the full suite. Do not change scoring or backend behavior.

- [ ] **Step 4: Final evidence and handoff**

Record in the ledger:

- the final build command and exit result;
- the final lint/typecheck result;
- the full Playwright test count and result;
- the browser smoke routes and observations;
- any deferred visual-only minor findings.

Because the source snapshot has no Git repository, report the final changed-file inventory and do not claim a commit or branch integration.
