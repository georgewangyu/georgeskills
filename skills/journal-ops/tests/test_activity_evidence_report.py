import importlib.util
import json
import tempfile
import unittest
import sys
from contextlib import ExitStack, redirect_stdout
from io import StringIO
from unittest import mock
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

SCRIPT = Path(__file__).parents[1] / "scripts/activity_evidence_report.py"
spec = importlib.util.spec_from_file_location("activity", SCRIPT)
activity = importlib.util.module_from_spec(spec)
spec.loader.exec_module(activity)


class ActivityEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.a = datetime(2026, 10, 12, tzinfo=timezone.utc)

    def interval(self, start, end, category="build", basis="observed_active"):
        return {"a": self.a + timedelta(hours=start), "b": self.a + timedelta(hours=end),
                "category": category, "basis": basis}

    def bounds(self, intervals):
        return activity.activity_bounds(intervals, self.a, self.a + timedelta(days=1), ["build", "admin"])

    def test_duplicate_overlap_is_unioned_and_conflict_unassigned(self):
        report = self.bounds([self.interval(1, 3), self.interval(2, 4), self.interval(3, 5, "admin")])
        self.assertEqual(report["categories"]["build"]["lower_seconds"], 7200)
        self.assertEqual(report["categories"]["admin"]["upper_seconds"], 3600)
        self.assertEqual(report["conflict_seconds"], 3600)
        self.assertEqual(report["unassigned_wallclock_seconds"], 21 * 3600)

    def test_inference_media_worker_and_host_gap(self):
        report = self.bounds([self.interval(1, 3, basis="inferred_active"),
                              self.interval(2, 3, basis="host_gap"),
                              self.interval(4, 8, basis="background_worker"),
                              self.interval(9, 10, basis="passive_media")])
        self.assertEqual(report["categories"]["build"], {"lower_seconds": 0, "upper_seconds": 3600})
        self.assertEqual(report["unassigned_wallclock_seconds"], 23 * 3600)

    def test_ambient_topics_do_not_imply_activity(self):
        source = self.root / "ambient.md"
        source.write_text("## 10:00 AM - 10:02 AM\nvideo with build\n## 10:01 AM - 10:03 AM\nvideo\n"
                          "## 10:03 AM - 10:03 AM\nbuild\n## 11:59 PM - 12:00 AM\nbuild\n")
        result = activity.ambient_day(source, date(2026, 10, 12), ZoneInfo("America/Los_Angeles"),
                                      {"build": ["build"], "creator": ["video"]})
        self.assertEqual(result["envelope_seconds"], 180)
        self.assertEqual(result["zero_minute_segments"], 1)
        self.assertEqual(result["ambiguous_or_boundary_segments"], 1)
        self.assertEqual(len(result["topics"]["creator"]), 2)
        self.assertEqual(self.bounds([])["unassigned_wallclock_fraction"], 1)

    def test_dst_and_missing_sources(self):
        zone = ZoneInfo("America/Los_Angeles")
        self.assertIsNone(activity.local_instant(date(2026, 11, 1), activity.clock("1:30 AM"), zone))
        self.assertIsNone(activity.local_instant(date(2026, 3, 8), activity.clock("2:30 AM"), zone))
        policy = {"timezone": str(zone), "topic_rules": {"build": ["build"]},
                  "ambient_root": str(self.root), "summaries_root": str(self.root),
                  "screen_archive_root": str(self.root)}
        report = activity.build_report(policy, date(2026, 11, 1), date(2026, 11, 1))
        self.assertEqual(report["activity"]["elapsed_seconds"], 25 * 3600)
        self.assertEqual(report["months"]["2026-11"]["ambient_days"], 0)
        self.assertEqual(report["activity"]["unassigned_wallclock_fraction"], 1)
        spring = activity.build_report(policy, date(2026, 3, 8), date(2026, 3, 8))
        self.assertEqual(spring["activity"]["elapsed_seconds"], 23 * 3600)

    def test_reviewed_source_validation_and_minute_uncertainty(self):
        source = self.root / "source.md"
        source.write_text("Observed interview\n")
        record = {"start": "2026-10-12T10:00:00-07:00", "end": "2026-10-12T11:00:00-07:00",
                  "category": "build", "basis": "observed_active", "source": str(source),
                  "line": 1, "rationale": "Retrospectively reviewed", "host_scope": "one device",
                  "boundary_uncertainty_seconds": 60}
        path = self.root / "reviewed.json"
        path.write_text(json.dumps([record]))
        intervals = activity.reviewed_intervals(path, ["build"])
        report = self.bounds(intervals)
        self.assertEqual(report["categories"]["build"], {"lower_seconds": 58 * 60, "upper_seconds": 62 * 60})
        record["start"] = "2026-10-12T10:00:00"
        path.write_text(json.dumps([record]))
        with self.assertRaisesRegex(ValueError, "explicit offsets"):
            activity.reviewed_intervals(path, ["build"])

    def test_daily_cli_refreshes_rollups_without_model_or_capture(self):
        policy = {"timezone": "America/Los_Angeles", "topic_rules": {"build": ["build"]},
                  "ambient_root": str(self.root / "ambient"), "summaries_root": str(self.root / "summaries"),
                  "screen_archive_root": str(self.root / "screen"), "derived_root": str(self.root / "derived")}
        path = self.root / "policy.json"
        path.write_text(json.dumps(policy))
        self.assertEqual(activity.main(["--policy", str(path), "--date", "2026-11-08"]), 0)
        for lane, count in [("daily", 1), ("weekly", 7), ("sprint", 14)]:
            output = self.root / "derived" / lane / "2026-11-08.json"
            report = json.loads(output.read_text())
            self.assertEqual(len(report["days"]), count)
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)

    def test_summary_presence_excludes_plans_and_background_sources(self):
        text = "## Tomorrow Priorities\nbuild\n## Sprints Today\nreal build\n## Audio Context\nplayed build lecture\n"
        self.assertEqual(list(activity.summary_activity_lines(text)), [(4, "real build")])

    def test_reviewed_offsets_reject_fixed_dst_error_and_accept_both_folds(self):
        source = self.root / "source.md"
        source.write_text("Synthetic recorded session\n")
        record = {"start": "2026-11-02T10:00:00-07:00", "end": "2026-11-02T11:00:00-07:00",
                  "category": "build", "basis": "observed_active", "source": str(source),
                  "line": 1, "rationale": "Synthetic observed session", "host_scope": "one device"}
        path = self.root / "reviewed.json"
        path.write_text(json.dumps([record]))
        zone = ZoneInfo("America/Los_Angeles")
        with self.assertRaisesRegex(ValueError, "offset conflicts"):
            activity.reviewed_intervals(path, ["build"], zone)
        for offset in ("-07:00", "-08:00"):
            record.update(start="2026-11-01T01:10:00" + offset, end="2026-11-01T01:20:00" + offset)
            path.write_text(json.dumps([record]))
            self.assertEqual(len(activity.reviewed_intervals(path, ["build"], zone)), 1)

    def test_screen_samples_are_metadata_not_measured_time(self):
        path = self.root / "2026/10/12/events.jsonl"
        path.parent.mkdir(parents=True)
        path.write_text('{"timestamp":"2026-10-12T10:00:00-07:00"}\nnot json\n'
                        '{"timestamp":"2026-10-12T12:00:00-07:00"}\n')
        result = activity.screen_metadata(self.root, date(2026, 10, 12))
        self.assertEqual(result["samples"], 2)
        self.assertEqual(result["invalid"], 1)
        self.assertNotIn("active_seconds", result)

    def test_existing_prep_routes_standard_full_and_skips_checkin_without_other_actions(self):
        sys.path.insert(0, str(SCRIPT.parent))
        import run_daily_workflow_prep as prep
        policy = self.root / "journal/allocation/policy.json"
        policy.parent.mkdir(parents=True)
        policy.write_text("{}")
        for profile in ("standard", "full", "checkin"):
            calls = []
            def run_step(name, command, **kwargs):
                calls.append((name, command))
                return prep.StepResult(name, True, "mocked unrelated action")
            with ExitStack() as stack:
                stack.enter_context(mock.patch.object(prep, "ROOT", self.root))
                stack.enter_context(mock.patch.object(prep, "run_step", side_effect=run_step))
                stack.enter_context(mock.patch.object(prep, "run_steps_parallel", return_value=[]))
                stack.enter_context(mock.patch.object(prep, "hydrate_summary_context", return_value=prep.StepResult("hydrate", True, "mock")))
                stack.enter_context(mock.patch.object(prep, "summary_path_for", return_value=self.root / "absent.md"))
                for name in ("print_audio_sources", "print_imessage_context", "note_count_for", "email_count_for", "reflection_exists_for"):
                    stack.enter_context(mock.patch.object(prep, name, return_value=0))
                stack.enter_context(mock.patch.object(sys, "argv", ["prep", "--date", "2026-11-08", "--module-profile", profile,
                                    "--skip-exports", "--skip-imessage", "--skip-health", "--skip-memory", "--skip-llm-wiki"]))
                with redirect_stdout(StringIO()):
                    self.assertEqual(prep.main(), 0)
            selected = [cmd for name, cmd in calls if name == "Activity evidence aggregates"]
            self.assertEqual(len(selected), 0 if profile == "checkin" else 1)
            if selected:
                self.assertEqual(selected[0][-4:], ["--policy", str(policy), "--date", "2026-11-08"])


if __name__ == "__main__":
    unittest.main()
