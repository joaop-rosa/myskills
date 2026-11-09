# Diretrizes de Autenticação e Autorização (`models/authentication.js` & `models/authorization.js`)

Este guia detalha o sistema de controle de acesso baseado em **Features (RBAC granular)**, o fluxo seguro de autenticação e a filtragem obrigatória de dados de saída.

---

## 1. Autorização Baseada em Features (`models/authorization.js`)

Em vez de papéis estáticos (`admin`, `moderator`, `user`), todo usuário (autenticado ou anônimo) carrega um array `features: string[]`.

### 1.1. Convenção de Nomenclatura de Features
Toda feature segue o formato `<verbo>:<recurso>` ou `<verbo>:<recurso>:<escopo>`:
- `create:<recurso>` (ex.: `create:user`, `create:session`, `create:migration`)
- `read:<recurso>` (ex.: `read:user`, `read:session`, `read:activation_token`, `read:migration`, `read:status`)
- `read:<recurso>:<escopo>` (ex.: `read:user:self`, `read:status:all`)
- `update:<recurso>` e `update:<recurso>:<escopo>` (ex.: `update:user`, `update:user:others`)

### 1.2. Estados e Progressão de Features do Usuário
1. **Usuário Anônimo** (injetado em `request.context.user` quando não há sessão):
   - `["read:activation_token", "create:session", "create:user"]`
2. **Usuário Recém-Cadastrado / Pendente de Ativação**:
   - `["read:activation_token"]` (impede que um usuário já logado ou inativo crie novas contas ou faça login antes de ativar o e-mail).
3. **Usuário Ativo Padrão (`Default user`)**:
   - `["create:session", "read:session", "update:user"]` (definido via `user.setFeatures` no momento da ativação).
4. **Usuário Privilegiado (`Privileged user`)**:
   - Recebe features adicionais via `user.addFeatures` (ex.: `["update:user:others"]`).

---

## 2. Checklist para Criar uma Nova Feature

Ao adicionar um novo endpoint ou permissão, execute estes **4 passos obrigatórios** em `models/authorization.js`:

1. **Cadastrar na Constante `availableFeatures`**:
   - `availableFeatures` é uma allowlist estrita. Qualquer chamada a `can()` ou `filterOutput()` com uma feature ausente dessa lista lança `InternalServerError`.
2. **Implementar a Regra em `can(user, feature, resource)`**:
   - Sempre valide os argumentos no início com `validateUser(user)` e `validateFeature(feature)`.
   - Para ações que dependem de titularidade sobre o recurso (`resource`), exija que `user.id === resource.id` ou que o usuário possua a feature de escopo `:others`:
   ```javascript
   function can(user, feature, resource) {
     validateUser(user);
     validateFeature(feature);

     let authorized = false;

     if (user.features.includes(feature)) {
       authorized = true;
     }

     if (feature === "update:user" && resource) {
       authorized = false;

       if (user.id === resource.id || can(user, "update:user:others")) {
         authorized = true;
       }
     }

     return authorized;
   }
   ```
3. **Implementar a Allowlist de Saída em `filterOutput(user, feature, resource)`**:
   - Sempre valide `validateUser(user)`, `validateFeature(feature)` e `validateResource(resource)` no topo.
   - Construa explicitamente um **novo objeto literal** listando apenas os atributos públicos/permitidos para aquela feature.
   - **Proibido** usar `delete resource.password` ou espalhar `...resource` (se uma coluna nova sensível for criada no banco no futuro, o spread a vazaria automaticamente).
   ```javascript
   if (feature === "read:user") {
     return {
       id: resource.id,
       username: resource.username,
       features: resource.features,
       created_at: resource.created_at,
       updated_at: resource.updated_at,
     };
   }

   if (feature === "read:user:self") {
     if (user.id === resource.id) {
       return {
         id: resource.id,
         username: resource.username,
         email: resource.email,
         features: resource.features,
         created_at: resource.created_at,
         updated_at: resource.updated_at,
       };
     }
   }
   ```
4. **Adicionar Testes Unitários em `tests/unit/models/authorization.test.js`**:
   - Teste as guard clauses (`without user`, `without user.features`, `with unknown feature`, `without resource`) e o formato exato retornado por `filterOutput`.

---

## 3. Guard Clauses Defensivas em `authorization.js`

As funções internas `validateUser`, `validateFeature` e `validateResource` protegem o sistema contra bugs de programação (esquecer de passar `user`, `feature` ou `resource` nos controllers), lançando `InternalServerError`:

```javascript
function validateUser(user) {
  if (!user || !user.features) {
    throw new InternalServerError({
      cause: "É necessário fornecer `user` no model `authorization`.",
    });
  }
}

function validateFeature(feature) {
  if (!feature || !availableFeatures.includes(feature)) {
    throw new InternalServerError({
      cause:
        "É necessário fornecer uma `feature` conhecida no model `authorization`.",
    });
  }
}

function validateResource(resource) {
  if (!resource) {
    throw new InternalServerError({
      cause:
        "É necessário fornecer um `resource` em `authorization.filterOutput()`.",
    });
  }
}
```

---

## 4. Autenticação com Prevenção de Enumeração (`models/authentication.js`)

Ao autenticar credenciais (`email` + `password`), mantenha mensagens específicas nas funções auxiliares internas (úteis para debug/stack trace via `cause` se necessário), mas capture `UnauthorizedError` no bloco `try/catch` de `getUser` para expor uma mensagem única na API pública:

```javascript
async function getUser(providedEmail, providedPassword) {
  try {
    const storedUser = await findUserByEmail(providedEmail);
    await validatePassword(providedPassword, storedUser.password);

    return storedUser;
  } catch (error) {
    if (error instanceof UnauthorizedError) {
      throw new UnauthorizedError({
        message: "Dados de autenticação não conferem.",
        action: "Verifique se os dados enviados estão corretos.",
      });
    }

    throw error;
  }

  async function findUserByEmail(providedEmail) {
    let storedUser;

    try {
      storedUser = await user.findOneByEmail(providedEmail);
    } catch (error) {
      if (error instanceof NotFoundError) {
        throw new UnauthorizedError({
          message: "Email não confere.",
          action: "Verifique se este dado está correto.",
        });
      }

      throw error;
    }

    return storedUser;
  }

  async function validatePassword(providedPassword, storedPassword) {
    const correctPasswordMatch = await password.compare(
      providedPassword,
      storedPassword,
    );

    if (!correctPasswordMatch) {
      throw new UnauthorizedError({
        message: "Senha não confere.",
        action: "Verifique se este dado está correto.",
      });
    }
  }
}
```
