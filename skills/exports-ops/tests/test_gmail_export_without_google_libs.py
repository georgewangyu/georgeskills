from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "export_emails_gmail_api.py"

BLOCK_GOOGLE_AND_RUN = f"""
import runpy, sys
for name in ("google", "google.auth", "google.auth.transport.requests", "google.oauth2.credentials",
             "google_auth_oauthlib", "google_auth_oauthlib.flow", "googleapiclient",
             "googleapiclient.discovery", "googleapiclient.errors"):
    sys.modules[name] = None
sys.path.insert(0, {str(SCRIPT.parent)!r})
import export_emails_gmail_api
print("imported", flush=True)
sys.argv = [{str(SCRIPT)!r}]
runpy.run_path({str(SCRIPT)!r}, run_name="__main__")
"""


class GmailExportWithoutGoogleLibsTests(unittest.TestCase):
    def test_imports_then_main_exits_with_install_hint(self) -> None:
        result = subprocess.run([sys.executable, "-c", BLOCK_GOOGLE_AND_RUN],
                                capture_output=True, text=True, env=dict(os.environ))
        self.assertIn("imported", result.stdout)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("Gmail API libraries not installed", result.stderr)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
