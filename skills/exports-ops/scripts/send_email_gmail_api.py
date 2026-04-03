#!/usr/bin/env python3
"""
Send Gmail messages for configured accounts using Gmail API.

Only accounts explicitly configured with allow_send=true may send.
The default behavior appends the configured assistant disclosure footer.
"""

from __future__ import annotations

import argparse
import base64
import mimetypes
import re
import sys
from datetime import datetime
from email import encoders
from email.mime.application import MIMEApplication
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html import escape
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


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return slug or "email"


def create_message(
    sender: str,
    to: str,
    subject: str,
    body: str,
    cc: str | None = None,
    attachments: list[Path] | None = None,
):
    attachments = attachments or []
    if attachments:
        msg = MIMEMultipart("mixed")
        msg.attach(MIMEText(body, _subtype="plain", _charset="utf-8"))
    else:
        msg = MIMEText(body, _subtype="plain", _charset="utf-8")

    msg["to"] = to
    msg["from"] = sender
    msg["subject"] = subject
    if cc:
        msg["cc"] = cc

    for attachment in attachments:
        if not attachment.exists():
            raise FileNotFoundError(f"Attachment not found: {attachment}")
        data = attachment.read_bytes()
        mime_type, _ = mimetypes.guess_type(attachment.name)
        if mime_type and mime_type.startswith("image/"):
            subtype = mime_type.split("/", 1)[1]
            part = MIMEImage(data, _subtype=subtype, name=attachment.name)
        elif mime_type == "application/pdf":
            part = MIMEApplication(data, _subtype="pdf", Name=attachment.name)
        else:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(data)
            encoders.encode_base64(part)
        part.add_header("Content-Disposition", "attachment", filename=attachment.name)
        msg.attach(part)

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    return {"raw": raw}


def build_preview_html(
    sender: str,
    to: str,
    subject: str,
    body: str,
    cc: str | None,
    attachments: list[Path],
) -> str:
    body_html = "<br>\n".join(escape(line) for line in body.rstrip().splitlines())
    image_blocks: list[str] = []
    file_blocks: list[str] = []

    for attachment in attachments:
        mime_type, _ = mimetypes.guess_type(attachment.name)
        if mime_type and mime_type.startswith("image/"):
            encoded = base64.b64encode(attachment.read_bytes()).decode("ascii")
            image_blocks.append(
                f"""
                <div class="attachment-card">
                  <div class="attachment-name">{escape(attachment.name)}</div>
                  <img src="data:{mime_type};base64,{encoded}" alt="{escape(attachment.name)}" />
                </div>
                """
            )
        else:
            file_blocks.append(f"<li>{escape(attachment.name)}</li>")

    attachments_html = ""
    if image_blocks or file_blocks:
        attachments_html += "<section><h2>Attachments</h2>"
        if image_blocks:
            attachments_html += '<div class="attachments-grid">' + "".join(image_blocks) + "</div>"
        if file_blocks:
            attachments_html += "<ul>" + "".join(file_blocks) + "</ul>"
        attachments_html += "</section>"

    cc_html = f"<div><strong>CC:</strong> {escape(cc)}</div>" if cc else ""
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>{escape(subject)}</title>
    <style>
      body {{
        background: #f5f7fb;
        color: #162033;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        margin: 0;
        padding: 32px;
      }}
      .frame {{
        background: #ffffff;
        border: 1px solid #d9e1ee;
        border-radius: 16px;
        box-shadow: 0 16px 48px rgba(28, 39, 60, 0.08);
        margin: 0 auto;
        max-width: 920px;
        overflow: hidden;
      }}
      .meta {{
        background: #eef3fb;
        border-bottom: 1px solid #d9e1ee;
        padding: 24px 28px;
      }}
      .subject {{
        font-size: 24px;
        font-weight: 700;
        margin: 0 0 16px;
      }}
      .meta div {{
        margin: 6px 0;
      }}
      .body {{
        font-size: 16px;
        line-height: 1.7;
        padding: 28px;
        white-space: normal;
      }}
      section {{
        border-top: 1px solid #e6ebf4;
        padding: 28px;
      }}
      h2 {{
        font-size: 18px;
        margin: 0 0 18px;
      }}
      .attachments-grid {{
        display: grid;
        gap: 20px;
      }}
      .attachment-card {{
        border: 1px solid #d9e1ee;
        border-radius: 14px;
        overflow: hidden;
      }}
      .attachment-name {{
        background: #f7f9fd;
        border-bottom: 1px solid #d9e1ee;
        font-size: 13px;
        font-weight: 600;
        padding: 12px 14px;
      }}
      img {{
        display: block;
        height: auto;
        max-width: 100%;
      }}
    </style>
  </head>
  <body>
    <div class="frame">
      <div class="meta">
        <div class="subject">{escape(subject)}</div>
        <div><strong>From:</strong> {escape(sender)}</div>
        <div><strong>To:</strong> {escape(to)}</div>
        {cc_html}
      </div>
      <div class="body">{body_html}</div>
      {attachments_html}
    </div>
  </body>
</html>
"""


def write_preview_artifacts(
    preview_dir: Path,
    sender: str,
    to: str,
    subject: str,
    body: str,
    cc: str | None,
    attachments: list[Path],
):
    preview_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    stem = f"{stamp}_{slugify(subject)}"
    eml_path = preview_dir / f"{stem}.eml"
    html_path = preview_dir / f"{stem}.html"

    raw_message = create_message(sender, to, subject, body, cc=cc, attachments=attachments)
    message_bytes = base64.urlsafe_b64decode(raw_message["raw"].encode("utf-8"))
    eml_path.write_bytes(message_bytes)
    html_path.write_text(
        build_preview_html(sender, to, subject, body, cc=cc, attachments=attachments),
        encoding="utf-8",
    )
    return eml_path, html_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Send Gmail email for an allow_send-enabled account.")
    parser.add_argument("--account", required=True, help="Configured account email address")
    parser.add_argument("--to", help="Recipient email address")
    parser.add_argument("--subject", help="Email subject")
    parser.add_argument("--body", help="Email body text")
    parser.add_argument("--body-file", help="Path to plain text body file")
    parser.add_argument("--cc", help="Optional CC email address")
    parser.add_argument(
        "--attach",
        action="append",
        default=[],
        help="Attachment file path. Repeat for multiple attachments.",
    )
    parser.add_argument("--preview-dir", help="Directory to write .eml and .html preview artifacts")
    parser.add_argument("--preview-only", action="store_true", help="Generate preview artifacts without sending")
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

    if args.auth_only:
        creds = account.get_credentials()
        if creds is None:
            return 1
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
    attachments = [Path(path).expanduser().resolve() for path in args.attach]

    if args.preview_dir or args.preview_only:
        preview_dir = Path(args.preview_dir or ".email-previews").expanduser().resolve()
        eml_path, html_path = write_preview_artifacts(
            preview_dir,
            account.email,
            args.to,
            args.subject,
            body,
            cc=args.cc,
            attachments=attachments,
        )
        print(f"Preview EML: {eml_path}")
        print(f"Preview HTML: {html_path}")

    if args.preview_only:
        print("Preview only; email was not sent.")
        return 0

    creds = account.get_credentials()
    if creds is None:
        return 1

    service = build("gmail", "v1", credentials=creds)
    message = create_message(account.email, args.to, args.subject, body, cc=args.cc, attachments=attachments)

    try:
        result = service.users().messages().send(userId="me", body=message).execute()
    except HttpError as exc:
        print(f"Failed to send email: {exc}", file=sys.stderr)
        return 1

    print(f"Sent message id: {result.get('id')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
