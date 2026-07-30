---
name: resume-creation-ops
description: Orchestrate end-to-end professional resume creation, rewriting, multi-role variants, one-page compression, feedback, document generation, and ATS and visual QA. Use when a user asks to create, fix, shorten, reconstruct, or redesign someone's resume rather than perform only one specialized resume pass.
metadata:
  memory_tags:
    - domain:resume
    - workflow:resume-creation
    - skill_role:orchestrator
    - repo_boundary:tools
    - data_class:private-derived
    - risk:medium
---

# Resume Creation Ops

## Core Contract

Treat resume creation as one verified pipeline:

1. Use `resume-role-tailoring-ops` to extract the full source, build the
   evidence bank, select target lanes, and tailor truthful content.
2. Use `resume-formatting-ops` to produce readable editable and PDF artifacts,
   choose an appropriate template family, and enforce page fit.
3. Use `resume-ats-validation-ops` as the independent final gate for
   parseability, truthfulness, required content, and page utilization.

Do not mark the work complete until all applicable gates pass. Loop a failed
artifact back to the skill that owns the defect.

## Preflight

1. Read every page and extract all available source text. Do not rewrite from
   only the first page or an abbreviated preview.
2. Resolve exact identity facts: name, contact details, dates, degree,
   institution, GPA and its scale, links, and role titles. Preserve the
   original facts unless the user corrects them.
3. Determine the target lane or job description. When the user wants multiple
   lanes, create distinct variants from one shared evidence bank rather than
   one vague general resume.
4. Score evidence sufficiency before drafting:
   - `3 — sufficient`: verified evidence supports the target and an
     evidence-dense full page.
   - `2 — usable`: credible, but one or two important gaps weaken targeting or
     page density.
   - `1 — sparse`: too little relevant detail for a strong full page.
   - `0 — blocked`: identity, dates, target direction, or core experience is
     unresolved.
5. At levels 0–1, stop final generation and ask 3–7 high-yield questions. At
   level 2, ask the targeted questions unless the user explicitly asks to
   proceed with the known gaps. Never replace missing evidence with padding,
   repetition, generic claims, or invented details.

## Evidence Intake

Ask only questions that can materially improve the resume. Prioritize:

- current work or study since the last dated entry
- the candidate's exact ownership and contribution boundary
- users, datasets, scale, performance, adoption, accuracy, or other outcomes
- exact tools, languages, platforms, scientific methods, and modalities used
- testing, validation, deployment, maintenance, reproducibility, or handoff
- public artifacts, publications, presentations, awards, or project links
- work authorization and location only when application strategy requires them

Treat answers as evidence, not permission to exaggerate. If an answer remains
vague, ask a follow-up or write a narrower claim.

## Content and Variant Workflow

1. Build a fact-preserving evidence bank from the source and any answers.
2. Rank evidence separately for each target lane.
3. Preserve the strongest recent and role-relevant experience, projects,
   publications, education, awards, and skills.
4. Compress a multi-page source by removing duplication and weak material
   before shrinking typography. Do not preserve every old section equally.
5. Write bullets that make ownership, method, scope, and outcome clear without
   claiming unsupported metrics.
6. Produce genuinely different variants when the screening signal differs.
   A software version should foreground engineering and delivery evidence; a
   research or bioinformatics version should foreground methods, data,
   reproducibility, scientific interpretation, and relevant outputs.

## Template Selection

Read [references/template-families.md](references/template-families.md) before
choosing a layout. Default to an ATS-safe one-column family:

- `ATS Classic` for broad professional use
- `Technical Accent` for software, data, and technical product roles
- `Research & Publications` for scientific, research, and bioinformatics roles

Color may create hierarchy but must not carry meaning. Avoid sidebars, icons,
text boxes, image-only text, and decorative structures that corrupt reading
order.

## One-Page Hard Gate

When the user requests one page, all of these conditions are required:

1. The final PDF has exactly one page.
2. Run
   `skills/resume-formatting-ops/scripts/resume_page_utilization.py <pdf>`.
3. Visible content normally spans at least 80% of page height.
4. Bottom whitespace is normally no more than 1.25 inches and no less than
   0.35 inches.
5. Body text is normally at least 9.5 pt and margins at least 0.45 inches.
6. A rendered visual inspection shows no clipping, crowding, orphaned bullets,
   awkward gaps, or false visual balance.
7. Extracted text preserves a sane ATS reading order.

A one-page file that occupies only part of the page fails. An overcompressed
page with tiny type also fails. Underfill loops back to evidence selection or
the evidence interview; overflow loops back to prioritization and deduplication.
Do not solve either failure with invented content or extreme spacing.

## Final Verification and Deliverables

Run the ATS validator after formatting and report:

- pass or fail and exact page count
- evidence-sufficiency level
- page-utilization metrics
- parser and hyperlink sanity
- unsupported claims or unresolved facts
- important target-keyword gaps
- any questions or residual risks

Deliver the editable source or DOCX, final PDF, concise feedback on the
original, and a short note explaining which target each variant serves.

## Boundaries

- Do not claim a universal ATS score.
- Do not invent facts, metrics, methods, tools, dates, or ownership.
- Do not upload private resumes to online checkers without explicit approval.
- Keep reusable instructions free of personal identifiers and private paths.
- Use document and PDF skills for file conversion or rendering when available;
  this skill owns the resume workflow and acceptance criteria.
