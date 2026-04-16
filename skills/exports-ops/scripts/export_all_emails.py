#!/usr/bin/env python3
"""
⚠️ ONE-TIME MIGRATION SCRIPT - NOT FOR REGULAR USE ⚠️

Migrate ALL emails (sent and received) to markdown files.
This script processes all emails, not just today's, and can run for many hours.
It skips emails that have already been exported to avoid duplicates.

**Purpose**: One-time historical migration from Apple Mail to markdown files.
**Regular exports**: Use `export_emails_gmail_api.py` for daily incremental exports.

See EMAIL_MIGRATION_INSTRUCTIONS.md for usage instructions.
"""

import subprocess
import os
import sys
import re
import signal
from pathlib import Path
from datetime import datetime
from html import unescape

from repo_paths import resolve_private_repo_root

PRIVATE_REPO_ROOT = resolve_private_repo_root()
EMAIL_DIR = PRIVATE_REPO_ROOT / "captures" / "email"
SENT_DIR = EMAIL_DIR / "sent"
RECEIVED_DIR = EMAIL_DIR / "received"
LAST_EXPORT_FILE = EMAIL_DIR / ".last_export"

MAILBOX_SENT_NAMES = [
    "Sent",
    "Sent Mail",
    "Sent Messages",
    "Sent Items",
    "[Gmail]/Sent Mail",
    "[Gmail]/Sent Messages",
    "INBOX.Sent",
    "INBOX.Sent Messages"
]

MAILBOX_INBOX_NAMES = [
    "Inbox",
    "INBOX"
]

# Global flag for interrupt handling
interrupt_requested = False

def sanitize_filename(filename):
    """Remove invalid characters from filename"""
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    filename = filename.strip(' .')
    if len(filename) > 200:
        filename = filename[:200]
    return filename or "Untitled Email"

