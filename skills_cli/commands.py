"""Handlers dos subcomandos da CLI de gerenciamento de skills."""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

from skills_cli.console import Colors, log_error, log_info, log_success, log_title, log_warn
from skills_cli.discovery import discover_repo_skills, find_skill_by_name
from skills_cli.expo_sync import sync_expo_upstream, write_sync_summary_json
from skills_cli.upstream_sync import (
    load_all_upstream_configs,
    sync_all_upstreams,
    write_multi_sync_summary_json,
)
from skills_cli.git_client import GitClient, SubprocessGitClient
from skills_cli.installer import (
    get_target_directories,
    import_untracked_skills,
    inspect_global_dir_health,
    install_skill_to_dir,
    prune_broken_repo_symlinks,
)
from skills_cli.mcp_commands import (
    print_mcp_catalog_table,
    print_mcp_status_section,
    sync_global_mcps,
)
from skills_cli.models import (
    BIN_DIR,
    CLAUDE_GLOBAL_DIR,
    CLAUDE_MCP_GLOBAL_FILE,
    GEMINI_GLOBAL_DIR,
    GEMINI_MCP_GLOBAL_FILE,
    MCPS_FILE,
    REPO_ROOT,
    RESERVED_GROUP_NAMES,
    SKILLS_DIR,
    SOURCES_FILE,
    AgentTarget,
    ExpoSyncSummary,
    InstallMode,
    Scope,
    SkillEntry,
    TargetDirectory,
)


def _select_skills_to_install(
    requested_names: Sequence[str],
    repo_skill_map: Mapping[str, Path],
) -> list[Path]:
    if not requested_names:
        return list(repo_skill_map.values())
    selected: list[Path] = []
    for name in requested_names:
        skill_path = repo_skill_map.get(name)
        if skill_path is not None:
            selected.append(skill_path)
        else:
            log_warn(f"Skill '{name}' não encontrada no repositório. Ignorando.")
    return selected


def _install_to_target(
    target: TargetDirectory,
    skill_paths: Sequence[Path],
    mode: InstallMode,
    force: bool,
    dry_run: bool,
) -> int:
    print(f"📦 Destino {Colors.BOLD}[{target.agent.upper()}]{Colors.RESET}: {target.path}")
    installed_count = 0
    for skill_path in skill_paths:
        if install_skill_to_dir(skill_path, target.path, REPO_ROOT, mode, force, dry_run):
            installed_count += 1
    log_success(f"{installed_count}/{len(skill_paths)} skills instaladas para {target.agent.upper()}.\n")
    return installed_count


def cmd_install(args: argparse.Namespace) -> int:
    """Instala todas ou apenas as skills informadas no escopo global ou de projeto.

    Exemplo:
        >>> cmd_install(build_parser().parse_args(["install", "--dry-run"]))
    """
    log_title("Instalação de Skills")
    scope: Scope = "project" if args.project is not None else "global"
    project_path = Path(args.project).resolve() if args.project else None
    targets = get_target_directories(scope, args.agent, project_path, GEMINI_GLOBAL_DIR, CLAUDE_GLOBAL_DIR)
    repo_skill_map = {entry.name: entry.path for entry in discover_repo_skills(SKILLS_DIR)}
    skill_paths = _select_skills_to_install(args.skills, repo_skill_map)
    if not skill_paths:
        log_error("Nenhuma skill válida selecionada para instalação.")
        return 1
    log_info(f"Escopo: {Colors.BOLD}{scope.upper()}{Colors.RESET} | Agente(s): {args.agent} | Modo: {args.mode}")
    log_info(f"Total de skills para instalar: {len(skill_paths)}\n")
    for target in targets:
        _install_to_target(target, skill_paths, args.mode, args.force, args.dry_run)
    return 0


def _prune_targets(global_targets: Sequence[TargetDirectory]) -> list[str]:
    pruned: list[str] = []
    for target in global_targets:
        pruned.extend(prune_broken_repo_symlinks(target.path, REPO_ROOT))
    return pruned


