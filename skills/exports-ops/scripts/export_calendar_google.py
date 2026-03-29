#!/usr/bin/env python3
"""
Google Calendar export script.
Exports calendar events from Google Calendar API to markdown format.
Supports multiple accounts via config.json.
Exports weekly calendar view (last week + upcoming week) and maintains 
monthly historical archive.

Requires:
- google-api-python-client
- google-auth-httplib2
- google-auth-oauthlib
- credentials.json (OAuth 2.0 credentials from Google Cloud Console)
- config.json (account configuration)
"""

import os
import sys
import re
import json
from pathlib import Path
from datetime import datetime, timedelta
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from repo_paths import resolve_private_repo_root

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

PRIVATE_REPO_ROOT = resolve_private_repo_root()
CALENDAR_DIR = PRIVATE_REPO_ROOT / "notes-private" / "calendar"
ARCHIVE_DIR = CALENDAR_DIR / "archive"
SCRIPT_DIR = PRIVATE_REPO_ROOT / "scripts" / "exports" / "calendar"
CREDENTIALS_FILE = SCRIPT_DIR / "credentials.json"
TOKEN_DIR = SCRIPT_DIR / "tokens"
CONFIG_FILE = SCRIPT_DIR / "config.json"
LOG_FILE = CALENDAR_DIR / "export.log"

# Ensure directories exist
TOKEN_DIR.mkdir(parents=True, exist_ok=True)
ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

class CalendarAccount:
    """Represents a Google Calendar account with its configuration"""
    
    def __init__(self, email, calendar_ids, enabled=True):
        self.email = email
        self.calendar_ids = calendar_ids if isinstance(calendar_ids, list) else [calendar_ids]
        self.enabled = enabled
        # Sanitize email for filename
        email_safe = email.replace('@', '_at_').replace('.', '_')
        self.token_file = TOKEN_DIR / f"token_{email_safe}.json"
    
    def verify_account(self, service):
        """Verify that the authenticated account matches the expected email"""
        try:
            # Get the primary calendar to verify account
            calendar_list = service.calendarList().list().execute()
            primary_calendar = None
            for calendar in calendar_list.get('items', []):
                if calendar.get('primary', False):
                    primary_calendar = calendar
                    break
            
            if primary_calendar:
                primary_id = primary_calendar.get('id', '')
                # Primary calendar ID should match the account email
                if primary_id.lower() == self.email.lower():
                    return True
                else:
                    log_message(f"WARNING: Authenticated account primary calendar is '{primary_id}', but expected '{self.email}'", error=True)
                    return False
            else:
                # If no primary calendar found, try to verify by checking if we can access the account's calendar
                try:
                    # Try to access the account's calendar directly
                    service.calendars().get(calendarId=self.email).execute()
                    return True
                except HttpError:
                    log_message(f"WARNING: Could not verify account - primary calendar not found and cannot access {self.email} calendar", error=True)
                    return False
        except Exception as e:
            log_message(f"Error verifying account: {e}", error=True)
            return False
    
    def get_credentials(self):
        """Get valid user credentials for this account, with account verification"""
        creds = None
        
        # Try to load existing token
        if self.token_file.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(self.token_file), SCOPES)
            except Exception as e:
                log_message(f"Error loading token for {self.email}: {e}", error=True)
        
        # If no valid credentials, refresh or get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    log_message(f"Error refreshing token for {self.email}: {e}", error=True)
                    creds = None
            
            # Need to authenticate
            if not creds:
                if not CREDENTIALS_FILE.exists():
                    log_message(f"Credentials file not found: {CREDENTIALS_FILE}", error=True)
                    log_message("Please follow the setup guide: calendar/setup/google_calendar_api_setup.md", error=True)
                    return None
                
                log_message(f"Authenticating {self.email}...")
                log_message(f"⚠️  IMPORTANT: Please sign in with {self.email} when the browser opens!")
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(CREDENTIALS_FILE), SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Verify the account matches
            try:
                service = build('calendar', 'v3', credentials=creds)
                if not self.verify_account(service):
                    log_message(f"ERROR: Authentication failed - wrong account detected!", error=True)
                    log_message(f"Expected: {self.email}", error=True)
                    log_message(f"Please delete the token file and try again: {self.token_file}", error=True)
                    # Delete the incorrect token
                    if self.token_file.exists():
                        self.token_file.unlink()
                    return None
            except Exception as e:
                log_message(f"Error verifying account after authentication: {e}", error=True)
                # Still save the token, but warn
                log_message(f"WARNING: Could not verify account, but saving token anyway", error=True)
            
            # Save credentials for next run
            try:
                with open(self.token_file, 'w') as token:
                    token.write(creds.to_json())
                log_message(f"Saved credentials for {self.email}")
            except Exception as e:
                log_message(f"Error saving token for {self.email}: {e}", error=True)
        else:
            # Verify existing token is for the correct account
            try:
                service = build('calendar', 'v3', credentials=creds)
                if not self.verify_account(service):
                    log_message(f"ERROR: Token mismatch detected! Token is for wrong account.", error=True)
                    log_message(f"Expected: {self.email}", error=True)
                    log_message(f"Deleting incorrect token. Please re-authenticate.", error=True)
                    # Delete the incorrect token
                    if self.token_file.exists():
                        self.token_file.unlink()
                    return None
            except Exception as e:
                log_message(f"Error verifying existing token: {e}", error=True)
                # Continue anyway - might be a temporary API issue
        
        return creds

