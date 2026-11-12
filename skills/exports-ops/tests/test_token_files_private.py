from __future__ import annotations

import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import export_calendar_google as calendar_export  # noqa: E402
import export_emails_gmail_api as gmail_export  # noqa: E402
import token_store  # noqa: E402


class RefreshableCreds:
    valid = False
    expired = True
    refresh_token = "refresh"

    def refresh(self, request) -> None:
        self.valid = True

    def to_json(self) -> str:
        return '{"token": "refreshed"}'


class TokenFilesPrivateTests(unittest.TestCase):
    def test_save_token_is_owner_only_and_keeps_old_token_on_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            token = Path(tmp) / "token.json"
            token_store.save_token(token, '{"token": "old"}')
            self.assertEqual(stat.S_IMODE(token.stat().st_mode), 0o600)
            with mock.patch.object(token_store.os, "fsync", side_effect=OSError("disk full")):
                with self.assertRaises(OSError):
                    token_store.save_token(token, '{"token": "new"}')
            self.assertEqual(token.read_text(), '{"token": "old"}')
            self.assertEqual([p.name for p in Path(tmp).iterdir()], ["token.json"])

    def test_refreshed_token_is_rewritten_owner_only(self) -> None:
        accounts = (
            (gmail_export, lambda: gmail_export.EmailAccount("me@example.com")),
            (calendar_export, lambda: calendar_export.CalendarAccount("me@example.com", [])),
        )
        for module, make_account in accounts:
            with self.subTest(module=module.__name__), tempfile.TemporaryDirectory() as tmp:
                account = make_account()
                account.token_file = Path(tmp) / "token.json"
                account.token_file.write_text('{"token": "old"}')
                account.token_file.chmod(0o644)
                with mock.patch.object(module.Credentials, "from_authorized_user_file", return_value=RefreshableCreds()), \
                        mock.patch.object(module, "build", return_value=mock.MagicMock()), \
                        mock.patch.object(type(account), "verify_account", return_value=True):
                    self.assertIsNotNone(account.get_credentials())
                self.assertEqual(account.token_file.read_text(), '{"token": "refreshed"}')
                self.assertEqual(stat.S_IMODE(account.token_file.stat().st_mode), 0o600)


if __name__ == "__main__":
    unittest.main()
