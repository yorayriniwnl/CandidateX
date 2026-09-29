# Completed-result visual verification

The before/after captures show `/analyze` using actual CandidateX output from a bounded scan of `pallets/flask` (122 evidence records, 100 files inspected). The resume is synthetic. The declared account is a test input, not a verified association between the synthetic candidate and a real contributor. No dashboard values or engineering findings were hand-authored.

The original capture used a synthetic name header the parser could not recognize; the final scan uses the plain header `Alex Morgan`. All scores and observations in both runs came from the backend. The captured JSON is a local verification artifact, not a fixture shipped in the application.

## Captures

- [Before, wide report](before-1440.png)
- [Final desktop, 1440px](after-1440.png)
- [Final laptop, 1280px](after-1280.png)
- [Final small laptop, 1024px](after-1024.png)
- [Final mobile, 390px](after-390.png)
- [Capabilities](capabilities.png)
- [Claim verification](claims.png)
- [Repository intelligence](repository.png)
- [Evidence ledger](ledger.png)
- [Evidence inspector](inspector.png)
- [Interview plan](interview.png)

Final screenshots use the production build. The report was checked repeatedly in Chromium, including expanded claims, capabilities, repository signals, ledger filters, the evidence drawer, and the interview plan. The drawer preserves report scroll position, traps keyboard focus, closes with Escape, and restores the trigger's focus.

## Reproduce

Start the web application and run `node apps/web/visual-result.cjs` from the repository root. It loads `live-result.json` into the real intake/result UI through Playwright response replay. Set `VISUAL_BASE_URL` to choose another local web port (the final capture used port 3002).

The production build and TypeScript lint pass. All 28 browser tests pass. Browser regression coverage includes the existing real-API upload/export/rerun tests, lazy graph inspection, research-demo tests, and result-interaction, responsive, claim-consistency and detailed-review checks. For this machine's test environment, set `DEBUG=false` before running `pnpm --filter web test` because an inherited `DEBUG=release` value is not a valid backend boolean.

## Data limits preserved

This checkout's live response does not include a confidence summary, architecture topology, structured security review targets, or twelve engineering-practice families. The UI preserves unavailable/unknown states and displays the six signal families actually returned. Backend contracts and scoring were not changed. The graph remains available on demand. Detailed resume review now uses the same compact rows and typography as the rest of the report. It mounts on first expansion and retains skill filters across collapse/reopen.

## Detailed-review refinement

The second visual pass replaced the remaining legacy result cards, unified overview and claim-list counts, added direct job-requirement evidence inspection, and connected capability details to the filtered ledger. Mobile capability labels remain visible during horizontal scrolling.

- [Previous detailed review](resume-before.png)
- [Detailed review, 1440px](resume-review-1440.png)
- [Detailed review, 1280px](resume-review-1280.png)
- [Detailed review, 1024px](resume-review-1024.png)
- [Detailed review, 390px](resume-review-390.png)
- [Expanded skill, mobile](resume-skill-mobile.png)

Run `node apps/web/visual-resume.cjs` with the same `VISUAL_BASE_URL` setting to reproduce the detailed-review captures. These use the saved real scan response; no extra sources or scores were fabricated.

## Visual character refinement

The latest captures include a candidate monogram, a compact role-index dial, a segmented capability map with category icons, a highlighted sticky section navigation, richer graphite surfaces, and clearer status badges. Observations have stronger hover affordances; interview questions use a numbered margin; the evidence drawer has a short entrance transition that respects reduced motion. On mobile, the dial sits beside its explanation to keep the evidence summary close.

The dial uses only the returned role index. Unavailable scores remain explicitly unknown. Capability bars, counts, and semantic status colors retain the same underlying data. Capture scripts disable animation and wait for the active section indicator before saving section screenshots.
