---
name: instagram-check-ops
description: Check an Instagram account or post for public status and basic metadata, preferring lightweight probes before browser viewing.
metadata:
  memory_tags:
    - domain:social-media
    - workflow:account-check
    - skill_role:researcher
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
- Optional: whether browser viewing is allowed, whether screen-control fallback is allowed, whether Meta developer credentials already exist

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
   - otherwise use browser viewing for visual inspection
   - the shared browser fallback rules in `skills/_shared/social-platform-fallbacks.md`

## Owned-Account Token Lifecycle

- For an operator's authorized professional account, use the official local
  bot's health and owned-media commands before public or unofficial fallbacks.
- Treat browser sign-in and app authorization as separate sessions. Being
  signed into instagram.com does not prove that IGBot has a valid OAuth token.
- IGBot health and check commands are read-only and never refresh credentials.
  A scheduled operator may run `node src/cli.js refresh-token --save` as a
  bounded credential-maintenance step only while the saved long-lived token is
  still valid.
- Run a daily non-secret health check and refresh when fewer than 14 days
  remain. Do not wait for the approximate 60-day long-lived-token boundary.
- If Meta reports code `190`, an expired/revoked token, or rejects refresh,
  stop retrying and report that fresh OAuth consent is required. Never attempt
  login, CAPTCHA handling, or credential rotation inside a research run.
- OAuth authorization codes are short-lived and one-time. Exchange a fresh
  code using exactly the same redirect URI used in the authorization request;
  never log or preserve the code in a report.

## Screen-Control Fallback

Follow `skills/_shared/social-platform-fallbacks.md`.

## Output Contract

- normalized target
- whether the first-party Instagram URL appears reachable
- any public profile title/summary extracted from the page
- recommended next path: official API, public probe, or browser viewing

## Guardrails

- Do not imply Graph API coverage for arbitrary public profiles without the right app/user access.
- Treat public HTML extraction as best-effort.
- Route interactive viewing to the appropriate browser skill rather than duplicating browser automation here.
- Do not intentionally play Reels/post audio during browser fallback unless the user asks to listen; keep media pages muted by default.
- Never print, copy into durable notes, or commit access tokens, refresh tokens,
  authorization codes, app secrets, or full callback URLs containing a code.

## References

Open only when needed:
- current API and extraction caveats: `references/current-options.md`
