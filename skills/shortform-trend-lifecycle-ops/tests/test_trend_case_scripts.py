from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
INIT = SKILL_ROOT / "scripts" / "init_trend_case.py"
VALIDATE = SKILL_ROOT / "scripts" / "validate_trend_case.py"
SYNC = SKILL_ROOT.parents[1] / "scripts" / "sync-to-agents.sh"
REPO_ROOT = SKILL_ROOT.parents[1]


class TrendCaseScriptsTest(unittest.TestCase):
    def run_command(self, *args: object) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, *(str(arg) for arg in args)],
            check=False,
            capture_output=True,
            text=True,
        )

    def initialize(self, root: Path) -> Path:
        result = self.run_command(
            INIT,
            "--root",
            root,
            "--slug",
            "visible-proof-ladder",
            "--title",
            "Visible Proof Ladder",
            "--discovered-on",
            "2026-09-01",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return root / "2026-09-01_visible-proof-ladder"

    def validate(self, case_dir: Path) -> tuple[subprocess.CompletedProcess[str], dict]:
        result = self.run_command(VALIDATE, case_dir)
        return result, json.loads(result.stdout)

    def test_initialize_validate_and_refuse_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            case_dir = self.initialize(root)
            result, payload = self.validate(case_dir)
            self.assertEqual(result.returncode, 0)
            self.assertTrue(payload["valid"])

            second = self.run_command(
                INIT,
                "--root",
                root,
                "--slug",
                "visible-proof-ladder",
                "--title",
                "Visible Proof Ladder",
                "--discovered-on",
                "2026-09-01",
            )
            self.assertNotEqual(second.returncode, 0)
            self.assertIn("refusing to overwrite", second.stderr)

    def test_rejects_bad_frontmatter_dates_and_empty_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            case_dir = self.initialize(Path(temporary))
            case_path = case_dir / "case.md"
            text = case_path.read_text(encoding="utf-8")
            text = text.replace('title: "Visible Proof Ladder"', 'title: ""')
            text = text.replace('discovered_on: "2026-09-01"', 'discovered_on: "yesterday"')
            text = text.replace('snapshot_at: "', 'snapshot_at: "not-a-timestamp')
            case_path.write_text(text, encoding="utf-8")
            result, payload = self.validate(case_dir)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(payload["valid"])
            self.assertTrue(any("title" in error for error in payload["errors"]))
            self.assertTrue(any("discovered_on" in error for error in payload["errors"]))
            self.assertTrue(any("snapshot_at" in error for error in payload["errors"]))

    def test_initializer_rejects_blank_title(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            result = self.run_command(
                INIT,
                "--root",
                temporary,
                "--slug",
                "visible-proof-ladder",
                "--title",
                "   ",
                "--discovered-on",
                "2026-09-01",
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("title must be a non-empty string", result.stderr)

    def test_initializer_refuses_symlinked_index(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temporary_root = Path(temporary)
            root = temporary_root / "cases"
            root.mkdir()
            outside_index = temporary_root / "outside.md"
            outside_index.write_text("outside\n", encoding="utf-8")
            (root / "INDEX.md").symlink_to(outside_index)
            result = self.run_command(
                INIT,
                "--root",
                root,
                "--slug",
                "visible-proof-ladder",
                "--title",
                "Visible Proof Ladder",
                "--discovered-on",
                "2026-09-01",
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("refusing symlinked case index", result.stderr)
            self.assertEqual(outside_index.read_text(encoding="utf-8"), "outside\n")
            self.assertFalse((root / "2026-09-01_visible-proof-ladder").exists())

    def test_sync_helper_refuses_source_skill_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temporary_root = Path(temporary)
            fake_repo = temporary_root / "repo"
            (fake_repo / "scripts").mkdir(parents=True)
            (fake_repo / "skills").mkdir()
            shutil.copy2(SYNC, fake_repo / "scripts" / "sync-to-agents.sh")
            outside_skill = temporary_root / "outside-skill"
            outside_skill.mkdir()
            (outside_skill / "SKILL.md").write_text("# Outside\n", encoding="utf-8")
            (fake_repo / "skills" / "outside").symlink_to(
                outside_skill, target_is_directory=True
            )
            destination = temporary_root / "destination"
            result = subprocess.run(
                ["bash", str(fake_repo / "scripts" / "sync-to-agents.sh")],
                check=False,
                capture_output=True,
                text=True,
                env={**os.environ, "AGENTS_SKILLS_DIR": str(destination)},
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Refusing source skill symlink", result.stderr)
            self.assertFalse((destination / "outside").exists())

    def test_owned_account_skills_use_current_metadata_and_refresh_contract(self) -> None:
        instagram = (REPO_ROOT / "skills" / "instagram-check-ops" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        tiktok = (REPO_ROOT / "skills" / "tiktok-check-ops" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        for skill in (instagram, tiktok):
            self.assertIn("\nmetadata:\n  memory_tags:\n", skill)
            self.assertNotIn("\nmemory_tags:\n", skill)
        self.assertNotIn("automatic refresh", tiktok)
        self.assertIn("explicit saved-token refresh", tiktok)

    def test_rejects_folder_identity_and_non_iso_milestones(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            case_dir = self.initialize(Path(temporary))
            renamed = case_dir.with_name("wrong-folder-name")
            case_dir.rename(renamed)
            case_path = renamed / "case.md"
            text = case_path.read_text(encoding="utf-8")
            text = text.replace("first_breakout_at: null", 'first_breakout_at: "June breakout"')
            text = text.replace("copy_wave_onset_at: null", 'copy_wave_onset_at: "2026-07"')
            case_path.write_text(text, encoding="utf-8")
            result, payload = self.validate(renamed)
            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(any("directory name" in error for error in payload["errors"]))
            self.assertTrue(any("first_breakout_at" in error for error in payload["errors"]))
            self.assertTrue(any("copy_wave_onset_at" in error for error in payload["errors"]))

    def test_rejects_invalid_milestone_order(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            case_dir = self.initialize(Path(temporary))
            case_path = case_dir / "case.md"
            text = case_path.read_text(encoding="utf-8")
            text = text.replace("earliest_source_backed_at: null", 'earliest_source_backed_at: "2026-08-01"')
            text = text.replace("peak_at: null", 'peak_at: "2026-07-01"')
            case_path.write_text(text, encoding="utf-8")
            result, payload = self.validate(case_dir)
            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(any("earliest_source_backed_at cannot follow peak_at" in error for error in payload["errors"]))

    def test_published_at_null_is_valid_with_note(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            case_dir = self.initialize(Path(temporary))
            evidence = {
                "evidence_id": "instagram-example-2026-09-01",
                "platform": "instagram",
                "url": "https://www.instagram.com/reel/example/",
                "creator": "creator",
                "published_at": None,
                "observed_at": "2026-09-01",
                "views": None,
                "likes": 1,
                "comments": None,
                "shares": None,
                "followers": None,
                "role": "source_candidate",
                "credit_targets": [],
                "format_match": "confirmed",
                "source_class": "platform_public",
                "notes": "Exact publication date unavailable.",
            }
            (case_dir / "evidence.jsonl").write_text(json.dumps(evidence) + "\n", encoding="utf-8")
            result, payload = self.validate(case_dir)
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertTrue(payload["valid"])

    def test_published_at_null_requires_note(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            case_dir = self.initialize(Path(temporary))
            evidence = {
                "evidence_id": "instagram-example-2026-09-01",
                "platform": "instagram",
                "url": "https://www.instagram.com/reel/example/",
                "creator": "creator",
                "published_at": None,
                "observed_at": "2026-09-01",
                "role": "source_candidate",
                "credit_targets": [],
                "format_match": "confirmed",
                "source_class": "platform_public",
                "notes": "",
            }
            (case_dir / "evidence.jsonl").write_text(json.dumps(evidence) + "\n", encoding="utf-8")
            result, payload = self.validate(case_dir)
            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(any("published_at null requires" in error for error in payload["errors"]))

    def test_non_object_and_unhashable_id_return_structured_errors(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            case_dir = self.initialize(Path(temporary))
            evidence_path = case_dir / "evidence.jsonl"
            records = [
                ["not", "an", "object"],
                {
                    "evidence_id": ["unhashable"],
                    "platform": "instagram",
                    "url": "https://www.instagram.com/reel/example/",
                    "creator": "creator",
                    "published_at": "bad-date",
                    "observed_at": "2026-09-01",
                    "role": "source_candidate",
                    "credit_targets": [],
                    "format_match": "confirmed",
                    "source_class": "platform_public",
                },
            ]
            evidence_path.write_text(
                "\n".join(json.dumps(record) for record in records) + "\n",
                encoding="utf-8",
            )
            result, payload = self.validate(case_dir)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(payload["valid"])
            self.assertTrue(any("must be an object" in error for error in payload["errors"]))
            self.assertTrue(any("evidence_id" in error for error in payload["errors"]))
            self.assertTrue(any("published_at" in error for error in payload["errors"]))


if __name__ == "__main__":
    unittest.main()