def log_message(message, error=False):
    """Log message to file and stdout"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {'ERROR' if error else 'INFO'}: {message}\n"
    
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_entry)
    except:
        pass
    
    if error:
        print(message, file=sys.stderr)
    else:
        print(message)

def load_accounts():
    """Load calendar accounts from config.json"""
    if not CONFIG_FILE.exists():
        log_message(f"Config file not found: {CONFIG_FILE}", error=True)
        log_message("Creating example config file...")
        create_example_config()
        log_message("Please edit config.json and add your accounts, then run again.", error=True)
        return []
    
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        accounts = []
        for account_config in config.get('accounts', []):
            account = CalendarAccount(
                email=account_config.get('email'),
                calendar_ids=account_config.get('calendar_ids', []),
                enabled=account_config.get('enabled', True)
            )
            accounts.append(account)
        
        return accounts
    except json.JSONDecodeError as e:
        log_message(f"Error parsing config.json: {e}", error=True)
        return []
    except Exception as e:
        log_message(f"Error loading config: {e}", error=True)
        return []

def create_example_config():
    """Create an example config.json file"""
    example_config = {
        "accounts": [
            {
                "email": "user@example.com",
                "calendar_ids": ["user@example.com"],
                "enabled": True
            }
        ]
    }
    
    example_file = SCRIPT_DIR / "config.json.example"
    with open(example_file, 'w', encoding='utf-8') as f:
        json.dump(example_config, f, indent=2)
    log_message(f"Created example config at {example_file}")

def get_calendar_list(service):
    """Get list of accessible calendars"""
    try:
        calendar_list = service.calendarList().list().execute()
        calendars = []
        for calendar in calendar_list.get('items', []):
            calendars.append({
                'id': calendar['id'],
                'summary': calendar.get('summary', 'Unknown'),
                'primary': calendar.get('primary', False)
            })
        return calendars
    except HttpError as error:
        log_message(f"Error getting calendar list: {error}", error=True)
        return []

def get_events_for_date(service, calendar_id, target_date):
    """Get events for a specific calendar and date"""
    # Convert date to RFC3339 format for API
    time_min = target_date.replace(hour=0, minute=0, second=0, microsecond=0).isoformat() + 'Z'
    time_max = target_date.replace(hour=23, minute=59, second=59, microsecond=0).isoformat() + 'Z'
    
    try:
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            maxResults=2500,  # Google Calendar API limit
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        return events_result.get('items', [])
    except HttpError as error:
        log_message(f"Error getting events for calendar {calendar_id}: {error}", error=True)
        return []

def get_upcoming_events(service, calendar_id, start_date, end_date):
    """Get events for a date range"""
    time_min = start_date.replace(hour=0, minute=0, second=0, microsecond=0).isoformat() + 'Z'
    time_max = end_date.replace(hour=23, minute=59, second=59, microsecond=0).isoformat() + 'Z'
    
    try:
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            maxResults=2500,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        return events_result.get('items', [])
    except HttpError as error:
        log_message(f"Error getting upcoming events for calendar {calendar_id}: {error}", error=True)
        return []

def format_event_time(event):
    """Format event start/end time for display"""
    start = event.get('start', {})
    end = event.get('end', {})
    
    # Check if all-day event
    if 'date' in start:
        return "All Day", None, None
    
    # Parse datetime
    start_dt = datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
    end_dt = datetime.fromisoformat(end['dateTime'].replace('Z', '+00:00'))
    
    start_str = start_dt.strftime("%H:%M")
    end_str = end_dt.strftime("%H:%M")
    time_str = f"{start_str} - {end_str}"
    
    return time_str, start_dt, end_dt

def format_event_markdown(event, calendar_name, account_email=None):
    """Format a single event as markdown"""
    time_str, start_dt, end_dt = format_event_time(event)
    
    markdown = f"### {time_str}\n"
    markdown += f"**{event.get('summary', 'No Title')}**\n"
    
    # Check if event is shared (organizer differs from account email)
    organizer = event.get('organizer', {})
    organizer_email = organizer.get('email', '').lower() if organizer else ''
    is_shared_event = account_email and organizer_email and organizer_email != account_email.lower()
    
    if is_shared_event:
        organizer_name = organizer.get('displayName', organizer_email)
        markdown += f"- **Shared event** — Created by: {organizer_name}\n"
    
    location = event.get('location')
    if location:
        markdown += f"- Location: {location}\n"
    
    attendees = event.get('attendees', [])
    if attendees:
        attendee_names = [att.get('displayName', att.get('email', 'Unknown')) for att in attendees]
        markdown += f"- Attendees: {', '.join(attendee_names)}\n"
    
    if calendar_name:
        markdown += f"- Calendar: {calendar_name}\n"
    
    if account_email:
        markdown += f"- Account: {account_email}\n"
    
    description = event.get('description')
    if description:
        # Clean up HTML if present, limit length
        desc = re.sub(r'<[^>]+>', '', description).strip()
        if len(desc) > 200:
            desc = desc[:200] + "..."
        markdown += f"- Notes: {desc}\n"
    
    markdown += "\n"
    return markdown

def get_events_for_date_from_accounts(accounts_data, target_date):
    """Get all events for a specific date from all accounts (deduplicated by event ID, preferring calendar owner)"""
    events_by_id = {}  # event_id -> event dict
    
    for account, service in accounts_data:
        if not account.enabled:
            continue
        
        calendars = get_calendar_list(service)
        calendar_names = {cal['id']: cal['summary'] for cal in calendars}
        
        # Use configured calendar IDs or all accessible calendars
        if account.calendar_ids:
            calendar_ids = account.calendar_ids
        else:
            calendar_ids = [cal['id'] for cal in calendars]
            # Always include the account's own calendar ID (primary calendar)
            # Even if it's not in the calendar list, we should query it
            if account.email not in calendar_ids:
                calendar_ids.append(account.email)
                # Try to get the summary from calendar list, or use email as fallback
                if account.email not in calendar_names:
                    calendar_names[account.email] = account.email
        
        for cal_id in calendar_ids:
            calendar_name = calendar_names.get(cal_id, cal_id)
            events = get_events_for_date(service, cal_id, target_date)
            
            for event in events:
                event_id = event.get('id')
                
                # Check if this account "owns" the calendar (calendar ID matches account email)
                is_calendar_owner = (cal_id.lower() == account.email.lower())
                
                if event_id:
                    # If we've seen this event before, only replace it if this account owns the calendar
                    if event_id in events_by_id:
                        if is_calendar_owner:
                            # Replace with the owner's version
                            event['_calendar_name'] = calendar_name
                            event['_account_email'] = account.email
                            events_by_id[event_id] = event
                        # Otherwise, keep the existing one
                    else:
                        # New event, add it
                        event['_calendar_name'] = calendar_name
                        event['_account_email'] = account.email
                        events_by_id[event_id] = event
                else:
                    # Event without ID (shouldn't happen, but handle it)
                    event['_calendar_name'] = calendar_name
                    event['_account_email'] = account.email
                    # Use a temporary key for events without IDs
                    events_by_id[f"no_id_{len(events_by_id)}"] = event
    
    # Convert to list and sort by start time
    all_events = list(events_by_id.values())
    all_events.sort(key=lambda e: e.get('start', {}).get('dateTime', e.get('start', {}).get('date', '')))
    
    return all_events

def archive_today_to_monthly(accounts_data):
    """Archive today's events to monthly archive file"""
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    date_str = today.strftime("%Y-%m-%d")
    date_display = today.strftime("%A, %B %d, %Y")
    
    log_message(f"Archiving today's calendar ({date_str}) to monthly archive...")
    
    # Get all events for today from all accounts
    all_events = get_events_for_date_from_accounts(accounts_data, today)
    
    # Generate markdown for this day
    day_markdown = f"## {date_str} ({date_display})\n\n"
    
    if not all_events:
        day_markdown += "No events scheduled.\n\n"
    else:
        for event in all_events:
            day_markdown += format_event_markdown(
                event,
                event.get('_calendar_name'),
                event.get('_account_email') if len(accounts_data) > 1 else None
            )
    
    # Get monthly archive file path (format: YYYY-MM.md)
    archive_filename = today.strftime("%Y-%m") + ".md"
    archive_file = ARCHIVE_DIR / archive_filename
    
    # Read existing archive or create new
    if archive_file.exists():
        existing_content = archive_file.read_text(encoding='utf-8')
        # Check if this date already exists in archive
        date_header = f"## {date_str}"
        if date_header in existing_content:
            # Replace existing entry for this date
            # Find the section for this date and replace it (up to next date header or end of file)
            pattern = rf"## {re.escape(date_str)}.*?(?=\n## \d{{4}}-\d{{2}}-\d{{2}}|\Z)"
            new_content = re.sub(pattern, day_markdown.rstrip(), existing_content, flags=re.DOTALL)
            archive_file.write_text(new_content, encoding='utf-8')
            log_message(f"  Updated existing entry in {archive_file}")
        else:
            # Append to end of file
            archive_file.write_text(existing_content.rstrip() + "\n\n" + day_markdown, encoding='utf-8')
            log_message(f"  Appended to {archive_file}")
    else:
        # Create new monthly archive with header
        header = f"# Calendar Archive — {today.strftime('%B %Y')}\n\n"
        archive_file.write_text(header + day_markdown, encoding='utf-8')
        log_message(f"  Created new monthly archive {archive_file}")
    
    log_message(f"  Archived {len(all_events)} events for {date_str}")
    return True

