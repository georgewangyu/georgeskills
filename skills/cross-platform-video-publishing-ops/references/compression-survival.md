# Instagram Compression Survival

Use this procedure for an Instagram Reel when the creator values delivered
picture quality or asks why one upload survived compression better than
another.

## What The Platform Does

Instagram creates multiple encodings from an uploaded video and uses adaptive
bitrate delivery. A direct API upload does not preserve the source bitstream.
Treat the upload path as a way to deliver the exact intended master to Meta,
not as a no-compression mode.

Official references:

- [Instagram media-container video specifications](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/media#creating)
- [Instagram's basic and advanced encoding pipeline](https://engineering.fb.com/2022/11/04/video-engineering/instagram-video-processing-encoding-reduction/)
- [AV1 and adaptive bitrate delivery for Reels](https://engineering.fb.com/2023/02/21/video-engineering/av1-codec-facebook-instagram-reels/)

Re-check the active publishing endpoint's official limits at execution time;
Meta's supported duration, file-size, and audio limits can differ by API flow
and can change.

## Pre-Ingest Gate

Start from the approved editorial master or a lossless/mezzanine authority.
Never create an Instagram derivative from a downloaded social copy or another
lossy platform derivative.

For an SDR vertical Reel, prefer these compatibility properties unless the
active official route or creator profile requires something else:

- native `9:16`, normally `1080x1920`; do not upscale a smaller source merely
  to satisfy the label
- H.264 High profile in MP4 for broad compatibility
- progressive scan, `yuv420p`, and a closed GOP
- constant or source-faithful frame rate within the official supported range;
  avoid gratuitous frame-rate conversion
- explicit BT.709 primaries, transfer, and matrix for SDR
- high-quality VBR below the active route's documented maximum
- AAC stereo or mono within the active route's documented sample-rate and
  bitrate limits
- front-loaded `moov` atom / fast start when producing MP4

Preserve fine detail by preventing upstream damage rather than compensating
with aggressive sharpening, denoising, or added grain. Apply the creator's
approved grade, privacy work, titles, captions, and mix in one final lossy
picture generation whenever practical. Render from primary sources or a
documented mezzanine, and do not re-export the accepted master through a phone
editor solely for upload.

Do not deliberately precompress to a guessed Instagram delivery bitrate. Give
Meta a clean, high-quality, compliant source and let its content-aware encoder
make the delivery renditions.

## Ingest Gate

When the creator profile selects the official API:

1. Fingerprint the exact master.
2. Make that exact file available through the approved temporary HTTPS ingest
   route or the official resumable-upload endpoint.
3. Before container creation, verify filename, byte size, content type, and
   that the URL returns the intended object. Compare a downloaded hash only
   when the upload system can do so without exposing credentials or creating an
   unnecessary durable copy.
4. Create the Reel container and wait for its status to reach the route's
   successful processing state before publication.
5. Publish the container, read back the media ID, account, caption, and
   permalink, then remove temporary hosting only after Meta no longer depends
   on it.

For a native-app upload, enable the platform's highest-quality upload setting
when available and use the exact same approved master. Avoid data-saver paths,
messenger transfers, cloud previews, or editor-to-camera-roll round trips that
may create an undocumented intermediate.

## Post-Publish Measurement

The API-exposed `media_url` may be only one rendition, not the complete
adaptive-bitrate ladder. Still, it is useful repeatable evidence.

Record:

- source and delivered width, height, codec, profile, pixel format, frame rate,
  bitrate, duration, color tags, and byte size
- source-to-delivery resolution and bitrate ratios
- whether frame rate and SDR color tags survived
- representative decoded-frame checks for faces, hair, grass/foliage, gradients,
  small captions, fast motion, and dark areas
- playback context: device, connection, and whether the Reel had recently been
  published or had time to receive additional encodings

Do not call an upload `compression-safe` from metadata alone. Require normal-
speed playback on an ordinary phone plus representative-frame inspection.

## Learning Loop

For the first few releases after adopting this gate, retain a compact
before/after measurement in the private video history. Compare failures against
the last accepted baseline. Change only one material encoding variable at a
time when a controlled test is justified; content, motion, lighting, and
platform-selected rendition can otherwise overwhelm the result.

Separate what the creator controls from what Meta controls:

- Creator-controlled: source quality, number of lossy generations, resolution,
  frame rate, color correctness, compatible encoding, ingest integrity, and
  upload route.
- Meta-controlled: rendition ladder, codec assignment, bitrate, processing
  priority, and viewer-side adaptive selection.
