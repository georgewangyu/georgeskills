# Export Specs

## Recommended Outputs

- X/Twitter and LinkedIn feed motion: MP4, H.264, no audio, 12-24 fps.
- Static poster: PNG or JPG.
- Editable source: SVG, HTML/CSS, or `.excalidraw` when feasible.

## Aspect Ratios

- Near-square: `1:1` or slightly tall, good for X and LinkedIn feed diagrams.
- Landscape: `16:9`, good for link cards, newsletter, and repo/social previews.
- Tall: `4:5`, good for LinkedIn mobile, but verify text size carefully.

## Practical Defaults

- Diagram loop: 2-3 seconds.
- Resolution: 1200-1600 px on the long edge.
- Safe margins: keep key text at least 64 px from the edge at 1200 px width.
- File size: keep MP4 compact; diagram loops should often be under a few MB.

## Validation Commands

Use `ffprobe` for motion assets:

```bash
ffprobe -v error \
  -show_entries format=duration:stream=width,height,r_frame_rate,nb_frames \
  -of default=noprint_wrappers=1 <asset>.mp4
```

Generate a contact sheet for quick review:

```bash
ffmpeg -y -i <asset>.mp4 \
  -vf "fps=4,scale=600:-1,tile=3x3" \
  -frames:v 1 <asset>-contact.jpg
```

## Platform Notes

- X may label uploaded MP4 loops as animated GIF-like media.
- MP4 is usually preferable to GIF because it is smaller and cleaner.
- LinkedIn often favors clear first frames; always export a strong poster PNG.