def export_weekly_calendar(accounts_data):
    """Export weekly calendar view: last week + today + upcoming week"""
    now = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today = now
    
    # Last week: 7 days ago to yesterday
    last_week_start = today - timedelta(days=7)
    last_week_end = today - timedelta(days=1)
    
    # Upcoming week: tomorrow to 7 days from tomorrow
    tomorrow = today + timedelta(days=1)
    upcoming_week_end = tomorrow + timedelta(days=6)
    
    log_message(f"Exporting weekly calendar (last week: {last_week_start.strftime('%Y-%m-%d')} to {last_week_end.strftime('%Y-%m-%d')}, today: {today.strftime('%Y-%m-%d')}, upcoming: {tomorrow.strftime('%Y-%m-%d')} to {upcoming_week_end.strftime('%Y-%m-%d')})...")
    
    # Collect events from all accounts (deduplicated by event ID, preferring calendar owner)
    events_by_id = {}  # event_id -> event dict
    
    for account, service in accounts_data:
        if not account.enabled:
            continue
        
        calendars = get_calendar_list(service)
        calendar_names = {cal['id']: cal['summary'] for cal in calendars}
        
        # Use configured calendar IDs or all accessible calendars
        if account.calendar_ids:
            calendar_ids = account.calendar_ids
        else:
            calendar_ids = [cal['id'] for cal in calendars]
            # Always include the account's own calendar ID (primary calendar)
            if account.email not in calendar_ids:
                calendar_ids.append(account.email)
                if account.email not in calendar_names:
                    calendar_names[account.email] = account.email
        
        for cal_id in calendar_ids:
            calendar_name = calendar_names.get(cal_id, cal_id)
            
            # Get events for last week
            last_week_events = get_upcoming_events(service, cal_id, last_week_start, last_week_end)
            # Get events for today
            today_events = get_upcoming_events(service, cal_id, today, today)
            # Get events for upcoming week
            upcoming_events = get_upcoming_events(service, cal_id, tomorrow, upcoming_week_end)
            
            # Combine all date ranges
            all_range_events = last_week_events + today_events + upcoming_events
            
            for event in all_range_events:
                event_id = event.get('id')
                
                # Check if this account "owns" the calendar (calendar ID matches account email)
                is_calendar_owner = (cal_id.lower() == account.email.lower())
                
                if event_id:
                    # If we've seen this event before, only replace it if this account owns the calendar
                    if event_id in events_by_id:
                        if is_calendar_owner:
                            # Replace with the owner's version
                            event['_calendar_name'] = calendar_name
                            event['_account_email'] = account.email
                            events_by_id[event_id] = event
                        # Otherwise, keep the existing one
                    else:
                        # New event, add it
                        event['_calendar_name'] = calendar_name
                        event['_account_email'] = account.email
                        events_by_id[event_id] = event
                else:
                    # Event without ID (shouldn't happen, but handle it)
                    event['_calendar_name'] = calendar_name
                    event['_account_email'] = account.email
                    # Use a temporary key for events without IDs
                    events_by_id[f"no_id_{len(events_by_id)}"] = event
    
    # Convert to list
    all_events = list(events_by_id.values())
    
    # Group events by date
    events_by_date = {}
    for event in all_events:
        start = event.get('start', {})
        if 'date' in start:
            # All-day event
            date_key = start['date']
        else:
            # Timed event
            start_dt = datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
            date_key = start_dt.strftime("%Y-%m-%d")
        
        if date_key not in events_by_date:
            events_by_date[date_key] = []
        events_by_date[date_key].append(event)
    
    # Sort events within each date
    for date_key in events_by_date:
        events_by_date[date_key].sort(key=lambda e: e.get('start', {}).get('dateTime', e.get('start', {}).get('date', '')))
    
    # Generate markdown
    markdown = "# Weekly Calendar View\n\n"
    markdown += f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n"
    
    # Last Week Section
    markdown += "## Last Week\n\n"
    last_week_count = 0
    for i in range(7):
        check_date = last_week_start + timedelta(days=i)
        date_key = check_date.strftime("%Y-%m-%d")
        date_display = check_date.strftime("%A, %B %d, %Y")
        
        markdown += f"### {date_key} ({date_display})\n\n"
        
        if date_key in events_by_date and events_by_date[date_key]:
            for event in events_by_date[date_key]:
                time_str, _, _ = format_event_time(event)
                title = event.get('summary', 'No Title')
                location = event.get('location')
                account_email = event.get('_account_email')
                
                # Check if event is shared
                organizer = event.get('organizer', {})
                organizer_email = organizer.get('email', '').lower() if organizer else ''
                is_shared_event = account_email and organizer_email and organizer_email != account_email.lower()
                
                markdown += f"- **{time_str}**: {title}"
                if is_shared_event:
                    organizer_name = organizer.get('displayName', organizer_email.split('@')[0])
                    markdown += f" *(shared — {organizer_name})*"
                if location:
                    markdown += f" ({location})"
                if account_email and len(accounts_data) > 1:
                    markdown += f" [{account_email}]"
                markdown += "\n"
                last_week_count += 1
        else:
            markdown += "- No events scheduled\n"
        
        markdown += "\n"
    
    # Today Section
    markdown += "## Today\n\n"
    today_count = 0
    today_key = today.strftime("%Y-%m-%d")
    today_display = today.strftime("%A, %B %d, %Y")
    
    markdown += f"### {today_key} ({today_display})\n\n"
    
    if today_key in events_by_date and events_by_date[today_key]:
        for event in events_by_date[today_key]:
            time_str, _, _ = format_event_time(event)
            title = event.get('summary', 'No Title')
            location = event.get('location')
            account_email = event.get('_account_email')
            
            # Check if event is shared
            organizer = event.get('organizer', {})
            organizer_email = organizer.get('email', '').lower() if organizer else ''
            is_shared_event = account_email and organizer_email and organizer_email != account_email.lower()
            
            markdown += f"- **{time_str}**: {title}"
            if is_shared_event:
                organizer_name = organizer.get('displayName', organizer_email.split('@')[0])
                markdown += f" *(shared — {organizer_name})*"
            if location:
                markdown += f" ({location})"
            if account_email and len(accounts_data) > 1:
                markdown += f" [{account_email}]"
            markdown += "\n"
            today_count += 1
    else:
        markdown += "- No events scheduled\n"
    
    markdown += "\n"
    
    # Upcoming Week Section
    markdown += "## Upcoming Week\n\n"
    upcoming_count = 0
    for i in range(7):
        check_date = tomorrow + timedelta(days=i)
        date_key = check_date.strftime("%Y-%m-%d")
        date_display = check_date.strftime("%A, %B %d, %Y")
        
        markdown += f"### {date_key} ({date_display})\n\n"
        
        if date_key in events_by_date and events_by_date[date_key]:
            for event in events_by_date[date_key]:
                time_str, _, _ = format_event_time(event)
                title = event.get('summary', 'No Title')
                location = event.get('location')
                account_email = event.get('_account_email')
                
                # Check if event is shared
                organizer = event.get('organizer', {})
                organizer_email = organizer.get('email', '').lower() if organizer else ''
                is_shared_event = account_email and organizer_email and organizer_email != account_email.lower()
                
                markdown += f"- **{time_str}**: {title}"
                if is_shared_event:
                    organizer_name = organizer.get('displayName', organizer_email.split('@')[0])
                    markdown += f" *(shared — {organizer_name})*"
                if location:
                    markdown += f" ({location})"
                if account_email and len(accounts_data) > 1:
                    markdown += f" [{account_email}]"
                markdown += "\n"
                upcoming_count += 1
        else:
            markdown += "- No events scheduled\n"
        
        markdown += "\n"
    
    # Write to file
    output_file = CALENDAR_DIR / "weekly_calendar.md"
    output_file.write_text(markdown, encoding='utf-8')
    
    total_events = last_week_count + today_count + upcoming_count
    log_message(f"Exported {total_events} events ({last_week_count} last week, {today_count} today, {upcoming_count} upcoming) to {output_file}")
    return True

