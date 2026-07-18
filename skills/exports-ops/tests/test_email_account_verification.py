from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from typing import Optional
from unittest.mock import patch


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import export_emails_gmail_api as gmail_export


class FakeCredentials:
    valid = True
    expired = False
    refresh_token = None

    def to_json(self):
        return "{}"


class FakeRequest:
    def __init__(self, result=None, error: Optional[Exception] = None):
        self.result = result
        self.error = error

    def execute(self):
        if self.error:
            raise self.error
        return self.result


class FakeUsers:
    def __init__(self, request: FakeRequest):
        self.request = request

    def getProfile(self, userId: str):
        self.user_id = userId
        return self.request


class FakeService:
    def __init__(self, request: FakeRequest):
        self.fake_users = FakeUsers(request)

    def users(self):
        return self.fake_users


class FakeFlow:
    def __init__(self, credentials):
        self.credentials = credentials
        self.run_kwargs = None

    def run_local_server(self, **kwargs):
        self.run_kwargs = kwargs
        return self.credentials


class EmailAccountVerificationTest(unittest.TestCase):
    def test_verification_error_is_unknown_not_mismatch(self) -> None:
        account = gmail_export.EmailAccount("expected@example.com")
        service = FakeService(FakeRequest(error=RuntimeError("temporary network failure")))

        self.assertIsNone(account.verify_account(service))

    def test_existing_token_survives_transient_verification_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            token_path = Path(temporary_directory) / "token.json"
            token_path.write_text("{}\n", encoding="utf-8")
            account = gmail_export.EmailAccount("expected@example.com")
            account.token_file = token_path
            credentials = FakeCredentials()
            service = FakeService(
                FakeRequest(error=RuntimeError("temporary network failure"))
            )

            with patch.object(
                gmail_export.Credentials,
                "from_authorized_user_file",
                return_value=credentials,
            ), patch.object(gmail_export, "build", return_value=service):
                result = account.get_credentials()

            self.assertIs(result, credentials)
            self.assertTrue(token_path.exists())

    def test_existing_token_is_removed_after_confirmed_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            token_path = Path(temporary_directory) / "token.json"
            token_path.write_text("{}\n", encoding="utf-8")
            account = gmail_export.EmailAccount("expected@example.com")
            account.token_file = token_path
            credentials = FakeCredentials()
            service = FakeService(
                FakeRequest(result={"emailAddress": "other@example.com"})
            )

            with patch.object(
                gmail_export.Credentials,
                "from_authorized_user_file",
                return_value=credentials,
            ), patch.object(gmail_export, "build", return_value=service):
                result = account.get_credentials()

            self.assertIsNone(result)
            self.assertFalse(token_path.exists())

    def test_oauth_flow_hints_and_requires_expected_account_selection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            token_path = root / "token.json"
            credentials_path = root / "credentials.json"
            credentials_path.write_text("{}\n", encoding="utf-8")
            account = gmail_export.EmailAccount("expected@example.com")
            account.token_file = token_path
            credentials = FakeCredentials()
            flow = FakeFlow(credentials)
            service = FakeService(
                FakeRequest(result={"emailAddress": "expected@example.com"})
            )

            with patch.object(gmail_export, "CREDENTIALS_FILE", credentials_path), patch.object(
                gmail_export.InstalledAppFlow,
                "from_client_secrets_file",
                return_value=flow,
            ), patch.object(gmail_export, "build", return_value=service):
                result = account.get_credentials()

            self.assertIs(result, credentials)
            self.assertEqual(
                flow.run_kwargs,
                {
                    "port": 0,
                    "prompt": "select_account",
                    "login_hint": "expected@example.com",
                },
            )
            self.assertTrue(token_path.exists())


if __name__ == "__main__":
    unittest.main()
