"""Comandos CLI para listagem, instalação, sincronização e diagnóstico de MCPs."""

from __future__ import annotations

import argparse
import re
from collections.abc import Mapping, Sequence
from pathlib import Path

from skills_cli.console import Colors, log_error, log_info, log_success, log_title, log_warn
from skills_cli.mcp_resolver import detect_browser_runtime, resolve_server_for_host
from skills_cli.mcp_store import (
    apply_server_override,
    get_mcp_target_files,
    import_untracked_mcps,
    load_mcp_overrides,
    load_mcp_servers_from_file,
    remove_mcp_server_from_file,
    save_mcp_servers_to_file,
)
from skills_cli.models import (
    CLAUDE_MCP_GLOBAL_FILE,
    GEMINI_MCP_GLOBAL_FILE,
    MCPS_FILE,
    MCPS_OVERRIDE_FILE,
    AgentTarget,
    BrowserRuntimeEnv,
    McpServerDefinition,
    McpTargetFile,
    Scope,
)


def _format_server_command(server: McpServerDefinition) -> str:
    if server.url and not server.command:
        return server.url
    return " ".join((server.command, *server.args)).strip()


def _format_mcp_presence(server_name: str, configured_names: set[str]) -> str:
    if server_name in configured_names:
        return f"{Colors.GREEN}✓ ativo{Colors.RESET}"
    return f"{Colors.DIM}-{Colors.RESET}"


def _read_configured_names(json_path: Path) -> set[str]:
    if not json_path.is_file():
        return set()
    return {entry.name for entry in load_mcp_servers_from_file(json_path)}


def print_mcp_catalog_table(
    mcps_file: Path = MCPS_FILE,
    gemini_file: Path = GEMINI_MCP_GLOBAL_FILE,
    claude_file: Path = CLAUDE_MCP_GLOBAL_FILE,
) -> int:
    """Imprime a tabela do catálogo de servidores MCP e seu status nos agentes.

    Exemplo:
        >>> count = print_mcp_catalog_table()
    """
    servers = load_mcp_servers_from_file(mcps_file)
    if not servers:
        log_warn("Nenhum servidor MCP encontrado no catálogo.")
        return 0
    gemini_names = _read_configured_names(gemini_file)
    claude_names = _read_configured_names(claude_file)
    print(f"{Colors.BOLD}{Colors.CYAN}[SERVIDORES MCP] ({len(servers)}){Colors.RESET}")
    print(f"{'Nome':<28} {'Gemini':<12} {'Claude':<12} {'Comando'}")
    print("-" * 90)
    for server in servers:
        gem_col = _format_mcp_presence(server.name, gemini_names)
        claude_col = _format_mcp_presence(server.name, claude_names)
        cmd_preview = _format_server_command(server)
        if len(cmd_preview) > 42:
            cmd_preview = cmd_preview[:39] + "..."
        print(f"{Colors.BOLD}{server.name:<28}{Colors.RESET} {gem_col:<20} {claude_col:<20} {Colors.DIM}{cmd_preview}{Colors.RESET}")
    print()
    return len(servers)


def _select_mcp_servers(
    requested_names: Sequence[str],
    catalog: Mapping[str, McpServerDefinition],
) -> list[McpServerDefinition]:
    if not requested_names:
        return list(catalog.values())
    selected: list[McpServerDefinition] = []
    for name in requested_names:
        found = catalog.get(name)
        if found is not None:
            selected.append(found)
        else:
            log_warn(f"MCP '{name}' não encontrado em {MCPS_FILE.name}. Ignorando.")
    return selected


def _resolve_servers(
    servers: Sequence[McpServerDefinition],
    runtime: BrowserRuntimeEnv,
    overrides: Mapping[str, McpServerDefinition],
) -> list[McpServerDefinition]:
    resolved: list[McpServerDefinition] = []
    for server in servers:
        with_override = apply_server_override(server, overrides)
        resolved.append(resolve_server_for_host(with_override, runtime))
    return resolved


def _apply_mcps_to_target(
    target: McpTargetFile,
    resolved_servers: Sequence[McpServerDefinition],
    dry_run: bool,
) -> None:
    print(f"🔌 Destino MCP {Colors.BOLD}[{target.agent.upper()}]{Colors.RESET}: {target.path}")
    if dry_run:
        names = ", ".join(server.name for server in resolved_servers)
        log_info(f"[DRY-RUN] Configuraria MCPs ({names}) em {target.path}\n")
        return
    save_mcp_servers_to_file(target.path, resolved_servers)
    log_success(f"{len(resolved_servers)} servidor(es) MCP sincronizado(s) para {target.agent.upper()}.\n")


