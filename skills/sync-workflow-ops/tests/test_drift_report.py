import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import drift_report as dr  # noqa: E402

ENV = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
       "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com",
       "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}


def sh(cwd, *args, env=None):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True,
                          env=env or ENV).stdout.strip()


def commit(repo, name, msg, env=None):
    (Path(repo) / name).write_text(msg)
    sh(repo, "add", name)
    sh(repo, "commit", "-qm", msg, env=env)
    return sh(repo, "rev-parse", "HEAD")


class DriftReportTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.up = self.tmp / "up"
        self.up.mkdir()
        sh(self.up, "init", "-q", "-b", "main")
        self.pin = commit(self.up, "a.txt", "initial")
        commit(self.up, "b.txt", "add feature")
        commit(self.up, "c.txt", "fix auth bypass in login")
        self.down = self.tmp / "down"
        sh(self.tmp, "clone", "-q", str(self.up), str(self.down))

    def report(self, pair, identity=None):
        reg = {"pairs": [pair], "identity": identity or {}}
        return dr.build_reports(reg, do_fetch=False, only=set())[0]

    def test_counts_new_commits_and_flags_security_since_pin(self):
        r = self.report({"id": "p", "class": "P", "reviewed_through": self.pin,
                         "upstream": {"repo": str(self.up), "ref": "main"}})
        self.assertEqual(r.new_commits, 2)
        self.assertEqual(len(r.security_hints), 1)
        self.assertIn("auth bypass", r.security_hints[0])
        self.assertTrue(r.default.startswith("review 1 security"))

    def test_pin_file_overrides_reviewed_through(self):
        pin_file = self.tmp / "UPSTREAM.md"
        head = sh(self.up, "rev-parse", "HEAD")
        pin_file.write_text(f"# Upstream\n\nPinned SHA: {head}\n")
        r = self.report({"id": "p", "class": "V", "reviewed_through": self.pin, "pin_file": str(pin_file),
                         "upstream": {"repo": str(self.up), "ref": "main"}})
        self.assertEqual(r.new_commits, 0)
        self.assertEqual(r.default, "safe: nothing new, advance reviewed_through")

    def test_missing_pin_is_a_finding(self):
        r = self.report({"id": "p", "class": "P", "upstream": {"repo": str(self.up), "ref": "main"}})
        self.assertIsNone(r.new_commits)
        self.assertIn("no pin recorded (set reviewed_through)", r.findings)

    def test_unknown_pin_reports_shallow_or_wrong_repo(self):
        r = self.report({"id": "p", "class": "P", "reviewed_through": "deadbeefdeadbeef",
                         "upstream": {"repo": str(self.up), "ref": "main"}})
        self.assertTrue(any("not found in upstream clone" in f for f in r.findings))

    def test_internal_repo_with_pushable_local_remote_is_leak_risk(self):
        r = self.report({"id": "p", "class": "P", "internal": True, "reviewed_through": self.pin,
                         "upstream": {"repo": str(self.up), "ref": "main"},
                         "downstream": {"repo": str(self.down)}})
        self.assertTrue(any(f.startswith("LEAK RISK") for f in r.findings))
        self.assertTrue(r.default.startswith("fix leak risk"))
        sh(self.down, "remote", "set-url", "--push", "origin", "DISABLED")
        r2 = self.report({"id": "p", "class": "P", "internal": True, "reviewed_through": self.pin,
                          "upstream": {"repo": str(self.up), "ref": "main"},
                          "downstream": {"repo": str(self.down)}})
        self.assertFalse(any(f.startswith("LEAK RISK") for f in r2.findings))

    def test_public_repo_flags_missing_hook_and_bad_identity_in_own_commits(self):
        bad_env = {**ENV, "GIT_AUTHOR_EMAIL": "blocked-me@example.com"}
        commit(self.down, "d.txt", "our change", env=bad_env)
        pair = {"id": "p", "class": "M", "public": True, "reviewed_through": self.pin,
                "upstream": {"repo": str(self.up), "ref": "main"},
                "downstream": {"repo": str(self.down), "upstream_ref": "origin/main"}}
        r = self.report(pair, identity={"forbidden_email_patterns": [r"^blocked-"]})
        self.assertIn("public repo has no pre-push hook (install the scrub gate)", r.findings)
        self.assertTrue(any(f.startswith("IDENTITY LEAK") for f in r.findings))
        self.assertEqual((r.behind, r.ahead), (0, 1))
        self.assertEqual(r.unpushed, 1)

    def test_upstream_authors_are_not_identity_leaks(self):
        corp = {**ENV, "GIT_AUTHOR_EMAIL": "blocked-dev@example.com", "GIT_COMMITTER_EMAIL": "blocked-dev@example.com"}
        commit(self.up, "e.txt", "upstream work", env=corp)
        sh(self.down, "fetch", "-q", "origin")
        pair = {"id": "p", "class": "M", "public": True, "reviewed_through": self.pin,
                "upstream": {"repo": str(self.up), "ref": "main"},
                "downstream": {"repo": str(self.down), "upstream_ref": "origin/main"}}
        r = self.report(pair, identity={"forbidden_email_patterns": [r"^blocked-"]})
        self.assertFalse(any(f.startswith("IDENTITY LEAK") for f in r.findings))
        self.assertEqual(r.behind, 1)

    def test_parked_and_planned_and_retire_defaults(self):
        base = {"class": "M", "reviewed_through": self.pin, "upstream": {"repo": str(self.up), "ref": "main"}}
        self.assertTrue(self.report({**base, "id": "a", "status": "parked"}).default.startswith("defer"))
        self.assertEqual(self.report({"id": "b", "class": "V", "status": "planned"}).default,
                         "none (planned, not built)")
        self.assertEqual(self.report({**base, "id": "c", "status": "retire-candidate"}).default,
                         "name-only: retire?")

    def test_skill_dir_compare_strips_suffix(self):
        here, there = self.tmp / "here", self.tmp / "there"
        for root, names in ((here, ["alpha", "beta"]), (there, ["alpha-ops", "gamma-ops"])):
            for n in names:
                (root / n).mkdir(parents=True)
                (root / n / "SKILL.md").write_text("x")
        r = self.report({"id": "c", "class": "C", "status": "active", "since": "2000-01-01",
                         "upstream": {"repo": str(self.up), "ref": "main"},
                         "compare_skill_dirs": {"here": str(here), "there": str(there), "strip_suffix": "-ops"}})
        self.assertEqual(r.skills_only_here, ["beta"])
        self.assertEqual(r.skills_only_there, ["gamma"])

    def test_cli_json_and_markdown(self):
        reg = self.tmp / "reg.json"
        reg.write_text(json.dumps({"pairs": [{"id": "p", "class": "P", "reviewed_through": self.pin,
                                              "upstream": {"repo": str(self.up), "ref": "main"}}]}))
        out = subprocess.run([sys.executable, str(Path(dr.__file__)), "--registry", str(reg), "--json"],
                             capture_output=True, text=True, check=True).stdout
        self.assertEqual(json.loads(out)[0]["new_commits"], 2)
        md = subprocess.run([sys.executable, str(Path(dr.__file__)), "--registry", str(reg)],
                            capture_output=True, text=True, check=True).stdout
        self.assertIn("| p | P | active |", md)


if __name__ == "__main__":
    unittest.main()
