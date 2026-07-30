---
name: resume-ats-validation-ops
description: Validate resume variants for ATS parseability, role-targeted keyword coverage, truthful tailoring, readable one-page utilization, evidence sufficiency, and required section/experience preservation before submission.
metadata:
  domain: resume
  workflow: ats-validation
  risk: medium
  memory_tags:
    - domain:career
    - workflow:resume-ats-validation
    - skill_role:evaluator
    - repo_boundary:tools
    - inputs:resume
    - outputs:validation-report
    - risk:medium
---

# Resume ATS Validation Ops

## Trigger

Use when:
- a resume PDF or LaTeX/Markdown source has been tailored for a role
- the user asks whether a resume will pass ATS or recruiter screening
- a resume variant must stay one page while preserving required experience
- keywords from a job description or target role need coverage checks

For an end-to-end request to create, fix, shorten, or redesign a resume, start
with `resume-creation-ops`; this skill owns the independent final QA gate.

Do not use when:
- the task is only visual resume design with no submission/ATS concern
- the user wants fabricated metrics or unsupported keyword stuffing

## Inputs

- Required: resume PDF or source path
- Optional: target job description, required role/experience list, forbidden
  phrases, target keyword list, baseline/master resume

## Workflow

1. Verify parseability:
   - extract text with a local parser such as `pdftotext`
   - confirm name, contact info, section headers, dates, and bullets appear in
     readable order
2. Verify structural constraints:
   - page count, usually exactly one page for software resumes unless told
     otherwise
   - standard sections such as Summary, Skills, Work Experience, Projects,
     Education
   - required work-history entries are still visible
   - for a requested full one-page resume, run the formatting skill's
     `scripts/resume_page_utilization.py`; a one-page file with excessive empty
     space is not a pass
3. Verify grounded tailoring:
   - compare added keywords against the master resume or source notes
   - flag invented skills, metrics, tools, or project claims
   - prefer "missing evidence" questions over hallucinated bullet strength
   - score evidence sufficiency before approving the artifact:
     - `3 — sufficient`: enough verified, role-relevant evidence for a full page
     - `2 — usable`: credible resume, but one or two targeted answers would
       materially improve density or fit
     - `1 — sparse`: the page cannot be filled well without an evidence interview
     - `0 — blocked`: identity, dates, target, or core experience is unresolved
   - At levels 0–1, fail QA and produce a short evidence questionnaire. At level
     2, pass only if the user accepts the known gaps.
4. Check role keywords:
   - extract exact terms from the JD or target profile
   - group by infrastructure, language/framework, AI/LLM, observability,
     testing, and leadership keywords
   - check coverage in Summary, Skills, Work Experience, and Projects
5. Review readability:
   - avoid cramped typography, tiny margins, unreadable dense bullets, or
     non-standard section names
   - keep older roles compressed but present when continuity matters
   - fail excessive whitespace, font shrinking, and ornamental padding as
     distinct defects; do not trade one for another
6. Produce a short validation report:
   - pass/fail
   - page count
   - parser issues
   - missing required content
   - unsupported claims
   - keyword gaps
   - recommended edits ranked by impact
   - page-utilization metrics and evidence-sufficiency level

## Outputs

- validation summary
- concrete missing keyword or missing-evidence list
- recommended edits
- commands run, if applicable

## Boundaries

- Do not claim a universal ATS score. ATS behavior varies by vendor.
- Do not use online upload checkers for private resumes unless the user
  explicitly approves.
- Keep this skill reusable: no hardcoded personal identifiers, private paths,
  emails, or credentials.
