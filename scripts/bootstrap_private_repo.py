#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Iterable


MARKER_FILENAME = ".liferepo-private.json"
POINTER_RELATIVE_PATH = Path(".liferepo") / "local" / "private_repo.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bootstrap liferepo private-state repo and local pointer config."
    )
    parser.add_argument(
        "--name",
        dest="private_repo_name",
        default="",
        help="Private repo folder name (e.g. my-private-repo).",
    )
    parser.add_argument(
        "--path",
        dest="private_repo_path",
        default="",
        help="Private repo path. Relative paths are resolved from liferepo root.",
    )
    parser.add_argument(
        "--liferepo-root",
        default="",
        help="Path to liferepo root (default: workspace sibling liferepo).",
    )
    parser.add_argument(
        "--create",
        action="store_true",
        help="Create the private repo folder if it does not exist.",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Prompt for optional scaffold modules (journal/resume/exports).",
    )
    parser.add_argument(
        "--init-journal",
        action="store_true",
        help="Create starter journal directories in private repo.",
    )
    parser.add_argument(
        "--init-resume",
        action="store_true",
        help="Create starter Resume directories in private repo.",
    )
    parser.add_argument(
        "--init-exports",
        action="store_true",
        help="Create starter export script directories and setup placeholders.",
    )
    parser.add_argument(
        "--init-all",
        action="store_true",
        help="Equivalent to --init-journal --init-resume --init-exports.",
    )
    return parser.parse_args()


def default_liferepo_root() -> Path:
    script_dir = Path(__file__).resolve().parent
    workspace_root = script_dir.parent.parent
    return workspace_root / "liferepo"


def resolve_liferepo_root(raw: str) -> Path:
    if raw:
        root = Path(raw).expanduser().resolve()
    else:
        root = default_liferepo_root().resolve()
    if not (root / "AGENTS.md").exists():
        raise FileNotFoundError(f"liferepo root not found: {root}")
    return root


def resolve_private_repo_root(liferepo_root: Path, name: str, raw_path: str) -> tuple[str, Path]:
    repo_name = name.strip() or "private-repo"
    if "/" in repo_name or "\\" in repo_name:
        raise ValueError("private repo name must be a single folder name")

    if raw_path.strip():
        candidate = Path(raw_path).expanduser()
        private_root = (liferepo_root / candidate).resolve() if not candidate.is_absolute() else candidate.resolve()
    else:
        private_root = (liferepo_root.parent / repo_name).resolve()
    return repo_name, private_root


def write_marker(private_root: Path) -> None:
    marker_path = private_root / MARKER_FILENAME
    marker = {"schema_version": 1, "role": "liferepo-private-state"}
    marker_path.write_text(json.dumps(marker, indent=2) + "\n", encoding="utf-8")


def write_pointer(liferepo_root: Path, repo_name: str, private_root: Path) -> Path:
    pointer_path = liferepo_root / POINTER_RELATIVE_PATH
    pointer_path.parent.mkdir(parents=True, exist_ok=True)
    pointer = {
        "private_repo_name": repo_name,
    }
    # Keep config name-based by default; only add path when needed as override.
    if private_root.parent != liferepo_root.parent or private_root.name != repo_name:
        pointer["private_repo_path"] = os.path.relpath(private_root, liferepo_root)
    pointer_path.write_text(json.dumps(pointer, indent=2) + "\n", encoding="utf-8")
    return pointer_path


def read_soul_template(liferepo_root: Path) -> str:
    template_path = liferepo_root / "templates" / "SOUL.template.md"
    if template_path.exists():
        return template_path.read_text(encoding="utf-8").rstrip() + "\n"
    return (
        "# SOUL.md\n\n"
        "## Core\n\n"
        "- Be direct, clear, and pragmatic.\n"
        "- Optimize for useful outcomes, not performative verbosity.\n"
        "- Surface tradeoffs when decisions are non-obvious.\n"
    )


def read_private_runtime_template(liferepo_root: Path) -> str:
    template_path = liferepo_root / "templates" / "PRIVATE_RUNTIME.template.md"
    if template_path.exists():
        return template_path.read_text(encoding="utf-8").rstrip() + "\n"
    return (
        "# Private Runtime Overrides\n\n"
        "Use this file for private runtime quirks and local execution policy.\n"
    )


def ensure_private_soul(liferepo_root: Path, private_root: Path) -> bool:
    soul_path = private_root / "SOUL.md"
    if soul_path.exists():
        return False
    soul_path.write_text(read_soul_template(liferepo_root), encoding="utf-8")
    return True


def ensure_private_runtime(liferepo_root: Path, private_root: Path) -> bool:
    runtime_path = private_root / "PRIVATE_RUNTIME.md"
    if runtime_path.exists():
        return False
    runtime_path.write_text(
        read_private_runtime_template(liferepo_root), encoding="utf-8"
    )
    return True


def write_if_missing(path: Path, content: str) -> bool:
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")
    return True


def ensure_dirs(private_root: Path, relative_dirs: Iterable[str]) -> int:
    created = 0
    for rel in relative_dirs:
        path = private_root / rel
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            created += 1
    return created


