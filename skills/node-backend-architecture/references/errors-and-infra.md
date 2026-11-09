# Diretrizes de Erros Customizados e Serviços de Infraestrutura (`infra/*.js`)

Este guia define a hierarquia de erros customizados, a forma de redigir mensagens/ações de erro e o padrão de encapsulamento de serviços externos em `infra/`.

---

## 1. Hierarquia de Classes de Erro (`infra/errors.js`)

Todas as classes de erro estendem a classe nativa `Error` do JavaScript e implementam o método `toJSON()` para garantir um contrato de resposta uniforme em toda a API:

```json
{
  "name": "ValidationError",
  "message": "O email informado já está sendo utilizado.",
  "action": "Utilize outro email para realizar esta operação.",
  "status_code": 400
}
```

### Catálogo Canônico de Erros:

| Classe | `statusCode` | Quando Lançar | Comportamento no `onErrorHandler` |
| :--- | :---: | :--- | :--- |
| `ValidationError` | `400` | Dados de entrada inválidos ou violação de regra de unicidade (`username`/`email` duplicado). | Retorna `400` com o JSON do erro. |
| `UnauthorizedError` | `401` | Usuário sem sessão válida, token expirado ou falha de credenciais no login. | Limpa o cookie `session_id` (`clearSessionCookie`) e retorna `401`. |
| `ForbiddenError` | `403` | Usuário autenticado (ou anônimo) sem a `feature` necessária ou tentando alterar recurso de terceiro. | Retorna `403` com o JSON do erro. |
| `NotFoundError` | `404` | Recurso buscado (`id`, `username`, `email`, `token_id`) não existe ou já foi consumido/expirado. | Retorna `404` com o JSON do erro. |
| `MethodNotAllowedError` | `405` | Verbo HTTP não suportado pelo endpoint (`onNoMatchHandler`). | Retorna `405` com o JSON do erro. |
| `InternalServerError` | `500` | Falha inesperada, violação de guard clause interna ou mascaramento de `ServiceError` para o cliente externo. | Loga o erro completo via `console.error(publicErrorObject)` e retorna `500`. |
| `ServiceError` | `503` | Queda ou falha de comunicação com infraestrutura externa (Banco de Dados, Servidor SMTP, API terceira). | Capturado pelo fallback do `onErrorHandler`, anexado como `cause` de um `InternalServerError` (ou com seu `statusCode` preservado quando desejado) e logado com `context`. |

---

## 2. Forma de Escrita de `message` e `action`

Ao instanciar qualquer erro de domínio ou de infraestrutura, siga estas diretrizes de redação:

1. **Idioma e Pontuação**: Sempre em português claro, iniciando com letra maiúscula e terminando com ponto final (exceto quando `action` termina com uma feature entre aspas, como `'Verifique se o seu usuário possui a feature "create:user"'`).
2. **`message` (Diagnóstico Objetivo)**: Descreve **o que aconteceu** sem jargões internos de banco/stack trace.
   - *Exemplos*:
     - `"O username informado já está sendo utilizado."`
     - `"O id informado não foi encontrado no sistema."`
     - `"Você não possui permissão para executar esta ação."`
     - `"Usuário não possui sessão ativa."`
3. **`action` (Instrução Acionável)**: Orienta exatamente **o que o usuário ou desenvolvedor consumidor da API deve fazer** para corrigir o problema.
   - *Exemplos*:
     - `"Utilize outro username para realizar esta operação."`
     - `"Verifique se o id está digitado corretamente."`
     - `"Faça novamente o login para continuar."`
     - `"Entre em contato com o suporte."`
4. **Encadeamento de `cause`**: Sempre que um erro for lançado dentro de um bloco `catch (error)`, passe `{ cause: error }` no construtor para preservar a stack trace original do Node.js.

---

## 3. Implementação Completa de `infra/errors.js`

