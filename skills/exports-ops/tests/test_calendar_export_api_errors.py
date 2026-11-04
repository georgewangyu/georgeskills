from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import httplib2
from googleapiclient.errors import HttpError

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import export_calendar_google as calendar_export  # noqa: E402

ACCOUNT = SimpleNamespace(email="me@example.com", enabled=True, calendar_ids=["me@example.com"])


def failing_service() -> mock.MagicMock:
    service = mock.MagicMock()
    service.calendarList.return_value.list.return_value.execute.return_value = {"items": []}
    error = HttpError(httplib2.Response({"status": 503}), b"backend error")
    service.events.return_value.list.return_value.execute.side_effect = error
    return service


class CalendarExportApiErrorTests(unittest.TestCase):
    def test_failed_fetch_keeps_existing_day(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            archive_dir = Path(tmp)
            today = datetime.now()
            archive = archive_dir / f"{today:%Y-%m}.md"
            good_day = f"# Calendar Archive\n\n## {today:%Y-%m-%d} (today)\n\n### Standup\n"
            archive.write_text(good_day, encoding="utf-8")

            with mock.patch.object(calendar_export, "ARCHIVE_DIR", archive_dir), \
                    self.assertRaises(calendar_export.CalendarFetchError):
                calendar_export.archive_today_to_monthly([(ACCOUNT, failing_service())])

            self.assertEqual(archive.read_text(encoding="utf-8"), good_day)

    def test_failed_fetch_does_not_write_weekly_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            calendar_dir = Path(tmp)
            weekly = calendar_dir / "weekly_calendar.md"
            weekly.write_text("previous week\n", encoding="utf-8")

            with mock.patch.object(calendar_export, "CALENDAR_DIR", calendar_dir), \
                    self.assertRaises(calendar_export.CalendarFetchError):
                calendar_export.export_weekly_calendar([(ACCOUNT, failing_service())])

            self.assertEqual(weekly.read_text(encoding="utf-8"), "previous week\n")

    def test_main_exits_nonzero_and_keeps_files_when_api_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            calendar_dir = Path(tmp)
            weekly = calendar_dir / "weekly_calendar.md"
            weekly.write_text("previous week\n", encoding="utf-8")
            (calendar_dir / "archive").mkdir()
            account = SimpleNamespace(**vars(ACCOUNT), get_credentials=lambda: object())
            with mock.patch.object(calendar_export, "CALENDAR_DIR", calendar_dir), \
                    mock.patch.object(calendar_export, "ARCHIVE_DIR", calendar_dir / "archive"), \
                    mock.patch.object(calendar_export, "load_accounts", return_value=[account]), \
                    mock.patch.object(calendar_export, "build", return_value=failing_service()):
                self.assertEqual(calendar_export.main(), 1)
            self.assertEqual(weekly.read_text(encoding="utf-8"), "previous week\n")
            self.assertEqual(list((calendar_dir / "archive").iterdir()), [])


if __name__ == "__main__":
    unittest.main()
