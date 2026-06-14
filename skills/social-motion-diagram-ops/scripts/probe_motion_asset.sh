#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <motion-asset> [contact-sheet-output]" >&2
  exit 2
fi

asset="$1"
contact="${2:-}"

ffprobe -v error \
  -show_entries format=duration:stream=width,height,r_frame_rate,nb_frames \
  -of default=noprint_wrappers=1 "$asset"

if [[ -n "$contact" ]]; then
  ffmpeg -y -i "$asset" \
    -vf "fps=4,scale=600:-1,tile=3x3" \
    -frames:v 1 "$contact" >/dev/null 2>&1
  echo "contact_sheet=$contact"
fi
