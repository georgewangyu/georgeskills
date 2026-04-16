#!/usr/bin/env python3
"""
Automated Cursor chat export script.
Exports Cursor AI chat conversations to markdown format with dates included in filenames.
"""

import sqlite3
import os
import sys
import re
import json
import signal
from pathlib import Path
from datetime import datetime
from html import unescape

from repo_paths import resolve_private_repo_root

PRIVATE_REPO_ROOT = resolve_private_repo_root()
AI_CHATS_DIR = PRIVATE_REPO_ROOT / "captures" / "ai-chats"

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
    return filename or "Untitled Chat"

def format_date_for_filename(date_str_or_timestamp):
    """Format date string or timestamp for use in filename (YYYY-MM-DD)"""
    try:
        # If it's already a string in ISO format or similar
        if isinstance(date_str_or_timestamp, str):
            # Try parsing various date formats
            for fmt in ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%S.%f']:
                try:
                    dt = datetime.strptime(date_str_or_timestamp.split('.')[0], fmt)
                    return dt.strftime("%Y-%m-%d")
                except:
                    continue
            # If all parsing fails, use current date
            return datetime.now().strftime("%Y-%m-%d")
        # If it's a timestamp (int or float)
        elif isinstance(date_str_or_timestamp, (int, float)):
            # Handle both seconds and milliseconds
            if date_str_or_timestamp > 1e10:
                # Likely milliseconds
                dt = datetime.fromtimestamp(date_str_or_timestamp / 1000)
            else:
                # Likely seconds
                dt = datetime.fromtimestamp(date_str_or_timestamp)
            return dt.strftime("%Y-%m-%d")
    except:
        pass
    # Fallback to current date
    return datetime.now().strftime("%Y-%m-%d")

def find_cursor_database():
    """Find the Cursor chat database file"""
    # Primary location: state.vscdb in globalStorage
    primary_db = Path.home() / "Library/Application Support/Cursor/User/globalStorage/state.vscdb"
    if primary_db.exists():
        return primary_db

    # Also check workspaceStorage for workspace-specific chats
    workspace_storage = Path.home() / "Library/Application Support/Cursor/User/workspaceStorage"
    if workspace_storage.exists():
        for workspace_dir in workspace_storage.iterdir():
            if workspace_dir.is_dir():
                retrieval_dir = workspace_dir / "anysphere.cursor-retrieval"
                if retrieval_dir.exists():
                    # Look for database files in checkpoints or other subdirectories
                    for db_file in retrieval_dir.rglob("*.db"):
                        if db_file.stat().st_size > 0:  # Skip empty files
                            return db_file
                    # Also check for .vscdb files
                    for db_file in retrieval_dir.rglob("*.vscdb"):
                        if db_file.stat().st_size > 0:
                            return db_file

    return None

