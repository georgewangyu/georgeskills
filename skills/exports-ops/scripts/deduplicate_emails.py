#!/usr/bin/env python3
"""
Deduplicate email files by checking message IDs from YAML frontmatter.
For files without frontmatter, uses filename and content comparison.
"""

import os
import sys
import re
import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime

from repo_paths import resolve_private_repo_root

PRIVATE_REPO_ROOT = resolve_private_repo_root()
EMAIL_DIR = PRIVATE_REPO_ROOT / "notes-private" / "email"

def extract_yaml_frontmatter(file_path):
    """Extract YAML frontmatter from a markdown file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Check if file starts with YAML frontmatter
        if not content.startswith('---\n'):
            return None
            
        # Find the end of frontmatter
        end_idx = content.find('\n---\n', 4)
        if end_idx == -1:
            return None
            
        frontmatter_text = content[4:end_idx]
        
        # Parse simple YAML (message_id, email_type, exported_at)
        frontmatter = {}
        for line in frontmatter_text.split('\n'):
            line = line.strip()
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                frontmatter[key] = value
        
        return frontmatter if frontmatter else None
    except Exception as e:
        print(f"  Warning: Could not read {file_path}: {e}", file=sys.stderr)
        return None

def get_message_id_from_file(file_path):
    """Get message ID from file (either from frontmatter or None)."""
    frontmatter = extract_yaml_frontmatter(file_path)
    if frontmatter:
        return frontmatter.get('message_id')
    return None

def parse_filename_for_counter(filename):
    """Extract counter from filename like 'subject_4.md' -> 4, or None."""
    match = re.search(r'_(\d+)\.md$', filename)
    if match:
        return int(match.group(1))
    return None

def find_email_files():
    """Find all email markdown files."""
    email_files = []
    for account_dir in EMAIL_DIR.iterdir():
        if not account_dir.is_dir() or account_dir.name.startswith('.'):
            continue
        
        for email_file in account_dir.rglob('*.md'):
            email_files.append(email_file)
    
    return email_files

def group_by_message_id(email_files):
    """Group files by message ID."""
    by_message_id = defaultdict(list)
    no_message_id = []
    
    for file_path in email_files:
        message_id = get_message_id_from_file(file_path)
        if message_id:
            by_message_id[message_id].append(file_path)
        else:
            no_message_id.append(file_path)
    
    return by_message_id, no_message_id

def find_duplicates_with_message_id(by_message_id):
    """Find duplicate files that have the same message ID."""
    duplicates_to_remove = []
    files_to_keep = []
    
    for message_id, files in by_message_id.items():
        if len(files) > 1:
            # Sort files: prefer files without counter suffix, then by counter (higher = newer)
            def sort_key(f):
                counter = parse_filename_for_counter(f.name)
                # Files without counter come first (counter is None)
                if counter is None:
                    return (0, 0)
                # Files with counter: higher number = newer
                return (1, -counter)
            
            sorted_files = sorted(files, key=sort_key)
            
            # Keep the first one (best version)
            keep_file = sorted_files[0]
            files_to_keep.append(keep_file)
            
            # Mark others for removal
            for dup_file in sorted_files[1:]:
                duplicates_to_remove.append(dup_file)
        else:
            # No duplicates for this message ID
            files_to_keep.append(files[0])
    
    return duplicates_to_remove, files_to_keep

def find_duplicates_by_filename(no_message_id_files):
    """Find duplicates by comparing filenames (for files without message ID)."""
    # Group by base filename (without counter)
    by_base_name = defaultdict(list)
    
    for file_path in no_message_id_files:
        base_name = re.sub(r'_\d+\.md$', '.md', file_path.name)
        by_base_name[base_name].append(file_path)
    
    duplicates_to_remove = []
    files_to_keep = []
    
    for base_name, files in by_base_name.items():
        if len(files) > 1:
            # Check if files have same size (likely duplicates)
            file_sizes = {f: f.stat().st_size for f in files}
            
            # Group by size
            by_size = defaultdict(list)
            for f, size in file_sizes.items():
                by_size[size].append(f)
            
            for size, size_files in by_size.items():
                if len(size_files) > 1:
                    # Multiple files with same size - likely duplicates
                    # Keep the one without counter, or highest counter
                    def sort_key(f):
                        counter = parse_filename_for_counter(f.name)
                        if counter is None:
                            return (0, 0)
                        return (1, -counter)
                    
                    sorted_files = sorted(size_files, key=sort_key)
                    keep_file = sorted_files[0]
                    files_to_keep.append(keep_file)
                    
                    for dup_file in sorted_files[1:]:
                        duplicates_to_remove.append(dup_file)
                else:
                    files_to_keep.extend(size_files)
        else:
            files_to_keep.extend(files)
    
    return duplicates_to_remove, files_to_keep

def update_message_id_index(account_email, duplicates_removed):
    """Update the message ID index to remove references to deleted files."""
    email_safe = account_email.replace('@', '_at_').replace('.', '_')
    index_file = EMAIL_DIR / f".message_id_index_{email_safe}.json"
    
    if not index_file.exists():
        return
    
    try:
        with open(index_file, 'r', encoding='utf-8') as f:
            index = json.load(f)
        
        # Remove entries for deleted files
        deleted_paths = {str(f.relative_to(EMAIL_DIR)) for f in duplicates_removed}
        
        updated = False
        message_ids_to_remove = []
        for msg_id, file_path in index.items():
            if file_path in deleted_paths:
                message_ids_to_remove.append(msg_id)
                updated = True
        
        for msg_id in message_ids_to_remove:
            del index[msg_id]
        
        if updated:
            # Write atomically
            temp_file = index_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(index, f, indent=2, ensure_ascii=False)
            temp_file.replace(index_file)
            print(f"  Updated message ID index for {account_email}")
    
    except Exception as e:
        print(f"  Warning: Could not update index for {account_email}: {e}", file=sys.stderr)

def main():
    """Main deduplication logic."""
    import argparse
    parser = argparse.ArgumentParser(description="Deduplicate email files")
    parser.add_argument('--yes', '-y', action='store_true', help='Skip confirmation and remove duplicates automatically')
    args = parser.parse_args()
    
    print("=" * 60)
    print("Email Deduplication Script")
    print("=" * 60)
    print(f"Scanning email directory: {EMAIL_DIR}\n")
    
    # Find all email files
    print("Finding all email files...")
    email_files = find_email_files()
    print(f"Found {len(email_files)} email files\n")
    
    # Group by message ID
    print("Analyzing files...")
    by_message_id, no_message_id = group_by_message_id(email_files)
    print(f"  - Files with message ID: {len(email_files) - len(no_message_id)}")
    print(f"  - Files without message ID (older exports): {len(no_message_id)}")
    print(f"  - Unique message IDs: {len(by_message_id)}\n")
    
    # Find duplicates
    print("Identifying duplicates...")
    dup_by_id, keep_by_id = find_duplicates_with_message_id(by_message_id)
    dup_by_filename, keep_by_filename = find_duplicates_by_filename(no_message_id)
    
    all_duplicates = dup_by_id + dup_by_filename
    all_kept = keep_by_id + keep_by_filename
    
    print(f"  - Duplicate files to remove: {len(all_duplicates)}")
    print(f"  - Files to keep: {len(all_kept)}")
    
    if not all_duplicates:
        print("\n✓ No duplicates found! All files are unique.")
        return 0
    
    # Group duplicates by account
    duplicates_by_account = defaultdict(list)
    for dup_file in all_duplicates:
        account_email = dup_file.parent.parent.parent.name
        duplicates_by_account[account_email].append(dup_file)
    
    # Show duplicates
    print("\n" + "=" * 60)
    print("Duplicates Found:")
    print("=" * 60)
    for account_email, dup_files in duplicates_by_account.items():
        print(f"\n{account_email}:")
        for dup_file in sorted(dup_files):
            rel_path = dup_file.relative_to(EMAIL_DIR)
            size_kb = dup_file.stat().st_size / 1024
            print(f"  - {rel_path} ({size_kb:.1f} KB)")
    
    # Ask for confirmation (unless --yes flag is used)
    if not args.yes:
        print("\n" + "=" * 60)
        response = input(f"Remove {len(all_duplicates)} duplicate file(s)? (yes/no): ").strip().lower()
        
        if response not in ['yes', 'y']:
            print("Cancelled. No files were removed.")
            return 0
    else:
        print(f"\nAuto-removing {len(all_duplicates)} duplicate file(s)...")
    
    # Remove duplicates
    print("\nRemoving duplicates...")
    removed_count = 0
    total_size_freed = 0
    
    for account_email, dup_files in duplicates_by_account.items():
        print(f"\n{account_email}:")
        for dup_file in dup_files:
            try:
                size = dup_file.stat().st_size
                dup_file.unlink()
                removed_count += 1
                total_size_freed += size
                rel_path = dup_file.relative_to(EMAIL_DIR)
                print(f"  ✓ Removed: {rel_path}")
            except Exception as e:
                print(f"  ✗ Error removing {dup_file}: {e}", file=sys.stderr)
        
        # Update index for this account
        update_message_id_index(account_email, dup_files)
    
    print("\n" + "=" * 60)
    print("Deduplication Complete")
    print("=" * 60)
    print(f"  - Files removed: {removed_count}")
    print(f"  - Space freed: {total_size_freed / (1024 * 1024):.2f} MB")
    print(f"  - Files remaining: {len(all_kept)}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
