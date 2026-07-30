#!/usr/bin/env python3
"""Measure whether a one-page resume uses the page without becoming cramped."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile


def pdf_page_count(pdf_path: Path) -> int:
    result = subprocess.run(
        ["pdfinfo", str(pdf_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    for line in result.stdout.splitlines():
        if line.startswith("Pages:"):
            return int(line.split(":", 1)[1].strip())
    raise RuntimeError("pdfinfo did not report a page count")


def render_first_page(pdf_path: Path, output_stem: Path, dpi: int) -> Path:
    if shutil.which("pdftoppm") is None:
        raise RuntimeError("pdftoppm is required")
    subprocess.run(
        [
            "pdftoppm",
            "-f",
            "1",
            "-l",
            "1",
            "-singlefile",
            "-gray",
            "-r",
            str(dpi),
            str(pdf_path),
            str(output_stem),
        ],
        check=True,
        capture_output=True,
    )
    image_path = output_stem.with_suffix(".pgm")
    if not image_path.exists():
        raise RuntimeError("pdftoppm did not produce the expected PGM image")
    return image_path


def read_pgm(image_path: Path) -> tuple[int, int, bytes]:
    data = image_path.read_bytes()
    index = 0

    def token() -> bytes:
        nonlocal index
        while index < len(data):
            if data[index : index + 1] == b"#":
                index = data.find(b"\n", index) + 1
                continue
            if not data[index : index + 1].isspace():
                break
            index += 1
        start = index
        while index < len(data) and not data[index : index + 1].isspace():
            index += 1
        return data[start:index]

    if token() != b"P5":
        raise RuntimeError("Expected a binary grayscale PGM image")
    width = int(token())
    height = int(token())
    max_value = int(token())
    if max_value != 255:
        raise RuntimeError(f"Unsupported PGM max value: {max_value}")
    while index < len(data) and data[index : index + 1].isspace():
        index += 1
    pixels = data[index:]
    if len(pixels) != width * height:
        raise RuntimeError("PGM pixel data has an unexpected size")
    return width, height, pixels


def content_bounds(image_path: Path, threshold: int = 245) -> dict[str, float]:
    width, height, pixels = read_pgm(image_path)

    min_row_ink = max(5, round(width * 0.002))
    min_col_ink = max(5, round(height * 0.002))
    row_counts = []
    col_counts = [0] * width
    for y in range(height):
        row = pixels[y * width : (y + 1) * width]
        row_count = 0
        for x, value in enumerate(row):
            if value < threshold:
                row_count += 1
                col_counts[x] += 1
        row_counts.append(row_count)
    ink_rows = [index for index, count in enumerate(row_counts) if count >= min_row_ink]
    ink_cols = [index for index, count in enumerate(col_counts) if count >= min_col_ink]
    if not ink_rows or not ink_cols:
        raise RuntimeError("No meaningful page content detected")

    top, bottom = min(ink_rows), max(ink_rows)
    left, right = min(ink_cols), max(ink_cols)
    dark_pixels = sum(row_counts)
    return {
        "width_px": width,
        "height_px": height,
        "top_px": top,
        "bottom_px": bottom,
        "left_px": left,
        "right_px": right,
        "content_height_pct": round((bottom - top + 1) / height * 100, 2),
        "content_width_pct": round((right - left + 1) / width * 100, 2),
        "ink_density_pct": round(dark_pixels / (width * height) * 100, 3),
    }


def evaluate(args: argparse.Namespace) -> dict[str, object]:
    pdf_path = Path(args.pdf).expanduser().resolve()
    if not pdf_path.exists():
        raise FileNotFoundError(pdf_path)

    pages = pdf_page_count(pdf_path)
    with tempfile.TemporaryDirectory(prefix="resume-utilization-") as temp_dir:
        image_path = render_first_page(
            pdf_path,
            Path(temp_dir) / "page",
            args.dpi,
        )
        metrics = content_bounds(image_path, threshold=args.white_threshold)

    height = metrics["height_px"]
    width = metrics["width_px"]
    metrics.update(
        {
            "top_whitespace_in": round(metrics["top_px"] / args.dpi, 2),
            "bottom_whitespace_in": round(
                (height - 1 - metrics["bottom_px"]) / args.dpi,
                2,
            ),
            "left_whitespace_in": round(metrics["left_px"] / args.dpi, 2),
            "right_whitespace_in": round(
                (width - 1 - metrics["right_px"]) / args.dpi,
                2,
            ),
        }
    )

    failures = []
    warnings = []
    if pages != 1:
        failures.append(f"expected exactly one page; found {pages}")
    if metrics["content_height_pct"] < args.min_content_height_pct:
        failures.append(
            "underfilled page: content height "
            f"{metrics['content_height_pct']}% < {args.min_content_height_pct}%"
        )
    if metrics["bottom_whitespace_in"] > args.max_bottom_whitespace_in:
        failures.append(
            "excessive bottom whitespace: "
            f"{metrics['bottom_whitespace_in']}in > {args.max_bottom_whitespace_in}in"
        )
    if metrics["bottom_whitespace_in"] < args.min_bottom_whitespace_in:
        failures.append(
            "crowded bottom edge: "
            f"{metrics['bottom_whitespace_in']}in < {args.min_bottom_whitespace_in}in"
        )
    if metrics["left_whitespace_in"] < args.min_side_whitespace_in:
        warnings.append("left content edge may be too close to the trim edge")
    if metrics["right_whitespace_in"] < args.min_side_whitespace_in:
        warnings.append("right content edge may be too close to the trim edge")

    return {
        "pdf": str(pdf_path),
        "pages": pages,
        "status": "PASS" if not failures else "FAIL",
        "metrics": metrics,
        "failures": failures,
        "warnings": warnings,
        "note": (
            "This is a layout gate, not a content-quality score. A passing span "
            "must still be achieved with relevant evidence and readable typography."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf")
    parser.add_argument("--dpi", type=int, default=144)
    parser.add_argument("--white-threshold", type=int, default=245)
    parser.add_argument("--min-content-height-pct", type=float, default=80.0)
    parser.add_argument("--max-bottom-whitespace-in", type=float, default=1.25)
    parser.add_argument("--min-bottom-whitespace-in", type=float, default=0.35)
    parser.add_argument("--min-side-whitespace-in", type=float, default=0.4)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report = evaluate(args)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        metrics = report["metrics"]
        print(f"{report['status']}: {report['pdf']}")
        print(
            "pages={pages} content_height={height}% bottom_blank={bottom}in "
            "left_blank={left}in right_blank={right}in".format(
                pages=report["pages"],
                height=metrics["content_height_pct"],
                bottom=metrics["bottom_whitespace_in"],
                left=metrics["left_whitespace_in"],
                right=metrics["right_whitespace_in"],
            )
        )
        for failure in report["failures"]:
            print(f"FAIL: {failure}")
        for warning in report["warnings"]:
            print(f"WARN: {warning}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
