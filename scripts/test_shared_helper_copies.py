from __future__ import annotations

import unittest
from pathlib import Path

SKILLS = Path(__file__).resolve().parents[1] / "skills"

VENDORED_HELPER_COPIES = {
    "repo_paths.py": ["health-ops", "journal-ops", "knowledge-ops", "memory-ops", "utility-ops"],
    "health_paths.py": ["health-ops", "journal-ops"],
}
EXPORTS_ONLY_CAPTURES_HINT = '    "captures",\n'
EXPORTS_VARIANT = ("repo_paths.py", "exports-ops")


def read(skill: str, name: str) -> str:
    return (SKILLS / skill / "scripts" / name).read_text(encoding="utf-8")


class SharedHelperCopiesTests(unittest.TestCase):
    def test_every_copy_is_listed(self) -> None:
        for name, skills in VENDORED_HELPER_COPIES.items():
            with self.subTest(helper=name):
                found = {path.parents[1].name for path in SKILLS.glob(f"*/scripts/{name}")}
                expected = set(skills) | ({EXPORTS_VARIANT[1]} if name == EXPORTS_VARIANT[0] else set())
                self.assertEqual(found, expected)

    def test_copies_are_identical(self) -> None:
        for name, skills in VENDORED_HELPER_COPIES.items():
            reference = read(skills[0], name)
            for skill in skills[1:]:
                with self.subTest(helper=name, skill=skill):
                    self.assertEqual(read(skill, name), reference, f"{skill}/scripts/{name} drifted from {skills[0]}")

    def test_exports_repo_paths_differs_only_by_the_captures_hint(self) -> None:
        exports = read(EXPORTS_VARIANT[1], EXPORTS_VARIANT[0])
        self.assertEqual(exports.count(EXPORTS_ONLY_CAPTURES_HINT), 1)
        self.assertEqual(exports.replace(EXPORTS_ONLY_CAPTURES_HINT, "", 1), read("journal-ops", "repo_paths.py"))


if __name__ == "__main__":
    unittest.main()
