from __future__ import annotations

import csv
import json
import os
import signal
import sys
import threading
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import send_email_gmail_api as sender  # noqa: E402

FIELDS = ["lead_id", "contact_email", "draft_subject", "draft_body", "draft_status"]
ACCOUNT = SimpleNamespace(email="me@example.com", assistant_signature=None)


def write_batch(path: Path, statuses: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for number, status in enumerate(statuses, start=1):
            writer.writerow({
                "lead_id": f"lead-{number}",
                "contact_email": f"person{number}@example.com",
                "draft_subject": "Hello",
                "draft_body": "Body",
                "draft_status": status,
            })


def read_rows(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return {row["lead_id"]: row for row in csv.DictReader(handle)}


class FakeGmail:
    def __init__(self, ctrl_c_after: int | None = None) -> None:
        self.calls: list[str] = []
        self.ctrl_c_after = ctrl_c_after
        self.lock = threading.Lock()

    def send(self, service, from_email, to, subject, body, cc=None, attachments=None):
        with self.lock:
            self.calls.append(to)
            count = len(self.calls)
        if count == self.ctrl_c_after:
            self.ctrl_c_after = None
            os.kill(os.getpid(), signal.SIGINT)
        return f"msg-{count}"


def run(batch: Path, gmail: FakeGmail, log: Path | None = None, output: Path | None = None,
        max_workers: int = 1) -> int:
    with patch.object(sender, "get_thread_service", return_value=object()), \
            patch.object(sender, "send_message_via_service", side_effect=gmail.send):
        return sender.run_batch_send(
            account=ACCOUNT, batch_csv=batch, output_csv=output or batch, log_path=log,
            to_column="contact_email", subject_column="draft_subject", body_column="draft_body",
            max_workers=max_workers, skip_sent=True, cc=None, attachments=[], append_signature=False,
        )


class BatchSendResumeTests(unittest.TestCase):
    def test_rerun_after_ctrl_c_sends_each_lead_once(self) -> None:
        for workers in (1, 3):
            with self.subTest(max_workers=workers), tempfile.TemporaryDirectory() as tmp:
                batch = Path(tmp) / "batch.csv"
                write_batch(batch, ["approved"] * 10)
                gmail = FakeGmail(ctrl_c_after=3)
                with self.assertRaises(KeyboardInterrupt):
                    run(batch, gmail, max_workers=workers)
                sent_before_rerun = {row["contact_email"] for row in read_rows(batch).values()
                                     if row["send_status"] == "sent"}
                self.assertEqual(sent_before_rerun, set(gmail.calls))

                self.assertEqual(run(batch, gmail, max_workers=workers), 0)
                sends = Counter(gmail.calls)
                self.assertEqual(sorted(sends), sorted(f"person{n}@example.com" for n in range(1, 11)))
                self.assertEqual(set(sends.values()), {1})

    def test_log_marks_leads_sent_when_output_is_another_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            batch, output, log = (Path(tmp) / name for name in ("batch.csv", "out.csv", "send.jsonl"))
            write_batch(batch, ["approved"] * 3)
            gmail = FakeGmail()
            run(batch, gmail, log=log, output=output)
            run(batch, gmail, log=log, output=output)
            self.assertEqual(len(gmail.calls), 3)
            statuses = [json.loads(line)["status"] for line in log.read_text().splitlines()]
            self.assertEqual(statuses, ["sent"] * 3)
            out = read_rows(output)
            self.assertEqual({row["send_status"] for row in out.values()}, {"sent"})
            self.assertEqual(sorted(row["gmail_message_id"] for row in out.values()), ["msg-1", "msg-2", "msg-3"])

    def test_follow_up_with_new_subject_is_not_skipped_by_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            batch, log = Path(tmp) / "batch.csv", Path(tmp) / "send.jsonl"
            write_batch(batch, ["approved"])
            gmail = FakeGmail()
            run(batch, gmail, log=log, output=Path(tmp) / "out.csv")
            rows = list(read_rows(batch).values())
            rows[0]["draft_subject"] = "Following up"
            with batch.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=FIELDS)
                writer.writeheader()
                writer.writerows(rows)
            run(batch, gmail, log=log, output=Path(tmp) / "out.csv")
            self.assertEqual(len(gmail.calls), 2)

    def test_only_approved_drafts_send(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            batch = Path(tmp) / "batch.csv"
            write_batch(batch, ["approved", "", "draft", "Approved"])
            gmail = FakeGmail()
            run(batch, gmail)
            self.assertEqual(gmail.calls, ["person1@example.com", "person4@example.com"])
            rows = read_rows(batch)
            self.assertEqual(rows["lead-2"]["send_status"], "skipped")
            self.assertEqual(rows["lead-2"]["draft_status"], "")
            self.assertIn("approved", rows["lead-3"]["last_error"])


if __name__ == "__main__":
    unittest.main()