def _sync_global_targets(global_targets: Sequence[TargetDirectory]) -> None:
    known_names = {entry.name for entry in discover_repo_skills(SKILLS_DIR)}
    imported = import_untracked_skills(global_targets, SKILLS_DIR, known_names)
    log_success(f"{len(imported)} skill(s) importada(s).") if imported else log_info("Nenhuma nova skill não-rastreada.")
    pruned = _prune_targets(global_targets)
    if pruned:
        log_info(f"Symlinks obsoletos removidos: {', '.join(sorted(set(pruned)))}")
    skill_paths = [entry.path for entry in discover_repo_skills(SKILLS_DIR)]
    for target in global_targets:
        _install_to_target(target, skill_paths, "symlink", False, False)


def _report_repo_git_status(client: GitClient) -> None:
    git_res = client.get_short_status(REPO_ROOT)
    if git_res.returncode != 0:
        return
    if git_res.stdout.strip():
        log_warn("Alterações pendentes detectadas no Git (prontas para commit):")
        print(Colors.DIM + git_res.stdout + Colors.RESET)
        return
    log_success("Repositório Git está limpo e sincronizado.")


def _run_sync_upstream_step(args: argparse.Namespace, client: GitClient) -> bool:
    if getattr(args, "upstream", False):
        print("🔄 Sincronizando todas as fontes upstream...")
        return cmd_update_upstream(argparse.Namespace(sources=[], summary_json=None), git_client=client) == 0
    if getattr(args, "expo", False):
        print("🔄 Sincronizando com o upstream do Expo...")
        return cmd_update_expo(args, git_client=client) == 0
    return True


def cmd_sync(args: argparse.Namespace, git_client: GitClient | None = None) -> int:
    """Sincroniza skills do repositório com os agentes, importando novas e reparando links.

    Exemplo:
        >>> cmd_sync(build_parser().parse_args(["sync"]))
    """
    log_title("Sincronização de Skills")
    client = git_client or SubprocessGitClient()
    if not _run_sync_upstream_step(args, client):
        return 1
    agent: AgentTarget = getattr(args, "agent", "all")
    global_targets = get_target_directories("global", agent, None, GEMINI_GLOBAL_DIR, CLAUDE_GLOBAL_DIR)
    _sync_global_targets(global_targets)
    repo_mcps_file = REPO_ROOT / "mcps" / "servers.json"
    if repo_mcps_file.is_file() and not getattr(args, "no_mcp", False):
        sync_global_mcps(agent=agent, mcps_file=repo_mcps_file)
    _report_repo_git_status(client)
    return 0


def cmd_pull(args: argparse.Namespace, git_client: GitClient | None = None) -> int:
    """Atualiza o repositório local via `git pull --ff-only` e executa `sync` em seguida.

    Exemplo:
        >>> cmd_pull(build_parser().parse_args(["pull"]))
    """
    log_title("Atualização Local do Repositório (Pull + Sync)")
    client = git_client or SubprocessGitClient()
    pull_result = client.pull_fast_forward(REPO_ROOT)
    if pull_result.returncode != 0:
        log_error(f"Falha ao executar 'git pull --ff-only': {pull_result.stderr.strip() or 'erro desconhecido'}")
        log_info(f"Resolva divergências manualmente com: git -C {REPO_ROOT} pull --rebase")
        return 1
    log_success("Repositório atualizado com sucesso a partir do remoto.")
    sync_args = argparse.Namespace(expo=False, agent=getattr(args, "agent", "all"))
    return cmd_sync(sync_args, git_client=client)


def _log_sync_summary(summary: ExpoSyncSummary) -> None:
    print()
    log_info(f"[{summary.source_name.upper()}] Commit upstream: {summary.short_sha} -> {summary.target_dir}")
    if summary.added:
        log_success(f"Novas skills adicionadas ({len(summary.added)}): {', '.join(summary.added)}")
    if summary.updated:
        log_success(f"Skills atualizadas ({len(summary.updated)}): {', '.join(summary.updated)}")
    if summary.removed:
        log_warn(f"Skills removidas do upstream ({len(summary.removed)}): {', '.join(summary.removed)}")
    log_info(f"Skills sem alterações: {summary.unchanged_count}\n")


