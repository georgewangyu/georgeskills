# georgeskills Vision

georgeskills should be the reusable execution layer for liferepo-style personal
operating systems and agent workflows.

## Product Thesis

Docs define what should happen; skills define how to execute it. The repo is
useful when each skill is a modular, trigger-driven capability with clear
inputs, workflow, outputs, scripts, and guardrails.

## Goals

- Keep each skill single-purpose and composable.
- Preserve generic, public-safe examples and placeholders.
- Put user-specific defaults, credentials, and private overlays outside this
  repo.
- Keep output contracts explicit enough that skills can be chained safely.

## Non-Goals

- Do not hardcode personal handles, emails, account ids, private URLs, or local
  machine paths into skills.
- Do not turn the skill catalog into a vague prompt dump.
- Do not hide workflow ownership when a capability belongs in another repo.
