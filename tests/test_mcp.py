"""Testes unitários para detecção de browser, sanitização e sincronização de MCPs."""

from __future__ import annotations

import argparse
import json
import tempfile
import unittest
from pathlib import Path

from skills_cli.mcp_commands import cmd_mcp_add, cmd_mcp_remove, sync_global_mcps
from skills_cli.mcp_resolver import (
    detect_browser_runtime,
    resolve_server_for_host,
    sanitize_server_for_repo,
)
from skills_cli.mcp_store import (
    get_mcp_target_files,
    load_mcp_servers_from_file,
    save_mcp_servers_to_file,
)
from skills_cli.models import BrowserRuntimeEnv, McpServerDefinition


class FakeWhichLookup:
    """Fake nomeado para substituir `shutil.which` nos testes de detecção de SO."""

    def __init__(self, mapping: dict[str, str]) -> None:
        self.mapping = mapping

    def __call__(self, binary_name: str) -> str | None:
        return self.mapping.get(binary_name)


def _touch_executable(file_path: Path) -> Path:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text("#!/bin/sh\n", encoding="utf-8")
    return file_path


class McpResolverTests(unittest.TestCase):
    """Valida resolução cross-platform (Linux e macOS) e sanitização para Git."""

    def test_linux_selects_highest_playwright_revision_and_deps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_name:
            home = Path(tmp_name)
            _touch_executable(home / ".cache/ms-playwright/chromium-1200/chrome-linux64/chrome")
            newest = _touch_executable(home / ".cache/ms-playwright/chromium-1248/chrome-linux64/chrome")
            deps_dir = home / ".local/lib/playwright-deps/usr/lib/x86_64-linux-gnu"
            deps_dir.mkdir(parents=True)
            runtime = detect_browser_runtime("linux", home_dir=home, which_fn=FakeWhichLookup({}))
            self.assertEqual(runtime.mode, "playwright-cache-linux")
            self.assertEqual(runtime.executable_path, str(newest))
            self.assertEqual(runtime.ld_library_path, str(deps_dir))

    def test_macos_prefers_system_chrome_without_extra_flags(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_name:
            root = Path(tmp_name)
            apps_dir = root / "Applications"
            _touch_executable(apps_dir / "Google Chrome.app/Contents/MacOS/Google Chrome")
            runtime = detect_browser_runtime("darwin", home_dir=root / "home", system_apps_dir=apps_dir)
            self.assertEqual(runtime.mode, "system-macos")
            self.assertIsNone(runtime.executable_path)
            self.assertIsNone(runtime.ld_library_path)

    def test_macos_falls_back_to_playwright_cache_when_system_chrome_absent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_name:
            root = Path(tmp_name)
            home = root / "home"
            cached = _touch_executable(
                home / "Library/Caches/ms-playwright/chromium-1248/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
            )
            runtime = detect_browser_runtime("darwin", home_dir=home, system_apps_dir=root / "Applications")
            self.assertEqual(runtime.mode, "playwright-cache-macos")
            self.assertEqual(runtime.executable_path, str(cached))
            self.assertIsNone(runtime.ld_library_path)

    def test_resolve_server_injects_correct_flags_for_each_browser_mcp(self) -> None:
        runtime = BrowserRuntimeEnv("linux", "playwright-cache-linux", "/opt/chrome/chrome", "/opt/deps")
        pw = McpServerDefinition("playwright", "npx", ("-y", "@playwright/mcp"))
        cdt = McpServerDefinition("chrome-devtools", "npx", ("-y", "chrome-devtools-mcp@latest"))
        resolved_pw = resolve_server_for_host(pw, runtime)
        resolved_cdt = resolve_server_for_host(cdt, runtime)
        self.assertEqual(resolved_pw.args, ("-y", "@playwright/mcp", "--executable-path", "/opt/chrome/chrome"))
        self.assertEqual(resolved_cdt.args, ("-y", "chrome-devtools-mcp@latest", "--executablePath", "/opt/chrome/chrome"))
        self.assertEqual(dict(resolved_pw.env)["LD_LIBRARY_PATH"], "/opt/deps")
        self.assertEqual(dict(resolved_cdt.env)["LD_LIBRARY_PATH"], "/opt/deps")

    def test_sanitize_server_strips_local_paths_and_deps(self) -> None:
        dirty = McpServerDefinition(
            name="chrome-devtools",
            command="npx",
            args=("-y", "chrome-devtools-mcp@latest", "--executablePath", "/home/user/.cache/chrome"),
            env=(("LD_LIBRARY_PATH", "/home/user/.local/lib/playwright-deps/usr/lib/x86_64-linux-gnu"), ("NODE_ENV", "test")),
        )
        clean = sanitize_server_for_repo(dirty)
        self.assertEqual(clean.args, ("-y", "chrome-devtools-mcp@latest"))
        self.assertEqual(clean.env, (("NODE_ENV", "test"),))


class McpStoreAndSyncTests(unittest.TestCase):
    """Valida merge não-destrutivo em arquivos de agente, importação reversa e comandos."""

    def test_save_preserves_existing_keys_in_claude_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_name:
            claude_file = Path(tmp_name) / ".claude.json"
            claude_file.write_text(json.dumps({"numStartups": 42, "projects": {"/app": {}}}), encoding="utf-8")
            server = McpServerDefinition("playwright", "npx", ("-y", "@playwright/mcp"))
            save_mcp_servers_to_file(claude_file, [server])
            saved = json.loads(claude_file.read_text(encoding="utf-8"))
            self.assertEqual(saved["numStartups"], 42)
            self.assertEqual(saved["projects"], {"/app": {}})
            self.assertIn("playwright", saved["mcpServers"])

    def test_sync_global_mcps_imports_untracked_and_propagates_to_both_agents(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_name:
            root = Path(tmp_name)
            mcps_file = root / "mcps" / "servers.json"
            gemini_file = root / "gemini" / "mcp_config.json"
            claude_file = root / ".claude.json"
            save_mcp_servers_to_file(mcps_file, [McpServerDefinition("playwright", "npx", ("-y", "@playwright/mcp"))])
            save_mcp_servers_to_file(
                gemini_file,
                [McpServerDefinition("local-tool", "npx", ("-y", "tool-mcp", "--executable-path", "/tmp/chrome"))],
            )
            runtime = BrowserRuntimeEnv("darwin", "system-macos", None, None)
            exit_code = sync_global_mcps(
                agent="all",
                mcps_file=mcps_file,
                override_file=root / "mcps" / "local.override.json",
                gemini_file=gemini_file,
                claude_file=claude_file,
                runtime=runtime,
            )
            self.assertEqual(exit_code, 0)
            repo_names = {entry.name: entry for entry in load_mcp_servers_from_file(mcps_file)}
            self.assertIn("local-tool", repo_names)
            self.assertEqual(repo_names["local-tool"].args, ("-y", "tool-mcp"))
            claude_names = {entry.name for entry in load_mcp_servers_from_file(claude_file)}
            self.assertEqual(claude_names, {"playwright", "local-tool"})

    def test_cmd_mcp_add_remove_and_project_targets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_name:
            root = Path(tmp_name)
            mcps_file = root / "mcps" / "servers.json"
            gemini_file = root / "gemini.json"
            claude_file = root / "claude.json"
            add_args = argparse.Namespace(
                name="sqlite-helper", command="npx", args=["-y", "sqlite-mcp"], url=None, env=["DB=ro"], force=False
            )
            self.assertEqual(cmd_mcp_add(add_args, mcps_file=mcps_file), 0)
            save_mcp_servers_to_file(gemini_file, load_mcp_servers_from_file(mcps_file))
            rm_args = argparse.Namespace(name="sqlite-helper", agent="all", keep_repo=False)
            self.assertEqual(cmd_mcp_remove(rm_args, mcps_file, gemini_file, claude_file), 0)
            self.assertEqual(load_mcp_servers_from_file(mcps_file), [])
            self.assertEqual(load_mcp_servers_from_file(gemini_file), [])
            project_targets = get_mcp_target_files("project", "all", root / "proj")
            self.assertEqual([t.path for t in project_targets], [root / "proj/.agents/mcp_config.json", root / "proj/.mcp.json"])
