from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "sync-to-codex.sh"


class SyncToCodexTests(unittest.TestCase):
    def run_sync(self, codex_home: Path) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ, CODEX_HOME=str(codex_home))
        return subprocess.run(["bash", str(SCRIPT)], env=env, capture_output=True, text=True, check=True)

    def test_keeps_a_real_directory_with_a_skill_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skills = Path(tmp) / "skills"
            own = skills / "journal-ops"
            own.mkdir(parents=True)
            (own / "notes.md").write_text("mine\n")

            result = self.run_sync(Path(tmp))

            self.assertTrue((own / "notes.md").exists())
            self.assertFalse(own.is_symlink())
            self.assertIn("Skipping existing non-symlink entry: journal-ops", result.stdout)

    def test_replaces_a_stale_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skills = Path(tmp) / "skills"
            skills.mkdir()
            (skills / "journal-ops").symlink_to(Path(tmp) / "gone")

            self.run_sync(Path(tmp))

            link = skills / "journal-ops"
            self.assertTrue(link.is_symlink())
            self.assertEqual(link.resolve(), (SCRIPT.parent.parent / "skills" / "journal-ops").resolve())


if __name__ == "__main__":
    unittest.main()