def cmd_update_expo(args: argparse.Namespace, git_client: GitClient | None = None) -> int:
    """Sincroniza as skills da Expo com o upstream oficial em `skills/expo/`.

    Exemplo:
        >>> cmd_update_expo(build_parser().parse_args(["update-expo"]))
    """
    log_title("Atualização de Skills do Expo (Upstream)")
    client = git_client or SubprocessGitClient()
    try:
        summary = sync_expo_upstream(REPO_ROOT, SOURCES_FILE, client)
    except (RuntimeError, ValueError) as exc:
        log_error(str(exc))
        return 1
    summary_json_path = getattr(args, "summary_json", None)
    if summary_json_path:
        write_sync_summary_json(summary, Path(summary_json_path))
        log_info(f"Resumo JSON salvo em: {summary_json_path}")
    _log_sync_summary(summary)
    return 0


def cmd_update_upstream(args: argparse.Namespace, git_client: GitClient | None = None) -> int:
    """Sincroniza todas ou determinadas fontes upstream configuradas em `sources.json`.

    Exemplo:
        >>> cmd_update_upstream(build_parser().parse_args(["update-upstream"]))
    """
    log_title("Atualização de Skills Upstream")
    client = git_client or SubprocessGitClient()
    source_names = getattr(args, "sources", ()) or ()
    try:
        summaries = sync_all_upstreams(REPO_ROOT, SOURCES_FILE, client, source_names)
    except (RuntimeError, ValueError) as exc:
        log_error(str(exc))
        return 1
    summary_json_path = getattr(args, "summary_json", None)
    if summary_json_path:
        write_multi_sync_summary_json(summaries, Path(summary_json_path))
        log_info(f"Resumo JSON salvo em: {summary_json_path}")
    for summary in summaries:
        _log_sync_summary(summary)
    return 0


def _group_skills_by_category(skill_entries: Sequence[SkillEntry]) -> dict[str, list[SkillEntry]]:
    grouped: dict[str, list[SkillEntry]] = {}
    for entry in skill_entries:
        grouped.setdefault(entry.category, []).append(entry)
    return grouped


def _category_heading(category: str) -> str:
    if category == "expo":
        return "EXPO & EAS FRAMEWORK"
    if category == "vercel":
        return "VERCEL LABS"
    if category == "custom":
        return "SKILLS CUSTOMIZADAS & WORKFLOWS"
    return f"{category.upper()} SKILLS"


def _format_agent_status(skill_path: Path, dest_dir: Path) -> str:
    link_path = dest_dir / skill_path.name
    if link_path.is_symlink():
        if not link_path.exists():
            return f"{Colors.RED}✗ broken{Colors.RESET}"
        if link_path.resolve() == skill_path.resolve():
            return f"{Colors.GREEN}✓ link{Colors.RESET}"
        return f"{Colors.YELLOW}⚠ stale{Colors.RESET}"
    if link_path.is_dir():
        return f"{Colors.GREEN}✓ copy{Colors.RESET}"
    return f"{Colors.DIM}-{Colors.RESET}"


def _print_category_table(category: str, entries: Sequence[SkillEntry]) -> None:
    print(f"{Colors.BOLD}{Colors.CYAN}[{_category_heading(category)}] ({len(entries)}){Colors.RESET}")
    print(f"{'Nome':<28} {'Gemini':<12} {'Claude':<12} {'Descrição'}")
    print("-" * 90)
    for entry in entries:
        gem_status = _format_agent_status(entry.path, GEMINI_GLOBAL_DIR)
        claude_status = _format_agent_status(entry.path, CLAUDE_GLOBAL_DIR)
        desc = entry.description[:39] + "..." if len(entry.description) > 42 else entry.description
        print(f"{Colors.BOLD}{entry.name:<28}{Colors.RESET} {gem_status:<20} {claude_status:<20} {Colors.DIM}{desc}{Colors.RESET}")
    print()


