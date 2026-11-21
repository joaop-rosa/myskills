"""Testes unitários para sincronização idempotente das skills da Expo."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from skills_cli.expo_sync import load_expo_source_config, sync_expo_upstream, write_sync_summary_json
from tests.fakes import FakeGitClient


def _seed_skill(directory: Path, content: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "SKILL.md").write_text(content, encoding="utf-8")


def _write_sources(sources_file: Path, last_commit: str = "oldsha000", last_sync: str = "2026-01-01T00:00:00+00:00") -> None:
    payload = {
        "expo": {
            "repo": "https://github.com/expo/skills.git",
            "branch": "main",
            "target_dir": "skills/expo",
            "scan_dirs": ["plugins/expo/skills"],
            "last_sync": last_sync,
            "last_commit": last_commit,
        }
    }
    sources_file.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


class ExpoSyncTests(unittest.TestCase):
    """Verifica sincronização em `skills/expo/`, remoção e idempotência de metadados."""

    def _prepare_sync_fixture(self, root: Path) -> tuple[Path, Path, Path]:
        repo_root = root / "repo"
        sources_file = repo_root / "sources.json"
        repo_root.mkdir()
        _write_sources(sources_file)
        _seed_skill(repo_root / "skills" / "expo" / "expo-keep", "same")
        _seed_skill(repo_root / "skills" / "expo" / "expo-router", "old")
        _seed_skill(repo_root / "skills" / "expo" / "expo-old", "gone")
        upstream = root / "upstream"
        _seed_skill(upstream / "plugins" / "expo" / "skills" / "expo-keep", "same")
        _seed_skill(upstream / "plugins" / "expo" / "skills" / "expo-router", "new")
        _seed_skill(upstream / "plugins" / "expo" / "skills" / "expo-ui", "added")
        return repo_root, sources_file, upstream

    def test_adds_updates_removes_and_keeps_unchanged_skills(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_name:
            repo_root, sources_file, upstream = self._prepare_sync_fixture(Path(tmp_name))
            client = FakeGitClient(upstream_tree=upstream, commit_sha="1234567890abcdef")
            fixed_now = lambda: datetime(2026, 11, 21, 9, 0, tzinfo=timezone.utc)
            summary = sync_expo_upstream(repo_root, sources_file, client, now_provider=fixed_now)
            self.assertEqual((summary.added, summary.updated, summary.removed), (("expo-ui",), ("expo-router",), ("expo-old",)))
            self.assertEqual(summary.unchanged_count, 1)
            self.assertTrue(summary.changed)
            self.assertFalse((repo_root / "skills" / "expo" / "expo-old").exists())
            config = load_expo_source_config(sources_file)
            self.assertEqual(config.last_commit, "1234567890abcdef")
            self.assertEqual(config.last_sync, "2026-11-21T09:00:00+00:00")

    def test_is_idempotent_when_contents_unchanged_despite_new_commit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_name:
            root = Path(tmp_name)
            repo_root = root / "repo"
            sources_file = repo_root / "sources.json"
            repo_root.mkdir()
            _write_sources(sources_file, last_commit="oldsha000", last_sync="2026-10-01T00:00:00+00:00")
            _seed_skill(repo_root / "skills" / "expo" / "expo-router", "same")
            upstream = root / "upstream"
            _seed_skill(upstream / "plugins" / "expo" / "skills" / "expo-router", "same")
            client = FakeGitClient(upstream_tree=upstream, commit_sha="newsha9999")
            summary = sync_expo_upstream(repo_root, sources_file, client)
            self.assertFalse(summary.changed)
            self.assertEqual(summary.unchanged_count, 1)
            config = load_expo_source_config(sources_file)
            self.assertEqual(config.last_commit, "oldsha000")
            self.assertEqual(config.last_sync, "2026-10-01T00:00:00+00:00")

    def test_aborts_without_deleting_local_skills_when_upstream_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_name:
            root = Path(tmp_name)
            repo_root = root / "repo"
            sources_file = repo_root / "sources.json"
            repo_root.mkdir()
            _write_sources(sources_file)
            local_skill = repo_root / "skills" / "expo" / "expo-router"
            _seed_skill(local_skill, "preserved")
            empty_upstream = root / "empty-upstream"
            empty_upstream.mkdir()
            client = FakeGitClient(upstream_tree=empty_upstream)
            with self.assertRaises(RuntimeError):
                sync_expo_upstream(repo_root, sources_file, client)
            self.assertTrue((local_skill / "SKILL.md").is_file())

    def test_writes_summary_json_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_name:
            root = Path(tmp_name)
            repo_root = root / "repo"
            sources_file = repo_root / "sources.json"
            repo_root.mkdir()
            _write_sources(sources_file)
            upstream = root / "upstream"
            _seed_skill(upstream / "plugins" / "expo" / "skills" / "expo-ui", "ui")
            client = FakeGitClient(upstream_tree=upstream, commit_sha="deadbeef11223344")
            summary = sync_expo_upstream(repo_root, sources_file, client)
            out_json = root / "artifacts" / "sync.json"
            write_sync_summary_json(summary, out_json)
            parsed = json.loads(out_json.read_text(encoding="utf-8"))
            self.assertTrue(parsed["changed"])
            self.assertEqual(parsed["short_sha"], "deadbeef")
            self.assertEqual(parsed["target_dir"], "skills/expo")
            self.assertEqual(parsed["added"], ["expo-ui"])
