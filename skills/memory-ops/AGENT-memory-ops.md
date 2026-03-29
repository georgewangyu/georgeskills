# Memory Scripts Agent Rules

Rules for automation in `scripts/memory/`.

## Purpose

These scripts automate extraction, validation, and querying for the structured
memory layer under `memory/`.

## Guardrails

- Prefer conservative extraction over aggressive recall.
- Candidate memories should be reviewable and traceable.
- Do not auto-promote extracted candidates into canonical memory stores unless
  the workflow explicitly says to do so.
- Keep source references precise enough that a human can inspect the origin
  quickly.

## Current Bias

- Strong preference for high-precision extraction from known daily-summary
  sections.
- Weak inference, especially around people and preferences, should stay out
  until the workflow gets a real review step.
