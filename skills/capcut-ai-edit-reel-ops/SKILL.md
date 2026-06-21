---
name: capcut-ai-edit-reel-ops
description: Create repeatable list-style short-form reels from an existing CapCut AI-edit template. Use when the user wants to duplicate a proven CapCut project, change only the title/on-screen text, and produce the matching numbered caption or comment copy for TikTok, Instagram Reels, or YouTube Shorts.
memory_tags:
  - domain:social-media
  - workflow:capcut-template-reel
  - repo_boundary:tools
  - outputs:shortform-caption
  - risk:medium
---

# CapCut AI Edit Reel Ops

## Trigger

Use when:
- the user mentions a CapCut AI-edit template, reusable reel template, or
  title-only short-form edit
- the requested video is a list-style reel where the visual template mostly
  stays fixed and only the title/topic changes
- the user needs both the CapCut handoff and the numbered caption/comment copy

Do not use when:
- raw clips need to be selected, trimmed, sequenced, or classified; use
  `shortform-rough-cut-ops`
- the user only wants a hook recommendation; use `social-hook-selection-ops`
- the user wants a full word-for-word spoken script; use
  `shortform-talking-points-ops`

## Inputs

- Required: source template or project name.
- Required: subject/topic for the title.
- Required: five points, or permission to propose five points.
- Optional: target platform, caption length, source material, reference reel,
  target project name, markdown save path, and available CapCutBot/capcut-cli
  commands.

## Core Rule

Preserve the proven edit structure. Change the title and the caption/comment
copy before changing timing, effects, music, captions, or clip structure.

The skill is for high-throughput list reels where the template already works.
Treat CapCut automation as draft plumbing, not taste replacement.

## Workflow

1. Establish the reusable format.
   - Identify the source CapCut template/project.
   - Identify the title overlay that should change.
   - Confirm whether the visual edit should stay otherwise unchanged.
   - If the user has not supplied five points, propose exactly five.
2. Draft the title.
   - Use the default list-reel pattern unless the user gives a stronger title:
     `5 <Subject> I / Wish I Knew Last Year`.
   - For the CapCut title overlay, put the line break after `I`:
     `5 <Subject> I\nWish I Knew Last Year`.
   - For the written reel title, keep it on one line:
     `5 <Subject> I Wish I Knew Last Year`.
   - Normalize user phrasing such as `top five <subject>` into the numeric
     overlay format when it fits the template.
   - Use title case unless the user's reference template uses another casing.
3. Draft the caption/comment block in the fixed format.
   - Use a numbered list from `1.` through `5.`
   - Start each item with the repo/resource name, then a colon, then the
     short rule sentence.
   - Follow each rule with a first-person paragraph that names the mistake,
     pain, or lesson.
   - Keep the voice concrete, candid, and slightly hard-won.
   - Avoid generic motivational advice, vague AI hype, and buzzword-only points.
4. Prepare the CapCut handoff.
   - Close the CapCut project before direct JSON patching. CapCut can overwrite
     local draft edits while a project is open.
   - Inspect the current CapCutBot or editor tool before claiming automation
     support. Prefer commands like:
     - `node src/cli.js env`
     - `node src/cli.js info "<template>"`
     - `node src/cli.js texts "<template>"`
   - When CapCutBot exposes draft duplication and text replacement, run:
     - `node src/cli.js duplicate "<template>" "<new-project>" --dry-run`
     - `node src/cli.js duplicate "<template>" "<new-project>"`
     - `node src/cli.js replace-text "<new-project>" --material-id "<id>" --text $'<new-title>' --dry-run`
     - `node src/cli.js replace-text "<new-project>" --material-id "<id>" --text $'<new-title>'`
   - If duplicate/title-update commands are not available, return manual CapCut
     steps: duplicate the template in CapCut, rename the new project, open the
     title text layer, replace it with the new title, and leave other layers
     unchanged.
5. Review before final.
   - Confirm the title fits the overlay without wrapping awkwardly.
   - Confirm the caption has exactly five numbered items.
   - Confirm the CapCut handoff distinguishes automated steps from manual steps.
6. Save a markdown artifact when the user wants persistence.
   - Prefer the active private/social-media draft area when one exists.
   - Do not save user-specific drafts inside the public reusable skill repo.
   - Include the reel title, CapCut draft/project name, five selected items,
     caption/comment copy, and manual review notes.
   - Follow the destination repo's markdown frontmatter rules when present.

## Title Format

Default overlay title:

```text
5 <Subject> I
Wish I Knew Last Year
```

Default written title:

```text
5 <Subject> I Wish I Knew Last Year
```

Examples:
- `5 AI Skill Repos I\nWish I Knew Last Year`
- `5 Coding Tips I\nWish I Knew Freshman Year`
- `5 AI Tools I\nWish I Knew Last Year`

## Caption Format

Use this shape exactly:

```text
1. [Repo or resource name]: [Short rule sentence].
[First-person lesson paragraph.]

2. [Repo or resource name]: [Short rule sentence].
[First-person lesson paragraph.]

3. [Repo or resource name]: [Short rule sentence].
[First-person lesson paragraph.]

4. [Repo or resource name]: [Short rule sentence].
[First-person lesson paragraph.]

5. [Repo or resource name]: [Short rule sentence].
[First-person lesson paragraph.]
```

Style rules:
- Put the repo/resource name first so viewers can scan the list before reading
  the explanation.
- Make each rule useful without the paragraph.
- Make each paragraph explain what broke, what changed, or what the creator
  learned.
- Use plain language. Avoid making every point start with the same verb.
- Keep claims grounded in the user's actual experience or clearly label them as
  proposed copy.

## Output Contract

Return:

```text
Reel title:
[title]

Caption/comment copy:
1. ...
2. ...
3. ...
4. ...
5. ...

CapCut handoff:
- Source template/project:
- New project name:
- Title overlay to replace:
- Automation path:
- Manual review:

Markdown artifact:
- Path:
- Status:
```

## Guardrails

- Do not hard-code private project names, local filesystem paths, account
  handles, or personal defaults into this skill.
- Do not overwrite a CapCut draft without a backup or dry-run equivalent.
- Do not imply CapCutBot can duplicate projects or edit title text unless the
  current local CLI actually exposes those commands.
- Do not expand the task into a full edit decision list when the user asked for
  a title-only template variant.