def get_chats_from_database(db_path):
    """Extract chat conversations from Cursor database"""
    chats = []

    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Try to find the chats table - Cursor's schema may vary
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        print(f"Found {len(tables)} tables in database")
        if len(tables) <= 20:
            print(f"Tables: {', '.join(tables)}")
        else:
            print(f"First 20 tables: {', '.join(tables[:20])}...")

        # Common table names to try (VS Code/Cursor often uses ItemTable)
        possible_table_names = [
            "ItemTable", "chats", "conversations", "messages", "chat_history",
            "entries", "data", "keyvalue", "keyValue"
        ]

        chat_table = None
        for table_name in possible_table_names:
            if table_name in tables:
                chat_table = table_name
                break

        if not chat_table:
            # Try to find any table with chat-related columns
            print("Searching for table with chat-related columns...")
            for table in tables:
                try:
                    cursor.execute(f"PRAGMA table_info({table})")
                    columns = [row[1].lower() for row in cursor.fetchall()]
                    if any(col in ['message', 'content', 'text', 'prompt', 'response', 'value', 'data'] for col in columns):
                        chat_table = table
                        print(f"Found potential chat table: {table}")
                        break
                except:
                    continue

        if not chat_table:
            print("\nCould not find chat table in database.")
            print("\nCursor may store chats in a different format.")
            print("You may need to use Cursor's built-in export feature:")
            print("1. Open a chat in Cursor")
            print("2. Click the menu/context button")
            print("3. Select 'Export Chat'")
            print("4. Save to ai-chats/ directory manually")
            conn.close()
            return []

        print(f"Using table: {chat_table}")

        # Get column names
        cursor.execute(f"PRAGMA table_info({chat_table})")
        columns_info = cursor.fetchall()
        columns = {row[1]: row[0] for row in columns_info}
        column_names = [row[1] for row in columns_info]

        print(f"Columns: {', '.join(column_names)}")

        # Try to extract chats - adapt based on actual schema
        try:
            # VS Code/Cursor often stores data as key-value pairs in ItemTable
            if chat_table == "ItemTable":
                # Look for entries with chat-related keys, but exclude UI state entries
                # Exclude workbench panel state and other UI metadata
                cursor.execute("""
                    SELECT key, value FROM ItemTable
                    WHERE (key LIKE '%chat%' OR key LIKE '%conversation%' OR key LIKE '%message%')
                    AND key NOT LIKE 'workbench.panel%'
                    AND key NOT LIKE 'workbench.view%'
                    AND key NOT LIKE 'workbench.state%'
                """)
                rows = cursor.fetchall()

                print(f"Found {len(rows)} potential chat entries (after filtering UI state)")

                for row in rows:
                    key = row['key']
                    value = row['value']

                    # Skip if it's clearly UI state
                    if 'workbench' in key.lower() or 'panel' in key.lower() or 'view' in key.lower():
                        continue

                    try:
                        # Try to parse JSON value
                        if isinstance(value, str):
                            parsed_value = json.loads(value)
                        else:
                            parsed_value = value

                        # Check if this looks like actual conversation data
                        # Conversations typically have messages, content, or are arrays/objects with message-like structure
                        is_conversation = False

                        if isinstance(parsed_value, dict):
                            # Look for conversation-like keys
                            if any(k in parsed_value for k in ['messages', 'conversation', 'messages', 'content', 'text', 'prompt', 'response']):
                                is_conversation = True
                            # Or if it's a large object that might contain conversation data
                            elif len(str(parsed_value)) > 100:
                                is_conversation = True
                        elif isinstance(parsed_value, list):
                            # If it's a list, check if items look like messages
                            if len(parsed_value) > 0:
                                first_item = parsed_value[0] if parsed_value else {}
                                if isinstance(first_item, dict) and any(k in first_item for k in ['message', 'content', 'text', 'role', 'user', 'assistant']):
                                    is_conversation = True
                                elif len(parsed_value) > 1:  # Multiple items might be messages
                                    is_conversation = True
                        elif isinstance(parsed_value, str) and len(parsed_value) > 50:
                            # Long strings might be conversation content
                            is_conversation = True

                        # Only add if it looks like actual conversation data
                        if is_conversation:
                            chats.append({
                                'key': key,
                                'value': parsed_value,
                                'raw_value': value
                            })
                        else:
                            print(f"  Skipping {key[:60]}... (doesn't look like conversation data)")

                    except json.JSONDecodeError:
                        # If it's not JSON, check if it's a long string that might be conversation content
                        if isinstance(value, str) and len(value) > 100:
                            chats.append({
                                'key': key,
                                'value': value,
                                'raw_value': value
                            })
                    except Exception as e:
                        print(f"  Error processing {key[:60]}...: {e}")
                        continue
            else:
                # For other table structures, get all rows
                query = f"SELECT * FROM {chat_table}"

                # Try to order by date if available
                date_columns = [col for col in column_names if 'date' in col.lower() or 'time' in col.lower() or 'created' in col.lower()]
                if date_columns:
                    query += f" ORDER BY {date_columns[0]} ASC"

                cursor.execute(query)
                rows = cursor.fetchall()

                for row in rows:
                    row_dict = dict(row)
                    chats.append(row_dict)

        except Exception as e:
            print(f"Error reading from table: {e}")
            import traceback
            traceback.print_exc()

        conn.close()

    except Exception as e:
        print(f"Error accessing database: {e}")
        import traceback
        traceback.print_exc()
        return []

    return chats

