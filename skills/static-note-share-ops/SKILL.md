---
name: static-note-share-ops
description: Publish selected local notes, transcripts, research docs, or markdown artifacts as public-safe static share pages. Use when the user wants a Notion-like "copy link" workflow, an unlisted/public page on a configured static site, a Vercel/Cloudflare/Netlify share route, or a repeatable export process from a private repo into a sanitized public page.
memory_tags:
  - domain:publishing
  - workflow:static-note-share
  - skill_role:generator
  - repo_boundary:tools
  - inputs:markdown-note
  - outputs:static-page
  - risk:medium
---

# Static Note Share Ops

## Overview

Turn one selected artifact into a shareable static page without exposing the
private repo. The skill owns the export protocol: classify the source, sanitize
it, place it in a configured share-site repo, validate locally, and deploy only
after explicit approval.

## Required Inputs

- Source artifact: local markdown, transcript, notes, HTML, or structured text.
- Share intent: `private-draft`, `unlisted`, or `public-indexed`.
- Share-site config: resolve from private repo config, environment variables,
  or explicit user instruction.

The reusable skill must not hardcode domains, account names, private repo names,
credentials, or personal defaults. Use placeholders such as `<share-site-repo>`,
`<share-domain>`, and `<private-repo>`.

## Config Contract

Look for user-specific defaults outside this skill, in this order:

1. Explicit user instruction in chat.
2. Private repo config or workflow doc.
3. Environment variables such as:
   - `SHARE_SITE_REPO`
   - `SHARE_SITE_DOMAIN`
   - `SHARE_SITE_DEPLOY_COMMAND`
4. Existing static-site conventions in the target repo.

If no share-site repo or deployment target exists, stop after producing a
public-safe export plan and ask for the missing target. Do not invent a domain.

## Workflow

1. Classify the source:
   - `owned-note`: user-authored idea, memo, outline, or explainer.
   - `derived-summary`: notes based on external sources.
   - `third-party-transcript`: transcript or close paraphrase of someone else's
     audio/video.
   - `private-record`: journal, health, finance, email, legal, client, or other
     sensitive material.
2. Choose the publish shape:
   - `note-page`: clean markdown/MDX article.
   - `source-backed-explainer`: summary, diagrams, takeaways, and source links.
   - `transcript-companion`: short excerpts only, plus user's analysis.
   - `redacted-brief`: sanitized excerpt from a larger private doc.
3. Apply the publication gate:
   - Treat `unlisted` as public. Anyone with the URL may read it.
   - Never publish secrets, credentials, private local paths, private emails,
     private names, client details, health/finance/legal details, or internal
     agent instructions.
   - For third-party transcripts, do not publish the full transcript by default.
     Publish a source-backed summary or companion page instead.
   - For private records, default to no publication unless the user explicitly
     approves the exact redacted content.
4. Sanitize the export:
   - Strip private frontmatter, memory tags, local repo metadata, and absolute
     paths.
   - Replace private references with public-safe descriptions.
   - Preserve public source URLs and clearly label facts versus interpretation.
   - Add a short provenance note when the page is derived from a source artifact.
5. Place the artifact in the share-site repo:
   - Follow existing route/content conventions.
   - Prefer stable slugs: `<topic>-<short-hash>` for unlisted pages, plain
     readable slugs only for intentionally indexed public pages.
   - Keep one source page per share item unless the site already supports
     collections.
6. Validate:
   - Run the share-site formatter, lint, typecheck, or build command when
     available.
   - Start the local dev server when needed and inspect the page if the change
     is visual.
   - Verify there are no broken links, leaked local paths, raw frontmatter, or
     accidental private content.
7. Deploy only with approval:
   - For `private-draft`, stop at local artifact path and preview URL.
   - For `unlisted` or `public-indexed`, ask before deploying unless the user
     already approved this exact publication action.
   - After deployment, read back the live URL and report the link.

## Redaction Checklist

Before deployment, check the rendered page and source file for:

- absolute local paths
- usernames, emails, account IDs, phone numbers, addresses
- credentials, tokens, cookies, env var values
- private repo names or internal directory structure that should not be public
- journal-only details, medical/financial/legal/client context
- raw full transcripts from third-party media
- unsupported claims presented as facts
- copyright-sensitive long excerpts

If any item is present, fix it or ask for explicit owner approval.

## Output Contract

Return:

- source artifact path
- source classification
- publish shape
- share-site repo/path
- local preview URL, if available
- deployment status: `not-deployed`, `approved-deployed`, or `blocked`
- live URL, if deployed
- redaction notes and residual risk
- validation commands run and results

## Boundaries

- This skill defines the repeatable publication workflow. It does not store
  user-specific domains or credentials.
- Do not expose private repositories directly through a static host.
- Do not make a private doc public merely because it can be deployed.
- Do not auto-deploy public pages without explicit approval for the exact page.
- Prefer a concise companion page over a copied private note when the source
  contains mixed private and public material.
