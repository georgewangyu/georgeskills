#!/usr/bin/env python3
"""
Verify Gmail OAuth scopes for configured accounts.

Fails fast if a token contains dangerous scopes or if the token scopes do not
match the configured account permissions.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from repo_paths import resolve_private_repo_root

PRIVATE_REPO_ROOT = resolve_private_repo_root()
SCRIPT_DIR = PRIVATE_REPO_ROOT / "scripts" / "exports" / "email"
CONFIG_FILE = SCRIPT_DIR / "config.json"
TOKEN_DIR = SCRIPT_DIR / "tokens"

GMAIL_READONLY_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"

DANGEROUS_SCOPES = {
    "https://www.googleapis.com/auth/gmail.modify",
    "https://mail.google.com/",
}


def token_file_for(email: str) -> Path:
    email_safe = email.replace("@", "_at_").replace(".", "_")
    return TOKEN_DIR / f"token_{email_safe}.json"


def expected_scopes_for(account: dict) -> set[str]:
    scopes = {GMAIL_READONLY_SCOPE}
    if account.get("allow_send", False):
        scopes.add(GMAIL_SEND_SCOPE)
    return scopes


def main() -> int:
    config = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    failures = []

    for account in config.get("accounts", []):
        if not account.get("enabled", True):
            continue

        email = account["email"]
        token_file = token_file_for(email)
        expected = expected_scopes_for(account)

        print(email)
        print(f"  expected: {sorted(expected)}")

        if not token_file.exists():
            print(f"  token: missing ({token_file.name})")
            failures.append(f"{email}: missing token")
            continue

        token_data = json.loads(token_file.read_text(encoding="utf-8"))
        actual = set(token_data.get("scopes", []))
        print(f"  actual:   {sorted(actual)}")

        dangerous = sorted(actual & DANGEROUS_SCOPES)
        if dangerous:
            failures.append(f"{email}: dangerous scopes present: {dangerous}")

        if actual != expected:
            failures.append(f"{email}: scope mismatch (expected {sorted(expected)}, got {sorted(actual)})")

    if failures:
        print("\nFAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("\nPASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
