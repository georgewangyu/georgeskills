---
name: health-ops
description: Modular tooling for health-data ingestion and derived analytics workflows.
memory_tags:
  - domain:health
  - workflow:ingest-analyze
  - repo_boundary:tools
  - data_class:sensitive-derived
  - risk:high
---

# Health Ops

## Trigger

Use this skill for reusable health processing logic:
- import/normalize pipelines
- derived daily context generation
- reusable analysis/reporting transforms

## Boundaries

- Specification source: `liferepo/health/`
- Private state source: `<private-repo>/personal-health/` and `<private-repo>/health-family/`
- New-user Apple Health setup guide: `liferepo/health/APPLE_HEALTH_ONBOARDING.md`

## Current Script Surface

Implementations currently live in:
- `skills/health-ops/scripts/`

Legacy entrypoints remain in `<private-repo>/scripts/journal/` as wrappers that
delegate to this skill.

Note:
- `health_overnight_analysis.py` currently stays in `journal-ops` because
  morning/context scripts import it as a module.
