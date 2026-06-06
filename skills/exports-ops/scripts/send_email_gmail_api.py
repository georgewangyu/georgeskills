#!/usr/bin/env python3
"""
Send Gmail messages for configured accounts using Gmail API.

Only accounts explicitly configured with allow_send=true may send.
The default behavior appends the configured assistant disclosure footer.
"""

from __future__ import annotations

import argparse
import base64
import csv
import json
import mimetypes
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from email.header import decode_header, make_header
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


THREAD_LOCAL = threading.local()


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


def decode_mime_header(value: str | None) -> str | None:
    if not value:
        return value
    try:
        return str(make_header(decode_header(value)))
    except Exception:
        return value


def extract_reply_message_id(export_path: Path) -> str:
    text = export_path.read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.startswith("message_id:"):
            return line.split(":", 1)[1].strip()
    raise ValueError(f"Could not find message_id in export: {export_path}")


def get_header_value(headers: list[dict], name: str) -> str | None:
    for header in headers:
        if header.get("name", "").lower() == name.lower():
            return header.get("value")
    return None


def load_reply_context(service, message_id: str) -> dict:
    message = service.users().messages().get(
        userId="me",
        id=message_id,
        format="metadata",
        metadataHeaders=["Message-ID", "References", "Subject"],
    ).execute()
    payload = message.get("payload", {})
    headers = payload.get("headers", [])
    original_subject = decode_mime_header(get_header_value(headers, "Subject")) or ""
    original_message_id = get_header_value(headers, "Message-ID")
    original_references = get_header_value(headers, "References")
    thread_id = message.get("threadId")

    references = original_references.strip() if original_references else ""
    if original_message_id:
        references = f"{references} {original_message_id}".strip()

    return {
        "thread_id": thread_id,
        "message_id_header": original_message_id,
        "references": references or None,
        "subject": original_subject,
    }


def create_message(
    sender: str,
    to: str,
    subject: str,
    body: str,
    cc: str | None = None,
    attachments: list[Path] | None = None,
    in_reply_to: str | None = None,
    references: str | None = None,
    thread_id: str | None = None,
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
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
    if references:
        msg["References"] = references

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
    message = {"raw": raw}
    if thread_id:
        message["threadId"] = thread_id
    return message


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
    in_reply_to: str | None = None,
    references: str | None = None,
    thread_id: str | None = None,
):
    preview_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    stem = f"{stamp}_{slugify(subject)}"
    eml_path = preview_dir / f"{stem}.eml"
    html_path = preview_dir / f"{stem}.html"

    raw_message = create_message(
        sender,
        to,
        subject,
        body,
        cc=cc,
        attachments=attachments,
        in_reply_to=in_reply_to,
        references=references,
        thread_id=thread_id,
    )
    message_bytes = base64.urlsafe_b64decode(raw_message["raw"].encode("utf-8"))
    eml_path.write_bytes(message_bytes)
    html_path.write_text(
        build_preview_html(sender, to, subject, body, cc=cc, attachments=attachments),
        encoding="utf-8",
    )
    return eml_path, html_path


def ensure_csv_fieldnames(rows: list[dict[str, str]], fieldnames: list[str], required: list[str]) -> list[str]:
    merged = list(fieldnames)
    existing = set(merged)
    for name in required:
        if name not in existing:
            merged.append(name)
            existing.add(name)
    for row in rows:
        for name in merged:
            row.setdefault(name, "")
    return merged


def get_thread_service(account):
    service = getattr(THREAD_LOCAL, "gmail_service", None)
    service_email = getattr(THREAD_LOCAL, "gmail_service_email", None)
    if service is None or service_email != account.email.lower():
        creds = account.get_credentials()
        if creds is None:
            raise RuntimeError(f"Could not load credentials for {account.email}")
        service = build("gmail", "v1", credentials=creds)
        THREAD_LOCAL.gmail_service = service
        THREAD_LOCAL.gmail_service_email = account.email.lower()
    return service


def send_message_via_service(
    service,
    sender: str,
    to: str,
    subject: str,
    body: str,
    cc: str | None = None,
    attachments: list[Path] | None = None,
    reply_context: dict | None = None,
) -> str:
    message = create_message(
        sender,
        to,
        subject,
        body,
        cc=cc,
        attachments=attachments,
        in_reply_to=reply_context["message_id_header"] if reply_context else None,
        references=reply_context["references"] if reply_context else None,
        thread_id=reply_context["thread_id"] if reply_context else None,
    )
    result = service.users().messages().send(userId="me", body=message).execute()
    return result.get("id", "")


