---
name: x-post-xbot
description: Post to X/Twitter through the local xbot official API path using app credentials from the X Developer Console.
memory_tags:
  - domain:social-media
  - workflow:posting
  - engine:xbot-native
  - auth:official-api
  - platform:x-twitter
---

# X Post Xbot

## Trigger

Use when:
- the user wants to post to X from this workspace
- the user wants a reliable write path instead of cookie-auth or browser-stealth posting
- the task should use the local `xbot` repo and official API credentials
- the user wants to turn a local markdown idea into a gist-backed X thread

## Workflow

1. Confirm the official API credentials exist:
   - `X_API_KEY`
   - `X_API_SECRET`
   - `X_ACCESS_TOKEN`
   - `X_ACCESS_TOKEN_SECRET`
2. If the credentials are missing, direct the user to the `xbot/README.md` official API setup section.
3. If the post is not already specified and there is no explicit preauthorized
   posting rule in the active user/workspace instructions, first propose one to
   three candidate post directions and ask the user which one to pursue.
4. If a preauthorized posting rule is active, draft the X-native copy
   internally and post only when the idea is public-safe:
   - no secrets, credentials, private URLs, or local filesystem paths
   - no private personal details or non-public names
   - no sensitive work, client, employer, health, legal, or financial context
   - no unverified factual claims about third parties
   - no commitments made on the user's behalf
   - no unusually sharp criticism or reputation-sensitive framing
   If any item is uncertain, pause and ask for explicit approval.
5. If the post is derived from a longer idea, first draft or refine a public-safe markdown source file.
   - Preferred location for public-safe shareable drafts:
     `liferepo/writing/shareable/`
   - Keep one clear argument per file and avoid private paths or identifiers.
6. If the longer piece should be public, create the gist first:
   - Strip repo frontmatter before gist publication. The public gist should
     start at the title/body, not with YAML metadata.
   - `gh gist create <markdown-file> --public --desc "<title>"`
   - Put the gist link in the final reply of the thread, not the opener.
7. Then post to X using the local CLI:
   - `node xbot/src/cli.js post "<text>"`
   - `node xbot/src/cli.js post --reply-to <tweet_id> "<text>"`
8. Prefer a hook-first thread over a single long post when:
   - the idea has multiple layers
   - there is an external link to include
   - the goal is reach and repostability, not just maximum text length
9. Report the returned tweet ID(s), gist URL when applicable, and posted text
   back to the user.
10. Log the publishing action into today's daily summary under
   `## Conversation Milestones`.

## Preferred X Pattern

- Standard format after topic selection: `gist first -> thread second -> gist
  link in final reply`
- Gist body should not include YAML frontmatter from the repo draft
- Opener: sharp claim, no link, no throat-clearing
- Reply 2-4: unpack the system or argument in compact chunks
- Final reply: gist link or deeper reference
- Default bias: 3-5 posts, one idea, one obvious takeaway

## Guardrails

- Do not fall back to browser automation unless the user explicitly asks for that path.
- Treat posting as high-risk and user-visible. Outside an explicit
  preauthorized posting rule, if the user did not provide the exact post to
  send, ask which candidate direction to pursue before drafting or posting.
- Even in preauthorized mode, ask before posting if the draft touches sensitive
  context, third-party claims, identity details, private operations, or
  reputation-sensitive criticism.
- Keep credentials in local env files only. Never paste secrets into chat or commit them into `georgeskills`.
- Avoid putting external links in the first post unless the user explicitly wants a single-link post despite likely suppression.
- If a long premium post is possible, still choose a thread when the hook-plus-replies format is more likely to travel.

## Tools

- `node xbot/src/cli.js post ...`
- `xbot/src/post_official.js`
- `gh gist create ...`
