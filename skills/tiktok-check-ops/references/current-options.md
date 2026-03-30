# Current Options

Use this note when deciding whether TikTok account checks can rely on an API or need browser fallback.

## Practical rule

- Default assumption: arbitrary public account checks do not have a simple stable official API path.
- Best default: probe the public web URL, then use `playwright` for actual viewing.

## Official TikTok paths

- TikTok for Developers provides official APIs, but their scopes are narrow and access-dependent.
- Content Posting API is for publishing, not public profile inspection.
- Research API is specialized and not a general-purpose profile-view API.
- If the target account itself has authorized an app and the needed scope exists, official APIs may help. Otherwise they usually do not solve "check this public account for me".

## CLI paths

- `yt-dlp` sometimes works for public TikTok URLs, but support can break without warning.
- `gallery-dl` may also work in some environments, but it is similarly best-effort.
- Missing output from either tool is not definitive evidence that the account or post is unavailable.

## Browser path

- Use the existing `playwright` skill when you need:
  - visual confirmation
  - a profile page check
  - manual inspection of recent posts
  - screenshots or artifact capture
