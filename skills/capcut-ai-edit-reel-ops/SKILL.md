---
name: capcut-ai-edit-reel-ops
description: Create repeatable caption-first list Reels from a short B-roll loop or an existing CapCut template. Use when the video only needs to sell one list promise on screen while the detailed numbered payoff lives in the Instagram, TikTok, or YouTube caption; when the creator wants a low-lift 6-10 second Reel built from ordinary laptop, desk, phone, walking, or working footage; or when an existing title-only short-form template should be duplicated and retitled.
memory_tags:
  - domain:social-media
  - workflow:capcut-template-reel
  - skill_role:generator
  - repo_boundary:tools
  - outputs:shortform-caption
  - risk:medium
---

# Caption-First List Reel Ops

## Trigger

Use when:
- the user mentions a reusable list Reel, low-lift template Reel, caption-first
  Reel, or title-only short-form edit
- the requested video is a 6-10 second loop where one hook/title stays on
  screen while its typography or B-roll refreshes
- the numbered tips, tools, lessons, or mistakes belong in the platform
  caption rather than as five separate video scenes
- the creator wants to reuse an ordinary laptop, desk, phone, walking, or
  working clip instead of filming a spoken story
- an existing CapCut project should be duplicated and retitled

Do not use when:
- a long raw session needs story selection or a spoken A-cut; use
  `shortform-rough-cut-ops`
- the user only wants a hook recommendation; use `social-hook-selection-ops`
- the user wants a full word-for-word spoken script; use
  `shortform-talking-points-ops`
- each list item needs its own scene, proof asset, or voiceover beat; this
  format intentionally keeps the video simple and moves the payoff to the
  caption

## Inputs

- Required: source clip, source template, or project name.
- Required: subject and list promise for the on-screen title.
- Required: numbered payoff points, or permission to propose them.
- Optional: credibility qualifier, target platform, desired list length,
  source material, reference Reel, target project name, markdown save path,
  music choice, and available CapCutBot/capcut-cli commands.

## Core Rule

The video earns the caption read; the platform caption delivers the value.
Keep one legible promise on screen for the entire loop. Use small visual or
typographic refreshes to reset attention without making the viewer parse new
information every second.

Preserve a proven edit structure when one exists. Change the title and
caption copy before changing timing, music, effects, or clip structure.
Treat editor automation as draft plumbing, not taste replacement.

## Workflow

1. Choose the production mode.
   - Use `fresh-broll-loop` when the creator supplied one useful continuous
     clip.
   - Use `existing-template` when a proven CapCut or editor project already
     contains the timing and title treatments.
   - Prefer `existing-template` or a native CapCut finishing pass when a
     creator's recognizable result depends on editor-native text animation,
     music, filters, color, or retouch. A programmatic render can still be a
     structural prototype, but it is not the creator-finished deliverable.
   - Do not require CapCut for `fresh-broll-loop`; Instagram's native editor
     or another editor is acceptable when it can preserve the text timing.
2. Select the source range.
   - Prefer a 7-10 second vertical range with the creator visibly doing
     something ordinary: typing, looking at a laptop, checking a phone,
     walking, drinking water, or moving an object.
   - Score the first, middle, and final frames before locking the range.
     Prefer one bounded physical state change in the first 1-2 seconds, such
     as opening or closing a laptop, picking up or setting down a phone,
     reaching for an object, sitting down, or looking up.
   - Use ambient micro-movement only when no clean physical action preserves
     the title safe zone. Do not begin after the useful action has already
     happened merely because the remaining range is stable.
   - Favor a readable physical action and loopable ending over a dramatic
     scene.
   - Keep the face or human presence visible when possible, but reserve a
     stable center or lower-middle area for the title.
   - Avoid ranges that require dialogue or source audio to make sense.
3. Draft the on-screen promise.
   - State the number, subject, and personal stakes immediately.
   - Prefer one of these shapes unless the user gives a stronger title:
     - `<Number> <tips/lessons/mistakes> I'd kill to tell my <past self>.`
     - `<Number> <things> I wish I knew <time/identity marker>.`
   - Add one short credibility qualifier only when it makes the promise more
     believable, such as `(after shipping my first production app)`.
   - Keep the wording fixed across all visual refreshes. Restyle the same
     promise; do not reveal a different tip on each beat.
4. Build the visual loop.
   - Target 6-10 seconds total.
   - Show the full promise within the first second.
   - Keep the title in a control-safe area and off the creator's eyes, mouth,
     hands, and important props.
   - Refresh attention every 0.8-1.4 seconds with one lightweight change:
     typography, scale, line break, looped font animation, crop, or a cut to a
     second moment from the same session.
   - When a proven editor-native loop can generate the refresh rhythm, prefer
     one consistent animation treatment across the title, qualifier, and CTA
     over manually constructing several unrelated typography systems.
   - Aim for 3-5 perceptible refreshes, not 3-5 unrelated visual systems. One
     looping treatment may supply several refreshes.
   - Add `read caption` or an equivalent accurate CTA for the final 1-2
     seconds when the payoff is in the post caption.
   - Let creator-owned or separately licensed music provide rhythm. Use
     platform-native music only through the licensing platform and account,
     and only for the publication, territory, and use its current terms permit;
     otherwise use separately licensed music or no music. In every case, make
     the format understandable while muted.