def cmd_list(args: argparse.Namespace) -> int:
    """Lista o catálogo de skills agrupado por categoria e status de vínculo.

    Exemplo:
        >>> cmd_list(build_parser().parse_args(["list"]))
    """
    log_title("Catálogo de Skills")
    skill_entries = discover_repo_skills(SKILLS_DIR)
    if not skill_entries:
        log_warn("Nenhuma skill encontrada no repositório.")
        return 0
    grouped = _group_skills_by_category(skill_entries)
    for category, entries in grouped.items():
        _print_category_table(category, entries)
    print(f"Total: {Colors.BOLD}{len(skill_entries)} skills disponíveis.{Colors.RESET}\n")
    if MCPS_FILE.is_file():
        print_mcp_catalog_table(MCPS_FILE, GEMINI_MCP_GLOBAL_FILE, CLAUDE_MCP_GLOBAL_FILE)
    return 0


def _print_global_health(label: str, global_dir: Path) -> None:
    health = inspect_global_dir_health(global_dir)
    print(f"🤖 {Colors.BOLD}{label}{Colors.RESET}:")
    print(f"   Caminho: {global_dir}")
    if not health.exists:
        print(f"   Status: {Colors.YELLOW}Diretório não existe ainda (será criado no primeiro install){Colors.RESET}\n")
        return
    print(f"   Skills ativas (Symlinks): {Colors.GREEN}{health.active_links}{Colors.RESET}")
    if health.copies > 0:
        print(f"   Skills copiadas (Pastas físicas): {Colors.YELLOW}{health.copies}{Colors.RESET}")
    if health.broken_links > 0:
        print(f"   Symlinks corrompidos: {Colors.RED}{health.broken_links}{Colors.RESET}")
    print()


def _print_upstream_sources_status() -> None:
    if not SOURCES_FILE.is_file():
        return
    for config in load_all_upstream_configs(SOURCES_FILE):
        short_sha = config.last_commit[:8] if config.last_commit else "Desconhecido"
        print(f"🌐 {Colors.BOLD}Upstream {config.source_name.title()}{Colors.RESET}:")
        print(f"   Repositório: {config.repo}")
        print(f"   Destino local: {config.target_dir}")
        if config.include:
            print(f"   Filtro include: {', '.join(config.include)}")
        print(f"   Última sincronização: {config.last_sync or 'Nunca'}")
        print(f"   Último commit: {short_sha}\n")


def cmd_status(args: argparse.Namespace) -> int:
    """Exibe diagnóstico de saúde do repositório, links globais e fontes upstream.

    Exemplo:
        >>> cmd_status(build_parser().parse_args(["status"]))
    """
    log_title("Status do Sistema de Skills")
    skill_entries = discover_repo_skills(SKILLS_DIR)
    grouped = _group_skills_by_category(skill_entries)
    breakdown = ", ".join(f"{cat}: {len(entries)}" for cat, entries in grouped.items())
    print(f"📁 Diretório do Repositório: {REPO_ROOT}")
    print(f"📚 Total de Skills no Repositório: {Colors.BOLD}{len(skill_entries)}{Colors.RESET} ({breakdown})\n")
    _print_global_health("Gemini (Antigravity)", GEMINI_GLOBAL_DIR)
    _print_global_health("Claude (Claude Code)", CLAUDE_GLOBAL_DIR)
    print_mcp_status_section(MCPS_FILE, GEMINI_MCP_GLOBAL_FILE, CLAUDE_MCP_GLOBAL_FILE)
    _print_upstream_sources_status()
    return 0


def _build_skill_template(skill_name: str) -> str:
    title = skill_name.replace("-", " ").title()
    return (
        f"---\nname: {skill_name}\ndescription: >-\n"
        f'  Descreva com clareza o objetivo desta skill e quando ela deve ser ativada pelo agente (ex: "Use esta skill quando o usuário pedir para...").\n'
        f"---\n\n# {title}\n\nInstruções e diretrizes de execução para o agente.\n\n"
        "## 1. Visão Geral\nDescreva aqui o propósito desta skill e seus casos de uso.\n\n"
        "## 2. Pré-requisitos e Validações\n- Liste arquivos, dependências ou comandos necessários antes de iniciar.\n\n"
        "## 3. Passo a Passo do Procedimento\n1. Primeiro passo de execução.\n2. Segundo passo com comandos específicos.\n3. Validação do resultado.\n\n"
        "## 4. Boas Práticas e Regras Críticas\n- Adicione diretrizes que evitam erros comuns pelo modelo.\n"
    )


