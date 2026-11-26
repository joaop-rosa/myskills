"""Fachada retrocompatível para sincronização das skills oficiais da Expo."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from skills_cli.git_client import GitClient
from skills_cli.models import SOURCES_FILE, ExpoSourceConfig, ExpoSyncSummary
from skills_cli.upstream_sync import (
    collect_upstream_skills,
    directories_match,
    load_upstream_source_config,
    save_upstream_source_config,
    sync_upstream_source,
    write_sync_summary_json,
)

__all__ = [
    "collect_upstream_skills",
    "directories_match",
    "load_expo_source_config",
    "save_expo_source_config",
    "sync_expo_upstream",
    "write_sync_summary_json",
]


def load_expo_source_config(sources_file: Path = SOURCES_FILE) -> ExpoSourceConfig:
    """Carrega a configuração `expo` de `sources.json` com valores padrão seguros.

    Exemplo:
        >>> config = load_expo_source_config(Path("sources.json"))
    """
    return load_upstream_source_config("expo", sources_file)


def save_expo_source_config(sources_file: Path, config: ExpoSourceConfig) -> None:
    """Persiste a seção `expo` em `sources.json` preservando outras entradas.

    Exemplo:
        >>> save_expo_source_config(Path("sources.json"), config)
    """
    save_upstream_source_config(sources_file, config)


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
    return sync_upstream_source("expo", repo_root, sources_file, git_client, now_provider)
