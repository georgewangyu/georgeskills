#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_DIR="$ROOT_DIR/skills"
DEST_DIR="${CODEX_HOME:-$HOME/.codex}/skills"

mkdir -p "$DEST_DIR"

shopt -s nullglob
found=0

for skill_dir in "$SOURCE_DIR"/*; do
  [ -d "$skill_dir" ] || continue
  [ -f "$skill_dir/SKILL.md" ] || continue

  found=1
  skill_name="$(basename "$skill_dir")"
  dest="$DEST_DIR/$skill_name"

  if [ -L "$dest" ] || [ -e "$dest" ]; then
    rm -rf "$dest"
  fi

  ln -s "$skill_dir" "$dest"
  echo "Linked $skill_name -> $dest"
done

if [ "$found" -eq 0 ]; then
  echo "No skills with SKILL.md found under $SOURCE_DIR"
fi

echo "Codex skills directory: $DEST_DIR"
echo "Restart Codex after adding a new skill."
