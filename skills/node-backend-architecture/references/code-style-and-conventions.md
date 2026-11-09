# Forma de Escrita e Convenções de Código (Code Style & Idioms)

Este guia documenta a assinatura estilística, organização sintática e convenções de nomenclatura utilizadas no desenvolvimento de backends Node.js (`infra/`, `models/`, `controllers/routes` e `tests/`).

---

## 1. Módulos ES (ESM) e Imports Absolutos

- **ES Modules por Padrão**: Utilize `import` e `export default` em todos os arquivos de `infra/`, `models/`, rotas/controllers e `tests/`.
  - *Exceção*: Arquivos de configuração ou ferramentas CLI que exijam CommonJS (`jest.config.js`, `commitlint.config.js`, migrations do `node-pg-migrate`).
- **Imports Absolutos via `jsconfig.json` / `tsconfig.json`**: Configure `"baseUrl": "."` para nunca utilizar caminhos relativos longos (`../../`). Importe módulos internos diretamente a partir da raiz do projeto:

```javascript
// ✅ Correto
import controller from "infra/controller.js";
import user from "models/user.js";
import authorization from "models/authorization.js";
import { ValidationError, NotFoundError } from "infra/errors.js";

// ❌ Incorreto (caminhos relativos entre camadas)
import controller from "../../infra/controller.js";
import user from "../models/user.js";
```

- **Módulos Nativos do Node.js**: Utilize sempre o prefixo explícito `node:` ao importar pacotes built-in:
  ```javascript
  import crypto from "node:crypto";
  import { resolve } from "node:path";
  ```

---

## 2. Padrão *Module Object* (Zero Classes em Domínio/Infra)

- **Proibido usar `class` ou `this` em `models/`, `controllers/` e serviços de `infra/`**:
  - A única exceção para o uso de `class` em todo o backend é o arquivo `infra/errors.js` (onde as classes de erro estendem `Error`).
- **Declaração de Funções + Objeto Exportado no Final**:
  - Declare funções nomeadas (`async function create(...)`, `function can(...)`) no escopo do módulo.
  - Ao final do arquivo, agrupe apenas as funções e constantes públicas em uma constante com o nome do módulo e exporte-a com `export default`:

```javascript
// models/password.js
import bcryptjs from "bcryptjs";

async function hash(password) {
  const rounds = getNumberOfRounds();
  return await bcryptjs.hash(password, rounds);
}

function getNumberOfRounds() {
  return process.env.NODE_ENV === "production" ? 14 : 1;
}

async function compare(providedPassword, storedPassword) {
  return await bcryptjs.compare(providedPassword, storedPassword);
}

const password = {
  hash,
  compare,
};

export default password;
```

---

## 3. Leitura *Top-Down* com Funções Aninhadas (*Hoisting* Intencional)

Uma das marcas mais fortes da escrita deste código é o uso intencional do **function hoisting** do JavaScript dentro de funções de domínio e de orquestração:

1. **Fluxo de Negócio no Topo**: As primeiras linhas da função pública funcionam como um índice executivo que narra a regra de negócio passo a passo (validações -> transformações -> chamada de persistência -> `return`).
2. **Detalhes de Implementação Abaixo do `return`**: Funções auxiliares exclusivas daquela operação — especialmente `runSelectQuery`, `runInsertQuery`, `runUpdateQuery` ou helpers locais como `injectDefaultFeaturesInObject` — são declaradas **dentro da função pública, logo abaixo da instrução `return`**.

```javascript
// ✅ Padrão Canônico de Leitura Top-Down
async function create(userInputValues) {
  await validateUniqueUsername(userInputValues.username);
  await validateUniqueEmail(userInputValues.email);
  await hashPasswordInObject(userInputValues);
  injectDefaultFeaturesInObject(userInputValues);

  const newUser = await runInsertQuery(userInputValues);
  return newUser;

  async function runInsertQuery(userInputValues) {
    // Implementação do acesso a dados (Prisma ou SQL puro) fica isolada aqui embaixo
  }

  function injectDefaultFeaturesInObject(userInputValues) {
    userInputValues.features = ["read:activation_token"];
  }
}
```

