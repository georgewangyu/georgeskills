from __future__ import annotations

import sys
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from io import StringIO
from pathlib import Path
from unittest import mock


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import print_location_interview_context as location  # noqa: E402
import run_daily_workflow_prep as prep  # noqa: E402


class LocationContextTests(unittest.TestCase):
    def test_owntracks_status_distinguishes_found_empty_and_stale(self) -> None:
        now = datetime(2026, 9, 8, 20, 0, tzinfo=timezone.utc)
        fresh = [
            location.Position(now - timedelta(hours=1), 0.0, 0.0, 0.0, ""),
        ]
        stale = [
            location.Position(now - timedelta(hours=13), 0.0, 0.0, 0.0, ""),
        ]

        self.assertEqual("empty", location.owntracks_source_status("2026-09-08", [], now=now))
        self.assertEqual("found", location.owntracks_source_status("2026-09-08", fresh, now=now))
        self.assertEqual("stale", location.owntracks_source_status("2026-09-08", stale, now=now))
        self.assertEqual("found", location.owntracks_source_status("2026-09-07", stale, now=now))

    @mock.patch.dict("os.environ", {"OWNTRACKS_STALE_AFTER_HOURS": "nan"})
    def test_non_finite_stale_override_uses_default(self) -> None:
        now = datetime(2026, 9, 8, 20, 0, tzinfo=timezone.utc)
        stale = [
            location.Position(now - timedelta(hours=13), 0.0, 0.0, 0.0, ""),
        ]

        self.assertEqual("stale", location.owntracks_source_status("2026-09-08", stale, now=now))

    def test_expired_owntracks_session_is_reported_without_private_error_text(self) -> None:
        error = RuntimeError("aws: Your session has expired. Please reauthenticate")

        self.assertEqual(
            "AWS CLI authentication expired; run `aws login`",
            location.summarize_owntracks_error(error),
        )

    def test_logged_out_session_is_classified_as_reauthentication(self) -> None:
        error = RuntimeError(
            "Error loading login session token: unable to load a existing login session; "
            "please reauthenticate with aws login"
        )

        self.assertEqual(
            "AWS CLI authentication expired; run `aws login`",
            location.summarize_owntracks_error(error),
        )

    @mock.patch.object(prep, "build_traccar_config", return_value=object())
    @mock.patch.object(prep, "fetch_traccar_positions", return_value=[])
    @mock.patch.object(prep, "build_owntracks_s3_config", return_value=object())
    @mock.patch.object(
        prep,
        "fetch_owntracks_s3_positions",
        side_effect=RuntimeError("aws: Your session has expired. Please reauthenticate"),
    )
    def test_summary_distinguishes_expired_owntracks_from_empty_traccar(
        self,
        _fetch_owntracks: mock.Mock,
        _build_owntracks: mock.Mock,
        _fetch_traccar: mock.Mock,
        _build_traccar: mock.Mock,
    ) -> None:
        body = prep.build_location_section("2026-08-11")

        self.assertIsNotNone(body)
        self.assertIn("OwnTracks/S3 status: `unreadable`", body)
        self.assertIn("AWS CLI authentication expired", body)
        self.assertIn("Traccar fallback returned no positions", body)

    @mock.patch.object(prep, "summarize_location_stop_clusters", return_value=[])
    @mock.patch.object(prep, "load_location_places", return_value=[])
    @mock.patch.object(prep, "build_traccar_config", return_value=object())
    @mock.patch.object(prep, "fetch_traccar_positions")
    @mock.patch.object(prep, "build_owntracks_s3_config", return_value=None)
    def test_summary_preserves_unavailable_status_when_fallback_succeeds(
        self,
        _build_owntracks: mock.Mock,
        fetch_traccar: mock.Mock,
        _build_traccar: mock.Mock,
        _load_places: mock.Mock,
        _stops: mock.Mock,
    ) -> None:
        fetch_traccar.return_value = [
            location.Position(datetime(2026, 8, 11, 10, 0).astimezone(), 0.0, 0.0, 0.0, ""),
        ]

        body = prep.build_location_section("2026-08-11")

        self.assertIsNotNone(body)
        self.assertIn("OwnTracks/S3 status: `unavailable`", body)
        self.assertIn("Source: `Traccar fallback`", body)

    @mock.patch.object(prep, "summarize_location_stop_clusters", return_value=[])
    @mock.patch.object(prep, "load_location_places", return_value=[])
    @mock.patch.object(prep, "build_traccar_config", return_value=object())
    @mock.patch.object(prep, "fetch_traccar_positions")
    @mock.patch.object(prep, "build_owntracks_s3_config", return_value=object())
    @mock.patch.object(prep, "fetch_owntracks_s3_positions", side_effect=RuntimeError("private provider detail"))
    def test_summary_preserves_unreadable_status_when_fallback_succeeds(
        self,
        _fetch_owntracks: mock.Mock,
        _build_owntracks: mock.Mock,
        fetch_traccar: mock.Mock,
        _build_traccar: mock.Mock,
        _load_places: mock.Mock,
        _stops: mock.Mock,
    ) -> None:
        fetch_traccar.return_value = [
            location.Position(datetime(2026, 8, 11, 10, 0).astimezone(), 0.0, 0.0, 0.0, ""),
        ]

        body = prep.build_location_section("2026-08-11")

        self.assertIsNotNone(body)
        self.assertIn("OwnTracks/S3 status: `unreadable`", body)
        self.assertIn("AWS/S3 read failed (RuntimeError)", body)
        self.assertNotIn("private provider detail", body)

    @mock.patch.object(prep, "summarize_location_stop_clusters")
    @mock.patch.object(prep, "load_location_places", return_value=[])
    @mock.patch.object(prep, "build_traccar_config")
    @mock.patch.object(prep, "build_owntracks_s3_config", return_value=object())
    @mock.patch.object(prep, "fetch_owntracks_s3_positions")
    def test_summary_redacts_coordinate_fallback_stop_labels(
        self,
        fetch_owntracks: mock.Mock,
        _build_owntracks: mock.Mock,
        _build_traccar: mock.Mock,
        _load_places: mock.Mock,
        summarize_stops: mock.Mock,
    ) -> None:
        fetch_owntracks.return_value = [
            location.Position(datetime(2026, 8, 11, 10, 0).astimezone(), 0.0, 0.0, 0.0, ""),
            location.Position(datetime(2026, 8, 11, 11, 0).astimezone(), 0.001, 0.001, 0.0, ""),
        ]
        summarize_stops.return_value = ["10:00-11:00 | 49.1234, -123.5678"]

        body = prep.build_location_section("2026-08-11")

        self.assertIsNotNone(body)
        self.assertIn("10:00-11:00 | unlabeled area", body)
        self.assertNotRegex(body, r"-?\d{1,3}\.\d{4},\s*-?\d{1,3}\.\d{4}")

    @mock.patch.object(location, "build_config", return_value=None)
    @mock.patch.object(location, "build_owntracks_s3_config", return_value=None)
    def test_standalone_reports_unavailable_owntracks_configuration(
        self,
        _build_owntracks: mock.Mock,
        _build_traccar: mock.Mock,
    ) -> None:
        output = StringIO()
        with mock.patch.object(sys, "argv", ["location", "--date", "2026-08-11"]):
            with redirect_stdout(output):
                self.assertEqual(0, location.main())

        self.assertIn("OwnTracks/S3 status: unavailable", output.getvalue())

    @mock.patch.object(prep, "summarize_location_stop_clusters", return_value=[])
    @mock.patch.object(prep, "load_location_places", return_value=[])
    @mock.patch.object(prep, "build_traccar_config")
    @mock.patch.object(prep, "build_owntracks_s3_config", return_value=object())
    @mock.patch.object(prep, "fetch_owntracks_s3_positions")
    def test_summary_prefers_owntracks_and_does_not_touch_traccar(
        self,
        fetch_owntracks: mock.Mock,
        _build_owntracks: mock.Mock,
        build_traccar: mock.Mock,
        _load_places: mock.Mock,
        _stops: mock.Mock,
    ) -> None:
        fetch_owntracks.return_value = [
            location.Position(
                timestamp=datetime(2026, 8, 11, 10, 0).astimezone(),
                latitude=0.0,
                longitude=0.0,
                speed_kph=0.0,
                address="",
            ),
            location.Position(
                timestamp=datetime(2026, 8, 11, 11, 0).astimezone(),
                latitude=0.001,
                longitude=0.001,
                speed_kph=1.0,
                address="",
            ),
        ]

        body = prep.build_location_section("2026-08-11")

        self.assertIsNotNone(body)
        self.assertIn("OwnTracks/S3 status: `found`", body)
        self.assertIn("Source: `OwnTracks/S3`", body)
        build_traccar.assert_not_called()


if __name__ == "__main__":
    unittest.main()
