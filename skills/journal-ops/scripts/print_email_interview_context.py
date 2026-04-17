#!/usr/bin/env python3
"""
Print compact, high-signal email context for daily-summary interviews.

Focuses on:
- credit-card purchase alerts (amount, merchant, card ending)
- interview-critical emails (assessment/interview/deadline signals)
- other finance notices that may explain the day
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from repo_paths import resolve_private_repo_root

ROOT = resolve_private_repo_root()
EMAIL_ROOT = ROOT / "captures" / "email"
LOCAL_TZ = datetime.now().astimezone().tzinfo

INTERVIEW_KEYWORDS = (
    "interview",
    "codesignal",
    "assessment",
    "pre-screen",
    "phone screen",
    "onsite",
    "recruit",
    "invited you to take",
)
FINANCE_KEYWORDS = (
    "credit card",
    "new purchase",
    "receipt",
    "statement",
    "bill",
    "invoice",
    "payment",
    "dividend",
    "interactive brokers",
    "cibc",
    "visa",
    "mastercard",
    "amex",
)


@dataclass
class EmailRecord:
    path: Path
    subject: str
    sender: str
    received_text: str
    received_at: datetime | None
    body: str


def find_target_emails(day_text: str) -> list[Path]:
    if not EMAIL_ROOT.exists():
        return []
    pattern = f"**/{day_text}_*.md"
    candidates = [p for p in EMAIL_ROOT.glob(pattern) if p.is_file()]
    return sorted(candidates)


def parse_email_file(path: Path) -> EmailRecord:
    text = path.read_text(encoding="utf-8", errors="ignore")
    subject_match = re.search(r"^#\s+(.+)$", text, flags=re.MULTILINE)
    sender_match = re.search(r"^\*\*From:\*\*\s+(.+)$", text, flags=re.MULTILINE)
    received_match = re.search(r"^\*\*Date Received:\*\*\s+(.+)$", text, flags=re.MULTILINE)

    subject = subject_match.group(1).strip() if subject_match else path.stem
    sender = sender_match.group(1).strip() if sender_match else ""
    received_text = received_match.group(1).strip() if received_match else ""
    received_at = parse_datetime(received_text)

    # Content after the second markdown horizontal separator is the body.
    # Format in exports is:
    # --- frontmatter --- ... --- message body
    parts = text.split("\n---\n")
    body = parts[-1] if parts else text
    return EmailRecord(
        path=path,
        subject=subject,
        sender=sender,
        received_text=received_text,
        received_at=received_at,
        body=body,
    )


def parse_datetime(value: str) -> datetime | None:
    if not value:
        return None
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
        if parsed.tzinfo is None and LOCAL_TZ is not None:
            return parsed.replace(tzinfo=LOCAL_TZ)
        return parsed.astimezone(LOCAL_TZ) if parsed.tzinfo is not None and LOCAL_TZ is not None else parsed
    except ValueError:
        return None


def extract_credit_card_purchase(record: EmailRecord) -> tuple[str, str, str] | None:
    text = f"{record.subject}\n{record.body}"
    lower = text.lower()
    if "credit card" not in lower and "new purchase" not in lower:
        return None

    # Example: "ending in 4012 for $121.42 at TST-Fiore Famiglia."
    pattern = re.compile(
        r"ending in\s+(\d{4})\s+for\s+\$([0-9]+(?:\.[0-9]{1,2})?)\s+at\s+([^\n\.]+)",
        flags=re.IGNORECASE,
    )
    match = pattern.search(text)
    if not match:
        return None

    card_ending = match.group(1).strip()
    amount = match.group(2).strip()
    merchant = match.group(3).strip()
    return card_ending, amount, merchant


def extract_deadline_hint(text: str) -> str:
    patterns = (
        r"before\s+([A-Za-z]+\s+\d{1,2}(?:st|nd|rd|th)?(?:,\s*)?\d{1,2}:\d{2}\s*(?:am|pm)\s*[A-Z]{2,4})",
        r"deadline[:\s]+([^\n]+)",
        r"due[:\s]+([^\n]+)",
    )
    for pat in patterns:
        match = re.search(pat, text, flags=re.IGNORECASE)
        if match:
            return " ".join(match.group(1).split())
    return ""


def is_interview_critical(record: EmailRecord) -> bool:
    subject = record.subject.lower()
    sender = record.sender.lower()

    if any(keyword in subject for keyword in INTERVIEW_KEYWORDS):
        return True

    recruiting_sender_hints = (
        "codesignal",
        "instacart",
        "databricks",
        "greenhouse",
        "goodtime",
        "lever.co",
        "workday",
        "recruit",
    )
    return any(hint in sender for hint in recruiting_sender_hints)


def is_finance_notice(record: EmailRecord) -> bool:
    combined = f"{record.subject}\n{record.body}\n{record.sender}".lower()
    return any(keyword in combined for keyword in FINANCE_KEYWORDS)


def display_time(record: EmailRecord) -> str:
    if record.received_at is None:
        return "unknown-time"
    return record.received_at.strftime("%H:%M")


def main() -> int:
    parser = argparse.ArgumentParser(description="Print high-signal email interview context for a target date.")
    parser.add_argument("--date", default=date.today().isoformat(), help="Target date YYYY-MM-DD (default: today)")
    args = parser.parse_args()

    files = find_target_emails(args.date)
    if not files:
        print(f"Email context for {args.date}: no emails found.")
        return 0

    records = [parse_email_file(path) for path in files]
    fallback = datetime.min.replace(tzinfo=LOCAL_TZ) if LOCAL_TZ is not None else datetime.min
    records.sort(key=lambda rec: rec.received_at or fallback)

    purchases: list[tuple[EmailRecord, tuple[str, str, str]]] = []
    interview_records: list[tuple[EmailRecord, str]] = []
    finance_records: list[EmailRecord] = []

    for rec in records:
        purchase = extract_credit_card_purchase(rec)
        if purchase:
            purchases.append((rec, purchase))

        if is_interview_critical(rec):
            deadline_hint = extract_deadline_hint(f"{rec.subject}\n{rec.body}")
            interview_records.append((rec, deadline_hint))

        if is_finance_notice(rec):
            finance_records.append(rec)

    print(f"Email context for {args.date}:")
    print(f"- Total emails found: {len(records)}")

    if purchases:
        print(f"- Credit-card purchases: {len(purchases)}")
        for rec, (card_ending, amount, merchant) in purchases:
            print(
                f"  - {display_time(rec)} | card {card_ending} | ${amount} | {merchant}"
            )
    else:
        print("- Credit-card purchases: none detected")

    if interview_records:
        print(f"- Interview-critical emails: {len(interview_records)}")
        for rec, deadline in interview_records[:8]:
            extra = f" | deadline: {deadline}" if deadline else ""
            print(f"  - {display_time(rec)} | {rec.subject} | from {rec.sender}{extra}")
    else:
        print("- Interview-critical emails: none detected")

    # Show finance notices that are not already represented by purchase alerts.
    finance_unique: list[EmailRecord] = []
    purchase_paths = {rec.path for rec, _ in purchases}
    for rec in finance_records:
        if rec.path not in purchase_paths:
            finance_unique.append(rec)

    if finance_unique:
        print(f"- Other finance notices: {len(finance_unique)}")
        for rec in finance_unique[:8]:
            print(f"  - {display_time(rec)} | {rec.subject} | from {rec.sender}")
    else:
        print("- Other finance notices: none detected")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
