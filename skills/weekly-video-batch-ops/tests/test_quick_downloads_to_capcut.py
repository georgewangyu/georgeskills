from __future__ import annotations

import argparse
import importlib.util
import json
import tempfile
import time
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "quick_downloads_to_capcut.py"
SPEC = importlib.util.spec_from_file_location("quick_downloads_to_capcut", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Could not load {SCRIPT}")
quick = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(quick)


class QuickDownloadsToCapCutTests(unittest.TestCase):
    def fixture(self, root: Path) -> tuple[Path, dict]:
        downloads = root / "Downloads"
        batch = root / "batches" / "2026-W29_video-batch"
        current = root / "_CURRENT_WEEK"
        drafts = root / "drafts"
        capcutbot = root / "capcutbot"
        downloads.mkdir()
        batch.mkdir(parents=True)
        drafts.mkdir()
        capcutbot.mkdir()
        current.symlink_to(batch)
        config = {
            "downloads_dir": str(downloads),
            "current_week_link": str(current),
            "drafts_root": str(drafts),
            "empty_template": "empty",
            "capcutbot_dir": str(capcutbot),
        }
        config_path = root / "config.json"
        config_path.write_text(json.dumps(config), encoding="utf-8")
        return config_path, config

    def test_requires_exact_recent_clip_count(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config_path, config = self.fixture(root)
            downloads = Path(config["downloads_dir"])
            (downloads / "one.MOV").write_bytes(b"one")
            (downloads / "two.MOV").write_bytes(b"two")
            with self.assertRaisesRegex(RuntimeError, "Expected exactly 1"):
                quick.recent_videos(downloads, 1, 60)
            self.assertTrue(config_path.is_file())

    def test_dry_run_does_not_create_project_or_move_clips(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config_path, config = self.fixture(root)
            clip = Path(config["downloads_dir"]) / "one.MOV"
            clip.write_bytes(b"one")
            args = argparse.Namespace(
                config=config_path,
                project_name="2026-07-12_test-video",
                count=1,
                max_age_minutes=60,
                dry_run=True,
                apply=False,
            )

            calls: list[str] = []

            def fake_draft_runner(mode: str, _project: Path, _payload: dict) -> dict:
                calls.append(mode)
                return {"mode": mode}

            output = quick.execute(args, draft_runner=fake_draft_runner)

            self.assertTrue(clip.is_file())
            self.assertFalse(Path(output["project_dir"]).exists())
            self.assertEqual(output["mode"], "dry-run")
            self.assertEqual(calls, ["dry-run"])
            self.assertEqual(output["draft_dry_run"]["mode"], "dry-run")

    def test_apply_moves_clips_and_runs_guarded_draft_sequence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config_path, config = self.fixture(root)
            downloads = Path(config["downloads_dir"])
            first = downloads / "one.MOV"
            second = downloads / "two.mp4"
            first.write_bytes(b"first-video")
            time.sleep(0.01)
            second.write_bytes(b"second-video")
            calls: list[str] = []

            def fake_draft_runner(mode: str, project_dir: Path, payload: dict) -> dict:
                calls.append(mode)
                if mode == "apply":
                    receipt = project_dir / "editor-projects" / "capcut-draft.json"
                    receipt.parent.mkdir(parents=True)
                    receipt.write_text("{}\n", encoding="utf-8")
                    (Path(payload["drafts_root"]) / project_dir.name).mkdir()
                return {"mode": mode}

            args = argparse.Namespace(
                config=config_path,
                project_name="2026-07-12_test-video",
                count=2,
                max_age_minutes=60,
                dry_run=False,
                apply=True,
            )

            output = quick.execute(args, draft_runner=fake_draft_runner)

            project = Path(output["project_dir"])
            self.assertEqual(calls, ["dry-run", "apply"])
            self.assertFalse(first.exists())
            self.assertFalse(second.exists())
            self.assertTrue((project / "raw" / "one.MOV").is_file())
            self.assertTrue((project / "raw" / "two.mp4").is_file())
            self.assertTrue((project / "assets").is_dir())
            self.assertTrue(Path(output["receipt"]).is_file())
            status = json.loads((project / "PROJECT_STATUS.json").read_text())
            self.assertEqual(status["status"], "active")
            self.assertTrue(all(item["verified"] for item in output["clip_verification"]))

    def test_apply_integrates_with_real_wrapper_and_isolated_capcutbot(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config_path, config = self.fixture(root)
            downloads = Path(config["downloads_dir"])
            drafts = Path(config["drafts_root"])
            capcutbot = Path(config["capcutbot_dir"])
            template = drafts / "empty"
            template.mkdir()
            (template / "draft_info.json").write_text(
                '{"duration": 0, "tracks": []}\n', encoding="utf-8"
            )
            (capcutbot / "src").mkdir()
            (capcutbot / "src" / "cli.js").write_text(
                """
const fs = require('fs');
const args = process.argv.slice(2);
const source = args[1];
const target = args[2];
const dryRun = args.includes('--dry-run');
if (!dryRun) fs.cpSync(source, target, {recursive: true});
process.stdout.write(JSON.stringify({copied: !dryRun, sourceDir: source, targetDir: target}));
""".strip()
                + "\n",
                encoding="utf-8",
            )
            clip = downloads / "one.MOV"
            clip.write_bytes(b"real-wrapper-video")
            args = argparse.Namespace(
                config=config_path,
                project_name="2026-07-12_real-wrapper-test",
                count=1,
                max_age_minutes=60,
                dry_run=False,
                apply=True,
            )

            output = quick.execute(args)

            project = Path(output["project_dir"])
            draft = drafts / args.project_name
            self.assertFalse(clip.exists())
            self.assertTrue((project / "raw" / clip.name).is_file())
            self.assertTrue(draft.is_dir())
            self.assertTrue((draft / "draft_info.json").is_file())
            self.assertTrue(Path(output["receipt"]).is_file())
            self.assertEqual(output["draft_dry_run"]["mode"], "dry-run")
            self.assertEqual(output["draft_apply"]["mode"], "apply")


if __name__ == "__main__":
    unittest.main()
