---
name: social-video-archive-ops
description: Archive reference videos from social platforms without putting large media inside active repos. Use when a user wants to download, preserve, transcribe, or keep a reference copy of an X/Twitter, YouTube, TikTok, Instagram, LinkedIn, Product Hunt, or other social/web video; when extracting direct MP4/HLS media URLs from platform metadata; or when creating repo-side provenance notes and symlinks that point to an external raw-media archive.
memory_tags:
  - domain:social-media
  - domain:transcripts
  - workflow:video-archive
  - skill_role:operator
  - repo_boundary:tools
  - risk:medium
---

# Social Video Archive Ops

## Purpose

Preserve source videos for reference while keeping heavy binaries out of active
git/workspace trees. The repo stores meaning and provenance; the external raw
media archive stores bytes.

## Storage Rule

Never save large source videos directly inside the active repo, even when the
path is git-ignored. Use this layout:

```text
<raw-media-archive>/transcripts/raw-media/<platform>/<source-id>/video.<ext>
<private-repo>/areas/transcripts/raw/<platform>/<source-id>/video.<ext> -> symlink
<private-repo>/areas/transcripts/raw/<platform>/<source-id>/command_notes.md
```

Resolve `<raw-media-archive>` from the private repo's transcript/media
instructions or an existing prior capture. Look first for:

```text
<private-repo>/areas/transcripts/README.md
<private-repo>/areas/transcripts/raw/<platform>/<source-id>/command_notes.md
```

If no archive root is documented, search existing notes for
`RawMediaArchive`, `transcripts/raw-media`, or prior symlink conventions before
choosing a new location. Only fall back to `<private-repo>/captures/` for small
metadata, intermediate text, or temporary one-shot artifacts, not source video
binaries.

## Workflow

1. Identify the platform, stable source ID, author, original URL, and whether
   the video is public, session-gated, or private.
2. Extract media using the least fragile route available:
   - X/Twitter: prefer local `xbot` GraphQL `TweetDetail`; inspect
     `video_info.variants`; choose the highest useful MP4 variant; use HLS only
     when MP4 is absent.
   - YouTube: prefer `yt-dlp` for source media and subtitles; preserve native
     captions when available.
   - TikTok/Instagram/LinkedIn/other social platforms: use official/local bots,
     `yt-dlp`, platform metadata, or browser/session extraction depending on
     what is available and allowed.
3. Create the external archive directory:

   ```text
   <raw-media-archive>/transcripts/raw-media/<platform>/<source-id>/
   ```

4. Download or move source media there using canonical names:
   - `video.mp4` or the real extension when MP4 is unavailable
   - `thumb.jpg` / `poster.jpg` when a thumbnail is available
   - optional raw metadata files when useful
5. Create the repo-side raw transcript directory:

   ```text
   <private-repo>/areas/transcripts/raw/<platform>/<source-id>/
   ```

6. Add symlinks from the repo directory to the external media files.
7. Write `command_notes.md` with frontmatter and:
   - source URL, source ID, media ID when known, author, retrieval date
   - extraction method and commands
   - external media path
   - repo symlink path
   - duration, resolution, codec, size, checksum when available
   - fallback failures or auth/session caveats
8. If transcribing, keep derived ASR/subtitle artifacts in the repo raw
   transcript directory and put readable Markdown under:

   ```text
   <private-repo>/areas/transcripts/processed/<platform>/
   ```

   On Apple Silicon, use the native ARM64 MLX Whisper path from the local
   transcription tooling. Do not use CPU Whisper, WhisperX, or
   `whisper-ctranslate2` as a normal fallback. If MLX cannot run, treat that as
   an environment blocker and fix the ARM64 venv/cache setup before
   transcribing.

9. Update the daily summary or relevant project note with the external media
   path and repo-side `command_notes.md`, not a stale temporary download path.

## Download Recipe

Use platform metadata rather than screen recording whenever possible. The core
pattern is:

1. Fetch the post/video metadata through the most stable available tool for
   that platform.
2. Inspect metadata for direct media variants, usually MP4 or HLS.
3. Prefer the highest-quality MP4 variant when available.
4. If MP4 is absent and HLS is allowed, download the playlist with `ffmpeg`.
5. Download into the external raw media archive with `curl -L --fail`, `yt-dlp`,
   or `ffmpeg`, depending on the platform and media type.
6. Run `ffprobe`, compute a checksum, and record size/duration/resolution.
7. Add repo-side symlinks and provenance notes. Do not store cookies, auth
   headers, bearer tokens, or volatile CDN URLs as the only source of truth.

