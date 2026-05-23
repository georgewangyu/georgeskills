# Format Runbooks

Use format runbooks for recurring video structures. A runbook should describe how a specific format works without bloating the main skill.

## When To Create One

Create or update a format runbook when:
- a format has repeated across multiple successful videos
- the hook dictates the rest of the edit
- clip classification depends on format-specific cues
- the user provides a script, reference video, or raw process notes for that format

## Suggested Structure

````markdown
# <Format Name> Editing Runbook

## Purpose

What this repeatable format is for and what kind of viewer promise it makes.

## Source Evidence

- raw process note, script, reference video, or performance note
- preserve exact user wording when it explains editorial judgment

## Format Pattern

```text
hook
-> setup
-> beat
-> beat
-> twist / payoff
```

## Clip Roles

- hook / anchor:
- A-roll:
- B-roll:
- proof/detail:
- transition:
- ending / twist:

## Automation Cues

- transcript phrases that identify key moments
- visual cues that identify B-roll or proof clips
- required sound effects, music, captions, overlays, or screenshots
- target pacing and approximate segment durations

## Taste-Heavy Steps

- choices that should stay human-reviewed
- jokes, emotional emphasis, pacing, text wording, final polish

## Minimum Useful Draft

Smallest draft worth generating before human review.
````

## Runbook Placement

Keep user-specific or private format runbooks in the user's private repo. Keep reusable public examples generic.

Useful private-repo locations often look like:
- `<private-repo>/areas/social-media/video/templates/<format-name>-editing-runbook.md`
- `<private-repo>/areas/social-media/video/research/<date>_<format-name>-analysis.md`

## Integration Pattern

When a runbook exists:
1. Load the runbook after reading the user's immediate request.
2. Extract the expected story pattern and clip roles.
3. Classify clips against those roles.
4. Produce the edit decision list with references to the runbook where useful.
5. Record any new format learning back into the private runbook if the user asks for durable capture.
