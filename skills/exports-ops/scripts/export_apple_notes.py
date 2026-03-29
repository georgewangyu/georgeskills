#!/usr/bin/env python3
"""
Automated Apple Notes export script.
Exports Apple Notes directly to markdown format with dates included in filenames.
"""

import subprocess
import os
import sys
import re
import signal
import base64
from pathlib import Path
from datetime import datetime, timedelta
from html import unescape

from repo_paths import resolve_private_repo_root

PRIVATE_REPO_ROOT = resolve_private_repo_root()
APPLE_NOTES_DIR = PRIVATE_REPO_ROOT / "notes-private" / "apple-notes"
ALL_NOTES_DIR = APPLE_NOTES_DIR / "all-notes"

# Global flag for interrupt handling
interrupt_requested = False

def sanitize_filename(filename):
    """Remove invalid characters from filename"""
    # Remove invalid filename characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove leading/trailing spaces and dots
    filename = filename.strip(' .')
    # Limit length
    if len(filename) > 200:
        filename = filename[:200]
    return filename or "Untitled Note"

def html_to_markdown(html_content, images_dir=None, note_index=None):
    """
    Convert HTML from Apple Notes to clean markdown.
    Handles common HTML tags and converts them to markdown formatting.
    Also extracts and preserves images.
    """
    if not html_content:
        return ""
    
    # First, unescape HTML entities
    text = unescape(html_content)
    
    # Counter for image filenames
    image_counter = [0]  # Use list to allow modification in nested function
    
    # Convert images: <img src="..."> → ![alt](path)
    # For Apple Notes, images are often embedded as data URIs or attachments
    def replace_image(match):
        img_tag = match.group(0)
        src_match = re.search(r'src=["\']([^"\']+)["\']', img_tag, re.IGNORECASE)
        alt_match = re.search(r'alt=["\']([^"\']*)["\']', img_tag, re.IGNORECASE)
        
        if src_match:
            src = src_match.group(1)
            alt = alt_match.group(1) if alt_match else "Image"
            
            # If it's a data URI, we'll need to extract and save it
            if src.startswith('data:image'):
                # Data URI - extract and save
                if images_dir and note_index:
                    # Extract base64 data
                    data_match = re.search(r'data:image/(\w+);base64,(.+)', src)
                    if data_match:
                        img_format = data_match.group(1)
                        img_data = data_match.group(2)
                        try:
                            image_bytes = base64.b64decode(img_data)
                            image_counter[0] += 1
                            img_filename = f"image_{note_index}_{image_counter[0]}.{img_format}"
                            img_path = images_dir / img_filename
                            img_path.write_bytes(image_bytes)
                            return f"![{alt}](images/{img_filename})"
                        except Exception as e:
                            print(f"Warning: Could not extract image: {e}", file=sys.stderr)
                            return f"![{alt}](embedded image)"
                return f"![{alt}](embedded image)"
            else:
                # Regular URL or file path
                return f"![{alt}]({src})"
        return "[Image]"
    
    text = re.sub(r'<img[^>]+>', replace_image, text, flags=re.IGNORECASE)
    
    # Convert common HTML formatting to markdown
    # Bold: <strong> or <b> → **text**
    text = re.sub(r'<strong>(.*?)</strong>', r'**\1**', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<b>(.*?)</b>', r'**\1**', text, flags=re.DOTALL | re.IGNORECASE)
    
    # Italic: <em> or <i> → *text*
    text = re.sub(r'<em>(.*?)</em>', r'*\1*', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<i>(.*?)</i>', r'*\1*', text, flags=re.DOTALL | re.IGNORECASE)
    
    # Underline: <u> → (markdown doesn't have underline, so we'll just remove tags)
    text = re.sub(r'<u>(.*?)</u>', r'\1', text, flags=re.DOTALL | re.IGNORECASE)
    
    # Line breaks: <div>, <p>, <br> → newlines
    text = re.sub(r'</div>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<div[^>]*>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'</p>', '\n\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<p[^>]*>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    
    # Lists: <ul>, <ol>, <li>
    text = re.sub(r'</li>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<li[^>]*>', '- ', text, flags=re.IGNORECASE)
    text = re.sub(r'</ul>|</ol>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<ul[^>]*>|<ol[^>]*>', '', text, flags=re.IGNORECASE)
    
    # Links: <a href="url">text</a> → [text](url)
    text = re.sub(r'<a\s+href=["\']([^"\']*)["\'][^>]*>(.*?)</a>', r'[\2](\1)', text, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove any remaining HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Clean up extra whitespace and newlines
    text = re.sub(r'\n{3,}', '\n\n', text)  # Max 2 consecutive newlines
    text = text.strip()
    
    return text

def format_date_for_filename(date_str):
    """Format date string for use in filename (YYYY-MM-DD)"""
    try:
        # Parse various date formats that AppleScript might return
        # AppleScript dates are typically in format like "Monday, November 10, 2025 at 2:00:00 PM"
        # We'll extract just the date part
        date_match = re.search(r'(\w+day),\s+(\w+)\s+(\d+),\s+(\d+)', date_str)
        if date_match:
            month_name = date_match.group(2)
            day = date_match.group(3)
            year = date_match.group(4)
            
            month_map = {
                'January': '01', 'February': '02', 'March': '03',
                'April': '04', 'May': '05', 'June': '06',
                'July': '07', 'August': '08', 'September': '09',
                'October': '10', 'November': '11', 'December': '12'
            }
            month = month_map.get(month_name, '01')
            return f"{year}-{month}-{day.zfill(2)}"
    except:
        pass
    
    # Fallback to today's date
    return datetime.now().strftime("%Y-%m-%d")

def build_existing_notes_map():
    """
    Build a map of existing notes by title+creation_date for fast lookup.
    Uses both title and creation date to uniquely identify notes (since titles can be duplicated).
    Only checks all-notes/ folder to avoid skipping notes that exist elsewhere.
    Returns dict: {(note_title, creation_date): (file_path, mod_date)}
    """
    existing_notes = {}
    print("Scanning existing notes in all-notes/...", end='\r')
    
    # Only check all-notes/ folder, not the entire apple-notes directory
    if not ALL_NOTES_DIR.exists():
        return existing_notes
    
    for md_file in ALL_NOTES_DIR.glob("*.md"):
        try:
            content = md_file.read_text(encoding='utf-8', errors='ignore')
            # Extract title from first line
            if content.startswith("# "):
                first_line = content.split('\n')[0]
                note_title = first_line[2:].strip()  # Remove "# " prefix
                
                # Extract creation date and modification date
                create_date_match = re.search(r'\*\*Created\*\*:\s*(.+)', content)
                create_date = create_date_match.group(1).strip() if create_date_match else None
                
                mod_date_match = re.search(r'\*\*Modified\*\*:\s*(.+)', content)
                mod_date = mod_date_match.group(1).strip() if mod_date_match else None
                
                # Use (title, creation_date) as key to handle duplicate titles
                key = (note_title, create_date) if create_date else (note_title, None)
                existing_notes[key] = (md_file, mod_date)
        except:
            continue
    
    return existing_notes

def find_existing_note(note_title, note_mod_date, note_create_date, existing_notes_map):
    """
    Fast lookup for existing note using pre-built map.
    Uses both title and creation date to uniquely identify notes.
    Returns (file_path, needs_update) tuple.
    """
    # Try to match by (title, creation_date) first - this is the primary matching method
    key = (note_title, note_create_date) if note_create_date else (note_title, None)
    
    if key in existing_notes_map:
        file_path, existing_mod_date = existing_notes_map[key]
        # If modification dates match, note hasn't changed
        if existing_mod_date and existing_mod_date == note_mod_date:
            return (file_path, False)
        # If different or no date, note was updated
        else:
            return (file_path, True)
    
    # Fallback: if exact match not found, try matching by title only
    # This handles cases where creation date might be missing or formatted differently in old exports
    # But we only match if the modification date is different (indicating it's an update to an existing note)
    # If mod dates match, it's likely a different note with the same title, so don't match
    for (map_title, map_create_date), (file_path, existing_mod_date) in existing_notes_map.items():
        if map_title == note_title:
            # Only match if modification dates are different (same note, updated)
            # If mod dates match, it's likely a different note with same title, so skip
            if existing_mod_date and existing_mod_date != note_mod_date:
                return (file_path, True)
            # If no existing mod date, assume it's the same note
            elif not existing_mod_date:
                return (file_path, True)
    
    # No match found - this is a new note
    return (None, True)

def get_last_export_time():
    """Get the timestamp of the last export (from a marker file)"""
    marker_file = ALL_NOTES_DIR / ".last_export"
    if marker_file.exists():
        try:
            timestamp = marker_file.read_text().strip()
            return datetime.fromisoformat(timestamp)
        except:
            pass
    return None

def save_last_export_time():
    """Save the current time as the last export timestamp"""
    marker_file = ALL_NOTES_DIR / ".last_export"
    marker_file.write_text(datetime.now().isoformat())

def get_recent_notes_since_date(since_date):
    """
    Get all notes modified since a specific date - processes one at a time to avoid memory issues.
    Returns a generator that yields note info strings.
    """
    # Format date for AppleScript (format: "Monday, November 10, 2025 at 2:00:00 PM")
    # Round down to the second (not minute) to avoid timezone/precision issues while being more precise
    since_date_rounded = since_date.replace(microsecond=0)
    date_str = since_date_rounded.strftime("%A, %B %d, %Y at %I:%M:%S %p")
    
    # First, get the total count to show progress
    total_notes = get_note_count()
    if total_notes == 0:
        return []
    
    print(f"Scanning {total_notes} notes for changes since {since_date_rounded.strftime('%Y-%m-%d %H:%M:%S')}...")
    
    # Process notes one at a time, checking modification date first
    # AppleScript returns notes with index 1 = newest, so we check newest first (most likely to be recent)
    recent_notes = []
    checked_count = 0
    
    for idx in range(1, total_notes + 1):  # Start from 1 (newest) to total_notes (oldest)
        if interrupt_requested:
            break
        
        checked_count += 1
        if checked_count % 100 == 0:
            print(f"  Checked {checked_count}/{total_notes} notes...", end='\r')
        
        # First, quickly check just the modification date
        check_date_script = f'''
        tell application "Notes"
            try
                set aNote to note {idx}
                set noteModDate to modification date of aNote
                return noteModDate as string
            on error
                return "ERROR"
            end try
        end tell
        '''
        
        try:
            result = subprocess.run(
                ['osascript', '-e', check_date_script],
                capture_output=True,
                text=True,
                check=True,
                timeout=5  # Quick check, should be fast
            )
            mod_date_str = result.stdout.strip()
            
            if mod_date_str == "ERROR":
                continue
            
            # Parse the modification date and compare
            # AppleScript date format: "Monday, November 10, 2025 at 6:35:57 PM"
            try:
                # Convert AppleScript date string to datetime
                mod_date_match = re.search(r'(\w+day),\s+(\w+)\s+(\d+),\s+(\d+)\s+at\s+(\d+):(\d+):(\d+)\s+(AM|PM)', mod_date_str)
                if mod_date_match:
                    month_name = mod_date_match.group(2)
                    day = int(mod_date_match.group(3))
                    year = int(mod_date_match.group(4))
                    hour = int(mod_date_match.group(5))
                    minute = int(mod_date_match.group(6))
                    second = int(mod_date_match.group(7))
                    am_pm = mod_date_match.group(8)
                    
                    # Convert to 24-hour format
                    if am_pm == "PM" and hour != 12:
                        hour += 12
                    elif am_pm == "AM" and hour == 12:
                        hour = 0
                    
                    month_map = {
                        'January': 1, 'February': 2, 'March': 3,
                        'April': 4, 'May': 5, 'June': 6,
                        'July': 7, 'August': 8, 'September': 9,
                        'October': 10, 'November': 11, 'December': 12
                    }
                    month = month_map.get(month_name, 1)
                    
                    note_mod_date = datetime(year, month, day, hour, minute, second)
                    
                    # If this note is older than or equal to cutoff, we can stop (notes are sorted newest to oldest)
                    # Use <= to include notes modified at the exact same second as the last export
                    if note_mod_date <= since_date_rounded:
                        # Since notes are sorted newest to oldest, all remaining notes will be older
                        print(f"\n  Reached notes older than cutoff. Stopped at note {checked_count}/{total_notes}")
                        break
                    
                    # This note is recent, fetch full details
                    note_info = get_single_note(idx)
                    if note_info and not note_info.startswith("ERROR|||"):
                        recent_notes.append(note_info)
            except Exception as e:
                # If date parsing fails, fetch the note anyway to be safe
                note_info = get_single_note(idx)
                if note_info and not note_info.startswith("ERROR|||"):
                    recent_notes.append(note_info)
        except subprocess.TimeoutExpired:
            print(f"\n  Timeout checking note {idx}, skipping...")
            continue
        except Exception as e:
            # Skip notes that can't be accessed
            continue
    
    print(f"\n  Found {len(recent_notes)} notes modified since last export.")
    return recent_notes

def get_note_count():
    """Get the total number of notes"""
    applescript = '''
    tell application "Notes"
        return count of every note
    end tell
    '''
    try:
        result = subprocess.run(
            ['osascript', '-e', applescript],
            capture_output=True,
            text=True,
            check=True,
            timeout=10
        )
        return int(result.stdout.strip())
    except:
        return 0

def get_single_note(index):
    """Get a single note by index (1-based), including images"""
    applescript = f'''
    tell application "Notes"
        try
            set aNote to note {index}
            set noteTitle to name of aNote
            set noteBody to body of aNote
            set noteModDate to modification date of aNote as string
            set noteCreateDate to creation date of aNote as string
            
            -- Get attachments (images)
            set imageList to {{}}
            try
                set attachmentsList to attachments of aNote
                repeat with anAttachment in attachmentsList
                    try
                        set attachmentName to name of anAttachment
                        set imageList to imageList & attachmentName
                    end try
                end repeat
            end try
            
            set imageInfo to my listToString(imageList, ":::IMAGE_SEP:::")
            return noteTitle & "|||" & noteBody & "|||" & noteModDate & "|||" & noteCreateDate & "|||" & imageInfo
        on error errMsg
            return "ERROR|||" & errMsg
        end try
    end tell
    
    on listToString(lst, delimiter)
        set AppleScript's text item delimiters to delimiter
        set result to lst as string
        set AppleScript's text item delimiters to ""
        return result
    end listToString
    '''
    try:
        result = subprocess.run(
            ['osascript', '-e', applescript],
            capture_output=True,
            text=True,
            check=True,
            timeout=30  # 30 seconds per note (should be plenty)
        )
        return result.stdout.strip()
    except:
        return None

def extract_images_from_note(index, note_title, output_dir):
    """Extract images from a note and save them to output_dir"""
    images_dir = output_dir / "images"
    images_dir.mkdir(exist_ok=True)
    
    applescript = f'''
    tell application "Notes"
        try
            set aNote to note {index}
            set attachmentsList to attachments of aNote
            set savedImages to {{}}
            
            repeat with anAttachment in attachmentsList
                try
                    set attachmentName to name of anAttachment
                    set attachmentData to data of anAttachment
                    
                    -- Determine file extension from name or default to png
                    if attachmentName contains "." then
                        set fileExt to text -4 thru -1 of attachmentName
                    else
                        set fileExt to ".png"
                    end if
                    
                    set savedImages to savedImages & (attachmentName & "|||FILE|||" & fileExt)
                end try
            end repeat
            
            return my listToString(savedImages, ":::IMAGE_SEP:::")
        on error errMsg
            return ""
        end try
    end tell
    
    on listToString(lst, delimiter)
        set AppleScript's text item delimiters to delimiter
        set result to lst as string
        set AppleScript's text item delimiters to ""
        return result
    end listToString
    '''
    
    try:
        result = subprocess.run(
            ['osascript', '-e', applescript],
            capture_output=True,
            text=True,
            check=True,
            timeout=60
        )
        
        image_info = result.stdout.strip()
        if not image_info:
            return []
        
        # Note: AppleScript can't directly save binary data, so we'll need to use a workaround
        # For now, we'll extract image references from the HTML body and handle them there
        return image_info.split(":::IMAGE_SEP:::") if image_info else []
    except:
        return []

def export_notes_to_markdown():
    """
    Export Apple Notes directly to markdown format using AppleScript.
    Includes date in filename and saves to all-notes/ folder.
    """
    global interrupt_requested
    
    # Create destination directory and images subdirectory
    ALL_NOTES_DIR.mkdir(parents=True, exist_ok=True)
    images_dir = ALL_NOTES_DIR / "images"
    images_dir.mkdir(exist_ok=True)
    
    try:
        # Build existing notes map once for fast lookups
        existing_notes_map = build_existing_notes_map()
        print(f"Found {len(existing_notes_map)} existing notes.")
        
        # Check if we have a last export time - if so, only fetch recent notes
        last_export = get_last_export_time()
        
        if last_export:
            # Incremental export: only fetch notes modified since last export
            print(f"Last export: {last_export.strftime('%Y-%m-%d %H:%M:%S')}")
            print("Fetching only notes modified since last export...")
            notes_data = get_recent_notes_since_date(last_export)
            if notes_data and len(notes_data) == 1 and not notes_data[0].strip():
                notes_data = []
            # If no recent notes, notes_data will be [] (empty list)
            if not notes_data:
                print("\nNo notes modified since last export. Export complete.")
                save_last_export_time()
                return True
        else:
            # First run: fetch notes one at a time
            print("First run detected. Fetching notes one at a time...")
            total_notes = get_note_count()
            if total_notes == 0:
                print("No notes found or access denied")
                return False
            print(f"Found {total_notes} notes. Processing one at a time...")
            notes_data = None  # We'll fetch one at a time
        
        exported_count = 0
        skipped_count = 0
        updated_count = 0
        error_count = 0
        
        # Process notes
        if notes_data:
            # Incremental mode: process the list of recent notes
            total_notes = len(notes_data)
            for i, note_info in enumerate(notes_data, 1):
                if interrupt_requested:
                    print("\n\nExport stopped by user. Files written so far have been saved.")
                    save_last_export_time()
                    return True
                
                exported_count, skipped_count, updated_count, error_count = _process_single_note(
                    i, total_notes, note_info, existing_notes_map, exported_count, skipped_count, updated_count, error_count, images_dir=images_dir, note_index=i
                )
        else:
            # First run: fetch and process one at a time (oldest first)
            # AppleScript returns notes with index 1 = newest, so we reverse to get oldest first
            for idx in range(total_notes, 0, -1):  # Start from total_notes down to 1
                if interrupt_requested:
                    print("\n\nExport stopped by user. Files written so far have been saved.")
                    save_last_export_time()
                    return True
                
                i = total_notes - idx + 1  # Display counter (1, 2, 3...)
                note_info = get_single_note(idx)
                
                if interrupt_requested:
                    print("\n\nExport stopped by user. Files written so far have been saved.")
                    save_last_export_time()
                    return True
                
                exported_count, skipped_count, updated_count, error_count = _process_single_note(
                    i, total_notes, note_info, existing_notes_map, exported_count, skipped_count, updated_count, error_count, images_dir=images_dir, note_index=idx
                )
        
        print(f"\n\nExport summary:")
        print(f"  - New notes exported: {exported_count}")
        print(f"  - Existing notes updated: {updated_count}")
        print(f"  - Unchanged notes skipped: {skipped_count}")
        print(f"  - Errors/skipped: {error_count}")
        print(f"  - Total processed: {exported_count + updated_count + skipped_count + error_count}")
        
        # Save export timestamp for next run
        save_last_export_time()
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"AppleScript export failed: {e.stderr}", file=sys.stderr)
        print("\nTroubleshooting:")
        print("1. Grant Terminal/Script Editor access to Notes:")
        print("   System Preferences → Security & Privacy → Privacy → Automation")
        print("2. Make sure Notes app is running or accessible")
        return False
    except Exception as e:
        print(f"Error during export: {e}", file=sys.stderr)
        return False

def _process_single_note(i, total_notes, note_info, existing_notes_map, exported_count, skipped_count, updated_count, error_count, images_dir=None, note_index=None):
    """Process a single note and return updated counts"""
    if not note_info or note_info == "|||":
        error_count += 1
        print(f"[{i}/{total_notes}] Error: Empty note")
        return exported_count, skipped_count, updated_count, error_count
        
    if note_info.startswith("ERROR|||"):
        error_count += 1
        print(f"[{i}/{total_notes}] Error: {note_info.split('|||')[1][:50]}...")
        return exported_count, skipped_count, updated_count, error_count
        
    parts = note_info.split("|||")
    if len(parts) < 4:
        error_count += 1
        print(f"[{i}/{total_notes}] Error: Invalid format")
        return exported_count, skipped_count, updated_count, error_count
    
    note_title = parts[0]
    note_body = parts[1]
    note_mod_date = parts[2]
    note_create_date = parts[3]
    
    # Fast lookup for existing note (using title + creation date for unique identification)
    existing_file, needs_update = find_existing_note(note_title, note_mod_date, note_create_date, existing_notes_map)
    
    if existing_file and not needs_update:
        # Note exists and hasn't changed, skip it
        skipped_count += 1
        print(f"[{i}/{total_notes}] Skipped: {note_title[:50]}...")
        return exported_count, skipped_count, updated_count, error_count
    
    # Format date for filename - use creation date from the note
    date_str = format_date_for_filename(note_create_date)
    
    # Sanitize title for filename
    safe_title = sanitize_filename(note_title)
    
    # Create filename with date: YYYY-MM-DD_Title.md
    filename = f"{date_str}_{safe_title}.md"
    file_path = ALL_NOTES_DIR / filename
    
    # If updating existing note, check if filename needs to be corrected
    if existing_file and needs_update:
        existing_filename = existing_file.name
        # Extract date from existing filename
        date_match = re.search(r'^(\d{4}-\d{2}-\d{2})_', existing_filename)
        existing_date_str = date_match.group(1) if date_match else None
        
        # If creation date doesn't match filename, rename the file
        if existing_date_str and existing_date_str != date_str:
            # The filename has wrong date - rename it to match actual creation date
            old_file_path = existing_file
            # Handle duplicates for renamed files
            counter = 1
            original_new_path = file_path
            while file_path.exists() and file_path != old_file_path:
                filename = f"{date_str}_{safe_title}_{counter}.md"
                file_path = ALL_NOTES_DIR / filename
                counter += 1
            # Rename the file
            old_file_path.rename(file_path)
            action = "Updated (renamed)"
        else:
            # Keep existing filename if dates match
            file_path = existing_file
            action = "Updated"
        updated_count += 1
    else:
        # Handle duplicates for new notes
        counter = 1
        original_path = file_path
        while file_path.exists():
            filename = f"{date_str}_{safe_title}_{counter}.md"
            file_path = ALL_NOTES_DIR / filename
            counter += 1
        exported_count += 1
        action = "Exported"
    
    # Convert HTML body to clean markdown (with image extraction)
    clean_body = html_to_markdown(note_body, images_dir=images_dir, note_index=note_index or i)
    
    # Create markdown content
    markdown_content = f"""# {note_title}

**Created**: {note_create_date}  
**Modified**: {note_mod_date}

---

{clean_body}
"""
    
    # Write markdown file immediately (incremental writing)
    file_path.write_text(markdown_content, encoding='utf-8')
    sys.stdout.flush()  # Ensure output is visible
    
    # Show progress (use newline so user can see files being written)
    print(f"[{i}/{total_notes}] {action}: {note_title[:50]}...")
    
    return exported_count, skipped_count, updated_count, error_count

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    global interrupt_requested
    interrupt_requested = True
    print("\n\nInterrupt requested (Ctrl+C). Finishing current note, then stopping...")
    print("(Press Ctrl+C again to force quit immediately)")

def main():
    """Main export function"""
    # Set up signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    print(f"Starting Apple Notes export at {datetime.now()}")
    print(f"Export destination: {ALL_NOTES_DIR}")
    print("Press Ctrl+C to stop (files written so far will be saved)\n")
    
    try:
        if export_notes_to_markdown():
            print("\nApple Notes export completed successfully!")
            return 0
        else:
            print("\nERROR: Failed to export Apple Notes")
            return 1
    except KeyboardInterrupt:
        print("\n\nExport interrupted by user (Ctrl+C)")
        print("Files written so far have been saved.")
        return 0

if __name__ == "__main__":
    sys.exit(main())
