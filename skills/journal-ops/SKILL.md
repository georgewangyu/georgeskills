---
name: journal-ops
description: Modular tooling for journal ingestion, prep, and derived-context generation. Use when work involves reusable journal processing logic.
memory_tags:
  - domain:journal
  - workflow:daily-summary
  - skill_role:operator
  - repo_boundary:tools
  - data_class:private-derived
  - risk:medium
---

# Journal Ops

## Trigger

Use this skill when implementing reusable journal tooling such as:
- context generation
- metrics ingestion
- workflow prep orchestration
- workflow completeness checks
- sprint metrics visualization

## Boundaries

- Specification source: `liferepo/journal/`
- Private state source: `<private-repo>/journal/`
- This skill should stay data-agnostic where possible.

## Current Script Surface

Implementations currently live in:
- `skills/journal-ops/scripts/`
- `skills/journal-ops/config/daily_workflow_modules.yml` defines the module
  profiles used to keep daily workflow prep lightweight without changing the
  normal output contract.

Legacy entrypoints remain in `<private-repo>/scripts/journal/` as wrappers that
delegate to this skill.

The prep runner discovers transcript sources and refreshes objective context;
it does not interpret transcripts or call an external model provider. The
active Codex agent must read the available transcript text directly, interpret
all same-day sources together, and write the most useful supported synthesis
into the private journal.

The standard and full prep profiles also create a bounded private iMessage
daily-context staging file through `exports-ops`. Treat it like transcript
source material: the active Codex agent interprets it and follows the private
journal policy on bounded raw excerpts. Never promote raw handles, credentials,
attachment bodies, or bulk message dumps. The check-in profile skips Messages.

## Activity evidence

`activity_evidence_report.py --policy <private-policy.json> --date YYYY-MM-DD`
refreshes local daily and trailing 7/14-day derived reports. Standard/full daily
prep invokes it only when `<private-repo>/journal/allocation/policy.json` exists;
check-in skips it. For exact historical/sprint windows use `--start-date`,
`--end-date` and `--output-prefix`. Policy supplies timezone, source roots, private
topic rules, reviewed-interval file and private derived root.

Ambient minute-heading unions measure conversation-envelope presence only.
Only separately reviewed source-linked activity intervals create supported
hour bounds: observed intervals have explicit boundary uncertainty, inferred
intervals have zero lower bound, and passive media/background workers add no
active work. Conflicting categories and explicit host gaps remain unknown.
Unquantified does not mean zero work; all-device coverage is never assumed.
Private rules, budgets and personal artifacts must stay outside this package.
There are no model/provider calls, background recording or scheduled jobs.
