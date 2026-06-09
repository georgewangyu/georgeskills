#!/usr/bin/env python3
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


def main() -> int:
    command = ignitionbot_command()
    completed = subprocess.run(command + sys.argv[1:], text=True)
    return completed.returncode


def ignitionbot_command() -> list[str]:
    installed = shutil.which("ignitionbot")
    if installed:
        return [installed]

    checkout = os.environ.get("IGNITIONBOT_DIR")
    if checkout:
        root = Path(checkout).expanduser().resolve()
        python = root / ".venv" / "bin" / "python"
        executable = str(python if python.exists() else sys.executable)
        env_path = str(root / "src")
        os.environ["PYTHONPATH"] = env_path + os.pathsep + os.environ.get("PYTHONPATH", "")
        return [executable, "-m", "ignitionbot"]

    print(
        "IgnitionBot not found. Install the `ignitionbot` command or set IGNITIONBOT_DIR.",
        file=sys.stderr,
    )
    return ["ignitionbot"]


if __name__ == "__main__":
    raise SystemExit(main())
