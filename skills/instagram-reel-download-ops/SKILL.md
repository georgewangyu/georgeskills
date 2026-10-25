---
name: instagram-reel-download-ops
description: Download one public Instagram Reel to a local file and verify the media. Use when a Reel reference is needed for viewing, editing, or archiving.
metadata:
  memory_tags:
    - domain:social-media
    - workflow:reel-download
    - skill_role:operator
    - repo_boundary:tools
    - inputs:web
    - outputs:video
    - risk:medium
---

# Instagram Reel Download Ops

Acquire one public Reel as a validated local MP4. The helper accepts a Reel URL and an explicit output directory; it never reads browser cookies or overwrites an existing file.

```bash
python3 <georgeskills-root>/skills/instagram-reel-download-ops/scripts/download_reel.py \
  'https://www.instagram.com/reel/<shortcode>/' --output-dir '<destination>'
```

The helper uses an installed `yt-dlp`, or `uv tool run --from yt-dlp yt-dlp` when `uv` is available. It requires `ffprobe`. It prints the final path, duration, resolution, size, and SHA-256 after verifying a video stream. Give the output a destination outside a Git repository unless the user explicitly requests otherwise.

The metadata preflight rejects carousel/multi-item posts before downloading
media, even when a `/reel/` URL resolves to a carousel. Do not treat the first
child as the complete reference or repeatedly retry this single-video helper.
For a carousel, preserve the complete item inventory and archive its items
under distinct media IDs through the existing social archive workflow. The
single-video receipt includes the extracted media ID separately from the URL
shortcode; the download uses the same validated metadata.
If saved media URLs expire, the helper fails rather than silently re-extracting
the post. A deliberate retry starts with a fresh single-video preflight.

If the direct extraction fails, open the public Reel in the user's Edge or Chrome session. When a trusted, already installed extension shows a download control on the Reel pane, use that visible control through the approved browser or app UI surface. Verify the downloaded file with `ffprobe` and a hash before reporting success. Do not install an extension, scrape browser cookies, or copy authenticated media requests to work around a failure. Report a private, removed, blocked, or inaccessible Reel as such.

Keep the original Reel URL with any provenance note. For a durable raw-media archive and repo-side symlink, compose with `social-video-archive-ops`. Local reference acquisition does not grant rights to publish or redistribute the media.
