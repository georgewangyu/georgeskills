from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"


def load_script(name: str):
    path = SCRIPTS / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


prepare = load_script("prepare_capcut_draft")
migrate = load_script("migrate_capcut_draft_name")


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{json.dumps(payload)}\n", encoding="utf-8")


class PrepareCapCutDraftTests(unittest.TestCase):
    def test_rejects_nonempty_template(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            template = Path(temporary)
            write_json(template / "draft_content.json", {"duration": 10, "tracks": []})

            with self.assertRaisesRegex(RuntimeError, "Template is not empty"):
                prepare.verify_empty_template(template)

    def test_apply_verifies_target_before_writing_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = root / "2026-07-10_test-video"
            drafts = root / "drafts"
            template = drafts / "empty-template"
            capcutbot = root / "capcutbot"
            project.mkdir()
            template.mkdir(parents=True)
            (capcutbot / "src").mkdir(parents=True)
            write_json(template / "draft_content.json", {"duration": 0, "tracks": []})
            (capcutbot / "src" / "cli.js").write_text("// mock\n", encoding="utf-8")
            target = drafts / project.name

            args = argparse.Namespace(
                project_dir=project,
                drafts_root=drafts,
                empty_template="empty-template",
                capcutbot_dir=capcutbot,
                dry_run=False,
                apply=True,
            )

            def duplicate(*_args, **_kwargs):
                shutil.copytree(template, target)
                return subprocess.CompletedProcess([], 0, stdout="{}", stderr="")

            with patch.object(prepare, "parse_args", return_value=args), patch.object(
                prepare, "capcut_is_open", return_value=(False, "mock")
            ), patch.object(prepare.subprocess, "run", side_effect=duplicate):
                output = prepare.run()

            receipt = project / "editor-projects" / "capcut-draft.json"
            self.assertTrue(target.is_dir())
            self.assertTrue(receipt.is_file())
            self.assertEqual(output["status"] if "status" in output else output["mode"], "apply")
            self.assertEqual(
                Path(output["created_draft_file"]),
                (target / "draft_content.json").resolve(),
            )

    def test_apply_rejects_missing_target_after_cli_success(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = root / "2026-07-10_test-video"
            drafts = root / "drafts"
            template = drafts / "empty-template"
            capcutbot = root / "capcutbot"
            project.mkdir()
            template.mkdir(parents=True)
            (capcutbot / "src").mkdir(parents=True)
            write_json(template / "draft_content.json", {"duration": 0, "tracks": []})
            (capcutbot / "src" / "cli.js").write_text("// mock\n", encoding="utf-8")
            args = argparse.Namespace(
                project_dir=project,
                drafts_root=drafts,
                empty_template="empty-template",
                capcutbot_dir=capcutbot,
                dry_run=False,
                apply=True,
            )
            success = subprocess.CompletedProcess([], 0, stdout="{}", stderr="")

            with patch.object(prepare, "parse_args", return_value=args), patch.object(
                prepare, "capcut_is_open", return_value=(False, "mock")
            ), patch.object(prepare.subprocess, "run", return_value=success):
                with self.assertRaisesRegex(RuntimeError, "did not create the target draft"):
                    prepare.run()

            self.assertFalse((project / "editor-projects" / "capcut-draft.json").exists())


class MigrateCapCutDraftTests(unittest.TestCase):
    def build_fixture(self, root: Path):
        drafts = root / "drafts"
        source = drafts / "0710"
        target = drafts / "2026-07-10_test-video"
        project = root / target.name
        backup = root / "backups"
        source.mkdir(parents=True)
        project.mkdir()
        write_json(
            source / "draft_meta_info.json",
            {"draft_name": "0710", "draft_fold_path": str(source)},
        )
        write_json(source / "nested.json", {"media": f"{source}/clip.mp4"})
        return drafts, source, target, project, backup

    def test_dry_run_does_not_mutate_draft(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            drafts, source, target, project, backup = self.build_fixture(Path(temporary))
            args = argparse.Namespace(
                drafts_root=drafts,
                current_name="0710",
                canonical_name=target.name,
                project_dir=project,
                backup_root=backup,
                dry_run=True,
                apply=False,
            )
            with patch.object(migrate, "parse_args", return_value=args), patch.object(
                migrate, "capcut_is_open", return_value=False
            ):
                output = migrate.run()

            self.assertEqual(output["mode"], "dry-run")
            self.assertTrue(source.is_dir())
            self.assertFalse(target.exists())
            self.assertFalse(backup.exists())

    def test_apply_preserves_backup_and_updates_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            drafts, source, target, project, backup = self.build_fixture(Path(temporary))
            args = argparse.Namespace(
                drafts_root=drafts,
                current_name="0710",
                canonical_name=target.name,
                project_dir=project,
                backup_root=backup,
                dry_run=False,
                apply=True,
            )
            with patch.object(migrate, "parse_args", return_value=args), patch.object(
                migrate, "capcut_is_open", return_value=False
            ):
                output = migrate.run()

            metadata = json.loads((target / "draft_meta_info.json").read_text())
            nested = json.loads((target / "nested.json").read_text())
            self.assertFalse(source.exists())
            self.assertTrue(Path(output["backup_path"]).is_dir())
            self.assertEqual(metadata["draft_name"], target.name)
            self.assertEqual(Path(metadata["draft_fold_path"]), target.resolve())
            self.assertEqual(Path(nested["media"]).resolve(), (target / "clip.mp4").resolve())
            self.assertTrue(
                (project / "editor-projects" / "capcut-draft-migration.json").is_file()
            )


if __name__ == "__main__":
    unittest.main()
