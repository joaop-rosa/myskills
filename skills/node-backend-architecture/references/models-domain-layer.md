# Diretrizes da Camada de Models e Domínio (`models/*.js`)

Este guia define como estruturar a camada de negócio em `models/`. A arquitetura de Models deste padrão é **agnóstica de ORM**: a regra de negócio, as validações e os erros lançados são idênticos independentemente de o projeto usar **Prisma** ou **SQL Puro (`pg`)**.

---

## 1. Princípios Inegociáveis dos Models

1. **Zero Conhecimento de HTTP**: Models nunca recebem `request` ou `response`, nunca manipulam cookies/headers e nunca retornam status HTTP numéricos. Eles operam sobre primitivos e objetos de domínio (`userInputValues`, `id`, `username`) e lançam erros de `infra/errors.js` (`ValidationError`, `NotFoundError`, `UnauthorizedError`, `ForbiddenError`).
2. **Isolamento do Acesso a Dados em Funções Internas (`run*Query`)**:
   - Nenhum método público de um model deve misturar chamadas de banco/ORM diretamente no meio do fluxo de validação.
   - Toda leitura ou escrita no banco deve ser encapsulada em uma função interna `runSelectQuery`, `runInsertQuery` ou `runUpdateQuery` declarada **abaixo do `return`** da função pública.
3. **Validações de Domínio Explícitas (Nunca Dependa de Exceções do Banco/ORM)**:
   - Não deixe um `INSERT` ou `UPDATE` estourar erro nativo de constraint (como código `23505` do Postgres ou `P2002` do Prisma) para validar regras de negócio previsíveis.
   - Antes de persistir, execute funções explícitas como `validateUniqueUsername` e `validateUniqueEmail` e lance `ValidationError` com `message` e `action` orientados ao usuário.
4. **Retorno Completo Internamente**:
   - As funções `run*Query` retornam o registro completo vindo do banco (incluindo `id`, `password`, `features`, `created_at`, `updated_at`), pois outros models podem precisar desses atributos. A remoção de campos sensíveis para a resposta HTTP é responsabilidade exclusiva do `authorization.filterOutput` no Controller.

---

## 2. Como `run*Query` Desacopla o Model do ORM (Prisma vs. SQL Puro)

Graças ao isolamento via funções internas, **todo o topo do Model permanece 100% igual** em projetos com Prisma ou SQL puro; apenas o corpo de `run*Query` muda:

### Exemplo 1: Buscas Unitárias (`findOneBy*` / `findOneValidBy*`)

- Nomeie sempre como `findOneBy<Campo>` (`findOneById`, `findOneByUsername`, `findOneByEmail`) ou `findOneValidBy<Campo>` quando filtrar expiração/uso (`findOneValidByToken`, `findOneValidById`).
- Para buscas por campos de texto únicos (`username`, `email`), a comparação deve ser sempre **case-insensitive**.
- Se o registro não for encontrado, lance `NotFoundError` (ou `UnauthorizedError` em `session.findOneValidByToken`) dentro de `runSelectQuery`:

```javascript
// Fluxo público idêntico em ambos:
async function findOneByUsername(username) {
  const userFound = await runSelectQuery(username);

  return userFound;

  // --- VARIANTE A: Com Prisma ---
  async function runSelectQuery(username) {
    const user = await prisma.user.findFirst({
      where: {
        username: {
          equals: username,
          mode: "insensitive",
        },
      },
    });

    if (!user) {
      throw new NotFoundError({
        message: "O username informado não foi encontrado no sistema.",
        action: "Verifique se o username está digitado corretamente.",
      });
    }

    return user;
  }

  // --- VARIANTE B: Com SQL Puro (ver skill node-pg-sql) ---
  async function runSelectQuerySql(username) {
    const results = await database.query({
      text: `
        SELECT
          *
        FROM
          users
        WHERE
          LOWER(username) = LOWER($1)
        LIMIT
          1
        ;`,
      values: [username],
    });

    if (results.rowCount === 0) {
      throw new NotFoundError({
        message: "O username informado não foi encontrado no sistema.",
        action: "Verifique se o username está digitado corretamente.",
      });
    }

    return results.rows[0];
  }
}
```

