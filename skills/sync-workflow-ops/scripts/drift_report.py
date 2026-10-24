#!/usr/bin/env python3
"""Report upstream drift and sync hygiene for every fork or mirror pair in a registry.

Read only. The only side effect is `--fetch`, which updates remote-tracking refs.
The registry is YAML (needs PyYAML) or JSON. See the skill's references/registry-format.md.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

SECURITY_HINT = re.compile(
    r"\b(security|cve-\d|ghsa-|vuln|exploit|rce|xss|csrf|ssrf|injection|leak|secret|credential|token|oauth|auth(?!or)\w*|bypass|sanitiz|traversal|sandbox|permission)",
    re.IGNORECASE,
)
SHA_RE = re.compile(r"\b[0-9a-f]{7,40}\b")
PIN_LINE_RE = re.compile(r"(?i)(pin|pinned|sha|commit)[^0-9a-f\n]*([0-9a-f]{7,40})\b")
MAX_SUBJECTS = 15
STALE_FETCH_DAYS = 7
CLASSES = {"V", "M", "P", "C", "R"}


@dataclass
class PairReport:
    id: str
    cls: str
    status: str
    direction: str = ""
    upstream_tip: str = ""
    upstream_tip_date: str = ""
    base: str = ""
    base_source: str = ""
    new_commits: int | None = None
    subjects: list[str] = field(default_factory=list)
    security_hints: list[str] = field(default_factory=list)
    new_tags: list[str] = field(default_factory=list)
    behind: int | None = None
    ahead: int | None = None
    unpushed: int | None = None
    dirty: bool | None = None
    skills_only_here: list[str] = field(default_factory=list)
    skills_only_there: list[str] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)
    default: str = ""
    upstream_label: str = ""
    our_copy: str = ""
    last_decision: str = ""
    next_action: str = ""
    owner: str = ""


def git(repo: Path, *args: str, check: bool = False) -> str | None:
    proc = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if proc.returncode != 0:
        if check:
            raise RuntimeError(proc.stderr.strip())
        return None
    return proc.stdout.strip()


def expand(p: str | None) -> Path | None:
    return Path(os.path.expanduser(p)) if p else None


def load_registry(path: Path) -> dict:
    text = path.read_text()
    if path.suffix in (".yaml", ".yml"):
        try:
            import yaml  # type: ignore
        except ImportError:
            sys.exit("drift-report: PyYAML is not installed. Install it or use a .json registry.")
        data = yaml.safe_load(text)
    else:
        data = json.loads(text)
    if not isinstance(data, dict) or not isinstance(data.get("pairs"), list):
        sys.exit("drift-report: registry needs a top-level 'pairs' list.")
    return data


def read_pin_file(pattern: str) -> tuple[str, str] | None:
    matches = sorted(glob.glob(os.path.expanduser(pattern), recursive=True))
    for m in matches:
        text = Path(m).read_text(errors="replace")
        hit = PIN_LINE_RE.search(text) or SHA_RE.search(text)
        if hit:
            sha = hit.group(2) if hit.re is PIN_LINE_RE else hit.group(0)
            return sha, m
    return None


def resolves(repo: Path, rev: str) -> bool:
    return git(repo, "rev-parse", "--verify", "--quiet", f"{rev}^{{commit}}") is not None


def fetch_age_days(repo: Path) -> float | None:
    gitdir = git(repo, "rev-parse", "--git-dir")
    if not gitdir:
        return None
    fh = (repo / gitdir / "FETCH_HEAD") if not os.path.isabs(gitdir) else Path(gitdir) / "FETCH_HEAD"
    if not fh.exists():
        return None
    return (time.time() - fh.stat().st_mtime) / 86400


def is_repo(p: Path | None) -> bool:
    return bool(p and p.exists() and git(p, "rev-parse", "--git-dir") is not None)


def check_upstream(pair: dict, rep: PairReport, do_fetch: bool) -> None:
    up = pair.get("upstream") or {}
    repo = expand(up.get("repo"))
    ref = up.get("ref")
    path = up.get("path")
    if not repo or not ref:
        if rep.status != "planned":
            rep.findings.append("no upstream repo/ref in registry")
        return
    if not is_repo(repo):
        url = up.get("url")
        if do_fetch and url:
            repo.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(["git", "clone", "--filter=blob:none", "--no-checkout", url, str(repo)],
                           capture_output=True, text=True)
        if not is_repo(repo):
            rep.findings.append(f"upstream clone missing: {repo}" + (" (run with --fetch)" if url else ""))
            return
    if do_fetch:
        remote = up.get("remote") or ref.split("/", 1)[0]
        if git(repo, "fetch", "--quiet", "--tags", remote) is None:
            rep.findings.append(f"fetch failed for remote '{remote}' (auth, or push/fetch disabled)")
    age = fetch_age_days(repo)
    if age is not None and age > STALE_FETCH_DAYS:
        rep.findings.append(f"upstream refs are {age:.0f} days old (run with --fetch)")
    if not resolves(repo, ref):
        rep.findings.append(f"upstream ref '{ref}' does not resolve in {repo}")
        return
    rep.upstream_tip = git(repo, "rev-parse", "--short", ref) or ""
    rep.upstream_tip_date = git(repo, "log", "-1", "--format=%cs", ref) or ""

    base, source = "", ""
    if pair.get("pin_file"):
        pin = read_pin_file(pair["pin_file"])
        if pin:
            base, source = pin[0], f"pin file {pin[1]}"
        else:
            rep.findings.append(f"pin file not found or has no SHA: {pair['pin_file']}")
    if not base and pair.get("reviewed_through"):
        base, source = str(pair["reviewed_through"]), "reviewed_through"
    if not base and pair.get("landed_through"):
        base, source = str(pair["landed_through"]), "landed_through"
    rep.base, rep.base_source = base, source

    scope = ["--", path] if path else []
    if base:
        if not resolves(repo, base):
            rep.findings.append(f"pin {base} not found in upstream clone (shallow clone, or wrong repo)")
            return
        rng = f"{base}..{ref}"
        rep.new_commits = int(git(repo, "rev-list", "--count", rng, *scope) or 0)
        tags = git(repo, "tag", "--contains", base, "--merged", ref, "--sort=-creatordate") or ""
        rep.new_tags = [t for t in tags.splitlines() if t and not resolves_same(repo, t, base)][:10]
    elif pair.get("since"):
        rng = ref
        rep.new_commits = int(git(repo, "rev-list", "--count", f"--since={pair['since']}", ref, *scope) or 0)
        rep.base_source = f"since {pair['since']}"
        rep.findings.append("no pin recorded, counting by date")
    else:
        rep.findings.append("no pin recorded (set reviewed_through)")
        return
    since_args = [f"--since={pair['since']}"] if not base and pair.get("since") else []
    log = git(repo, "log", "--no-merges", "--format=%h %cs %s", *since_args, rng, *scope) or ""
    lines = [ln for ln in log.splitlines() if ln]
    rep.subjects = lines[:MAX_SUBJECTS]
    rep.security_hints = [ln for ln in lines if SECURITY_HINT.search(ln.split(" ", 2)[-1])][:10]


def resolves_same(repo: Path, a: str, b: str) -> bool:
    return git(repo, "rev-parse", f"{a}^{{commit}}") == git(repo, "rev-parse", f"{b}^{{commit}}")


def check_downstream(pair: dict, rep: PairReport, identity: dict) -> None:
    down = pair.get("downstream") or {}
    repo = expand(down.get("repo"))
    if not repo:
        return
    if not is_repo(repo):
        if rep.status != "planned":
            rep.findings.append(f"downstream repo missing: {repo}")
        return
    rep.dirty = bool(git(repo, "status", "--porcelain", "--untracked-files=no"))
    up = git(repo, "rev-list", "--count", "@{u}..HEAD")
    rep.unpushed = int(up) if up is not None else None
    if rep.unpushed:
        rep.findings.append(f"{rep.unpushed} local commits not pushed")

    fork_ref = down.get("upstream_ref")
    if fork_ref and resolves(repo, fork_ref):
        lr = git(repo, "rev-list", "--left-right", "--count", f"{fork_ref}...HEAD")
        if lr:
            rep.behind, rep.ahead = (int(x) for x in lr.split())

    if pair.get("internal"):
        for name, url in remote_push_urls(repo):
            if url != "DISABLED" and (is_local_path(url) or "github.com" in url):
                rep.findings.append(f"LEAK RISK: internal repo remote '{name}' can push to {url} (set its push URL to DISABLED)")
    if pair.get("public"):
        if not has_pre_push(repo):
            rep.findings.append("public repo has no pre-push hook (install the scrub gate)")
        forbidden = identity.get("forbidden_email_patterns") or []
        own = f"{fork_ref}..HEAD" if fork_ref and resolves(repo, fork_ref) else "-200"
        emails = git(repo, "log", "--format=%ae%n%ce", own) or ""
        bad = sorted({e for e in emails.splitlines() if any(re.search(p, e) for p in forbidden)})
        if bad:
            rep.findings.append(f"IDENTITY LEAK: {len(bad)} non-public author/committer identities in our commits")


def remote_push_urls(repo: Path) -> list[tuple[str, str]]:
    out = git(repo, "remote", "-v") or ""
    return [(p[0], p[1]) for p in (ln.split() for ln in out.splitlines()) if len(p) >= 3 and p[2] == "(push)"]


def is_local_path(url: str) -> bool:
    return url.startswith("/") or url.startswith("file://") or url.startswith("~")


def has_pre_push(repo: Path) -> bool:
    hooks = git(repo, "config", "core.hooksPath")
    if hooks:
        hp = Path(os.path.expanduser(hooks))
        return (hp if hp.is_absolute() else repo / hp).joinpath("pre-push").exists()
    gitdir = git(repo, "rev-parse", "--git-common-dir") or ".git"
    gd = Path(gitdir) if os.path.isabs(gitdir) else repo / gitdir
    return (gd / "hooks" / "pre-push").exists()


def check_skills(pair: dict, rep: PairReport) -> None:
    cmp_ = pair.get("compare_skill_dirs")
    if not cmp_:
        return
    a, b = expand(cmp_.get("here")), expand(cmp_.get("there"))
    if not (a and b and a.is_dir() and b.is_dir()):
        rep.findings.append("compare_skill_dirs path missing")
        return
    strip = cmp_.get("strip_suffix", "")

    def names(d: Path) -> set[str]:
        out = set()
        for s in d.iterdir():
            if (s / "SKILL.md").exists():
                n = s.name
                out.add(n[: -len(strip)] if strip and n.endswith(strip) else n)
        return out

    here, there = names(a), names(b)
    rep.skills_only_here = sorted(here - there)
    rep.skills_only_there = sorted(there - here)


def pick_default(rep: PairReport) -> str:
    if rep.status == "planned":
        return "none (planned, not built)"
    if rep.status == "retire-candidate":
        return "name-only: retire?"
    leak = [f for f in rep.findings if f.startswith(("LEAK", "IDENTITY"))]
    if leak:
        return "fix leak risk first (safe: disable push URL / install hook)"
    if rep.status == "parked":
        return "defer (parked)" + ("; security hints need review" if rep.security_hints else "")
    if rep.security_hints:
        return f"review {len(rep.security_hints)} security hint(s), adopt real fixes"
    if rep.new_commits == 0:
        return "safe: nothing new, advance reviewed_through"
    if rep.new_commits is None:
        return "fix registry or clone (see findings)"
    return {
        "V": "draft subtree pull of latest release",
        "M": "draft merge of latest release tag",
        "P": f"review {rep.new_commits} commits, port PRD matches",
        "C": "promote or vendor missing items",
        "R": "name-only: retire?",
    }.get(rep.cls, "review")


def build_reports(reg: dict, do_fetch: bool, only: set[str]) -> list[PairReport]:
    identity = reg.get("identity") or {}
    reports = []
    for pair in reg["pairs"]:
        pid = str(pair.get("id", "?"))
        if only and pid not in only:
            continue
        cls = str(pair.get("class", "?")).upper()
        rep = PairReport(id=pid, cls=cls, status=str(pair.get("status", "active")),
                         direction=str(pair.get("direction", "")))
        if cls not in CLASSES:
            rep.findings.append(f"unknown class '{cls}' (use one of V M P C R)")
        check_upstream(pair, rep, do_fetch)
        check_downstream(pair, rep, identity)
        check_skills(pair, rep)
        rep.default = pick_default(rep)
        up, down = pair.get("upstream") or {}, pair.get("downstream") or {}
        rep.upstream_label = label(up.get("url") or up.get("repo"), up.get("ref"), up.get("path"))
        rep.our_copy = label(down.get("repo"), None, None) or "n/a"
        rep.last_decision = str(pair.get("last_decision") or "")
        rep.next_action = str(pair.get("next_action") or rep.default)
        rep.owner = str(pair.get("owner") or "")
        reports.append(rep)
    return reports


def label(location: str | None, ref: str | None, path: str | None) -> str:
    if not location:
        return ""
    name = str(location).rstrip("/").split("/")[-1].removesuffix(".git")
    return name + (f" {ref}" if ref else "") + (f" ({path})" if path else "")


def cell(text: str) -> str:
    return (text or "").replace("|", "/").replace("\n", " ")


def to_status_md(reports: list[PairReport], when: str) -> str:
    out = ["# Sync status", "",
           f"Regenerated by `drift_report.py --status-md` on {when}. Do not hand-edit:",
           "set `last_decision`, `next_action` and `owner` in the registry instead.", "",
           "| Pair | Upstream | Our copy | Direction | Pin or last sync | Drift | Last decision | Next action | Owner |",
           "|---|---|---|---|---|---|---|---|---|"]
    for r in reports:
        pin = f"`{r.base[:10]}` ({r.base_source})" if r.base else (r.base_source or "none")
        drift = "n/a" if r.new_commits is None else str(r.new_commits)
        if r.behind is not None:
            drift += f" (behind {r.behind}, ahead {r.ahead})"
        if any(f.startswith(("LEAK", "IDENTITY")) for f in r.findings):
            drift += ", leak risk"
        out.append("| " + " | ".join(cell(x) for x in (
            r.id, r.upstream_label or "n/a", r.our_copy, r.direction, pin, drift,
            r.last_decision or "none yet", r.next_action, r.owner or "unassigned")) + " |")
    return "\n".join(out) + "\n"


def to_markdown(reports: list[PairReport]) -> str:
    out = ["# Drift report", "", "| Pair | Class | Status | Upstream tip | Since pin | Behind/ahead | Default |",
           "|---|---|---|---|---|---|---|"]
    for r in reports:
        tip = f"{r.upstream_tip} ({r.upstream_tip_date})" if r.upstream_tip else "n/a"
        since = "n/a" if r.new_commits is None else f"{r.new_commits} new ({r.base_source})"
        ba = "n/a" if r.behind is None else f"{r.behind}/{r.ahead}"
        out.append(f"| {r.id} | {r.cls} | {r.status} | {tip} | {since} | {ba} | {r.default} |")
    for r in reports:
        if not (r.findings or r.security_hints or r.subjects or r.skills_only_here or r.skills_only_there):
            continue
        out += ["", f"## {r.id}"]
        out += [f"- finding: {f}" for f in r.findings]
        if r.new_tags:
            out.append(f"- new tags: {', '.join(r.new_tags)}")
        out += [f"- security hint: {s}" for s in r.security_hints]
        if r.subjects:
            out.append(f"- latest commits (up to {MAX_SUBJECTS}):")
            out += [f"  - {s}" for s in r.subjects]
        if r.skills_only_here or r.skills_only_there:
            out.append(f"- skills only here ({len(r.skills_only_here)}): {', '.join(r.skills_only_here[:20])}")
            out.append(f"- skills only there ({len(r.skills_only_there)}): {', '.join(r.skills_only_there[:20])}")
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--registry", default=os.environ.get("SYNC_WORKFLOW_REGISTRY"),
                    help="registry file (.yaml or .json); default $SYNC_WORKFLOW_REGISTRY")
    ap.add_argument("--fetch", action="store_true", help="fetch upstream remotes first (updates remote refs only)")
    ap.add_argument("--json", action="store_true", help="print JSON instead of markdown")
    ap.add_argument("--only", action="append", default=[], help="limit to a pair id (repeatable)")
    ap.add_argument("--status-md", help="also write the per-pair STATUS.md table to this path")
    args = ap.parse_args(argv)
    if not args.registry:
        ap.error("--registry or $SYNC_WORKFLOW_REGISTRY is required")
    reg = load_registry(Path(os.path.expanduser(args.registry)))
    reports = build_reports(reg, args.fetch, set(args.only))
    if args.status_md:
        Path(os.path.expanduser(args.status_md)).write_text(
            to_status_md(reports, time.strftime("%Y-%m-%d %H:%M %Z")))
    if args.json:
        print(json.dumps([r.__dict__ for r in reports], indent=2))
    else:
        sys.stdout.write(to_markdown(reports))
    return 0


if __name__ == "__main__":
    sys.exit(main())
