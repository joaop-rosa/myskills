"""Instalação, relink automático, limpeza e importação de skills nos agentes."""

from __future__ import annotations

import shutil
from collections.abc import Sequence
from pathlib import Path
from typing import Literal

from skills_cli.console import log_error, log_info, log_success, log_warn
from skills_cli.models import (
    CLAUDE_GLOBAL_DIR,
    GEMINI_GLOBAL_DIR,
    REPO_ROOT,
    AgentTarget,
    GlobalDirHealth,
    InstallMode,
    Scope,
    TargetDirectory,
)


def _select_targets(
    agent: AgentTarget,
    gemini_path: Path,
    claude_path: Path,
) -> list[TargetDirectory]:
    targets: list[TargetDirectory] = []
    if agent in ("all", "gemini"):
        targets.append(TargetDirectory(agent="gemini", path=gemini_path))
    if agent in ("all", "claude"):
        targets.append(TargetDirectory(agent="claude", path=claude_path))
    return targets


def get_target_directories(
    scope: Scope,
    agent: AgentTarget,
    target_project_path: Path | None = None,
    gemini_dir: Path = GEMINI_GLOBAL_DIR,
    claude_dir: Path = CLAUDE_GLOBAL_DIR,
) -> list[TargetDirectory]:
    """Retorna os diretórios de destino para o escopo e agente escolhidos.

    Exemplo:
        >>> dirs = get_target_directories("global", "all")
    """
    if scope == "global":
        return _select_targets(agent, gemini_dir, claude_dir)
    project_root = target_project_path or Path.cwd()
    return _select_targets(agent, project_root / ".agents" / "skills", project_root / ".claude" / "skills")


def is_path_within(candidate: Path, parent: Path) -> bool:
    """Verifica se o destino resolvido de `candidate` está dentro de `parent`.

    Exemplo:
        >>> is_path_within(Path("/repo/skills/expo/expo-ui"), Path("/repo"))
        True
    """
    resolved_candidate = candidate.resolve(strict=False)
    resolved_parent = parent.resolve(strict=False)
    return resolved_candidate.is_relative_to(resolved_parent)


def _prepare_existing_symlink(
    dest_path: Path,
    skill_path: Path,
    repo_root: Path,
    force: bool,
) -> Literal["skip", "install", "conflict"]:
    resolved_target = dest_path.resolve(strict=False)
    if resolved_target == skill_path.resolve():
        return "skip"
    if not dest_path.exists() or is_path_within(dest_path, repo_root):
        dest_path.unlink()
        return "install"
    if force:
        dest_path.unlink()
        return "install"
    log_warn(
        f"Symlink existente '{dest_path.name}' aponta para outro destino ({resolved_target}). "
        "Use --force para sobrescrever."
    )
    return "conflict"


def _resolve_existing_destination(
    dest_path: Path,
    skill_path: Path,
    repo_root: Path,
    force: bool,
) -> Literal["skip", "install", "conflict"]:
    if dest_path.is_symlink():
        return _prepare_existing_symlink(dest_path, skill_path, repo_root, force)
    if dest_path.is_dir():
        if not force:
            log_warn(f"Diretório existente '{dest_path.name}' em {dest_path.parent}. Use --force para sobrescrever.")
            return "conflict"
        shutil.rmtree(dest_path)
    elif dest_path.exists():
        if not force:
            log_warn(f"Arquivo conflitante existente '{dest_path.name}'. Use --force para sobrescrever.")
            return "conflict"
        dest_path.unlink()
    return "install"


def _write_skill_target(skill_path: Path, dest_path: Path, mode: InstallMode) -> bool:
    try:
        if mode == "symlink":
            dest_path.symlink_to(skill_path.resolve(), target_is_directory=True)
            return True
        shutil.copytree(skill_path, dest_path)
        return True
    except OSError as exc:
        log_error(f"Erro ao instalar {skill_path.name} em {dest_path}: {exc}")
        return False


