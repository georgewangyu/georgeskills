from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import run_daily_workflow_prep as prep  # noqa: E402


class BuildWikiIngestStateTests(unittest.TestCase):
    def test_counts_wiki_markdown_when_summary_and_wiki_exist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            summary = root / "summary.md"
            summary.write_text("day\n")
            wiki = root / "wiki"
            (wiki / "topics").mkdir(parents=True)
            (wiki / "index.md").write_text("a\n")
            (wiki / "topics" / "one.md").write_text("b\n")
            (wiki / ".git").mkdir()
            (wiki / ".git" / "ignored.md").write_text("c\n")

            with mock.patch.object(prep, "LLM_WIKI_ROOT", wiki), \
                    mock.patch.object(prep, "git_head_sha", return_value="abc123"):
                state = prep.build_wiki_ingest_state(target_date="2026-11-04", summary_path=summary)

        self.assertIsNotNone(state)
        self.assertEqual(state["wiki_markdown_count"], 2)
        self.assertEqual(state["git_head_sha"], "abc123")

    def test_returns_none_without_wiki(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            summary = Path(tmp) / "summary.md"
            summary.write_text("day\n")
            with mock.patch.object(prep, "LLM_WIKI_ROOT", Path(tmp) / "missing"):
                state = prep.build_wiki_ingest_state(target_date="2026-11-04", summary_path=summary)
        self.assertIsNone(state)


if __name__ == "__main__":
    unittest.main()
