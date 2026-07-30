---
name: resume-role-tailoring-ops
description: Use when tailoring any professional resume to a job description, company, role family, career lane, ATS keyword set, or application variant, including software, data, research, scientific, and bioinformatics roles.
metadata:
  memory_tags:
    - domain:resume
    - workflow:role-tailoring
    - skill_role:operator
    - repo_boundary:tools
    - data_class:private-derived
    - risk:medium
---

# Resume Role Tailoring Ops

## Trigger

Use when:
- the user provides or points to a job description and wants a targeted resume
- the user asks for ATS keywords, company-specific tailoring, match analysis, or JD fit
- the user wants a new company, role-family, or career-lane resume variant

For an end-to-end request to create, fix, shorten, or redesign a resume, start
with `resume-creation-ops`; this skill owns its evidence and tailoring phase.

Do not use when:
- the request is only to fix layout, compile a PDF, or clean formatting; use `resume-formatting-ops`
- the user asks for cover letters or application answers without changing the resume

## Inputs

- Required: target role or job description, baseline resume or variant family
- Optional: company name, role family/category, seniority target, application URL, source notes, commit/work summaries, project docs, performance review notes, brag docs, or interview answers about missing evidence

## Workflow

1. Load local resume context.
   - Read the private resume area's nearest `AGENT-*.md`, `README.md`, prompt library, and variant strategy if present.
   - Inspect existing `default/` and `variants/` folders before choosing a destination.
2. Normalize the target.
   - Extract company, title, level, team/domain, location if relevant, and application URL.
   - Classify the role family using local conventions when available, such as `ai_infra`, `data_infra`, or `product_backend`.
3. Extract the hiring signal from the JD or target lane.
   - Look for explicit ATS wording around domain methods, tools, languages,
     platforms, workflows, ownership, collaboration, seniority, and outcomes.
   - For software roles, include architecture, reliability, testing, CI/CD,
     data systems, and delivery evidence. For scientific/research roles, include
     methods, modalities, data scale, reproducibility, publications, and
     biological or experimental interpretation.
   - Separate recruiter-facing exact phrases from hiring-manager evidence needs.
   - Preserve important company vocabulary when truthful, but do not mirror awkward JD language if it makes the resume sound fake.
4. Audit available evidence before rewriting.
   - Search existing resume variants, project notes, application notes, brag docs, commit summaries, and local source material if available.
   - For each target keyword or seniority signal, mark evidence as `strong`, `partial`, `missing`, or `unsupported`.
   - If evidence is missing or only partial, interview the user before adding it. Ask concise questions that elicit concrete facts: system scale, ownership boundary, architecture choices, technologies used, measurable outcome, reliability/performance impact, cross-team work, leadership/mentorship, and dates.
   - If the user cannot provide evidence, leave the term out or put it in a gap list. Do not infer work-laptop history, internal project details, metrics, tools, or scope.
   - Assign an evidence-sufficiency level before layout:
     - `3 — sufficient`: verified evidence can support the target and a full page
     - `2 — usable`: viable, but targeted answers would strengthen one or two gaps
     - `1 — sparse`: insufficient relevant detail for an evidence-dense page
     - `0 — blocked`: essential facts or target direction are unresolved
   - At levels 0–1, pause final resume generation and ask 3–7 high-yield
     questions. Do not compensate with padding, repeated content, generic
     summaries, or tiny typography.
5. Decide the destination path.
   - Category variant: `variants/<role_family>/<company_or_lane>/<person_or_profile>/`
   - Company-specific variant: use a company folder when the resume is targeted to one employer.
   - Keep filenames consistent with local naming conventions and avoid overwriting an existing tailored source without checking the diff.
6. Build the keyword plan before rewriting.
   - Separate must-have requirements, nice-to-have requirements, domain nouns, tool names, action verbs, and seniority signals.
   - Mark each keyword as `already evidenced`, `truthfully addable from known evidence`, or `unsupported`.
   - Do not add unsupported skills just because the JD asks for them.
7. Map evidence to resume sections.
   - Summary: role-family positioning and seniority signal.
   - Experience bullets: ownership, scope, technical depth, measurable outcomes.
   - Projects: strongest matching systems or artifacts.
   - Skills: only verified skills that are already present in the candidate's real background or clearly supported by source material.
8. Rewrite in small passes.
   - Preserve factual consistency and interview defensibility.
   - Prefer natural keyword integration over stuffing.
   - Keep bullets outcome-first, concrete, and scoped.
   - When compressing a multi-page source, use the page for the highest-value
     evidence instead of preserving every role equally. Prefer strong projects,
     quantified outcomes, publications, awards, and recent/relevant experience;
     remove duplicated or weak material first.
9. Run the verifier loop.
   - Compare final resume against the JD keyword plan.
   - List missing but important terms, explain whether each is unsupported or intentionally omitted.
   - Hand off to `resume-formatting-ops` for PDF build, one-page fit, parseability, and final QA.

## ATS Keyword Method

Use this structure for the keyword plan:

| Bucket | Meaning |
|---|---|
| Must-have | Explicit qualifications or repeated JD requirements |
| Domain | Product/team area terms that show context fit |
| Technical | Languages, frameworks, infra, ML/data tools, platforms |
| Workflow | Practices such as experimentation, observability, reliability, CI/CD |
| Seniority | Ownership, architecture, cross-team influence, mentoring, roadmap judgment |
| Unsupported | JD terms that should not be added without evidence |

Scoring should be directional, not fake precision. Prefer `strong / medium / weak` with concrete reasons over pretending ATS behavior is knowable.

## Evidence Interview

If target-role evidence is missing, interview before editing. Prefer questions like:

- What system or feature did you own end-to-end, and what boundary was clearly yours?
- What scale, latency, reliability, cost, adoption, or business metric changed?
- What architecture or technical tradeoff did you choose, and why?
- Which exact technologies, cloud services, data stores, frameworks, or internal platforms did you use?
- Who did you influence: partner teams, PM/design, on-call rotations, junior engineers, customers, leadership?
- What was the before/after state, and what would a coworker say you specifically contributed?
- Which project artifacts are public, who used them, and how were they tested,
  deployed, maintained, or handed off?
- What have you done since the last dated resume entry, and should it appear as
  work, research, coursework, volunteering, or an independent project?

Treat interview answers as source material, but keep uncertainty visible. If an answer is vague, ask a follow-up or write a weaker truthful bullet instead of upgrading it into a senior-sounding claim.

## Open-Source Patterns Worth Borrowing

- `srbhr/Resume-Matcher`: master resume plus JD-specific tailored output, keyword highlighting, and match suggestions.
- `rendercv/rendercv`: structured source of truth and reproducible generated resumes.
- `Reactive Resume`: privacy-first resume profiles and versioned variants.
- `open-resume`: parser-aware resume generation and resume import/export thinking.

## Outputs

- Tailored resume source in the chosen category/company variant folder
- Keyword plan with supported and unsupported terms
- Fit notes: top strengths, top gaps, and final risks
- Handoff note for formatting/build QA

## Boundaries

- Public specs live in `liferepo`.
- Private resume sources, job notes, company strategy, and application artifacts live in `<private-repo>`.
- This skill should not hardcode a person's name, email, private repo path, or company-specific private strategy.
- Keep claims defensible. A resume that gets an interview by creating a later interview landmine is not a win.
