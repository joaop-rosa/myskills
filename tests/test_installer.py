"""Testes unitários para instalação, relink automático e limpeza de symlinks."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from skills_cli.installer import (
    import_untracked_skills,
    inspect_global_dir_health,
    install_skill_to_dir,
    prune_broken_repo_symlinks,
)
from skills_cli.models import TargetDirectory


def _create_skill_dir(base_dir: Path, body: str = "skill") -> Path:
    base_dir.mkdir(parents=True, exist_ok=True)
    (base_dir / "SKILL.md").write_text(f"---\nname: {base_dir.name}\ndescription: test\n---\n{body}\n", encoding="utf-8")
    return base_dir


class InstallerTests(unittest.TestCase):
    """Valida regras de symlink, cópia, relink automático e importação segura."""

    def test_installs_symlink_and_copy_modes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_name:
            root = Path(tmp_name)
            repo_skill = _create_skill_dir(root / "repo" / "skills" / "expo" / "expo-ui")
            sym_dest = root / "sym"
            copy_dest = root / "copy"
            self.assertTrue(install_skill_to_dir(repo_skill, sym_dest, root / "repo", mode="symlink"))
            self.assertTrue(install_skill_to_dir(repo_skill, copy_dest, root / "repo", mode="copy"))
            self.assertTrue((sym_dest / "expo-ui").is_symlink())
            self.assertEqual((sym_dest / "expo-ui").resolve(), repo_skill.resolve())
            self.assertFalse((copy_dest / "expo-ui").is_symlink())
            self.assertTrue((copy_dest / "expo-ui" / "SKILL.md").is_file())

    def test_relinks_broken_moved_repo_symlink_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_name:
            root = Path(tmp_name)
            repo_root = root / "repo"
            new_skill = _create_skill_dir(repo_root / "skills" / "expo" / "expo-router")
            dest_dir = root / "gemini"
            dest_dir.mkdir(parents=True)
            (dest_dir / "expo-router").symlink_to(repo_root / "skills" / "expo-router")
            self.assertTrue(install_skill_to_dir(new_skill, dest_dir, repo_root, force=False))
            self.assertEqual((dest_dir / "expo-router").resolve(), new_skill.resolve())

    def test_relinks_live_stale_repo_symlink_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_name:
            root = Path(tmp_name)
            repo_root = root / "repo"
            old_skill = _create_skill_dir(repo_root / "skills" / "expo-router")
            new_skill = _create_skill_dir(repo_root / "skills" / "expo" / "expo-router")
            dest_dir = root / "claude"
            dest_dir.mkdir(parents=True)
            (dest_dir / "expo-router").symlink_to(old_skill)
            self.assertTrue(install_skill_to_dir(new_skill, dest_dir, repo_root, force=False))
            self.assertEqual((dest_dir / "expo-router").resolve(), new_skill.resolve())

    def test_preserves_live_external_symlink_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_name:
            root = Path(tmp_name)
            repo_root = root / "repo"
            repo_skill = _create_skill_dir(repo_root / "skills" / "expo" / "expo-ui")
            external_skill = _create_skill_dir(root / "external" / "expo-ui")
            dest_dir = root / "gemini"
            dest_dir.mkdir(parents=True)
            (dest_dir / "expo-ui").symlink_to(external_skill)
            self.assertFalse(install_skill_to_dir(repo_skill, dest_dir, repo_root, force=False))
            self.assertEqual((dest_dir / "expo-ui").resolve(), external_skill.resolve())
            self.assertTrue(install_skill_to_dir(repo_skill, dest_dir, repo_root, force=True))
            self.assertEqual((dest_dir / "expo-ui").resolve(), repo_skill.resolve())

    def test_prunes_only_broken_symlinks_pointing_inside_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_name:
            root = Path(tmp_name)
            repo_root = root / "repo"
            repo_root.mkdir()
            dest_dir = root / "gemini"
            dest_dir.mkdir()
            (dest_dir / "expo-removed").symlink_to(repo_root / "skills" / "expo" / "expo-removed")
            (dest_dir / "external-broken").symlink_to(root / "other" / "missing-skill")
            pruned = prune_broken_repo_symlinks(dest_dir, repo_root)
            self.assertEqual(pruned, ["expo-removed"])
            self.assertFalse((dest_dir / "expo-removed").is_symlink())
            self.assertTrue((dest_dir / "external-broken").is_symlink())

    def test_import_untracked_skills_skips_known_expo_names(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_name:
            root = Path(tmp_name)
            skills_dir = root / "repo" / "skills"
            skills_dir.mkdir(parents=True)
            gemini_dir = root / "gemini"
            _create_skill_dir(gemini_dir / "nova-custom")
            _create_skill_dir(gemini_dir / "expo-router")
            known = {"expo-router"}
            imported = import_untracked_skills([TargetDirectory("gemini", gemini_dir)], skills_dir, known)
            self.assertEqual(imported, ["nova-custom"])
            self.assertTrue((skills_dir / "nova-custom" / "SKILL.md").is_file())
            self.assertTrue((gemini_dir / "nova-custom").is_symlink())
            self.assertFalse((gemini_dir / "expo-router").is_symlink())
            health = inspect_global_dir_health(gemini_dir)
            self.assertEqual((health.active_links, health.copies, health.broken_links), (1, 1, 0))