def format_chat_as_markdown(chat_data):
    """Convert chat data to markdown format"""
    # Try to extract title
    title = "Untitled Chat"
    key_name = chat_data.get('key', '')

    # Try to get title from various sources
    if 'value' in chat_data and isinstance(chat_data['value'], dict):
        value_dict = chat_data['value']
        for key in ['title', 'name', 'subject', 'id', 'conversationId', 'chatId']:
            if key in value_dict and value_dict[key]:
                title = str(value_dict[key])
                break
        # If no title found, try to use first message as title
        if title == "Untitled Chat" and 'messages' in value_dict:
            messages = value_dict['messages']
            if isinstance(messages, list) and len(messages) > 0:
                first_msg = messages[0]
                if isinstance(first_msg, dict):
                    msg_text = first_msg.get('content', first_msg.get('text', first_msg.get('message', '')))
                    if msg_text:
                        title = sanitize_filename(msg_text[:50])

    # If still no title, try to extract from key name
    if title == "Untitled Chat" and key_name:
        # Try to extract meaningful part from key
        parts = key_name.split('.')
        if len(parts) > 1:
            title = parts[-1]
        else:
            title = key_name[:50]

    # Try to extract creation date
    create_date = None
    if 'value' in chat_data and isinstance(chat_data['value'], dict):
        value_dict = chat_data['value']
        for key in ['createdAt', 'created_at', 'timestamp', 'date', 'time', 'created', 'updatedAt']:
            if key in value_dict and value_dict[key]:
                create_date = value_dict[key]
                break

    # Extract and format messages
    content = ""
    value = chat_data.get('value', chat_data)

    # If value is a dict, look for messages
    if isinstance(value, dict):
        # Look for messages array
        if 'messages' in value:
            messages = value['messages']
            if isinstance(messages, list):
                content = format_messages_as_markdown(messages)
            else:
                content = format_messages_as_markdown([messages])
        # Look for conversation array
        elif 'conversation' in value:
            conv = value['conversation']
            if isinstance(conv, list):
                content = format_messages_as_markdown(conv)
            else:
                content = format_messages_as_markdown([conv])
        # Look for single message
        elif 'message' in value or 'content' in value or 'text' in value:
            msg_text = value.get('message') or value.get('content') or value.get('text', '')
            role = value.get('role', value.get('sender', 'user'))
            content = f"## {role.capitalize()}\n\n{msg_text}\n"
        # Otherwise, format the whole dict
        else:
            content = format_dict_as_markdown(value)
    # If value is a list, treat as messages
    elif isinstance(value, list):
        content = format_messages_as_markdown(value)
    # If value is a string, use it directly
    elif isinstance(value, str):
        content = value
    # Otherwise, format as JSON
    else:
        content = json.dumps(chat_data, indent=2, default=str)

    # Format markdown
    markdown = f"""# {title}

**Created**: {create_date if create_date else 'Unknown'}
**Exported**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Key**: `{key_name}`

---

{content}
"""
    return title, create_date, markdown

