#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compile a LaTeX resume file to PDF with build artifacts under build/."
    )
    parser.add_argument("tex_file", help="Path to .tex file (relative to project root or absolute).")
    parser.add_argument(
        "--project-root",
        default=".",
        help="Project root used for relative paths and build directory placement.",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Optional output PDF path. Defaults to source directory with same basename.",
    )
    return parser.parse_args()


def resolve_paths(args: argparse.Namespace) -> tuple[Path, Path, Path, Path]:
    project_root = Path(args.project_root).expanduser().resolve()
    tex_path = Path(args.tex_file).expanduser()
    if not tex_path.is_absolute():
        tex_path = (project_root / tex_path).resolve()
    if tex_path.suffix.lower() != ".tex":
        raise ValueError("tex_file must end with .tex")
    if not tex_path.exists():
        raise FileNotFoundError(f"File not found: {tex_path}")

    source_dir = tex_path.parent
    base_name = tex_path.stem
    relative_source_dir = source_dir.relative_to(project_root)
    build_dir = project_root / "build" / relative_source_dir
    build_dir.mkdir(parents=True, exist_ok=True)

    if args.output:
        output_pdf = Path(args.output).expanduser()
        if not output_pdf.is_absolute():
            output_pdf = (project_root / output_pdf).resolve()
    else:
        output_pdf = source_dir / f"{base_name}.pdf"

    return project_root, tex_path, build_dir, output_pdf


def compile_tex(tex_path: Path, build_dir: Path) -> None:
    cmd = [
        "pdflatex",
        "-interaction=nonstopmode",
        f"-output-directory={build_dir}",
        str(tex_path),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise RuntimeError("pdflatex not found; install a LaTeX distribution.") from exc
    except subprocess.CalledProcessError as exc:
        err = (exc.stderr or "").strip()
        raise RuntimeError(f"pdflatex failed for {tex_path}\n{err}") from exc


def main() -> int:
    args = parse_args()
    try:
        project_root, tex_path, build_dir, output_pdf = resolve_paths(args)
        compile_tex(tex_path, build_dir)
        built_pdf = build_dir / f"{tex_path.stem}.pdf"
        if not built_pdf.exists():
            raise RuntimeError(f"Expected PDF not found: {built_pdf}")
        output_pdf.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(built_pdf), str(output_pdf))
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"project root: {project_root}")
    print(f"source tex:   {tex_path}")
    print(f"output pdf:   {output_pdf}")
    print(f"build dir:    {build_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
