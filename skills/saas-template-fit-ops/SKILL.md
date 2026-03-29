---
name: saas-template-fit-ops
description: Translate a chosen SaaS idea into the right template shape by deciding account model, billing model, core workflow, required integrations, and day-1 architecture constraints. Use when the opportunity is chosen and the user needs to map it into a buildable SaaS template.
memory_tags:
  - domain:product-strategy
  - workflow:template-fit
  - repo_boundary:tools
  - inputs:product-idea
  - outputs:template-spec
  - risk:medium
---

# SaaS Template Fit Ops

## Trigger

Use when:
- a SaaS idea has already been selected
- the user wants to know which template shape fits the product
- the task is turning research into a buildable default architecture

Do not use when:
- the market itself is still unclear
- the user only wants high-level business research

## Inputs

- Required: product concept or chosen wedge
- Optional: target customer, pricing model, platform, team size, expected integrations

## Workflow

1. Restate the product in operational terms:
   - who the user is
   - what core workflow they perform
   - what data shape the product needs
2. Decide the critical template choices:
   - solo vs workspace vs org account model
   - subscription vs usage vs hybrid billing
   - required file storage, email, webhooks, or background jobs
   - admin/support surface
3. Compare the idea against the default SaaS template stance.
4. Identify what is standard day 1 and what should wait until a real trigger appears.
5. Hand off into the relevant SaaS template docs in `liferepo/business/saas-templates/` and private overlays where needed.

## Output Contract

- recommended template shape
- account and billing model
- must-have integrations
- schema/permission implications
- day-1 architecture vs later upgrades

## Boundaries

- Public defaults live in `liferepo/business/saas-templates/` and `liferepo/business/SAAS_PRODUCT_DEFAULTS.md`.
- Private venture-specific constraints live in `<private-repo>` or `georgerepo` private overlays.
