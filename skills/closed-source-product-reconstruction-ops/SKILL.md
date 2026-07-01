---
name: closed-source-product-reconstruction-ops
description: Analyze a public closed-source product's visible stack, UI/API patterns, design language, and open-source analogues to produce an original rebuild plan.
memory_tags:
  - domain:product-research
  - workflow:closed-source-reconstruction
  - skill_role:researcher
  - repo_boundary:tools
  - inputs:web
  - outputs:rebuild-plan
  - risk:high
---

# Closed Source Product Reconstruction Ops

## Trigger

Use when:
- the user wants to understand how a closed-source app or website is probably built
- the user asks for a BuiltWith-style stack read plus DevTools/network inference
- the user wants open-source GitHub analogues for a closed-source product
- the user wants to rebuild a similar product with an original implementation plan
- the task involves identifying frontend framework, design language, APIs, data model, backend modules, third-party services, or implementation sequence

Do not use when:
- the user asks to bypass auth, scrape private data, defeat security controls, or exfiltrate proprietary code
- the user wants to copy protected assets, brand identity, or exact source code
- the target cannot be inspected from public pages, demo flows, or user-authorized access
- the task is only broad market research with no reconstruction goal

## Inputs

- Required: product/app URL or name, reconstruction goal
- Optional: target feature flow, screenshots, public docs, demo credentials supplied by the user, comparable products, preferred stack, desired MVP scope, open-source search keywords

## Workflow

1. Define the reconstruction boundary:
   - target product and feature flow
   - what is public, demo-accessible, or user-authorized
   - what must not be copied
   - intended rebuild goal: MVP, clone-for-learning, internal tool, competitor analysis, or open-source analogue search
2. Run surface stack inspection:
   - page source and bundled script names
   - response headers, cookies, CDN, hosting, analytics, auth, payments, chat, email, feature flags, and error reporting
   - visible framework clues such as Next.js, Remix, Vite, Nuxt, Rails, Laravel, Django, Shopify, Webflow, Framer, WordPress, Tailwind, shadcn, Radix, Material, Chakra, or custom design system
   - BuiltWith, Wappalyzer, public docs, status pages, changelogs, and job posts when useful
3. Inspect frontend behavior:
   - route structure and app shell
   - component inventory: nav, dashboard, tables, forms, modals, editor surfaces, onboarding, settings, billing, command palette, upload flows
   - layout rules, density, visual language, icon system, animation, empty states, error states, and responsive behavior
   - client state patterns visible through storage, URL params, local/session storage, and network cache behavior
4. Inspect public network behavior:
   - REST, GraphQL, RPC, websocket, SSE, file upload, polling, or background-job patterns
   - endpoint naming and payload shapes visible in user-authorized flows
   - auth/session shape, rate-limit hints, feature flags, analytics events, and third-party SDK calls
   - separate observed facts from backend guesses
5. Infer likely backend architecture:
   - core entities and relationships
   - modules such as auth, users, teams, projects, artifacts, jobs, integrations, billing, notifications, analytics, admin, and AI/model calls
   - async work, queues, storage, search, vector/RAG, email, webhooks, and scheduled tasks
   - confidence label for each inference
6. Find open-source analogues:
   - search GitHub, GitHub Trending, curated awesome lists, package ecosystems, and docs examples
   - rank repos by product similarity, stack similarity, code quality, activity, license, and copyable patterns
   - identify what to study in each repo: app shell, data model, editor, billing, auth, AI workflow, background jobs, or design system
7. Translate into an original build plan:
   - recommended stack
   - pages and components
   - data model
   - API routes or server actions
   - background jobs and integrations
   - MVP scope
   - unknowns to spike first
   - first 3 implementation steps

## Output Contract

Return:
- product summary and reconstruction boundary
- detected stack with confidence levels
- frontend architecture and component inventory
- design language notes
- public network/API observations
- inferred backend modules and data model
- third-party services and integrations
- open-source analogue shortlist with what to study
- original rebuild plan
- unknowns and next probes
- legal/ethical boundary notes when relevant

## Boundaries

- Inspect only public or user-authorized surfaces.
- Do not bypass paywalls, auth, captchas, rate limits, or technical access controls.
- Do not provide instructions to steal proprietary code, secrets, or private data.
- Do not copy protected branding, visual assets, or exact proprietary text.
- Mark each claim as observed, inferred, or unknown.
- Prefer original implementation plans inspired by patterns, not one-to-one cloning.
