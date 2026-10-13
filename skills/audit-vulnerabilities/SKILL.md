---
name: audit-vulnerabilities
description: "Audita e atualiza dependências vulneráveis via npm/pnpm/yarn sem quebrar o projeto. Remove overrides e allowScripts indevidos, analisa breaking changes de majors e peer deps, atualiza pacote por pacote manualmente e valida build/lint/tipos. Ative ao pedir 'atualizar dependências vulneráveis', 'corrigir vulnerabilidades', 'npm audit fix seguro', 'resolver vulnerabilidades' ou 'audit'."
---

# Auditoria e Atualização Segura de Dependências

Esta skill define o fluxo seguro para atualizar dependências **vulneráveis** do projeto sem quebrar o build, avaliando cuidadosamente breaking changes e evitando downgrades acidentais.

> [!IMPORTANT]
> **Regras Obrigatórias:**
> 1. **NUNCA use `npm audit fix` nem `npm audit fix --force`**: Ambos podem fazer downgrade destrutivo de dependências para versões incompatíveis com o projeto. As correções devem ser pontuais, pacote a pacote.
> 2. **NUNCA use `npm install --force` nem `--legacy-peer-deps`** sem analisar a raiz do conflito e justificar explicitamente ao usuário.
> 3. **Não remova dependências em uso** pelo código.
> 4. **Não promova versões major desnecessariamente**: Se a vulnerabilidade for eliminada com um patch ou minor seguro dentro da major atual, prefira essa opção.
> 5. **Não commite alterações automaticamente** a menos que o usuário solicite explicitamente.

---

## Fluxo de Execução

### Etapa 1 — Coleta de Contexto
1. Inspecione o `package.json` para verificar:
   - Gerenciador de pacotes utilizado (`npm`, `pnpm`, `yarn`).
   - Versões atuais das dependências diretas (`dependencies` e `devDependencies`).
   - Scripts de validação existentes (ex.: `build`, `lint`, `lint:biome`, `lint:ts`, `typecheck`, `test`).
   - Existência de blocos `overrides`, `resolutions` ou `allowScripts`.

### Etapa 2 — Higienização de `overrides` e `allowScripts`
Antes de atualizar, limpe mecanismos que possam mascarar versões vulneráveis:
1. No `package.json`, remova:
   - O bloco `"overrides": { ... }` (ou correspondente) caso existente.
   - O bloco `"allowScripts": { ... }` caso existente.
2. Reinstale as dependências para refletir o estado limpo:
   ```bash
   npm install
   ```
3. **Atenção ao warning do install**: Ao remover `allowScripts`, o `npm install` pode exibir avisos de scripts de instalação ignorados. **Ignore esse aviso por enquanto** — ele será tratado no final (Etapa 8).

### Etapa 3 — Identificar Dependências Vulneráveis
Execute a auditoria de segurança:
```bash
npm audit
```
Analise o relatório e liste as dependências com vulnerabilidades reais, separando as dependências **diretas** das **transitivas** (internas).

### Etapa 4 — Atualização Segura (Pacote por Pacote)
Trate as dependências individualmente:

1. **Avaliação de Breaking Changes**:
   - Para cada pacote, consulte a versão atual e a versão corrigida recomendada.
   - Se houver mudança de major (ex.: `1.x → 2.x`), avalie as notas de release e se há breaking changes em peer dependencies (React, Vite, TanStack Router, etc.).
   - Confirme se o projeto utiliza APIs alteradas buscando no código:
     ```bash
     grep -rn "<nome-do-pacote>" src/
     ```
2. **Aplicação da Atualização**:
   - Instale a versão segura recomendada:
     ```bash
     npm install <pacote>@<nova-versao>
     ```
3. **Dependências Transitivas (Internas)**:
   - Se a vulnerabilidade estiver em uma dependência interna de um pacote pai:
     1. Tente reinstalar o pacote pai na versão mais recente compatível para regenerar a árvore de resolução:
        ```bash
        npm install <pacote-pai>@<versao-mais-recente>
        ```
     2. Rode `npm audit` e verifique se a vulnerabilidade transitiva sumiu.
     3. Apenas se persistir e o pacote pai não tiver versão compatível sem a falha, avalie um `override` pontual com justificativa documentada.
4. **Validação Intermediária**:
   - Após atualizar o pacote, execute as checagens disponíveis no `package.json` (ex: `npm run lint`, `npm run typecheck` ou `npm audit`).

### Etapa 5 — Conflitos de Peer Dependencies
Se o `npm install` acusar conflito de peer dependencies, resolva alinhando as versões declaradas de forma compatível, sem mascarar com `--force` sem necessidade.

### Etapa 6 — Validação do Build do Projeto
Execute o build do projeto e as suítes de validação que existirem no `package.json`:
```bash
npm run build
```
Rode também os linters e verificadores de tipo disponíveis (ex.: `lint`, `typecheck`, etc.).

### Etapa 7 — Tratar Warnings de Scripts de Instalação (allowScripts)
Com a atualização concluída e validada:
1. Rode `npm install` e observe se há alertas de scripts de ciclo de vida ignorados.
2. Se necessário pelo ecossistema do projeto, adicione ao `package.json` no bloco `allowScripts` apenas os pacotes estritamente necessários sinalizados pelo warning.
3. Revalide o `npm install` e o `build`.

---

## Formato Obrigatório do Relatório Final

Apresente um resumo claro para o usuário:

1. **Dependências Atualizadas**:
   - `pacote`: `versão_antiga` → `versão_nova` (vulnerabilidade eliminada).
2. **Breaking Changes e Riscos Avaliados**:
   - Resumo das mudanças de major/minor e por que foram seguras.
3. **Alterações no `package.json`**:
   - Remoção de overrides e ajustes realizados.
4. **Validações Executadas**:
   - Comandos rodados (`audit`, `build`, `lint`) e status de sucesso.
5. **Pendências / Bloqueios**:
   - Vulnerabilidades restantes sem correção upstream ou decisões que dependem do usuário.
