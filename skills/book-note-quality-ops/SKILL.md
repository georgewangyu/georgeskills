---
name: book-note-quality-ops
description: Evaluate and improve public-ready book recommendation notes before they are published to a catalog, reading radar, newsletter, or agent skill. Use when checking whether a book summary, recommendation rationale, reader fit, personal-note synthesis, or copyable markdown is substantive, public-safe, and distinct from raw import metadata.
memory_tags:
  - domain:books
  - workflow:public-note-quality
  - repo_boundary:tools
  - inputs:markdown
  - outputs:quality-audit
  - risk:medium
---

# Book Note Quality Ops

## Trigger

Use when:
- evaluating public-ready book recommendation markdown
- deciding whether imported/private reading notes are ready for publication
- checking a book catalog, reading radar, newsletter, or agent skill for thin or generic book descriptions
- rewriting a book note after a user says the summary, recommendation, or notes are not good enough

Do not use when:
- the user wants raw Apple Books/iBooks extraction; use the Apple Books export skill
- the user asks for a full literary review, school essay, or exhaustive book report
- the task requires quoting long copyrighted passages

## Inputs

- Required: one or more book note drafts, generated catalog records, or rendered page excerpts.
- Optional: private source notes, import summaries, desired audience, catalog style, and target output format.

## Public Note Contract

Each public book note should contain separate layers:

1. **Book summary**: what the book is about, in plain language, without explaining why it was imported.
2. **Recommendation lens**: why this reader or curator thinks the book matters.
3. **Reader fit**: who should read it and what problem, taste, or context it serves.
4. **Personal-note synthesis**: what the source notes or highlights suggest mattered, paraphrased safely.
5. **Next action**: one concrete way to read, revisit, compare, or apply the book.
6. **Copyable markdown**: includes the same canonical sections and is not a separate stale summary.

## Quality Rubric

Score each note `pass`, `revise`, or `block`.

Pass only if:
- the summary is specific enough to distinguish the book from nearby books
- the recommendation lens is not just "I highlighted this a lot"
- personal-note synthesis is paraphrased and public-safe
- the note avoids raw import language such as annotation counts, private draft markers, asset IDs, and local paths
- sections are consistent between the source markdown, generated catalog data, and copyable markdown
- the note says something a reader could act on

Revise if:
- the summary is accurate but generic
- the recommendation lens repeats the summary
- notes are useful but too abstract
- the copyable markdown is missing a section or has stale wording

Block if:
- raw private notes, long copyrighted excerpts, account details, local paths, or credentials appear
- the title/author is uncertain but presented as confirmed
- the public page describes import mechanics instead of the book
- the recommendation relies mainly on private counts or metadata

## Review Workflow

1. Identify the source layer:
   - raw/private import
   - reviewed public markdown
   - generated JSON/catalog record
   - rendered public page
2. Check the section contract:
   - Summary
   - Why/recommendation lens
   - Best for/reader fit
   - Notes/personal synthesis
   - Next action
   - Copyable markdown
3. Flag public-safety issues:
   - import metadata
   - raw quotes
   - private notes
   - local paths, credentials, email addresses, account IDs
   - uncertain metadata presented as fact
4. Evaluate substance:
   - Does the summary explain the book's core argument, story, or premise?
   - Does the recommendation explain the curator's lens?
   - Do the notes add specific, non-generic reading value?
   - Is the next action concrete?
5. Return a compact audit and, when asked, a revised public-safe version.

## Output Contract

For each note, return:

```text
Status: pass | revise | block
Main issue: <one sentence>
Fixes:
- <specific edit>
- <specific edit>
Public-safety concerns:
- none | <concern>
```

When rewriting, return only public-ready text unless the user asks for an audit
table. Do not include raw source excerpts in the rewritten note.

## Boundaries

- Keep raw highlights and private notes out of public output.
- Do not mention import counts, annotation counts, asset IDs, or draft mechanics in public recommendation copy.
- If private source material is used, synthesize patterns rather than quoting it.
- Keep this skill reusable: no hardcoded personal handles, private repo names, account IDs, local paths, or user-specific defaults.
