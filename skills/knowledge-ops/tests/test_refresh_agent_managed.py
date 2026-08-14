import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path


PRIVATE_ROOT = Path(__file__).resolve().parents[4] / "georgerepo"
SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "refresh_agent_managed.py"
SCRIPTS_DIR = SCRIPT.parent

os.environ.setdefault("LIFEREPO_PRIVATE_ROOT", str(PRIVATE_ROOT))
sys.path.insert(0, str(SCRIPTS_DIR))

spec = importlib.util.spec_from_file_location("refresh_agent_managed", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class BulletParsingTests(unittest.TestCase):
    def test_preserved_created_date_keeps_existing_frontmatter_value(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.md"
            path.write_text(
                "---\ntitle: Report\ncreated: 2026-07-29\n---\n# Report\n",
                encoding="utf-8",
            )

            self.assertEqual(
                module.preserved_created_date(path, "2026-08-05"),
                "2026-07-29",
            )

    def test_preserved_created_date_uses_fallback_for_new_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing.md"

            self.assertEqual(
                module.preserved_created_date(path, "2026-08-05"),
                "2026-08-05",
            )

    def test_bullet_lines_join_wrapped_continuations(self) -> None:
        section = module.Section(
            title="Important Evidence",
            anchor="important-evidence",
            lines=[
                "",
                "- The original framework argues",
                "  that opportunity scoring needs five signals.",
                "- A complete second bullet.",
            ],
        )

        self.assertEqual(
            module.bullet_lines(section),
            [
                "The original framework argues that opportunity scoring needs five signals.",
                "A complete second bullet.",
            ],
        )

    def test_bullet_lines_keep_nested_items_as_separate_evidence(self) -> None:
        section = module.Section(
            title="Important Evidence",
            anchor="important-evidence",
            lines=[
                "- Parent observation:",
                "  - Nested detail with",
                "    a wrapped continuation.",
            ],
        )

        self.assertEqual(
            module.bullet_lines(section),
            ["Parent observation:", "Nested detail with a wrapped continuation."],
        )

    def test_append_unique_bullets_preserves_existing_wrapped_text(self) -> None:
        text = (
            "---\ntitle: Test\n---\n# Test\n\n"
            "## Important Evidence\n\n"
            "- Existing evidence spans\n"
            "  more than one line.\n\n"
            "## Source Map\n\n- `source.md`\n"
        )

        updated = module.append_unique_bullets(
            text,
            "Important Evidence",
            ["- New complete evidence."],
        )

        self.assertIn("- Existing evidence spans more than one line.", updated)
        self.assertIn("- New complete evidence.", updated)
        self.assertNotIn("- Existing evidence spans\n", updated)

    def test_representative_evidence_uses_a_complete_bounded_sentence(self) -> None:
        long_evidence = (
            "Context " + "setup " * 180 + ". "
            "The workflow now preserves complete evidence without bloating the wiki preflight. "
            "More " + "detail " * 180 + "."
        )

        selected = module.representative_evidence([long_evidence], limit=1)

        self.assertEqual(
            selected,
            ["The workflow now preserves complete evidence without bloating the wiki preflight."],
        )
        self.assertLessEqual(len(selected[0]), 480)

    def test_compiled_page_write_normalizes_the_final_newline(self) -> None:
        updated = module.upsert_level2_section(
            "---\ntitle: Test\n---\n# Test\n\n## Summary\n\n- Old.\n\n",
            "Summary",
            "- New.",
        )

        normalized = updated.rstrip() + "\n"

        self.assertTrue(normalized.endswith("\n"))
        self.assertFalse(normalized.endswith("\n\n"))


if __name__ == "__main__":
    unittest.main()
