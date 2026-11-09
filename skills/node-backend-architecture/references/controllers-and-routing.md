# Diretrizes de Rotas e Controllers HTTP (Next.js & Express)

Este guia define como estruturar endpoints HTTP e como separar estritamente a camada de controle HTTP (`pages/api/v1/**` ou `routes/**` + `infra/controller.js`) da camada de domínio (`models/`), tanto em projetos **Next.js (`next-connect`)** quanto em servidores **Express.js**.

---

## 1. O Pipeline de Requisição HTTP (4 Estágios)

Independentemente de o roteador ser `next-connect` (Next.js) ou `express.Router()` (Express), toda rota da API segue o mesmo pipeline determinístico:

1. **Injeção de Contexto (`controller.injectAnonymousOrUser`)**:
   - Lê o cookie `session_id`.
   - Se existir sessão válida, busca o usuário correspondente e o injeta em `request.context.user`.
   - Se não existir cookie de sessão, injeta `anonymousUserObject` em `request.context.user` com as features públicas iniciais (`["read:activation_token", "create:session", "create:user"]`).
2. **Guard de Permissão da Rota (`controller.canRequest("<feature>")`)**:
   - Middleware executado antes do handler que verifica `authorization.can(request.context.user, feature)`.
   - Se negado, interrompe a requisição lançando `ForbiddenError` (403).
3. **Handler do Verbo HTTP (`getHandler`, `postHandler`, `patchHandler`, `deleteHandler`)**:
   - Extrai os dados da requisição, orquestra chamadas aos `models/`, gerencia cookies e filtra a saída com `authorization.filterOutput`.
4. **Tratamento Centralizado de Erros (`controller.errorHandlers`)**:
   - `onNoMatch`: Retorna `405 MethodNotAllowedError` para métodos HTTP não suportados na rota.
   - `onError`: Converte as instâncias de `infra/errors.js` na resposta JSON padronizada.

---

## 2. Registro de Rotas: Next.js vs. Express.js

### 2.1. Padrão em Next.js (`pages/api/v1/<recurso>/index.js` com `next-connect`)

No Next.js, cada rota vive em `pages/api/v1/<recurso>/index.js` (ou `pages/api/v1/<recurso>/[<param>]/index.js`) e exporta `createRouter()`:

```javascript
// pages/api/v1/users/[username]/index.js
import { createRouter } from "next-connect";
import controller from "infra/controller.js";
import user from "models/user.js";
import authorization from "models/authorization.js";
import { ForbiddenError } from "infra/errors.js";

export default createRouter()
  .use(controller.injectAnonymousOrUser)
  .get(getHandler)
  .patch(controller.canRequest("update:user"), patchHandler)
  .handler(controller.errorHandlers);

async function getHandler(request, response) {
  // ...
}

async function patchHandler(request, response) {
  // ...
}
```

### 2.2. Padrão Equivalente em Express.js (`routes/v1/<recurso>.js`)

Em projetos Express (recomendado Express 5+, que captura rejeições de `async` nativamente), a estrutura do arquivo de rota mantém **exatamente os mesmos handlers e middlewares**:

```javascript
// routes/v1/users.routes.js
import { Router } from "express";
import controller from "infra/controller.js";
import user from "models/user.js";
import authorization from "models/authorization.js";
import { ForbiddenError } from "infra/errors.js";

const router = Router();

router.use(controller.injectAnonymousOrUser);

router
  .route("/users/:username")
  .get(getHandler)
  .patch(controller.canRequest("update:user"), patchHandler)
  .all(controller.errorHandlers.onNoMatch);

export default router;

async function getHandler(request, response) {
  // No Express, parâmetros de rota vêm de request.params (ou unificados)
  const username = request.params.username;
  // ...
}

async function patchHandler(request, response) {
  // ...
}
```

E no `app.js` / `server.js` principal do Express, registre o `cookie-parser`, as rotas e o `onError` global (com assinatura de 4 argumentos exigida pelo Express):

```javascript
import express from "express";
import cookieParser from "cookie-parser";
import controller from "infra/controller.js";
import usersRouter from "routes/v1/users.routes.js";

const app = express();
app.use(express.json());
app.use(cookieParser());

app.use("/api/v1", usersRouter);

// Error handler global do Express delegando para o controller padronizado
app.use((error, request, response, _next) => {
  controller.errorHandlers.onError(error, request, response);
});

export default app;
```

---

## 3. Anatomia de um Handler de Controller

Os handlers (`getHandler`, `postHandler`, `patchHandler`, `deleteHandler`) são sempre declarados **abaixo** da definição da rota e seguem 5 passos estritos:

1. **Extrair Ator e Dados da Requisição**:
   - `const userTryingToPatch = request.context.user;`
   - `const username = request.query?.username ?? request.params?.username;`
   - `const userInputValues = request.body;`
