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
- Private compiled pages: sibling LLM-wiki repo configured by `LLM_WIKI_ROOT`
- Raw sources remain in repo docs, exports, and daily summaries

## Current Script Surface

Implementations currently live in:
- `skills/knowledge-ops/scripts/`
- `refresh_agent_managed.py` for deterministic candidate extraction and low-risk auto-apply into the configured LLM wiki

Scheduled refreshes are deterministic and do not call an external LLM
provider. When semantic synthesis is needed, the calling agent should review
the deterministic candidates and update the wiki within its already-approved
runtime instead of delegating private source material to a second model API.
