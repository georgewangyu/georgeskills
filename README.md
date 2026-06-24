# georgeskills

Modular execution skills and reusable tooling for the liferepo personal
operating system. Where `liferepo` defines what to do, `georgeskills` defines
how to do it.

---

## Philosophy

An AI assistant is only as capable as the tools it can invoke. Skills in this
repo are modular, single-purpose building blocks — each with a clear trigger,
defined inputs, a workflow, and an output contract. The AI loads a skill by
name, follows the workflow, and produces the expected output without needing
bespoke instructions every time.

Design rules:

- **One responsibility per skill.** A skill does one kind of work. Complex
  tasks are handled by composing multiple skills in sequence.
- **No hardcoded private data.** Skills use generic placeholders and resolve
  private state via environment variables or the private repo pointer config.
  Personal account handles, tokens, and paths stay in the private repo.
- **Trigger-driven.** Each skill defines exactly when to use it. The AI
  selects the right skill from the trigger conditions, not from keyword
  matching on the skill name.
- **Output contracts.** Every skill specifies what it produces and where. This
  makes skill output predictable and composable.

---

## Structure

```
georgeskills/
  AGENTS.md                    ← session bootstrap
  README.md                    ← this file
  MEMORY_TAGS.md               ← canonical tag vocabulary for memory extraction
  MIGRATION_QUEUE.md           ← pending migrations from private repo to skills
  skills/
    <skill-name>/
      SKILL.md                 ← skill definition (trigger, inputs, workflow, output)
      scripts/                 ← optional supporting scripts
  scripts/
    bootstrap_private_repo.py  ← scaffold a new private repo from liferepo templates
    sync-to-codex.sh           ← symlink skills into ~/.codex/skills/
  templates/
    SKILL_TEMPLATE.md          ← template for new skills
```

---

## Skill Catalog

### Data Exports

| Skill | Description |
|---|---|
| `exports-ops` | Umbrella skill for multi-source export pipelines. Use when no more specific export skill applies. |
| `apple-notes-export-ops` | Export Apple Notes into private markdown artifacts for journaling and context-building. |
| `apple-books-export-ops` | Explain and run Apple Books highlights, notes, and bookmarks export into private markdown drafts. |
| `email-ops` | Work with the Gmail export pipeline for triage context, scope verification, and lightweight send/reply helpers. |
| `calendar-ops` | Work with the Google Calendar export pipeline for schedule context and day planning. |
| `cursor-chat-export-ops` | Export Cursor chats into private artifacts for search, review, and context recovery. |

### Social Media

| Skill | Description |
|---|---|
| `x-check-xbot` | Pull X/Twitter home and latest feeds with the native xbot engine. Summarizes signal themes. |
| `x-check-bird` | Deprecated legacy Bird fallback for explicit baseline or blocked-xbot cases only. |
| `tiktok-check-ops` | Check TikTok account or video public metadata and recent content. |
| `instagram-check-ops` | Check Instagram account or post public status and profile metadata. |
| `instagram-carousel-ops` | Create branded Instagram carousel assets, including PNG posters, short MP4 motion pages, editable references, and posting notes. |
| `social-screen-control-ops` | Use Codex Computer Use for bounded logged-in visual checks on social-media pages when CLI or Playwright paths are blocked. |
| `social-motion-diagram-ops` | Create Excalidraw-style static diagrams and short looping motion assets for LinkedIn/X/social drafts. |
| `social-hook-selection-ops` | Select and adapt high-fit hooks for TikTok, Instagram Reels, YouTube Shorts, and short-form video ideas. |
| `shortform-talking-points-ops` | Create natural point-form talking outlines for TikTok, Instagram Reels, and Shorts using a sourced hook, hot take beats, and final twist. |
| `capcut-ai-edit-reel-ops` | Create list-style short-form reels by duplicating a proven CapCut AI-edit template, updating the title, and drafting the numbered caption/comment copy. |
| `weekly-video-batch-ops` | Organize recurring short-form video batch folders, CapCut final export inboxes, canonical final names, quick-access final-video indexes, and weekly phone-transfer bundles. |
| `youtube-check-ops` | Check YouTube channel or video public metadata. Falls back to lightweight public probes. |
| `youtube-transcribe-ops` | Transcribe a YouTube video. Prefers existing subtitles; falls back to local Whisper. |
| `durable-transcript-archive-ops` | Preserve transcripts and source media into a durable archive with provenance and cleanup notes. |
| `social-video-archive-ops` | Archive reference videos from social platforms outside active repos, with provenance notes and repo-side symlinks. |
| `video-breakout-research-ops` | Sweep TikTok, Instagram, and YouTube Shorts for low-follower, high-traction video patterns. |
| `niche-video-watchlist-ops` | Run targeted YouTube/TikTok bot sweeps for niche search lanes and creator watchlists. |
| `account-video-watchlist-ops` | Track a private list of niche creator accounts for new high-view videos worth emulating. |
| `broad-video-trend-radar-ops` | Run broad cross-platform trend sweeps for high-multiplier short-form formats outside a narrow niche. |
| `shortform-rough-cut-ops` | Turn raw short-form clips, creator intent, and format runbooks into an edit decision list and rough draft plan. |
| `video-companion-page-ops` | Create local HTML/blog-style companion pages for educational videos with clickable sources, screenshots, diagrams, and talking outlines. |

