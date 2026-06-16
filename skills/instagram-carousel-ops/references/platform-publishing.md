# Instagram Carousel Publishing Reference

Verify platform limits before publishing because Instagram app and API behavior can change.

## Current Working Defaults

- Design size: `1080 x 1350` for 4:5 educational/feed carousels.
- App carousel limit: Instagram Help says a feed carousel can include up to `20` photos and videos.
- API/posting-bot limit: treat API carousel child count as tool-specific and verify before queueing. Many Graph API publishing workflows historically use stricter child limits than the Instagram app.
- Mixed media: plan for a carousel to contain both static images and short videos when the posting path supports it.
- Motion format: use MP4 or MOV for publishable motion pages. Use GIF only as a preview format.
- Loop duration: use `2-4s` for GIF-style motion; keep at least `3s` when targeting Graph API-style video publishing constraints.
- Aspect ratio: keep all carousel children the same ratio to avoid unexpected crop/letterbox behavior.

## Preflight Checks

Run these checks before posting:

- Confirm target account and posting tool.
- Confirm every media URL is publicly accessible if the API requires URL ingest.
- For local files, prefer a temporary direct-public HTTPS hosting prefix over
  presigned URLs when publishing MP4 carousel pages through Graph API-style
  tools.
- Confirm all media files share dimensions/aspect ratio.
- Confirm MP4 duration, frame rate, codec, and file size are accepted by the posting path.
- Confirm caption length and hashtags fit the target platform limits.
- Get explicit user approval before publishing.

## Media Hosting Notes

When the carousel assets are local files, the posting tool may need public URL
ingest. The safest observed pattern is:

1. Upload media to a narrow temporary public prefix.
2. Verify each URL returns `HEAD 200` and the expected content type.
3. Publish with the platform tool.
4. Delete temporary media and remove the temporary public-read policy.

Keep concrete bucket names, account IDs, credentials, and private paths in the
project-local private overlay, not in this reusable skill.

## Source Links

- Instagram Help, carousel app behavior: `https://help.instagram.com/269314186824048/`
- Meta for Developers, Instagram content publishing: `https://developers.facebook.com/docs/instagram-platform/content-publishing/`
- Meta for Developers, media/video specifications reference: `https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/media/`
