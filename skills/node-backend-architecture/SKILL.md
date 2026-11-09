---
name: node-backend-architecture
description: >-
  Aplica e orquestra as diretrizes canônicas de arquitetura, forma de escrita e padrões de engenharia para backends em Node.js (Next.js API Routes ou Express, compatível com Prisma ou SQL puro). Cobre o padrão Module Object, leitura Top-Down com funções internas aninhadas (run*Query), vocabulário semântico, controllers finos, hierarquia de erros customizados, RBAC por features (can e filterOutput) e testes de integração caixa-preta com orchestrator. Ative sempre ao criar, refatorar ou revisar rotas de API, controllers, models, middlewares de autenticação/autorização, erros de domínio/infraestrutura ou testes em projetos backend Node.js.
---

# Diretrizes de Arquitetura e Escrita para Backends Node.js

Esta skill define a arquitetura em camadas (Controllers, Models e Infra), a **forma de escrita de código** e a estratégia de testes para backends em **Node.js** (**Next.js** com `next-connect` ou **Express.js**), sendo **agnóstica de ORM** (funciona tanto com **Prisma** quanto em conjunto com a skill `node-pg-sql` para **SQL Puro**).

---

## 1. Princípios Transversais Inegociáveis

1. **Padrão *Module Object* (Zero Classes em Domínio/Infra)**:
   - Nunca utilize `class` ou `this` em `models/`, `controllers/` ou serviços de `infra/`. Declare funções nomeadas no arquivo e exporte um objeto literal com `export default` no final (`const user = { create, findOneById, ... }; export default user;`).
   - O uso de `class` é exclusivo para as classes de erro em `infra/errors.js` (`extends Error`).
2. **Leitura *Top-Down* com Hoisting Intencional (`run*Query` abaixo do `return`)**:
   - O topo de cada função pública de um `model` narra a regra de negócio passo a passo (validações -> transformações -> chamada à função de persistência -> `return`).
   - As funções auxiliares de banco (`runSelectQuery`, `runInsertQuery`, `runUpdateQuery`) e helpers locais (`injectDefaultFeaturesInObject`) são declaradas **dentro da função pública, abaixo do `return`**.
3. **Desacoplamento de ORM na Fronteira `run*Query`**:
   - Regras de negócio e validações (`validateUniqueUsername`, `validateUniqueEmail`, `hashPasswordInObject`) residem no Model e nunca dependem de exceções nativas do Prisma (`P2002`) ou do driver SQL. O código específico do Prisma ou do `database.query` fica estritamente confinado dentro das funções `run*Query`.
4. **Controllers Finos e Pipeline Determinístico**:
   - Toda rota segue o pipeline: `controller.injectAnonymousOrUser` -> `controller.canRequest("<feature>")` -> `<verbo>Handler` (`getHandler`, `postHandler`, `patchHandler`, `deleteHandler`) -> `controller.errorHandlers`.
   - Controllers apenas extraem inputs, validam permissão sobre o recurso alvo (`authorization.can`), orquestram models, manipulam cookies e filtram a saída.
5. **Filtragem Obrigatória de Saída (`authorization.filterOutput`)**:
   - Nenhum dado retornado por um model pode ser enviado diretamente em `response.json()`. Todo retorno passa por `authorization.filterOutput(userTryingTo*, feature, resource)` gerando `secureOutputValues` (allowlist explícita de propriedades).
6. **Erros Semânticos Orientados à Ação**:
   - Todo erro operacional (`ValidationError` 400, `UnauthorizedError` 401, `ForbiddenError` 403, `NotFoundError` 404, `MethodNotAllowedError` 405, `InternalServerError` 500, `ServiceError` 503) possui `message` (o que ocorreu) e `action` (como o cliente resolve), em português, serializando via `toJSON()` em `snake_case` (`{ name, message, action, status_code }`).
