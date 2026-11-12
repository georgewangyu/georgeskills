from __future__ import annotations

import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import health_auto_export_rest_receiver as receiver  # noqa: E402

PATH = "/api/healthautoexport/v1/daily-metrics/ingest"


class ReceiverHttpGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), receiver.ReceiverHandler)
        self.server.dest_csv = Path(self.tmp.name) / "health.csv"
        self.server.raw_dir = Path(self.tmp.name) / "raw"
        self.server.auth_token = "secret-token"
        self.server.sync_write = False
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.tmp.cleanup()

    def post(self, body: bytes, token: str = "secret-token", length: int | str | None = None) -> int:
        request = urllib.request.Request(f"http://127.0.0.1:{self.server.server_port}{PATH}", data=body, method="POST")
        request.add_header("Authorization", f"Bearer {token}")
        if length is not None:
            request.add_header("Content-Length", str(length))
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                return response.status
        except urllib.error.HTTPError as error:
            return error.code

    def test_valid_token_is_accepted_and_wrong_token_rejected(self) -> None:
        self.assertEqual(self.post(json.dumps({}).encode()), 200)
        self.assertEqual(self.post(json.dumps({}).encode(), token="wrong"), 401)

    def test_bad_content_length_is_rejected_before_reading(self) -> None:
        for length, status in ((receiver.MAX_BODY_BYTES + 1, 413), (-1, 400), ("abc", 400)):
            with self.subTest(length=length):
                self.assertEqual(self.post(b"{}", length=length), status)
        self.assertFalse(self.server.raw_dir.exists())


class BindGuardTests(unittest.TestCase):
    def test_non_loopback_bind_requires_a_token(self) -> None:
        self.assertIsNotNone(receiver.bind_error("0.0.0.0", ""))
        self.assertIsNotNone(receiver.bind_error("192.168.1.20", ""))
        self.assertIsNone(receiver.bind_error("0.0.0.0", "secret-token"))
        self.assertIsNone(receiver.bind_error("127.0.0.1", ""))
        self.assertIsNone(receiver.bind_error("localhost", ""))
        self.assertIsNone(receiver.bind_error("::1", ""))


if __name__ == "__main__":
    unittest.main()
