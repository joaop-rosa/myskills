"""Testes unitários para comandos `add` e `pull` da CLI."""

from __future__ import annotations

import argparse
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from skills_cli import commands
from skills_cli.git_client import GitCommandResult
from tests.fakes import FakeGitClient


def _write_skill(skill_dir: Path, name: str) -> None:
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(f"---\nname: {name}\ndescription: ok\n---\n", encoding="utf-8")


class CommandTests(unittest.TestCase):
    """Valida regras de proteção em `cmd_add` e fluxo `cmd_pull`."""

    def test_cmd_add_rejects_reserved_group_name_expo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_name:
            skills_dir = Path(tmp_name) / "skills"
            skills_dir.mkdir()
            exit_code = commands.cmd_add(argparse.Namespace(name="expo"), skills_dir=skills_dir)
            self.assertEqual(exit_code, 1)
            self.assertFalse((skills_dir / "expo").exists())

    def test_cmd_add_rejects_collision_with_nested_expo_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_name:
            skills_dir = Path(tmp_name) / "skills"
            _write_skill(skills_dir / "expo" / "expo-router", "expo-router")
            exit_code = commands.cmd_add(argparse.Namespace(name="expo-router"), skills_dir=skills_dir)
            self.assertEqual(exit_code, 1)
            self.assertFalse((skills_dir / "expo-router").exists())

    def test_cmd_add_creates_custom_skill_scaffold(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_name:
            skills_dir = Path(tmp_name) / "skills"
            skills_dir.mkdir()
            exit_code = commands.cmd_add(argparse.Namespace(name="minha-skill"), skills_dir=skills_dir)
            self.assertEqual(exit_code, 0)
            self.assertTrue((skills_dir / "minha-skill" / "SKILL.md").is_file())

    def _run_pull_with_patched_dirs(
        self,
        repo_root: Path,
        skills_dir: Path,
        gemini_dir: Path,
        claude_dir: Path,
        client: FakeGitClient,
    ) -> int:
        with (
            patch.object(commands, "REPO_ROOT", repo_root),
            patch.object(commands, "SKILLS_DIR", skills_dir),
            patch.object(commands, "GEMINI_GLOBAL_DIR", gemini_dir),
            patch.object(commands, "CLAUDE_GLOBAL_DIR", claude_dir),
        ):
            return commands.cmd_pull(argparse.Namespace(agent="all"), git_client=client)

    def test_cmd_pull_runs_fast_forward_and_repairs_symlinks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_name:
            root = Path(tmp_name)
            repo_root = root / "repo"
            expo_skill = repo_root / "skills" / "expo" / "expo-router"
            _write_skill(expo_skill, "expo-router")
            gemini_dir, claude_dir = root / "gemini", root / "claude"
            gemini_dir.mkdir()
            (gemini_dir / "expo-router").symlink_to(repo_root / "skills" / "expo-router")
            client = FakeGitClient()
            exit_code = self._run_pull_with_patched_dirs(repo_root, repo_root / "skills", gemini_dir, claude_dir, client)
            self.assertEqual(exit_code, 0)
            self.assertEqual(client.pull_calls, [repo_root])
            self.assertEqual((gemini_dir / "expo-router").resolve(), expo_skill.resolve())
            self.assertEqual((claude_dir / "expo-router").resolve(), expo_skill.resolve())

    def test_cmd_pull_returns_error_when_git_pull_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_name:
            repo_root = Path(tmp_name) / "repo"
            repo_root.mkdir()
            failing_client = FakeGitClient(
                pull_result=GitCommandResult(1, "", "fatal: Not possible to fast-forward, aborting.\n")
            )
            with patch.object(commands, "REPO_ROOT", repo_root):
                exit_code = commands.cmd_pull(argparse.Namespace(agent="all"), git_client=failing_client)
            self.assertEqual(exit_code, 1)
            self.assertEqual(failing_client.pull_calls, [repo_root])
