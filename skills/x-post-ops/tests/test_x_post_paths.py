from __future__ import annotations

import argparse
import importlib.util
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"


def load_script(name: str):
    path = SCRIPT_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


generate_x_posts = load_script("generate_x_posts")
post_to_x = load_script("post_to_x")


class GeneratePathsTest(unittest.TestCase):
    def test_private_repo_builds_default_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            args = argparse.Namespace(
                date="2026-07-11",
                private_repo=tmp,
                summary_path=None,
                feed_path=None,
            )
            _, summary, feed = generate_x_posts.resolve_inputs(args)
            root = Path(tmp).resolve()
            self.assertEqual(
                summary,
                root / "journal/summaries/2026/07/2026-07-11_Summary.md",
            )
            self.assertEqual(
                feed,
                root
                / "notes-private"
                / "social-media"
                / "x"
                / "home"
                / "latest.json",
            )

    def test_explicit_inputs_do_not_require_private_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = argparse.Namespace(
                date="2026-07-11",
                private_repo=None,
                summary_path=str(root / "summary.md"),
                feed_path=str(root / "feed.json"),
            )
            with mock.patch.dict(
                os.environ,
                {"LIFEREPO_PRIVATE_ROOT": "", "PRIVATE_REPO_ROOT": ""},
            ):
                _, summary, feed = generate_x_posts.resolve_inputs(args)
            self.assertEqual(summary, (root / "summary.md").resolve())
            self.assertEqual(feed, (root / "feed.json").resolve())


class TokenPathsTest(unittest.TestCase):
    def test_private_repo_infers_token_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            token_file = post_to_x.resolve_token_file(None, tmp)
            self.assertEqual(
                token_file,
                Path(tmp).resolve() / ".tokens/x-twitter.env",
            )

    def test_bird_inherits_process_env_and_overlays_token_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "x.env"
            token_file.write_text("EXAMPLE_TOKEN=fixture\n", encoding="utf-8")
            completed = subprocess.CompletedProcess([], 0, "", "")
            with mock.patch.object(
                post_to_x.subprocess,
                "run",
                return_value=completed,
            ) as run:
                post_to_x.run_bird(["whoami"], token_file)
            child_env = run.call_args.kwargs["env"]
            self.assertIn("PATH", child_env)
            self.assertEqual(child_env["EXAMPLE_TOKEN"], "fixture")


if __name__ == "__main__":
    unittest.main()
