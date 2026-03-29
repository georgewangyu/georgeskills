#!/usr/bin/env python3
"""Generate repository summaries in the configured private repo."""
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from repo_paths import resolve_private_repo_root


def github_owner() -> str:
    owner = subprocess.run(
        ["gh", "api", "user", "--jq", ".login"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    if not owner:
        raise RuntimeError("Could not determine GitHub owner from gh auth context.")
    return owner

def get_repo_languages(repo_name):
    """Get languages used in a repository"""
    try:
        owner = github_owner()
        result = subprocess.run(
            ['gh', 'repo', 'view', f'{owner}/{repo_name}', '--json', 'languages'],
            capture_output=True,
            text=True,
            check=True
        )
        data = json.loads(result.stdout)
        languages = [edge['node']['name'] for edge in data.get('languages', {}).get('edges', [])]
        return languages[:5]  # Top 5 languages
    except:
        return []

def get_repo_readme(repo_name):
    """Try to get README content"""
    try:
        owner = github_owner()
        result = subprocess.run(
            ['gh', 'api', f'repos/{owner}/{repo_name}/readme'],
            capture_output=True,
            text=True,
            check=True
        )
        data = json.loads(result.stdout)
        import base64
        content = base64.b64decode(data.get('content', '')).decode('utf-8')
        # Get first few lines for summary
        lines = content.split('\n')[:10]
        return '\n'.join(lines)
    except:
        return None

def format_date(date_str):
    """Format ISO date string to readable format"""
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d')
    except:
        return date_str

def create_repo_summary(repo_data):
    """Create a markdown summary for a repository"""
    repo_name = repo_data['name']
    description = repo_data.get('description', 'No description available')
    is_private = repo_data.get('isPrivate', False)
    updated_at = repo_data.get('updatedAt', 'Unknown')
    primary_lang = repo_data.get('primaryLanguage', {}).get('name', 'Unknown') if repo_data.get('primaryLanguage') else 'Unknown'
    owner = github_owner()
    url = repo_data.get('url', f'https://github.com/{owner}/{repo_name}')
    
    # Get additional details
    languages = get_repo_languages(repo_name)
    if not languages and primary_lang != 'Unknown':
        languages = [primary_lang]
    
    readme_preview = get_repo_readme(repo_name)
    
    # Create markdown content
    content = f"""# {repo_name}

**Repository**: [{repo_name}]({url})  
**Visibility**: {'Private' if is_private else 'Public'}  
**Last Updated**: {format_date(updated_at)}  
**Primary Language**: {primary_lang}

## Purpose

{description}

## Tech Stack

{', '.join(languages) if languages else primary_lang}

## Notes

{readme_preview if readme_preview else 'No README available or could not be retrieved.'}

---
*Generated automatically from GitHub repository metadata*
"""
    
    return content

def main():
    # Get all repos
    result = subprocess.run(
        ['gh', 'repo', 'list', '--limit', '1000', '--json', 'name,description,isPrivate,updatedAt,url,primaryLanguage'],
        capture_output=True,
        text=True,
        check=True
    )
    
    repos = json.loads(result.stdout)
    
    # Filter out this repo and public docs repo.
    repos = [r for r in repos if r['name'] not in {'liferepo', 'georgeskills'}]

    # Create projects/repos directory if it doesn't exist
    private_repo_root = resolve_private_repo_root()
    repos_dir = private_repo_root / 'projects' / 'repos'
    repos_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate summary for each repo
    for repo in repos:
        summary = create_repo_summary(repo)
        output_file = repos_dir / f"{repo['name']}.md"
        output_file.write_text(summary)
        print(f"Created summary for {repo['name']}")

if __name__ == '__main__':
    main()