Common commands:

```bash
mkdir -p "<raw-media-archive>/transcripts/raw-media/<platform>/<source-id>"
curl -L --fail "<direct-mp4-url>" \
  -o "<raw-media-archive>/transcripts/raw-media/<platform>/<source-id>/video.mp4"
ffprobe -v error -show_format -show_streams -of json \
  "<raw-media-archive>/transcripts/raw-media/<platform>/<source-id>/video.mp4"
shasum -a 256 \
  "<raw-media-archive>/transcripts/raw-media/<platform>/<source-id>/video.mp4"
ln -s "<raw-media-archive>/transcripts/raw-media/<platform>/<source-id>/video.mp4" \
  "<private-repo>/areas/transcripts/raw/<platform>/<source-id>/video.mp4"
```

For HLS-only sources:

```bash
ffmpeg -i "<hls-m3u8-url>" -c copy \
  "<raw-media-archive>/transcripts/raw-media/<platform>/<source-id>/video.mp4"
```

## Transcription Preference

For Mac-local long-form video, use the native ARM64 MLX transcription path when
the project has one:

```bash
source <skills-repo>/scripts/transcription/venv/bin/activate
HF_HOME="<stable-huggingface-cache>" \
  python <skills-repo>/scripts/transcription/mlx_transcriber.py \
  "<private-repo>/areas/transcripts/raw/<platform>/<source-id>/audio.mp3" \
  --outdir "<private-repo>/areas/transcripts/raw/<platform>/<source-id>/"
```

If `mlx` or `mlx_whisper` cannot import from that venv, or if the package
resolver reports non-ARM64 wheel constraints, do not waste time forcing the
generic installer path and do not silently switch to CPU ASR. Fix the native
venv/cache setup first, then rerun MLX. Record the MLX environment blocker in
`command_notes.md` if transcription cannot proceed.

## X/Twitter Direct MP4 Pattern

Use local `xbot` credentials to fetch raw `TweetDetail`, then walk the JSON for
`video_info.variants`. Pick the highest exposed `video/mp4` URL.

Core extraction shape:

```js
import { XClient } from "/path/to/xbot/src/client.js";

const client = new XClient();
const res = await client.fetchGraphQL("TweetDetail", {
  focalTweetId: "<tweet-id>",
  referrer: "profile",
  with_rux_injections: false,
  rankingMode: "Relevance",
  includePromotedContent: false,
  withCommunity: true,
  withQuickPromoteEligibilityTweetFields: true,
  withBirdwatchNotes: false,
  withVoice: true
});

const variants = [];
function walk(x) {
  if (!x || typeof x !== "object") return;
  if (Array.isArray(x)) return x.forEach(walk);
  const contentType = x.content_type || x.type || "";
  if (contentType === "video/mp4" && x.url) {
    variants.push({
      bitrate: x.bitrate ?? x.bit_rate ?? 0,
      width: x.width ?? 0,
      height: x.height ?? 0,
      url: x.url
    });
  }
  for (const v of Object.values(x)) walk(v);
}
walk(res);
variants.sort((a, b) =>
  (b.bitrate - a.bitrate) ||
  ((b.width * b.height) - (a.width * a.height))
);
console.log(variants);
```

Then download with `curl -L --fail` into the external archive, not into the
repo.

If `xbot` is unavailable, public metadata helpers such as FixTweet/VxTwitter
may expose `mediaURLs`, `media_extended`, or `variants`. Treat them as
fallbacks: they are useful for public posts, but they are third-party services
and may be stale, incomplete, rate-limited, or blocked.

## Platform Coverage

For platform-specific caveats, read `references/platforms.md`.

Short version: yes, this pattern works for many platforms, but not identically.
Some expose direct MP4/HLS URLs in metadata, some require `yt-dlp`, and some
require a logged-in browser/session or are not appropriate to archive without
authorization. The reusable part is the archive/provenance/symlink discipline.

## Guardrails

- Do not publish, redistribute, or upload downloaded media unless the user has
  rights and explicitly asks.
- Do not print or store cookies, auth tokens, or private headers in notes.
- Do not bypass paywalls, private accounts, DRM, or access controls.
- Do not commit large binary media files to git.
- Treat extracted media URLs as volatile; store the source URL and retrieval
  method because CDN URLs may expire or disappear.
- If the source is sensitive, private, or reputation-relevant, preserve only the
  minimal local reference needed and label access assumptions clearly.

## Output Contract

Return:

- external media path
- repo-side symlink/provenance path
- source URL
- duration/resolution/size/checksum when available
- any blocked/stale/auth caveats