def install_mcp_servers(
    requested_names: Sequence[str],
    scope: Scope,
    agent: AgentTarget,
    project_path: Path | None,
    dry_run: bool,
    mcps_file: Path = MCPS_FILE,
    override_file: Path = MCPS_OVERRIDE_FILE,
    gemini_file: Path = GEMINI_MCP_GLOBAL_FILE,
    claude_file: Path = CLAUDE_MCP_GLOBAL_FILE,
    runtime: BrowserRuntimeEnv | None = None,
) -> int:
    """Resolve servidores MCP para o SO atual e grava nos arquivos de destino.

    Exemplo:
        >>> exit_code = install_mcp_servers([], "global", "all", None, True)
    """
    catalog = {entry.name: entry for entry in load_mcp_servers_from_file(mcps_file)}
    selected = _select_mcp_servers(requested_names, catalog)
    if not selected:
        log_error("Nenhum servidor MCP válido selecionado para instalação.")
        return 1
    active_runtime = runtime or detect_browser_runtime()
    overrides = load_mcp_overrides(override_file)
    resolved = _resolve_servers(selected, active_runtime, overrides)
    targets = get_mcp_target_files(scope, agent, project_path, gemini_file, claude_file)
    for target in targets:
        _apply_mcps_to_target(target, resolved, dry_run)
    return 0


def sync_global_mcps(
    agent: AgentTarget = "all",
    mcps_file: Path = MCPS_FILE,
    override_file: Path = MCPS_OVERRIDE_FILE,
    gemini_file: Path = GEMINI_MCP_GLOBAL_FILE,
    claude_file: Path = CLAUDE_MCP_GLOBAL_FILE,
    runtime: BrowserRuntimeEnv | None = None,
) -> int:
    """Importa MCPs locais não rastreados e propaga o catálogo portátil para os agentes.

    Exemplo:
        >>> exit_code = sync_global_mcps("all")
    """
    targets = get_mcp_target_files("global", agent, None, gemini_file, claude_file)
    imported = import_untracked_mcps(targets, mcps_file)
    if imported:
        log_success(f"{len(imported)} MCP(s) importado(s) para {mcps_file.name}: {', '.join(imported)}")
    else:
        log_info("Nenhum novo servidor MCP não-rastreado.")
    return install_mcp_servers([], "global", agent, None, False, mcps_file, override_file, gemini_file, claude_file, runtime)


def print_mcp_status_section(
    mcps_file: Path = MCPS_FILE,
    gemini_file: Path = GEMINI_MCP_GLOBAL_FILE,
    claude_file: Path = CLAUDE_MCP_GLOBAL_FILE,
    runtime: BrowserRuntimeEnv | None = None,
) -> None:
    """Imprime o diagnóstico dos servidores MCP e do navegador local detectado.

    Exemplo:
        >>> print_mcp_status_section()
    """
    active_runtime = runtime or detect_browser_runtime()
    catalog_count = len(load_mcp_servers_from_file(mcps_file))
    print(f"🔌 {Colors.BOLD}Servidores MCP{Colors.RESET} (catálogo: {catalog_count}):")
    print(f"   SO / Modo Browser: {active_runtime.platform_name} ({active_runtime.mode})")
    if active_runtime.executable_path:
        print(f"   Binário Chromium: {active_runtime.executable_path}")
    if active_runtime.ld_library_path:
        print(f"   LD_LIBRARY_PATH: {active_runtime.ld_library_path}")
    print(f"   Gemini ({gemini_file}): {Colors.GREEN}{len(_read_configured_names(gemini_file))}{Colors.RESET} ativo(s)")
    print(f"   Claude ({claude_file}): {Colors.GREEN}{len(_read_configured_names(claude_file))}{Colors.RESET} ativo(s)\n")


def cmd_mcp_list(args: argparse.Namespace) -> int:
    """Lista os servidores MCP do repositório e o status nos agentes globais.

    Exemplo:
        >>> exit_code = cmd_mcp_list(argparse.Namespace())
    """
    log_title("Catálogo de Servidores MCP")
    total = print_mcp_catalog_table()
    print(f"Total: {Colors.BOLD}{total} servidor(es) MCP disponíveis.{Colors.RESET}\n")
    return 0