### Research

| Skill | Description |
|---|---|
| `market-landscape-research-ops` | Map a software or app market: categories, leading products, pricing, user segments, upstarts. |
| `revenue-signal-research-ops` | Estimate which apps or SaaS products are likely making meaningful revenue from public signals. |
| `asymmetric-revenue-case-study-ops` | Produce single-company case studies for small-team or under-the-radar products with disproportionate revenue signals. |
| `breakout-signal-research-ops` | Find products with asymmetric traction relative to their starting base — the low-follower breakout pattern. |
| `person-ignition-case-study-ops` | Research how a public creator, founder, builder, or operator got their first major audience, reputation, or open-source traction spike. |
| `customer-pain-mining-ops` | Mine reviews, forums, and App Store comments for repeated user pain points and unmet needs. |
| `product-hunt-trends-ops` | Scout Product Hunt launches for interesting products, breakout signals, positioning patterns, and market ideas. |
| `ignitionbot-trend-radar-ops` | Run IgnitionBot scored trend sweeps across developer, social, video, RSS, web, and watchlist sources. |
| `yc-company-scouting-ops` | Scout YC companies, batches, and Launch YC posts for standout startups, batch themes, and useful product ideas. |
| `deep-exploration-ops` | Exploration artifact processing and framework distillation support. |
| `closed-source-product-reconstruction-ops` | Inspect public closed-source products to infer stack, frontend/API/backend patterns, open-source analogues, and rebuild plans. |

### Product / Business

| Skill | Description |
|---|---|
| `idea-wedge-selection-ops` | Turn market and pain research into a concrete product direction: wedge, target user, why-now thesis. |
| `product-ignition-critique-ops` | Critique product ideas for pain legibility, ignition events, capture loops, and post-spike survival. |
| `saas-template-fit-ops` | Map a chosen SaaS idea to the right template shape: account model, billing, architecture constraints. |
| `naming-ops` | Generate and screen brandable company, product, and SaaS names with domain and trademark checks. |
| `sales-discovery-email-ops` | Write respectful first-touch outbound emails for sales discovery and consulting outreach. |
| `stripe-ops` | Reusable local Stripe setup workflow using shared private credentials, Stripe CLI, and the installed upstream Stripe skills. |
| `tax-filing-ops` | Build a repeatable tax-prep workflow with checklist automation, product-specific filing runbooks, and human-reviewed submission gates. |

### Design

| Skill | Description |
|---|---|
| `website-page-planning-ops` | Turn a rough site concept into a concrete page plan with section structure and CTA map before design starts. |
| `frontend-art-direction-ops` | Build visual direction for a product UI: style references, typography, color tokens, layout and motion rules. |
| `frontend-catalog-design-ops` | Start catalog-first frontend prototypes for searchable indexes, libraries, radars, directories, and contribution-backed resource hubs. |
| `frontend-polish-pass-ops` | Final polish pass: responsiveness, accessibility, hierarchy, interaction quality, and perceived performance. |
| `pencil-design-orchestration-ops` | Run a repeatable Pencil MCP design workflow from the coding agent through to frontend handoff. |
| `disk-space-ops` | Inspect disk usage, highlight large folders/files, and suggest conservative cleanup targets with risk framing. |

### Journal and Workflow

