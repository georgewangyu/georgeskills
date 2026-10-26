#!/usr/bin/env python3
"""Check and report bitter-lesson tags.

SKILL.md carries short inline tags on relevant headings or numbered steps, for
example "### 3. Push Back When Warranted [bl: soft]". BITTER_LESSON.md next to it
holds the full analysis: one table row per tagged item, keyed by the first words
of the item (tag removed).

  bitter_lesson.py check  --root <pkg>   allowlisted skills; exit 1 on errors
  bitter_lesson.py report --root <pkg>   every sidecar under root: the cleanup list
  bitter_lesson.py ablate --root <pkg>   soft and past-review items with their text, for a with/without eval

Allowlist: <pkg>/bitter-lesson.allowlist, one skill folder per line ('#' comments).
"""
import argparse
import datetime
import json
import re
import sys
from pathlib import Path

# Tag vocabulary, least to most likely to be made unnecessary by a smarter model.
# name -> sidecar fields that tag requires. Renaming a tag is a one-line change here.
TAGS = {"invariant": frozenset(), "strong": frozenset({"review"}), "soft": frozenset({"review", "delete-when"})}
ORDER = list(TAGS)
ABLATE = ORDER[-1]  # tag whose items an ablation eval tests first

SIDECAR = "BITTER_LESSON.md"
ALLOWLIST = "bitter-lesson.allowlist"
COLUMNS = ("item", "tag", "why", "review", "delete-when", "ablation")
TAG = re.compile(r"\s*\[bl:\s*([^\]]*?)\s*\]")
HEADING = re.compile(r"^(#{1,6})\s+")
ITEM = re.compile(r"^\s*(?:[-*+]|\d+\.)\s+")
FENCE = re.compile(r"^\s*(```|~~~)")
CODE_SPAN = re.compile(r"`[^`]*`")  # tags inside inline code are mentions, not tags


def norm(text):
    text = re.sub(r"^\s*(#{1,6}|[-*+])\s+", "", text)
    return " ".join(text.replace("**", "").replace("`", "").replace("\\|", "|").split())


def starts_with_words(text, prefix):
    return bool(prefix) and (text == prefix or (text.startswith(prefix) and not text[len(prefix)].isalnum()))


def tagged_items(skill_text):
    """Return dicts(text, tag, start, end, line) for every tag outside frontmatter, code fences, and code spans."""
    lines = skill_text.splitlines()
    body = 0
    if lines and lines[0].strip() == "---":
        body = next((i + 1 for i in range(1, len(lines)) if lines[i].strip() == "---"), 0)
    items, in_fence = [], False
    for i in range(body, len(lines)):
        if FENCE.match(lines[i]):
            in_fence = not in_fence
            continue
        match = None if in_fence else TAG.search(CODE_SPAN.sub("", lines[i]))
        if not match:
            continue
        line = lines[i]
        items.append({"text": norm(line.replace(match.group(0), "", 1)), "tag": match.group(1), "line": i + 1,
                      "start": i, "end": _block_end(lines, i)})
    return items, lines


def _block_end(lines, start):
    """End of a tagged heading's section, or of a tagged list item or paragraph."""
    heading = HEADING.match(lines[start])
    if heading:
        level, in_fence = len(heading.group(1)), False
        for j in range(start + 1, len(lines)):
            if FENCE.match(lines[j]):
                in_fence = not in_fence
            other = None if in_fence else HEADING.match(lines[j])
            if other and len(other.group(1)) <= level:
                return j
        return len(lines)
    for j in range(start + 1, len(lines)):
        if not lines[j].strip() or HEADING.match(lines[j]) or (ITEM.match(lines[j]) and not lines[j].startswith(" ")):
            return j
    return len(lines)


def _cells(line):
    body = line.strip()
    body = body[1:] if body.startswith("|") else body
    body = body[:-1] if body.endswith("|") and not body.endswith("\\|") else body
    return [c.strip() for c in re.split(r"(?<!\\)\|", body)]


def parse_sidecar(text):
    """Return row dicts from the first table whose header matches COLUMNS."""
    rows, in_table = [], False
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip().startswith("|"):
            if in_table:
                break
            continue
        cells = _cells(line)
        if not in_table:
            in_table = tuple(c.lower().replace(" ", "-") for c in cells) == COLUMNS
            continue
        if all(set(c) <= set("-: ") for c in cells):
            continue
        cells += [""] * (len(COLUMNS) - len(cells))
        row = dict(zip(COLUMNS, cells))
        row["line"] = number
        rows.append(row)
    return rows


def _date(value):
    try:
        return datetime.date.fromisoformat(value)
    except ValueError:
        return None


def match_rows(rows, items):
    """Map each row index to the tagged items its key matches."""
    return {n: [it for it in items if starts_with_words(it["text"], norm(row["item"]))] for n, row in enumerate(rows)}


