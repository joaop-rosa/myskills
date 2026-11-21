"""Sincronização idempotente das skills oficiais da Expo em `skills/expo/`."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path

from skills_cli.git_client import GitClient
from skills_cli.models import SOURCES_FILE, ExpoSourceConfig, ExpoSyncSummary

DEFAULT_EXPO_REPO = "https://github.com/expo/skills.git"
DEFAULT_EXPO_BRANCH = "main"
DEFAULT_EXPO_TARGET_DIR = "skills/expo"
DEFAULT_EXPO_SCAN_DIRS: tuple[str, ...] = ("plugins/expo/skills", "plugins/expo-experiments/skills")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _read_raw_sources(sources_file: Path) -> dict[str, object]:
    if not sources_file.is_file():
        return {}
    try:
        parsed: object = json.loads(sources_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(
            f"Failed to parse sources config at {sources_file}: {exc}; expected valid JSON object"
        ) from exc
    if not isinstance(parsed, dict):
        raise ValueError(
            f"Invalid root type in {sources_file}: received {type(parsed).__name__}, expected JSON object"
        )
    return parsed


def _parse_scan_dirs(raw_scan_dirs: object, sources_file: Path) -> tuple[str, ...]:
    if raw_scan_dirs is None:
        return DEFAULT_EXPO_SCAN_DIRS
    if not isinstance(raw_scan_dirs, list) or not all(isinstance(entry, str) for entry in raw_scan_dirs):
        raise ValueError(
            f"Invalid 'expo.scan_dirs' in {sources_file}: received {raw_scan_dirs!r}, expected list[str]"
        )
    return tuple(raw_scan_dirs)


def load_expo_source_config(sources_file: Path = SOURCES_FILE) -> ExpoSourceConfig:
    """Carrega a configuração `expo` de `sources.json` com valores padrão seguros.

    Exemplo:
        >>> config = load_expo_source_config(Path("sources.json"))
    """
    raw_sources = _read_raw_sources(sources_file)
    raw_expo = raw_sources.get("expo", {})
    if not isinstance(raw_expo, dict):
        raise ValueError(
            f"Invalid 'expo' section in {sources_file}: received {type(raw_expo).__name__}, expected JSON object"
        )
    return ExpoSourceConfig(
        repo=str(raw_expo.get("repo") or DEFAULT_EXPO_REPO),
        branch=str(raw_expo.get("branch") or DEFAULT_EXPO_BRANCH),
        scan_dirs=_parse_scan_dirs(raw_expo.get("scan_dirs"), sources_file),
        target_dir=str(raw_expo.get("target_dir") or DEFAULT_EXPO_TARGET_DIR),
        last_sync=str(raw_expo["last_sync"]) if raw_expo.get("last_sync") else None,
        last_commit=str(raw_expo["last_commit"]) if raw_expo.get("last_commit") else None,
    )


def save_expo_source_config(sources_file: Path, config: ExpoSourceConfig) -> None:
    """Persiste a seção `expo` em `sources.json` preservando chaves extras de topo.

    Exemplo:
        >>> save_expo_source_config(Path("sources.json"), config)
    """
    raw_sources = _read_raw_sources(sources_file) if sources_file.is_file() else {}
    raw_sources["expo"] = {
        "repo": config.repo,
        "branch": config.branch,
        "target_dir": config.target_dir,
        "scan_dirs": list(config.scan_dirs),
        "last_sync": config.last_sync,
        "last_commit": config.last_commit,
    }
    sources_file.parent.mkdir(parents=True, exist_ok=True)
    sources_file.write_text(json.dumps(raw_sources, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _entries_match(left_entry: Path, right_entry: Path) -> bool:
    if left_entry.is_symlink() or right_entry.is_symlink():
        return (
            left_entry.is_symlink()
            and right_entry.is_symlink()
            and os.readlink(left_entry) == os.readlink(right_entry)
        )
    if left_entry.is_dir() or right_entry.is_dir():
        return directories_match(left_entry, right_entry)
    if left_entry.is_file() and right_entry.is_file():
        return left_entry.read_bytes() == right_entry.read_bytes()
    return False


def directories_match(left_dir: Path, right_dir: Path) -> bool:
    """Compara recursivamente dois diretórios (arquivos, subpastas e symlinks).

    Exemplo:
        >>> directories_match(Path("a/expo-ui"), Path("b/expo-ui"))
        True
    """
    if not left_dir.is_dir() or not right_dir.is_dir():
        return False
    left_names = sorted(entry.name for entry in left_dir.iterdir())
    right_names = sorted(entry.name for entry in right_dir.iterdir())
    if left_names != right_names:
        return False
    return all(_entries_match(left_dir / name, right_dir / name) for name in left_names)


def _collect_scan_dir_skills(scan_dir: Path) -> dict[str, Path]:
    if not scan_dir.is_dir():
        return {}
    found: dict[str, Path] = {}
    for entry in sorted(scan_dir.iterdir()):
        if entry.is_dir() and not entry.name.startswith(".") and (entry / "SKILL.md").is_file():
            found[entry.name] = entry
    return found


def collect_upstream_skills(upstream_root: Path, scan_dirs: Sequence[str]) -> dict[str, Path]:
    """Coleta todas as skills válidas presentes nos diretórios configurados do upstream.

    Exemplo:
        >>> skills = collect_upstream_skills(Path("/tmp/expo"), ("plugins/expo/skills",))
    """
    collected: dict[str, Path] = {}
    for relative_dir in scan_dirs:
        collected.update(_collect_scan_dir_skills(upstream_root / relative_dir))
    return collected


def _sync_single_upstream_skill(skill_name: str, src_dir: Path, target_dir: Path) -> str:
    dest_dir = target_dir / skill_name
    if not dest_dir.exists():
        shutil.copytree(src_dir, dest_dir)
        return "added"
    if directories_match(src_dir, dest_dir):
        return "unchanged"
    shutil.rmtree(dest_dir)
    shutil.copytree(src_dir, dest_dir)
    return "updated"


def _apply_upstream_add_or_update(
    upstream_skills: Mapping[str, Path],
    target_dir: Path,
) -> tuple[list[str], list[str], int]:
    added: list[str] = []
    updated: list[str] = []
    unchanged_count = 0
    for skill_name in sorted(upstream_skills):
        outcome = _sync_single_upstream_skill(skill_name, upstream_skills[skill_name], target_dir)
        if outcome == "added":
            added.append(skill_name)
        elif outcome == "updated":
            updated.append(skill_name)
        else:
            unchanged_count += 1
    return added, updated, unchanged_count


def _remove_obsolete_skills(upstream_skills: Mapping[str, Path], target_dir: Path) -> list[str]:
    removed: list[str] = []
    for entry in sorted(target_dir.iterdir()):
        if entry.is_dir() and not entry.name.startswith(".") and entry.name not in upstream_skills:
            shutil.rmtree(entry)
            removed.append(entry.name)
    return removed


def _clone_upstream_or_raise(
    config: ExpoSourceConfig,
    git_client: GitClient,
    temp_dir: Path,
) -> tuple[str, dict[str, Path]]:
    clone_result = git_client.clone_shallow(config.repo, config.branch, temp_dir)
    if clone_result.returncode != 0:
        raise RuntimeError(
            f"Failed to clone Expo repository {config.repo!r} (branch {config.branch!r}): "
            f"{clone_result.stderr.strip() or 'unknown git error'}"
        )
    commit_sha = git_client.get_head_commit(temp_dir)
    upstream_skills = collect_upstream_skills(temp_dir, config.scan_dirs)
    if not upstream_skills:
        raise RuntimeError(
            f"No valid skills with SKILL.md found in scan_dirs={list(config.scan_dirs)!r} "
            f"at commit {commit_sha!r}; expected at least one upstream skill directory"
        )
    return commit_sha, upstream_skills


def _persist_sync_metadata(
    sources_file: Path,
    config: ExpoSourceConfig,
    commit_sha: str,
    now_provider: Callable[[], datetime] | None,
) -> None:
    timestamp = (now_provider or _utc_now)().isoformat()
    updated_config = ExpoSourceConfig(
        repo=config.repo,
        branch=config.branch,
        scan_dirs=config.scan_dirs,
        target_dir=config.target_dir,
        last_sync=timestamp,
        last_commit=commit_sha,
    )
    save_expo_source_config(sources_file, updated_config)


def _mirror_upstream_to_target(
    config: ExpoSourceConfig, repo_root: Path, git_client: GitClient
) -> ExpoSyncSummary:
    target_dir = repo_root / config.target_dir
    temp_dir = Path(tempfile.mkdtemp(prefix="expo-skills-"))
    try:
        commit_sha, upstream_skills = _clone_upstream_or_raise(config, git_client, temp_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        added, updated, unchanged_count = _apply_upstream_add_or_update(upstream_skills, target_dir)
        removed = _remove_obsolete_skills(upstream_skills, target_dir)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
    return ExpoSyncSummary(
        commit_sha, config.target_dir, tuple(added), tuple(updated), tuple(removed), unchanged_count
    )


def sync_expo_upstream(
    repo_root: Path,
    sources_file: Path,
    git_client: GitClient,
    now_provider: Callable[[], datetime] | None = None,
) -> ExpoSyncSummary:
    """Sincroniza `skills/expo/` com o upstream da Expo de forma idempotente.

    Exemplo:
        >>> summary = sync_expo_upstream(REPO_ROOT, SOURCES_FILE, SubprocessGitClient())
    """
    config = load_expo_source_config(sources_file)
    summary = _mirror_upstream_to_target(config, repo_root, git_client)
    if summary.changed:
        _persist_sync_metadata(sources_file, config, summary.commit_sha, now_provider)
    return summary


def write_sync_summary_json(summary: ExpoSyncSummary, output_path: Path) -> None:
    """Grava o resumo da sincronização Expo em arquivo JSON para consumo em CI/CD.

    Exemplo:
        >>> write_sync_summary_json(summary, Path("/tmp/expo-sync.json"))
    """
    payload: dict[str, object] = {
        "changed": summary.changed,
        "commit_sha": summary.commit_sha,
        "short_sha": summary.short_sha,
        "target_dir": summary.target_dir,
        "added": list(summary.added),
        "updated": list(summary.updated),
        "removed": list(summary.removed),
        "unchanged_count": summary.unchanged_count,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
