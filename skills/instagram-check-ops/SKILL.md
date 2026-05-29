---
name: instagram-check-ops
description: Check an Instagram account or post for public status and basic metadata, preferring lightweight probes before browser viewing.
memory_tags:
  - domain:social-media
  - workflow:account-check
  - repo_boundary:tools
  - inputs:web
  - outputs:status-report
  - risk:medium
---

# Instagram Check Ops

## Trigger

Use when:
- the user wants to check an Instagram profile, reel, or public post
- the user asks to inspect or view an Instagram handle or profile
- the task needs a quick public-profile summary before browser fallback

Do not use when:
- the task is general browser automation with no Instagram-specific logic
- the user needs DM, login, or private-account access
- the goal is to build or debug browser flows directly; use `playwright`

## Inputs

- Required: Instagram username, profile URL, or post URL
- Optional: whether browser viewing is allowed, whether Meta developer credentials already exist

## Workflow

1. Normalize the target:
   - username like `examplecreator`
   - profile URL like `https://www.instagram.com/examplecreator/`
2. Run the local probe:
   - `skills/instagram-check-ops/scripts/check_instagram_target.sh <target>`
3. Interpret the result conservatively:
   - public meta tags can expose profile title and high-level counts
   - missing public metadata does not prove the account is gone
4. Decide access path:
   - if the user already has valid Meta app access for the needed scope, read `references/current-options.md`
   - otherwise use `playwright` for visual inspection, with browser audio muted when possible, for example Chrome launched with `--mute-audio`

## Output Contract

- normalized target
- whether the first-party Instagram URL appears reachable
- any public profile title/summary extracted from the page
- recommended next path: official API, public probe, or browser viewing

## Guardrails

- Do not imply Graph API coverage for arbitrary public profiles without the right app/user access.
- Treat public HTML extraction as best-effort.
- Route interactive viewing to `playwright` rather than duplicating browser automation here.
- Do not intentionally play Reels/post audio during browser fallback unless the user asks to listen; keep media pages muted by default.

## References

Open only when needed:
- current API and extraction caveats: `references/current-options.md`
