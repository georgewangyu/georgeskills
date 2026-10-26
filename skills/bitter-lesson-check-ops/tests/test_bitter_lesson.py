import datetime
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import bitter_lesson as bl  # noqa: E402

# Resolve tag names from the vocabulary so a rename does not break the tests.
KEEP, GATE, SOFT = bl.ORDER

SKILL = f"""---
name: demo
description: mentions [bl: {SOFT}] in frontmatter, which is ignored
---

# Demo

## Overview

Tags look like `[bl: {SOFT}]` in prose, which is a mention.

### 1. Push Back When Warranted [bl: {SOFT}]

You are not a yes-machine.

```
## Example [bl: {SOFT}]
```

### 2. Verify [bl: {KEEP}]

Run the tests.

## Rules

1. **Check for a skill first.** Always.

2. **Skills are workflows.** Follow the steps in order. [bl: {SOFT}]
   Continuation line.

- **Verify:** the dry run is the gate. [bl: {KEEP}]
- **Comments:** only touch `new` ones. [bl: {GATE}]
"""

HEADER = "| Item | Tag | Why | Review | Delete when | Ablation |\n|---|---|---|---|---|---|\n"
ROWS = [
    ("1. Push Back", SOFT, "coaching", "2027-01-26", "an eval shows no change", ""),
    ("2. Verify", KEEP, "feedback signal", "", "", ""),
    ("2. Skills are workflows", SOFT, "rigid", "2027-01-26", "judgment suffices", ""),
    ("Verify: the dry run", KEEP, "build gate", "", "", ""),
    ("Comments:", GATE, "protocol", "2027-04-26", "", ""),
]


def sidecar(rows):
    return "# Bitter lesson: demo\n\n" + HEADER + "".join(f"| {' | '.join(r)} |\n" for r in rows)


class BitterLessonTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.skill = self.root / "skills" / "demo"
        self.skill.mkdir(parents=True)
        (self.root / bl.ALLOWLIST).write_text("# ratchet\nskills/demo\n")

    def write(self, rows=ROWS, skill=SKILL):
        (self.skill / "SKILL.md").write_text(skill)
        if rows is not None:
            (self.skill / bl.SIDECAR).write_text(sidecar(rows))

    def errors(self):
        return bl.check_skill(self.skill)

    def run_main(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = bl.main([*args, "--root", str(self.root)])
        return code, out.getvalue()

    def test_tagged_items_skip_frontmatter_and_fences(self):
        items, _ = bl.tagged_items(SKILL)
        self.assertEqual([(i["text"], i["tag"]) for i in items], [
            ("1. Push Back When Warranted", SOFT), ("2. Verify", KEEP),
            ("2. Skills are workflows. Follow the steps in order.", SOFT),
            ("Verify: the dry run is the gate.", KEEP), ("Comments: only touch new ones.", GATE)])

    def test_check_passes_when_tags_and_rows_match(self):
        self.write()
        self.assertEqual(self.errors(), [])

    def test_check_flags_missing_sidecar_and_no_tags(self):
        self.write(rows=None, skill="# Demo\n\n## Overview\n")
        errs = " ".join(self.errors())
        self.assertIn("no [bl: ...] tags", errs)
        self.assertIn("missing", errs)

    def test_check_flags_unknown_inline_tag(self):
        self.write(skill=SKILL.replace(f"[bl: {GATE}]", "[bl: maybe]"), rows=ROWS[:-1] + [("Comments:", GATE, "p", "2027-04-26", "", "")])
        errs = " ".join(self.errors())
        self.assertIn("tag must be one of", errs)
        self.assertIn("is tagged 'maybe' in SKILL.md", errs)

    def test_check_flags_tagged_item_without_row(self):
        self.write(rows=ROWS[1:])
        self.assertEqual(len(self.errors()), 1)
        self.assertIn("'1. Push Back When Warranted' has no row", self.errors()[0])

    def test_check_flags_stale_ambiguous_duplicate_and_mismatched_rows(self):
        extra = [("Gone", KEEP, "x", "", "", ""), ("2.", KEEP, "x", "", "", ""),
                 ("2. Verify", KEEP, "x", "", "", ""), ]
        self.write(rows=ROWS[:3] + [("Verify: the dry run", GATE, "x", "2027-01-01", "", "")] + ROWS[4:] + extra)
        errs = " ".join(self.errors())
        self.assertIn("stale row, no tagged item starts with 'Gone'", errs)
        self.assertIn("matches 2 tagged items", errs)
        self.assertIn("describes the same item", errs)
        self.assertIn(f"is tagged '{KEEP}' in SKILL.md but '{GATE}' here", errs)

    def test_check_enforces_required_fields_per_tag(self):
        cases = {"review": (GATE, "", ""), "delete-when": (SOFT, "2027-01-26", "")}
        for field, (tag, review, delete_when) in cases.items():
            with self.subTest(field=field):
                skill = SKILL.replace(f"### 2. Verify [bl: {KEEP}]", f"### 2. Verify [bl: {tag}]")
                rows = [r if r[0] != "2. Verify" else ("2. Verify", tag, "why", review, delete_when, "") for r in ROWS]
                self.write(rows=rows, skill=skill)
                self.assertEqual(len(self.errors()), 1)
                self.assertIn(f"needs {field}", self.errors()[0])

    def test_check_rejects_bad_date_and_missing_why(self):
        rows = [r if r[0] != "Comments:" else ("Comments:", GATE, "", "next week", "", "") for r in ROWS]
        self.write(rows=rows)
        errs = " ".join(self.errors())
        self.assertIn("needs a why", errs)
        self.assertIn("is not YYYY-MM-DD", errs)

    def test_main_check_exit_codes(self):
        self.write()
        self.assertEqual(self.run_main("check")[0], 0)
        self.write(rows=ROWS[1:])
        self.assertEqual(self.run_main("check")[0], 1)
        (self.root / bl.ALLOWLIST).write_text("# nothing yet\n")
        self.assertEqual(self.run_main("check")[0], 1)

    def test_report_reads_sidecar_only_and_flags_past_review(self):
        self.write()
        (self.skill / "SKILL.md").unlink()
        before = list(bl.report_rows(self.root, datetime.date(2026, 10, 26)))
        self.assertEqual(sorted(r["item"] for _, r, _ in before), ["1. Push Back", "2. Skills are workflows", "Comments:"])
        code, out = self.run_main("report", "--today", "2027-02-01")
        self.assertIn("2027-01-26 PAST", out)
        self.assertIn("2 past review", out)

    def test_ablate_lists_soft_and_past_review_items_with_text(self):
        self.write()
        items = bl.ablation_items(self.root, datetime.date(2026, 10, 26))
        self.assertEqual([i["item"] for i in items], ["1. Push Back", "2. Skills are workflows"])
        self.assertIn("You are not a yes-machine.", items[0]["text"])
        self.assertIn("## Example", items[0]["text"])
        self.assertIn("Continuation line.", items[1]["text"])
        self.assertNotIn("Verify:", items[1]["text"])
        later = [i["item"] for i in bl.ablation_items(self.root, datetime.date(2027, 5, 1))]
        self.assertIn("Comments:", later)
        code, out = self.run_main("ablate", "--format", "json")
        self.assertEqual(len(json.loads(out)), 2)


if __name__ == "__main__":
    unittest.main()
