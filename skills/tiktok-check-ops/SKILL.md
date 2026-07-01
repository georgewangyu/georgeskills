---
name: tiktok-check-ops
description: Check a TikTok account or video for public status and recent viewable content, preferring lightweight probes before browser viewing.
memory_tags:
  - domain:social-media
  - workflow:account-check
  - skill_role:researcher
  - repo_boundary:tools
  - inputs:web
  - outputs:status-report
  - risk:medium
---

# TikTok Check Ops

## Trigger

Use when:
- the user wants to check a TikTok account, profile, or public video
- the user wants a quick answer on whether a username appears reachable
- the user asks to inspect or view a TikTok handle or profile
- the task may benefit from a CLI probe before falling back to a browser

Do not use when:
- the task is general browser automation with no TikTok-specific logic
- the user needs private account access or inbox/session management
- the goal is to build or debug Playwright flows themselves; use `playwright`

## Inputs

- Required: TikTok username, profile URL, or video URL
- Optional: number of items to sample, whether browser viewing is allowed, whether screen-control fallback is allowed, whether developer credentials already exist

## Local Probe Prerequisites

- If the goal is to check the operator's own authorized TikTok account and a
  local `tiktokbot` checkout is available, prefer that CLI before public-page
  probing:
  - `node src/cli.js check --min-outlier 2 --max-results 60`
  - This returns the authorized account follower count and recent videos above
    the requested creator-baseline multiplier.
  - It requires Display API OAuth tokens in that bot's private env file.
- The local probe script always uses `curl` for a first-party reachability check.
- It can also use `yt-dlp` and `gallery-dl` as optional best-effort extractors for
  public metadata when those tools are installed locally.
- These extractor tools are not required. Missing extractor output does not mean a
  profile or video is unavailable; it only means the CLI path is limited and the
  next step should be browser viewing via `playwright`, or screen-control viewing
  via `social-screen-control-ops` when logged-in local browser state is needed.
- Treat both extractors as volatile dependencies. They can work one week and fail
  the next due to upstream TikTok changes.

## Workflow

1. Normalize the target:
   - username like `examplecreator`
   - profile URL like `https://www.tiktok.com/@examplecreator`
   - video URL when checking a specific post
2. Run the local probe:
   - `skills/tiktok-check-ops/scripts/check_tiktok_target.sh <target>`
   - interpret the result as:
     - `http_status`: first-party web reachability
     - `yt_dlp=installed|missing`: whether optional extractor path exists
     - `gallery_dl=installed|missing`: whether optional extractor path exists
3. Interpret the result conservatively:
   - first-party HTTP reachability is useful
   - unofficial extractor output is opportunistic, not guaranteed
   - missing extractor output does not prove the account is gone
4. Decide access path:
   - for the operator's own authorized account analytics, use the local `tiktokbot` CLI when available
   - if the user already has valid TikTok developer access for the needed scope, read `references/current-options.md`
   - otherwise use browser viewing
5. For browser viewing, prefer:
   - profile page open
   - fresh snapshot
   - click through visible posts only after re-snapshotting
   - the `playwright` skill for public/clean-session checks
   - the shared browser fallback rules in `skills/_shared/social-platform-fallbacks.md`

## Screen-Control Fallback

Follow `skills/_shared/social-platform-fallbacks.md`.

## Output Contract

- normalized target
- whether the first-party TikTok web URL appears reachable
- whether optional local extractors (`yt-dlp`, `gallery-dl`) were installed
- whether any installed extractor produced usable metadata
- recommended next path: official API, CLI probe, or browser viewing
- blockers such as captcha, login wall, rate limits, or missing local tools

## Guardrails

- Do not imply official API coverage when the account has not authorized access.
- Treat third-party extractors as volatile and best-effort.
- For anything interactive or visually confirmatory, use the appropriate browser skill instead of inventing a second browser workflow here.
- Do not store cookies or credentials inside this skill.
- Do not intentionally play TikTok video audio during browser fallback unless the user asks to listen; keep media pages muted by default.

## References

Open only when needed:
- current API and CLI caveats: `references/current-options.md`
