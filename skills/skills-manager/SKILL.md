---
name: skills-manager
description: >-
  Gerencia, cria, edita, instala e sincroniza skills no repositório myskills e atualiza o upstream oficial da Expo. Ative quando o usuário pedir para 'criar uma nova skill', 'adicionar skill', 'atualizar skills do expo', 'instalar skills no projeto', 'sincronizar skills', 'listar skills' ou gerenciar o repositório de skills.
---

# Skills Manager — Gerenciador do Repositório de Skills

Este runbook orienta os agentes (Google Gemini/Antigravity e Anthropic Claude Code) na manutenção, criação, sincronização e instalação de skills no ecossistema centralizado do repositório `myskills`.

---

## 1. Contexto do Ambiente

- **Repositório Central:** `/home/joaop/myskills`
- **Repositório Remoto GitHub:** `https://github.com/joaop-rosa/myskills.git`
- **CLI Centralizada:** `skills` (localizada em `/home/joaop/myskills/bin/skills` ou disponível globalmente no PATH)
- **Diretórios Globais de Agentes:**
  - **Gemini (Antigravity):** `~/.gemini/config/skills/<skill-name>/`
  - **Claude (Claude Code):** `~/.claude/skills/<skill-name>/`
- **Diretórios de Projeto (Workspaces Locais):**
  - **Gemini:** `<projeto>/.agents/skills/<skill-name>/`
  - **Claude:** `<projeto>/.claude/skills/<skill-name>/`

---

## 2. Catálogo de Comandos da CLI (`skills`)

Sempre prefira utilizar o comando `skills` em vez de criar ou mover pastas manualmente:

| Comando | Finalidade | Quando Usar |
| :--- | :--- | :--- |
| `skills list` (ou `ls`) | Lista todas as skills, categorias e status nos agentes | Para inspecionar as skills existentes antes de criar novas |
| `skills status` | Exibe diagnóstico de saúde dos diretórios e links | Para verificar se há symlinks quebrados ou pastas não rastreadas |
| `skills add <nome>` | Cria o scaffold padronizado de uma nova skill | Sempre ao iniciar a criação de uma nova skill |
| `skills sync` | Sincronização bidirecional entre repo e diretórios globais | Após criar ou alterar qualquer skill para garantir links ativos |
| `skills sync --expo` | Sincroniza local e busca atualizações do upstream da Expo | Para sincronização completa incluindo a Expo |
| `skills pull` | Executa `git pull --ff-only` no repo e roda `skills sync` | Para trazer atualizações remotas (ex: bot do GitHub Actions) para a máquina local |
| `skills update-expo` | Clona e atualiza as skills do upstream `expo/skills` em `skills/expo/` | Quando o usuário solicitar atualização manual das skills do Expo |
| `skills install` | Instala globalmente todas as skills via symlinks | Para restaurar ou vincular todo o catálogo na máquina |
| `skills install --project <dir>` | Instala as skills na pasta de um projeto específico | Quando o usuário pedir para instalar skills em um projeto |

---

## 3. Padrão Canônico para Novas Skills

Ao criar uma nova skill, siga **estritamente** este padrão:

### 3.1 Nomenclatura
- Letras minúsculas com hífens (`kebab-case`). Exemplo: `react-vite-architecture`, `audit-vulnerabilities`.

### 3.2 Frontmatter Obrigatório no `SKILL.md`
O topo do arquivo deve conter metadados YAML delimitados por `---`:
```markdown
---
name: nome-da-skill
description: >-
  Explicação em terceira pessoa indicando claramente o que a skill faz e quando o agente DEVE ativá-la. Inclua palavras-chave e intenções de ativação (ex: "Ative quando o usuário pedir para '...").
---
```

> [!IMPORTANT]
> A `description` é o campo mais crítico. O agente lê esta descrição para decidir dinamicamente se carrega a skill no contexto. Seja específico nas frases e intenções de acionamento.

