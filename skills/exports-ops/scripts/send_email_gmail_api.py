#!/usr/bin/env python3
"""
Send Gmail messages for configured accounts using Gmail API.

Only accounts explicitly configured with allow_send=true may send.
The default behavior appends the configured assistant disclosure footer.
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
from email.mime.text import MIMEText
from pathlib import Path

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from export_emails_gmail_api import load_accounts


def find_account(email: str):
    for account in load_accounts():
        if account.email.lower() == email.lower():
            return account
    return None


def build_body(body: str, assistant_signature: str | None, append_signature: bool) -> str:
    body = body.rstrip()
    if append_signature and assistant_signature:
        if assistant_signature not in body:
            body = f"{body}\n\n---\n{assistant_signature}"
    return body + "\n"


def create_message(sender: str, to: str, subject: str, body: str, cc: str | None = None) -> dict:
    msg = MIMEText(body)
    msg["to"] = to
    msg["from"] = sender
    msg["subject"] = subject
    if cc:
        msg["cc"] = cc
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    return {"raw": raw}


def main() -> int:
    parser = argparse.ArgumentParser(description="Send Gmail email for an allow_send-enabled account.")
    parser.add_argument("--account", required=True, help="Configured account email address")
    parser.add_argument("--to", help="Recipient email address")
    parser.add_argument("--subject", help="Email subject")
    parser.add_argument("--body", help="Email body text")
    parser.add_argument("--body-file", help="Path to plain text body file")
    parser.add_argument("--cc", help="Optional CC email address")
    parser.add_argument("--no-signature", action="store_true", help="Do not append assistant disclosure footer")
    parser.add_argument("--auth-only", action="store_true", help="Only run OAuth/auth verification and save token")
    parser.add_argument("--reauth", action="store_true", help="Delete the existing token for this account first")
    args = parser.parse_args()

    account = find_account(args.account)
    if account is None:
        print(f"Unknown account: {args.account}", file=sys.stderr)
        return 1
    if not account.allow_send:
        print(f"Account is not send-enabled: {account.email}", file=sys.stderr)
        return 1

    if args.reauth and account.token_file.exists():
        account.token_file.unlink()
        print(f"Deleted existing token for {account.email}; re-authentication required.")

    creds = account.get_credentials()
    if creds is None:
        return 1

    if args.auth_only:
        print(f"Authentication complete for {account.email}")
        print(f"Scopes: {', '.join(account.scopes)}")
        return 0

    if not args.to or not args.subject or (not args.body and not args.body_file):
        print("--to, --subject, and one of --body/--body-file are required unless --auth-only is used.", file=sys.stderr)
        return 1

    body = args.body
    if args.body_file:
        body = Path(args.body_file).read_text(encoding="utf-8")

    body = build_body(body, account.assistant_signature, not args.no_signature)
    service = build("gmail", "v1", credentials=creds)
    message = create_message(account.email, args.to, args.subject, body, cc=args.cc)

    try:
        result = service.users().messages().send(userId="me", body=message).execute()
    except HttpError as exc:
        print(f"Failed to send email: {exc}", file=sys.stderr)
        return 1

    print(f"Sent message id: {result.get('id')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
