from __future__ import annotations

import csv
import stat
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import health_auto_export_rest_receiver as receiver  # noqa: E402

EXISTING_DAYS = 365
CONCURRENT_POSTS = 20


def read_dates(path: Path) -> list[str]:
    with path.open(encoding="utf-8", newline="") as handle:
        return [row["date"] for row in csv.DictReader(handle)]


class ConcurrentUpsertTests(unittest.TestCase):
    def test_parallel_upserts_keep_every_row(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "daily_health_metrics.csv"
            receiver.upsert_rows(dest, [{"date": f"2024-{i:03d}", "steps": "1000"}
                                        for i in range(EXISTING_DAYS)])
            self.assertEqual(len(read_dates(dest)), EXISTING_DAYS)

            start = threading.Barrier(CONCURRENT_POSTS)
            errors: list[BaseException] = []

            def post(index: int) -> None:
                start.wait()
                try:
                    receiver.upsert_rows(dest, [{"date": f"2026-{index:03d}", "steps": str(index)}])
                except BaseException as exc:  # surfaced below
                    errors.append(exc)

            threads = [threading.Thread(target=post, args=(i,)) for i in range(CONCURRENT_POSTS)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

            self.assertEqual(errors, [])
            dates = read_dates(dest)
            self.assertEqual(len(dates), EXISTING_DAYS + CONCURRENT_POSTS)
            self.assertEqual(len(set(dates)), len(dates))
            leftovers = [p.name for p in Path(tmp).iterdir() if p.name.startswith(".") and p.suffix == ".tmp"]
            self.assertEqual(leftovers, [])

    def test_failed_write_keeps_previous_csv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "daily_health_metrics.csv"
            receiver.upsert_rows(dest, [{"date": f"2024-{i:03d}", "steps": "1"} for i in range(3)])
            with mock.patch.object(receiver.csv.DictWriter, "writerow", side_effect=OSError("disk full")):
                with self.assertRaises(OSError):
                    receiver.upsert_rows(dest, [{"date": "2026-001", "steps": "2"}])
            self.assertEqual(read_dates(dest), ["2024-000", "2024-001", "2024-002"])
            self.assertEqual(sorted(p.name for p in Path(tmp).iterdir()), [dest.name])

    def test_parallel_processes_keep_every_row(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "daily_health_metrics.csv"
            receiver.upsert_rows(dest, [{"date": f"2024-{i:03d}", "steps": "1"} for i in range(EXISTING_DAYS)])
            writer = (
                "import sys; sys.path.insert(0, sys.argv[1]); "
                "import health_auto_export_rest_receiver as r; from pathlib import Path; "
                "[r.upsert_rows(Path(sys.argv[2]), [{'date': f'2026-{sys.argv[3]}-{n:02d}', 'steps': '1'}]) "
                "for n in range(10)]"
            )
            procs = [subprocess.Popen([sys.executable, "-c", writer, str(SCRIPTS_DIR), str(dest), str(p)])
                     for p in range(4)]
            self.assertEqual([proc.wait() for proc in procs], [0, 0, 0, 0])
            self.assertEqual(len(read_dates(dest)), EXISTING_DAYS + 40)

    def test_new_csv_is_private_and_symlink_target_is_updated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "real.csv"
            receiver.upsert_rows(target, [{"date": "2024-001", "steps": "1"}])
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o600)
            link = Path(tmp) / "link.csv"
            link.symlink_to(target)
            receiver.upsert_rows(link, [{"date": "2024-002", "steps": "2"}])
            self.assertTrue(link.is_symlink())
            self.assertEqual(read_dates(target), ["2024-001", "2024-002"])

    def test_same_second_same_session_archives_do_not_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            first = receiver.archive_payload(Path(tmp), {"n": 1}, session_id="s")
            second = receiver.archive_payload(Path(tmp), {"n": 2}, session_id="s")
            self.assertNotEqual(first, second)
            self.assertEqual(len(list(Path(tmp).glob("*.json"))), 2)


if __name__ == "__main__":
    unittest.main()
