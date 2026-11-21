"""Implementações Fake nomeadas para isolar operações Git nos testes."""

from __future__ import annotations

import shutil
from pathlib import Path

from skills_cli.git_client import GitCommandResult


class FakeGitClient:
    """Fake nomeado de `GitClient` para testes unitários sem acesso à rede ou subprocessos."""

    def __init__(
        self,
        upstream_tree: Path | None = None,
        commit_sha: str = "abcdef1234567890",
        clone_error: str | None = None,
        pull_result: GitCommandResult | None = None,
        short_status_result: GitCommandResult | None = None,
    ) -> None:
        self.upstream_tree = upstream_tree
        self.commit_sha = commit_sha
        self.clone_error = clone_error
        self.pull_result = pull_result or GitCommandResult(0, "Already up to date.\n", "")
        self.short_status_result = short_status_result or GitCommandResult(0, "", "")
        self.cloned_requests: list[tuple[str, str, Path]] = []
        self.pull_calls: list[Path] = []

    def clone_shallow(self, repo_url: str, branch: str, dest_dir: Path) -> GitCommandResult:
        """Simula clone raso copiando a árvore de fixtures configurada.

        Exemplo:
            >>> res = fake_client.clone_shallow("https://example.com/expo.git", "main", dest)
        """
        self.cloned_requests.append((repo_url, branch, dest_dir))
        if self.clone_error is not None:
            return GitCommandResult(1, "", self.clone_error)
        if self.upstream_tree is not None and self.upstream_tree.is_dir():
            shutil.copytree(self.upstream_tree, dest_dir, dirs_exist_ok=True)
        return GitCommandResult(0, "", "")

    def get_head_commit(self, repo_dir: Path) -> str:
        """Retorna o commit SHA configurado para o repositório simulado.

        Exemplo:
            >>> sha = fake_client.get_head_commit(Path("/tmp/clone"))
        """
        return self.commit_sha

    def pull_fast_forward(self, repo_dir: Path) -> GitCommandResult:
        """Registra a chamada e retorna o resultado simulado de `git pull --ff-only`.

        Exemplo:
            >>> res = fake_client.pull_fast_forward(Path("/tmp/repo"))
        """
        self.pull_calls.append(repo_dir)
        return self.pull_result

    def get_short_status(self, repo_dir: Path) -> GitCommandResult:
        """Retorna o resultado simulado de `git status --short`.

        Exemplo:
            >>> res = fake_client.get_short_status(Path("/tmp/repo"))
        """
        return self.short_status_result
