"""Sincronização idempotente de múltiplas fontes upstream de skills."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path

from skills_cli.discovery import parse_frontmatter
from skills_cli.git_client import GitClient
from skills_cli.models import SOURCES_FILE, UpstreamSourceConfig, UpstreamSyncSummary

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


def _parse_string_list(raw_value: object, field_name: str, sources_file: Path, default: tuple[str, ...]) -> tuple[str, ...]:
    if raw_value is None:
        return default
    if not isinstance(raw_value, list) or not all(isinstance(entry, str) for entry in raw_value):
        raise ValueError(
            f"Invalid '{field_name}' in {sources_file}: received {raw_value!r}, expected list[str]"
        )
    return tuple(raw_value)


def _build_expo_default_config(raw_expo: Mapping[str, object], sources_file: Path) -> UpstreamSourceConfig:
    return UpstreamSourceConfig(
        repo=str(raw_expo.get("repo") or DEFAULT_EXPO_REPO),
        branch=str(raw_expo.get("branch") or DEFAULT_EXPO_BRANCH),
        scan_dirs=_parse_string_list(raw_expo.get("scan_dirs"), "expo.scan_dirs", sources_file, DEFAULT_EXPO_SCAN_DIRS),
        target_dir=str(raw_expo.get("target_dir") or DEFAULT_EXPO_TARGET_DIR),
        last_sync=str(raw_expo["last_sync"]) if raw_expo.get("last_sync") else None,
        last_commit=str(raw_expo["last_commit"]) if raw_expo.get("last_commit") else None,
        include=_parse_string_list(raw_expo.get("include"), "expo.include", sources_file, ()),
        source_name="expo",
    )


def _build_named_config(source_name: str, raw_entry: Mapping[str, object], sources_file: Path) -> UpstreamSourceConfig:
    if source_name == "expo":
        return _build_expo_default_config(raw_entry, sources_file)
    repo = raw_entry.get("repo")
    target_dir = raw_entry.get("target_dir")
    if not isinstance(repo, str) or not repo or not isinstance(target_dir, str) or not target_dir:
        raise ValueError(
            f"Invalid source '{source_name}' in {sources_file}: received repo={repo!r}, target_dir={target_dir!r}; "
            "expected non-empty strings"
        )
    return UpstreamSourceConfig(
        repo=repo,
        branch=str(raw_entry.get("branch") or "main"),
        scan_dirs=_parse_string_list(raw_entry.get("scan_dirs"), f"{source_name}.scan_dirs", sources_file, ("skills",)),
        target_dir=target_dir,
        last_sync=str(raw_entry["last_sync"]) if raw_entry.get("last_sync") else None,
        last_commit=str(raw_entry["last_commit"]) if raw_entry.get("last_commit") else None,
        include=_parse_string_list(raw_entry.get("include"), f"{source_name}.include", sources_file, ()),
        source_name=source_name,
    )


def load_upstream_source_config(source_name: str, sources_file: Path = SOURCES_FILE) -> UpstreamSourceConfig:
    """Carrega uma fonte upstream nomeada de `sources.json`.

    Exemplo:
        >>> config = load_upstream_source_config("vercel", Path("sources.json"))
    """
    raw_sources = _read_raw_sources(sources_file)
    if source_name not in raw_sources:
        if source_name == "expo":
            return _build_expo_default_config({}, sources_file)
        raise ValueError(f"Unknown upstream source {source_name!r} in {sources_file}: available={sorted(raw_sources)}")
    raw_entry = raw_sources[source_name]
    if not isinstance(raw_entry, dict):
        raise ValueError(f"Invalid '{source_name}' section in {sources_file}: received {type(raw_entry).__name__}, expected object")
    return _build_named_config(source_name, raw_entry, sources_file)


def load_all_upstream_configs(sources_file: Path = SOURCES_FILE) -> list[UpstreamSourceConfig]:
    """Carrega todas as fontes upstream configuradas em `sources.json`.

    Exemplo:
        >>> configs = load_all_upstream_configs(Path("sources.json"))
    """
    raw_sources = _read_raw_sources(sources_file)
    if not raw_sources:
        return []
    return [load_upstream_source_config(str(name), sources_file) for name in raw_sources]


def save_upstream_source_config(sources_file: Path, config: UpstreamSourceConfig) -> None:
    """Persiste uma fonte upstream em `sources.json` preservando as demais entradas.

    Exemplo:
        >>> save_upstream_source_config(Path("sources.json"), config)
    """
    raw_sources = _read_raw_sources(sources_file) if sources_file.is_file() else {}
    serialized: dict[str, object] = {
        "repo": config.repo,
        "branch": config.branch,
        "target_dir": config.target_dir,
        "scan_dirs": list(config.scan_dirs),
    }
    if config.include:
        serialized["include"] = list(config.include)
    serialized["last_sync"] = config.last_sync
    serialized["last_commit"] = config.last_commit
    raw_sources[config.source_name] = serialized
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


def _collect_scan_dir_skills(scan_dir: Path, include_set: frozenset[str]) -> dict[str, Path]:
    if not scan_dir.is_dir():
        return {}
    found: dict[str, Path] = {}
    for entry in sorted(scan_dir.iterdir()):
        if not entry.is_dir() or entry.name.startswith(".") or not (entry / "SKILL.md").is_file():
            continue
        canonical_name = parse_frontmatter(entry / "SKILL.md").name or entry.name
        if include_set and canonical_name not in include_set and entry.name not in include_set:
            continue
        found[canonical_name] = entry
    return found


def collect_upstream_skills(
    upstream_root: Path,
    scan_dirs: Sequence[str],
    include: Sequence[str] = (),
) -> dict[str, Path]:
    """Coleta skills válidas do upstream aplicando filtro opcional `include` por nome.

    Exemplo:
        >>> skills = collect_upstream_skills(Path("/tmp/vercel"), ("skills",), ("vercel-react-best-practices",))
    """
    include_set = frozenset(include)
    collected: dict[str, Path] = {}
    for relative_dir in scan_dirs:
        collected.update(_collect_scan_dir_skills(upstream_root / relative_dir, include_set))
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
    config: UpstreamSourceConfig,
    git_client: GitClient,
    temp_dir: Path,
) -> tuple[str, dict[str, Path]]:
    clone_result = git_client.clone_shallow(config.repo, config.branch, temp_dir)
    if clone_result.returncode != 0:
        raise RuntimeError(
            f"Failed to clone '{config.source_name}' repository {config.repo!r} (branch {config.branch!r}): "
            f"{clone_result.stderr.strip() or 'unknown git error'}"
        )
    commit_sha = git_client.get_head_commit(temp_dir)
    upstream_skills = collect_upstream_skills(temp_dir, config.scan_dirs, config.include)
    if not upstream_skills:
        raise RuntimeError(
            f"No valid skills with SKILL.md found for '{config.source_name}' in scan_dirs={list(config.scan_dirs)!r} "
            f"(include={list(config.include)!r}) at commit {commit_sha!r}"
        )
    return commit_sha, upstream_skills


def _persist_sync_metadata(
    sources_file: Path,
    config: UpstreamSourceConfig,
    commit_sha: str,
    now_provider: Callable[[], datetime] | None,
) -> None:
    timestamp = (now_provider or _utc_now)().isoformat()
    updated_config = UpstreamSourceConfig(
        repo=config.repo,
        branch=config.branch,
        scan_dirs=config.scan_dirs,
        target_dir=config.target_dir,
        last_sync=timestamp,
        last_commit=commit_sha,
        include=config.include,
        source_name=config.source_name,
    )
    save_upstream_source_config(sources_file, updated_config)


def _mirror_upstream_to_target(
    config: UpstreamSourceConfig, repo_root: Path, git_client: GitClient
) -> UpstreamSyncSummary:
    target_dir = repo_root / config.target_dir
    temp_dir = Path(tempfile.mkdtemp(prefix=f"{config.source_name}-skills-"))
    try:
        commit_sha, upstream_skills = _clone_upstream_or_raise(config, git_client, temp_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        added, updated, unchanged_count = _apply_upstream_add_or_update(upstream_skills, target_dir)
        removed = _remove_obsolete_skills(upstream_skills, target_dir)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
    return UpstreamSyncSummary(
        commit_sha, config.target_dir, tuple(added), tuple(updated), tuple(removed), unchanged_count, config.source_name
    )


def sync_upstream_source(
    source_name: str,
    repo_root: Path,
    sources_file: Path,
    git_client: GitClient,
    now_provider: Callable[[], datetime] | None = None,
) -> UpstreamSyncSummary:
    """Sincroniza uma fonte upstream específica de forma idempotente.

    Exemplo:
        >>> summary = sync_upstream_source("vercel", REPO_ROOT, SOURCES_FILE, SubprocessGitClient())
    """
    config = load_upstream_source_config(source_name, sources_file)
    summary = _mirror_upstream_to_target(config, repo_root, git_client)
    if summary.changed:
        _persist_sync_metadata(sources_file, config, summary.commit_sha, now_provider)
    return summary


def sync_all_upstreams(
    repo_root: Path,
    sources_file: Path,
    git_client: GitClient,
    source_names: Sequence[str] = (),
    now_provider: Callable[[], datetime] | None = None,
) -> list[UpstreamSyncSummary]:
    """Sincroniza todas (ou as selecionadas) fontes upstream definidas em `sources.json`.

    Exemplo:
        >>> summaries = sync_all_upstreams(REPO_ROOT, SOURCES_FILE, SubprocessGitClient())
    """
    names = list(source_names) if source_names else [cfg.source_name for cfg in load_all_upstream_configs(sources_file)]
    if not names:
        raise ValueError(f"No upstream sources configured in {sources_file}; expected at least one source entry")
    return [sync_upstream_source(name, repo_root, sources_file, git_client, now_provider) for name in names]


def _summary_to_dict(summary: UpstreamSyncSummary) -> dict[str, object]:
    return {
        "source": summary.source_name,
        "changed": summary.changed,
        "commit_sha": summary.commit_sha,
        "short_sha": summary.short_sha,
        "target_dir": summary.target_dir,
        "added": list(summary.added),
        "updated": list(summary.updated),
        "removed": list(summary.removed),
        "unchanged_count": summary.unchanged_count,
    }


def write_sync_summary_json(summary: UpstreamSyncSummary, output_path: Path) -> None:
    """Grava o resumo de uma sincronização upstream em JSON.

    Exemplo:
        >>> write_sync_summary_json(summary, Path("/tmp/expo-sync.json"))
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(_summary_to_dict(summary), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_multi_sync_summary_json(summaries: Sequence[UpstreamSyncSummary], output_path: Path) -> None:
    """Grava o resumo consolidado de múltiplas fontes upstream em JSON para CI/CD.

    Exemplo:
        >>> write_multi_sync_summary_json(summaries, Path("/tmp/upstream-sync.json"))
    """
    payload: dict[str, object] = {
        "changed": any(summary.changed for summary in summaries),
        "sources": [_summary_to_dict(summary) for summary in summaries],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
