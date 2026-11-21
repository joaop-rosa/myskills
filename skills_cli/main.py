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
    p_sync = subparsers.add_parser("sync", help="Sincroniza skills com os destinos globais e importa novas")
    p_sync.add_argument("-e", "--expo", action="store_true", help="Também atualiza as skills do upstream oficial da Expo")
    p_sync.add_argument("-a", "--agent", choices=["all", "gemini", "claude"], default="all", help="Agente alvo (padrão: all)")
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


def build_parser() -> argparse.ArgumentParser:
    """Constrói e retorna o parser completo de comandos da CLI.

    Exemplo:
        >>> parser = build_parser()
    """
    parser = argparse.ArgumentParser(
        prog="skills",
        description="Gerenciador Central de Skills para Gemini (Antigravity) e Claude Code.",
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Comandos disponíveis")
    _add_install_parser(subparsers)
    _add_sync_and_remote_parsers(subparsers)
    _add_catalog_parsers(subparsers)
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
