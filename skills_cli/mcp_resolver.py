"""Detecção multiplataforma de navegador (Linux e macOS) e sanitização de configs MCP."""

from __future__ import annotations

import shutil
import sys
from collections.abc import Callable
from pathlib import Path

from skills_cli.models import BrowserRuntimeEnv, McpServerDefinition

LINUX_SYSTEM_CHROME_BINS: tuple[str, ...] = (
    "google-chrome",
    "google-chrome-stable",
    "chromium",
    "chromium-browser",
)
BROWSER_EXECUTABLE_FLAGS: tuple[str, ...] = ("--executable-path", "--executablePath")


def _extract_chromium_revision(candidate_path: Path) -> int:
    for part in candidate_path.parts:
        if part.startswith("chromium-") and part[9:].isdigit():
            return int(part[9:])
    return -1


def _find_macos_system_chrome(home_dir: Path, system_apps_dir: Path) -> Path | None:
    system_binary = system_apps_dir / "Google Chrome.app/Contents/MacOS/Google Chrome"
    user_binary = home_dir / "Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    for candidate in (system_binary, user_binary):
        if candidate.is_file():
            return candidate
    return None


def _find_macos_playwright_chrome(home_dir: Path) -> Path | None:
    cache_dir = home_dir / "Library" / "Caches" / "ms-playwright"
    if not cache_dir.is_dir():
        return None
    pattern = "chromium-*/chrome-mac-*/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
    matches = sorted(cache_dir.glob(pattern), key=_extract_chromium_revision, reverse=True)
    for binary_path in matches:
        if binary_path.is_file():
            return binary_path
    return None


def _find_linux_system_chrome(which_fn: Callable[[str], str | None]) -> str | None:
    for binary_name in LINUX_SYSTEM_CHROME_BINS:
        resolved = which_fn(binary_name)
        if resolved:
            return resolved
    return None


def _find_linux_playwright_chrome(home_dir: Path) -> Path | None:
    cache_dir = home_dir / ".cache" / "ms-playwright"
    if not cache_dir.is_dir():
        return None
    matches = sorted(cache_dir.glob("chromium-*/chrome-linux64/chrome"), key=_extract_chromium_revision, reverse=True)
    for binary_path in matches:
        if binary_path.is_file():
            return binary_path
    return None


def _find_linux_playwright_deps(home_dir: Path) -> Path | None:
    deps_dir = home_dir / ".local" / "lib" / "playwright-deps" / "usr" / "lib" / "x86_64-linux-gnu"
    return deps_dir if deps_dir.is_dir() else None


def _detect_macos_runtime(home_dir: Path, system_apps_dir: Path) -> BrowserRuntimeEnv:
    if _find_macos_system_chrome(home_dir, system_apps_dir) is not None:
        return BrowserRuntimeEnv("darwin", "system-macos", None, None)
    cached_chrome = _find_macos_playwright_chrome(home_dir)
    if cached_chrome is not None:
        return BrowserRuntimeEnv("darwin", "playwright-cache-macos", str(cached_chrome), None)
    return BrowserRuntimeEnv("darwin", "default", None, None)


def _detect_linux_runtime(home_dir: Path, which_fn: Callable[[str], str | None]) -> BrowserRuntimeEnv:
    if _find_linux_system_chrome(which_fn) is not None:
        return BrowserRuntimeEnv("linux", "system-linux", None, None)
    cached_chrome = _find_linux_playwright_chrome(home_dir)
    deps_dir = _find_linux_playwright_deps(home_dir)
    if cached_chrome is None and deps_dir is None:
        return BrowserRuntimeEnv("linux", "default", None, None)
    return BrowserRuntimeEnv(
        platform_name="linux",
        mode="playwright-cache-linux",
        executable_path=str(cached_chrome) if cached_chrome else None,
        ld_library_path=str(deps_dir) if deps_dir else None,
    )


def detect_browser_runtime(
    platform_name: str | None = None,
    home_dir: Path | None = None,
    which_fn: Callable[[str], str | None] = shutil.which,
    system_apps_dir: Path | None = None,
) -> BrowserRuntimeEnv:
    """Detecta o navegador local disponível no Linux ou macOS para MCPs de browser.

    Exemplo:
        >>> runtime = detect_browser_runtime()
    """
    active_platform = platform_name or sys.platform
    resolved_home = home_dir or Path.home()
    resolved_apps = system_apps_dir or Path("/Applications")
    if active_platform == "darwin":
        return _detect_macos_runtime(resolved_home, resolved_apps)
    if active_platform.startswith("linux"):
        return _detect_linux_runtime(resolved_home, which_fn)
    return BrowserRuntimeEnv(active_platform, "default", None, None)


def _resolve_browser_flag(server: McpServerDefinition) -> str | None:
    if server.name == "playwright" or any("@playwright/mcp" in arg for arg in server.args):
        return "--executable-path"
    if server.name == "chrome-devtools" or any("chrome-devtools-mcp" in arg for arg in server.args):
        return "--executablePath"
    return None


def _strip_browser_args(args: tuple[str, ...]) -> tuple[str, ...]:
    cleaned: list[str] = []
    skip_next = False
    for arg in args:
        if skip_next:
            skip_next = False
            continue
        if arg in BROWSER_EXECUTABLE_FLAGS:
            skip_next = True
            continue
        if not arg.startswith(("--executable-path=", "--executablePath=")):
            cleaned.append(arg)
    return tuple(cleaned)


def _strip_playwright_ld_library_path(env: tuple[tuple[str, str], ...]) -> tuple[tuple[str, str], ...]:
    kept: list[tuple[str, str]] = []
    for key, value in env:
        is_local_deps = key == "LD_LIBRARY_PATH" and ("playwright-deps" in value or ".local/lib" in value)
        if not is_local_deps:
            kept.append((key, value))
    return tuple(kept)


def sanitize_server_for_repo(server: McpServerDefinition) -> McpServerDefinition:
    """Remove caminhos locais de navegador e `LD_LIBRARY_PATH` antes de salvar no Git.

    Exemplo:
        >>> clean = sanitize_server_for_repo(local_server)
    """
    return McpServerDefinition(
        name=server.name,
        command=server.command,
        args=_strip_browser_args(server.args),
        env=_strip_playwright_ld_library_path(server.env),
        url=server.url,
    )


def _merge_env_var(
    env: tuple[tuple[str, str], ...],
    var_name: str,
    var_value: str,
) -> tuple[tuple[str, str], ...]:
    env_map = dict(env)
    env_map[var_name] = var_value
    return tuple(sorted(env_map.items()))


def resolve_server_for_host(
    server: McpServerDefinition,
    runtime: BrowserRuntimeEnv,
) -> McpServerDefinition:
    """Adapta um servidor MCP portátil às flags de navegador do sistema operacional atual.

    Exemplo:
        >>> resolved = resolve_server_for_host(server, detect_browser_runtime())
    """
    flag = _resolve_browser_flag(server)
    if flag is None:
        return server
    resolved_args = _strip_browser_args(server.args)
    resolved_env = _strip_playwright_ld_library_path(server.env)
    if runtime.executable_path:
        resolved_args = resolved_args + (flag, runtime.executable_path)
    if runtime.ld_library_path:
        resolved_env = _merge_env_var(resolved_env, "LD_LIBRARY_PATH", runtime.ld_library_path)
    return McpServerDefinition(
        name=server.name,
        command=server.command,
        args=resolved_args,
        env=resolved_env,
        url=server.url,
    )
