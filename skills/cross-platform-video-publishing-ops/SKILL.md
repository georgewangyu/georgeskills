---
name: cross-platform-video-publishing-ops
description: Prepare a reviewable pre-posting packet or publish an approved video across a creator-defined platform set with account verification, platform-specific routing, compression-survival QA, final-click authorization, and durable live proof. Use when the creator says post, publish, release, upload, schedule, or post on all platforms; asks to preserve Instagram upload quality; when TikTok must be published through TikTok Studio instead of an API inbox transfer; or when Xiaohongshu must be published through the canonical RedNote website.
metadata:
  memory_tags:
    - domain:social-media
    - workflow:cross-platform-publishing
    - skill_role:operator
    - repo_boundary:tools
    - outputs:publication-receipts
    - risk:high
---

# Cross-Platform Video Publishing Ops

## Purpose

Publish one approved video to a creator-defined destination set without
confusing an upload, draft, inbox transfer, or prefilled composer with a live
post. Keep platform mechanics reusable; load private handles, destination
membership, copy defaults, and standing authorization from an injected creator
profile.

## Pre-posting preparation

When asked to prepare a post or establish its pre-posting procedure, use
[pre-posting-checklist.md](references/pre-posting-checklist.md). Produce the
caption, verified resource mapping, conditional delivery draft, and exact-asset
approval handoff before release. Preparation does not authorize upload,
activation, test messages, or publication. Reuse the creator's established
campaign through `manychat-automation-ops` only when fulfillment requires it.

## Required Inputs

- exact master path and SHA-256
- approved copy, plus any approved platform-specific variants
- creator publishing profile containing:
  - destination set for shorthand such as `post on all platforms`
  - format-specific destination sets when short-form, horizontal long-form,
    or another delivery class has different membership
  - whether a bare `post`, `publish`, `release`, or `upload` cue for a resolved
    delivery class selects that class's default destination set
  - expected account identity per destination
  - preferred and fallback route per destination
  - expected session state when known
  - whether the creator has granted standing authorization for final Publish
    or Post actions
  - private creator-owned or project-owned path for release receipts
- disclosure, rights, audience, timing, and cover choices required by each
  destination
- explicitly requested or approved Instagram collaborator usernames, if any;
  collaborator selection is separate from destination-set authorization
- for a comment-keyword resource promise, the verified resource destination,
  fulfillment channel, campaign owner and readiness state

Do not embed a creator's real handles, private URLs, or private filesystem paths
in this skill.

## Release Contract

1. Resolve the media's delivery class from the approved artifact and brief,
   then resolve shorthand through the matching format-specific creator
   profile. When that profile explicitly declares a default destination set for
   a bare release cue, `post`, `publish`, `release`, or `upload` plus the
   resolved format selects that set without requiring the creator to repeat
   `all platforms`.
   An explicit destination addition, exclusion, or list in the current request
   overrides the default. Do not guess which platforms `all platforms`
   includes, and do not assume one universal set covers both short-form and
   horizontal long-form.
2. Fingerprint the master before the first upload. Every destination must
   receive that exact file unless the creator approved a platform-specific
   derivative.
3. Verify the visible or API-returned account identity before upload or final
   submission.
4. If the creator profile grants standing final-publish authorization for the
   resolved destination set, or the creator explicitly says to post/publish the
   resolved artifact to that set in the current conversation, continue through
   every final Publish/Post action without asking for a redundant workflow-level
   confirmation or pausing between platforms. A tool- or system-enforced
   confirmation boundary still applies when present. Otherwise stop at the
   profile's approval boundary.
5. Respect required disclosures and music, rights, audience, and policy
   warnings. Standing authorization does not authorize inventing answers.
6. Record each destination independently as `published`, `scheduled`,
   `processing`, `under_review`, `staged`, or `failed`.

## Comment-Keyword Campaign Readiness

