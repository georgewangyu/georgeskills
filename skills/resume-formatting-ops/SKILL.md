---
name: resume-formatting-ops
description: Use when a resume needs formatting, LaTeX/PDF build cleanup, evidence-dense one-page fit, ATS parseability, page-utilization measurement, or final submission QA without changing role targeting strategy.
metadata:
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

For an end-to-end request to create, fix, shorten, or redesign a resume, start
with `resume-creation-ops`; this skill owns its document-build and page-fit phase.

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
   - If the page is underfilled, hand back to `resume-role-tailoring-ops` for
     evidence selection or intake. Do not disguise missing content with large
     gaps, decorative elements, or exaggerated spacing.
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
7. Enforce the one-page utilization gate.
   - Run `scripts/resume_page_utilization.py <resume.pdf>`.
   - Treat the default gate as a failure when the visible content spans less
     than 80% of page height, bottom whitespace exceeds 1.25 inches, or content
     crowds within 0.35 inches of the bottom edge.
   - These are defaults, not permission to pad. Prefer relevant source evidence
     first, then balanced section/bullet spacing, then small typography changes.
   - Manually confirm body text is normally at least 9.5 pt, headings are
     legible, and margins are normally at least 0.45 inches.
8. Report the final artifact and exact checks.

## Formatting Heuristics

- ATS-friendly resumes should favor one-column or simple two-column layouts with extractable text and standard headings.
- Keep headings conventional: Summary, Work Experience, Technical Projects, Education, Skills.
- Preserve real hyperlinks where the source format supports them.
- Use bold emphasis sparingly for concrete metrics and role-critical keywords; avoid bolding full bullets or generic filler.
- Avoid icons, text boxes, image-only text, dense tables, and absolute-positioned layout if ATS parseability matters.
- For software engineering resumes, content density is useful, but do not solve overflow by making text unreasonably small.
- "One page" is not satisfied merely by having a one-page PDF. A submission
  should look intentionally full: normally 80–92% vertical content span with a
  readable bottom margin.
- Fill in this order: strongest role-relevant evidence from the source; concise
  projects/publications/awards that improve screening; balanced spacing; minor
  font adjustment. Never fill with duplicated bullets, generic summaries, or
  unsupported claims.
- If there is not enough relevant evidence to fill the page at readable sizes,
  stop and return an evidence-intake request rather than stretching whitespace.

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
