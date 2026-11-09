# Diretrizes de Testes Automatizados e Orquestrador (`tests/**`)

Este guia define a arquitetura de testes (integração por verbo HTTP, casos de uso ponta a ponta e testes unitários), a escrita de cenários por persona e o padrão do `tests/orchestrator.js`.

---

## 1. Estrutura de Diretórios de Testes

Os arquivos de teste espelham a estrutura da aplicação divididos em 3 categorias:

```text
tests/
├── orchestrator.js                                      # Utilitário central de setup e factories de teste
├── integration/
│   ├── _use-cases/
│   │   └── registration-flow.test.js                    # Jornadas completas multi-endpoint
│   ├── api/
│   │   └── v1/
│   │       ├── users/
│   │       │   ├── post.test.js                         # 1 arquivo para cada verbo HTTP
│   │       │   └── [username]/
│   │       │       ├── get.test.js
│   │       │       └── patch.test.js
│   │       └── sessions/
│   │           ├── post.test.js
│   │           └── delete.test.js
│   └── infra/
│       └── email.test.js                                # Testes de integração de adaptadores de infra
└── unit/
    └── models/
        └── authorization.test.js                        # Testes unitários rápidos para lógica pura
```

### Regras de Execução:
- Sempre execute o Jest de forma serial (`jest --runInBand --verbose`) para evitar condições de corrida no banco de dados real compartilhado entre suítes de integração.
- O comando `npm test` deve subir os containers necessários (`services:up`), iniciar o servidor da aplicação (Next.js ou Express) e rodar o Jest em paralelo via `concurrently`, derrubando ou parando os serviços no `posttest`.

---

## 2. Anatomia de um Teste de Integração de API (`<verbo>.test.js`)

1. **Zero Mocks de Banco ou HTTP**:
   - Os testes de integração fazem chamadas `fetch` reais para `${webserver.origin}/api/v1/...`.
   - Após validar a resposta HTTP (`status` e `responseBody`), o teste consulta diretamente o model (`await user.findOneByUsername(...)`) quando precisa confirmar efeitos colaterais não expostos no JSON (como verificar se a senha foi salva com hash via `password.compare`).
2. **Setup no `beforeAll` via `orchestrator`**:
   - Todo arquivo de teste de integração inicia limpando o banco e rodando as migrations:
   ```javascript
   beforeAll(async () => {
     await orchestrator.waitForAllServices();
     await orchestrator.clearDatabase();
     await orchestrator.runPendingMigrations();
   });
   ```
3. **Agrupamento de `describe` por Persona (Ator)**:
   - O `describe` externo identifica o verbo e a rota: `describe("PATCH /api/v1/users/[username]", () => { ... })`.
   - Os `describe` internos dividem os cenários pelo perfil de permissão do ator:
     - `describe("Anonymous user", () => { ... })`
     - `describe("Default user", () => { ... })`
     - `describe("Privileged user", () => { ... })`
4. **Nomenclatura dos `test(...)` e Uso de Backticks**:
   - Comece sempre com `"With ..."` ou `"Retrieving ..."`, envolvendo nomes de campos ou variáveis entre crases (ex.: `test("With unique and valid data", ...)`, `test("With duplicated \`email\`", ...)`, `test("With \`userB\` targeting \`userA\`", ...)`).
5. **Asserções Estritas de Contrato (`toEqual`)**:
   - Nunca valide apenas `expect(response.status).toBe(200)`. Valide o objeto completo retornado usando `expect(responseBody).toEqual({ ... })`.
   - Para campos dinâmicos (`id`, `created_at`, `updated_at`), referencie a própria propriedade no `toEqual` e adicione asserções explícitas logo abaixo:

```javascript
expect(response.status).toBe(201);

const responseBody = await response.json();

expect(responseBody).toEqual({
  id: responseBody.id,
  username: "filipedeschamps",
  features: ["read:activation_token"],
  created_at: responseBody.created_at,
  updated_at: responseBody.updated_at,
});

expect(uuidVersion(responseBody.id)).toBe(4);
expect(Date.parse(responseBody.created_at)).not.toBeNaN();
expect(Date.parse(responseBody.updated_at)).not.toBeNaN();
```

   - Para respostas de erro, valide sempre as 4 propriedades do contrato de erro:
```javascript
expect(response.status).toBe(400);

const responseBody = await response.json();

expect(responseBody).toEqual({
  name: "ValidationError",
  message: "O email informado já está sendo utilizado.",
  action: "Utilize outro email para realizar esta operação.",
  status_code: 400,
});
```

---

## 3. Padrão do `tests/orchestrator.js`

O `orchestrator` centraliza a preparação do ambiente e as *factories* de entidades para que os testes não precisem repetir chamadas HTTP de cadastro/ativação/login quando esse não é o alvo do teste:

- **Factories com `@faker-js/faker`**:
  - `orchestrator.createUser(userObject)`: Aceita sobrescrever apenas o campo relevante para o teste (ex.: `await orchestrator.createUser({ username: "user1" })`) e preenche o restante com dados aleatórios válidos do Faker.
  - `orchestrator.activateUser(inactiveUser)`: Ativa o usuário diretamente via `activation.activateUserByUserId`.
  - `orchestrator.createSession(userObject)`: Cria uma sessão válida diretamente via `session.create(userObject.id)` para enviar no header `Cookie: session_id=${sessionObject.token}`.
  - `orchestrator.addFeaturesToUser(userObject, features)`: Concede features extras para testar cenários de `Privileged user`.

### Adaptação de `clearDatabase` e `runPendingMigrations` (SQL Puro vs. Prisma):

```javascript
// --- VARIANTE A: Com SQL Puro + node-pg-migrate ---
async function clearDatabase() {
  await database.query("drop schema public cascade; create schema public;");
}

async function runPendingMigrations() {
  await migrator.runPendingMigrations();
}

// --- VARIANTE B: Com Prisma ---
// No Prisma, quando o schema já foi aplicado antes da suíte de testes (ex: prisma migrate deploy),
// clearDatabase pode truncar as tabelas em cascata mantendo a estrutura do schema:
async function clearDatabasePrisma() {
  const tablenames = await prisma.$queryRaw`
    SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename != '_prisma_migrations';
  `;

  const tables = tablenames
    .map(({ tablename }) => `"public"."${tablename}"`)
    .join(", ");

  if (tables.length > 0) {
    await prisma.$executeRawUnsafe(`TRUNCATE TABLE ${tables} CASCADE;`);
  }
}
```

---

## 4. Testes de Casos de Uso (`tests/integration/_use-cases/*.test.js`)

Diferente dos testes por verbo HTTP (onde cada `test()` é totalmente independente e cria seus próprios dados via `orchestrator`), um teste em `_use-cases/` valida uma **jornada sequencial de ponta a ponta** compartilhando variáveis de estado entre os blocos `test()` dentro do mesmo `describe`:

1. `test("Create user account", ...)` -> faz `POST /api/v1/users` e guarda `createUserResponseBody`.
2. `test("Receive activation email", ...)` -> busca o último e-mail via `orchestrator.getLastEmail()`, extrai o UUID com `orchestrator.extractUUID(lastEmail.text)` e guarda `activationTokenId`.
3. `test("Activate account", ...)` -> faz `PATCH /api/v1/activations/${activationTokenId}` e verifica as novas features do usuário.
4. `test("Login", ...)` -> faz `POST /api/v1/sessions` e guarda `createSessionsResponseBody`.
5. `test("Get user information", ...)` -> faz `GET /api/v1/user` enviando o cookie `session_id` e valida o acesso autenticado.
