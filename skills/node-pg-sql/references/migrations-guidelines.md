# Diretrizes de Migrations (`infra/migrations/*.js` & `models/migrator.js`)

Este guia define como criar e executar migrations de banco de dados utilizando `node-pg-migrate`.

---

## 1. Criação e Nomenclatura de Migrations

- Crie novas migrations sempre via script do `package.json`:
  ```bash
  npm run migrations:create <nome-da-migration-em-kebab-case>
  ```
- Os arquivos são gerados em `infra/migrations/<timestamp>_<nome-da-migration>.js` (ex.: `1739649142726_create-users.js`, `1758201790990_add-features-to-users.js`).

---

## 2. Regras de Escrita de uma Migration

1. **Política *Forward-Only* (`exports.down = false`)**:
   - Toda migration deve definir `exports.down = false;` na última linha.
2. **Chave Primária (`id`) Sempre UUID v4 Nativo**:
   ```javascript
   id: {
     type: "uuid",
     primaryKey: true,
     default: pgm.func("gen_random_uuid()"),
   },
   ```
3. **Colunas de Data/Hora Sempre `timestamptz` em UTC**:
   - Nunca utilize `timestamp` sem timezone. Utilize sempre `timestamptz` com default `pgm.func("timezone('utc', now())")` para `created_at` e `updated_at`:
   ```javascript
   // Why timestamp with timezone? https://justatheory.com/2012/04/postgres-use-timestamptz/
   created_at: {
     type: "timestamptz",
     notNull: true,
     default: pgm.func("timezone('utc', now())"),
   },

   updated_at: {
     type: "timestamptz",
     notNull: true,
     default: pgm.func("timezone('utc', now())"),
   },
   ```
4. **Documente o "Porquê" dos Limites de `varchar(N)`**:
   - Sempre que definir um limite específico de caracteres em uma coluna `varchar`, adicione um comentário acima da coluna com a referência técnica ou link que justifica aquele número:

```javascript
exports.up = (pgm) => {
  pgm.createTable("users", {
    id: {
      type: "uuid",
      primaryKey: true,
      default: pgm.func("gen_random_uuid()"),
    },

    // For reference, GitHub limits usernames to 39 characters.
    username: {
      type: "varchar(30)",
      notNull: true,
      unique: true,
    },

    // Why 254 in length? https://stackoverflow.com/a/1199238
    email: {
      type: "varchar(254)",
      notNull: true,
      unique: true,
    },

    // Why 60 in length? https://www.npmjs.com/package/bcrypt#hash-info
    password: {
      type: "varchar(60)",
      notNull: true,
    },

    // Why timestamp with timezone? https://justatheory.com/2012/04/postgres-use-timestamptz/
    created_at: {
      type: "timestamptz",
      notNull: true,
      default: pgm.func("timezone('utc', now())"),
    },

    updated_at: {
      type: "timestamptz",
      notNull: true,
      default: pgm.func("timezone('utc', now())"),
    },
  });
};

exports.down = false;
```

---

## 3. Runner Programático (`models/migrator.js`)

O model `migrator` permite listar e rodar migrations pendentes tanto via endpoint (`GET/POST /api/v1/migrations`) quanto via `tests/orchestrator.js`, reutilizando uma única instância de conexão (`dbClient`) por execução:

```javascript
import migrationRunner from "node-pg-migrate";
import { resolve } from "node:path";
import database from "infra/database.js";

const defaultMigrationOptions = {
  dryRun: true,
  dir: resolve("infra", "migrations"),
  direction: "up",
  log: () => {},
  migrationsTable: "pgmigrations",
};

async function listPendingMigrations() {
  let dbClient;

  try {
    dbClient = await database.getNewClient();

    const pendingMigrations = await migrationRunner({
      ...defaultMigrationOptions,
      dbClient,
    });
    return pendingMigrations;
  } finally {
    await dbClient?.end();
  }
}

async function runPendingMigrations() {
  let dbClient;

  try {
    dbClient = await database.getNewClient();

    const migratedMigrations = await migrationRunner({
      ...defaultMigrationOptions,
      dbClient,
      dryRun: false,
    });

    return migratedMigrations;
  } finally {
    await dbClient?.end();
  }
}

const migrator = {
  listPendingMigrations,
  runPendingMigrations,
};

export default migrator;
```