def cmd_mcp_install(args: argparse.Namespace) -> int:
    """Instala servidores MCP do catálogo no escopo global ou de projeto.

    Exemplo:
        >>> exit_code = cmd_mcp_install(argparse.Namespace(mcps=[], project=None, agent="all", dry_run=True))
    """
    log_title("Instalação de Servidores MCP")
    scope: Scope = "project" if args.project is not None else "global"
    project_path = Path(args.project).resolve() if args.project else None
    return install_mcp_servers(args.mcps, scope, args.agent, project_path, args.dry_run)


def cmd_mcp_sync(args: argparse.Namespace) -> int:
    """Sincroniza bidirecionalmente servidores MCP entre o catálogo e os agentes globais.

    Exemplo:
        >>> exit_code = cmd_mcp_sync(argparse.Namespace(agent="all"))
    """
    log_title("Sincronização de Servidores MCP")
    return sync_global_mcps(agent=getattr(args, "agent", "all"))


def cmd_mcp_status(args: argparse.Namespace) -> int:
    """Exibe diagnóstico detalhado do runtime de browser e MCPs configurados.

    Exemplo:
        >>> exit_code = cmd_mcp_status(argparse.Namespace())
    """
    log_title("Status dos Servidores MCP")
    print_mcp_status_section()
    return 0


def _parse_env_pairs(raw_pairs: Sequence[str]) -> tuple[tuple[str, str], ...]:
    parsed: list[tuple[str, str]] = []
    for raw_pair in raw_pairs:
        if "=" not in raw_pair:
            raise ValueError(f"Invalid '--env' entry {raw_pair!r}: expected 'KEY=VALUE' format")
        key, value = raw_pair.split("=", 1)
        parsed.append((key.strip(), value))
    return tuple(sorted(parsed))


def cmd_mcp_add(args: argparse.Namespace, mcps_file: Path = MCPS_FILE) -> int:
    """Adiciona ou atualiza um servidor MCP portátil no catálogo `mcps/servers.json`.

    Exemplo:
        >>> exit_code = cmd_mcp_add(argparse.Namespace(name="sqlite", command="npx", args=["-y", "sqlite-mcp"], url=None, env=[], force=False))
    """
    server_name = args.name.lower().strip()
    if not re.match(r"^[a-z0-9-_]+$", server_name):
        log_error(f"Nome de MCP inválido {server_name!r}: esperado kebab-case (a-z, 0-9, -, _).")
        return 1
    if not args.command and not args.url:
        log_error("Informe '--command <executável>' ou '--url <endpoint>' para registrar o MCP.")
        return 1
    existing = {entry.name: entry for entry in load_mcp_servers_from_file(mcps_file)}
    if server_name in existing and not args.force:
        log_error(f"O servidor MCP '{server_name}' já existe em {mcps_file}. Use --force para atualizar.")
        return 1
    new_entry = McpServerDefinition(
        name=server_name,
        command=args.command or "",
        args=tuple(args.args or ()),
        env=_parse_env_pairs(args.env or ()),
        url=args.url,
    )
    save_mcp_servers_to_file(mcps_file, [new_entry])
    log_success(f"Servidor MCP '{server_name}' salvo em {mcps_file}.")
    log_info("Execute 'skills mcp sync' para propagá-lo aos agentes configurados.")
    return 0


def cmd_mcp_remove(
    args: argparse.Namespace,
    mcps_file: Path = MCPS_FILE,
    gemini_file: Path = GEMINI_MCP_GLOBAL_FILE,
    claude_file: Path = CLAUDE_MCP_GLOBAL_FILE,
) -> int:
    """Remove um servidor MCP dos agentes globais e opcionalmente do catálogo central.

    Exemplo:
        >>> exit_code = cmd_mcp_remove(argparse.Namespace(name="sqlite", agent="all", keep_repo=True))
    """
    server_name = args.name.strip()
    targets = get_mcp_target_files("global", args.agent, None, gemini_file, claude_file)
    for target in targets:
        if remove_mcp_server_from_file(target.path, server_name):
            log_success(f"MCP '{server_name}' removido de {target.agent.upper()} ({target.path}).")
    if not args.keep_repo and remove_mcp_server_from_file(mcps_file, server_name):
        log_success(f"MCP '{server_name}' removido do catálogo ({mcps_file}).")
    return 0