def main():
    """Main export function"""
    log_message(f"Starting Google Calendar export at {datetime.now()}")
    log_message(f"Export destination: {CALENDAR_DIR}")
    log_message(f"Archive destination: {ARCHIVE_DIR}\n")
    
    try:
        # Load accounts from config
        accounts = load_accounts()
        if not accounts:
            log_message("No accounts configured. Please set up config.json", error=True)
            return 1
        
        enabled_accounts = [acc for acc in accounts if acc.enabled]
        if not enabled_accounts:
            log_message("No enabled accounts found in config.json", error=True)
            return 1
        
        log_message(f"Found {len(enabled_accounts)} enabled account(s)\n")
        
        # Authenticate and get services for all accounts
        accounts_data = []
        for account in enabled_accounts:
            log_message(f"Authenticating {account.email}...")
            creds = account.get_credentials()
            if not creds:
                log_message(f"Failed to get credentials for {account.email}. Skipping.", error=True)
                continue
            
            service = build('calendar', 'v3', credentials=creds)
            accounts_data.append((account, service))
            log_message(f"✓ Authenticated {account.email}\n")
        
        if not accounts_data:
            log_message("No accounts successfully authenticated.", error=True)
            return 1
        
        # 1. Archive today's events to monthly archive (captures any changes during the day)
        archive_success = archive_today_to_monthly(accounts_data)
        
        # 2. Export weekly calendar (last week + upcoming week)
        weekly_success = export_weekly_calendar(accounts_data)
        
        if archive_success and weekly_success:
            log_message("\n✓ Calendar export completed successfully!")
            return 0
        else:
            log_message("\n⚠ WARNING: Some exports may have failed. Check errors above.", error=True)
            return 1
            
    except HttpError as error:
        log_message(f"Google Calendar API error: {error}", error=True)
        return 1
    except Exception as e:
        log_message(f"Error during export: {e}", error=True)
        import traceback
        log_message(traceback.format_exc(), error=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())
