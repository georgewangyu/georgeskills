---
name: resume-role-tailoring-ops
description: Use when tailoring a senior software engineering resume to a specific job description, company, role family, ATS keyword set, or application folder/variant.
memory_tags:
  - domain:resume
  - workflow:role-tailoring
  - repo_boundary:tools
  - data_class:private-derived
  - risk:medium
---

# Resume Role Tailoring Ops

## Trigger

Use when:
- the user provides or points to a job description and wants a targeted senior software engineering resume
- the user asks for ATS keywords, company-specific tailoring, match analysis, or JD fit
- the user wants a new company or category resume variant created under an existing resume folder structure

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
3. Extract the senior SWE hiring signal from the JD.
   - Look for explicit ATS wording around languages, platforms, architecture, distributed systems, cloud, data/ML/AI infra, reliability, observability, CI/CD, ownership, mentorship, technical leadership, cross-functional execution, and business impact.
   - Separate recruiter-facing exact phrases from hiring-manager evidence needs.
   - Preserve important company vocabulary when truthful, but do not mirror awkward JD language if it makes the resume sound fake.
4. Audit available evidence before rewriting.
   - Search existing resume variants, project notes, application notes, brag docs, commit summaries, and local source material if available.
   - For each target keyword or seniority signal, mark evidence as `strong`, `partial`, `missing`, or `unsupported`.
   - If evidence is missing or only partial, interview the user before adding it. Ask concise questions that elicit concrete facts: system scale, ownership boundary, architecture choices, technologies used, measurable outcome, reliability/performance impact, cross-team work, leadership/mentorship, and dates.
   - If the user cannot provide evidence, leave the term out or put it in a gap list. Do not infer work-laptop history, internal project details, metrics, tools, or scope.
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
