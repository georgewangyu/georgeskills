import subprocess
import argparse
import sys
from pathlib import Path

# Path to your native source repo
NATIVE_BIRD_ROOT = Path(__file__).resolve().parents[4] / "xbot"
CLI_PATH = NATIVE_BIRD_ROOT / "src" / "cli.js"

def run_native_cli(args):
    """Executes the native Node.js CLI."""
    if not CLI_PATH.exists():
        print(f"Error: Native CLI not found at {CLI_PATH}")
        sys.exit(1)

    cmd = ["node", str(CLI_PATH)] + args
    try:
        # Use a headless browser by default for fetches, visible for posts if needed
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result
    except Exception as e:
        print(f"Failed to execute native CLI: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Native X-Agent Skills")
    parser.add_argument("--post", help="Post a tweet using xbot's official API path.")
    parser.add_argument("--reply-to", help="Optional tweet ID to reply to when used with --post.")
    parser.add_argument("--fetch", choices=["home", "bookmarks"], help="Fetch a feed using the active browser session.")
    parser.add_argument("--user", help="Fetch a specific user's timeline (e.g. your own handle).")
    parser.add_argument("--count", type=int, default=10, help="Number of items to fetch.")

    args = parser.parse_args()

    if args.post:
        print(f"Posting to X (Official API): {args.post[:50]}...")
        post_args = ["post"]
        if args.reply_to:
            post_args.extend(["--reply-to", args.reply_to])
        post_args.append(args.post)
        res = run_native_cli(post_args)
        if res and res.returncode == 0:
            print("Successfully posted!")
        else:
            print("Failed to post.")
            if res: print(res.stderr)

    if args.fetch:
        print(f"Fetching {args.fetch} feed (Native Session)...")
        res = run_native_cli([args.fetch, "--count", str(args.count)])
        if res and res.returncode == 0:
            print(res.stdout)
        else:
            print(f"Failed to fetch {args.fetch}.")
            if res: print(res.stderr)

    if args.user:
        print(f"Fetching posts for @{args.user} (Native Session)...")
        res = run_native_cli(["user", args.user, "--count", str(args.count)])
        if res and res.returncode == 0:
            print(res.stdout)
        else:
            print(f"Failed to fetch @{args.user}.")
            if res: print(res.stderr)

if __name__ == "__main__":
    main()
