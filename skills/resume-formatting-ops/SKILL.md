---
name: resume-formatting-ops
description: Use when a resume needs formatting, LaTeX/PDF build cleanup, one-page fit, ATS parseability, or final submission QA without changing role targeting strategy.
memory_tags:
  - domain:resume
  - workflow:formatting
  - skill_role:operator
  - repo_boundary:tools
  - data_class:private-derived
  - risk:medium
---

# Resume Formatting Ops

## Trigger

Use when:
- the user asks to fix resume formatting, spacing, margins, typography, layout, or one-page fit
- a resume `.tex`, `.pdf`, `.docx`, or parsed text artifact needs final submission QA
- a role-tailored resume is ready for build, ATS parseability, and visual cleanup

Do not use when:
- the main task is deciding what content belongs in the resume for a specific company or role; use `resume-role-tailoring-ops` first
- the user asks for broad career strategy rather than a concrete resume artifact

## Inputs

- Required: resume source path or enough context to locate one
- Optional: target output format, target page count, existing validation script, style constraints, submission portal constraints

## Workflow

1. Locate the resume root and read local instructions before editing.
   - In a private repo, check the nearest resume `AGENT-*.md`, `README.md`, variant strategy, and build workflow.
   - Keep private paths and personal details out of reusable skill files and public docs.
2. Identify the source of truth.
   - Prefer structured source (`.tex`, YAML/JSON resume data, or canonical document source) over editing generated PDFs.
   - If only PDF/DOCX exists, extract text first and decide whether conversion is needed.
3. Make formatting-only edits unless the user explicitly asks for content rewrites.
   - Safe edits: margins, spacing, line breaks, section ordering for layout, font sizing, bullet wrapping, link formatting, filename consistency.
   - Preserve and normalize selective bolding for scan-critical metrics and ATS keywords when the local resume style uses bold emphasis.
   - Avoid inflating claims, changing metrics, or adding skills during this pass.
4. Build using the repo's deterministic path.
   - Prefer local build scripts if present.
   - Otherwise use reusable helpers such as `skills/utility-ops/scripts/build_resume_pdf.py` for LaTeX sources.
5. Run parseability checks.
   - `pdfinfo <resume.pdf>`: confirm page count.
   - `pdftotext <resume.pdf> -`: confirm section order, names, dates, skills, and links parse in a sane reading order.
   - If a repo-specific validator exists, run it.
6. Run visual QA when layout risk is nontrivial.
   - Inspect the generated PDF screenshot or render.
   - Check for clipped text, overfull lines, orphaned bullets, excessive whitespace, tiny fonts, and inconsistent alignment.
7. Report the final artifact and exact checks.

## Formatting Heuristics

- ATS-friendly resumes should favor one-column or simple two-column layouts with extractable text and standard headings.
- Keep headings conventional: Summary, Work Experience, Technical Projects, Education, Skills.
- Preserve real hyperlinks where the source format supports them.
- Use bold emphasis sparingly for concrete metrics and role-critical keywords; avoid bolding full bullets or generic filler.
- Avoid icons, text boxes, image-only text, dense tables, and absolute-positioned layout if ATS parseability matters.
- For software engineering resumes, content density is useful, but do not solve overflow by making text unreasonably small.

## Open-Source Patterns Worth Borrowing

- `rendercv/rendercv`: strict resumes-as-code generation and reproducible PDF output.
- `amruthpillai/reactive-resume`: privacy-first resume management and export discipline.
- `xitanggg/open-resume`: parser-first thinking; validate what the PDF turns into when machines read it.
- `srbhr/Resume-Matcher`: final resume scoring, keyword highlighting, and template/export QA as separate passes.

## Outputs

- Updated source resume, if edits were needed
- Built PDF or requested output artifact
- Concise QA notes: page count, parser sanity, visual risks, commands run, and remaining submission risks

## Boundaries

- Public specs live in `liferepo`.
- Private resume sources and company variants live in `<private-repo>`.
- Reusable build/conversion tools live in `georgeskills`.
- Keep this skill reusable: no hardcoded personal handles, emails, account ids, credentials, or user-specific defaults.
