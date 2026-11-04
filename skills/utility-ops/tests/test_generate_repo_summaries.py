from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import generate_repo_summaries as summaries  # noqa: E402


class RepoSummaryTests(unittest.TestCase):
    def test_metadata_lines_keep_markdown_hard_breaks(self) -> None:
        repo = {"name": "demo", "url": "https://github.com/o/demo", "isPrivate": False,
                "updatedAt": "2026-01-02T00:00:00Z", "primaryLanguage": {"name": "Python"}}
        with mock.patch.object(summaries, "github_owner", return_value="o"), \
                mock.patch.object(summaries, "get_repo_languages", return_value=["Python"]), \
                mock.patch.object(summaries, "get_repo_readme", return_value=""):
            content = summaries.create_repo_summary(repo)
        self.assertIn("**Repository**: [demo](https://github.com/o/demo)  \n**Visibility**: Public  \n", content)
        self.assertIn("**Last Updated**: ", content)
        self.assertRegex(content, r"\*\*Last Updated\*\*: [^\n]*  \n\*\*Primary Language\*\*")


if __name__ == "__main__":
    unittest.main()
