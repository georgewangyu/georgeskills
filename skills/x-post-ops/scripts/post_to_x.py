#!/usr/bin/env python3
from __future__ import annotations

import sys
import os
import subprocess
import argparse
from pathlib import Path

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

def resolve_token_file(
    token_file: str | None,
    private_repo: str | None,
) -> Path | None:
    raw_token_file = token_file or os.environ.get("X_TWITTER_TOKEN_FILE", "").strip()
    if raw_token_file:
        return Path(raw_token_file).expanduser().resolve()

    raw_private_repo = private_repo
    if not raw_private_repo:
        for key in ("LIFEREPO_PRIVATE_ROOT", "PRIVATE_REPO_ROOT"):
            raw_private_repo = os.environ.get(key, "").strip()
            if raw_private_repo:
                break
    if raw_private_repo:
        return Path(raw_private_repo).expanduser().resolve() / ".tokens" / "x-twitter.env"
    return None


def run_bird(args: list[str], token_file: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Executes the original bird CLI via npx."""
    cmd = ["npx", "--yes", "@steipete/bird"] + args
    env = dict(os.environ)
    if token_file is not None:
        if not token_file.exists():
            raise FileNotFoundError(f"Token file not found: {token_file}")
        env.update(load_env_file(token_file))
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    return result

def post_tweet(
    content: str,
    reply_to: str | None = None,
    stealth: bool = False,
    token_file: Path | None = None,
) -> str | None:
    if not content:
        print("Error: No content provided for tweet.")
        return None

    # Reverting to original bird (with tokens)
    print("Using Original Bird (npx) to post to X...")
    args = ["tweet", content]
    result = run_bird(args, token_file=token_file)

    if result.returncode == 0:
        print("Successfully posted via Original Bird!")
        return "SUCCESS_ORIGINAL"
    else:
        print("Failed to post to X via Original Bird.")
        if result.stderr:
            print(result.stderr)
        return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Post a tweet or reply to X using the bird CLI.")
    parser.add_argument("--tweet", required=True, help="The content of the tweet.")
    parser.add_argument("--reply-to", help="The ID or URL of the tweet to reply to.")
    parser.add_argument("--stealth", action="store_true", default=True, help="Use browser-based posting (native x-agent).")
    parser.add_argument(
        "--token-file",
        help="Env file containing Bird credentials (or X_TWITTER_TOKEN_FILE).",
    )
    parser.add_argument(
        "--private-repo",
        help=(
            "Private repo root used to infer .tokens/x-twitter.env. Defaults "
            "to LIFEREPO_PRIVATE_ROOT or PRIVATE_REPO_ROOT."
        ),
    )
    args = parser.parse_args()

    try:
        token_file = resolve_token_file(args.token_file, args.private_repo)
        tid = post_tweet(
            args.tweet,
            reply_to=args.reply_to,
            stealth=args.stealth,
            token_file=token_file,
        )
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(2)
    if not tid:
        sys.exit(1)

    # Print the ID to stdout so it can be captured by the caller
    print(f"TWEET_ID:{tid}")
