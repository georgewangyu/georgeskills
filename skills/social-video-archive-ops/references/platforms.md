# Platform Notes

Use this file only when the main skill needs platform-specific extraction
choices.

## X / Twitter

- Preferred path: local `xbot` GraphQL `TweetDetail`.
- Useful field: `legacy.extended_entities.media[].video_info.variants`.
- Prefer highest `video/mp4` variant. Use `.m3u8` only if MP4 is absent and a
  tool like `ffmpeg` can assemble it.
- Avoid saving auth cookies or headers in notes.
- Store media under:
  `<raw-media-archive>/transcripts/raw-media/x/<tweet-id>/`.

## YouTube

- Preferred path: `yt-dlp`.
- Preserve native subtitles/captions when available; fall back to ASR only when
  native captions are absent or insufficient.
- Store media under:
  `<raw-media-archive>/transcripts/raw-media/youtube/<video-id>/`.

## TikTok

- First try local/official bot tooling when available for the account or URL.
- `yt-dlp` and public extractors are opportunistic and may break.
- Browser/session inspection may be needed for public pages, but avoid saving
  session secrets.
- Store media under:
  `<raw-media-archive>/transcripts/raw-media/tiktok/<video-id>/`.

## Instagram

- Prefer official/local bot tooling for owned-account media.
- For public posts, extraction often depends on logged-in browser/session state
  or brittle public metadata. Label confidence and access assumptions.
- Store media under:
  `<raw-media-archive>/transcripts/raw-media/instagram/<shortcode-or-media-id>/`.

## LinkedIn

- Treat as session-gated by default.
- Use browser inspection only when the user has legitimate access and asks for
  a private reference copy.
- Preserve source URL and access caveat. Avoid storing cookies or request
  headers.

## Product Hunt / Embedded Launch Videos

- Product Hunt pages often embed YouTube, Loom, Vimeo, or product-hosted videos.
- Resolve the canonical embedded provider first, then use that provider's path.
- Store under the provider when possible, not under `product-hunt`, unless the
  media is truly hosted by Product Hunt.

## General Web Video

- Check page metadata and network requests for direct MP4/HLS only when the
  content is public and not protected by DRM or paywall controls.
- Prefer official download/export links when available.
- If only HLS is available, use `ffmpeg -i <m3u8> -c copy video.mp4` when legal
  and technically allowed.