### 3.3 Estrutura de Conteúdo Recomendada
```markdown
# Título da Skill

Breve descrição introdutória do propósito da skill.

## 1. Visão Geral e Casos de Uso
Explicar em que situações esta skill se aplica e o resultado esperado.

## 2. Regras Estritas e Proibições (Diretrizes Críticas)
Listar de forma destacada o que o modelo NUNCA deve fazer ou regras inegociáveis.

## 3. Passo a Passo Procedural (Runbook)
Instruções sequenciais, comandos determinísticos e verificações pós-passo.

## 4. Boas Práticas e Padrões de Código
Exemplos práticos, templates ou convenções recomendadas.
```

### 3.4 Progressive Disclosure (Subdiretórios Opcionais)
- Para documentações extensas ou manuais de referência, crie a pasta `references/` e aponte para os arquivos com links relativos markdown: `[Guia](./references/guia.md)`.
- Para rotinas automatizadas, coloque scripts executáveis na pasta `scripts/`.

---

## 4. Fluxos de Trabalho Automatizados (Runbooks)

### 🚀 Fluxo 1: Criar uma Nova Skill
1. **Verificar se já existe:**
   Execute `skills list` para checar se uma skill similar já existe.
2. **Criar o esqueleto:**
   Execute `skills add <nome-da-skill>`.
3. **Preencher o conteúdo:**
   Edite `skills/<nome-da-skill>/SKILL.md` seguindo o Padrão Canônico (Seção 3).
4. **Vincular nos agentes:**
   Execute `skills sync` para criar os symlinks em `~/.gemini/config/skills` e `~/.claude/skills`.
5. **Versionar no Git:**
   ```bash
   git add skills/<nome-da-skill>/
   git commit -m "feat(skills): add <nome-da-skill> skill"
   git push origin main
   ```

---

### 🌐 Fluxo 2: Atualizar as Skills da Expo (Upstream)
> [!NOTE]
> O workflow `.github/workflows/sync-expo-skills.yml` já sincroniza automaticamente as skills da Expo em `skills/expo/` todo dia às 06:00 BRT e envia para a `main`. Para atualizar apenas sua máquina local, execute `skills pull`.

Para rodar uma sincronização manual contra o upstream:
1. **Executar a atualização:**
   ```bash
   skills update-expo
   ```
2. **Inspecionar as alterações:**
   Execute `git status -s` e `git diff` para revisar as novidades em `skills/expo/` que vieram do repositório oficial da Expo.
3. **Commitar e Subir:**
   ```bash
   git add skills/expo/ sources.json
   git commit -m "chore(expo): sync upstream skills from expo/skills"
   git push origin main
   ```

---

### 📦 Fluxo 3: Instalar Skills em um Projeto Específico
Se o usuário estiver trabalhando em um projeto (ex: `/home/joaop/meu-app`) e pedir para adicionar as skills nele:
1. **Perguntar/Identificar o modo desejado:**
   - **Symlink (recomendado para desenvolvimento local):**
     ```bash
     skills install --project /caminho/do/projeto
     ```
   - **Copy (recomendado se o usuário for commitar as skills dentro do repositório do projeto):**
     ```bash
     skills install --project /caminho/do/projeto --mode copy
     ```
2. **Se o usuário desejar apenas skills pontuais:**
   ```bash
   skills install expo-router expo-native-ui coding-standards --project /caminho/do/projeto
   ```

---

## 5. Regras Críticas para o Agente

1. **Respeite a separação entre customizadas e Expo**: Skills customizadas ficam em `/home/joaop/myskills/skills/<nome>/`, enquanto as skills oficiais da Expo ficam exclusivamente em `/home/joaop/myskills/skills/expo/<nome>/` (nunca crie pastas soltas fora de `skills/`).
2. **Sempre rode `skills sync` após criar ou renomear skills**: Sem isso, os diretórios globais do Gemini e Claude não receberão o link simbólico atualizado.
3. **Mantenha a compatibilidade dupla (Gemini + Claude)**: Nunca utilize sintaxes ou estruturas exclusivas de uma única ferramenta que quebrem a leitura pelo outro agente.
4. **Preserve os commits limpos**: Sempre utilize Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`).