def format_messages_as_markdown(messages):
    """Format a list of messages as markdown"""
    if not messages:
        return "No messages found."

    content_parts = []
    for i, msg in enumerate(messages, 1):
        if isinstance(msg, dict):
            role = msg.get('role', msg.get('sender', msg.get('type', 'user')))
            msg_content = msg.get('content', msg.get('text', msg.get('message', '')))

            # Handle HTML entities
            if isinstance(msg_content, str):
                msg_content = unescape(msg_content)

            # Format role header
            role_display = role.capitalize() if role else 'User'
            if role_display.lower() == 'assistant':
                role_display = '🤖 Assistant'
            elif role_display.lower() == 'user':
                role_display = '👤 User'

            content_parts.append(f"## {role_display}\n\n{msg_content}\n")
        elif isinstance(msg, str):
            content_parts.append(f"## Message {i}\n\n{msg}\n")
        else:
            content_parts.append(f"## Message {i}\n\n```json\n{json.dumps(msg, indent=2, default=str)}\n```\n")

    return "\n---\n\n".join(content_parts)

def format_dict_as_markdown(data):
    """Format a dictionary as markdown, trying to extract meaningful content"""
    # If it's a simple key-value structure, format nicely
    if len(data) <= 10:
        parts = []
        for key, val in data.items():
            if isinstance(val, (dict, list)):
                parts.append(f"### {key}\n\n```json\n{json.dumps(val, indent=2, default=str)}\n```\n")
            else:
                parts.append(f"**{key}**: {val}\n")
        return "\n".join(parts)
    else:
        # Large dict, just format as JSON
        return f"```json\n{json.dumps(data, indent=2, default=str)}\n```"

def export_chats_to_markdown():
    """Export Cursor chats to markdown format"""
    global interrupt_requested

    # Create destination directory
    AI_CHATS_DIR.mkdir(parents=True, exist_ok=True)

    # Find database
    print("Looking for Cursor chat database...")
    db_path = find_cursor_database()

    if not db_path:
        print("ERROR: Could not find Cursor chat database.")
        print("\nPlease check:")
        print("1. Cursor is installed and has been used")
        print("2. Chat history exists in Cursor")
        print("\nYou may need to manually specify the database path.")
        return False

    print(f"Found database: {db_path}")

    # Get chats from database
    print("Reading chats from database...")
    chats = get_chats_from_database(db_path)

    if not chats:
        print("No chats found in database.")
        print("\nThis could mean:")
        print("1. No chat history exists yet")
        print("2. The database schema is different than expected")
        print("3. Chats are stored in a different location")
        return False

    print(f"Found {len(chats)} chat entries")

    # Export each chat
    exported_count = 0
    error_count = 0

    for i, chat_data in enumerate(chats, 1):
        if interrupt_requested:
            print("\n\nExport stopped by user.")
            return True

        try:
            title, create_date, markdown = format_chat_as_markdown(chat_data)

            # Format date for filename
            date_str = format_date_for_filename(create_date)

            # Sanitize title for filename
            safe_title = sanitize_filename(title)

            # Create filename
            filename = f"{date_str}_{safe_title}.md"
            file_path = AI_CHATS_DIR / filename

            # Handle duplicates
            counter = 1
            original_path = file_path
            while file_path.exists():
                filename = f"{date_str}_{safe_title}_{counter}.md"
                file_path = AI_CHATS_DIR / filename
                counter += 1

            # Write markdown file
            file_path.write_text(markdown, encoding='utf-8')
            exported_count += 1

            print(f"[{i}/{len(chats)}] Exported: {title[:50]}...")

        except Exception as e:
            error_count += 1
            print(f"[{i}/{len(chats)}] Error: {str(e)[:50]}...")

    print(f"\n\nExport summary:")
    print(f"  - Chats exported: {exported_count}")
    print(f"  - Errors: {error_count}")

    return True

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    global interrupt_requested
    interrupt_requested = True
    print("\n\nInterrupt requested (Ctrl+C). Finishing current chat, then stopping...")

def main():
    """Main entry point"""
    signal.signal(signal.SIGINT, signal_handler)

    print("Cursor Chat Export Script")
    print("=" * 50)

    success = export_chats_to_markdown()

    if success:
        print("\nExport completed successfully!")
        sys.exit(0)
    else:
        print("\nExport failed. See errors above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
