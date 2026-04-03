---
name: knowledge-ops
description: Maintain compiled knowledge pages that sit between raw source artifacts and compact structured memory.
memory_tags:
  - domain:knowledge
  - workflow:compiled-knowledge
  - repo_boundary:tools
  - data_class:private-derived
  - outputs:markdown-synthesis
  - risk:medium
---

# Knowledge Ops

## Trigger

Use when:
- a recurring topic needs a maintained current-best markdown page
- a conversation produced durable synthesis, not just a chronological update
- an agent should refresh compiled knowledge from daily-summary milestones and related source files

## Boundaries

- Public specification source: `liferepo/knowledge/`
- Private compiled pages: `<private-repo>/knowledge/agent-managed/`
- Raw sources remain in repo docs, exports, and daily summaries

## Current Script Surface

Implementations currently live in:
- `skills/knowledge-ops/scripts/`