2. **Validar Autorização sobre o Recurso Alvo (quando necessário)**:
   - Se a ação exigir verificar *quem* é o dono do recurso (ex.: um usuário atualizando seu próprio perfil vs. tentando atualizar outro usuário), carregue o recurso alvo e consulte `authorization.can` passando o 3º argumento (`targetUser`):
   ```javascript
   const targetUser = await user.findOneByUsername(username);

   if (!authorization.can(userTryingToPatch, "update:user", targetUser)) {
     throw new ForbiddenError({
       message: "Você não possui permissão para atualizar outro usuário.",
       action:
         "Verifique se você possui a feature necessária para atualizar outro usuário.",
     });
   }
   ```
3. **Delegar Regras de Negócio e Persistência aos `models/`**:
   - Chame `user.create`, `user.update`, `activation.create`, `session.create`, etc.
   - **Proibido** executar queries (SQL ou Prisma) ou validações de banco diretamente dentro do controller.
4. **Aplicar Cookies ou Headers HTTP**:
   - Utilize exclusivamente `controller.setSessionCookie(token, response)` e `controller.clearSessionCookie(response)`.
   - Quando a rota retornar dados sensíveis da sessão atual (`GET /api/v1/user`), previna cache HTTP:
     ```javascript
     response.setHeader(
       "Cache-Control",
       "no-store, no-cache, max-age=0, must-revalidate",
     );
     ```
5. **Filtrar a Saída (`authorization.filterOutput`) e Responder**:
   - **Regra Inegociável**: Nunca envie um objeto retornado pelo model diretamente no `.json()`. Sempre atribua o retorno de `authorization.filterOutput` à variável `secureOutputValues`:

```javascript
async function postHandler(request, response) {
  const userTryingToPost = request.context.user;
  const userInputValues = request.body;
  const newUser = await user.create(userInputValues);

  const activationToken = await activation.create(newUser.id);
  await activation.sendEmailToUser(newUser, activationToken);

  const secureOutputValues = authorization.filterOutput(
    userTryingToPost,
    "read:user",
    newUser,
  );

  return response.status(201).json(secureOutputValues);
}
```

---

## 4. Implementação Canônica de `infra/controller.js`

```javascript
import * as cookie from "cookie";
import session from "models/session.js";
import user from "models/user.js";
import authorization from "models/authorization.js";

import {
  InternalServerError,
  MethodNotAllowedError,
  ValidationError,
  NotFoundError,
  UnauthorizedError,
  ForbiddenError,
} from "infra/errors.js";

function onNoMatchHandler(request, response) {
  const publicErrorObject = new MethodNotAllowedError();
  response.status(publicErrorObject.statusCode).json(publicErrorObject);
}

function onErrorHandler(error, request, response) {
  if (
    error instanceof ValidationError ||
    error instanceof NotFoundError ||
    error instanceof ForbiddenError
  ) {
    return response.status(error.statusCode).json(error);
  }

  if (error instanceof UnauthorizedError) {
    clearSessionCookie(response);
    return response.status(error.statusCode).json(error);
  }

  const publicErrorObject = new InternalServerError({
    cause: error,
  });

  console.error(publicErrorObject);

  response.status(publicErrorObject.statusCode).json(publicErrorObject);
}

function setSessionCookie(sessionToken, response) {
  const setCookie = cookie.serialize("session_id", sessionToken, {
    path: "/",
    maxAge: session.EXPIRATION_IN_MILLISECONDS / 1000,
    secure: process.env.NODE_ENV === "production",
    httpOnly: true,
    sameSite: "lax",
  });

  response.setHeader("Set-Cookie", setCookie);
}

function clearSessionCookie(response) {
  const setCookie = cookie.serialize("session_id", "invalid", {
    path: "/",
    maxAge: -1,
    secure: process.env.NODE_ENV === "production",
    httpOnly: true,
  });

  response.setHeader("Set-Cookie", setCookie);
}

async function injectAnonymousOrUser(request, response, next) {
  if (request.cookies?.session_id) {
    await injectAuthenticatedUser(request);
    return next();
  }

  injectAnonymousUser(request);
  return next();
}

async function injectAuthenticatedUser(request) {
  const sessionToken = request.cookies.session_id;
  const sessionObject = await session.findOneValidByToken(sessionToken);
  const userObject = await user.findOneById(sessionObject.user_id);

  request.context = {
    ...request.context,
    user: userObject,
  };
}

function injectAnonymousUser(request) {
  const anonymousUserObject = {
    features: ["read:activation_token", "create:session", "create:user"],
  };

  request.context = {
    ...request.context,
    user: anonymousUserObject,
  };
}

function canRequest(feature) {
  return function canRequestMiddleware(request, response, next) {
    const userTryingToRequest = request.context.user;

    if (authorization.can(userTryingToRequest, feature)) {
      return next();
    }

    throw new ForbiddenError({
      message: "Você não possui permissão para executar esta ação.",
      action: `Verifique se o seu usuário possui a feature "${feature}"`,
    });
  };
}

const controller = {
  errorHandlers: {
    onNoMatch: onNoMatchHandler,
    onError: onErrorHandler,
  },
  setSessionCookie,
  clearSessionCookie,
  injectAnonymousOrUser,
  canRequest,
};

export default controller;
```
