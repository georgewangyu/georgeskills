# Native X-Agent (Stealth Mode)

This skill provides a native, browser-based interface for X/Twitter that bypasses bot detection and reuses your active Chrome session.

## Configuration

The skill uses your local source implementation located in:
`georgerepo/xbot/`

It automatically attempts to use your primary Google Chrome profile:
`~/Library/Application Support/Google/Chrome/Default`

## Usage

### Post a Tweet (Stealth Mode)
Posts a tweet by automating your real browser UI.
```bash
python3 scripts/native_x_ops.py --post "Your tweet content here"
```

### Fetch Home Feed
Retrieves your "For You" timeline using your active browser session.
```bash
python3 scripts/native_x_ops.py --fetch home --count 10
```

## Troubleshooting
- **SingletonLock**: If you get a "File exists" error for `SingletonLock`, close Google Chrome before running the script, or run it while Chrome is closed.
