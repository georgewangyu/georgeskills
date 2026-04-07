#!/usr/bin/env python3
import sys
import os
import subprocess
import argparse
import json
import re
from pathlib import Path
from typing import Any

# Simple path resolution for georgerepo tokens
WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
PRIVATE_REPO = WORKSPACE_ROOT / "georgerepo"
DEFAULT_TOKEN_FILE = PRIVATE_REPO / ".tokens" / "x-twitter.env"

def load_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    loaded: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        loaded[key] = value
    return loaded

def run_bird(args):
    """Executes the original bird CLI via npx."""
    cmd = ["npx", "--yes", "@steipete/bird"] + args
    result = subprocess.run(cmd, capture_output=True, text=True, env=load_env_file(Path.home() / ".tokens/x-twitter.env"))
    return result

def post_tweet(content, reply_to=None, stealth=False):
    if not content:
        print("Error: No content provided for tweet.")
        return None

    # Reverting to original bird (with tokens)
    print(f"Using Original Bird (npx) to post to X...")
    args = ["tweet", content]
    result = run_bird(args)

    if result.returncode == 0:
        print(f"Successfully posted via Original Bird!")
        return "SUCCESS_ORIGINAL"
    else:
        print("Failed to post to X via Original Bird.")
        if result: print(result.stderr)
        return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Post a tweet or reply to X using the bird CLI.")
    parser.add_argument("--tweet", required=True, help="The content of the tweet.")
    parser.add_argument("--reply-to", help="The ID or URL of the tweet to reply to.")
    parser.add_argument("--stealth", action="store_true", default=True, help="Use browser-based posting (native x-agent).")
    args = parser.parse_args()

    tid = post_tweet(args.tweet, reply_to=args.reply_to, stealth=args.stealth)
    if not tid:
        sys.exit(1)

    # Print the ID to stdout so it can be captured by the caller
    print(f"TWEET_ID:{tid}")
