"""Modelos de domínio, constantes de caminho e tipos da CLI de skills."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"
SOURCES_FILE = REPO_ROOT / "sources.json"
BIN_DIR = REPO_ROOT / "bin"

GEMINI_GLOBAL_DIR = Path.home() / ".gemini" / "config" / "skills"
CLAUDE_GLOBAL_DIR = Path.home() / ".claude" / "skills"

RESERVED_GROUP_NAMES: frozenset[str] = frozenset({"expo"})

Scope = Literal["global", "project"]
AgentTarget = Literal["all", "gemini", "claude"]
InstallMode = Literal["symlink", "copy"]


@dataclass(frozen=True)
class SkillMetadata:
    """Metadados extraídos do frontmatter YAML de um arquivo SKILL.md."""

    name: str
    description: str


@dataclass(frozen=True)
class SkillEntry:
    """Representa uma skill descoberta no repositório local."""

    name: str
    path: Path
    category: str
    description: str


@dataclass(frozen=True)
class TargetDirectory:
    """Diretório de destino para instalação de skills em um agente."""

    agent: str
    path: Path


@dataclass(frozen=True)
class GlobalDirHealth:
    """Contadores de diagnóstico de um diretório global de skills."""

    exists: bool
    active_links: int
    copies: int
    broken_links: int
    other: int


@dataclass(frozen=True)
class ExpoSourceConfig:
    """Configuração de sincronização com o repositório upstream da Expo."""

    repo: str
    branch: str
    scan_dirs: tuple[str, ...]
    target_dir: str
    last_sync: str | None
    last_commit: str | None


@dataclass(frozen=True)
class ExpoSyncSummary:
    """Resultado consolidado de uma execução de sincronização com a Expo."""

    commit_sha: str
    target_dir: str
    added: tuple[str, ...]
    updated: tuple[str, ...]
    removed: tuple[str, ...]
    unchanged_count: int

    @property
    def short_sha(self) -> str:
        """Retorna os primeiros 8 caracteres do hash de commit upstream.

        Exemplo:
            >>> summary.short_sha
            '05754e71'
        """
        return self.commit_sha[:8]

    @property
    def changed(self) -> bool:
        """Indica se houve criação, atualização ou remoção de alguma skill.

        Exemplo:
            >>> summary.changed
            True
        """
        return bool(self.added or self.updated or self.removed)
