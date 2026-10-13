---
name: coding-standards
description: >-
  Diretrizes canônicas de qualidade de código, Clean Code, arquitetura, testes, tipagem,
  documentação e logging. DEVE ser ativada e seguida obrigatoriamente SEMPRE que for escrever,
  implementar, refatorar, criar ou modificar código (funções, classes, arquivos, testes e módulos)
  em qualquer linguagem ou framework, e serve como referência obrigatória para auditorias e revisões de código.
---

# Padrões de Código e Engenharia de Software (Coding Standards)

Este documento define os padrões canônicos e obrigatórios de qualidade de código, boas práticas de engenharia e arquitetura.
Deve ser seguido **sempre que for escrever, implementar ou refatorar código**, e serve como critério formal na execução de **Code Reviews**.

---

## 1. Estilo de Código & Clean Code

- **Tamanho de Funções e Métodos de Lógica**: Entre **4 e 20 linhas**.
  - Aplica-se a: funções de negócio, utilitários, transformações de dados, helpers e event handlers.
  - Se uma função utilitária ou handler ultrapassar 20 linhas, divida-a imediatamente por responsabilidade.
- **Componentes React (Unidades de UI / Arquivo)**:
  - Componentes React representam a entidade visual/estrutural do arquivo e são governados primariamente pela **regra de tamanho de arquivos** e coesão de UI, **não** pelo limite de 20 linhas.
  - **Limites de complexidade**:
    - Componentes atômicos e visuais reutilizáveis: idealmente **< 100–120 linhas**.
    - Componentes de Tela/Container (Screens/Pages): até **150–250 linhas**.
    - Limite máximo do arquivo: sempre **< 500 linhas**.
  - **Critérios de Decomposição de Componentes**:
    1. **Extração de Estado e Efeitos (Custom Hooks)**: Componentes React devem priorizar renderização e composição de UI. Regras de negócio, listeners, fluxos assíncronos e múltiplos `useEffect`/`useState` DEVEM ser extraídos para **Custom Hooks dedicados** (ex: `useMapCamera`, `useRouteTrack`).
    2. **Decomposição de JSX**: Árvores de JSX extensas, seções modais ou itens repetidos devem ser extraídos em sub-componentes especializados.
    3. **Handlers Internos**: Callbacks e handlers (`handlePress`, `onChange`) dentro do componente continuam sujeitos à regra de funções curtas (< 20 linhas).
- **Custom Hooks (`use*`)**:
  - Encapsulam lógica de estado e ciclo de vida. Devem ser focados e coesos (idealmente até **40–50 linhas**). Se ultrapassarem essa faixa, devem ser divididos em sub-hooks ou máquinas de estado/reducers.
- **Tamanho de Arquivos**: Máximo de **500 linhas**. Arquivos que excederem esse limite devem ser decompostos por domínio e responsabilidade.
- **Responsabilidade Única (SRP)**:
  - Uma única responsabilidade por função.
  - Uma única responsabilidade por módulo/arquivo (em React: 1 componente principal por arquivo).
- **Nomenclatura Específica e Única**:
  - Nomes devem ser expressivos, descritivos e precisos.
  - Priorize nomes que gerem **menos de 5 ocorrências (`< 5 grep hits`)** no codebase.
  - **Termos proibidos**: Evite terminologias genéricas como `data`, `handler`, `Manager`, `info`, `item`, `helper`.
- **Tipagem Estrita e Explícita**:
  - Proibido o uso de `any`, `Dict` genérico ou tipos evasivos/permissivos.
  - Nenhuma função deve ficar sem tipagem explícita em seus parâmetros e tipo de retorno.
- **Sem Duplicação de Código (DRY)**:
  - Não repita lógica de negócio, transformações ou regras de validação.
  - Extraia blocos compartilhados ou equivalentes para funções ou módulos utilitários coesos.
- **Controle de Fluxo Linear & Early Returns**:
  - Priorize guard clauses e early returns sobre blocos `if/else` aninhados.
  - Limite estrito de **no máximo 2 níveis de indentação** no corpo de qualquer bloco ou função.
- **Mensagens de Exceção Semânticas**:
  - Toda exceção ou erro lançado DEVE obrigatoriamente informar o valor causador (`offending value`) e o formato/estrutura esperada (`expected shape`).
  - *Exemplo*: Em vez de `"Invalid configuration"`, use `f"Invalid configuration for 'timeout': received {timeout!r}, expected positive integer"`.

---

## 2. Paradigma Funcional & Imutabilidade (Exclusivo para Código React / Frontend)

> [!NOTE]
> Esta diretriz aplica-se especificamente ao código **React, React Native e ecossistema Frontend/UI**, onde o modelo de reconciliação, reatividade e previsibilidade de estado exigem imutabilidade estrita. Em código backend, scripts ou linguagens onde laços imperativos são idiomáticos (Go, Python, etc.), respeite as convenções naturais da respectiva linguagem.

- **Transformações Declarativas de Coleções (`map`, `filter`, `reduce`)**:
  - Em componentes, hooks e utilitários de UI, prefira métodos funcionais de lista (`map`, `filter`, `reduce`, `flatMap`, `some`, `every`, `find`) sobre loops imperativos (`for`, `while`, `for..in`, `for..of`) com acumuladores mutáveis (`let resultado = []`).