Before the first platform upload, check the video and caption for a comment
CTA and load the creator profile’s automation readiness policy. When either
promises a resource, finish fulfillment preparation first, including for
`post on all platforms`. Load the existing `manychat-automation-ops` skill for ManyChat
campaigns rather than creating a second automation skill.

Before release, verify the public resource and inspect the connected account,
channel, existing triggers and other responding providers. Prepare the exact
matching mode, public replies, email request, follow request, delivery links
and follow-up, plus an opening DM/button only if selected in the source flow
or explicitly requested. Preserve the creator's approved options. Keep
email collection purpose explicit; a resource request does not establish
newsletter or marketing consent. Verify every link in the saved configuration
or preview. If the UI cannot persist an inactive draft, save the exact setup
privately and report `preview-only`, not `saved` or `live`.

When the target post does not yet exist and the creator explicitly selects
next-post preparation, configure that scope before uploading. Inspect existing
next-post campaigns, provider overlap, exact delivery copy and links; only one
next-post campaign can be active. Activate before publication only when the
creator has authorized that exact campaign, copy and next-post scope. Otherwise
keep the prepared draft inactive. Do not replace another active reservation or
use any-post targeting as a shortcut. After publication, verify that the
automation bound to the exact new post; repair a mismatch only within approved
scope. When specific-post targeting is selected instead, prepare inactive, then
bind and activate after the exact post ID exists.
Video publication authorization alone does not authorize DMs, test sends,
retrospective replies or changes to another live campaign.

Apply the keyword promise only to channels with verified fulfillment. Use an
approved direct-resource link or explicit route to the supported channel on
other destinations. Hold the affected promise when fulfillment is unavailable;
do not silently publish an unsupported `comment for the resource` claim.
Record resource URL, keyword, account/channel, provider overlap, campaign ID,
target post and truthful draft/live/delivery state in the private release
receipt. Preview and activation are separate from delivery proof.

## Route Selection

Use the profile's primary route. A fallback does not become the new default
merely because it can accept a file.

Check the configured publishing API and its required media-hosting route before
opening a browser composer. Use that API when it can complete publication and
return durable proof. A missing account in an unrelated connector, an old
failure receipt, or convenience does not prove the configured API is unavailable.
For Instagram, use the profile's official publishing client and verify its
account plus current hosting capability before considering a browser fallback.
Record the exact current API limitation or failure that requires browser use.

### TikTok

The default creator-UI route is TikTok Studio:

`https://www.tiktok.com/tiktokstudio/upload?lang=en`

- Open TikTok Studio in the creator-controlled browser session and verify the
  expected account before uploading.
- Do not start with a TikTok API creator-inbox or `MEDIA_UPLOAD` transfer when
  the profile selects Studio. Such transfers are fallback staging routes and
  never constitute a published TikTok.
- Upload the exact master, set the exact caption, choose the intended cover,
  audience, timing, and disclosure settings, wait for upload checks to finish,
  and invoke Post when authorized.
- For reactive web editors, enter caption text with normal click, Select All,
  Delete, and typing actions when direct accessibility-value injection does not
  trigger the editor's state updates. Perform Select All while the original
  caption is still one clean text run; after hashtags become tokenized spans,
  partial accessibility selection can duplicate hidden text. If an edit becomes
  malformed, cancel the unsaved edit, reopen the clean server state, and replace
  it once rather than stacking corrective typing.
- After posting, reload or open the published item and verify account,
  visibility, caption, and durable video URL or ID.
- If TikTok substituted the filename for the caption, edit the post immediately
  through Studio, save it, and read the creator-list result. TikTok may place a
  caption edit under review and keep the old public page cached; record
  `edits_saved`, intended visibility, creator-list caption, review state, and the
  stale public readback separately. Do not spend the platform's once-per-day
  caption edit on repeated retries or report the cached filename as corrected.
- Use an API creator-inbox fallback only after the Studio route is observably
  unavailable or the creator explicitly requests it. Report the result as
  `staged` until a final post and public readback occur.

