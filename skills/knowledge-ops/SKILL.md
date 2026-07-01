---
name: knowledge-ops
description: Maintain compiled knowledge pages that sit between raw source artifacts and compact structured memory.
memory_tags:
  - domain:knowledge
  - workflow:compiled-knowledge
  - skill_role:operator
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
- Private compiled pages: `<private-repo>/agent-managed/`
- Raw sources remain in repo docs, exports, and daily summaries

## Current Script Surface

Implementations currently live in:
- `skills/knowledge-ops/scripts/`
- `refresh_agent_managed.py` for deterministic candidate extraction and low-risk auto-apply
- `llm_refresh_agent_managed.py` for headless semantic routing and topic-page rewrites via an LLM provider