- **Imutabilidade Rigorosa**:
  - Evite mutações diretas em arrays ou objetos (`.push()`, `.splice()`, `obj.prop = val`).
  - Utilize operações imutáveis (`[...arr, item]`, `{ ...obj, prop: val }`, `.concat()`, `.toSorted()`).
  - Em React, garanta que estados (`useState`, `useReducer`), props e referências nunca sofram mutações diretas.
- **Funções Puras & Efeitos Isolados**:
  - Funções de transformação de dados, helpers e renderização devem ser puras (mesmas entradas sempre produzem as mesmas saídas, sem efeitos colaterais).
  - I/O, timers, chamadas de rede e sincronizações de storage devem ser estritamente isolados em hooks dedicados (`useEffect`, React Query, services).
- **Ausência de Classes com Estado Mutável Oculto**:
  - Em código React/Frontend, prefira tipos/interfaces e funções puras sobre classes com métodos alterando propriedades de `this`.

---

## 3. Comentários & Documentação

- **Preservação de Intenção**:
  - Mantenha comentários existentes. Nunca os remova sumariamente durante refatorações — eles carregam intenção, histórico e contexto de decisões passadas.
- **Documente o "PORQUÊ", nunca o "O QUÊ"**:
  - Não adicione comentários redundantes ou óbvios (ex: `// incrementa contador` acima de `i++`).
  - Escreva o motivo técnico ou regra de negócio por trás da decisão: por que essa abordagem foi escolhida ou qual restrição ela atende.
- **Docstrings em Funções Públicas**:
  - Toda função pública ou de interface exposta DEVE conter docstring com:
    1. **Intenção** clara da função.
    2. **Um exemplo prático de uso**.
- **Rastreabilidade de Bugs e Restrições**:
  - Quando uma linha, ajuste ou contorno existir devido a um bug específico, issue upstream ou restrição externa de plataforma, referencie o número da issue ou o commit SHA no comentário explicativo.

---

## 4. Testes Automatizados (F.I.R.S.T)

- **Comando Único de Execução**:
  - Os testes do projeto devem rodar através de um comando único padronizado (ex: `npm test`, `pytest`, `cargo test`, `go test ./...`).
- **Cobertura Contínua e Regressão**:
  - **Toda nova função** deve vir acompanhada de seu teste unitário correspondente.
  - **Toda correção de bug** deve incluir obrigatoriamente um teste de regressão que reproduza a falha e comprove a correção.
- **Isolamento de I/O Externo com Fakes Nomeados**:
  - I/O externo (APIs, Banco de Dados, Sistema de Arquivos, Mensageria) DEVE ser mockado através de **Fake Classes nomeadas** (ex: `FakeUserRepository`, `FakeHttpClient`, `FakeFileSystem`).
  - **Proibido o uso de stubs inline** soltos e opacos espalhados nos arquivos de teste.
- **Princípios F.I.R.S.T**:
  - **F**ast: Testes devem rodar rapidamente para permitir feedback contínuo.
  - **I**ndependent: Nenhum teste deve depender do estado ou da execução de outro teste.
  - **R**epeatable: Devem produzir o mesmo resultado em qualquer ambiente (local, CI/CD, container).
  - **S**elf-validating: O teste deve ter resultado binário claro (passou ou falhou), sem necessidade de inspeção manual de logs.
  - **T**imely: Escritos no momento do desenvolvimento do código de produção (ou antes, via TDD).

---

## 5. Dependências & Arquitetura

- **Injeção de Dependências**:
  - Injete dependências via construtor ou parâmetros de função.
  - Não utilize variáveis globais, singletons implícitos ou imports diretos para serviços de infraestrutura acoplados.
- **Encapsulamento de Bibliotecas Terceiras**:
  - Encapsule bibliotecas de terceiros atrás de uma interface/abstração fina pertencente ao próprio projeto (*Boundary / Adapter Pattern*).
  - O código de domínio da aplicação nunca deve acoplar tipos ou APIs proprietárias de bibliotecas externas diretamente.
- **Estrutura e Convenções**:
  - Siga estritamente as convenções do framework utilizado (Rails, Django, Next.js, Expo, NestJS, etc.).
  - Prefira módulos pequenos e coesos a "god files" ou arquivos genéricos.
  - Mantenha caminhos e estruturas de pastas previsíveis (`controller/model/view`, `src/lib/test`, etc.).

---

## 6. Formatação

- Utilize exclusivamente o formatador oficial ou padrão adotado pela linguagem/projeto (`prettier`, `biome`, `cargo fmt`, `gofmt`, `black`, `rubocop -A`).
- Não discuta nem introduza regras manuais ou divergentes de estilo visual além do que o formatador automatizado define.

---

## 7. Logging & Observabilidade

- **JSON Estruturado para Observabilidade**:
  - Logs de depuração, telemetria, erros e auditoria de sistema DEVEM ser formatados em **JSON estruturado** com campos padronizados (ex: `timestamp`, `level`, `context`, `error`, `trace_id`).
- **Texto Puro para Linha de Comando**:
  - O formato de texto plano (*plain text*) é reservado única e exclusivamente para saídas de CLI voltadas ao usuário final no terminal.