def install_skill_to_dir(
    skill_path: Path, dest_dir: Path, repo_root: Path = REPO_ROOT,
    mode: InstallMode = "symlink", force: bool = False, dry_run: bool = False,
) -> bool:
    """Instala ou atualiza o link/cópia de uma skill em um diretório de destino.

    Exemplo:
        >>> install_skill_to_dir(Path("/repo/skills/expo/expo-ui"), Path("~/.claude/skills"))
    """
    dest_path = dest_dir / skill_path.name
    if dry_run:
        log_info(f"[DRY-RUN] Instalar '{skill_path.name}' em {dest_path} via {mode}")
        return True
    dest_dir.mkdir(parents=True, exist_ok=True)
    resolution = _resolve_existing_destination(dest_path, skill_path, repo_root, force)
    if resolution != "install":
        return resolution == "skip"
    return _write_skill_target(skill_path, dest_path, mode)


def _is_broken_repo_symlink(entry: Path, repo_root: Path) -> bool:
    return entry.is_symlink() and not entry.exists() and is_path_within(entry, repo_root)


def prune_broken_repo_symlinks(dest_dir: Path, repo_root: Path = REPO_ROOT) -> list[str]:
    """Remove symlinks quebrados em `dest_dir` que apontavam para dentro de `repo_root`.

    Exemplo:
        >>> removed = prune_broken_repo_symlinks(Path("~/.claude/skills"))
    """
    if not dest_dir.is_dir():
        return []
    pruned: list[str] = []
    for entry in sorted(dest_dir.iterdir()):
        if _is_broken_repo_symlink(entry, repo_root):
            entry.unlink()
            pruned.append(entry.name)
    return pruned


def _import_single_dir(
    agent_name: str,
    candidate_dir: Path,
    skills_dir: Path,
    known_skill_names: set[str],
) -> str | None:
    if candidate_dir.is_symlink() or not candidate_dir.is_dir():
        return None
    if not (candidate_dir / "SKILL.md").is_file() or candidate_dir.name in known_skill_names:
        return None
    log_info(f"Nova skill encontrada em {agent_name}: '{candidate_dir.name}'. Importando para o repositório...")
    dest_in_repo = skills_dir / candidate_dir.name
    shutil.copytree(candidate_dir, dest_in_repo)
    shutil.rmtree(candidate_dir)
    candidate_dir.symlink_to(dest_in_repo.resolve(), target_is_directory=True)
    known_skill_names.add(candidate_dir.name)
    log_success(f"Skill '{candidate_dir.name}' importada e transformada em symlink.")
    return candidate_dir.name


def _import_from_target(
    target: TargetDirectory,
    skills_dir: Path,
    known_skill_names: set[str],
) -> list[str]:
    if not target.path.is_dir():
        return []
    imported: list[str] = []
    for candidate_dir in sorted(target.path.iterdir()):
        imported_name = _import_single_dir(target.agent, candidate_dir, skills_dir, known_skill_names)
        if imported_name is not None:
            imported.append(imported_name)
    return imported


def import_untracked_skills(
    global_targets: Sequence[TargetDirectory],
    skills_dir: Path,
    known_skill_names: set[str],
) -> list[str]:
    """Importa skills criadas localmente nos diretórios globais que ainda não existem no repo.

    Exemplo:
        >>> imported = import_untracked_skills(targets, SKILLS_DIR, known_names)
    """
    imported: list[str] = []
    for target in global_targets:
        imported.extend(_import_from_target(target, skills_dir, known_skill_names))
    return imported


def _classify_dir_entry(entry: Path) -> str:
    if entry.is_symlink():
        return "active" if entry.exists() else "broken"
    return "copy" if entry.is_dir() else "other"


def inspect_global_dir_health(global_dir: Path) -> GlobalDirHealth:
    """Inspeciona symlinks ativos, quebrados e cópias físicas em um diretório global.

    Exemplo:
        >>> health = inspect_global_dir_health(Path("~/.gemini/config/skills"))
    """
    if not global_dir.exists():
        return GlobalDirHealth(exists=False, active_links=0, copies=0, broken_links=0, other=0)
    counts = {"active": 0, "copy": 0, "broken": 0, "other": 0}
    for entry in global_dir.iterdir():
        counts[_classify_dir_entry(entry)] += 1
    return GlobalDirHealth(
        exists=True,
        active_links=counts["active"],
        copies=counts["copy"],
        broken_links=counts["broken"],
        other=counts["other"],
    )