5. Draft the caption/comment block.
   - Match the list length promised on screen.
   - Start each item with a scannable point, resource, or lesson label, then a
     colon, then the short rule sentence.
   - Follow each rule with a first-person paragraph that names the mistake,
     pain, or lesson.
   - Keep the voice concrete, candid, and slightly hard-won.
   - Avoid generic motivational advice, vague AI hype, and buzzword-only points.
6. Prepare the editor handoff.
   - For `fresh-broll-loop`, return the exact source range, target duration,
     title text, qualifier, CTA, and timed treatment sequence. When using
     Instagram's native editor, add the title layers manually and verify their
     durations before review. Treat the result as a draft; do not publish or
     schedule it without the user's explicit approval of the exact final media
     and copy.
   - For `existing-template`, close the CapCut project before direct JSON
     patching. CapCut can overwrite local draft edits while a project is open.
   - Resolve a new, uniquely named destination before duplicating. If the
     destination already exists, stop instead of overwriting or reusing it.
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
   - Before the non-dry-run text mutation, require a recoverable, timestamped
     backup or a verified tool-native backup receipt for the new destination.
     If neither is available, return manual steps instead of mutating JSON.
   - If duplicate/title-update commands are not available, return manual CapCut
     steps: duplicate the template in CapCut to a unique new project, confirm
     there is no same-name collision, rename it, open the title text layer,
     replace it with the new title, and leave other layers unchanged.
   - When the creator has a trusted CapCut finishing stack, apply it only
     after the source range and text are locked. Copy or duplicate the
     verified native filter, color, and retouch stack; do not reconstruct it
     by eye. Read back native names, intensities, ordering, and dependencies,
     then compare the export with the accepted reference.
   - Keep exact creator preset values in the private preset registry or project
     receipt, not in this reusable skill.
   - Outside CapCut, do not imitate a creator's retouch or finishing preset
     unless a portable LUT/preset and reference export were supplied. Return a
     neutral structural draft or hand the locked edit back to CapCut.
7. Review before final.
   - Confirm every title treatment is readable on a phone without pausing.
   - Confirm the title remains semantically identical across treatments.
   - Confirm the CTA points to the actual payoff location.
   - Confirm the caption item count matches the on-screen number.
   - Confirm the loop works muted and has no dead opening or ending frame.
   - Confirm the source range contains a visible state change when a suitable
     one exists in the supplied clip.
   - Confirm any claimed creator finishing preset came from a verified native
     draft rather than visual guesswork.
   - Confirm the editor handoff distinguishes automated steps from manual
     steps.
8. Save a markdown artifact when the user wants persistence.
   - Prefer the active private/social-media draft area when one exists.
   - Do not save user-specific drafts inside the public reusable skill repo.
   - Include the production mode, source range, Reel title, editor project
     name, timed text treatments, selected list items, caption/comment copy,
     and manual review notes.
   - Follow the destination repo's markdown frontmatter rules when present.

## Title Format

Default overlay patterns:

```text
5 <Subject> I'd Kill to Tell My
<Past Self>

5 <Subject> I Wish I Knew
<Time or Identity Marker>
```

Default credibility qualifier:

```text
(after <specific experience>)
```

Examples:
- `5 Coding Lessons I'd Kill to Tell My Intern Self`
- `5 AI Workflow Mistakes I Wish I Knew Before Shipping`
- `7 Agent Skills I Wish I Had Last Year`

## Caption Format

Repeat this shape until the numbered item count matches the on-screen promise:

```text
1. [Point, resource, or lesson]: [Short rule sentence].
[First-person lesson paragraph.]

2. [Point, resource, or lesson]: [Short rule sentence].
[First-person lesson paragraph.]

...

N. [Point, resource, or lesson]: [Short rule sentence].
[First-person lesson paragraph.]
```

Style rules:
- Put a concrete label first so viewers can scan the list before reading the
  explanation.
- Make each rule useful without the paragraph.
- Make each paragraph explain what broke, what changed, or what the creator
  learned.
- Use plain language. Avoid making every point start with the same verb.
- Keep claims grounded in the user's actual experience or clearly label them as
  proposed copy.

## Output Contract

Return:

```text
Production mode:
[fresh-broll-loop | existing-template]

Source:
- Clip/template:
- Selected range:
- Target duration:

Reel title:
[title]

On-screen sequence:
- 0.0-...:
- ...

Caption/comment copy:
1. ...
2. ...
...
N. ...

Editor handoff:
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
- Do not force a five-item list when the on-screen promise uses another number.
- Do not put all detailed list items on screen in this format; the caption is
  the intended payoff surface.
- Do not label a CTA `read bio` when the value is actually in the post caption.
- Do not rely on source audio or dialogue to explain the Reel.
- Do not post, upload, schedule, or publish the Reel without the user's
  explicit approval of the exact final media and copy.
- Do not overwrite a CapCut draft without a backup or dry-run equivalent.
- Do not imply CapCutBot can duplicate projects or edit title text unless the
  current local CLI actually exposes those commands.
- Do not expand the task into a full edit decision list when the user asked for
  a title-only template variant.
