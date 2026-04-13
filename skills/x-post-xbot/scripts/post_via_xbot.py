#!/usr/bin/env python3
import argparse
import subprocess
import sys
from pathlib import Path


WORKSPACE_ROOT = Path(__file__).resolve().parents[4]
CLI_PATH = WORKSPACE_ROOT / "xbot" / "src" / "cli.js"


def main() -> int:
    parser = argparse.ArgumentParser(description="Post to X via the local xbot official API path.")
    parser.add_argument("--tweet", required=True, help="Tweet text to post.")
    parser.add_argument("--reply-to", help="Optional tweet ID to reply to.")
    args = parser.parse_args()

    if not CLI_PATH.exists():
        print(f"Error: xbot CLI not found at {CLI_PATH}", file=sys.stderr)
        return 1

    cmd = ["node", str(CLI_PATH), "post"]
    if args.reply_to:
        cmd.extend(["--reply-to", args.reply_to])
    cmd.append(args.tweet)

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