def run_batch_send(
    account,
    batch_csv: Path,
    output_csv: Path,
    log_path: Path | None,
    to_column: str,
    subject_column: str,
    body_column: str,
    max_workers: int,
    skip_sent: bool,
    cc: str | None,
    attachments: list[Path],
    append_signature: bool,
) -> int:
    if max_workers < 1:
        raise ValueError("--max-workers must be at least 1")

    with batch_csv.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fieldnames = reader.fieldnames or []

    required_fields = [
        "lead_id",
        "draft_status",
        "send_status",
        "delivery_status",
        "last_subject",
        "last_sent_at",
        "gmail_message_id",
        "last_error",
    ]
    fieldnames = ensure_csv_fieldnames(rows, fieldnames, required_fields)

    now = datetime.now().astimezone()
    batch_id = now.strftime("%Y%m%dT%H%M%S")
    pending: list[tuple[int, dict[str, str]]] = []
    skipped = 0

    for index, row in enumerate(rows):
        lead_id = row.get("lead_id", "").strip() or f"lead-{index + 1}"
        row["lead_id"] = lead_id
        recipient = row.get(to_column, "").strip()
        subject = row.get(subject_column, "").strip()
        body = row.get(body_column, "").strip()
        send_status = row.get("send_status", "").strip().lower()
        if not recipient or not subject or not body:
            row["last_error"] = f"Missing required batch fields: {to_column}, {subject_column}, or {body_column}"
            row["send_status"] = "skipped"
            skipped += 1
            continue
        if skip_sent and send_status in {"sent", "delivered", "replied"}:
            skipped += 1
            continue
        pending.append((index, row))

    if log_path:
        log_path.parent.mkdir(parents=True, exist_ok=True)

    def emit_log(event: dict[str, str]) -> None:
        if not log_path:
            return
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")

    def worker(index: int, row: dict[str, str]) -> tuple[int, str, str]:
        service = get_thread_service(account)
        subject = row[subject_column].strip()
        body = build_body(row[body_column], account.assistant_signature, append_signature)
        to = row[to_column].strip()
        message_id = send_message_via_service(
            service,
            account.email,
            to,
            subject,
            body,
            cc=cc,
            attachments=attachments,
        )
        return index, message_id, ""

    sent = 0
    failed = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {
            executor.submit(worker, index, row): (index, row)
            for index, row in pending
        }
        for future in as_completed(future_map):
            index, row = future_map[future]
            stamp = datetime.now().astimezone().isoformat(timespec="seconds")
            subject = row[subject_column].strip()
            to = row[to_column].strip()
            try:
                _, message_id, _ = future.result()
                row["draft_status"] = row.get("draft_status", "").strip() or "approved"
                row["send_status"] = "sent"
                row["last_subject"] = subject
                row["last_sent_at"] = stamp
                row["gmail_message_id"] = message_id
                row["last_error"] = ""
                sent += 1
                emit_log(
                    {
                        "batch_id": batch_id,
                        "lead_id": row["lead_id"],
                        "to": to,
                        "subject": subject,
                        "status": "sent",
                        "gmail_message_id": message_id,
                        "timestamp": stamp,
                    }
                )
                print(f"SENT {row['lead_id']} -> {to} ({message_id})")
            except Exception as exc:
                row["send_status"] = "failed"
                row["last_subject"] = subject
                row["last_sent_at"] = stamp
                row["last_error"] = str(exc)
                failed += 1
                emit_log(
                    {
                        "batch_id": batch_id,
                        "lead_id": row["lead_id"],
                        "to": to,
                        "subject": subject,
                        "status": "failed",
                        "error": str(exc),
                        "timestamp": stamp,
                    }
                )
                print(f"FAILED {row['lead_id']} -> {to}: {exc}", file=sys.stderr)

    with output_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(
        f"Batch complete: {sent} sent, {failed} failed, {skipped} skipped. "
        f"Output CSV: {output_csv}"
    )
    if log_path:
        print(f"Batch log: {log_path}")

    return 0 if failed == 0 else 1


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
    parser.add_argument(
        "--no-signature",
        action="store_true",
        help="Do not append assistant disclosure footer. Use only when George explicitly requests no signature.",
    )
    parser.add_argument("--auth-only", action="store_true", help="Only run OAuth/auth verification and save token")
    parser.add_argument("--reauth", action="store_true", help="Delete the existing token for this account first")
    parser.add_argument("--reply-to-message-id", help="Reply to an existing Gmail message id")
    parser.add_argument("--reply-to-export", help="Reply to an exported markdown email note")
    parser.add_argument("--batch-csv", help="CSV file with one outbound row per email")
    parser.add_argument("--batch-output-csv", help="Optional output CSV path; defaults to overwriting --batch-csv")
    parser.add_argument("--batch-log", help="Optional JSONL log path for batch send events")
    parser.add_argument("--to-column", default="contact_email", help="Recipient column name for --batch-csv")
    parser.add_argument("--subject-column", default="draft_subject", help="Subject column name for --batch-csv")
    parser.add_argument("--body-column", default="draft_body", help="Body column name for --batch-csv")
    parser.add_argument("--max-workers", type=int, default=1, help="Parallel workers for --batch-csv")
    parser.add_argument(
        "--resend",
        action="store_true",
        help="Send rows even if their send_status is already sent/delivered/replied",
    )
    args = parser.parse_args()

    account = find_account(args.account)
    if account is None:
        print(f"Unknown account: {args.account}", file=sys.stderr)
        return 1
    if not account.allow_send:
        print(f"Account is not send-enabled: {account.email}", file=sys.stderr)
        return 1
    if args.no_signature and account.assistant_signature:
        print(
            f"WARNING: sending from {account.email} without the configured assistant disclosure footer.",
            file=sys.stderr,
        )

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

    if args.batch_csv:
        if args.reply_to_message_id or args.reply_to_export:
            print("Reply context is not supported together with --batch-csv.", file=sys.stderr)
            return 1
        batch_csv = Path(args.batch_csv).expanduser().resolve()
        if not batch_csv.exists():
            print(f"Batch CSV not found: {batch_csv}", file=sys.stderr)
            return 1
        output_csv = Path(args.batch_output_csv).expanduser().resolve() if args.batch_output_csv else batch_csv
        log_path = Path(args.batch_log).expanduser().resolve() if args.batch_log else None
        return run_batch_send(
            account=account,
            batch_csv=batch_csv,
            output_csv=output_csv,
            log_path=log_path,
            to_column=args.to_column,
            subject_column=args.subject_column,
            body_column=args.body_column,
            max_workers=args.max_workers,
            skip_sent=not args.resend,
            cc=args.cc,
            attachments=[Path(path).expanduser().resolve() for path in args.attach],
            append_signature=not args.no_signature,
        )

    if args.reply_to_message_id and args.reply_to_export:
        print("Use only one of --reply-to-message-id or --reply-to-export.", file=sys.stderr)
        return 1
    if (not args.to) or ((not args.subject) and not (args.reply_to_message_id or args.reply_to_export)) or (not args.body and not args.body_file):
        print("--to, one of --body/--body-file, and either --subject or reply context are required unless --auth-only is used.", file=sys.stderr)
        return 1

    body = args.body
    if args.body_file:
        body = Path(args.body_file).read_text(encoding="utf-8")

    body = build_body(body, account.assistant_signature, not args.no_signature)
    attachments = [Path(path).expanduser().resolve() for path in args.attach]

    creds = account.get_credentials()
    if creds is None:
        return 1

    service = build("gmail", "v1", credentials=creds)
    reply_context = None
    if args.reply_to_export:
        reply_message_id = extract_reply_message_id(Path(args.reply_to_export).expanduser().resolve())
        reply_context = load_reply_context(service, reply_message_id)
    elif args.reply_to_message_id:
        reply_context = load_reply_context(service, args.reply_to_message_id)

    subject = args.subject
    if not subject and reply_context:
        subject = reply_context["subject"] or ""
        if subject and not subject.lower().startswith("re:"):
            subject = f"Re: {subject}"

    if args.preview_dir or args.preview_only:
        preview_dir = Path(args.preview_dir or ".email-previews").expanduser().resolve()
        eml_path, html_path = write_preview_artifacts(
            preview_dir,
            account.email,
            args.to,
            subject,
            body,
            cc=args.cc,
            attachments=attachments,
            in_reply_to=reply_context["message_id_header"] if reply_context else None,
            references=reply_context["references"] if reply_context else None,
            thread_id=reply_context["thread_id"] if reply_context else None,
        )
        print(f"Preview EML: {eml_path}")
        print(f"Preview HTML: {html_path}")

    if args.preview_only:
        print("Preview only; email was not sent.")
        return 0

    message = create_message(
        account.email,
        args.to,
        subject,
        body,
        cc=args.cc,
        attachments=attachments,
        in_reply_to=reply_context["message_id_header"] if reply_context else None,
        references=reply_context["references"] if reply_context else None,
        thread_id=reply_context["thread_id"] if reply_context else None,
    )

    try:
        result = service.users().messages().send(userId="me", body=message).execute()
    except HttpError as exc:
        print(f"Failed to send email: {exc}", file=sys.stderr)
        return 1

    print(f"Sent message id: {result.get('id')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
