---
name: frontend-catalog-design-ops
description: >-
  Design catalog-first frontend prototypes for searchable indexes, blog-like
  reference libraries, public resource catalogs, contribution libraries, and
  intake-backed directories. Use when a user wants a frontend starting point
  similar to Loops Radar: scrollable/searchable items, detail pages or detail
  panels, category filters, and a bottom contribution/request form that can
  route submissions into a private review workflow.
memory_tags:
  - domain:frontend-design
  - workflow:catalog-ui-generation
  - skill_role:generator
  - repo_boundary:tools
  - inputs:product-catalog
  - outputs:frontend-ui
  - risk:medium
---

# Frontend Catalog Design Ops

## Overview

Use this skill to start frontend work from a calm, useful catalog surface instead of a generic SaaS landing page. The default artifact is a local clickable prototype with 2-3 distinct design options, screenshots, and a recommendation.

## Reference Routing

- Read `references/catalog-first-pattern.md` when the requested surface is a library, index, directory, radar, resource hub, collection, or searchable blog.
- Read `references/snackvoice-design-language.md` when the user wants the softer SnackVoice-inspired design language: warm surfaces, restrained accent color, rounded controls, focus rings, and friendly technical polish.

## Workflow

1. Define the catalog job in one sentence: who is browsing, what they are looking for, and what action they should take next.
2. Choose three option lanes unless the user asks for one direction:
   - Plain Codex index: direct, open-source, searchable list plus detail preview.
   - Editorial reference catalog: blog-like field guide with stronger typography and article-style rows.
   - Product catalog: app-like list/table, side detail panel, badges, filters, and structured controls.
3. Keep the primary screen useful:
   - brand/name in the first viewport
   - search input above the list
   - category/status filters
   - scrollable item list
   - selected item detail or detail-page preview
   - contribution/request form near the bottom
4. Build a local prototype before debating implementation stack. Static HTML/CSS is acceptable when the user is choosing direction; use React/shadcn only after the direction is selected.
5. Capture screenshots for each option and at least one mobile viewport. Fix obvious overflow, squeezed headers, raw inputs, and text crowding before presenting.
6. Recommend one option with a direct rationale. Usually choose the option that makes the catalog easiest to scan, copy from, and contribute to.

## Design Defaults

- Prefer utility over marketing: the catalog itself is the hero.
- Use sections, rails, rows, detail panels, and forms. Do not lead with a decorative hero, logo cloud, or card mosaic.
- Use one strong accent color for CTAs, focus rings, and active states.
- Use off-white or warm neutral surfaces with restrained borders and shadows.
- Keep cards purposeful: item containers, selected detail panels, forms, and modals. Avoid nested cards.
- Make labels and metadata compact: category, status, updated date, difficulty, verified/draft/review state.
- Keep contribution language simple: submit, request, improve, private review, public candidate.

## Contribution Form Pattern

Place the contribution form after the catalog/detail content unless the user asks for intake-first.

Fields:
- request type: submit, request, improve
- visibility: private review, public candidate
- title/name
- what it helps someone do
- rough steps or description
- handle optional
- link/context optional

The form can create a private issue, send a private request, or write to a review queue. Keep the skill public-safe: use generic `<private-review-repo>` or "private review workflow" language, not user-specific repo names or accounts.

## Output Contract

Return or create:
- visual thesis
- three design options, or a clear reason for fewer
- local prototype path or implementation plan
- screenshots when a prototype is built
- mobile/responsive check result
- recommended option and next implementation step

## Guardrails

- Do not use a generic SaaS dashboard as the first screen.
- Do not make a landing page unless the user explicitly asks for marketing.
- Do not hide the catalog below a large hero.
- Do not copy another product's exact frontend design; extract the interaction pattern instead.
- Do not hardcode private names, handles, emails, account IDs, private repo URLs, or local filesystem paths inside reusable skill artifacts.
