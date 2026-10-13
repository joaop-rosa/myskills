#!/usr/bin/env python3
"""
CLI de Gerenciamento de Skills para Gemini (Antigravity) e Claude Code.
Permite instalar, sincronizar, listar e atualizar skills locais e upstream (Expo).
"""

import os
import sys
import json
import shutil
import subprocess
import argparse
import tempfile
import re
from pathlib import Path
from datetime import datetime

# Cores ANSI para output no terminal
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RESET = '\033[0m'

def log_info(msg):
    print(f"{Colors.CYAN}ℹ{Colors.RESET} {msg}")

def log_success(msg):
    print(f"{Colors.GREEN}✓{Colors.RESET} {msg}")

def log_warn(msg):
    print(f"{Colors.YELLOW}⚠{Colors.RESET} {msg}")

def log_error(msg):
    print(f"{Colors.RED}✗{Colors.RESET} {msg}")

def log_title(msg):
    print(f"\n{Colors.BOLD}{Colors.HEADER}=== {msg} ==={Colors.RESET}\n")

# Diretórios principais
REPO_ROOT = Path(__file__).resolve().parent
SKILLS_DIR = REPO_ROOT / "skills"
SOURCES_FILE = REPO_ROOT / "sources.json"
BIN_DIR = REPO_ROOT / "bin"

# Destinos Globais padrão
GEMINI_GLOBAL_DIR = Path.home() / ".gemini" / "config" / "skills"
CLAUDE_GLOBAL_DIR = Path.home() / ".claude" / "skills"

def parse_frontmatter(skill_md_path: Path):
    """Extrai metadata simples do YAML frontmatter do SKILL.md."""
    if not skill_md_path.is_file():
        return {"name": skill_md_path.parent.name, "description": ""}
    
    try:
        content = skill_md_path.read_text(encoding="utf-8")
        match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
        if not match:
            return {"name": skill_md_path.parent.name, "description": ""}
        
        front = match.group(1)
        name_match = re.search(r"^name:\s*([^\n]+)", front, re.MULTILINE)
        name = name_match.group(1).strip().strip("'\"") if name_match else skill_md_path.parent.name
        
        # Extrai descrição (pode ser de linha única ou multiline)
        desc = ""
        desc_start = re.search(r"^description:\s*(?:>-\s*|\|\s*)?(.*)", front, re.MULTILINE)
        if desc_start:
            first_line = desc_start.group(1).strip()
            rest_of_text = front[desc_start.end():]
            desc_lines = [first_line] if first_line else []
            for line in rest_of_text.splitlines():
                if line.startswith("  ") or line.startswith("\t"):
                    desc_lines.append(line.strip())
                elif line.strip() == "":
                    continue
                else:
                    break
            desc = " ".join(desc_lines).strip().strip("'\"")
            
        return {"name": name, "description": desc}
    except Exception:
        return {"name": skill_md_path.parent.name, "description": ""}

def get_repo_skills():
    """Retorna lista de todas as skills existentes no repositório."""
    if not SKILLS_DIR.is_dir():
        return []
    skills = []
    for item in sorted(SKILLS_DIR.iterdir()):
        if item.is_dir() and (item / "SKILL.md").is_file():
            meta = parse_frontmatter(item / "SKILL.md")
            category = "expo" if item.name.startswith(("expo-", "eas-")) else "custom"
            skills.append({
                "name": item.name,
                "path": item,
                "category": category,
                "description": meta.get("description", "")
            })
    return skills

def get_target_directories(scope: str, agent: str, target_project_path: Path = None):
    """
    Retorna lista de tuplas (agent_name, dir_path) com base no escopo e no agente selecionado.
    scope: 'global' ou 'project'
    agent: 'all', 'gemini' ou 'claude'
    """
    targets = []
    if scope == "global":
        if agent in ("all", "gemini"):
            targets.append(("gemini", GEMINI_GLOBAL_DIR))
        if agent in ("all", "claude"):
            targets.append(("claude", CLAUDE_GLOBAL_DIR))
    else:
        base = target_project_path or Path.cwd()
        if agent in ("all", "gemini"):
            targets.append(("gemini", base / ".agents" / "skills"))
        if agent in ("all", "claude"):
            targets.append(("claude", base / ".claude" / "skills"))
    return targets

