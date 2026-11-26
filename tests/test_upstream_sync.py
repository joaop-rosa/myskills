"""Testes unitários para sincronização multi-fonte (Expo + Vercel) e filtro `include`."""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from skills_cli import commands
from skills_cli.git_client import GitCommandResult
from skills_cli.upstream_sync import (
    load_upstream_source_config,
    sync_all_upstreams,
    sync_upstream_source,
    write_multi_sync_summary_json,
)


class FakeMultiRepoGitClient:
    """Fake nomeado de `GitClient` que mapeia URLs de repositório para fixtures locais."""

    def __init__(self, trees_by_repo: dict[str, Path], commits_by_repo: dict[str, str]) -> None:
        self.trees_by_repo = trees_by_repo
        self.commits_by_repo = commits_by_repo
        self.repo_by_dest: dict[Path, str] = {}

    def clone_shallow(self, repo_url: str, branch: str, dest_dir: Path) -> GitCommandResult:
        source_tree = self.trees_by_repo.get(repo_url)
        if source_tree is None or not source_tree.is_dir():
            return GitCommandResult(1, "", f"Unknown fake repo {repo_url!r}")
        shutil.copytree(source_tree, dest_dir, dirs_exist_ok=True)
        self.repo_by_dest[dest_dir] = repo_url
        return GitCommandResult(0, "", "")

    def get_head_commit(self, repo_dir: Path) -> str:
        repo_url = self.repo_by_dest.get(repo_dir, "")
        return self.commits_by_repo.get(repo_url, "unknown")

    def pull_fast_forward(self, repo_dir: Path) -> GitCommandResult:
        return GitCommandResult(0, "", "")

    def get_short_status(self, repo_dir: Path) -> GitCommandResult:
        return GitCommandResult(0, "", "")


def _write_skill(directory: Path, frontmatter_name: str, body: str = "content") -> None:
    directory.mkdir(parents=True, exist_ok=True)
    content = f"---\nname: {frontmatter_name}\ndescription: test\n---\n\n{body}\n"
    (directory / "SKILL.md").write_text(content, encoding="utf-8")


def _write_multi_sources(sources_file: Path) -> None:
    payload = {
        "expo": {
            "repo": "https://github.com/expo/skills.git",
            "branch": "main",
            "target_dir": "skills/expo",
            "scan_dirs": ["plugins/expo/skills"],
            "last_sync": "2026-10-28T19:55:26",
            "last_commit": "05754e71",
        },
        "vercel": {
            "repo": "https://github.com/vercel-labs/agent-skills.git",
            "branch": "main",
            "target_dir": "skills/vercel",
            "scan_dirs": ["skills"],
            "include": ["vercel-react-best-practices"],
            "last_sync": None,
            "last_commit": None,
        },
    }
    sources_file.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _fixed_utc_now() -> datetime:
    return datetime(2026, 11, 25, 12, 0, tzinfo=timezone.utc)


class MultiUpstreamSyncTests(unittest.TestCase):
    """Valida filtro `include` por frontmatter, multi-source sync e proteção de grupo."""

    def test_vercel_include_matches_frontmatter_name_and_preserves_expo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_name:
            root = Path(tmp_name)
            repo_root = root / "repo"
            sources_file = repo_root / "sources.json"
            repo_root.mkdir()
            _write_multi_sources(sources_file)

            vercel_tree = root / "vercel-upstream"
            _write_skill(vercel_tree / "skills" / "react-best-practices", "vercel-react-best-practices", "rules")
            _write_skill(vercel_tree / "skills" / "deploy-to-vercel", "deploy-to-vercel", "ignore")

            client = FakeMultiRepoGitClient(
                {"https://github.com/vercel-labs/agent-skills.git": vercel_tree},
                {"https://github.com/vercel-labs/agent-skills.git": "5a37a6329fbad366"},
            )
            summary = sync_upstream_source("vercel", repo_root, sources_file, client, now_provider=_fixed_utc_now)
            self.assertEqual(summary.added, ("vercel-react-best-practices",))
            self.assertTrue((repo_root / "skills/vercel/vercel-react-best-practices/SKILL.md").is_file())
            self.assertFalse((repo_root / "skills/vercel/deploy-to-vercel").exists())

            vercel_cfg = load_upstream_source_config("vercel", sources_file)
            expo_cfg = load_upstream_source_config("expo", sources_file)
            self.assertEqual(vercel_cfg.include, ("vercel-react-best-practices",))
            self.assertEqual(vercel_cfg.last_commit, "5a37a6329fbad366")
            self.assertEqual(expo_cfg.last_commit, "05754e71")

    def test_vercel_sync_is_idempotent_when_content_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_name:
            root = Path(tmp_name)
            repo_root = root / "repo"
            sources_file = repo_root / "sources.json"
            repo_root.mkdir()
            _write_multi_sources(sources_file)
            _write_skill(repo_root / "skills/vercel/vercel-react-best-practices", "vercel-react-best-practices", "same")

            vercel_tree = root / "vercel-upstream"
            _write_skill(vercel_tree / "skills/react-best-practices", "vercel-react-best-practices", "same")

            client = FakeMultiRepoGitClient(
                {"https://github.com/vercel-labs/agent-skills.git": vercel_tree},
                {"https://github.com/vercel-labs/agent-skills.git": "newcommit1234"},
            )
            summary = sync_upstream_source("vercel", repo_root, sources_file, client)
            self.assertFalse(summary.changed)
            self.assertEqual(summary.unchanged_count, 1)
            self.assertIsNone(load_upstream_source_config("vercel", sources_file).last_commit)

    def test_sync_all_upstreams_and_multi_summary_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_name:
            root = Path(tmp_name)
            repo_root = root / "repo"
            sources_file = repo_root / "sources.json"
            repo_root.mkdir()
            _write_multi_sources(sources_file)

            expo_tree = root / "expo-upstream"
            vercel_tree = root / "vercel-upstream"
            _write_skill(expo_tree / "plugins/expo/skills/expo-ui", "expo-ui")
            _write_skill(vercel_tree / "skills/react-best-practices", "vercel-react-best-practices")

            client = FakeMultiRepoGitClient(
                {
                    "https://github.com/expo/skills.git": expo_tree,
                    "https://github.com/vercel-labs/agent-skills.git": vercel_tree,
                },
                {
                    "https://github.com/expo/skills.git": "aaaa1111bbbb2222",
                    "https://github.com/vercel-labs/agent-skills.git": "cccc3333dddd4444",
                },
            )
            summaries = sync_all_upstreams(repo_root, sources_file, client, now_provider=_fixed_utc_now)
            out_json = root / "multi-sync.json"
            write_multi_sync_summary_json(summaries, out_json)
            payload = json.loads(out_json.read_text(encoding="utf-8"))
            self.assertTrue(payload["changed"])
            self.assertEqual([entry["source"] for entry in payload["sources"]], ["expo", "vercel"])

    def test_cmd_add_rejects_reserved_vercel_and_collision(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_name:
            skills_dir = Path(tmp_name) / "skills"
            _write_skill(skills_dir / "vercel" / "vercel-react-best-practices", "vercel-react-best-practices")
            self.assertEqual(commands.cmd_add(argparse.Namespace(name="vercel"), skills_dir=skills_dir), 1)
            self.assertEqual(
                commands.cmd_add(argparse.Namespace(name="vercel-react-best-practices"), skills_dir=skills_dir), 1
            )
