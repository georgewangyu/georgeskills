---
name: tax-filing-ops
description: Plan and run a repeatable tax-prep workflow with AI-assisted checklisting while keeping filing submission human-reviewed.
memory_tags:
  - domain:finance
  - workflow:tax-filing
  - skill_role:operator
  - inputs:user-doc-inventory
  - outputs:filing-runbook
  - risk:high
  - repo_boundary:tools
---
# tax-filing-ops

## When To Use

Use when the user asks to automate, streamline, or orchestrate personal tax filing work (for example with Wealthsimple Tax or TurboTax).

## Core Principle

Automate preparation and verification workflow, not blind submission.

This skill should never claim full end-to-end auto-filing unless a verified and authorized integration explicitly supports submission actions.

## Inputs

- tax year (for example `2025`)
- filing jurisdiction (for example `CA` or `US`)
- preferred filing product (`Wealthsimple Tax`, `TurboTax`, or undecided)
- known income and deduction categories
- current document inventory (what is already available vs missing)

## Workflow

1. Scope and constraints
   - Confirm tax year, jurisdiction, and filing product.
   - Identify whether the session is planning-only, prep, or filing-ready.
2. Build intake matrix
   - Create a checklist of required documents by category.
   - Track status per item: `missing`, `requested`, `received`, `entered`, `verified`.
3. Gap closure
   - Produce a short task list for each missing document.
   - Flag assumptions that can materially change filing outcome.
4. Filing runbook
   - Generate a step-by-step session plan for the chosen filing surface.
   - Include a manual validation gate before any final submit step.
5. Closeout and retention
   - Record non-sensitive filing metadata (date, product, status, follow-ups).
   - Keep raw tax files and identity documents outside git.

## Connector Notes

- Treat third-party tax integrations as product-level capabilities unless there is a documented local API/connector path available in the current runtime.
- If a filing product integration is only available in a chat UI, use it for guided Q&A and checklist support, then keep final submission human-reviewed.

## Guardrails

- Do not provide legal or tax advice beyond organizational workflow support.
- Do not store raw tax slips/returns, SSN/SIN, account IDs, or full personal addresses in repository files.
- Require explicit user confirmation before any irreversible step.

## Output Contract

Return:

- `checklist`: categorized required docs with status
- `gaps`: missing items and concrete retrieval actions
- `filing_runbook`: ordered session steps for chosen platform
- `risk_flags`: unresolved assumptions and high-impact uncertainties
- `closeout_template`: non-sensitive filing summary skeleton
