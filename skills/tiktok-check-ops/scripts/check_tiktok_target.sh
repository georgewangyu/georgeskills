#!/usr/bin/env bash
set -euo pipefail

target="${1:-examplecreator}"

if [[ "${target}" == "--help" || "${target}" == "-h" ]]; then
  cat <<'EOF'
Usage: check_tiktok_target.sh <username|profile-url|video-url>

Print a lightweight public reachability probe for a TikTok target and report
whether optional extractor tools are installed and usable.
EOF
  exit 0
fi

normalize_target() {
  local raw="$1"
  if [[ "$raw" =~ ^https?:// ]]; then
    printf '%s\n' "$raw"
    return
  fi

  raw="${raw#@}"
  printf 'https://www.tiktok.com/@%s\n' "$raw"
}

url="$(normalize_target "$target")"
tmp_headers="$(mktemp)"
cleanup() {
  rm -f "$tmp_headers"
}
trap cleanup EXIT

printf 'target=%s\n' "$target"
printf 'url=%s\n' "$url"

status="curl_failed"
final_url=""
if curl -sS -I -L --max-time 20 -D "$tmp_headers" -o /dev/null "$url"; then
  status="$(awk 'toupper($1) ~ /^HTTP\// { code=$2 } END { print code }' "$tmp_headers")"
  final_url="$(awk 'BEGIN { IGNORECASE=1 } /^location:/ { sub(/\r$/, "", $2); loc=$2 } END { print loc }' "$tmp_headers")"
fi

printf 'http_status=%s\n' "${status:-unknown}"
if [[ -n "$final_url" ]]; then
  printf 'redirect_location=%s\n' "$final_url"
fi

if command -v yt-dlp >/dev/null 2>&1; then
  printf 'yt_dlp=installed\n'
  if yt-dlp --flat-playlist --playlist-end 3 --dump-single-json "$url" >/tmp/tiktok-check-yt-dlp.json 2>/tmp/tiktok-check-yt-dlp.err; then
    printf 'yt_dlp_probe=ok\n'
  else
    printf 'yt_dlp_probe=failed\n'
    printf 'yt_dlp_error=%s\n' "$(tail -n 1 /tmp/tiktok-check-yt-dlp.err 2>/dev/null || true)"
  fi
else
  printf 'yt_dlp=missing\n'
fi

if command -v gallery-dl >/dev/null 2>&1; then
  printf 'gallery_dl=installed\n'
  if gallery-dl --range 1-2 --simulate "$url" >/tmp/tiktok-check-gallery-dl.out 2>/tmp/tiktok-check-gallery-dl.err; then
    printf 'gallery_dl_probe=ok\n'
  else
    printf 'gallery_dl_probe=failed\n'
    printf 'gallery_dl_error=%s\n' "$(tail -n 1 /tmp/tiktok-check-gallery-dl.err 2>/dev/null || true)"
  fi
else
  printf 'gallery_dl=missing\n'
fi

if [[ "${status:-}" == "200" ]]; then
  printf 'recommended_next_step=browser-view-or-extractor\n'
else
  printf 'recommended_next_step=browser-check-for-blocks-or-login-wall\n'
fi
