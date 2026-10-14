# 🧠 My Skills — Repositório Central de Agent Skills

Repositório central para armazenamento, versionamento e distribuição de **AI Agent Skills** compatível tanto com o **Google Gemini (Antigravity IDE / CLI)** quanto com o **Anthropic Claude (Claude Code)**.

Inclui uma CLI (`skills`) integrada para instalar com um clique, sincronizar alterações bidirecionalmente e manter as skills do ecossistema **Expo / EAS** sempre atualizadas com o repositório upstream oficial ([expo/skills](https://github.com/expo/skills)).

---

## ⚡ Início Rápido

### 1. Habilitar o comando `skills` globalmente
Dentro desta pasta, execute o comando de setup para tornar o comando acessível de qualquer lugar do seu terminal:

```bash
./bin/skills setup
```

Em seguida, recarregue seu terminal ou execute:
```bash
source ~/.bashrc
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

### 🔄 Sincronização Inteligente (`sync`)

O comando `sync` executa uma sincronização inteligente:
1. **Importa novidades locais:** Se você criou ou editou uma skill diretamente em `~/.gemini/config/skills` ou `~/.claude/skills`, o comando detecta e importa a pasta para este repositório Git!
2. **Garante integridade:** Assegura que todas as skills do repositório estejam ativas e apontadas corretamente.
3. **Status do Git:** Exibe se há alterações pendentes prontas para commit.

```bash
skills sync

# Sincronizar tudo E também atualizar as skills do Expo em uma única etapa:
skills sync --expo
```

---

### 🌐 Atualizar Skills do Expo Upstream (`update-expo`)

As skills do Expo vêm do repositório oficial da equipe da Expo ([https://github.com/expo/skills](https://github.com/expo/skills)). Para buscar as versões mais recentes:

```bash
skills update-expo
```

O comando:
- Clona superficialmente a branch `main` do repositório oficial.
- Varre os plugins (`plugins/expo/skills` e `plugins/expo-experiments/skills`).
- Compara com os arquivos locais e atualiza apenas o que mudou.
- Notifica quais skills foram adicionadas, atualizadas ou permaneceram idênticas.
- Registra a data e o hash do commit sincronizado em `sources.json`.

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

### Estrutura de uma Skill
```text
skills/<nome-da-skill>/
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

### 🛡️ Qualidade, Arquitetura e Engenharia
- **`audit-vulnerabilities`**: Auditoria profunda de dependências, resolução de vulnerabilidades e patches.
- **`code-review`**: Runbook completo para revisões de código rigorosas e relatórios de melhoria.
- **`coding-standards`**: Padrões rígidos de Clean Code, SOLID e consistência arquitetural.
- **`react-vite-architecture`**: Diretrizes de Clean Architecture e separação de camadas para React + Vite.
- **`playwright-test`**: Testes ponta a ponta (E2E), automação de interface e MCP com Playwright.
- **`wordpress-update`**: Procedimento seguro para atualização e manutenção de sites WordPress.

### ✍️ Produtividade e Workflow
- **`skills-manager`**: Meta-skill para gerenciamento, criação padronizada, instalação e sincronização de skills.
- **`git-commit`**: Criação de mensagens convencionais de commit com verificação de staging.
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
