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
| `email-ops` | Work with the Gmail export pipeline for triage context, scope verification, and lightweight send/reply helpers. |
| `calendar-ops` | Work with the Google Calendar export pipeline for schedule context and day planning. |
| `cursor-chat-export-ops` | Export Cursor chats into private artifacts for search, review, and context recovery. |

### Social Media

| Skill | Description |
|---|---|
| `x-check-ops` | Pull the X/Twitter home feed, run searches, or read a specific post. Summarizes signal themes. |
| `tiktok-check-ops` | Check TikTok account or video public metadata and recent content. |
| `instagram-check-ops` | Check Instagram account or post public status and profile metadata. |
| `youtube-check-ops` | Check YouTube channel or video public metadata. Falls back to lightweight public probes. |
| `youtube-transcribe-ops` | Transcribe a YouTube video. Prefers existing subtitles; falls back to local Whisper. |
| `video-breakout-research-ops` | Sweep TikTok, Instagram, and YouTube Shorts for low-follower, high-traction video patterns. |

### Research

| Skill | Description |
|---|---|
| `market-landscape-research-ops` | Map a software or app market: categories, leading products, pricing, user segments, upstarts. |
| `revenue-signal-research-ops` | Estimate which apps or SaaS products are likely making meaningful revenue from public signals. |
| `breakout-signal-research-ops` | Find products with asymmetric traction relative to their starting base — the low-follower breakout pattern. |
| `customer-pain-mining-ops` | Mine reviews, forums, and App Store comments for repeated user pain points and unmet needs. |
| `deep-exploration-ops` | Exploration artifact processing and framework distillation support. |

### Product / Business

| Skill | Description |
|---|---|
| `idea-wedge-selection-ops` | Turn market and pain research into a concrete product direction: wedge, target user, why-now thesis. |
| `saas-template-fit-ops` | Map a chosen SaaS idea to the right template shape: account model, billing, architecture constraints. |
| `naming-ops` | Generate and screen brandable company, product, and SaaS names with domain and trademark checks. |
| `sales-discovery-email-ops` | Write respectful first-touch outbound emails for sales discovery and consulting outreach. |

### Design

| Skill | Description |
|---|---|
| `website-page-planning-ops` | Turn a rough site concept into a concrete page plan with section structure and CTA map before design starts. |
| `frontend-art-direction-ops` | Build visual direction for a product UI: style references, typography, color tokens, layout and motion rules. |
| `frontend-polish-pass-ops` | Final polish pass: responsiveness, accessibility, hierarchy, interaction quality, and perceived performance. |
| `pencil-design-orchestration-ops` | Run a repeatable Pencil MCP design workflow from the coding agent through to frontend handoff. |

### Journal and Workflow

| Skill | Description |
|---|---|
| `journal-ops` | Reusable journal ingestion, prep, and derived-context generation logic. |
| `health-ops` | Health data ingestion and derived analytics workflows (Apple Health pipeline). |
| `memory-ops` | Structured memory extraction, validation, promotion, and document salience indexing. |
| `knowledge-ops` | Maintain compiled knowledge pages between raw source artifacts and compact structured memory. |
| `aida-ops` | Aida workflow bookkeeping and audit tooling. |
| `utility-ops` | Resume conversion, PDF text helpers, repo summary generation, and frontmatter backfills. |
| `pdf-reconstruction-ops` | PDF and image text extraction and OCR pre-processing. |

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