---

### Exemplo 2: Criação de Registro (`create`)

1. Executa todas as validações de unicidade/regras (`validateUnique*`).
2. Aplica transformações no objeto de entrada com funções de nome explícito (`hashPasswordInObject`, `injectDefaultFeaturesInObject`).
3. Persiste via `runInsertQuery(userInputValues)`.

```javascript
async function create(userInputValues) {
  await validateUniqueUsername(userInputValues.username);
  await validateUniqueEmail(userInputValues.email);
  await hashPasswordInObject(userInputValues);
  injectDefaultFeaturesInObject(userInputValues);

  const newUser = await runInsertQuery(userInputValues);
  return newUser;

  // Com Prisma:
  async function runInsertQuery(userInputValues) {
    return await prisma.user.create({
      data: {
        username: userInputValues.username,
        email: userInputValues.email,
        password: userInputValues.password,
        features: userInputValues.features,
      },
    });
  }

  function injectDefaultFeaturesInObject(userInputValues) {
    userInputValues.features = ["read:activation_token"];
  }
}
```

---

### Exemplo 3: Atualização Parcial (`update`)

Para suportar operações `PATCH` previsíveis e seguras:
1. Carregue o registro existente usando `findOneBy*` (que já garante 404 `NotFoundError` se não existir).
2. Verifique quais campos foram enviados usando `"campo" in userInputValues` e execute as respectivas validações/transformações.
3. Gere um novo objeto combinando o estado atual e os novos valores: `const userWithNewValues = { ...currentUser, ...userInputValues };`.
4. Passe `userWithNewValues` para `runUpdateQuery`, garantindo a atualização de `updated_at`:

```javascript
async function update(username, userInputValues) {
  const currentUser = await findOneByUsername(username);

  if ("username" in userInputValues) {
    await validateUniqueUsername(userInputValues.username);
  }

  if ("email" in userInputValues) {
    await validateUniqueEmail(userInputValues.email);
  }

  if ("password" in userInputValues) {
    await hashPasswordInObject(userInputValues);
  }

  const userWithNewValues = { ...currentUser, ...userInputValues };

  const updatedUser = await runUpdateQuery(userWithNewValues);
  return updatedUser;

  // Com Prisma:
  async function runUpdateQuery(userWithNewValues) {
    return await prisma.user.update({
      where: { id: userWithNewValues.id },
      data: {
        username: userWithNewValues.username,
        email: userWithNewValues.email,
        password: userWithNewValues.password,
        updated_at: new Date(),
      },
    });
  }
}
```

---

## 3. Funções de Validação e Transformação Compartilhadas

- **Validações `validateUnique*`**:
  - Devem consultar apenas a existência do campo (de forma case-insensitive) e lançar `ValidationError`:
    ```javascript
    // Com Prisma:
    async function validateUniqueEmail(email) {
      const existingUser = await prisma.user.findFirst({
        where: {
          email: {
            equals: email,
            mode: "insensitive",
          },
        },
        select: { email: true },
      });

      if (existingUser) {
        throw new ValidationError({
          message: "O email informado já está sendo utilizado.",
          action: "Utilize outro email para realizar esta operação.",
        });
      }
    }
    ```
- **Mutação Explícita de Objeto (`*InObject`)**:
  - Quando uma função auxiliar modifica uma propriedade de `userInputValues` in-place, seu nome DEVE terminar com `InObject` para deixar o efeito colateral explícito na leitura:
    - `await hashPasswordInObject(userInputValues);`
    - `injectDefaultFeaturesInObject(userInputValues);`
