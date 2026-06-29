---
name: website-github-issue-form-ops
description: >-
  Add or retrofit a GitHub-backed request, contribution, feedback, or audience
  intake form near the bottom of a website. Use when a site needs a public or
  private issue-submission form, when existing radar/catalog sites lack the
  standard bottom-page request form, or when GitHub issue routing, labels,
  server-side tokens, environment variables, and verification need to be wired
  consistently.
metadata:
  memory_tags:
    - domain:frontend
    - workflow:github-issue-intake
    - inputs:website
    - outputs:code-change
    - risk:medium
    - repo_boundary:tools
---

# Website GitHub Issue Form Ops

## Overview

Use this skill to add a production-safe website form that turns visitor input into a GitHub issue. The default placement is near the bottom of the main page, after the primary content and before the footer, so the site remains useful before asking for contributions.

## Fit Check

Use this pattern when the request is one of:
- "add a GitHub issue form"
- "add a request/contribution/audience form"
- "put the form at the bottom of the page"
- "make public/private submissions create GitHub issues"
- "standardize intake across radar/catalog/resource sites"

If the site already has an intake form, inspect the existing implementation first and adapt it instead of adding a second form.

## Workflow

1. Read local instructions first:
   - nearest `AGENTS.md` or repo-specific agent instructions
   - `README.md` for deployment and env conventions
   - existing `.env.example`
   - existing issue helpers or API routes matching `github`, `issue`, `request`, `submission`, `contact`, or `feedback`
2. Identify the frontend stack and route surface:
   - Next.js App Router: prefer `app/api/<intake>/route.ts` for server issue creation.
   - Next.js Pages Router: prefer `pages/api/<intake>.ts`.
   - Serverless or backend apps: add the server endpoint in the existing backend pattern.
   - Static-only sites: do not put GitHub tokens in client code; add a backend/serverless function or stop with an implementation plan.
3. Define the intake contract:
   - request type: `submit`, `request`, `improve`, or site-specific equivalents
   - visibility: `public` or `private` when supported
   - title/name
   - description, outcome, or "why this matters"
   - optional handle/contact
   - optional link/context
4. Implement validation with the repo's existing schema tool. Prefer existing Zod/Yup/schema patterns. Keep client and server validation aligned.
5. Implement server-only GitHub issue creation:
   - read `GITHUB_TOKEN`, `GITHUB_OWNER`, `GITHUB_REPO`, and optional `GITHUB_PRIVATE_REPO` from server env
   - choose the private repo only when the submitted visibility is private
   - never expose tokens through `NEXT_PUBLIC_*`, client props, bundled JSON, or browser logs
   - send issues to `https://api.github.com/repos/{owner}/{repo}/issues`
6. Add source tagging:
   - include a source app/repo name in the issue title or body
   - add labels for source, request type, triage status, and visibility when the target repo supports labels
   - if workspace instructions define shared intake repos or label conventions, follow those local instructions rather than hardcoding user-specific destinations in the skill
7. Add the form UI near the bottom of the page:
   - place after the primary catalog/content/detail sections and before the footer
   - use the existing design system and form controls
   - include loading, success, validation-error, and server-error states
   - keep the copy short and specific to the site
   - do not add a marketing hero just to explain the form
8. Update docs:
   - `.env.example` with server-side env names
   - `README.md` with routing behavior, required GitHub token permissions, and local testing notes
   - mention that private submissions require an existing private issue target with token access
9. Verify:
   - run typecheck/lint/build/test commands listed in the repo docs
   - manually confirm the form is reachable near the bottom of the page
   - confirm env variables are server-only
   - if credentials are available and safe to use, submit one test issue and close/delete it only if the user asks

## Issue Helper Shape

Prefer a small helper such as `lib/github-issue.ts`:

```ts
export function issueTitle(input: Submission) {
  return `[source:${input.type}] ${compactTitle(input.title)}`;
}

export function issueLabels(input: Submission) {
  return [
    "status:needs-triage",
    `type:${input.type}`,
    `visibility:${input.visibility}`,
    `source-repo:${sourceRepo}`,
  ];
}

export async function createGitHubIssue(input: Submission) {
  const token = process.env.GITHUB_TOKEN;
  const owner = process.env.GITHUB_OWNER;
  const repo =
    input.visibility === "private"
      ? process.env.GITHUB_PRIVATE_REPO
      : process.env.GITHUB_REPO;

  if (!token || !owner || !repo) {
    throw new Error("Missing GitHub issue environment configuration.");
  }

  // POST to GitHub from the server route only.
}
```

Adapt names and labels to the repository. Do not copy this snippet blindly if the repo already has a stronger local helper pattern.

## UI Defaults

- Use a compact section title like "Request an addition", "Submit a resource", or "Improve this catalog".
- Use radio/segmented controls for request type and visibility.
- Use text inputs for title, handle, and link/context.
- Use textarea controls for description, why it matters, or rough steps.
- Put submit feedback inline, not in an alert-only flow.
- Ensure mobile layout has no clipped inputs, overlapping labels, or layout shift when validation messages appear.

## Guardrails

- Do not put GitHub tokens in client-side code.
- Do not hardcode private usernames, repo names, handles, emails, account ids, or local filesystem paths in reusable skill artifacts.
- Do not create public issues containing private submissions.
- Do not invent private repo names; require env config or follow explicit local workspace instructions.
- Do not add a second form when an existing form should be extended.
- Do not skip docs for env vars and token permissions.

## Output Contract

When complete, report:
- files changed
- public/private issue destination logic
- source labels/body fields added
- env vars required
- validation commands run and results
- any deployment or credential steps still required
