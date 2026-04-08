#!/usr/bin/env python3
import requests
import re
import argparse
import json
import os
from datetime import date

def fetch_trending(since='daily'):
    url = f"https://github.com/trending?since={since}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Error fetching {url}: {response.status_code}")
        return []

    html = response.text
    # Each repo is in an <article class="Box-row">
    articles = re.findall(r'<article class="Box-row".*?>(.*?)</article>', html, re.DOTALL)

    repos = []
    for article in articles:
        # Repository Name
        h2_match = re.search(r'<h2 class="h3 lh-condensed">(.*?)</h2>', article, re.DOTALL)
        if h2_match:
            repo_link_match = re.search(r'href="/(.*?)"', h2_match.group(1))
            repo_name = repo_link_match.group(1).strip() if repo_link_match else "Unknown"
        else:
            repo_name = "Unknown"

        # Description
        desc_match = re.search(r'<p class="col-9 color-fg-muted my-1 pr-4">\s*(.*?)\s*</p>', article, re.DOTALL)
        description = desc_match.group(1).strip() if desc_match else ""

        # Language
        lang_match = re.search(r'<span itemprop="programmingLanguage">(.*?)</span>', article)
        language = lang_match.group(1) if lang_match else "N/A"

        # Stars
        stars_match = re.search(r'stargazers".*?>\s*([\d,]+)\s*</a>', article, re.DOTALL)
        stars = stars_match.group(1).strip() if stars_match else "0"

        repos.append({
            "name": repo_name,
            "description": description,
            "language": language,
            "stars": stars,
            "url": f"https://github.com/{repo_name}"
        })

    return repos

def main():
    parser = argparse.ArgumentParser(description="Fetch GitHub trending repositories.")
    parser.add_argument("--since", choices=['daily', 'weekly', 'monthly'], default='daily', help="Time range (daily/weekly/monthly)")
    parser.add_argument("--limit", type=int, default=5, help="Number of repos to show")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    repos = fetch_trending(args.since)
    top_repos = repos[:args.limit]

    if args.json:
        print(json.dumps(top_repos, indent=2))
    else:
        print(f"\n### GitHub Trending ({args.since.capitalize()})")
        for i, repo in enumerate(top_repos, 1):
            print(f"{i}. [{repo['name']}]({repo['url']}) - {repo['language']} ({repo['stars']} stars)")
            if repo['description']:
                print(f"   _{repo['description']}_")

if __name__ == "__main__":
    main()
