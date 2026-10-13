---
name: code-review
description: "Executa code reviews aprofundados identificando bugs, inconsistências, duplicações de código, violações do paradigma funcional e melhores práticas de Expo/React/TypeScript. Classifica os apontamentos em CRÍTICO, ALTO, MÉDIO e BAIXO, sem listar pontos positivos. Deve ser ativada sempre que o usuário pedir um code review (ex: 'code review', 'faça o review', 'revise o código', 'analise essa branch/pr')."
---

# Code Review Skill

Esta skill define o fluxo padronizado para execução de **Code Reviews** rigorosos, técnicos e focados em problemas e manutenibilidade.

> [!IMPORTANT]
> **Diretrizes Fundamentais:**
> 1. **Zero "Fluff" / Sem Pontos Positivos:** O objetivo é identificar problemas, inconsistências e riscos. Não inclua elogios ou listas de aspectos positivos. Vá direto aos pontos que precisam de correção ou melhoria.
> 2. **Classificação Estrita de Severidade:** Todo problema encontrado DEVE ser categorizado em um dos 4 níveis: `CRÍTICO`, `ALTO`, `MÉDIO` ou `BAIXO`.
> 3. **Não Alterar a Branch de Trabalho:** Se o review for de outra branch, **NUNCA** execute `git checkout` ou `git switch`. Inspecione sempre em modo somente leitura (via `git diff`, `git show`, `git log`).
> 4. **Paradigma Funcional no Ecossistema React / Frontend:** Em código React, React Native e frontend, considere a programação funcional (imutabilidade, pureza, transformações declarativas com `map`/`filter`/`reduce`, composição) como padrão obrigatório para evitar mutações de estado e problemas de re-render. Em backend, scripts ou linguagens onde loops imperativos são idiomáticos, respeite as convenções naturais da linguagem.
> 5. **Padrões Canônicos de Engenharia (`coding-standards`):** Audite obrigatoriamente sob as diretrizes da skill [coding-standards](file:///Users/joaopaulodarosa/.gemini/config/skills/coding-standards/SKILL.md): funções de lógica/handlers de 4-20 linhas, componentes React tratados como unidades de UI/arquivo (avaliados por coesão, extração de lógica para Custom Hooks e teto de tela/arquivo < 500 linhas), SRP, nomes específicos (< 5 grep hits, sem `data`/`handler`/`Manager`), tipagem 100% explícita (sem `any`/`Dict`), early returns (máx 2 níveis de indentação), exceções com valor e formato esperado, docstrings públicas com exemplo, testes F.I.R.S.T com classes Fake nomeadas, injeção de dependências e logging estruturado em JSON.
> 6. **Consultar Skills do Expo quando Pertinente:** Se o código envolver React Native/Expo (`app/`), utilize as diretrizes das skills instaladas (`expo-native-ui`, `expo-animation`, `expo-data-fetching`, `expo-router`, `expo-design-system`, `expo-ui`, etc.).

---

## Fluxo de Execução

### Passo 1 — Identificação do Alvo (Branch / Arquivos)

Antes de inspecionar o código, verifique se o alvo do review está evidente no prompt:

1. **Se a intenção já estiver clara:**
   - Exemplo: "revise a branch feat/xyz", "revise o PR #123", "revise o arquivo User.tsx", "revise o que alterei localmente".
   - Proceda diretamente com a coleta de diffs do alvo especificado.
2. **Se a intenção NÃO estiver clara:**
   - Pergunte interativamente ao usuário antes de iniciar a análise, apresentando as opções:
     - **Opção 1:** Alterações locais não commitadas / staged da branch atual (`git diff` / `git diff --staged`).
     - **Opção 2:** Commits da branch atual em relação à branch base (`origin/stage` ou `origin/main`).
     - **Opção 3:** Uma branch específica (solicitando o nome da branch).

---

### Passo 2 — Coleta de Diffs e Contexto

Colete os diffs e arquivos relevantes **sem alterar a branch do usuário**:

- **Para outra branch (modo somente leitura):**
  ```bash
  # Identifique a base comum (merge-base)
  git merge-base <branch-alvo> origin/stage
  # Verifique os arquivos modificados
  git diff --stat <base>..<branch-alvo>
  # Inspecione o diff detalhado
  git diff <base>..<branch-alvo>
  ```
- **Para a branch atual:**
  ```bash
  # Diff contra a base
  git diff origin/stage...HEAD
  # Ou diff local não commitado
  git diff HEAD
  ```

Identifique as áreas impactadas:
- Se tocar no aplicativo móvel (`app/`), considere as convenções das skills do Expo.
- Se tocar no frontend web (`frontend/`), avalie CSS modules, acessibilidade, Vite e assets.
- Se tocar no backend (`backend/`), avalie migrações de banco, idempotência, schemas e tipagem.

---

### Passo 3 — Critérios de Análise

Analise cada alteração sob os seguintes pilares:

#### 1. Paradigma Funcional (FP — Exclusivo para React / Frontend)
> **Escopo**: Esta checagem é restrita a código React, React Native e ecossistema frontend/UI (`app/`, `frontend/`). Para backend ou scripts (ex: Python, Go), loops imperativos são válidos e aceitos se idiomáticos na linguagem.

- **Imutabilidade:**
  - Evitar mutações diretas em arrays ou objetos (`.push()`, `.splice()`, `obj.prop = val`).
  - Utilizar operações imutáveis (`[...arr, item]`, `{ ...obj, prop: val }`, `.map()`, `.filter()`, `.concat()`, `.toSorted()`).
  - Em React, garantir que objetos/arrays de estado ou refs nunca sofram mutações diretas.
- **Funções Puras & Determinismo:**
  - Funções de transformação de dados, regras de negócio e utilitários devem ser puras (mesmas entradas sempre produzem as mesmas saídas, sem efeitos colaterais em variáveis externas).
  - Isolar efeitos colaterais (chamadas de rede, timers, manipulação de storage/DOM) em hooks dedicados (`useEffect`, React Query, services).
- **Abordagem Declarativa vs Imperativa:**
  - Preferir métodos funcionais de lista (`map`, `filter`, `reduce`, `flatMap`, `some`, `every`, `find`) sobre loops imperativos (`for`, `while`, `for..in`) com acumuladores mutáveis (`let temp = ...`).
  - Funções pequenas com responsabilidade única (SRP), com composição clara e legível.
- **Ausência de Classes com Estado Mutável Oculto:**
  - Preferir tipos/interfaces e funções puras sobre classes com métodos alterando propriedades de `this`.
- **Early Returns & Fluxo Linear:**
  - Evitar aninhamento excessivo de `if/else`. Favorecer guard clauses e early returns (máximo 2 níveis de indentação).

#### 2. Padrões de Código e Engenharia (Skill `coding-standards`)
- **Tamanho e Responsabilidade (SRP):**
  - Funções regulares, métodos utilitários e handlers entre 4 e 20 linhas. Apontar funções de lógica > 20 linhas para refatoração.
  - **Componentes React (UI)**: Representam a entidade visual/arquivo e **NÃO** devem ser limitados a 20 linhas. Avaliar se componentes de tela (> 250 linhas) ou visuais (> 120 linhas) possuem acoplamento de estado que deveria ser extraído para **Custom Hooks** ou JSX que deveria ser modularizado em sub-componentes.
  - **Custom Hooks (`use*`)**: Focados e coesos (idealmente < 50 linhas).
  - Arquivos < 500 linhas.
  - Uma única responsabilidade por função e por módulo/arquivo.
- **Nomenclatura e Tipagem:**
  - Nomes específicos e expressivos (< 5 grep hits no codebase).
  - Proibidos nomes genéricos: `data`, `handler`, `Manager`, `info`, `helper`.
  - Tipagem 100% explícita: sem `any`, sem `Dict` genérico, sem funções com parâmetros ou retornos implícitos.
- **Exceções Semânticas:**
  - Exceções devem conter o valor causador (`offending value`) e o formato esperado (`expected shape`).
- **Comentários e Documentação:**
  - Preservar comentários existentes nas refatorações.
  - Comentários devem explicar o PORQUÊ e não o QUÊ.
  - Docstrings obrigatórias em funções públicas (intenção + 1 exemplo prático de uso).
  - Referência a issues/commits quando um ajuste contorna bugs ou limitações externas.
- **Testes Automatizados (F.I.R.S.T):**
  - Toda nova função possui teste unitário correspondente?
  - Correções de bug incluem teste de regressão?
  - Mocks de I/O externo usam **Fake Classes nomeadas** (sem stubs inline opacos)?
- **Dependências & Arquitetura:**
  - Dependências injetadas por parâmetro/construtor (sem globais/imports diretos de serviços).
  - Bibliotecas de terceiros encapsuladas por interface/wrapper do projeto (*Boundary Pattern*).
- **Logging & Formatação:**
  - Logs de depuração/observabilidade em JSON estruturado (texto plano apenas em CLI).
  - Formatação aderente ao formatador padrão do projeto (`prettier`, `biome`, etc.).

#### 3. Duplicação de Código (DRY)
- Blocos de lógica repetidos ou equivalentes em múltiplos componentes/arquivos.
- Formatações de strings, datas, máscaras ou cálculos repetidos que deveriam estar em utilitários ou hooks compartilhados.
- Componentes com layouts ou comportamentos redundantes que poderiam ser unificados com props de variação.

#### 4. Integração com Skills do Expo (quando aplicável ao `app/`)
- **`expo-native-ui`**: Uso apropriado de componentes nativos, Safe Area insets, acessibilidade, fontes do sistema e respeito às diretrizes de plataforma (iOS HIG e Android Material).
- **`expo-animation`**: Animações feitas no thread nativo via Reanimated/Gesture Handler; evitar animações na thread JS; uso adequado de springs vs timings.
- **`expo-router`**: Navegação declarativa, tratamento de parâmetros de rotas, layouts e stacks nativos.
- **`expo-data-fetching`**: Gerenciamento de cache via React Query, tratamento dos estados `isLoading`, `isError`, `data`, offline-first e retry.
- **`expo-design-system`**: Uso consistente de tokens de tema (cores, espaçamentos, tipografia), evitando estilos inline hardcoded ou cores mágicas dispersas.
- **`expo-ui`**: Uso de componentes nativos modernos (ex: SwiftUI/Jetpack Compose) quando aplicável.

#### 5. Bugs, Regressões e Inconsistências
- Classes ausentes em CSS Modules ou seletores quebrados.
- Tratamento ausente de valores nulos/undefined (`null check`, optional chaining).
- Regressões em fallbacks ou telas de estado vazio (ex: listas vazias, rotas não encontradas).
- Listeners ou timers que não são limpos no desmonte (`removeEventListener`, `clearInterval`).
- Problemas de sincronização de estado e re-renders desnecessários.

#### 6. Higiene de Código e Dependências
- Imports mortos (`dead imports`) e variáveis não utilizadas.
- Classes CSS declaradas mas nunca utilizadas no JSX.
- Commits acidentais de arquivos compilados (`lib/`, `dist/`, `*.map`).
- Arquivos de mídia pesados adicionados sem compressão.

---

### Passo 4 — Estrutura e Formatação do Relatório

O relatório DEVE ser apresentado no formato abaixo, omitindo seções vazias caso não haja apontamentos para determinada severidade:

```markdown
# 🔍 Code Review

## 🔴 CRÍTICO
*(Bugs bloqueantes, crashes, vazamentos de memória, falhas de segurança, perda de dados, bug fix sem teste de regressão)*
- **[Arquivo:Linha](file:///caminho/do/arquivo#L10)**: Título sucinto do problema
  - **Problema**: O que está incorreto ou perigoso.
  - **Impacto**: Consequência direta na aplicação ou para o usuário.
  - **Sugestão de Correção**: Snippet de código ou diff demonstrando a solução funcional recomendada.

## 🟠 ALTO
*(Bugs de regra de negócio, regressões importantes de UX, novas funções sem testes unitários, tipagem `any`/frouxa em contratos públicos, bibliotecas de terceiros acopladas diretamente sem abstração, re-renders excessivos, problemas de sincronização de estado, mutações imperativas severas)*
- **[Arquivo:Linha](file:///caminho/do/arquivo#L25)**: ...

## 🟡 MÉDIO
*(Funções de lógica/handlers > 20 linhas, componentes React com lógica/efeitos não extraídos para Custom Hooks ou componentes excessivamente inflados (> 250 linhas), arquivos > 500 linhas, violação de SRP, duplicação de código relevante, aninhamento > 2 níveis/falta de early return, mutações/efeitos colaterais em código React onde deveria ser funcional/puro, stubs inline ao invés de classes Fake nomeadas, exceções sem valor causador/shape esperado, logging não estruturado em observabilidade, classes CSS ausentes, desvios das diretrizes Expo)*
- **[Arquivo:Linha](file:///caminho/do/arquivo#L40)**: ...

## 🔵 BAIXO
*(Nomenclaturas genéricas como data/handler/Manager, comentários explicando o quê em vez de por quê, falta de docstring com exemplo em função pública, código morto/imports não utilizados, inconsistências de nomenclatura, melhorias cosméticas ou de formatação)*
- **[Arquivo:Linha](file:///caminho/do/arquivo#L55)**: ...
```
