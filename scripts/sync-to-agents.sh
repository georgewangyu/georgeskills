#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_DIR="$ROOT_DIR/skills"
DEST_DIR="${AGENTS_SKILLS_DIR:-$HOME/.agents/skills}"

mkdir -p "$DEST_DIR"

shopt -s nullglob
found=0

for skill_dir in "$SOURCE_DIR"/*; do
  if [ -L "$skill_dir" ]; then
    echo "Refusing source skill symlink: $skill_dir" >&2
    exit 1
  fi
  [ -d "$skill_dir" ] || continue
  [ -f "$skill_dir/SKILL.md" ] || continue
  if [ -n "$(find "$skill_dir" -type l -print -quit)" ]; then
    echo "Refusing skill containing a source symlink: $skill_dir" >&2
    exit 1
  fi

  found=1
  skill_name="$(basename "$skill_dir")"
  dest="$DEST_DIR/$skill_name"

  if [ -L "$dest" ]; then
    rm -f "$dest"
  elif [ -e "$dest" ]; then
    echo "Skipping existing non-symlink entry: $skill_name"
    continue
  fi

  ln -s "$skill_dir" "$dest"
  echo "Linked $skill_name -> $dest"
done

if [ "$found" -eq 0 ]; then
  echo "No skills with SKILL.md found under $SOURCE_DIR"
fi

echo "Agent skills directory: $DEST_DIR"
echo "Restart the assistant session after adding a new skill."