### Xiaohongshu / RedNote

Use the canonical RedNote website:

`https://www.rednote.com/`

- Do not route routine RedNote publishing through `creator.rednote.com` or
  `creator.xiaohongshu.com`.
- Reuse the creator's normal persistent browser profile and its existing
  `rednote.com` session. Do not open an Incognito window, temporary profile, or
  automation-owned profile for routine RedNote publishing, because those
  contexts discard or isolate the login cookies.
- When a signed-in `rednote.com` tab exists, continue from that same browser
  profile at the canonical URL above and use the publishing flow exposed there.
  Do not infer that a session on either creator subdomain represents the
  canonical RedNote session.
- Load the creator-controlled browser session and verify the expected visible
  account. If the profile says the session is expected to be active, do not ask
  the creator to log in unless the page actually presents a login or expired-
  session state.
- If RedNote presents a login, preserve the existing tab and
  ask the creator to complete the platform's SMS or QR verification there.
  Never bypass the verification, copy authentication material into a skill, or
  promise that a platform-issued session will remain valid indefinitely.
- After successful authentication, continue in that same profile and tab when
  practical. Record the canonical RedNote route in the receipt so future runs
  do not regress to either creator subdomain.
- Upload the exact master, enter the platform-appropriate title and body within
  visible limits, set audience/timing/disclosures, and invoke Publish when
  authorized.
- Require the success screen, creator-content list, or durable post identifier
  before marking the destination `published` or `under_review`.

### Other Destinations

- Prefer a verified official API when it can complete publication and return a
  durable post ID or URL.
- Use the creator UI when the API can only stage media, omits required controls,
  or the profile explicitly selects the UI.
- Treat platform review or processing honestly. A successful submission may be
  `under_review` or `processing`, not yet publicly visible.
- For an X video that exceeds the current API media limit or is too long for a
  useful native post, do not solve the problem by crushing the complete master
  below the byte ceiling. When the creator profile authorizes a long-form X
  fallback, read [x-longform-trailer.md](references/x-longform-trailer.md) and
  build a coherent, separately approved excerpt or trailer with an end CTA to
  the full YouTube video. X has no durable private/unlisted media-processing
  state in the normal post API, so media upload and public post remain one
  release action; preparation is local until final authorization.
- Clean up only the exact immutable temporary-hosting object created by the
  current run, after verifying that the destination has safely ingested it,
  the platform route no longer depends on it, and the operator owns that exact
  object. Never delete the local master, a creator-owned source, a container,
  or a path prefix. Stop when the target identity or ownership is ambiguous,
  and record the exact object and deletion result in the private release
  receipt.

### Instagram Compression Survival

When Instagram delivery quality matters, read
[compression-survival.md](references/compression-survival.md) before upload.
Use one clean, route-compliant master, verify that the ingest URL serves the
exact intended bytes, and measure at least one delivered rendition after
publication. Do not claim that API publishing bypasses Instagram compression;
the goal is to give Instagram's encoder the strongest compatible source and
avoid any avoidable lossy generation before ingestion.

### Instagram Collaborators

Read this section when a collaborator is explicitly requested or approved.
`Post on all platforms` selects destinations; it does not authorize collaborator
invitations. A relevant topic may justify suggesting a collaborator under the
creator profile, but wait for approval before including one. Omit collaborators
for ordinary releases.

Resolve the exact usernames through the private creator profile and current
profile readback. Verify the publishing account independently. For a Reel,
use the official API container's `collaborators` array through the configured
client. With IGBot:

```bash
node src/cli.js video '<public-master-url>' \
  --caption '<approved-caption>' \
  --collaborators 'examplecreator'
```

The flag accepts up to three unique usernames. Create the container, wait for
`FINISHED`, then publish the same container under the existing release
authorization. Preserve the exact-master hosting and cleanup workflow.
Do not substitute a caption mention or user tag for a collaboration invite.
If Meta rejects the requested collaboration, report the specific error rather
than silently publishing without it or creating a replacement post.

