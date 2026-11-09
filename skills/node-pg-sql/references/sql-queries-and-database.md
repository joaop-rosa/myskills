# Cliente de Banco (`infra/database.js`) e Escrita de Queries SQL

Este guia define como implementar o módulo de conexão com o PostgreSQL (`infra/database.js`) e como formatar queries SQL puras dentro dos `models/`.

---

## 1. Implementação Canônica de `infra/database.js`

O módulo `infra/database.js` encapsula o pacote `pg`, gerencia o ciclo de vida do `Client` por query e traduz qualquer falha de conexão ou sintaxe SQL em `ServiceError`:

```javascript
import { Client } from "pg";
import { ServiceError } from "./errors.js";

async function query(queryObject) {
  let client;
  try {
    client = await getNewClient();
    const result = await client.query(queryObject);
    return result;
  } catch (error) {
    const serviceErrorObject = new ServiceError({
      message: "Erro na conexão com Banco ou na Query.",
      cause: error,
    });
    throw serviceErrorObject;
  } finally {
    await client?.end();
  }
}

async function getNewClient() {
  const client = new Client({
    host: process.env.POSTGRES_HOST,
    port: process.env.POSTGRES_PORT,
    user: process.env.POSTGRES_USER,
    database: process.env.POSTGRES_DB,
    password: process.env.POSTGRES_PASSWORD,
    ssl: getSSLValues(),
  });

  await client.connect();
  return client;
}

const database = {
  query,
  getNewClient,
};

export default database;

function getSSLValues() {
  if (process.env.POSTGRES_CA) {
    return {
      ca: process.env.POSTGRES_CA,
    };
  }

  return process.env.NODE_ENV === "production" ? true : false;
}
```

---

## 2. Estilo Visual e Formatação de Queries SQL

Todas as queries enviadas a `database.query` devem ser escritas em **template literals multi-linha**, seguindo estas regras de formatação:

1. **Cláusulas SQL em MAIÚSCULO em Linha Própria**:
   - `SELECT`, `FROM`, `WHERE`, `LIMIT`, `INSERT INTO`, `VALUES`, `UPDATE`, `SET`, `RETURNING` ficam sozinhos em sua linha, e o conteúdo de cada cláusula fica indentado 2 espaços à direita na linha seguinte.
   - Operadores adicionais no `WHERE` (`AND`, `OR`) iniciam uma nova linha alinhada com a condição anterior.
2. **Fechamento com Ponto e Vírgula (`;`)**:
   - Finalize o comando SQL com `;` na última linha do template literal.

### 2.1. Template de `SELECT` Unitário (`runSelectQuery`)

```javascript
async function runSelectQuery(username) {
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
```

### 2.2. Template de `INSERT` (`runInsertQuery`)

Sempre utilize `RETURNING *` para devolver o registro completo recém-criado com seu `id`, `created_at` e `updated_at` gerados pelo PostgreSQL:

```javascript
async function runInsertQuery(userInputValues) {
  const results = await database.query({
    text: `
      INSERT INTO
        users (username, email, password, features)
      VALUES
        ($1, $2, $3, $4)
      RETURNING
        *
      ;`,
    values: [
      userInputValues.username,
      userInputValues.email,
      userInputValues.password,
      userInputValues.features,
    ],
  });
  return results.rows[0];
}
```

### 2.3. Template de `UPDATE` (`runUpdateQuery`)

Sempre atualize `updated_at = timezone('utc', now())` e retorne `RETURNING *`:

```javascript
async function runUpdateQuery(userWithNewValues) {
  const results = await database.query({
    text: `
      UPDATE
        users
      SET
        username = $2,
        email = $3,
        password = $4,
        updated_at = timezone('utc', now())
      WHERE
        id = $1
      RETURNING
        *
      ;`,
    values: [
      userWithNewValues.id,
      userWithNewValues.username,
      userWithNewValues.email,
      userWithNewValues.password,
    ],
  });

  return results.rows[0];
}
```

---

## 3. Idiomas SQL Frequentes no Projeto

- **Comparação Case-Insensitive**: Use `LOWER(coluna) = LOWER($1)` tanto nas buscas (`findOneByUsername`, `findOneByEmail`) quanto nas validações (`validateUniqueUsername`, `validateUniqueEmail`).
- **Validação de Expiração e Uso Único em Tokens/Sessões**:
  ```sql
  WHERE
    id = $1
    AND expires_at > NOW()
    AND used_at IS NULL
  ```
- **Concatenação de Arrays no PostgreSQL (`features`)**:
  - Para adicionar novas features sem sobrescrever as existentes em `user.addFeatures`:
  ```sql
  UPDATE
    users
  SET
    features = array_cat(features, $2),
    updated_at = timezone('utc', now())
  WHERE
    id = $1
  RETURNING
    *
  ;
  ```
- **Expiração Forçada de Sessão (`session.expireById`)**:
  - Em vez de deletar o registro de sessão do banco (preservando histórico de auditoria), subtraia 1 ano de `expires_at`:
  ```sql
  UPDATE
    sessions
  SET
    expires_at = expires_at - interval '1 year',
    updated_at = NOW()
  WHERE
    id = $1
  RETURNING
    *
  ;
  ```