def install_skill_to_dir(skill_path: Path, dest_dir: Path, mode: str = "symlink", force: bool = False, dry_run: bool = False):
    """Instala uma skill individual em um diretório de destino."""
    skill_name = skill_path.name
    dest_path = dest_dir / skill_name

    if dry_run:
        log_info(f"[DRY-RUN] Instalar '{skill_name}' em {dest_path} via {mode}")
        return True

    dest_dir.mkdir(parents=True, exist_ok=True)

    if dest_path.is_symlink():
        target = dest_path.resolve()
        if target == skill_path.resolve():
            # Já aponta para o lugar correto
            return True
        else:
            if force:
                dest_path.unlink()
            else:
                log_warn(f"Symlink existente '{skill_name}' aponta para outro destino ({target}). Use --force para sobrescrever.")
                return False

    elif dest_path.is_dir():
        if force:
            shutil.rmtree(dest_path)
        else:
            log_warn(f"Diretório existente '{skill_name}' em {dest_dir}. Use --force para sobrescrever.")
            return False

    elif dest_path.exists():
        if force:
            dest_path.unlink()
        else:
            log_warn(f"Arquivo conflitante existente '{skill_name}'. Use --force para sobrescrever.")
            return False

    # Instalação
    if mode == "symlink":
        try:
            dest_path.symlink_to(skill_path.resolve(), target_is_directory=True)
            return True
        except Exception as e:
            log_error(f"Erro ao criar symlink para {skill_name}: {e}")
            return False
    elif mode == "copy":
        try:
            shutil.copytree(skill_path, dest_path)
            return True
        except Exception as e:
            log_error(f"Erro ao copiar {skill_name}: {e}")
            return False
    return False

def cmd_install(args):
    """Executa o comando de instalação de skills."""
    log_title("Instalação de Skills")
    
    scope = "project" if args.project is not None else "global"
    target_project_path = Path(args.project).resolve() if args.project else None
    
    targets = get_target_directories(scope, args.agent, target_project_path)
    all_repo_skills = get_repo_skills()
    repo_skill_map = {s["name"]: s["path"] for s in all_repo_skills}
    
    # Seleção de skills a instalar
    skills_to_install = []
    if args.skills:
        for name in args.skills:
            if name in repo_skill_map:
                skills_to_install.append(repo_skill_map[name])
            else:
                log_warn(f"Skill '{name}' não encontrada no repositório. Ignorando.")
    else:
        skills_to_install = [s["path"] for s in all_repo_skills]

    if not skills_to_install:
        log_error("Nenhuma skill válida selecionada para instalação.")
        return 1

    log_info(f"Escopo: {Colors.BOLD}{scope.upper()}{Colors.RESET}")
    log_info(f"Agente(s): {Colors.BOLD}{args.agent}{Colors.RESET}")
    log_info(f"Modo: {Colors.BOLD}{args.mode}{Colors.RESET}")
    log_info(f"Total de skills para instalar: {len(skills_to_install)}")
    print()

    for agent_name, dest_dir in targets:
        print(f"📦 Destino {Colors.BOLD}[{agent_name.upper()}]{Colors.RESET}: {dest_dir}")
        count = 0
        for skill_path in skills_to_install:
            ok = install_skill_to_dir(
                skill_path=skill_path,
                dest_dir=dest_dir,
                mode=args.mode,
                force=args.force,
                dry_run=args.dry_run
            )
            if ok:
                count += 1
        log_success(f"{count}/{len(skills_to_install)} skills instaladas para {agent_name.upper()}.\n")

    return 0

