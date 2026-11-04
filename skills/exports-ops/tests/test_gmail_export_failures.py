from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import httplib2
from googleapiclient.errors import HttpError

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import export_emails_gmail_api as gmail_export  # noqa: E402

SINCE = datetime.now(timezone.utc) - timedelta(days=1)


def fake_account(root: Path) -> SimpleNamespace:
    index: dict[str, str] = {}
    return SimpleNamespace(
        email="me@example.com", account_dir=root, sent_dir=root / "sent", received_dir=root / "received",
        last_export_file=root / "last.txt", message_id_index_file=root / "index.json",
        get_credentials=lambda: object(), load_message_id_index=lambda: index,
        save_message_id_index=lambda value: index.update(value),
    )


def listing_service(ids: list[str] | None, error: HttpError | None = None) -> mock.MagicMock:
    service = mock.MagicMock()
    execute = service.users.return_value.messages.return_value.list.return_value.execute
    if error:
        execute.side_effect = error
    else:
        execute.return_value = {"messages": [{"id": i} for i in ids or []]}
    return service


def message(message_id: str) -> dict:
    return {"datetime": datetime.now(timezone.utc), "subject": f"s-{message_id}", "from": "a@example.com",
            "to": "me@example.com", "cc": "", "bcc": "", "date": "today", "content": "body"}


class GmailExportFailureTests(unittest.TestCase):
    def run_export(self, service: mock.MagicMock, fetch) -> tuple:
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(gmail_export, "EMAIL_DIR", Path(tmp)), \
                    mock.patch.object(gmail_export, "build", return_value=service), \
                    mock.patch.object(gmail_export, "fetch_message_details", side_effect=fetch):
                return gmail_export.export_emails_for_account(fake_account(Path(tmp)), SINCE)

    def test_listing_error_is_a_failed_export(self) -> None:
        error = HttpError(httplib2.Response({"status": 500}), b"backend error")
        success, exported, errors, _ = self.run_export(listing_service(None, error), fetch=lambda s, i: message(i))
        self.assertFalse(success)

    def test_a_message_that_fails_keeps_the_account_failed(self) -> None:
        fetch = lambda service, message_id: None if message_id == "m2" else message(message_id)  # noqa: E731
        success, exported, errors, _ = self.run_export(listing_service(["m1", "m2", "m3"]), fetch)
        self.assertFalse(success)
        self.assertGreater(exported, 0)
        self.assertGreater(errors, 0)

    def test_clean_run_succeeds(self) -> None:
        success, exported, errors, latest = self.run_export(listing_service(["m1"]), fetch=lambda s, i: message(i))
        self.assertTrue(success)
        self.assertEqual(errors, 0)
        self.assertIsNotNone(latest)


class PagedService:
    def __init__(self, ids: list[str], page_size: int = 200) -> None:
        self.pages = [ids[i:i + page_size] for i in range(0, len(ids), page_size)] or [[]]
        self.service = mock.MagicMock()
        self.service.users.return_value.messages.return_value.list.side_effect = self.list

    def list(self, userId, q, maxResults, pageToken=None):
        index = int(pageToken or 0)
        page = {"messages": [{"id": i} for i in self.pages[index]]}
        if index + 1 < len(self.pages):
            page["nextPageToken"] = str(index + 1)
        return mock.MagicMock(execute=mock.MagicMock(return_value=page))


class GmailListingTests(unittest.TestCase):
    def test_listing_follows_every_page(self) -> None:
        ids = [f"m{n}" for n in range(700)]
        self.assertEqual(gmail_export.get_emails_since(PagedService(ids).service, SINCE), ids)


class GmailMainMarkerTests(unittest.TestCase):
    def run_main(self, root: Path, fetch) -> int:
        with mock.patch.object(gmail_export, "EMAIL_DIR", root):
            account = gmail_export.EmailAccount("me@example.com")
            account.get_credentials = lambda: object()
            with mock.patch.object(gmail_export, "parse_arguments", return_value=mock.Mock(since=None)), \
                    mock.patch.object(gmail_export, "acquire_lock", return_value=True), \
                    mock.patch.object(gmail_export.atexit, "register"), \
                    mock.patch.object(gmail_export.signal, "signal"), \
                    mock.patch.object(gmail_export, "load_accounts", return_value=[account]), \
                    mock.patch.object(gmail_export, "build", return_value=PagedService(["m1", "m2", "m3"]).service), \
                    mock.patch.object(gmail_export, "fetch_message_details", side_effect=fetch), \
                    self.assertRaises(SystemExit) as exit_info:
                gmail_export.main()
            return exit_info.exception.code, account.last_export_file

    def test_failed_or_interrupted_run_keeps_marker_and_retry_fetches_only_the_rest(self) -> None:
        def m2_fails(service, message_id):
            return None if message_id == "m2" else message(message_id)

        def interrupt_after_m1(service, message_id):
            if message_id == "m1":
                gmail_export.interrupt_requested = True
            return message(message_id)

        for name, first_run, refetched in (("m2 fails", m2_fails, ["m2"]), ("interrupt", interrupt_after_m1, ["m2", "m3"])):
            with self.subTest(name), tempfile.TemporaryDirectory() as tmp:
                try:
                    code, marker = self.run_main(Path(tmp), first_run)
                finally:
                    gmail_export.interrupt_requested = False
                self.assertEqual(code, 1)
                self.assertFalse(marker.exists())

                fetched: list[str] = []

                def record(service, message_id):
                    fetched.append(message_id)
                    return message(message_id)

                code, marker = self.run_main(Path(tmp), record)
                self.assertEqual(code, 0)
                self.assertTrue(marker.exists())
                self.assertEqual(sorted(set(fetched)), refetched)

    def test_message_deleted_before_fetch_does_not_fail_the_run(self) -> None:
        gone = HttpError(httplib2.Response({"status": 404}), b"not found")
        service = PagedService(["m1", "m2"]).service
        service.users.return_value.messages.return_value.get.return_value.execute.side_effect = gone
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(gmail_export, "EMAIL_DIR", Path(tmp)), \
                mock.patch.object(gmail_export, "build", return_value=service):
            success, exported, errors, _ = gmail_export.export_emails_for_account(fake_account(Path(tmp)), SINCE)
        self.assertTrue(success)
        self.assertEqual((exported, errors), (0, 0))


if __name__ == "__main__":
    unittest.main()