```javascript
export class InternalServerError extends Error {
  constructor({ cause, statusCode }) {
    super("Um erro interno não esperado aconteceu.", {
      cause,
    });
    this.name = "InternalServerError";
    this.action = "Entre em contato com o suporte.";
    this.statusCode = statusCode || 500;
  }

  toJSON() {
    return {
      name: this.name,
      message: this.message,
      action: this.action,
      status_code: this.statusCode,
    };
  }
}

export class ServiceError extends Error {
  constructor({ cause, message, action, context }) {
    super(message || "Serviço indisponível no momento.", {
      cause,
    });
    this.name = "ServiceError";
    this.action = action || "Verifique se o serviço está disponível.";
    this.statusCode = 503;
    this.context = context;
  }

  toJSON() {
    return {
      name: this.name,
      message: this.message,
      action: this.action,
      status_code: this.statusCode,
      context: this.context,
    };
  }
}

export class ValidationError extends Error {
  constructor({ cause, message, action }) {
    super(message || "Um erro de validação ocorreu.", {
      cause,
    });
    this.name = "ValidationError";
    this.action = action || "Ajuste os dados enviados e tente novamente.";
    this.statusCode = 400;
  }

  toJSON() {
    return {
      name: this.name,
      message: this.message,
      action: this.action,
      status_code: this.statusCode,
    };
  }
}

export class NotFoundError extends Error {
  constructor({ cause, message, action }) {
    super(message || "Não foi possível encontrar este recurso no sistema.", {
      cause,
    });
    this.name = "NotFoundError";
    this.action =
      action || "Verifique se os parâmetros enviados na consulta estão certos.";
    this.statusCode = 404;
  }

  toJSON() {
    return {
      name: this.name,
      message: this.message,
      action: this.action,
      status_code: this.statusCode,
    };
  }
}

export class ForbiddenError extends Error {
  constructor({ cause, message, action }) {
    super(message || "Acesso negado.", {
      cause,
    });
    this.name = "ForbiddenError";
    this.action =
      action || "Verifique as features necessárias antes de continuar.";
    this.statusCode = 403;
  }

  toJSON() {
    return {
      name: this.name,
      message: this.message,
      action: this.action,
      status_code: this.statusCode,
    };
  }
}

export class UnauthorizedError extends Error {
  constructor({ cause, message, action }) {
    super(message || "Usuário não autenticado.", {
      cause,
    });
    this.name = "UnauthorizedError";
    this.action = action || "Faça novamente o login para continuar.";
    this.statusCode = 401;
  }

  toJSON() {
    return {
      name: this.name,
      message: this.message,
      action: this.action,
      status_code: this.statusCode,
    };
  }
}

export class MethodNotAllowedError extends Error {
  constructor() {
    super("Método não permitido para este endpoint.");
    this.name = "MethodNotAllowedError";
    this.action =
      "Verifique se o método HTTP enviado é válido para este endpoint.";
    this.statusCode = 405;
  }

  toJSON() {
    return {
      name: this.name,
      message: this.message,
      action: this.action,
      status_code: this.statusCode,
    };
  }
}
```

---

## 4. Padrão de Adapters de Infraestrutura (`infra/email.js`, `infra/webserver.js`)

Todo serviço externo (envio de e-mail, gateway de pagamento, storage S3, etc.) deve ser encapsulado em `infra/<servico>.js` seguindo o padrão *Module Object*:

1. **Nunca exponha o SDK terceiro diretamente aos `models/`**: O model chama `email.send(mailOptions)`, nunca `nodemailer` diretamente.
2. **Capture falhas e converta em `ServiceError`**: Anexe a exceção original em `cause` e os parâmetros de tentativa em `context` para facilitar o diagnóstico nos logs:

```javascript
// infra/email.js
import nodemailer from "nodemailer";
import { ServiceError } from "./errors.js";

const transporter = nodemailer.createTransport({
  host: process.env.EMAIL_SMTP_HOST,
  port: process.env.EMAIL_SMTP_PORT,
  auth: {
    user: process.env.EMAIL_SMTP_USER,
    pass: process.env.EMAIL_SMTP_PASSWORD,
  },
  secure: process.env.NODE_ENV === "production" ? true : false,
});

async function send(mailOptions) {
  try {
    await transporter.sendMail(mailOptions);
  } catch (error) {
    throw new ServiceError({
      message: "Não foi possível enviar o email.",
      action: "Verifique se o serviço de email está disponível.",
      cause: error,
      context: mailOptions,
    });
  }
}

const email = {
  send,
};

export default email;
```

3. **Resolução Centralizada de Origem/Ambiente (`infra/webserver.js`)**:
   - Evite espalhar `process.env.NODE_ENV` ou URLs hardcoded nos models e testes; exponha `webserver.origin`:
   ```javascript
   function getOrigin() {
     if (["test", "development"].includes(process.env.NODE_ENV)) {
       return `http://localhost:${process.env.PORT || 3000}`;
     }

     if (process.env.VERCEL_ENV === "preview") {
       return `https://${process.env.VERCEL_URL}`;
     }

     return process.env.WEB_ORIGIN;
   }

   const webserver = {
     origin: getOrigin(),
   };

   export default webserver;
   ```
