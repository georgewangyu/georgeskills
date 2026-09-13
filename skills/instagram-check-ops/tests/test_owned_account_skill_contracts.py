from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


class OwnedAccountSkillContractsTest(unittest.TestCase):
    def test_current_metadata_and_saved_token_refresh_contract(self) -> None:
        instagram = (REPO_ROOT / "skills" / "instagram-check-ops" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        tiktok = (REPO_ROOT / "skills" / "tiktok-check-ops" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        for skill in (instagram, tiktok):
            self.assertIn("\nmetadata:\n  memory_tags:\n", skill)
            self.assertNotIn("\nmemory_tags:\n", skill)
        self.assertNotIn("automatic refresh", tiktok)
        self.assertIn("explicit saved-token refresh", tiktok)


if __name__ == "__main__":
    unittest.main()
