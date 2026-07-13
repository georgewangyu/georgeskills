#!/usr/bin/env python3
"""Build and verify a native Apple Silicon MLX Whisper runtime."""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


DEFAULT_PACKAGE = "mlx-whisper==0.4.3"


def run(command: list[str], *, env: dict[str, str] | None = None) -> None:
    print("+", " ".join(command))
    subprocess.run(command, check=True, env=env)


def native_python(candidate: str | None) -> Path:
    choices = [candidate] if candidate else []
    choices.extend(
        [
            "/opt/homebrew/bin/python3.13",
            "/opt/homebrew/bin/python3",
            shutil.which("python3"),
        ]
    )
    for raw in choices:
        if not raw:
            continue
        path = Path(raw).expanduser().resolve()
        if not path.exists():
            continue
        machine = subprocess.check_output(
            [str(path), "-c", "import platform; print(platform.machine())"],
            text=True,
        ).strip()
        if machine == "arm64":
            return path
    raise SystemExit("No native arm64 Python found. Install Apple Silicon Python under /opt/homebrew first.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-dir", required=True, help="Durable runtime root, preferably outside disposable repos/caches.")
    parser.add_argument("--cache-dir", required=True, help="Durable Hugging Face cache root.")
    parser.add_argument("--python", help="Native arm64 Python executable. Auto-detected when omitted.")
    parser.add_argument("--package", default=DEFAULT_PACKAGE, help="MLX Whisper requirement to install.")
    parser.add_argument("--rebuild", action="store_true", help="Replace an existing venv before installing.")
    args = parser.parse_args()

    if platform.system() != "Darwin" or platform.machine() != "arm64":
        raise SystemExit("MLX Whisper bootstrap requires an Apple Silicon macOS process (arm64).")

    runtime_dir = Path(args.runtime_dir).expanduser().resolve()
    cache_dir = Path(args.cache_dir).expanduser().resolve()
    venv_dir = runtime_dir / "venv"
    python = native_python(args.python)
    uv = shutil.which("uv")

    runtime_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)
    (runtime_dir / ".protected-mlx-whisper-runtime").touch()
    (cache_dir / ".protected-mlx-whisper-cache").touch()

    if args.rebuild and venv_dir.exists():
        shutil.rmtree(venv_dir)

    if not (venv_dir / "bin/python").exists():
        if uv:
            run([uv, "venv", "--python", str(python), str(venv_dir)])
        else:
            run([str(python), "-m", "venv", str(venv_dir)])

    if uv:
        run(
            [
                uv,
                "pip",
                "install",
                "--link-mode",
                "copy",
                "--python",
                str(venv_dir / "bin/python"),
                args.package,
                "scipy",
            ]
        )
    else:
        run([str(venv_dir / "bin/python"), "-m", "pip", "install", args.package, "scipy"])

    env = os.environ.copy()
    env["HF_HOME"] = str(cache_dir)
    check = (
        "import platform, mlx, mlx_whisper, scipy; "
        "assert platform.machine() == 'arm64'; "
        "print('native_arm64=ok'); "
        "print('mlx_whisper=' + getattr(mlx_whisper, '__version__', 'unknown')); "
        "print('scipy=' + scipy.__version__)"
    )
    run([str(venv_dir / "bin/python"), "-c", check], env=env)
    print(f"runtime={runtime_dir}")
    print(f"cache={cache_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
