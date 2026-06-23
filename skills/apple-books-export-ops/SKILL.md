---
name: apple-books-export-ops
description: Explain and run the Apple Books export workflow that turns local Apple Books highlights, notes, and bookmarks into private markdown drafts. Use when a user asks how Apple Books/iBooks import works, where annotations are stored, how to export Apple Books notes, how to reconcile Apple Books drafts into a books source repo, or how Apple Books data feeds a public Books Radar-style site.
metadata:
  memory_tags:
    - domain:books
    - workflow:apple-books-export
    - repo_boundary:tools
    - data_class:private-derived
    - inputs:apple-books
    - outputs:markdown-export
    - risk:high
---

# Apple Books Export Ops

## Purpose

Use this skill to explain or execute a local Apple Books export pipeline:
Apple Books annotations are read from the user's Mac, grouped by book asset ID,
and written as private markdown drafts for later review.

The export is source material, not publication. Raw highlights and notes can be
private and may include long copyrighted excerpts.

## Repo Boundary

- The books source repo owns import scripts, private drafts, and public-ready
  book markdown. In George's current workspace, that repo is `georgesbooks`.
- The public radar repo owns the website, public feed, installable public skill,
  tests, and deployment. In George's current workspace, that repo is
  `books-radar`.
- Do not move raw Apple Books imports into the public radar repo.
- Do not commit generated Apple Books draft markdown unless the user explicitly
  asks and confirms the content has been reviewed for privacy and copyright.

## What The Importer Reads

The importer should copy live SQLite files into a temporary directory before
reading them, because Apple Books may keep the databases locked or in WAL mode.

Typical local data sources on macOS:

- Annotation database: `~/Library/Containers/com.apple.iBooksX/Data/Documents/AEAnnotation/AEAnnotation_v10312011_1727_local.sqlite`
- Library metadata database: `~/Library/Containers/com.apple.iBooksX/Data/Documents/BKLibrary/BKLibrary-1-091020131601.sqlite`
- Synced iCloud Books folder: `~/Library/Mobile Documents/iCloud~com~apple~iBooks/Documents`

Important annotation fields in `ZAEANNOTATION`:

- `ZANNOTATIONASSETID`: book asset ID
- `ZANNOTATIONSELECTEDTEXT`: highlighted text
- `ZANNOTATIONNOTE`: user note
- `ZANNOTATIONREPRESENTATIVETEXT`: nearby context
- `ZANNOTATIONLOCATION`: EPUB/PDF location marker
- `ZANNOTATIONCREATIONDATE` and `ZANNOTATIONMODIFICATIONDATE`: Apple epoch timestamps
- `ZANNOTATIONTYPE`: annotation/bookmark type
- `ZANNOTATIONDELETED`: filter out deleted rows

Useful library metadata fields in `ZBKLIBRARYASSET`:

- `ZASSETID`: book asset ID
- `ZTITLE`: title
- `ZAUTHOR`: author
- `ZGENRE`: genre
- `ZPATH`: local asset path when available

## Run Workflow

1. Locate the books source repo.
   - Prefer a repo that explicitly owns book source notes and Apple Books
     imports.
   - If no repo is obvious, ask the user where to place private export output.
2. Read the repo instructions before running anything.
3. Verify the importer exists, usually:

```sh
node scripts/import-apple-books.mjs --help
```

4. Run the importer from the source repo:

```sh
node scripts/import-apple-books.mjs
```

5. Confirm the output summary:
   - number of non-deleted annotation rows
   - number of books/assets exported
   - number of titles resolved from the Apple Books library database
   - number inferred from synced EPUB text, if supported
   - number still unresolved by asset ID
6. Confirm generated drafts are ignored by git.

## Output Shape

Private draft files should land under a gitignored path like:

```text
imports/apple-books/drafts/
```

Each draft should contain:

- frontmatter marking it as a private Apple Books draft
- title and author if resolved
- Apple Books asset ID
- counts for highlights, notes, and bookmarks
- a public recommendation TODO section
- raw imported highlights/notes/bookmarks below the private warning

The importer may also write a gitignored machine-readable summary under:

```text
imports/apple-books/raw/
```

## Promotion Workflow

To turn an Apple Books draft into public Books Radar content:

1. Open the private draft.
2. Rewrite it into a short public-safe book note.
3. Avoid long direct excerpts from copyrighted books.
4. Remove private thoughts, names, local paths, and account details.
5. Save the reviewed note in the books source repo's public-ready `books/`
   folder.
6. Sync or copy only the reviewed public fields into the public radar repo.
7. Regenerate feeds and run the public app checks.

## Explanation Template

When the user asks what happened, answer in this shape:

```text
Yes. The Apple Books import is a script-based local export.

It reads your Mac's Apple Books annotation SQLite database for highlights,
notes, and bookmarks, joins what it can to the Apple Books library database for
titles/authors, optionally checks synced iCloud EPUB folders for title
inference, and writes one private markdown draft per annotated book.

The generated drafts stay in the books source repo under
imports/apple-books/drafts/ and are gitignored. They are source material for
rewriting public book recommendations, not something to publish directly.
```

## Guardrails

- Treat all Apple Books output as private-derived data.
- Do not print raw highlights or notes into chat unless the user explicitly asks
  for a small excerpt from a specific file.
- Do not quote long copyrighted passages.
- Do not commit generated drafts by default.
- Do not copy Apple Books databases into git-tracked folders.
- Do not assume old annotation asset IDs still map to current library titles;
  Apple Books can retain annotations for books no longer present locally.
