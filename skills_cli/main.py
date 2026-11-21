"""Parser de argumentos e ponto de entrada principal da CLI."""

from __future__ import annotations

import argparse
import sys
import traceback
from collections.abc import Sequence

from skills_cli.commands import (
    cmd_add,
    cmd_install,
    cmd_list,
    cmd_pull,
    cmd_setup,
    cmd_status,
    cmd_sync,
    cmd_update_expo,
)
from skills_cli.console import log_error
from skills_cli.mcp_commands import (
    cmd_mcp_add,
    cmd_mcp_install,
    cmd_mcp_list,
    cmd_mcp_remove,
    cmd_mcp_status,
    cmd_mcp_sync,
)


def _add_install_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("install", help="Instala skills globalmente ou no projeto local")
    parser.add_argument("skills", nargs="*", help="Nomes das skills específicas a instalar (opcional)")
    parser.add_argument("-g", "--global", dest="global_install", action="store_true", default=True, help="Instalar globalmente")
    parser.add_argument("-p", "--project", nargs="?", const=".", default=None, help="Instalar em um projeto específico")
    parser.add_argument("-a", "--agent", choices=["all", "gemini", "claude"], default="all", help="Agente alvo (padrão: all)")
    parser.add_argument("-m", "--mode", choices=["symlink", "copy"], default="symlink", help="Modo de instalação")
    parser.add_argument("-f", "--force", action="store_true", help="Sobrescrever destinos conflitantes")
    parser.add_argument("--dry-run", action="store_true", help="Simular operação sem aplicar alterações")
    parser.set_defaults(func=cmd_install)


