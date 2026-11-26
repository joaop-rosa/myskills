# 🧠 My Skills — Repositório Central de Agent Skills & MCPs

Repositório central para armazenamento, versionamento e distribuição de **AI Agent Skills** e **Servidores MCP** compatível com **Google Gemini (Antigravity IDE / CLI)** e **Anthropic Claude (Claude Code)** em **Linux e macOS**.

Inclui uma CLI (`skills`) integrada para instalar com um clique, sincronizar skills e configurações MCP bidirecionalmente (com detecção automática de navegador por sistema operacional) e manter as skills do ecossistema **Expo / EAS** sempre atualizadas com o repositório upstream oficial ([expo/skills](https://github.com/expo/skills)).

---

## ⚡ Início Rápido

### 1. Habilitar o comando `skills` globalmente
Dentro desta pasta, execute o comando de setup para tornar o comando acessível de qualquer lugar do seu terminal (configura `~/.local/bin/skills`, `~/.bash_aliases` no Linux e `~/.zshrc` no macOS):

```bash
./bin/skills setup
```

Em seguida, recarregue seu terminal ou execute:
```bash
# Linux (bash)
source ~/.bashrc

# macOS (zsh)
source ~/.zshrc
```

Pronto! Agora você pode rodar `skills` em qualquer diretório.

---

## 🚀 Comandos Principais

### 📦 Instalação de Skills (`install`)

Instala as skills do repositório nos diretórios globais do Gemini e do Claude via **symlinks** (links simbólicos). Dessa forma, qualquer edição que você fizer no repositório reflete imediatamente em todos os seus agentes, sem precisar reinstalar!

```bash
# Instala todas as skills globalmente para Gemini e Claude
skills install

# Instala apenas skills específicas
skills install expo-router git-commit code-review

# Instalar apenas para um agente específico (gemini ou claude)
skills install --agent gemini
skills install --agent claude

# Instalar em um projeto/workspace específico (cria .agents/skills e .claude/skills)
skills install --project /caminho/do/meu-projeto

# Copiar arquivos físicos em vez de criar symlinks (útil para versionar dentro do projeto)
skills install --project . --mode copy

# Simular a instalação sem aplicar alterações
skills install --dry-run
```

---

### 🔄 Sincronização Inteligente (`sync` e `pull`)

O comando `sync` executa uma sincronização inteligente de **skills e servidores MCP**:
1. **Importa novidades locais:** Detecta novas skills em `~/.gemini/config/skills` ou `~/.claude/skills` e novos MCPs em `~/.gemini/config/mcp_config.json` ou `~/.claude.json` (sanitizando caminhos locais antes de salvar em `mcps/servers.json`).
2. **Garante integridade:** Remove symlinks quebrados do repositório, re-vincula todas as skills e aplica todos os servidores MCP do catálogo adaptados ao sistema operacional atual (Linux ou macOS).
3. **Status do Git:** Exibe se há alterações pendentes prontas para commit.

```bash
skills sync

# Sincronizar apenas skills, pulando os servidores MCP:
skills sync --no-mcp

# Sincronizar tudo E também atualizar todas as fontes upstream (Expo + Vercel):
skills sync --upstream

# Sincronizar tudo E também atualizar apenas o upstream da Expo:
skills sync --expo

# Puxar alterações remotas da branch main (git pull --ff-only) e sincronizar skills + MCPs locais:
skills pull
```

---

### 🔌 Gerenciamento de Servidores MCP (`mcp`)

O catálogo portátil em `mcps/servers.json` mantém definições limpas de servidores MCP (como `playwright` e `chrome-devtools`) sem acoplar caminhos específicos de máquina no Git:

- **No macOS:** Detecta `/Applications/Google Chrome.app` nativamente sem injetar flags extras nem `LD_LIBRARY_PATH` (ou faz fallback para `~/Library/Caches/ms-playwright`).
- **No Linux:** Quando não há Chrome global no `PATH`, localiza automaticamente o binário mais recente em `~/.cache/ms-playwright` e as libs em `~/.local/lib/playwright-deps`, aplicando `--executable-path` (`@playwright/mcp`), `--executablePath` (`chrome-devtools-mcp`) e `LD_LIBRARY_PATH`.
- **Merge não-destrutivo:** Atualiza apenas a chave `mcpServers` em `~/.gemini/config/mcp_config.json` e `~/.claude.json`, preservando histórico, projetos e credenciais já salvos. Variáveis específicas de uma máquina podem ser adicionadas em `mcps/local.override.json` (ignorado pelo Git).

```bash
# Listar MCPs do catálogo e status em Gemini/Claude
skills mcp list

# Sincronizar MCPs bidirecionalmente entre catálogo e agentes
skills mcp sync

# Verificar runtime de navegador detectado e MCPs ativos
skills mcp status

# Instalar MCPs no escopo de um projeto (.agents/mcp_config.json e .mcp.json)
skills mcp install --project /caminho/do/meu-projeto

# Cadastrar ou remover um servidor MCP no catálogo
skills mcp add meu-mcp --command npx --args -y pacote-mcp@latest
skills mcp remove meu-mcp
```

---

### 🌐 Atualizar Skills de Fontes Upstream (`update-upstream` / `update-expo`)

As skills de repositórios externos configurados em `sources.json` (como **Expo** em `skills/expo/` e **Vercel Labs** em `skills/vercel/`) são sincronizadas de forma idempotente:

```bash
# Atualiza todas as fontes upstream configuradas em sources.json (Expo + Vercel)
skills update-upstream

# Atualiza apenas uma fonte específica
skills update-upstream vercel

# Atalho legado para atualizar apenas as skills da Expo
skills update-expo
```

O comando:
- Clona superficialmente a branch configurada de cada repositório upstream.
- Varre os diretórios configurados em `scan_dirs` e aplica filtros `include` (quando definidos, como `vercel-react-best-practices`).
- Compara com os arquivos locais, atualiza apenas o que mudou e remove skills descontinuadas no upstream.
- Atualiza `sources.json` apenas quando houver alteração real de conteúdo.

---

### 🤖 Sincronização Automática via GitHub Actions

O workflow [`.github/workflows/sync-upstream-skills.yml`](.github/workflows/sync-upstream-skills.yml) executa automaticamente todos os dias às **06:00 BRT** (`09:00 UTC`), além de poder ser disparado sob demanda pela aba **Actions** (`workflow_dispatch`):
1. Roda `python3 cli.py update-upstream` para sincronizar todas as fontes em `sources.json` (`expo`, `vercel`, etc.).
2. Quando houver novas skills, atualizações ou remoções, cria um commit automático e envia direto para `main`.
3. Se nada mudou no upstream, encerra sem gerar commit vazio.

Na sua máquina local, basta rodar `skills pull` para baixar as novidades e atualizar os symlinks do Gemini e do Claude.

---

### 📋 Listar e Inspecionar Skills (`list` / `status`)

```bash
# Lista todas as skills, suas descrições e status nos agentes
skills list

# Diagnóstico de saúde dos diretórios globais (~/.gemini e ~/.claude)
skills status
```

---

### ➕ Criar uma Nova Skill (`add`)

Para criar uma nova skill já padronizada com o formato YAML frontmatter e estrutura recomendada:

```bash
skills add minha-nova-skill
```

O comando gera automaticamente o arquivo `skills/minha-nova-skill/SKILL.md` pronto para edição. Após preencher as instruções, basta rodar `skills sync` para disponibilizá-la aos seus agentes!

---

## 🛠️ Como Funciona a Compatibilidade (Gemini & Claude)

Tanto o **Google Antigravity** quanto o **Claude Code** adotam o padrão de diretórios modulares com arquivo `SKILL.md` e frontmatter YAML (`name` e `description`):

| Agente | Escopo Global (Máquina) | Escopo Local (Projeto / Workspace) |
| :--- | :--- | :--- |
| **Google Gemini (Antigravity)** | `~/.gemini/config/skills/<skill-name>/` | `<projeto>/.agents/skills/<skill-name>/` |
| **Anthropic Claude (Claude Code)** | `~/.claude/skills/<skill-name>/` | `<projeto>/.claude/skills/<skill-name>/` |

### Organização do Repositório e Estrutura de uma Skill
```text
skills/
├── expo/<expo-skill>/      # Skills oficiais sincronizadas do upstream (expo/skills)
│   └── SKILL.md
├── vercel/<vercel-skill>/  # Skills sincronizadas do upstream (vercel-labs/agent-skills)
│   └── SKILL.md
└── <custom-skill>/         # Suas skills customizadas e workflows
    ├── SKILL.md            # Obrigatório: Metadados YAML + Instruções do modelo
    ├── references/         # Opcional: Documentações pesadas ou guias extras
    └── scripts/            # Opcional: Scripts auxiliares executáveis
```

---

## 📚 Catálogo Atual de Skills

### 📱 Expo & EAS Framework (Upstream Oficial)
- **`expo-overview`**: Ponto de entrada e visão geral do ecossistema Expo.
- **`expo-project-structure`**: Estrutura canônica de arquivos e pastas para apps Expo.
- **`expo-router`**: Roteamento baseado em arquivos, layouts dinâmicos, tabs e modais.
- **`expo-native-ui`**: Design nativo, Apple HIG, Material Design 3 e UI fluida.
- **`expo-animation`**: Animações fluidas em React Native e Expo.
- **`expo-data-fetching`**: React Query, requisições de rede, cache e offline first.
- **`expo-ui`**: Componentes da biblioteca oficial `@expo/ui`.
- **`expo-dom`**: Renderização de componentes Web dentro de apps nativos via DOM.
- **`expo-dev-client`**: Configuração e geração de builds de desenvolvimento customizadas.
- **`expo-design-system`**: Construção e manutenção de design systems para Expo.
- **`expo-examples`**: Consulta a repositórios e padrões oficiais de exemplo da Expo.
- **`expo-module`**: Criação de módulos nativos Expo com Swift/Kotlin.
- **`expo-migrate-module`**: Migração de módulos antigos da Apple/Swift para o Expo Modules Core.
- **`expo-app-clip`**: Configuração de App Clips (iOS) em aplicações Expo.
- **`expo-brownfield`**: Integração de Expo dentro de apps nativos já existentes.
- **`expo-web-to-native`**: Migração de código React Web para mobile nativo Expo.
- **`expo-upgrade`**: Procedimento seguro de upgrade de versões do SDK Expo.
- **`expo-skill-feedback`**: Feedback e relatórios de melhorias para a equipe Expo.
- **`eas-workflows`**: Automação de pipelines CI/CD com EAS Workflows.
- **`eas-app-stores`**: Submissão automática para Apple App Store e Google Play Store.
- **`eas-hosting`**: Deploy de sites e APIs estáticas/SSR no EAS Hosting.
- **`eas-update`**: Publicação e gerenciamento de Over-The-Air (OTA) Updates.
- **`eas-update-insights`**: Monitoramento de integridade e rollouts de updates.
- **`eas-simulator`**: Execução e controle de builds em simuladores remotos do EAS.
- **`eas-observe`**: Observabilidade, telemetria e monitoramento de logs em produção.

### ▲ Vercel Labs (Upstream Oficial)
- **`vercel-react-best-practices`**: Guias de otimização de performance em React e Next.js mantidos pela engenharia da Vercel.

### 🛡️ Qualidade, Arquitetura e Engenharia
- **`audit-vulnerabilities`**: Auditoria profunda de dependências, resolução de vulnerabilidades e patches.
- **`code-review`**: Runbook completo para revisões de código rigorosas e relatórios de melhoria.
- **`coding-standards`**: Padrões rígidos de Clean Code, SOLID e consistência arquitetural.
- **`react-vite-architecture`**: Diretrizes de Clean Architecture e separação de camadas para React + Vite.
- **`playwright-test`**: Runbook agnóstico para testes E2E, automação e diagnóstico web coordenando Playwright MCP e Chrome DevTools MCP.
- **`wordpress-update`**: Procedimento seguro para atualização e manutenção de sites WordPress.

### ✍️ Produtividade e Workflow
- **`skills-manager`**: Meta-skill para gerenciamento, criação padronizada, instalação e sincronização de skills.
- **`skill-curator`**: Curadoria contínua e atualização automática de regras nas skills durante o chat com sync no Git.
- **`git-commit`**: Criação de mensagens convencionais de commit com verificação de staging.
- **`mr-template`**: Geração e preenchimento de templates de Merge Request (MR) e Pull Request (PR) de forma humana, direta e focada em QA.
- **`humanizer`**: Humanização de textos com IA, eliminando clichês e tons robóticos.
- **`lingui-translate`**: Extração e tradução de mensagens multilíngues com Lingui.js.

---

## 🐙 Repositório GitHub

O repositório oficial está configurado em: [https://github.com/joaop-rosa/myskills.git](https://github.com/joaop-rosa/myskills.git)

2. **Execute os comandos no terminal:**

```bash
git remote add origin https://github.com/joaop-rosa/myskills.git
git branch -M main
git push -u origin main
```

Sempre que adicionar novas skills ou atualizar as da Expo:
```bash
skills update-expo
git add .
git commit -m "chore: update expo skills from upstream"
git push
```
