"""Leitura, merge não-destrutivo e importação reversa de configurações MCP."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path

from skills_cli.mcp_resolver import sanitize_server_for_repo
from skills_cli.models import (
    CLAUDE_MCP_GLOBAL_FILE,
    GEMINI_MCP_GLOBAL_FILE,
    AgentTarget,
    McpServerDefinition,
    McpTargetFile,
    Scope,
)


def _select_mcp_targets(
    agent: AgentTarget,
    gemini_file: Path,
    claude_file: Path,
) -> list[McpTargetFile]:
    targets: list[McpTargetFile] = []
    if agent in ("all", "gemini"):
        targets.append(McpTargetFile(agent="gemini", path=gemini_file))
    if agent in ("all", "claude"):
        targets.append(McpTargetFile(agent="claude", path=claude_file))
    return targets


def get_mcp_target_files(
    scope: Scope,
    agent: AgentTarget,
    project_path: Path | None = None,
    gemini_file: Path = GEMINI_MCP_GLOBAL_FILE,
    claude_file: Path = CLAUDE_MCP_GLOBAL_FILE,
) -> list[McpTargetFile]:
    """Retorna os arquivos de configuração MCP alvo para o escopo e agente informados.

    Exemplo:
        >>> targets = get_mcp_target_files("global", "all")
    """
    if scope == "global":
        return _select_mcp_targets(agent, gemini_file, claude_file)
    base_dir = project_path or Path.cwd()
    return _select_mcp_targets(agent, base_dir / ".agents" / "mcp_config.json", base_dir / ".mcp.json")


def _read_json_mapping(json_path: Path) -> dict[str, object]:
    if not json_path.is_file():
        return {}
    raw_text = json_path.read_text(encoding="utf-8").strip()
    if not raw_text:
        return {}
    parsed = json.loads(raw_text)
    if not isinstance(parsed, dict):
        raise ValueError(
            f"Invalid MCP JSON root in '{json_path}': received {type(parsed).__name__}, expected JSON object"
        )
    return parsed


def _parse_args_tuple(raw_args: object, server_name: str, source_path: Path) -> tuple[str, ...]:
    if raw_args is None:
        return ()
    if not isinstance(raw_args, list) or not all(isinstance(arg, str) for arg in raw_args):
        raise ValueError(
            f"Invalid 'args' for MCP server '{server_name}' in '{source_path}': "
            f"received {raw_args!r}, expected list[str]"
        )
    return tuple(raw_args)


def _parse_env_tuple(raw_env: object, server_name: str, source_path: Path) -> tuple[tuple[str, str], ...]:
    if raw_env is None:
        return ()
    if not isinstance(raw_env, dict):
        raise ValueError(
            f"Invalid 'env' for MCP server '{server_name}' in '{source_path}': "
            f"received {raw_env!r}, expected dict[str, str]"
        )
    return tuple(sorted((str(k), str(v)) for k, v in raw_env.items()))


def _parse_server_entry(name: str, raw_entry: object, source_path: Path) -> McpServerDefinition:
    if not isinstance(raw_entry, dict):
        raise ValueError(
            f"Invalid MCP entry '{name}' in '{source_path}': received {raw_entry!r}, expected JSON object"
        )
    command = raw_entry.get("command") or ""
    url = raw_entry.get("url") or raw_entry.get("serverUrl")
    if not isinstance(command, str) or (url is not None and not isinstance(url, str)):
        raise ValueError(
            f"Invalid 'command'/'url' for MCP '{name}' in '{source_path}': expected strings"
        )
    return McpServerDefinition(
        name=name,
        command=command,
        args=_parse_args_tuple(raw_entry.get("args"), name, source_path),
        env=_parse_env_tuple(raw_entry.get("env"), name, source_path),
        url=url,
    )


def load_mcp_servers_from_file(json_path: Path) -> list[McpServerDefinition]:
    """Carrega todas as definições sob `mcpServers` em um arquivo JSON.

    Exemplo:
        >>> servers = load_mcp_servers_from_file(Path("mcps/servers.json"))
    """
    document = _read_json_mapping(json_path)
    raw_servers = document.get("mcpServers")
    if raw_servers is None:
        return []
    if not isinstance(raw_servers, dict):
        raise ValueError(
            f"Invalid 'mcpServers' section in '{json_path}': received {type(raw_servers).__name__}, expected object"
        )
    return [_parse_server_entry(str(name), entry, json_path) for name, entry in raw_servers.items()]


def load_mcp_overrides(override_path: Path) -> dict[str, McpServerDefinition]:
    """Carrega sobrescritas locais opcionais por servidor a partir de `local.override.json`.

    Exemplo:
        >>> overrides = load_mcp_overrides(Path("mcps/local.override.json"))
    """
    if not override_path.is_file():
        return {}
    return {server.name: server for server in load_mcp_servers_from_file(override_path)}


def apply_server_override(
    server: McpServerDefinition,
    overrides: Mapping[str, McpServerDefinition],
) -> McpServerDefinition:
    """Aplica argumentos e variáveis extras de `overrides` quando existir entrada para o servidor.

    Exemplo:
        >>> merged = apply_server_override(server, overrides)
    """
    override = overrides.get(server.name)
    if override is None:
        return server
    merged_env = dict(server.env)
    merged_env.update(dict(override.env))
    return McpServerDefinition(
        name=server.name,
        command=override.command or server.command,
        args=server.args + override.args,
        env=tuple(sorted(merged_env.items())),
        url=override.url or server.url,
    )


def _serialize_server_entry(server: McpServerDefinition) -> dict[str, object]:
    serialized: dict[str, object] = {}
    if server.url and not server.command:
        serialized["url"] = server.url
    else:
        serialized["command"] = server.command
        if server.args:
            serialized["args"] = list(server.args)
    if server.env:
        serialized["env"] = dict(server.env)
    return serialized


def _write_json_mapping(json_path: Path, document: Mapping[str, object]) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def save_mcp_servers_to_file(
    json_path: Path,
    servers: Sequence[McpServerDefinition],
    replace_all: bool = False,
) -> None:
    """Salva servidores MCP em `json_path` preservando outras chaves de topo (ex: `~/.claude.json`).

    Exemplo:
        >>> save_mcp_servers_to_file(Path("~/.claude.json"), servers)
    """
    document = _read_json_mapping(json_path)
    existing = document.get("mcpServers")
    merged: dict[str, object] = {} if replace_all or not isinstance(existing, dict) else dict(existing)
    for server in servers:
        merged[server.name] = _serialize_server_entry(server)
    document["mcpServers"] = merged
    _write_json_mapping(json_path, document)


def remove_mcp_server_from_file(json_path: Path, server_name: str) -> bool:
    """Remove `server_name` de `mcpServers` em `json_path` preservando o restante do JSON.

    Exemplo:
        >>> removed = remove_mcp_server_from_file(Path("mcps/servers.json"), "custom-mcp")
    """
    if not json_path.is_file():
        return False
    document = _read_json_mapping(json_path)
    raw_servers = document.get("mcpServers")
    if not isinstance(raw_servers, dict) or server_name not in raw_servers:
        return False
    del raw_servers[server_name]
    _write_json_mapping(json_path, document)
    return True


def _collect_new_servers_from_target(
    target: McpTargetFile,
    known_names: set[str],
) -> list[McpServerDefinition]:
    if not target.path.is_file():
        return []
    discovered: list[McpServerDefinition] = []
    for candidate in load_mcp_servers_from_file(target.path):
        if candidate.name not in known_names:
            known_names.add(candidate.name)
            discovered.append(sanitize_server_for_repo(candidate))
    return discovered


def import_untracked_mcps(targets: Sequence[McpTargetFile], mcps_file: Path) -> list[str]:
    """Importa servidores MCP novos dos agentes globais para `mcps/servers.json` sanitizados.

    Exemplo:
        >>> imported = import_untracked_mcps(targets, Path("mcps/servers.json"))
    """
    repo_servers = load_mcp_servers_from_file(mcps_file)
    known_names = {server.name for server in repo_servers}
    newly_imported: list[McpServerDefinition] = []
    for target in targets:
        newly_imported.extend(_collect_new_servers_from_target(target, known_names))
    if not newly_imported:
        return []
    save_mcp_servers_to_file(mcps_file, [*repo_servers, *newly_imported], replace_all=True)
    return [server.name for server in newly_imported]