def _validate_new_skill_name(skill_name: str, skills_dir: Path) -> str | None:
    if not re.match(r"^[a-z0-9-_]+$", skill_name):
        return "O nome da skill deve conter apenas letras minúsculas, números, hífens e sublinhados."
    if skill_name in RESERVED_GROUP_NAMES:
        return f"O nome '{skill_name}' é reservado para diretório de grupo de skills."
    existing = find_skill_by_name(skill_name, skills_dir)
    if existing is not None:
        return f"A skill '{skill_name}' já existe em {existing.path}!"
    return None


def cmd_add(args: argparse.Namespace, skills_dir: Path = SKILLS_DIR) -> int:
    """Cria o scaffold de uma nova skill customizada em `skills/<nome>/`.

    Exemplo:
        >>> cmd_add(build_parser().parse_args(["add", "minha-skill"]))
    """
    skill_name = args.name.lower().strip()
    validation_error = _validate_new_skill_name(skill_name, skills_dir)
    if validation_error is not None:
        log_error(validation_error)
        return 1
    skill_path = skills_dir / skill_name
    skill_path.mkdir(parents=True, exist_ok=True)
    skill_md = skill_path / "SKILL.md"
    skill_md.write_text(_build_skill_template(skill_name), encoding="utf-8")
    log_success(f"Nova skill criada com sucesso em: {skill_md}")
    log_info("Você pode editar o arquivo e rodar 'skills sync' para ativá-la globalmente!")
    return 0


def _ensure_local_bin_symlink(bin_script: Path) -> None:
    local_bin = Path.home() / ".local" / "bin"
    symlink_target = local_bin / "skills"
    local_bin.mkdir(parents=True, exist_ok=True)
    if symlink_target.exists() or symlink_target.is_symlink():
        symlink_target.unlink()
    symlink_target.symlink_to(bin_script.resolve())
    log_success(f"Link criado em: {symlink_target} -> {bin_script}")


def _ensure_shell_rc_entry(rc_path: Path, bin_script: Path) -> None:
    resolved_bin = str(bin_script.resolve())
    if rc_path.exists() and resolved_bin in rc_path.read_text(encoding="utf-8"):
        log_info(f"Alias já configurado em {rc_path}")
        return
    with open(rc_path, "a", encoding="utf-8") as rc_file:
        rc_file.write(f'\n# Skills CLI\nexport PATH="$HOME/.local/bin:$PATH"\nalias skills="{resolved_bin}"\n')
    log_success(f"Alias e PATH adicionados em {rc_path}")


def cmd_setup(args: argparse.Namespace) -> int:
    """Configura o atalho global `skills` em `~/.local/bin` e arquivos de shell (Bash/Zsh).

    Exemplo:
        >>> cmd_setup(build_parser().parse_args(["setup"]))
    """
    log_title("Configuração do Atalho Global 'skills'")
    bin_script = BIN_DIR / "skills"
    _ensure_local_bin_symlink(bin_script)
    _ensure_shell_rc_entry(Path.home() / ".bash_aliases", bin_script)
    zshrc_path = Path.home() / ".zshrc"
    if sys.platform == "darwin" or zshrc_path.exists():
        _ensure_shell_rc_entry(zshrc_path, bin_script)
    rc_reload = "~/.zshrc" if sys.platform == "darwin" else "~/.bashrc"
    print(f"\n{Colors.GREEN}{Colors.BOLD}✓ Configuração concluída!{Colors.RESET}")
    print(f"Execute {Colors.CYAN}source {rc_reload}{Colors.RESET} ou abra um novo terminal e digite {Colors.CYAN}skills --help{Colors.RESET}\n")
    return 0