Read back the published Reel and capture the requested usernames plus invitation
state. Publication and acceptance are separate: `invited-pending-acceptance`
is successful invitation proof, not proof that the post appears on both
profiles. Accepting from another account requires authorization for that
account and a supported, account-verified route; do not infer it from the
original publish request. Record these fields in the private release receipt.
This is an Instagram-specific option; other destinations keep their configured
routes and are not assigned the same collaborator automatically.

Re-check the current [Meta media-container reference](https://developers.facebook.com/documentation/instagram-platform/instagram-graph-api/reference/ig-user/media/)
before using a new publishing feature. Stories do not support collaborators.

## Browser Control

Use the approved creator-controlled browser surface. Reuse an existing signed-
in tab when practical. Do not use an automation-owned browser or a forbidden
browser framework merely to bypass the creator session.
Honor the profile's required fallback browser. If that browser presents an
expired or missing login, preserve it for the creator to sign in; do not switch
to another browser without explicit creator authorization.

Before the final click, re-read the visible account, media preview, caption,
audience, timing, and disclosure state. When the UI changes after upload, take a
fresh state snapshot rather than acting from stale coordinates.

## Proof Gate

An upload response is not publication proof.

Mark a destination `published` only with at least one durable artifact:

- public post URL
- platform post/video ID plus a successful readback
- visible creator-content entry that matches the account, caption, and media

For `scheduled`, capture the platform ID and scheduled time. For
`under_review` or `processing`, capture the platform ID or creator-list entry
and its exact state. For `staged`, name the draft or inbox transfer and the
remaining final action.

If the creator explicitly waives an additional public-page verification pass
after every destination has already accepted the release, stop polling. The
waiver removes only the secondary readback: retain the durable submission/post
ID and last truthful per-platform state, keep `under_review` or `processing`
where applicable, and never upgrade a staged upload or draft to `published`.

## Post-release editing-history closeout

After completing the authorized destination set, update editing history before
reporting release closeout. Also perform this checkpoint after a partial or
blocked release attempt so review, failure and staged states are not lost.
Do not wait for every platform to become public or call partial release complete.

When the creator profile supplies a private history root, invoke
`video-edit-history-ops`. Update the existing per-video record, its index row
and the project-side `AI_EDIT_HISTORY.md` together. Create a missing record only
from inspectable project/edit evidence; filenames and publication alone cannot
supply editing lessons. Reuse the canonical record for a repost; give a separately
reviewed derivative its own entry only when its edit warrants one.

Link the released master and hash, release receipt, per-destination actual
state and post identifiers, creator corrections and rejected passes, editing
choices/tool outcomes, and unresolved review or rights limitations. Separate
observations, creator feedback and candidate lessons. Unknown learning evidence
stays unknown; release is not proof of performance or approval of rejected edits.

Run the history validator and project reconciliation. Repair scoped pointer or
index issues from evidence; preserve and report remaining validation gaps rather
than fabricate feedback. Record history capture paths and check results in the
private release receipt. Missing history configuration or unavailable storage
is `history_pending`; it does not justify an invented repository or another
publication. Report platform release and history closeout as separate outcomes.

## Output Contract

Return and persist a release receipt only at the injected private creator-owned
or project-owned receipt path. Never store account-scoped receipts, local
paths, approved copy, account identities, or post identifiers in this skill
package or another public repository. The receipt must contain:

- master path and SHA-256
- exact copy used per destination
- resolved delivery class and destination-profile name
- expected and verified account identity
- route used, including any fallback reason
- final state per destination
- durable URL or platform ID when available
- submission/readback time
- editing-history record, index and project-pointer paths, closeout state and validation results when history is configured
- remaining review, processing, correction, or cleanup work
- comment-keyword fulfillment readiness and post-binding/activation evidence,
  when applicable

Never collapse partial platform results into a single `posted everywhere`
claim.
