#!/usr/bin/env python3
"""
Gmail API-based email export script.
Exports Gmail messages (sent and received) for multiple accounts
using Gmail API with incremental approach.
Supports multi-account via config.json.
"""

import argparse
import os
import sys
import re
import signal
import base64
import json
import fcntl
import atexit
from pathlib import Path
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from html import unescape
from repo_paths import resolve_private_repo_root

# PST timezone (UTC-8), PDT is UTC-7 but we'll use PST for simplicity
# For daylight saving time handling, you may want to use pytz library in the future
PST = timezone(timedelta(hours=-8))

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    print("Error: Gmail API libraries not installed.", file=sys.stderr)
    print("Install with: pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib", file=sys.stderr)
    sys.exit(1)

GMAIL_READONLY_SCOPE = 'https://www.googleapis.com/auth/gmail.readonly'
GMAIL_SEND_SCOPE = 'https://www.googleapis.com/auth/gmail.send'

PRIVATE_REPO_ROOT = resolve_private_repo_root()
EMAIL_DIR = PRIVATE_REPO_ROOT / "notes-private" / "email"

# Credentials and token file paths
SCRIPT_DIR = PRIVATE_REPO_ROOT / "scripts" / "exports" / "email"
CREDENTIALS_FILE = SCRIPT_DIR / "credentials.json"
TOKEN_DIR = SCRIPT_DIR / "tokens"
CONFIG_FILE = SCRIPT_DIR / "config.json"

# Ensure directories exist
TOKEN_DIR.mkdir(parents=True, exist_ok=True)

# Global flag for interrupt handling
interrupt_requested = False

# Global lock file handle
lock_file = None

