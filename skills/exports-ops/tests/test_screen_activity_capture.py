from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from PIL import Image


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
import sys

sys.path.insert(0, str(SCRIPTS))

import capture_screen_activity as capture


class ScreenActivityCaptureTests(unittest.TestCase):
    def test_gpt56_original_token_formula(self) -> None:
        self.assertEqual(capture.gpt56_original_tokens(512, 512), 256)
        self.assertEqual(capture.gpt56_original_tokens(1600, 900), 1450)

    def test_contact_sheet_bucket(self) -> None:
        value = datetime(2026, 7, 18, 10, 17, 42, tzinfo=timezone.utc)
        self.assertEqual(
            capture.contact_sheet_bucket(value, 10),
            datetime(2026, 7, 18, 10, 10, tzinfo=timezone.utc),
        )

    def test_build_contact_sheet_and_usage_report(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = capture.Config(
                archive_root=root / "archive",
                state_root=root / "state",
                require_external_archive=False,
            )
            capture_dir = config.archive_root / "2026/07/18/captures"
            capture_dir.mkdir(parents=True)
            images = []
            for second, color in ((0, "red"), (30, "blue")):
                path = capture_dir / (
                    f"2026-07-18T10-00-{second:02d}+0000_Test-App.jpg"
                )
                Image.new("RGB", (1600, 900), color).save(path, "JPEG")
                images.append(path)

            output = (
                config.archive_root
                / "2026/07/18/analysis/contact-sheets/1000.jpg"
            )
            capture.build_contact_sheet(images, output, 5, 320, 180)
            self.assertTrue(output.exists())
            with Image.open(output) as sheet:
                self.assertEqual(sheet.size, (1600, 180))

            report = capture.usage_report(config, "2026-07-18")
            self.assertEqual(report["captures"]["count"], 2)
            self.assertEqual(
                report["captures"]["gpt_5_6_tokens_if_all_low_detail"],
                512,
            )
            self.assertEqual(
                report["captures"]["gpt_5_6_tokens_if_all_original_detail"],
                2900,
            )
            self.assertEqual(report["contact_sheets"]["count"], 1)
            self.assertFalse(
                report["recommended_analysis"]["automatic_model_calls"]
            )
            projection = report["projected_eight_hour_day"]
            self.assertEqual(
                projection["captures_before_lock_idle_sensitive_app_skips"], 960
            )
            self.assertEqual(projection["tokens_if_all_raw_low_detail"], 245760)
            self.assertEqual(projection["contact_sheets"], 48)
            self.assertEqual(
                projection["tokens_if_contact_sheets_low_detail"], 12288
            )

    def test_config_validation_and_loading(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / "config.json"
            path.write_text(
                json.dumps(
                    {
                        "archive_root": "/Volumes/screen-activity-unit-test/archive",
                        "state_root": str(root / "state"),
                        "interval_seconds": 30,
                    }
                ),
                encoding="utf-8",
            )
            config = capture.Config.from_path(path)
            self.assertEqual(config.interval_seconds, 30)
            self.assertEqual(config.retention_days, 7)

            with self.assertRaises(ValueError):
                capture.Config(
                    archive_root=root / "same",
                    state_root=root / "same",
                    require_external_archive=False,
                ).validate()

            path.write_text(
                json.dumps(
                    {
                        "archive_root": str(root / "internal"),
                        "state_root": str(root / "state"),
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "under /Volumes"):
                capture.Config.from_path(path)

    def test_missing_external_volume_does_not_create_mount_path(self) -> None:
        missing = Path("/Volumes/screen-activity-test-volume-that-does-not-exist")
        config = capture.Config(
            archive_root=missing / "archive",
            state_root=Path(tempfile.gettempdir()) / "screen-activity-test-state",
        )
        available, reason = capture.archive_available(config)
        self.assertFalse(available)
        self.assertTrue(reason.startswith("volume_missing:"))
        self.assertFalse(missing.exists())

    def test_privacy_checks_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = capture.Config(
                archive_root=root / "archive",
                state_root=root / "state",
                require_external_archive=False,
            )
            with mock.patch.object(capture, "screen_locked", return_value=None):
                result = capture.capture_once(config)
            self.assertEqual(result["status"], "skipped_lock_state_unknown")

            with mock.patch.object(capture, "screen_locked", return_value=False), mock.patch.object(
                capture, "idle_seconds", return_value=None
            ):
                result = capture.capture_once(config)
            self.assertEqual(result["status"], "skipped_idle_state_unknown")

            with mock.patch.object(capture, "screen_locked", return_value=False), mock.patch.object(
                capture, "idle_seconds", return_value=0.0
            ), mock.patch.object(capture, "frontmost_app", return_value=(None, None, None)):
                result = capture.capture_once(config)
            self.assertEqual(result["status"], "skipped_frontmost_app_unknown")

    def test_pause_still_purges_expired_raw_frames(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = capture.Config(
                archive_root=root / "archive",
                state_root=root / "state",
                require_external_archive=False,
            )
            old = (
                config.archive_root
                / "2026/07/01/captures/2026-07-01T10-00-00+0000_Test.jpg"
            )
            old.parent.mkdir(parents=True)
            Image.new("RGB", (10, 10), "black").save(old, "JPEG")
            old_time = (datetime.now().astimezone() - timedelta(days=10)).timestamp()
            os.utime(old, (old_time, old_time))
            config.state_root.mkdir(parents=True)
            config.pause_file.write_text("paused\n", encoding="utf-8")

            result = capture.capture_once(config)
            self.assertEqual(result["status"], "paused")
            self.assertFalse(old.exists())

    def test_retention_purges_expired_contact_sheet_and_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = capture.Config(
                archive_root=root / "archive",
                state_root=root / "state",
                retention_days=7,
                require_external_archive=False,
            )
            old_root = config.archive_root / "2026/07/01/analysis/contact-sheets"
            old_root.mkdir(parents=True)
            old_sheet = old_root / "1000.jpg"
            old_manifest = old_root / "1000.json"
            Image.new("RGB", (10, 10), "black").save(old_sheet, "JPEG")
            old_manifest.write_text("{}\n", encoding="utf-8")

            recent_root = config.archive_root / "2026/07/18/analysis/contact-sheets"
            recent_root.mkdir(parents=True)
            recent_sheet = recent_root / "1000.jpg"
            Image.new("RGB", (10, 10), "white").save(recent_sheet, "JPEG")

            deleted = capture.purge_expired(
                config, now=datetime(2026, 7, 18, 12, 0, tzinfo=timezone.utc)
            )

            self.assertEqual(deleted, 2)
            self.assertFalse(old_sheet.exists())
            self.assertFalse(old_manifest.exists())
            self.assertTrue(recent_sheet.exists())

    def test_external_archive_rejects_parent_traversal(self) -> None:
        self.assertIsNone(
            capture.configured_volume_root(
                Path("/Volumes/External/../Internal/screen-activity")
            )
        )

    def test_external_archive_rejects_symlink_escape(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            volume = root / "External"
            outside = root / "Outside"
            volume.mkdir()
            outside.mkdir()
            (volume / "escape").symlink_to(outside, target_is_directory=True)
            config = capture.Config(
                archive_root=volume / "escape" / "screen-activity",
                state_root=root / "state",
            )

            with (
                mock.patch.object(capture, "configured_volume_root", return_value=volume),
                mock.patch.object(capture.os.path, "ismount", return_value=True),
            ):
                available, reason = capture.archive_available(config)

            self.assertFalse(available)
            self.assertEqual(reason, "archive_outside_volume")

    def test_retention_prunes_expired_timeline_events(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = capture.Config(
                archive_root=root / "archive",
                state_root=root / "state",
                retention_days=7,
                require_external_archive=False,
            )
            events = config.archive_root / "2026/07/18/events.jsonl"
            events.parent.mkdir(parents=True)
            events.write_text(
                "\n".join(
                    [
                        json.dumps({"timestamp": "2026-07-01T10:00:00+00:00"}),
                        json.dumps({"timestamp": "2026-07-18T10:00:00+00:00"}),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            deleted = capture.purge_expired(
                config, now=datetime(2026, 7, 18, 12, 0, tzinfo=timezone.utc)
            )

            self.assertEqual(deleted, 1)
            self.assertEqual(
                [json.loads(line)["timestamp"] for line in events.read_text().splitlines()],
                ["2026-07-18T10:00:00+00:00"],
            )

    def test_pause_still_finalizes_completed_contact_sheet(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = capture.Config(
                archive_root=root / "archive",
                state_root=root / "state",
                require_external_archive=False,
            )
            frame = (
                config.archive_root
                / "2026/07/18/captures/2026-07-18T10-00-00+0000_Test.jpg"
            )
            frame.parent.mkdir(parents=True)
            Image.new("RGB", (1600, 900), "black").save(frame, "JPEG")
            config.state_root.mkdir(parents=True)
            config.pause_file.write_text("paused\n", encoding="utf-8")

            result = capture.capture_once(
                config, now=datetime(2026, 7, 18, 10, 11, tzinfo=timezone.utc)
            )
            self.assertEqual(result["status"], "paused")
            self.assertTrue(
                (
                    config.archive_root
                    / "2026/07/18/analysis/contact-sheets/1000.jpg"
                ).exists()
            )

    def test_internal_state_omits_app_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = capture.Config(
                archive_root=root / "archive",
                state_root=root / "state",
                idle_skip_seconds=86_400,
                require_external_archive=False,
            )

            def fake_command(args, timeout=30):
                if args[0] == "/usr/sbin/screencapture":
                    Image.new("RGB", (1600, 900), "green").save(args[-1], "JPEG")
                elif args[0] == "/usr/bin/sips" and "--out" in args:
                    output = Path(args[args.index("--out") + 1])
                    shutil.copy2(args[args.index("--out") - 1], output)
                return subprocess.CompletedProcess(args, 0, "", "")

            with mock.patch.object(capture, "screen_locked", return_value=False), mock.patch.object(
                capture, "idle_seconds", return_value=0.0
            ), mock.patch.object(
                capture,
                "frontmost_app",
                return_value=("Private App", "com.example.private", 42),
            ), mock.patch.object(capture, "run_command", side_effect=fake_command), mock.patch.object(
                capture, "image_dimensions", return_value=(1600, 900)
            ):
                result = capture.capture_once(config)

            self.assertEqual(result["status"], "captured")
            state_text = config.state_file.read_text(encoding="utf-8")
            self.assertNotIn("Private App", state_text)
            self.assertNotIn("com.example.private", state_text)
            self.assertNotIn('"latest_capture":', state_text)
            events = next(config.archive_root.glob("*/*/*/events.jsonl")).read_text(
                encoding="utf-8"
            )
            self.assertIn("Private App", events)

    def test_collector_lock_is_singleton(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = capture.Config(
                archive_root=root / "archive",
                state_root=root / "state",
                require_external_archive=False,
            )
            first = capture.acquire_collector_lock(config)
            self.assertIsNotNone(first)
            try:
                self.assertIsNone(capture.acquire_collector_lock(config))
            finally:
                first.close()


if __name__ == "__main__":
    unittest.main()