7. **Testes de Integração Caixa-Preta com `orchestrator`**:
   - Endpoints são testados com requisições HTTP reais (`fetch`), banco de dados real e serviços reais, organizados por arquivo de verbo HTTP (`get.test.js`, `post.test.js`, `patch.test.js`, `delete.test.js`) e agrupados por persona (`Anonymous user`, `Default user`, `Privileged user`).

---

## 2. Fontes de Referência das Diretrizes (Progressive Disclosure)

Consulte o guia específico correspondente à tarefa em execução:

- [Forma de Escrita, Hoisting, Vocabulário e Case](./references/code-style-and-conventions.md)
- [Rotas e Controllers HTTP (Next.js & Express)](./references/controllers-and-routing.md)
- [Models, Regras de Domínio e Fronteira `run*Query` (Prisma / SQL)](./references/models-domain-layer.md)
- [Autenticação e Autorização Baseada em Features (RBAC)](./references/auth-and-authorization.md)
- [Hierarquia de Erros e Serviços de Infraestrutura](./references/errors-and-infra.md)
- [Testes Automatizados e Padrão Orchestrator](./references/testing-and-orchestrator.md)

> [!TIP]
> Se o projeto utilizar **SQL Puro com `pg` e `node-pg-migrate`** (sem Prisma), carregue também a skill complementar **`node-pg-sql`** para aplicar as regras de formatação de queries SQL e criação de migrations.

---

## 3. Mapeamento Tarefa -> Diretriz

- **Escrever ou refatorar qualquer código JS/TS no backend**:
  Leia [code-style-and-conventions.md](./references/code-style-and-conventions.md) (regra transversal obrigatória).
- **Criar ou alterar um endpoint de API, rota Next.js/Express ou manipulação de cookies**:
  Leia [controllers-and-routing.md](./references/controllers-and-routing.md) e [auth-and-authorization.md](./references/auth-and-authorization.md).
- **Criar ou alterar um Model (`models/*.js`), validação de negócio ou integração com Prisma/Banco**:
  Leia [models-domain-layer.md](./references/models-domain-layer.md).
- **Adicionar uma nova permissão (`feature`), regra de acesso (`can`) ou filtro de resposta (`filterOutput`)**:
  Leia [auth-and-authorization.md](./references/auth-and-authorization.md).
- **Criar erros customizados, tratar falhas ou integrar serviços externos (SMTP/e-mail, storage, filas)**:
  Leia [errors-and-infra.md](./references/errors-and-infra.md).
- **Escrever testes de integração de API, fluxos `_use-cases`, testes unitários ou helpers no `tests/orchestrator.js`**:
  Leia [testing-and-orchestrator.md](./references/testing-and-orchestrator.md).

---

## 4. Modo de Execução Obrigatório

Ao implementar qualquer funcionalidade ou correção em um backend Node.js seguindo esta skill:

1. **Respeite o Vocabulário e a Forma de Escrita**:
   - Nomeie variáveis conforme o padrão (`userTryingToPost`, `userInputValues`, `secureOutputValues`, `sessionObject`).
   - Posicione funções `runSelectQuery`, `runInsertQuery` e `runUpdateQuery` abaixo do `return` da função pública do model.
2. **Garanta a Segurança de Ponta a Ponta**:
   - Registre novas features em `availableFeatures`, proteja a rota com `controller.canRequest`, valide posse de recurso com `authorization.can` quando aplicável e filtre a saída com `authorization.filterOutput`.
3. **Cobertura de Testes**:
   - Crie ou atualize os testes unitários (`tests/unit/`) e de integração (`tests/integration/api/v1/<recurso>/<verbo>.test.js`) cobrindo as personas aplicáveis (`Anonymous user`, `Default user`, `Privileged user`).
4. **Validação Determinística**:
   - Execute os scripts de lint, formatação e testes presentes no `package.json` do projeto (ex.: `npm run lint:eslint:check`, `npm run lint:prettier:check`, `npm test`) e corrija qualquer apontamento antes de concluir.
