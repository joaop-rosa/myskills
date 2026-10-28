---
name: skill-curator
description: >-
  Curador de evolução contínua das skills. Gerencia, atualiza e sincroniza regras nas skills do repositório ~/myskills sempre que o usuário corrigir um padrão durante o chat ("nunca faça X", "sempre faça Y", "nos meus projetos fazemos assim"), pedir para salvar um aprendizado em uma skill, atualizar uma skill existente ou consolidar aprendizados da conversa.
---

# Curador de Skills (`skill-curator`)

Você é responsável por evitar que as skills fiquem defasadas e por transformar correções de código ou arquitetura feitas durante o chat em regras permanentes no repositório central `~/myskills`.

---

## 1. Contexto e Caminhos do Ecossistema

- **Repositório Central (Git):** `~/myskills` (funciona em macOS e Linux)
- **CLI de Gerenciamento:** `~/myskills/bin/skills`
- **Índice / Catálogo:** `~/myskills/README.md` (seção `## 📚 Catálogo Atual de Skills`)
- **Pasta das Skills:** `~/myskills/skills/<nome-da-skill>/`

> [!IMPORTANT]
> Você normalmente estará executando dentro do workspace de outro projeto (ex: um app React, Expo, WordPress). Por isso, **sempre** execute comandos Git e da CLI apontando explicitamente para `~/myskills` (usando `git -C ~/myskills ...` e `~/myskills/bin/skills ...`), sem alterar nem commitar nada no repositório do projeto em que estiver trabalhando.

---

## 2. Quando Agir

1. **Correção explícita durante o chat:**
   Sempre que o usuário corrigir um código, arquitetura ou comportamento dizendo algo como *"nunca faça X, sempre faça Y"*, *"nos meus projetos fazemos assim"* ou *"prefiro esse padrão"*:
   - Resolva o problema do usuário no projeto atual primeiro.
   - Ao final da resposta, pergunte de forma curta e direta:
     > *"Quer que eu atualize a skill `<nome-da-skill>` com essa regra?"*
2. **Sob demanda:**
   Quando o usuário pedir diretamente para *"atualizar a skill X"*, *"adicionar essa regra nas skills"*, *"consolidar aprendizados"* ou *"salvar esse padrão"*.

---

## 3. Fluxo de Atualização (Passo a Passo)

### Passo 1: Sincronizar o repositório `~/myskills`
Antes de ler ou editar qualquer arquivo, garanta que o repositório local está atualizado com o GitHub:
```bash
git -C ~/myskills pull --rebase origin main
```

### Passo 2: Identificar a skill alvo
1. Consulte `~/myskills/README.md` (ou execute `~/myskills/bin/skills list`) para identificar qual skill cobre o tema:
   - Ex: Padrões gerais de código/TS/Clean Code → `coding-standards`
   - Ex: Arquitetura React + Vite, Zustand, TanStack Router, CSS Modules, useApi, modais, Lingui → `react-vite-architecture`
   - Ex: Critérios de revisão de código → `code-review`
   - Ex: E2E e Playwright → `playwright-test`
2. **Atenção às skills da Expo (`expo-*` e `eas-*`):** Elas são sincronizadas de um repositório upstream oficial e são sobrescritas ao rodar `skills update-expo`. Nunca edite uma skill `expo-*` ou `eas-*` a menos que o usuário peça explicitamente; prefira colocar suas convenções próprias em `coding-standards` ou criar uma nova skill customizada.
3. Se for necessário criar uma skill nova, use `~/myskills/bin/skills add <nome-da-skill>`.

### Passo 3: Inspecionar a skill e seus `references/`
1. Leia o `SKILL.md` da skill alvo em `~/myskills/skills/<nome-da-skill>/SKILL.md`.
2. Verifique se a pasta possui subdiretório `references/` (ex: `~/myskills/skills/<nome-da-skill>/references/`). Se a regra pertencer a um guia específico dentro de `references/`, edite o arquivo correspondente lá também.
3. Avalie se a nova regra:
   - **Substitui** uma regra antiga defasada (remova ou reescreva a antiga para evitar contradições).
   - **Complementa** uma seção existente (adicione de forma concisa e imperativa, mantendo o mesmo estilo do documento).

### Passo 4: Apresentar o Resumo do Diff e pedir confirmação
Mostre ao usuário de forma enxuta qual arquivo será alterado e o trecho exato (antes/depois ou bullet adicionado) e aguarde a confirmação (caso ele ainda não tenha autorizado na mensagem anterior).

### Passo 5: Aplicar, Sincronizar Symlinks, Commitar e Fazer Push
Assim que o usuário confirmar (ou se ele já tiver pedido diretamente para aplicar e salvar na skill):

1. Salve as alterações no arquivo dentro de `~/myskills/skills/<nome-da-skill>/`.
2. Se uma **nova skill** tiver sido criada:
   - Adicione-a na seção `## 📚 Catálogo Atual de Skills` do `~/myskills/README.md`.
   - Execute `~/myskills/bin/skills sync` para criar os symlinks globais em `~/.gemini/config/skills` e `~/.claude/skills`.
3. Faça o stage, commit e push **apenas** dos arquivos da skill no repositório `~/myskills`:
   ```bash
   git -C ~/myskills add skills/<nome-da-skill> README.md
   git -C ~/myskills commit -m "chore(skills): update <nome-da-skill> rules"
   git -C ~/myskills push origin main
   ```

> [!NOTE]
> A confirmação do usuário para atualizar a skill **já inclui autorização para executar `git commit` e `git push` no repositório `~/myskills`**, não sendo necessário pedir uma segunda confirmação de commit.
