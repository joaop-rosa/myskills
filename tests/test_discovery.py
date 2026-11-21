"""Testes unitários para descoberta de skills e parsing de frontmatter."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from skills_cli.discovery import discover_repo_skills, find_skill_by_name, parse_frontmatter


def _write_skill(skill_dir: Path, name: str, description: str) -> None:
    skill_dir.mkdir(parents=True, exist_ok=True)
    content = f"---\nname: {name}\ndescription: >-\n  {description}\n---\n\n# {name}\n"
    (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")


class DiscoveryTests(unittest.TestCase):
    """Garante descoberta de skills customizadas e agrupadas em subpastas."""

    def test_discovers_flat_custom_and_nested_expo_skills(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_name:
            skills_dir = Path(tmp_name) / "skills"
            _write_skill(skills_dir / "git-commit", "git-commit", "Commits padronizados.")
            _write_skill(skills_dir / "expo" / "expo-router", "expo-router", "Rotas no Expo.")
            entries = discover_repo_skills(skills_dir)
            by_name = {entry.name: entry for entry in entries}
            self.assertEqual(set(by_name.keys()), {"git-commit", "expo-router"})
            self.assertEqual(by_name["git-commit"].category, "custom")
            self.assertEqual(by_name["expo-router"].category, "expo")
            self.assertEqual(by_name["expo-router"].path, skills_dir / "expo" / "expo-router")

    def test_ignores_hidden_directories_and_non_skill_folders(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_name:
            skills_dir = Path(tmp_name) / "skills"
            (skills_dir / ".hidden").mkdir(parents=True)
            (skills_dir / "empty-group").mkdir(parents=True)
            _write_skill(skills_dir / "expo" / ".draft", "draft", "Ignorado.")
            _write_skill(skills_dir / "expo" / "eas-update", "eas-update", "Atualizações OTA.")
            entries = discover_repo_skills(skills_dir)
            self.assertEqual([entry.name for entry in entries], ["eas-update"])

    def test_parses_multiline_yaml_description(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_name:
            skill_md = Path(tmp_name) / "sample" / "SKILL.md"
            skill_md.parent.mkdir(parents=True)
            skill_md.write_text(
                "---\nname: sample\ndescription: >-\n  Primeira linha\n  segunda linha.\n---\n",
                encoding="utf-8",
            )
            metadata = parse_frontmatter(skill_md)
            self.assertEqual(metadata.name, "sample")
            self.assertEqual(metadata.description, "Primeira linha segunda linha.")

    def test_raises_on_duplicate_skill_name_across_categories(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_name:
            skills_dir = Path(tmp_name) / "skills"
            _write_skill(skills_dir / "expo-router", "expo-router", "Custom duplicada.")
            _write_skill(skills_dir / "expo" / "expo-router", "expo-router", "Oficial.")
            with self.assertRaises(ValueError) as ctx:
                discover_repo_skills(skills_dir)
            self.assertIn("expo-router", str(ctx.exception))

    def test_find_skill_by_name_returns_nested_entry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_name:
            skills_dir = Path(tmp_name) / "skills"
            _write_skill(skills_dir / "expo" / "expo-ui", "expo-ui", "Componentes nativos.")
            found = find_skill_by_name("expo-ui", skills_dir)
            self.assertIsNotNone(found)
            assert found is not None
            self.assertEqual(found.category, "expo")
