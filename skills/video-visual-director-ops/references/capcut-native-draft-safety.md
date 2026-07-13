# CapCut Native Draft Safety

Use this low-freedom procedure for every programmatic CapCut timeline mutation.

## Before Writing

1. Fingerprint the creator source graph and leave it read-only.
2. Create a new, unopened, versioned destination draft.
3. Inventory the target's video materials, video tracks, segments, and
   `materials.drafts` entries.
4. Classify every candidate video archetype before cloning it.

Reject an archetype when any of these conditions is true:

- its segment references an id in `materials.drafts`;
- its material has `extra_type_option: 2`;
- its material path contains `Resources/combination`;
- its display name identifies a compound clip.

If the target contains only a compound A-cut, pass an explicit `--source` and
`--archetype-material-id` from a known-good draft with an ordinary overlay.
Never default to the first or only video segment.

An ordinary overlay archetype should have no draft/combination reference, use
an overlay track shape, and resolve to a normal video material. With CapCutBot,
the safe pattern is:

```bash
node <capcutbot>/src/cli.js add-video-overlay <target> <asset> \
  --source <known-good-overlay-draft> \
  --archetype-material-id <ordinary-video-material-id> \
  --start <seconds> --duration <seconds>
```

CapCutBot must reject compound/nested archetypes. Treat that rejection as a
required preflight result, not an error to bypass.

## After Every Mutation Batch

Verify all of the following before exposing the draft in CapCut:

- Only the intentional base A-cut references `materials.drafts`.
- Every inserted segment points to the newly created expected material id.
- Inserted overlay tracks use `flag: 2` and unique ordered
  `track_render_index` values above the base track.
- Every inserted material path is project-local under `capcutbot_media/`.
- Each copied file's SHA-256 matches its accepted source asset.
- Each video has a `local_material_id` registered in both
  `draft_meta_info.json` and `draft_virtual_store.json`.
- Audio materials also use project-local paths; reject volatile cache paths.
- All canonical root and nested graph copies are byte-identical.
- The creator source graph fingerprint is unchanged.

Run the media-index repair in dry-run mode after registration. A clean result
must reuse the expected records and plan zero new registrations.

## Render Proof

Build a deterministic proxy from the locked A-cut and the exact project-local
overlay files before first open. Check representative boundaries, black frames,
audio unity, SFX timing, sponsor disclosure, and source-faithful claims.

The proxy proves media identity and timing, but not CapCut-native text geometry.
Keep the native text/export smoke test explicit when desktop control is not
authorized.

## First Open

Open the generated destination only after all checks pass. Verify overlay
identity at every boundary, native text, disclosure, and audio; save once and
read the graph and media indexes back. Freeze that version after the first
CapCut save. Put any later bot changes in a newly duplicated version.

## Regression Coverage

Maintain both tests in the mutation tool:

1. A target containing only a compound clip must fail without an explicit safe
   cross-draft archetype.
2. The same target must succeed when given a known-good ordinary overlay
   archetype, producing no compound/draft references on the inserted segment.