def cmd_sync(args):
    """
    Sincroniza skills do repositório com os diretórios globais (Gemini e Claude).
    Importa skills novas criadas diretamente nos diretórios globais.
    Se requisitado (--expo), também atualiza as skills do Expo.
    """
    log_title("Sincronização de Skills")
    
    # 1. Atualizar Expo se especificado
    if args.expo:
        print("🔄 Sincronizando com o upstream do Expo...")
        cmd_update_expo(args)
        print()

    # 2. Verificar se existem skills locais nos diretórios globais que não estão no repo
    log_info("Verificando se há skills locais não rastreadas em ~/.gemini e ~/.claude...")
    imported_count = 0
    all_repo_skills = {s["name"]: s["path"] for s in get_repo_skills()}

    for agent_name, global_dir in [("gemini", GEMINI_GLOBAL_DIR), ("claude", CLAUDE_GLOBAL_DIR)]:
        if not global_dir.is_dir():
            continue
        for item in global_dir.iterdir():
            if item.is_dir() and not item.is_symlink() and (item / "SKILL.md").is_file():
                if item.name not in all_repo_skills:
                    log_info(f"Nova skill encontrada em {agent_name}: '{item.name}'. Importando para o repositório...")
                    dest_in_repo = SKILLS_DIR / item.name
                    shutil.copytree(item, dest_in_repo)
                    all_repo_skills[item.name] = dest_in_repo
                    imported_count += 1
                    # Substitui diretório original por symlink para manter sincronizado
                    shutil.rmtree(item)
                    item.symlink_to(dest_in_repo.resolve(), target_is_directory=True)
                    log_success(f"Skill '{item.name}' importada e transformada em symlink.")

    if imported_count > 0:
        log_success(f"{imported_count} skill(s) importada(s) para o repositório.")
    else:
        log_info("Nenhuma nova skill não-rastreada para importar.")

    # 3. Garantir que todas as skills do repo estão instaladas/linkadas nos globais
    log_info("Garantindo que todas as skills do repositório estão instaladas globalmente...")
    class FakeArgs:
        skills = []
        global_install = True
        project = None
        agent = "all"
        mode = "symlink"
        force = False
        dry_run = False
    
    cmd_install(FakeArgs)

    # 4. Status do Git
    try:
        git_res = subprocess.run(["git", "status", "--short"], cwd=REPO_ROOT, capture_output=True, text=True)
        if git_res.returncode == 0:
            if git_res.stdout.strip():
                log_warn("Alterações pendentes detectadas no Git (prontas para commit):")
                print(Colors.DIM + git_res.stdout + Colors.RESET)
            else:
                log_success("Repositório Git está limpo e sincronizado.")
    except Exception:
        pass

    return 0

