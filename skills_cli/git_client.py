"""Abstração de operações Git para sincronização local e upstream."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class GitCommandResult:
    """Resultado encapsulado de um comando Git executado."""

    returncode: int
    stdout: str
    stderr: str


class GitClient(Protocol):
    """Protocolo de cliente Git para isolar chamadas externas e facilitar testes."""

    def clone_shallow(self, repo_url: str, branch: str, dest_dir: Path) -> GitCommandResult:
        """Executa clone raso de um repositório remoto em `dest_dir`.

        Exemplo:
            >>> result = client.clone_shallow("https://github.com/expo/skills.git", "main", Path("/tmp/out"))
        """
        ...

    def get_head_commit(self, repo_dir: Path) -> str:
        """Retorna o hash completo do commit HEAD em `repo_dir`.

        Exemplo:
            >>> sha = client.get_head_commit(Path("/tmp/out"))
        """
        ...

    def pull_fast_forward(self, repo_dir: Path) -> GitCommandResult:
        """Executa `git pull --ff-only` no repositório indicado.

        Exemplo:
            >>> result = client.pull_fast_forward(Path("/home/joaop/myskills"))
        """
        ...

    def get_short_status(self, repo_dir: Path) -> GitCommandResult:
        """Executa `git status --short` no repositório indicado.

        Exemplo:
            >>> result = client.get_short_status(Path("/home/joaop/myskills"))
        """
        ...


class SubprocessGitClient:
    """Implementação padrão de `GitClient` utilizando o binário `git` do sistema."""

    def _run(self, command: list[str], cwd: Path | None = None) -> GitCommandResult:
        completed = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
        return GitCommandResult(
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )

    def clone_shallow(self, repo_url: str, branch: str, dest_dir: Path) -> GitCommandResult:
        """Executa `git clone --depth 1 --single-branch` para o diretório de destino.

        Exemplo:
            >>> res = SubprocessGitClient().clone_shallow("https://example.com/repo.git", "main", Path("/tmp/x"))
        """
        return self._run(
            ["git", "clone", "--depth", "1", "--single-branch", "--branch", branch, repo_url, str(dest_dir)]
        )

    def get_head_commit(self, repo_dir: Path) -> str:
        """Retorna o SHA do commit HEAD em `repo_dir`, ou `'unknown'` em caso de falha.

        Exemplo:
            >>> sha = SubprocessGitClient().get_head_commit(Path("/home/joaop/myskills"))
        """
        result = self._run(["git", "rev-parse", "HEAD"], cwd=repo_dir)
        return result.stdout.strip() if result.returncode == 0 else "unknown"

    def pull_fast_forward(self, repo_dir: Path) -> GitCommandResult:
        """Atualiza o repositório local via `git pull --ff-only`.

        Exemplo:
            >>> res = SubprocessGitClient().pull_fast_forward(Path("/home/joaop/myskills"))
        """
        return self._run(["git", "pull", "--ff-only"], cwd=repo_dir)

    def get_short_status(self, repo_dir: Path) -> GitCommandResult:
        """Obtém o status resumido do repositório local com `git status --short`.

        Exemplo:
            >>> res = SubprocessGitClient().get_short_status(Path("/home/joaop/myskills"))
        """
        return self._run(["git", "status", "--short"], cwd=repo_dir)