def check_skill(skill_dir):
    """Return a list of error strings for one skill folder."""
    skill_dir = Path(skill_dir)
    skill_md, sidecar = skill_dir / "SKILL.md", skill_dir / SIDECAR
    if not skill_md.is_file():
        return [f"{skill_md}: missing"]
    items, _ = tagged_items(skill_md.read_text(encoding="utf-8"))
    errors = [f"{skill_md}:{it['line']}: tag must be one of {ORDER}, got {it['tag']!r}"
              for it in items if it["tag"] not in TAGS]
    if not items:
        errors.append(f"{skill_md}: no [bl: ...] tags")
    if not sidecar.is_file():
        return errors + [f"{sidecar}: missing"]
    rows = parse_sidecar(sidecar.read_text(encoding="utf-8"))
    if not rows:
        return errors + [f"{sidecar}: no table with columns {' | '.join(COLUMNS)}"]
    claimed = {}
    for n, matched in match_rows(rows, items).items():
        row = rows[n]
        where, key, tag = f"{sidecar}:{row['line']}", row["item"], row["tag"]
        if not matched:
            errors.append(f"{where}: stale row, no tagged item starts with '{key}'")
        elif len(matched) > 1:
            errors.append(f"{where}: '{key}' matches {len(matched)} tagged items; add words")
        else:
            item = matched[0]
            if item["line"] in claimed:
                errors.append(f"{where}: '{key}' describes the same item as line {claimed[item['line']]}")
            claimed[item["line"]] = row["line"]
            if item["tag"] != tag:
                errors.append(f"{where}: '{key}' is tagged {item['tag']!r} in SKILL.md but {tag!r} here")
        if tag not in TAGS:
            errors.append(f"{where}: tag must be one of {ORDER}, got {tag!r}")
            continue
        if not row["why"]:
            errors.append(f"{where}: '{key}' needs a why")
        if row["review"] and not _date(row["review"]):
            errors.append(f"{where}: review date {row['review']!r} is not YYYY-MM-DD")
        for field in sorted(TAGS[tag]):
            if not row[field]:
                errors.append(f"{where}: {tag} '{key}' needs {field}")
    for item in items:
        if item["line"] not in claimed:
            errors.append(f"{skill_md}:{item['line']}: tagged item '{item['text']}' has no row in {SIDECAR}")
    return errors


def read_allowlist(root):
    path = Path(root) / ALLOWLIST
    if not path.is_file():
        return []
    entries = (line.split("#", 1)[0].strip() for line in path.read_text(encoding="utf-8").splitlines())
    return [Path(root) / e for e in entries if e]


def report_rows(root, today):
    """Yield (sidecar, row, overdue) for every row above the lowest tag, reading sidecars only."""
    for sidecar in sorted(Path(root).rglob(SIDECAR)):
        for row in parse_sidecar(sidecar.read_text(encoding="utf-8")):
            if row["tag"] == ORDER[0]:
                continue
            review = _date(row["review"])
            yield sidecar, row, bool(review and review <= today)


def ablation_items(root, today):
    """Rows to test with and without: every soft row plus any row past its review date, with SKILL.md text."""
    out = []
    for sidecar, row, overdue in report_rows(root, today):
        if row["tag"] != ABLATE and not overdue:
            continue
        text, lines_ref = "", None
        skill_md = sidecar.parent / "SKILL.md"
        if skill_md.is_file():
            items, lines = tagged_items(skill_md.read_text(encoding="utf-8"))
            matched = [it for it in items if starts_with_words(it["text"], norm(row["item"]))]
            if len(matched) == 1:
                it = matched[0]
                text, lines_ref = "\n".join(lines[it["start"]:it["end"]]).strip(), [it["start"] + 1, it["end"]]
        out.append({"skill": str(sidecar.parent.relative_to(root)), "item": row["item"], "tag": row["tag"],
                    "review": row["review"], "overdue": overdue, "delete-when": row["delete-when"],
                    "ablation": row["ablation"], "lines": lines_ref, "text": text})
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=("check", "report", "ablate"))
    ap.add_argument("--root", default=".", help="package root")
    ap.add_argument("--today", type=datetime.date.fromisoformat, default=datetime.date.today())
    ap.add_argument("--format", choices=("markdown", "json"), default="markdown", help="ablate output")
    a = ap.parse_args(argv)
    root = Path(a.root).resolve()
    if a.mode == "check":
        skills = read_allowlist(root)
        if not skills:
            print(f"bitter-lesson: no skills in {root / ALLOWLIST}", file=sys.stderr)
            return 1
        errors = [e for s in skills for e in check_skill(s)]
        for e in errors:
            print(e, file=sys.stderr)
        print(f"bitter-lesson check: {len(skills)} skill(s), {len(errors)} error(s)")
        return 1 if errors else 0
    if a.mode == "ablate":
        items = ablation_items(root, a.today)
        if a.format == "json":
            print(json.dumps(items, indent=2))
            return 0
        print(f"# Ablation candidates as of {a.today}: {len(items)} item(s)\n")
        print("Run the eval with and without each item. Record the result in the Ablation column.")
        print("No difference: delete the item. Run on a new model release, a passed review date,")
        print("or when a strong item becomes a hard check.\n")
        for it in items:
            where = f", SKILL.md lines {it['lines'][0]}-{it['lines'][1]}" if it["lines"] else ""
            print(f"## {it['skill']}: {it['item']}\n")
            print(f"- tag: {it['tag']}, review: {it['review']}{' (past)' if it['overdue'] else ''}{where}")
            print(f"- delete when: {it['delete-when'] or '(none)'}")
            print(f"- last ablation: {it['ablation'] or '(not run)'}\n")
            if it["text"]:
                print("\n".join("> " + line for line in it["text"].splitlines()) + "\n")
        return 0
    rows = list(report_rows(root, a.today))
    rank = {k: n for n, k in enumerate(reversed(ORDER))}
    rows.sort(key=lambda r: (not r[2], rank.get(r[1]["tag"], -1), r[1]["review"] or "9999"))
    overdue = sum(1 for _, _, o in rows if o)
    print(f"bitter-lesson report for {root} as of {a.today}: {len(rows)} item(s), {overdue} past review")
    print("| Skill | Item | Tag | Review | Delete when | Ablation |")
    print("|---|---|---|---|---|---|")
    for sidecar, row, is_overdue in rows:
        review = f"{row['review']} PAST" if is_overdue else row["review"]
        print(f"| {sidecar.parent.relative_to(root)} | {row['item']} | {row['tag']} | {review} "
              f"| {row['delete-when']} | {row['ablation']} |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
