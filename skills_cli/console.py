"""Utilitários de saída formatada no terminal para a CLI."""

from __future__ import annotations


class Colors:
    """Códigos ANSI para destaque visual no terminal."""

    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"


def log_info(message: str) -> None:
    """Exibe mensagem informativa padrão no terminal.

    Exemplo:
        >>> log_info("Sincronização iniciada")
    """
    print(f"{Colors.CYAN}ℹ{Colors.RESET} {message}")


def log_success(message: str) -> None:
    """Exibe mensagem de conclusão bem-sucedida no terminal.

    Exemplo:
        >>> log_success("Skills atualizadas")
    """
    print(f"{Colors.GREEN}✓{Colors.RESET} {message}")


def log_warn(message: str) -> None:
    """Exibe aviso não-fatal no terminal.

    Exemplo:
        >>> log_warn("Conflito ignorado")
    """
    print(f"{Colors.YELLOW}⚠{Colors.RESET} {message}")


def log_error(message: str) -> None:
    """Exibe mensagem de erro no terminal.

    Exemplo:
        >>> log_error("Falha ao executar git pull")
    """
    print(f"{Colors.RED}✗{Colors.RESET} {message}")


def log_title(title: str) -> None:
    """Exibe cabeçalho de seção no terminal.

    Exemplo:
        >>> log_title("Catálogo de Skills")
    """
    print(f"\n{Colors.BOLD}{Colors.HEADER}=== {title} ==={Colors.RESET}\n")
