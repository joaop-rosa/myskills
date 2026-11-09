---
name: node-pg-sql
description: >-
  Aplica as convenções canônicas de persistência PostgreSQL com SQL puro (pacote pg, sem ORM) e migrations com node-pg-migrate em backends Node.js. Cobre a implementação do cliente infra/database.js, formatação e indentação de queries SQL parametrizadas dentro de run*Query, buscas case-insensitive com LOWER(), atualizações em UTC e criação de migrations forward-only (UUID, timestamptz, down = false) e models/migrator.js. Ative ao criar ou manter queries SQL, models com database.query ou migrations com node-pg-migrate em projetos Node.js sem ORM.
---

# Persistência PostgreSQL com SQL Puro (`pg`) e `node-pg-migrate`

Esta skill complementa a `node-backend-architecture` para projetos Node.js que utilizam **SQL puro** com o driver `pg` e **`node-pg-migrate`** em vez de um ORM como Prisma.

---

## 1. Regras Estritas e Proibições

1. **Queries 100% Parametrizadas (`$1, $2...`)**:
   - **Proibido** interpolar variáveis diretamente na string SQL (`WHERE id = '${id}'`). Sempre envie `{ text: \`...\`, values: [...] }` para `database.query`.
2. **Isolamento dentro de `run*Query`**:
   - Chamadas a `database.query` nos models devem ficar dentro das funções internas `runSelectQuery`, `runInsertQuery` ou `runUpdateQuery` declaradas abaixo do `return` da função pública (ou dentro de funções `validateUnique*`).
3. **Conexão Fechada com `finally`**:
   - Todo método em `infra/database.js` ou `models/migrator.js` que abre um `client` do `pg` deve obrigatoriamente fechá-lo no bloco `finally { await client?.end(); }`.
4. **Migrations *Forward-Only* (`exports.down = false`)**:
   - Toda migration criada em `infra/migrations/` deve definir explicitamente `exports.down = false;`. Rollbacks em produção são feitos via novas migrations corretivas para frente.
5. **Timestamps sempre em UTC (`timestamptz`)**:
   - Colunas de data/hora devem ser do tipo `timestamptz` com default `timezone('utc', now())`, e atualizações de `updated_at` em queries `UPDATE` devem usar `updated_at = timezone('utc', now())`.

---

## 2. Fontes de Referência

- [Cliente `infra/database.js` e Formatação de Queries SQL](./references/sql-queries-and-database.md)
- [Migrations com `node-pg-migrate` e `models/migrator.js`](./references/migrations-guidelines.md)

---

## 3. Mapeamento Tarefa -> Diretriz

- **Configurar conexão com PostgreSQL, escrever `SELECT`, `INSERT` ou `UPDATE` em models**:
  Leia [sql-queries-and-database.md](./references/sql-queries-and-database.md).
- **Criar uma nova tabela, adicionar coluna ou manipular o runner de migrations**:
  Leia [migrations-guidelines.md](./references/migrations-guidelines.md).