def html_to_markdown(html_content):
    """Convert HTML from email to clean markdown."""
    if not html_content:
        return ""

    text = unescape(html_content)
    text = re.sub(r'<strong>(.*?)</strong>', r'**\1**', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<b>(.*?)</b>', r'**\1**', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<em>(.*?)</em>', r'*\1*', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<i>(.*?)</i>', r'*\1*', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<p[^>]*>(.*?)</p>', r'\1\n\n', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<br[^>]*>', '\n', text, flags=re.IGNORECASE)

    def replace_link(match):
        url = match.group(1) if match.group(1) else match.group(2)
        link_text = match.group(3) if match.group(3) else url
        return f"[{link_text}]({url})"

    text = re.sub(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', replace_link, text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
    text = text.strip()

    return text

def escape_applescript_string(value):
    """Escape double quotes for embedding in AppleScript strings."""
    return value.replace('"', r'\"')

def format_date_for_filename(date_str):
    """Convert AppleScript date string to YYYY-MM-DD format"""
    try:
        date_match = re.search(r'(\w+), (\w+) (\d+), (\d{4})', date_str)
        if date_match:
            month_name = date_match.group(2)
            day = date_match.group(3)
            year = date_match.group(4)

            month_map = {
                'January': '01', 'February': '02', 'March': '03', 'April': '04',
                'May': '05', 'June': '06', 'July': '07', 'August': '08',
                'September': '09', 'October': '10', 'November': '11', 'December': '12'
            }
            month = month_map.get(month_name, '01')
            return f"{year}-{month}-{day.zfill(2)}"
    except:
        pass

    return datetime.now().strftime("%Y-%m-%d")

def get_single_sent_email(account_index, mailbox_name, message_index):
    """Get a single sent email. Returns email info string or None."""
    mailbox_safe = escape_applescript_string(mailbox_name)
    applescript = f'''
    on join_addresses(recipientList)
        try
            if recipientList is missing value then return ""
            if (count of recipientList) is 0 then return ""
            set addressStrings to {{}}
            repeat with aRecipient in recipientList
                set addr to ""
                try
                    set addr to address of aRecipient
                    if name of aRecipient is not missing value then
                        set addr to (name of aRecipient) & " <" & addr & ">"
                    end if
                on error
                    set addr to "(unknown)"
                end try
                if addr is missing value then set addr to "(unknown)"
                copy addr to end of addressStrings
            end repeat
            set AppleScript's text item delimiters to ", "
            set joinedString to addressStrings as string
            set AppleScript's text item delimiters to ""
            return joinedString
        on error
            return ""
        end try
    end join_addresses

    tell application "Mail"
        try
            set anAccount to account {account_index}
            set sentMailbox to missing value
            repeat with aMailbox in mailboxes of anAccount
                set boxName to name of aMailbox as string
                if boxName is "{mailbox_safe}" then
                    set sentMailbox to aMailbox
                    exit repeat
                end if
            end repeat
            if sentMailbox is missing value then
                return ""
            end if
            set aMessage to message {message_index} of sentMailbox

            set msgSubject to subject of aMessage
            if msgSubject is missing value then set msgSubject to "(No Subject)"

            set msgFrom to ""
            try
                set msgFrom to sender of aMessage
            end try
            if msgFrom is missing value then set msgFrom to "(unknown)"

            set msgTo to my join_addresses(recipients of aMessage)
            set msgCc to my join_addresses(cc recipients of aMessage)
            set msgBcc to my join_addresses(bcc recipients of aMessage)

            set msgDateSent to date sent of aMessage
            set msgDate to msgDateSent as string

            set msgContent to ""
            try
                set msgContent to content of aMessage
                if msgContent is missing value then set msgContent to ""
            end try

            return msgSubject & "|||" & msgFrom & "|||" & msgTo & "|||" & msgCc & "|||" & msgBcc & "|||" & msgDate & "|||" & msgContent
        on error
            return ""
        end try
    end tell
    '''

    try:
        result = subprocess.run(
            ['osascript', '-e', applescript],
            capture_output=True,
            text=True,
            check=False,  # Don't raise on error, we'll check return code
            timeout=15  # Increased timeout
        )
        if result.returncode != 0:
            # AppleScript error - message might not exist or be inaccessible
            return None
        output = result.stdout.strip()
        return output if output else None
    except subprocess.TimeoutExpired:
        return None
    except:
        return None

def get_single_received_email(account_index, mailbox_name, message_index):
    """Get a single received email. Returns email info string or None."""
    mailbox_safe = escape_applescript_string(mailbox_name)
    applescript = f'''
    on join_addresses(recipientList)
        try
            if recipientList is missing value then return ""
            if (count of recipientList) is 0 then return ""
            set addressStrings to {{}}
            repeat with aRecipient in recipientList
                set addr to ""
                try
                    set addr to address of aRecipient
                    if name of aRecipient is not missing value then
                        set addr to (name of aRecipient) & " <" & addr & ">"
                    end if
                on error
                    set addr to "(unknown)"
                end try
                if addr is missing value then set addr to "(unknown)"
                copy addr to end of addressStrings
            end repeat
            set AppleScript's text item delimiters to ", "
            set joinedString to addressStrings as string
            set AppleScript's text item delimiters to ""
            return joinedString
        on error
            return ""
        end try
    end join_addresses

    tell application "Mail"
        try
            set anAccount to account {account_index}
            set inboxMailbox to missing value
            repeat with aMailbox in mailboxes of anAccount
                set boxName to name of aMailbox as string
                if boxName is "{mailbox_safe}" then
                    set inboxMailbox to aMailbox
                    exit repeat
                end if
            end repeat
            if inboxMailbox is missing value then
                return ""
            end if
            set aMessage to message {message_index} of inboxMailbox

            set msgSubject to subject of aMessage
            if msgSubject is missing value then set msgSubject to "(No Subject)"

            set msgFrom to ""
            try
                set msgFrom to sender of aMessage
                if msgFrom is missing value then set msgFrom to "(unknown)"
            end try

            set msgTo to my join_addresses(recipients of aMessage)
            set msgCc to my join_addresses(cc recipients of aMessage)
            set msgBcc to my join_addresses(bcc recipients of aMessage)

            set msgDateReceived to date received of aMessage
            set msgDate to msgDateReceived as string

            set msgContent to ""
            try
                set msgContent to content of aMessage
                if msgContent is missing value then set msgContent to ""
            end try

            return msgSubject & "|||" & msgFrom & "|||" & msgTo & "|||" & msgCc & "|||" & msgBcc & "|||" & msgDate & "|||" & msgContent
        on error
            return ""
        end try
    end tell
    '''

    try:
        result = subprocess.run(
            ['osascript', '-e', applescript],
            capture_output=True,
            text=True,
            check=False,  # Don't raise on error, we'll check return code
            timeout=15  # Increased timeout
        )
        if result.returncode != 0:
            # AppleScript error - message might not exist or be inaccessible
            return None
        output = result.stdout.strip()
        return output if output else None
    except subprocess.TimeoutExpired:
        return None
    except:
        return None

def get_last_export_progress():
    """Get the last export progress. Returns dict with account/mailbox -> message_index."""
    progress = {}
    if LAST_EXPORT_FILE.exists():
        try:
            content = LAST_EXPORT_FILE.read_text().strip()
            for line in content.split('\n'):
                if '|||' in line:
                    parts = line.split('|||')
                    if len(parts) >= 4:
                        key = "|||".join(parts[:-1])
                        progress[key] = int(parts[-1])
        except:
            pass
    return progress

def save_last_export_progress(progress):
    """Save the current export progress."""
    LAST_EXPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for key, msg_index in progress.items():
        lines.append(f"{key}|||{msg_index}")
    LAST_EXPORT_FILE.write_text('\n'.join(lines) + '\n')

def build_existing_files_map(directory):
    """Build a map of existing files to avoid duplicates. Key: (date, subject), Value: filepath"""
    existing_map = {}
    if not directory.exists():
        return existing_map

    for file_path in directory.glob("*.md"):
        try:
            # Extract date and subject from filename: YYYY-MM-DD_Subject.md
            filename = file_path.stem
            if '_' in filename:
                date_part = filename.split('_')[0]
                subject_part = '_'.join(filename.split('_')[1:])
                # Remove _1, _2 suffixes for duplicates
                subject_part = re.sub(r'_\d+$', '', subject_part)
                existing_map[(date_part, subject_part)] = file_path
        except:
            pass

    return existing_map

def get_mailbox_config_fallback():
    """Fallback mailbox discovery using known mailbox names directly (faster)."""
    applescript = '''
    tell application "Mail"
    set sentList to ""
    set inboxList to ""
    set sentNames to {"Sent Mail", "Sent", "Sent Messages", "Sent Items"}
    set inboxNames to {"INBOX", "Inbox"}

    try
        set allAccounts to accounts
        repeat with i from 1 to (count of allAccounts)
            set anAccount to account i
            repeat with sentName in sentNames
                try
                    set sentMailbox to mailbox sentName of anAccount
                    set boxName to name of sentMailbox as string
                    set sentList to sentList & i & "|||" & boxName & "|||999999:::SEP:::"
                    exit repeat
                end try
            end repeat
            repeat with inboxName in inboxNames
                try
                    set inboxMailbox to mailbox inboxName of anAccount
                    set boxName to name of inboxMailbox as string
                    set inboxList to inboxList & i & "|||" & boxName & "|||999999:::SEP:::"
                    exit repeat
                end try
            end repeat
        end repeat
    end try

    return sentList & "###" & inboxList
    end tell
    '''

    try:
        result = subprocess.run(
            ['osascript', '-e', applescript],
            capture_output=True,
            text=True,
            check=True,
            timeout=60  # Shorter timeout for fallback
        )
        output = result.stdout.strip()
    except:
        return [], []

    if "###" in output:
        raw_sent, raw_inbox = output.split("###")
    else:
        raw_sent, raw_inbox = output, ""

    def parse_list(raw):
        seen = set()
        entries = []
        for item in raw.split(":::SEP:::"):
            item = item.strip()
            if not item:
                continue
            parts = item.split("|||")
            if len(parts) >= 3:
                account = parts[0]
                mailbox = parts[1]
                try:
                    count = int(parts[2])
                except ValueError:
                    count = 999999
                key = (account, mailbox)
                if key in seen:
                    continue
                seen.add(key)
                entries.append({"account": account, "mailbox": mailbox, "count": count})
        return entries

    return parse_list(raw_sent), parse_list(raw_inbox)

def get_mailbox_config():
    """
    Discover sent/inbox mailboxes for each account.
    Uses special mailbox properties first, then falls back to name matching.
    Returns (sent_mailboxes, inbox_mailboxes) where each entry is a dict with
    account, mailbox, count (999999 means unknown, will process until errors).
    """
    applescript = '''
    tell application "Mail"
    set sentNames to {"Sent", "Sent Mail", "Sent Messages", "Sent Items", "[Gmail]/Sent Mail", "[Gmail]/Sent Messages", "INBOX.Sent", "INBOX.Sent Messages"}
    set inboxNames to {"Inbox", "INBOX"}

    set sentList to ""
    set inboxList to ""
    set seenSent to {}
    set seenInbox to {}

    try
        set allAccounts to accounts
        repeat with i from 1 to (count of allAccounts)
            set anAccount to account i

            -- Use special mailbox properties only (iterating through mailboxes is too slow)
            try
                set sentMailbox to sent mailbox of anAccount
                set boxName to name of sentMailbox as string
                set sentList to sentList & i & "|||" & boxName & "|||999999:::SEP:::"
            on error
                -- If special property doesn't work, try common names directly
                -- This avoids iterating through all mailboxes which is very slow
                try
                    set sentMailbox to mailbox "Sent Mail" of anAccount
                    set boxName to name of sentMailbox as string
                    set sentList to sentList & i & "|||" & boxName & "|||999999:::SEP:::"
                on error
                    try
                        set sentMailbox to mailbox "Sent" of anAccount
                        set boxName to name of sentMailbox as string
                        set sentList to sentList & i & "|||" & boxName & "|||999999:::SEP:::"
                    end try
                end try
            end try

            try
                set inboxMailbox to inbox of anAccount
                set boxName to name of inboxMailbox as string
                set inboxList to inboxList & i & "|||" & boxName & "|||999999:::SEP:::"
            on error
                -- If special property doesn't work, try common names directly
                try
                    set inboxMailbox to mailbox "INBOX" of anAccount
                    set boxName to name of inboxMailbox as string
                    set inboxList to inboxList & i & "|||" & boxName & "|||999999:::SEP:::"
                on error
                    try
                        set inboxMailbox to mailbox "Inbox" of anAccount
                        set boxName to name of inboxMailbox as string
                        set inboxList to inboxList & i & "|||" & boxName & "|||999999:::SEP:::"
                    end try
                end try
            end try
        end repeat
    end try

    return sentList & "###" & inboxList
    end tell
    '''

    try:
        result = subprocess.run(
            ['osascript', '-e', applescript],
            capture_output=True,
            text=True,
            check=True,
            timeout=300  # Increased to 5 minutes for large mailboxes
        )
        output = result.stdout.strip()
    except subprocess.SubprocessError as exc:
        print(f"[email migration] mailbox discovery failed: {exc}", file=sys.stderr)
        print("[email migration] Using fallback: trying known mailbox names directly...", file=sys.stderr)
        # Fallback: try known mailbox names directly for each account
        return get_mailbox_config_fallback()

    if "###" in output:
        raw_sent, raw_inbox = output.split("###")
    else:
        raw_sent, raw_inbox = output, ""

    def parse_list(raw):
        seen = set()
        entries = []
        for item in raw.split(":::SEP:::"):
            item = item.strip()
            if not item:
                continue
            parts = item.split("|||")
            if len(parts) >= 3:
                account = parts[0]
                mailbox = parts[1]
                try:
                    count = int(parts[2])
                except ValueError:
                    count = 0
                key = (account, mailbox)
                if key in seen:
                    continue
                seen.add(key)
                entries.append({"account": account, "mailbox": mailbox, "count": count})
        return entries

    return parse_list(raw_sent), parse_list(raw_inbox)

def process_email(email_info, output_dir, email_type="sent", existing_map=None):
    """Process and save a single email. Returns True if saved, False if skipped."""
    if not email_info or email_info == "":
        return False

    parts = email_info.split("|||")
    if len(parts) < 7:
        return False

    email_subject = parts[0]
    email_from = parts[1]
    email_to = parts[2]
    email_cc = parts[3]
    email_bcc = parts[4]
    email_date = parts[5]
    email_content = parts[6]

    # Format date for filename
    date_str = format_date_for_filename(email_date)

    # Sanitize subject for filename
    safe_subject = sanitize_filename(email_subject)

    # Check if already exists
    if existing_map:
        key = (date_str, safe_subject)
        if key in existing_map:
            return False  # Already exported, skip

    # Create filename
    filename = f"{date_str}_{safe_subject}.md"
    file_path = output_dir / filename

    # Handle duplicate filenames
    counter = 1
    while file_path.exists():
        filename = f"{date_str}_{safe_subject}_{counter}.md"
        file_path = output_dir / filename
        counter += 1

    # Convert HTML to markdown
    markdown_content = html_to_markdown(email_content)

    # Save file
    def display_line(label, value):
        value = value.strip() if value else ""
        if not value:
            value = "(none)"
        return f"**{label}:** {value}\n\n"

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(f"# {email_subject}\n\n")
        f.write(display_line("From", email_from))
        f.write(display_line("To", email_to))
        f.write(display_line("CC", email_cc))
        f.write(display_line("BCC", email_bcc))
        if email_type == "sent":
            f.write(display_line("Date Sent", email_date))
        else:
            f.write(display_line("Date Received", email_date))
        f.write("---\n\n")
        f.write(markdown_content)
        f.write("\n")

    return True

def migrate_all_emails():
    """Migrate all emails (sent and received) to markdown files."""
    global interrupt_requested

    # Create directories
    SENT_DIR.mkdir(parents=True, exist_ok=True)
    RECEIVED_DIR.mkdir(parents=True, exist_ok=True)

    # Load last export progress
    print("Loading last export progress...")
    last_progress = get_last_export_progress()
    if last_progress:
        print(f"  - Found progress for {len(last_progress)} account/mailbox combinations")
        print("  - Will resume from last position")
    else:
        print("  - No previous progress found, starting from beginning")
    print()

    # Build existing files maps to skip duplicates
    print("Building index of existing files...")
    sent_existing = build_existing_files_map(SENT_DIR)
    received_existing = build_existing_files_map(RECEIVED_DIR)
    print(f"  - Found {len(sent_existing)} existing sent emails")
    print(f"  - Found {len(received_existing)} existing received emails")
    print()

    # Track current progress
    current_progress = {}
    total_exported = 0
    total_skipped = 0
    total_errors = 0

    # Discover mailboxes
    sent_mailboxes, inbox_mailboxes = get_mailbox_config()
    if not sent_mailboxes:
        print("Warning: Could not find any sent mailboxes. Check Mail preferences or add more name patterns.")
    if not inbox_mailboxes:
        print("Warning: Could not find any inbox mailboxes.")

    total_sent = sum(m["count"] for m in sent_mailboxes)
    total_received = sum(m["count"] for m in inbox_mailboxes)

    print(f"Total messages to process:")
    print(f"  - Sent: {total_sent:,}")
    print(f"  - Received: {total_received:,}")
    print(f"  - Total: {total_sent + total_received:,}")
    print()
    print("Starting migration (this will take many hours)...")
    print("Press Ctrl+C to stop gracefully (will save progress)")
    print()

    start_time = datetime.now()

    # Process sent emails
    print("=" * 60)
    print("Processing SENT emails...")
    print("=" * 60)

    processed_sent = 0
    sent_skipped_total = 0

    for mailbox in sent_mailboxes:
        if interrupt_requested:
            break

        account_index = mailbox["account"]
        mailbox_name = mailbox["mailbox"]
        mailbox_count = mailbox["count"]

        # Skip mailboxes with 0 messages
        if mailbox_count == 0:
            print(f"Account {account_index} mailbox '{mailbox_name}': 0 messages, skipping")
            continue

        processed = 0
        skipped = 0
        errors = 0

        progress_key = f"{account_index}|||sent|||{mailbox_name}"
        start_index = last_progress.get(progress_key, 1)
        if start_index > 1:
            print(f"  Resuming account {account_index} mailbox '{mailbox_name}' from message {start_index}/{mailbox_count}")
        else:
            print(f"  Processing account {account_index} mailbox '{mailbox_name}' ({mailbox_count:,} messages)")

        msg_index = start_index
        consecutive_errors = 0
        max_consecutive_errors = 50  # Only stop after many consecutive errors
        last_success_index = start_index - 1

        while msg_index <= max_index:
            if interrupt_requested:
                break

            email_info = get_single_sent_email(account_index, mailbox_name, msg_index)
            if email_info is None or email_info == "":
                consecutive_errors += 1
                errors += 1
                total_errors += 1
                # Only stop if we hit many consecutive errors AND we haven't had a success in a while
                # This handles gaps in message indices (deleted messages)
                if consecutive_errors >= max_consecutive_errors and (msg_index - last_success_index) > max_consecutive_errors:
                    print(f"  Warning: {max_consecutive_errors} consecutive errors starting at message {msg_index}, likely reached end. Moving to next mailbox.")
                    break
                msg_index += 1
                continue

            consecutive_errors = 0  # Reset error counter on success
            last_success_index = msg_index  # Track last successful message

            if process_email(email_info, SENT_DIR, "sent", sent_existing):
                processed += 1
                processed_sent += 1
                total_exported += 1
                if processed_sent % 50 == 0:
                    elapsed = (datetime.now() - start_time).total_seconds()
                    rate = processed_sent / elapsed if elapsed > 0 else 0
                    remaining = (total_sent - processed_sent) / rate if rate > 0 and total_sent else 0
                    total_sent_display = f"{total_sent:,}" if total_sent else "?"
                    hours = int(remaining / 3600) if remaining else 0
                    minutes = int((remaining % 3600) / 60) if remaining else 0
                    print(f"  [{processed_sent:,}/{total_sent_display}] Sent emails exported "
                          f"(~{hours}h {minutes}m remaining)")
            else:
                skipped += 1
                total_skipped += 1
                sent_skipped_total += 1

            current_progress[progress_key] = msg_index
            msg_index += 1
            if processed % 20 == 0:
                save_last_export_progress(current_progress)

        print(f"Account {account_index} mailbox '{mailbox_name}': {processed:,} exported, {skipped:,} skipped, {errors:,} errors")
        current_progress[progress_key] = msg_index
        save_last_export_progress(current_progress)

    print(f"\nSent emails: {processed_sent:,} exported, {sent_skipped_total:,} skipped")
    print()

    # Process received emails
    print("=" * 60)
    print("Processing RECEIVED emails...")
    print("=" * 60)

    processed_received = 0
    received_skipped = 0

    for mailbox in inbox_mailboxes:
        if interrupt_requested:
            break

        account_index = mailbox["account"]
        mailbox_name = mailbox["mailbox"]
        mailbox_count = mailbox["count"]

        # Skip mailboxes with 0 messages
        if mailbox_count == 0:
            print(f"Account {account_index} mailbox '{mailbox_name}': 0 messages, skipping")
            continue

        processed = 0
        skipped = 0
        errors = 0

        progress_key = f"{account_index}|||inbox|||{mailbox_name}"
        start_index = last_progress.get(progress_key, 1)
        if start_index > 1:
            print(f"  Resuming account {account_index} mailbox '{mailbox_name}' from message {start_index}/{mailbox_count}")
        else:
            print(f"  Processing account {account_index} mailbox '{mailbox_name}' ({mailbox_count:,} messages)")

        msg_index = start_index
        consecutive_errors = 0
        max_consecutive_errors = 50  # Only stop after many consecutive errors
        last_success_index = start_index - 1

        while msg_index <= max_index:
            if interrupt_requested:
                break

            email_info = get_single_received_email(account_index, mailbox_name, msg_index)
            if email_info is None or email_info == "":
                consecutive_errors += 1
                errors += 1
                total_errors += 1
                # Only stop if we hit many consecutive errors AND we haven't had a success in a while
                # This handles gaps in message indices (deleted messages)
                if consecutive_errors >= max_consecutive_errors and (msg_index - last_success_index) > max_consecutive_errors:
                    print(f"  Warning: {max_consecutive_errors} consecutive errors starting at message {msg_index}, likely reached end. Moving to next mailbox.")
                    break
                msg_index += 1
                continue

            consecutive_errors = 0  # Reset error counter on success
            last_success_index = msg_index  # Track last successful message

            if process_email(email_info, RECEIVED_DIR, "received", received_existing):
                processed_received += 1
                processed += 1
                total_exported += 1
                if processed_received % 50 == 0:
                    elapsed = (datetime.now() - start_time).total_seconds()
                    rate = processed_received / elapsed if elapsed > 0 else 0
                    remaining = (total_received - processed_received) / rate if rate > 0 and total_received else 0
                    total_recv_display = f"{total_received:,}" if total_received else "?"
                    hours = int(remaining / 3600) if remaining else 0
                    minutes = int((remaining % 3600) / 60) if remaining else 0
                    print(f"  [{processed_received:,}/{total_recv_display}] Received emails exported "
                          f"(~{hours}h {minutes}m remaining)")
            else:
                skipped += 1
                received_skipped += 1
                total_skipped += 1

            current_progress[progress_key] = msg_index
            msg_index += 1
            if processed_received % 20 == 0:
                save_last_export_progress(current_progress)

        print(f"Account {account_index} mailbox '{mailbox_name}': {processed:,} exported, {skipped:,} skipped, {errors:,} errors")
        current_progress[progress_key] = msg_index
        save_last_export_progress(current_progress)

    print(f"\nReceived emails: {processed_received:,} exported, {received_skipped:,} skipped")
    print()

    # Summary
    elapsed = datetime.now() - start_time
    hours = int(elapsed.total_seconds() / 3600)
    minutes = int((elapsed.total_seconds() % 3600) / 60)

    print("=" * 60)
    print("MIGRATION SUMMARY")
    print("=" * 60)
    print(f"Total exported: {total_exported:,}")
    print(f"Total skipped (already existed): {total_skipped:,}")
    print(f"Total errors: {total_errors:,}")
    print(f"Time elapsed: {hours}h {minutes}m")
    print()

    # Save final progress
    save_last_export_progress(current_progress)

    if interrupt_requested:
        print("Migration interrupted by user. Progress has been saved.")
        print("Run the script again to resume from where it left off.")
    else:
        print("Migration completed successfully!")
        # Clear progress file on successful completion
        if LAST_EXPORT_FILE.exists():
            LAST_EXPORT_FILE.unlink()

def signal_handler(signum, frame):
    """Handle interrupt signals gracefully"""
    global interrupt_requested
    interrupt_requested = True
    print("\n\nInterrupt received. Finishing current email and saving progress...")

def main():
    """Main entry point"""
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print("=" * 60)
    print("EMAIL MIGRATION SCRIPT")
    print("=" * 60)
    print(f"Export directory: {EMAIL_DIR}")
    print(f"  - Sent emails: {SENT_DIR}")
    print(f"  - Received emails: {RECEIVED_DIR}")
    print()
    print("This script will migrate ALL emails (not just today's).")
    print("It will skip emails that have already been exported.")
    print()

    migrate_all_emails()

if __name__ == "__main__":
    main()
