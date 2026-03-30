#!/usr/bin/env bash
set -euo pipefail

target="${1:-examplecreator}"

if [[ "${target}" == "--help" || "${target}" == "-h" ]]; then
  cat <<'EOF'
Usage: check_instagram_target.sh <username|profile-url|post-url>

Print a lightweight public reachability and metadata probe for an Instagram target.
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
  printf 'https://www.instagram.com/%s/\n' "$raw"
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

title="$(perl -0ne 'print $1 if /<meta property="og:title" content="([^"]+)"/s' "$tmp" | sed "s/&#x2019;/'/g; s/&#064;/@/g; s/&#x2022;/•/g")"
description="$(perl -0ne 'print $1 if /<meta property="og:description" content="([^"]+)"/s' "$tmp" | sed "s/&#x2019;/'/g; s/&#064;/@/g; s/&#x2022;/•/g")"

if [[ -n "${title:-}" ]]; then
  printf 'og_title=%s\n' "$title"
fi
if [[ -n "${description:-}" ]]; then
  printf 'og_description=%s\n' "$description"
fi

if [[ "${status:-}" == "200" ]]; then
  printf 'recommended_next_step=browser-view-or-public-meta\n'
else
  printf 'recommended_next_step=browser-check-for-login-wall-or-block\n'
fi