def cmd_update_expo(args):
    """Atualiza as skills oficiais do Expo a partir de https://github.com/expo/skills."""
    log_title("Atualização de Skills do Expo (Upstream)")
    
    repo_url = "https://github.com/expo/skills.git"
    scan_dirs = ["plugins/expo/skills", "plugins/expo-experiments/skills"]
    branch = "main"

    if SOURCES_FILE.is_file():
        try:
            with open(SOURCES_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                expo_cfg = cfg.get("expo", {})
                repo_url = expo_cfg.get("repo", repo_url)
                scan_dirs = expo_cfg.get("scan_dirs", scan_dirs)
                branch = expo_cfg.get("branch", branch)
        except Exception:
            pass

    log_info(f"Clonando repositório upstream {repo_url} ({branch})...")
    
    temp_dir = tempfile.mkdtemp(prefix="expo-skills-")
    try:
        clone_cmd = [
            "git", "clone", "--depth", "1", "--single-branch",
            "--branch", branch, repo_url, temp_dir
        ]
        res = subprocess.run(clone_cmd, capture_output=True, text=True)
        if res.returncode != 0:
            log_error(f"Falha ao clonar repositório do Expo: {res.stderr}")
            return 1

        # Obter commit SHA
        rev_cmd = ["git", "rev-parse", "HEAD"],
        rev_res = subprocess.run(["git", "rev-parse", "HEAD"], cwd=temp_dir, capture_output=True, text=True)
        commit_sha = rev_res.stdout.strip() if rev_res.returncode == 0 else "unknown"

        log_info(f"Commit upstream: {commit_sha[:8]}")

        added = []
        updated = []
        unchanged = []

        for sub in scan_dirs:
            upstream_path = Path(temp_dir) / sub
            if not upstream_path.is_dir():
                continue
            
            for item in upstream_path.iterdir():
                if item.is_dir() and (item / "SKILL.md").is_file():
                    skill_name = item.name
                    local_dest = SKILLS_DIR / skill_name
                    
                    if not local_dest.exists():
                        shutil.copytree(item, local_dest)
                        added.append(skill_name)
                    else:
                        # Compara conteúdo usando diff recursivo simples
                        diff_res = subprocess.run(
                            ["diff", "-r", "-q", str(item), str(local_dest)],
                            capture_output=True, text=True
                        )
                        if diff_res.returncode == 0:
                            unchanged.append(skill_name)
                        else:
                            shutil.rmtree(local_dest)
                            shutil.copytree(item, local_dest)
                            updated.append(skill_name)

        # Atualiza sources.json
        if SOURCES_FILE.is_file():
            try:
                with open(SOURCES_FILE, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                if "expo" not in cfg:
                    cfg["expo"] = {}
                cfg["expo"]["last_sync"] = datetime.now().isoformat()
                cfg["expo"]["last_commit"] = commit_sha
                with open(SOURCES_FILE, "w", encoding="utf-8") as f:
                    json.dump(cfg, f, indent=2)
            except Exception as e:
                log_warn(f"Não foi possível salvar metadata em sources.json: {e}")

        # Exibir relatório
        print()
        if added:
            log_success(f"Novas skills adicionadas ({len(added)}): {', '.join(added)}")
        if updated:
            log_success(f"Skills atualizadas ({len(updated)}): {', '.join(updated)}")
        if unchanged:
            log_info(f"Skills sem alterações ({len(unchanged)}): {len(unchanged)} skills já estavam atualizadas.")

        print(f"\n{Colors.GREEN}{Colors.BOLD}Atualização do Expo concluída com sucesso!{Colors.RESET}\n")
        return 0

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

def cmd_list(args):
    """Lista todas as skills do repositório e o status de instalação."""
    log_title("Catálogo de Skills")
    skills = get_repo_skills()
    
    if not skills:
        log_warn("Nenhuma skill encontrada no repositório.")
        return 0

    # Categorias
    categories = {}
    for s in skills:
        cat = s["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(s)

    for cat_name, cat_skills in categories.items():
        title = "EXPO & EAS FRAMEWORK" if cat_name == "expo" else "SKILLS CUSTOMIZADAS & WORKFLOWS"
        print(f"{Colors.BOLD}{Colors.CYAN}[{title}] ({len(cat_skills)}){Colors.RESET}")
        print(f"{'Nome':<28} {'Gemini':<12} {'Claude':<12} {'Descrição'}")
        print("-" * 90)

        for s in cat_skills:
            name = s["name"]
            
            # Status Gemini
            gem_path = GEMINI_GLOBAL_DIR / name
            if gem_path.is_symlink():
                gem_status = f"{Colors.GREEN}✓ link{Colors.RESET}"
            elif gem_path.is_dir():
                gem_status = f"{Colors.GREEN}✓ copy{Colors.RESET}"
            else:
                gem_status = f"{Colors.DIM}-{Colors.RESET}"

            # Status Claude
            claude_path = CLAUDE_GLOBAL_DIR / name
            if claude_path.is_symlink():
                claude_status = f"{Colors.GREEN}✓ link{Colors.RESET}"
            elif claude_path.is_dir():
                claude_status = f"{Colors.GREEN}✓ copy{Colors.RESET}"
            else:
                claude_status = f"{Colors.DIM}-{Colors.RESET}"

            desc = s["description"]
            if len(desc) > 42:
                desc = desc[:39] + "..."

            print(f"{Colors.BOLD}{name:<28}{Colors.RESET} {gem_status:<20} {claude_status:<20} {Colors.DIM}{desc}{Colors.RESET}")
        print()

    print(f"Total: {Colors.BOLD}{len(skills)} skills disponíveis.{Colors.RESET}\n")
    return 0

def cmd_status(args):
    """Exibe o status geral de saúde das skills e caminhos globais."""
    log_title("Status do Sistema de Skills")
    skills = get_repo_skills()

    print(f"📁 Diretório do Repositório: {REPO_ROOT}")
    print(f"📚 Total de Skills no Repositório: {Colors.BOLD}{len(skills)}{Colors.RESET}")
    print()

    for agent_name, gdir in [("Gemini (Antigravity)", GEMINI_GLOBAL_DIR), ("Claude (Claude Code)", CLAUDE_GLOBAL_DIR)]:
        print(f"🤖 {Colors.BOLD}{agent_name}{Colors.RESET}:")
        print(f"   Caminho: {gdir}")
        if not gdir.exists():
            print(f"   Status: {Colors.YELLOW}Diretório não existe ainda (será criado no primeiro install){Colors.RESET}")
        else:
            active_links = 0
            copies = 0
            broken_links = 0
            other = 0
            for item in gdir.iterdir():
                if item.is_symlink():
                    if item.exists():
                        active_links += 1
                    else:
                        broken_links += 1
                elif item.is_dir():
                    copies += 1
                else:
                    other += 1
            print(f"   Skills ativas (Symlinks): {Colors.GREEN}{active_links}{Colors.RESET}")
            if copies > 0:
                print(f"   Skills copiadas (Pastas físicas): {Colors.YELLOW}{copies}{Colors.RESET}")
            if broken_links > 0:
                print(f"   Symlinks corrompidos: {Colors.RED}{broken_links}{Colors.RESET}")
        print()

    if SOURCES_FILE.is_file():
        try:
            with open(SOURCES_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            expo_cfg = cfg.get("expo", {})
            last_sync = expo_cfg.get("last_sync") or "Nunca"
            last_commit = expo_cfg.get("last_commit") or "Desconhecido"
            print(f"🌐 {Colors.BOLD}Upstream Expo{Colors.RESET}:")
            print(f"   Repositório: {expo_cfg.get('repo')}")
            print(f"   Última sincronização: {last_sync}")
            print(f"   Último commit: {last_commit[:8] if len(last_commit) > 8 else last_commit}")
            print()
        except Exception:
            pass

    return 0

def cmd_add(args):
    """Cria uma nova skill com template padronizado."""
    name = args.name.lower().strip()
    if not re.match(r"^[a-z0-9-_]+$", name):
        log_error("O nome da skill deve conter apenas letras minúsculas, números, hífens e sublinhados.")
        return 1

    skill_path = SKILLS_DIR / name
    if skill_path.exists():
        log_error(f"A skill '{name}' já existe em {skill_path}!")
        return 1

    skill_path.mkdir(parents=True, exist_ok=True)
    skill_md = skill_path / "SKILL.md"

    template = f"""---
name: {name}
description: >-
  Descreva com clareza o objetivo desta skill e quando ela deve ser ativada pelo agente (ex: "Use esta skill quando o usuário pedir para...").
---

# {name.replace('-', ' ').title()}

Instruções e diretrizes de execução para o agente.

## 1. Visão Geral
Descreva aqui o propósito desta skill e seus casos de uso.

## 2. Pré-requisitos e Validações
- Liste arquivos, dependências ou comandos necessários antes de iniciar.

## 3. Passo a Passo do Procedimento
1. Primeiro passo de execução.
2. Segundo passo com comandos específicos.
3. Validação do resultado.

## 4. Boas Práticas e Regras Críticas
- Adicione diretrizes que evitam erros comuns pelo modelo.
"""
    skill_md.write_text(template, encoding="utf-8")
    log_success(f"Nova skill criada com sucesso em: {skill_md}")
    log_info("Você pode editar o arquivo e rodar 'skills sync' para ativá-la globalmente!")
    return 0

def cmd_setup(args):
    """Configura o comando 'skills' globalmente no sistema."""
    log_title("Configuração do Atalho Global 'skills'")

    bin_script = BIN_DIR / "skills"
    local_bin = Path.home() / ".local" / "bin"
    symlink_target = local_bin / "skills"

    local_bin.mkdir(parents=True, exist_ok=True)

    # Cria symlink em ~/.local/bin/skills
    try:
        if symlink_target.exists() or symlink_target.is_symlink():
            symlink_target.unlink()
        symlink_target.symlink_to(bin_script.resolve())
        log_success(f"Link criado em: {symlink_target} -> {bin_script}")
    except Exception as e:
        log_warn(f"Não foi possível criar symlink em ~/.local/bin: {e}")

    # Configura alias em ~/.bash_aliases como garantia
    bash_aliases = Path.home() / ".bash_aliases"
    alias_line = f"alias skills=\"{bin_script.resolve()}\""
    path_line = 'export PATH="$HOME/.local/bin:$PATH"'

    already_configured = False
    if bash_aliases.exists():
        content = bash_aliases.read_text(encoding="utf-8")
        if str(bin_script.resolve()) in content:
            already_configured = True

    if not already_configured:
        with open(bash_aliases, "a", encoding="utf-8") as f:
            f.write(f"\n# Skills CLI\n{path_line}\n{alias_line}\n")
        log_success(f"Alias e PATH adicionados em {bash_aliases}")
    else:
        log_info(f"Alias já configurado em {bash_aliases}")

    print(f"\n{Colors.GREEN}{Colors.BOLD}✓ Configuração concluída!{Colors.RESET}")
    print(f"Para aplicar imediatamente nesta sessão de terminal, execute:")
    print(f"  {Colors.CYAN}source ~/.bashrc{Colors.RESET}")
    print(f"Ou abra uma nova janela de terminal e digite: {Colors.CYAN}skills --help{Colors.RESET}\n")
    return 0

def build_parser():
    parser = argparse.ArgumentParser(
        prog="skills",
        description="Gerenciador Central de Skills para Gemini (Antigravity) e Claude Code."
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Comandos disponíveis")

    # Install
    p_install = subparsers.add_parser("install", help="Instala skills globalmente ou no projeto local")
    p_install.add_argument("skills", nargs="*", help="Nomes das skills específicas a instalar (opcional)")
    p_install.add_argument("-g", "--global", dest="global_install", action="store_true", default=True, help="Instalar nas pastas de configuração globais (~/.gemini e ~/.claude) [Padrão]")
    p_install.add_argument("-p", "--project", nargs="?", const=".", default=None, help="Instalar na pasta do projeto atual ou indicada (.agents e .claude)")
    p_install.add_argument("-a", "--agent", choices=["all", "gemini", "claude"], default="all", help="Agente alvo (padrão: all)")
    p_install.add_argument("-m", "--mode", choices=["symlink", "copy"], default="symlink", help="Modo de instalação (padrão: symlink)")
    p_install.add_argument("-f", "--force", action="store_true", help="Sobrescrever destinos conflitantes sem perguntar")
    p_install.add_argument("--dry-run", action="store_true", help="Apenas simular a operação sem aplicar alterações")
    p_install.set_defaults(func=cmd_install)

    # Sync
    p_sync = subparsers.add_parser("sync", help="Sincroniza todas as skills com os destinos globais e importa novas")
    p_sync.add_argument("-e", "--expo", action="store_true", help="Também atualiza as skills do upstream oficial da Expo")
    p_sync.add_argument("-a", "--agent", choices=["all", "gemini", "claude"], default="all", help="Agente alvo (padrão: all)")
    p_sync.set_defaults(func=cmd_sync)

    # Update Expo
    p_update_expo = subparsers.add_parser("update-expo", help="Busca atualizações do repositório oficial da Expo (github.com/expo/skills)")
    p_update_expo.set_defaults(func=cmd_update_expo)

    # List
    p_list = subparsers.add_parser("list", aliases=["ls"], help="Lista todas as skills disponíveis no catálogo e seus status")
    p_list.set_defaults(func=cmd_list)

    # Status
    p_status = subparsers.add_parser("status", help="Exibe status geral das pastas e conexões de skills")
    p_status.set_defaults(func=cmd_status)

    # Add
    p_add = subparsers.add_parser("add", help="Cria o scaffold de uma nova skill")
    p_add.add_argument("name", help="Nome da nova skill (ex: minha-nova-skill)")
    p_add.set_defaults(func=cmd_add)

    # Setup
    p_setup = subparsers.add_parser("setup", aliases=["link"], help="Configura o comando 'skills' no PATH para uso global")
    p_setup.set_defaults(func=cmd_setup)

    return parser

def main():
    parser = build_parser()
    args = parser.parse_args()

    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(0)

    try:
        ret = args.func(args)
        sys.exit(ret or 0)
    except KeyboardInterrupt:
        print("\nOperação cancelada pelo usuário.")
        sys.exit(130)
    except Exception as e:
        log_error(f"Erro inesperado: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