| Skill | Description |
|---|---|
| `journal-ops` | Reusable journal ingestion, prep, and derived-context generation logic. |
| `later-queue-orchestrator-ops` | Orchestrate later queues: classify routing, prepare decision-ready briefs, promote work, and enforce proof gates. |
| `later-queue-triage-ops` | Convert deferred work queues into source-first decision cards with fit, risk, proof, blockers, and next action. |
| `live-proof-gate-ops` | Define proof-before-done gates for agent workflows, automations, integrations, and queued work. |
| `decision-gate-ops` | Evaluate meaningful operational, automation, product, workflow, or personal execution decisions with constraints, proof thresholds, reversible defaults, and future principles. |
| `codex-thread-hygiene-ops` | Organize Codex conversations by renaming vague threads and reviewing pinned-chat cleanup candidates. |
| `skill-forge-ops` | Mine journals, transcripts, PRs, commits, scripts, and agent notes for workflows worth turning into reusable skills. |
| `agent-eval-harness-ops` | Design lightweight eval harnesses for coding or workflow agents, including rubrics and failure taxonomies. |
| `repo-readme-onboarding-ops` | Audit and improve repository READMEs and GitHub About metadata for clearer first impressions, quickstarts, usage proof, and contribution onboarding. |
| `rental-search-due-diligence-ops` | Run bounded rental-search due diligence with ranked shortlists, tour questions, risk checks, and stop conditions. |
| `health-ops` | Health data ingestion and derived analytics workflows (Apple Health pipeline). |
| `memory-ops` | Structured memory extraction, validation, promotion, and document salience indexing. |
| `knowledge-ops` | Maintain compiled knowledge pages between raw source artifacts and compact structured memory. |
| `aida-ops` | Aida workflow bookkeeping and audit tooling. |
| `utility-ops` | Resume conversion, PDF text helpers, repo summary generation, and frontmatter backfills. |
| `pdf-reconstruction-ops` | PDF and image text extraction and OCR pre-processing. |

### Career

| Skill | Description |
|---|---|
| `resume-role-tailoring-ops` | Tailor resumes to a target JD, company, role family, and ATS keyword plan while preserving truthful evidence. |
| `resume-formatting-ops` | Fix resume formatting, build PDFs, check one-page fit, and verify ATS parseability before submission. |
| `resume-ats-validation-ops` | Validate resume variants for parser sanity, keyword coverage, truthful tailoring, and required content preservation. |

---

## Installation

### 1. Clone

```bash
git clone https://github.com/<user>/georgeskills
```

Place it as a sibling of `liferepo` and your private repo:

```
Workspace/
  liferepo/
  georgeskills/
  <private-repo>/
```

### 2. Enable git hooks

```bash
git config core.hooksPath .githooks
chmod +x .githooks/commit-msg .githooks/pre-commit
```

### 3. Sync skills to your AI assistant

```bash
./scripts/sync-to-codex.sh
```

This symlinks each skill directory from `skills/` into `~/.codex/skills/`.
After adding a new skill, re-run this script and restart your AI assistant
so the skill list refreshes.

### 4. Install transcription dependencies (optional)

If you want the local Whisper transcription pipeline (Apple Silicon):

```bash
cd scripts/transcription
python3 -m venv venv
source venv/bin/activate
pip install mlx-whisper
```

Requires ARM64 Python (`/opt/homebrew/bin/python3` on Apple Silicon).

---

## Adding a New Skill

1. Create a folder under `skills/<skill-name>/`.
2. Copy `templates/SKILL_TEMPLATE.md` to `skills/<skill-name>/SKILL.md`.
3. Fill in all sections: trigger, inputs, workflow, output contract, guardrails.
4. Add YAML frontmatter with at least `name`, `description`, and `memory_tags`.
5. Run `./scripts/sync-to-codex.sh` and restart your AI assistant.
6. Update the skill catalog table in this README.

### Skill header example

```yaml
---
name: my-skill-ops
description: One-line description of what this skill does and when to use it.
memory_tags:
  - domain:my-domain
  - workflow:my-workflow
  - inputs:web
  - outputs:status-report
  - risk:low
---
```

### Reusability rules

- Do not hardcode usernames, emails, account IDs, or private defaults.
- Use generic placeholders such as `exampleuser`, `<target>`, or `<private-repo>`.
- Put user-specific wrappers and defaults in the private repo.
- When documenting examples, use public-safe sample data.

---

## Private Repo Bootstrap

To scaffold a new private repo from liferepo templates:

```bash
# Guided interactive setup
python3 scripts/bootstrap_private_repo.py --name my-private-repo --create --interactive

# Non-interactive with all modules
python3 scripts/bootstrap_private_repo.py \
  --name my-private-repo \
  --create \
  --init-journal \
  --init-resume \
  --init-exports
```

See `liferepo/docs/PRIVATE_REPO_SETUP.md` for full prerequisites and
integration setup (Gmail API, Google Calendar API, Apple Notes).

---

## Notes

- `~/.codex/skills/` is machine-level, not workspace-local.
- This repo is the editable source of truth for all skills.
- Skills that reference `<private-repo>` resolve the path via the
  `LIFEREPO_PRIVATE_ROOT` environment variable or the pointer config at
  `liferepo/.liferepo/local/private_repo.json`.
