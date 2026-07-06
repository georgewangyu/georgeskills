---
name: frontend-e2e-evaluator-ops
description: Evaluate a frontend with end-to-end checks that combine real user journeys, clickable-control validation, visual screenshots, responsive fit, source/link integrity, and production-preview confidence. Use when a page or app appears functional but may have fake controls, broken navigation, clipped text, invalid links, layout regressions, or browser-specific issues before launch.
memory_tags:
  - domain:frontend-design
  - workflow:e2e-evaluation
  - skill_role:evaluator
  - repo_boundary:tools
  - inputs:running-frontend
  - outputs:launch-readiness-report
  - risk:medium
---

# Frontend E2E Evaluator Ops

## Purpose

Catch the failures that shallow smoke tests miss: UI that looks clickable but is inert, links that point to prose instead of URLs, text that clips in realistic viewports, visual hierarchy that violates the design language, and previews that differ from local assumptions.

## Workflow

1. Establish the intended experience.
   - Identify the primary user journeys, conversion action, and pages that must work.
   - Read the local design notes or surrounding UI patterns before judging visual quality.
   - State the design language in one sentence so the evaluation has a target.

2. Run functional journeys in a real browser.
   - Prefer Playwright or an equivalent browser automation tool.
   - Cover at least desktop and mobile; include Firefox when the user asks for it or when CSS/layout behavior matters.
   - Test the actual actions a user would try: navigation links, filters, forms, copy buttons, modals, downloads, and external links.
   - Assert state changes, URL changes, button pressed/disabled states, success/error messages, and submitted payload shape when applicable.

3. Detect fake affordances.
   - Inspect controls that look interactive: chips, pills, cards, table rows, icon buttons, headings with hover styling, and CTA-like text.
   - Verify each one is either a semantic interactive element (`button`, `a`, form control) or visually demoted so users do not expect interaction.
   - Add regression tests for any fake-control fix.

4. Check content fit and source integrity.
   - Measure horizontal overflow at realistic desktop and mobile viewports.
   - Check repeated cards, sidebars, tables, panels, and long links for clipping, overlap, or unreadable truncation.
   - Verify `href` values are real URLs or internal routes, not labels such as product names, source descriptions, or `N/A`.
   - Prefer readable link labels with valid URLs over raw unbounded URLs.

5. Take screenshots and inspect them.
   - Capture screenshots at the viewport where the issue was reported, plus one mobile viewport.
   - Do a visual pass for hierarchy, density, alignment, first-screen composition, and whether any section feels generic or overproduced.
   - If a page has a design system or design language, compare the screenshot against it explicitly.

6. Harden the tests.
   - Convert every confirmed bug into a regression check.
   - Add semantic assertions for clickability and state, not only text visibility.
   - Add layout assertions sparingly for failure modes that already happened, such as no horizontal overflow or maximum heading size.
   - Avoid brittle pixel-perfect tests unless the component is fixed-format and layout-critical.

7. Verify deploy confidence.
   - Run typecheck, production build, and the relevant end-to-end test suite before deployment.
   - After preview deployment, use the preview URL for a final browser pass when possible.
   - For production promotion, confirm the production deploy reports `READY` and note the canonical production URL.

## Output Contract

Return:

- `Verdict`: launch-ready, launch-ready with caveats, or blocked.
- `Design target`: one sentence naming the intended design language.
- `Findings`: prioritized bugs or polish issues with page/selector/file pointers when available.
- `Fixes made`: concise list of changes, if the evaluator also implemented them.
- `Regression coverage`: tests added or updated.
- `Verification`: commands run, browsers/viewports checked, screenshot paths if useful, and deploy URLs.
- `Residual risk`: anything not tested, intentionally deferred, or dependent on external services.

## Common Regression Checks

Use these patterns when they match the bug class:

```ts
await expect(page.locator(".rail .chip")).toHaveCount(0);
await expect(page.getByRole("button", { name: "Repos" })).toHaveAttribute("aria-pressed", "true");
expect(await page.locator('a[href^="N/A"], a[href^="Product Hunt"]').count()).toBe(0);
expect(document.documentElement.scrollWidth).toBeLessThanOrEqual(window.innerWidth);
expect(parseFloat(getComputedStyle(heading).fontSize)).toBeLessThanOrEqual(58);
```

Adapt selectors to the app. The point is to test the user-visible failure mode, not copy these selectors literally.