class EmailAccount:
    """Represents a Gmail account with its configuration"""

    def __init__(self, email, enabled=True, allow_send=False, assistant_name=None, assistant_signature=None):
        self.email = email
        self.enabled = enabled
        self.allow_send = allow_send
        self.assistant_name = assistant_name
        self.assistant_signature = assistant_signature
        # Sanitize email for filename
        email_safe = email.replace('@', '_at_').replace('.', '_')
        self.token_file = TOKEN_DIR / f"token_{email_safe}.json"
        self.last_export_file = EMAIL_DIR / f".last_incremental_export_{email_safe}"
        self.message_id_index_file = EMAIL_DIR / f".message_id_index_{email_safe}.json"
        self.account_dir = EMAIL_DIR / email
        self.sent_dir = self.account_dir / "sent"
        self.received_dir = self.account_dir / "received"

    @property
    def scopes(self):
        scopes = [GMAIL_READONLY_SCOPE]
        if self.allow_send:
            scopes.append(GMAIL_SEND_SCOPE)
        return scopes

    def verify_account(self, service):
        """Verify that the authenticated account matches the expected email"""
        try:
            # Get the user's profile to verify account
            profile = service.users().getProfile(userId='me').execute()
            authenticated_email = profile.get('emailAddress', '')

            if authenticated_email.lower() == self.email.lower():
                return True
            else:
                print(f"WARNING: Authenticated account is '{authenticated_email}', but expected '{self.email}'", file=sys.stderr)
                return False
        except Exception as e:
            print(f"Error verifying account: {e}", file=sys.stderr)
            return False

    def get_credentials(self):
        """Get valid user credentials for this account, with account verification"""
        creds = None

        # Try to load existing token
        if self.token_file.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(self.token_file), self.scopes)
            except Exception as e:
                print(f"Warning: Could not load existing token for {self.email}: {e}", file=sys.stderr)

        # If no valid credentials, refresh or get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    print(f"Error refreshing token for {self.email}: {e}", file=sys.stderr)
                    creds = None

            # Need to authenticate
            if not creds:
                if not CREDENTIALS_FILE.exists():
                    print(f"Error: credentials.json not found at {CREDENTIALS_FILE}", file=sys.stderr)
                    print("Please download credentials.json from Google Cloud Console.", file=sys.stderr)
                    print("See email/setup/gmail_api_implementation.md for setup instructions.", file=sys.stderr)
                    return None

                print(f"Authenticating {self.email}...")
                print(f"⚠️  IMPORTANT: Please sign in with {self.email} when the browser opens!", file=sys.stderr)
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), self.scopes)
                    creds = flow.run_local_server(port=0)
                except Exception as e:
                    print(f"Error during OAuth flow for {self.email}: {e}", file=sys.stderr)
                    return None

            # Verify the account matches
            try:
                service = build('gmail', 'v1', credentials=creds)
                if not self.verify_account(service):
                    print(f"ERROR: Authentication failed - wrong account detected!", file=sys.stderr)
                    print(f"Expected: {self.email}", file=sys.stderr)
                    print(f"Please delete the token file and try again: {self.token_file}", file=sys.stderr)
                    # Delete the incorrect token
                    if self.token_file.exists():
                        self.token_file.unlink()
                    return None
            except Exception as e:
                print(f"Error verifying account after authentication: {e}", file=sys.stderr)
                # Still save the token, but warn
                print(f"WARNING: Could not verify account, but saving token anyway", file=sys.stderr)

            # Save credentials for next run
            try:
                with open(self.token_file, 'w') as token:
                    token.write(creds.to_json())
                print(f"Saved credentials for {self.email}")
            except Exception as e:
                print(f"Warning: Could not save token for {self.email}: {e}", file=sys.stderr)
        else:
            # Verify existing token is for the correct account
            try:
                service = build('gmail', 'v1', credentials=creds)
                if not self.verify_account(service):
                    print(f"ERROR: Token mismatch detected! Token is for wrong account.", file=sys.stderr)
                    print(f"Expected: {self.email}", file=sys.stderr)
                    print(f"Deleting incorrect token. Please re-authenticate.", file=sys.stderr)
                    # Delete the incorrect token
                    if self.token_file.exists():
                        self.token_file.unlink()
                    return None
            except Exception as e:
                print(f"Error verifying existing token: {e}", file=sys.stderr)
                # Continue anyway - might be a temporary API issue

        return creds

    def get_last_export_time(self):
        """Load the last incremental export time for this account (defaults to start of today)."""
        if self.last_export_file.exists():
            try:
                content = self.last_export_file.read_text().strip()
                if content:
                    last_export = datetime.fromisoformat(content)
                    # Make timezone-aware if it's naive
                    if last_export.tzinfo is None:
                        last_export = last_export.replace(tzinfo=timezone.utc)
                    # If last export was today, use start of today
                    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
                    if last_export.date() == datetime.now(timezone.utc).date():
                        return today_start
                    return last_export
            except Exception:
                pass
        # Default to start of today (timezone-aware)
        return datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    def save_last_export_time(self, timestamp):
        """Persist the last incremental export time for this account."""
        try:
            self.last_export_file.parent.mkdir(parents=True, exist_ok=True)
            self.last_export_file.write_text(timestamp.isoformat())
        except Exception as exc:
            print(f"Warning: failed to save last export time for {self.email}: {exc}", file=sys.stderr)

    def load_message_id_index(self):
        """Load the message ID index (maps message_id -> file_path)."""
        if self.message_id_index_file.exists():
            try:
                with open(self.message_id_index_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load message ID index for {self.email}: {e}", file=sys.stderr)
                return {}
        return {}

    def save_message_id_index(self, index):
        """Save the message ID index."""
        try:
            self.message_id_index_file.parent.mkdir(parents=True, exist_ok=True)
            # Write atomically by writing to a temp file first
            temp_file = self.message_id_index_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(index, f, indent=2, ensure_ascii=False)
            temp_file.replace(self.message_id_index_file)
        except Exception as exc:
            print(f"Warning: failed to save message ID index for {self.email}: {exc}", file=sys.stderr)

    def add_message_to_index(self, message_id, file_path):
        """Add a message ID to the index."""
        index = self.load_message_id_index()
        # Store relative path from EMAIL_DIR
        rel_path = str(file_path.relative_to(EMAIL_DIR))
        index[message_id] = rel_path
        self.save_message_id_index(index)

    def is_message_exported(self, message_id):
        """Check if a message ID has already been exported."""
        index = self.load_message_id_index()
        if message_id not in index:
            return False

        # Verify the file still exists
        stored_path = EMAIL_DIR / index[message_id]
        return stored_path.exists()

def load_accounts():
    """Load email accounts from config.json"""
    if not CONFIG_FILE.exists():
        print(f"Config file not found: {CONFIG_FILE}", file=sys.stderr)
        print("Creating example config file...", file=sys.stderr)
        create_example_config()
        print("Please edit config.json and add your accounts, then run again.", file=sys.stderr)
        return []

    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)

        accounts = []
        for account_config in config.get('accounts', []):
            account = EmailAccount(
                email=account_config.get('email'),
                enabled=account_config.get('enabled', True),
                allow_send=account_config.get('allow_send', False),
                assistant_name=account_config.get('assistant_name'),
                assistant_signature=account_config.get('assistant_signature'),
            )
            accounts.append(account)

        return accounts
    except json.JSONDecodeError as e:
        print(f"Error parsing config.json: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"Error loading config: {e}", file=sys.stderr)
        return []

def create_example_config():
    """Create an example config.json file"""
    example_config = {
        "accounts": [
            {
                "email": "user@example.com",
                "enabled": True,
                "allow_send": False
            }
        ]
    }

    example_file = SCRIPT_DIR / "config.json.example"
    with open(example_file, 'w', encoding='utf-8') as f:
        json.dump(example_config, f, indent=2)
    print(f"Created example config at {example_file}")

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

    # Convert common HTML formatting to markdown
    text = re.sub(r'<strong>(.*?)</strong>', r'**\1**', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<b>(.*?)</b>', r'**\1**', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<em>(.*?)</em>', r'*\1*', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<i>(.*?)</i>', r'*\1*', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<p[^>]*>(.*?)</p>', r'\1\n\n', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<br[^>]*>', '\n', text, flags=re.IGNORECASE)

    # Links: <a href="...">text</a> → [text](url)
    def replace_link(match):
        url = match.group(1)  # href value
        link_text = match.group(2) if match.group(2) else url  # link text
        return f"[{link_text}]({url})"

    text = re.sub(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', replace_link, text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
    text = text.strip()

    return text

def format_date_for_filename(date_dt):
    """Convert datetime to YYYY-MM-DD format for filename using PST timezone"""
    if isinstance(date_dt, datetime):
        # Convert to PST if timezone-aware
        if date_dt.tzinfo is not None:
            # Convert UTC to PST
            pst_dt = date_dt.astimezone(PST)
        else:
            # Assume UTC if naive
            pst_dt = date_dt.replace(tzinfo=timezone.utc).astimezone(PST)
        return pst_dt.strftime("%Y-%m-%d")
    return datetime.now(PST).strftime("%Y-%m-%d")

def decode_message_body(parts):
    """Decode email body from Gmail API message parts."""
    body_text = ""
    body_html = ""

    for part in parts:
        mime_type = part.get('mimeType', '')
        data = part.get('body', {}).get('data')

        if data:
            try:
                decoded = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                if mime_type == 'text/plain':
                    body_text = decoded
                elif mime_type == 'text/html':
                    body_html = decoded
            except Exception as e:
                print(f"  Warning: Could not decode message part: {e}")

        # Recursively handle nested parts (multipart messages)
        if 'parts' in part:
            nested_text, nested_html = decode_message_body(part['parts'])
            if nested_text:
                body_text = nested_text
            if nested_html:
                body_html = nested_html

    return body_text, body_html

def get_header_value(headers, name):
    """Get header value by name from Gmail API headers list."""
    for header in headers:
        if header['name'].lower() == name.lower():
            return header['value']
    return ""

def parse_gmail_date(date_str):
    """Parse date from Gmail header to datetime."""
    if not date_str:
        return None
    try:
        return parsedate_to_datetime(date_str)
    except Exception:
        return None

def fetch_message_details(service, message_id):
    """Fetch full message details from Gmail API."""
    try:
        message = service.users().messages().get(userId='me', id=message_id, format='full').execute()

        payload = message.get('payload', {})
        headers = payload.get('headers', [])

        # Extract headers
        subject = get_header_value(headers, 'Subject') or "(No Subject)"
        from_addr = get_header_value(headers, 'From') or "(unknown)"
        to_addr = get_header_value(headers, 'To') or "(none)"
        cc_addr = get_header_value(headers, 'Cc') or "(none)"
        bcc_addr = get_header_value(headers, 'Bcc') or "(none)"
        date_str = get_header_value(headers, 'Date') or ""

        # Parse date
        email_datetime = parse_gmail_date(date_str)
        if not email_datetime:
            email_datetime = datetime.now()

        # Decode body
        parts = payload.get('parts', [])
        if not parts:
            # Single part message
            data = payload.get('body', {}).get('data')
            body_text = ""
            body_html = ""
            if data:
                try:
                    decoded = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                    mime_type = payload.get('mimeType', '')
                    if mime_type == 'text/plain':
                        body_text = decoded
                    elif mime_type == 'text/html':
                        body_html = decoded
                except Exception:
                    pass
        else:
            body_text, body_html = decode_message_body(parts)

        # Prefer HTML, fallback to text
        email_content = body_html if body_html else body_text

        # Format date string for display (ISO format)
        date_display = email_datetime.isoformat()

        return {
            'subject': subject,
            'from': from_addr,
            'to': to_addr,
            'cc': cc_addr,
            'bcc': bcc_addr,
            'date': date_display,
            'datetime': email_datetime,
            'content': email_content
        }
    except HttpError as error:
        print(f"  Error fetching message {message_id}: {error}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  Error processing message {message_id}: {e}", file=sys.stderr)
        return None

def get_emails_since(service, since_dt, label='INBOX', max_results=500):
    """
    Get email message IDs since the provided datetime using Gmail API search.
    Uses search query: 'in:inbox after:YYYY/MM/DD' or 'in:sent after:YYYY/MM/DD'
    """
    since_dt_rounded = since_dt.replace(microsecond=0)
    date_str = since_dt_rounded.strftime("%Y/%m/%d")

    # Build search query
    if label.upper() == 'SENT':
        query = f'in:sent after:{date_str}'
        label_name = 'sent'
    else:
        query = f'in:inbox after:{date_str}'
        label_name = 'inbox'

    print(f"  Searching {label_name} for messages after {date_str}...")

    message_ids = []
    page_token = None

    try:
        while True:
            # List messages with search query
            results = service.users().messages().list(
                userId='me',
                q=query,
                maxResults=min(500, max_results - len(message_ids)),
                pageToken=page_token
            ).execute()

            messages = results.get('messages', [])
            message_ids.extend([msg['id'] for msg in messages])

            print(f"    Found {len(message_ids)} messages so far...", end='\r')

            # Check if we've reached the limit
            if len(message_ids) >= max_results:
                break

            # Check for next page
            page_token = results.get('nextPageToken')
            if not page_token:
                break

        print(f"\n    Found {len(message_ids)} total messages in {label_name} since {date_str}")
        return message_ids

    except HttpError as error:
        print(f"\n  Error searching messages: {error}", file=sys.stderr)
        return []

def process_emails(service, message_ids, output_dir, email_type="sent", since_dt=None, account=None):
    """Process and export a list of email message IDs to markdown files."""
    global interrupt_requested

    exported_count = 0
    skipped_count = 0
    error_count = 0
    latest_timestamp = None

    # Cache the message ID index in memory for performance (avoid loading from disk for each message)
    message_id_index_cache = None
    if account:
        message_id_index_cache = account.load_message_id_index()

    # Track message_ids processed in this batch to avoid processing duplicates in the same run
    processed_in_batch = set()

    for i, message_id in enumerate(message_ids, 1):
        # Skip if we've already processed this message_id in this batch (Gmail API might return duplicates)
        if message_id in processed_in_batch:
            skipped_count += 1
            continue
        processed_in_batch.add(message_id)
        if interrupt_requested:
            print("\n\nExport stopped by user. Files written so far have been saved.")
            return exported_count, skipped_count, error_count, latest_timestamp

        if i % 10 == 0:
            print(f"  Processing {i}/{len(message_ids)} messages...", end='\r')

        # Check if message was already exported (using cached index)
        if account and message_id_index_cache is not None:
            if message_id in message_id_index_cache:
                stored_path = EMAIL_DIR / message_id_index_cache[message_id]
                if stored_path.exists():
                    skipped_count += 1
                    continue

        # Fetch message details
        message_data = fetch_message_details(service, message_id)
        if not message_data:
            error_count += 1
            continue

        # Store message_id in message_data
        message_data['message_id'] = message_id

        email_datetime = message_data['datetime']

        # Filter by date if needed (double-check since search might include edge cases)
        if since_dt and email_datetime < since_dt:
            continue

        email_subject = message_data['subject']
        email_from = message_data['from']
        email_to = message_data['to']
        email_cc = message_data['cc']
        email_bcc = message_data['bcc']
        email_date = message_data['date']
        email_content = message_data['content']

        # Generate filename
        date_str = format_date_for_filename(email_datetime)
        safe_subject = sanitize_filename(email_subject)
        filename = f"{date_str}_{safe_subject}.md"

        # Determine output directory based on date (YYYY/MM/) in PST
        # Convert to PST for directory structure
        if email_datetime.tzinfo is not None:
            pst_dt = email_datetime.astimezone(PST)
        else:
            pst_dt = email_datetime.replace(tzinfo=timezone.utc).astimezone(PST)
        year = pst_dt.strftime("%Y")
        month = pst_dt.strftime("%m")
        month_dir = output_dir / year / month
        month_dir.mkdir(parents=True, exist_ok=True)

        file_path = month_dir / filename

        # Handle duplicate filenames
        counter = 1
        while file_path.exists():
            filename = f"{date_str}_{safe_subject}_{counter}.md"
            file_path = month_dir / filename
            counter += 1

        # Convert HTML to markdown
        markdown_content = html_to_markdown(email_content)

        def display_line(label, value):
            value = value.strip() if value else ""
            if not value:
                value = "(none)"
            return f"**{label}:** {value}\n\n"

        # Get message ID for YAML frontmatter
        message_id = message_data.get('message_id', '')

        # Write markdown file with YAML frontmatter
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                # Write YAML frontmatter with message ID
                f.write("---\n")
                f.write(f"message_id: {message_id}\n")
                f.write(f"email_type: {email_type}\n")
                f.write(f"exported_at: {datetime.now(timezone.utc).isoformat()}\n")
                f.write("---\n\n")

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

            # Add to index (both in-memory cache and persist to disk)
            if account and message_id_index_cache is not None:
                rel_path = str(file_path.relative_to(EMAIL_DIR))
                message_id_index_cache[message_id] = rel_path
                # Persist to disk
                account.save_message_id_index(message_id_index_cache)

            exported_count += 1
            if email_datetime and (latest_timestamp is None or email_datetime > latest_timestamp):
                latest_timestamp = email_datetime
            print(f"[{i}/{len(message_ids)}] Exported: {email_subject[:50]}...")
        except Exception as e:
            error_count += 1
            print(f"[{i}/{len(message_ids)}] Error writing file: {e}", file=sys.stderr)

    return exported_count, skipped_count, error_count, latest_timestamp

def acquire_lock():
    """Acquire a file lock to prevent concurrent script runs."""
    global lock_file
    lock_file_path = SCRIPT_DIR / ".export_lock"

    try:
        lock_file = open(lock_file_path, 'w')
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        lock_file.write(f"{os.getpid()}\n")
        lock_file.flush()
        return True
    except (IOError, OSError):
        if lock_file:
            lock_file.close()
        lock_file = None
        print("ERROR: Another instance of the script is already running!", file=sys.stderr)
        print(f"       If this is incorrect, delete: {lock_file_path}", file=sys.stderr)
        return False

def release_lock():
    """Release the file lock."""
    global lock_file
    if lock_file:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            lock_file.close()
            lock_file_path = SCRIPT_DIR / ".export_lock"
            if lock_file_path.exists():
                lock_file_path.unlink()
        except Exception:
            pass
        lock_file = None

def export_emails_for_account(account, since_dt):
    """Export emails for a specific account."""
    global interrupt_requested

    account.sent_dir.mkdir(parents=True, exist_ok=True)
    account.received_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"Exporting emails for {account.email}")
    print(f"{'='*60}")
    print(f"Account directory: {account.account_dir}")
    print(f"  - Sent emails: {account.sent_dir}")
    print(f"  - Received emails: {account.received_dir}")
    print(f"Last export marker: {account.last_export_file}")
    print(f"Message ID index: {account.message_id_index_file}")
    print(f"Exporting emails modified on/after: {since_dt.isoformat()}")
    print()

    print("Authenticating with Gmail API...")
    creds = account.get_credentials()
    if not creds:
        print(f"ERROR: Could not authenticate {account.email} with Gmail API")
        return False, 0, 0, None

    try:
        service = build('gmail', 'v1', credentials=creds)
    except Exception as e:
        print(f"Error building Gmail service for {account.email}: {e}", file=sys.stderr)
        return False, 0, 0, None

    print("Authentication successful!")
    print()

    try:
        total_exported = 0
        total_errors = 0
        latest_timestamp = None

        # Get received emails (inbox)
        print(f"Fetching received emails since {since_dt.isoformat()}...")
        received_message_ids = get_emails_since(service, since_dt, label='INBOX')
        if received_message_ids:
            print(f"Processing {len(received_message_ids)} received emails...")
            exported, skipped, errors, latest = process_emails(service, received_message_ids, account.received_dir, "received", since_dt=since_dt, account=account)
            total_exported += exported
            total_errors += errors
            if latest and (latest_timestamp is None or latest > latest_timestamp):
                latest_timestamp = latest
            print(f"  - Received emails exported: {exported}")
            print(f"  - Received emails skipped (already exported): {skipped}")
            print(f"  - Received emails errors: {errors}")
        else:
            print("No new received emails found.")
        print()

        # Get sent emails
        print(f"Fetching sent emails since {since_dt.isoformat()}...")
        sent_message_ids = get_emails_since(service, since_dt, label='SENT')
        if sent_message_ids:
            print(f"Processing {len(sent_message_ids)} sent emails...")
            exported, skipped, errors, latest = process_emails(service, sent_message_ids, account.sent_dir, "sent", since_dt=since_dt, account=account)
            total_exported += exported
            total_errors += errors
            if latest and (latest_timestamp is None or latest > latest_timestamp):
                latest_timestamp = latest
            print(f"  - Sent emails exported: {exported}")
            print(f"  - Sent emails skipped (already exported): {skipped}")
            print(f"  - Sent emails errors: {errors}")
        else:
            print("No new sent emails found.")

        print(f"\nExport summary for {account.email}:")
        print(f"  - Total emails exported: {total_exported}")
        print(f"  - Total errors: {total_errors}")
        print(f"  - Time window start: {since_dt.isoformat()}")
        if latest_timestamp:
            print(f"  - Latest email timestamp: {latest_timestamp.isoformat()}")

        return True, total_exported, total_errors, latest_timestamp
    except Exception as e:
        print(f"Error during export for {account.email}: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return False, 0, 0, None

def signal_handler(signum, frame):
    """Handle interrupt signals gracefully"""
    global interrupt_requested
    interrupt_requested = True
    print("\n\nInterrupt received. Finishing current email...")
    release_lock()

def parse_arguments():
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Export Gmail emails using Gmail API since the last export time."
    )
    parser.add_argument(
        "--since",
        help="ISO timestamp (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS) to start exporting from. "
             "Defaults to the last saved export time or start of today if none."
    )
    return parser.parse_args()

def main():
    """Main entry point"""
    args = parse_arguments()

    # Register cleanup handler
    atexit.register(release_lock)

    # Acquire lock to prevent concurrent runs
    if not acquire_lock():
        sys.exit(1)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print("=" * 60)
    print("Gmail API Email Export Script (Multi-Account)")
    print("=" * 60)
    print(f"Export directory: {EMAIL_DIR}")
    print()

    # Load accounts from config
    accounts = load_accounts()
    if not accounts:
        print("No accounts configured. Please set up config.json", file=sys.stderr)
        sys.exit(1)

    enabled_accounts = [acc for acc in accounts if acc.enabled]
    if not enabled_accounts:
        print("No enabled accounts found in config.json", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(enabled_accounts)} enabled account(s)\n")

    # Process each account
    all_success = True
    total_exported = 0
    total_errors = 0

    for account in enabled_accounts:
        # Get since_dt for this account
        since_dt = None
        if args.since:
            since_input = args.since.strip()
            try:
                since_dt = datetime.fromisoformat(since_input)
            except ValueError:
                try:
                    since_dt = datetime.fromisoformat(f"{since_input}T00:00:00")
                except ValueError:
                    print(f"Invalid --since format for {account.email}. Use YYYY-MM-DD or full ISO timestamp.", file=sys.stderr)
                    continue
            # Make timezone-aware if it's naive
            if since_dt.tzinfo is None:
                since_dt = since_dt.replace(tzinfo=timezone.utc)
        else:
            since_dt = account.get_last_export_time()

        success, exported, errors, latest_timestamp = export_emails_for_account(account, since_dt)

        if success:
            if latest_timestamp:
                account.save_last_export_time(latest_timestamp)
                print(f"\nUpdated last export time for {account.email} to {latest_timestamp.isoformat()}")
            else:
                print(f"\nNo newer emails found for {account.email}. Last export time unchanged.")

            total_exported += exported
            total_errors += errors
        else:
            all_success = False
            print(f"\nExport failed for {account.email}. Check errors above.")

        print()

    print("=" * 60)
    print("Overall Export Summary")
    print("=" * 60)
    print(f"  - Total emails exported: {total_exported}")
    print(f"  - Total errors: {total_errors}")

    if all_success:
        print("\nExport completed successfully for all accounts!")
        sys.exit(0)
    else:
        print("\nExport completed with errors. Check errors above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
