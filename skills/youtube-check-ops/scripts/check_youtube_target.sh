#!/usr/bin/env bash
set -euo pipefail

target="${1:-examplecreator}"

if [[ "${target}" == "--help" || "${target}" == "-h" ]]; then
  cat <<'EOF'
Usage: check_youtube_target.sh <handle|channel-url|video-url>

Print a lightweight public reachability and metadata probe for a YouTube target.
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
  printf 'https://www.youtube.com/@%s\n' "$raw"
}

url="$(normalize_target "$target")"
tmp="$(mktemp)"
headers="$tmp.headers"
cleanup() {
  rm -f "$tmp" "$headers"
}
trap cleanup EXIT

printf 'target=%s\n' "$target"
printf 'url=%s\n' "$url"

status="curl_failed"
if curl -sS -L --max-time 20 -A 'Mozilla/5.0' -D "$headers" -o "$tmp" "$url"; then
  status="$(awk 'toupper($1) ~ /^HTTP\// { code=$2 } END { print code }' "$headers")"
fi

printf 'http_status=%s\n' "${status:-unknown}"

title="$(perl -0ne 'print $1 if /<title>([^<]+)<\/title>/s' "$tmp")"
meta_description="$(perl -0ne 'print $1 if /<meta name="description" content="([^"]+)"/s' "$tmp")"
og_title="$(perl -0ne 'print $1 if /<meta property="og:title" content="([^"]+)"/s' "$tmp")"
og_description="$(perl -0ne 'print $1 if /<meta property="og:description" content="([^"]+)"/s' "$tmp")"
subscriber_text="$(perl -0ne 'print $1 if /([0-9.,]+[KMB]? subscribers)/i' "$tmp")"

if [[ -n "${title:-}" ]]; then
  printf 'title=%s\n' "$title"
fi
if [[ -n "${og_title:-}" ]]; then
  printf 'og_title=%s\n' "$og_title"
fi
if [[ -n "${meta_description:-}" ]]; then
  printf 'meta_description=%s\n' "$meta_description"
fi
if [[ -n "${og_description:-}" ]]; then
  printf 'og_description=%s\n' "$og_description"
fi
if [[ -n "${subscriber_text:-}" ]]; then
  printf 'subscriber_text=%s\n' "$subscriber_text"
fi

if [[ "${status:-}" == "200" ]]; then
  printf 'recommended_next_step=public-metadata-or-browser-view\n'
else
  printf 'recommended_next_step=browser-check\n'
fi