def _add_sync_and_remote_parsers(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    p_sync = subparsers.add_parser("sync", help="Sincroniza skills e MCPs com os destinos globais")
    p_sync.add_argument("-e", "--expo", action="store_true", help="Também atualiza as skills do upstream oficial da Expo")
    p_sync.add_argument("-a", "--agent", choices=["all", "gemini", "claude"], default="all", help="Agente alvo (padrão: all)")
    p_sync.add_argument("--no-mcp", action="store_true", help="Pula a sincronização automática de servidores MCP")
    p_sync.set_defaults(func=cmd_sync)

    p_pull = subparsers.add_parser("pull", help="Executa git pull --ff-only no repo e sincroniza os links globais")
    p_pull.add_argument("-a", "--agent", choices=["all", "gemini", "claude"], default="all", help="Agente alvo (padrão: all)")
    p_pull.set_defaults(func=cmd_pull)

    p_expo = subparsers.add_parser("update-expo", help="Atualiza skills do repositório oficial da Expo (github.com/expo/skills)")
    p_expo.add_argument("--summary-json", default=None, help="Salva resumo estruturado em JSON no caminho indicado")
    p_expo.set_defaults(func=cmd_update_expo)


def _add_catalog_parsers(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    p_list = subparsers.add_parser("list", aliases=["ls"], help="Lista todas as skills disponíveis e seus status")
    p_list.set_defaults(func=cmd_list)

    p_status = subparsers.add_parser("status", help="Exibe status geral das pastas e conexões de skills")
    p_status.set_defaults(func=cmd_status)

    p_add = subparsers.add_parser("add", help="Cria o scaffold de uma nova skill")
    p_add.add_argument("name", help="Nome da nova skill (ex: minha-nova-skill)")
    p_add.set_defaults(func=cmd_add)

    p_setup = subparsers.add_parser("setup", aliases=["link"], help="Configura o comando 'skills' no PATH para uso global")
    p_setup.set_defaults(func=cmd_setup)


def _add_mcp_install_and_sync(mcp_sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    p_install = mcp_sub.add_parser("install", help="Instala servidores MCP globalmente ou no projeto local")
    p_install.add_argument("mcps", nargs="*", help="Nomes dos servidores MCP a instalar (opcional)")
    p_install.add_argument("-g", "--global", dest="global_install", action="store_true", default=True, help="Instalar globalmente")
    p_install.add_argument("-p", "--project", nargs="?", const=".", default=None, help="Instalar em um projeto específico")
    p_install.add_argument("-a", "--agent", choices=["all", "gemini", "claude"], default="all", help="Agente alvo (padrão: all)")
    p_install.add_argument("--dry-run", action="store_true", help="Simular operação sem aplicar alterações")
    p_install.set_defaults(func=cmd_mcp_install)

    p_sync = mcp_sub.add_parser("sync", help="Sincroniza servidores MCP entre repositório, Gemini e Claude")
    p_sync.add_argument("-a", "--agent", choices=["all", "gemini", "claude"], default="all", help="Agente alvo (padrão: all)")
    p_sync.set_defaults(func=cmd_mcp_sync)


def _add_mcp_catalog_actions(mcp_sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    p_list = mcp_sub.add_parser("list", aliases=["ls"], help="Lista servidores MCP do catálogo e status nos agentes")
    p_list.set_defaults(func=cmd_mcp_list)
    p_status = mcp_sub.add_parser("status", help="Exibe diagnóstico de runtime de browser e MCPs ativos")
    p_status.set_defaults(func=cmd_mcp_status)
    p_add = mcp_sub.add_parser("add", help="Registra um servidor MCP em mcps/servers.json")
    p_add.add_argument("name", help="Nome do servidor MCP em kebab-case")
    p_add.add_argument("--command", default="", help="Executável principal (para transporte stdio)")
    p_add.add_argument("--args", nargs="*", default=[], help="Argumentos passados ao comando")
    p_add.add_argument("--url", default=None, help="Endpoint Streamable HTTP (para servidores remotos)")
    p_add.add_argument("--env", nargs="*", default=[], help="Variáveis de ambiente no formato CHAVE=VALOR")
    p_add.add_argument("-f", "--force", action="store_true", help="Atualiza o servidor caso já exista")
    p_add.set_defaults(func=cmd_mcp_add)
    p_rm = mcp_sub.add_parser("remove", aliases=["rm"], help="Remove um servidor MCP dos agentes e do catálogo")
    p_rm.add_argument("name", help="Nome do servidor MCP a remover")
    p_rm.add_argument("-a", "--agent", choices=["all", "gemini", "claude"], default="all", help="Agente alvo (padrão: all)")
    p_rm.add_argument("--keep-repo", action="store_true", help="Mantém o servidor no catálogo mcps/servers.json")
    p_rm.set_defaults(func=cmd_mcp_remove)


def _add_mcp_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    p_mcp = subparsers.add_parser("mcp", help="Gerencia servidores MCP sincronizados entre Gemini e Claude")
    p_mcp.set_defaults(func=cmd_mcp_list)
    mcp_sub = p_mcp.add_subparsers(dest="mcp_command", help="Operações MCP disponíveis")
    _add_mcp_install_and_sync(mcp_sub)
    _add_mcp_catalog_actions(mcp_sub)


def build_parser() -> argparse.ArgumentParser:
    """Constrói e retorna o parser completo de comandos da CLI.

    Exemplo:
        >>> parser = build_parser()
    """
    parser = argparse.ArgumentParser(
        prog="skills",
        description="Gerenciador Central de Skills e MCPs para Gemini (Antigravity) e Claude Code.",
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Comandos disponíveis")
    _add_install_parser(subparsers)
    _add_sync_and_remote_parsers(subparsers)
    _add_catalog_parsers(subparsers)
    _add_mcp_parser(subparsers)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Executa a CLI de gerenciamento de skills e retorna o código de saída.

    Exemplo:
        >>> code = main(["status"])
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 0
    try:
        return int(args.func(args) or 0)
    except KeyboardInterrupt:
        print("\nOperação cancelada pelo usuário.")
        return 130
    except Exception as exc:
        log_error(f"Erro inesperado: {exc}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