### Critério: Quando manter aninhada abaixo do `return` vs. extrair para o módulo?
- **Mantenha aninhada abaixo do `return`**: Quando a função executa a operação de persistência específica daquele método (`runSelectQuery`, `runInsertQuery`, `runUpdateQuery`) ou uma sub-etapa que só faz sentido dentro daquela função (ex.: `findUserByEmail` e `validatePassword` dentro de `authentication.getUser`, ou `waitForWebServer` dentro de `orchestrator.waitForAllServices`).
- **Extraia para o escopo do arquivo (fora da função)**: Quando a regra ou validação é compartilhada entre múltiplos métodos do mesmo model (ex.: `validateUniqueUsername`, `validateUniqueEmail` e `hashPasswordInObject` compartilhados entre `user.create` e `user.update`).

---

## 4. Vocabulário Semântico de Variáveis

Nunca utilize nomes vagos ou abreviados (`data`, `res`, `req`, `input`, `output`, `err`, `u`, `usr`). Siga o vocabulário padronizado:

| Contexto | Nome Canônico | Uso |
| :--- | :--- | :--- |
| Parâmetros HTTP do handler | `(request, response)` ou `(request, response, next)` | Nunca abrevie para `(req, res, next)` |
| Ator que realiza a requisição | `userTryingToGet`, `userTryingToPost`, `userTryingToPatch`, `userTryingToDelete`, `userTryingToRequest` | Identifica quem está tentando executar a ação a partir de `request.context.user` |
| Payload bruto de entrada | `userInputValues` (ou `<recurso>InputValues`) | Dados recebidos de `request.body` e repassados para `create`/`update` no model |
| Registro atual antes de atualizar | `currentUser`, `targetUser`, `userToActivate` | Registro carregado do banco antes de validar permissão ou fazer merge |
| Registro mesclado para update | `userWithNewValues` | Resultado de `{ ...currentUser, ...userInputValues }` |
| Retorno de busca no banco | `userFound`, `sessionFound`, `storedUser` | Registro retornado por `findOne*` |
| Retorno de criação ou mutação | `newUser`, `updatedUser`, `newSession`, `renewedSessionObject`, `expiredSessionObject`, `newToken`, `usedActivationToken` | Registro retornado por `create`, `update`, `renew`, `expireById` |
| Saída sanitizada para o cliente | `secureOutputValues` | Resultado obrigatório de `authorization.filterOutput(...)` antes de enviar o JSON |
| Desambiguação de instância vs. módulo | `sessionObject`, `anonymousUserObject`, `activationTokenObject`, `publicErrorObject`, `serviceErrorObject` | Sufixo `Object` evita sombrear o módulo importado (`session`, `activation`) |

---

## 5. Fronteira de Case (`camelCase` vs. `snake_case`)

Mantenha uma separação clara entre o código interno JavaScript e as interfaces externas (JSON/Banco):

1. **`camelCase` (Interno no JavaScript)**:
   - Variáveis, argumentos, funções, métodos e propriedades internas de classes JS (`statusCode`, `sessionToken`, `activationTokenId`, `userId`).
2. **`snake_case` (Contratos JSON de API, Cookies e Colunas de Banco)**:
   - Campos serializados em respostas HTTP e em `error.toJSON()`: `status_code`, `created_at`, `updated_at`, `expires_at`, `used_at`, `user_id`, `max_connections`, `opened_connections`.
   - Nome do cookie de sessão: `session_id`.
3. **`UPPER_SNAKE_CASE` (Constantes de Módulo)**:
   - Sempre escreva durações de tempo em milissegundos usando a multiplicação explícita acompanhada de comentário com a unidade legível:
     ```javascript
     const EXPIRATION_IN_MILLISECONDS = 60 * 60 * 24 * 30 * 1000; // 30 Days
     const EXPIRATION_IN_MILLISECONDS = 60 * 15 * 1000; // 15 minutes
     ```