def scaffold_journal(private_root: Path) -> list[str]:
    created_dirs = ensure_dirs(
        private_root,
        (
            "journal/summaries",
            "journal/sprints",
            "journal/reflections",
        ),
    )
    created_files = 0
    created_files += int(
        write_if_missing(
            private_root / "journal" / "README.md",
            (
                "# Private Journal\n\n"
                "Private journal state for your liferepo workflows.\n\n"
                "Suggested structure:\n"
                "- `summaries/`\n"
                "- `sprints/`\n"
                "- `reflections/`\n"
            ),
        )
    )
    return [f"journal: +{created_dirs} dirs, +{created_files} files"]


def scaffold_resume(private_root: Path) -> list[str]:
    created_dirs = ensure_dirs(
        private_root,
        (
            "Resume/sources/main",
            "Resume/variants",
            "Resume/archive",
        ),
    )
    created_files = 0
    created_files += int(
        write_if_missing(
            private_root / "Resume" / "README.md",
            (
                "# Private Resume\n\n"
                "Private resume source files, role-specific variants, and generated artifacts.\n\n"
                "Suggested structure:\n"
                "- `sources/main/`\n"
                "- `variants/`\n"
                "- `archive/`\n"
            ),
        )
    )
    return [f"resume: +{created_dirs} dirs, +{created_files} files"]


def scaffold_exports(private_root: Path) -> list[str]:
    created_dirs = ensure_dirs(
        private_root,
        (
            "scripts/exports/apple-notes",
            "scripts/exports/email",
            "scripts/exports/calendar",
        ),
    )
    created_files = 0
    created_files += int(
        write_if_missing(
            private_root / "scripts" / "exports" / "README.md",
            (
                "# Private Export Setup\n\n"
                "Private wrappers and credentials for personal data exports.\n\n"
                "Expected areas:\n"
                "- `apple-notes/`\n"
                "- `email/` (OAuth: Gmail API)\n"
                "- `calendar/` (OAuth: Google Calendar API)\n"
            ),
        )
    )
    created_files += int(
        write_if_missing(
            private_root / "scripts" / "exports" / "email" / "setup.md",
            (
                "# Gmail Export Setup\n\n"
                "1. Create Google Cloud OAuth client credentials.\n"
                "2. Enable Gmail API.\n"
                "3. Place `credentials.json` in this folder.\n"
                "4. Run your local export wrapper to generate token files.\n"
            ),
        )
    )
    created_files += int(
        write_if_missing(
            private_root / "scripts" / "exports" / "calendar" / "setup.md",
            (
                "# Calendar Export Setup\n\n"
                "1. Enable Google Calendar API in Google Cloud.\n"
                "2. Place `credentials.json` in this folder.\n"
                "3. Run your local export wrapper to generate token files.\n"
            ),
        )
    )
    created_files += int(
        write_if_missing(
            private_root / "scripts" / "exports" / "apple-notes" / "setup.md",
            (
                "# Apple Notes Export Setup (macOS)\n\n"
                "1. Grant Terminal automation access to Notes.\n"
                "2. Run your local Apple Notes export wrapper script.\n"
            ),
        )
    )
    return [f"exports: +{created_dirs} dirs, +{created_files} files"]


def prompt_yes_no(question: str, default: bool = False) -> bool:
    suffix = " [Y/n]: " if default else " [y/N]: "
    while True:
        raw = input(question + suffix).strip().lower()
        if not raw:
            return default
        if raw in {"y", "yes"}:
            return True
        if raw in {"n", "no"}:
            return False
        print("Please answer y or n.")


def main() -> int:
    args = parse_args()

    liferepo_root = resolve_liferepo_root(args.liferepo_root)
    repo_name, private_root = resolve_private_repo_root(
        liferepo_root=liferepo_root,
        name=args.private_repo_name,
        raw_path=args.private_repo_path,
    )

    if not private_root.exists():
        if args.create:
            private_root.mkdir(parents=True, exist_ok=True)
        else:
            raise FileNotFoundError(
                f"Private repo path does not exist: {private_root}\n"
                "Run with --create to create it."
            )

    write_marker(private_root)
    pointer_path = write_pointer(liferepo_root, repo_name, private_root)
    created_soul = ensure_private_soul(liferepo_root, private_root)
    created_runtime = ensure_private_runtime(liferepo_root, private_root)

    init_journal = args.init_all or args.init_journal
    init_resume = args.init_all or args.init_resume
    init_exports = args.init_all or args.init_exports

    if args.interactive:
        if not init_journal:
            init_journal = prompt_yes_no("Initialize private journal folders now?")
        if not init_resume:
            init_resume = prompt_yes_no("Initialize private Resume folders now?")
        if not init_exports:
            init_exports = prompt_yes_no("Initialize private export/OAuth folders now?")

    scaffold_notes: list[str] = []
    if init_journal:
        scaffold_notes.extend(scaffold_journal(private_root))
    if init_resume:
        scaffold_notes.extend(scaffold_resume(private_root))
    if init_exports:
        scaffold_notes.extend(scaffold_exports(private_root))

    print(f"liferepo root: {liferepo_root}")
    print(f"private repo:  {private_root}")
    print(f"pointer file:  {pointer_path}")
    print(f"marker file:   {private_root / MARKER_FILENAME}")
    print(f"SOUL.md:       {'created' if created_soul else 'exists'}")
    print(f"PRIVATE_RUNTIME.md: {'created' if created_runtime else 'exists'}")
    if scaffold_notes:
        print("scaffold:")
        for note in scaffold_notes:
            print(f"  - {note}")
    print("")
    print("Optional shell export:")
    print(f'export LIFEREPO_PRIVATE_ROOT="{private_root}"')

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
