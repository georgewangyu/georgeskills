# X Long-Form Trailer Fallback

Use this only when the destination profile includes X and the approved
long-form master exceeds X's current media byte/duration constraints or is a
poor fit as a complete native post. Verify current limits from an authoritative
surface at execution time; numeric limits can change.

## Boundary

An X trailer is a separately approved derivative, not a lower-quality copy of
the master and not an upload-staging trick. The normal X post API does not
provide a durable private or unlisted media-only state: uploading and
processing the video culminates in a public post. Keep preparation local until
the creator has authorized the exact derivative and copy.

Before building it, require:

- verified target-account identity for the actual write credentials;
- the exact approved long-form source and rights-cleared audio identity;
- the intended full-video YouTube URL;
- the current X media constraints;
- creator approval or an injected standing rule authorizing this derivative.

If the authoritative YouTube upload contains an in-platform soundtrack
replacement that the local master does not contain, stop. Do not derive the X
version from the stale local soundtrack or from a compressed social download.

## Editorial Shape

Choose a coherent excerpt or trailer that stands on its own:

1. Preserve the hook and enough setup to make the problem legible.
2. Include one representative proof/action passage and a truthful partial
   payoff; do not end mid-sentence or imply the complete story is present.
3. End with a short lower-safe-area CTA such as `Watch the full video on
   YouTube` for roughly `2–3s`. Keep it clear of burned captions and faces.
4. Put the full YouTube link in the X post copy or a reply according to the
   creator's current X-link policy. Do not bake a long unreadable URL into the
   picture.
5. Choose a strong opening frame because X has no required custom-thumbnail
   step for this fallback.

Prefer editorial shortening over severe bitrate reduction. Preserve the source
aspect ratio, cadence, color contract, dialogue sync, caption system, and one-
lossy-generation ceiling. Aim below the active byte limit with headroom rather
than landing exactly on it.

## Acceptance

Before posting, record:

- source path/hash and derivative path/hash;
- selected source ranges and final duration;
- rendered dimensions, frame rate, codec, size, and active limit/headroom;
- exact CTA text/timing and YouTube destination;
- full decode plus start/middle/end and late-sync checks;
- verified X account identity and exact approved post copy.

Mark the result `derivative_ready` until the public X post returns a durable ID
and readback. Never describe local preparation or an uploaded media ID as a
published post.
