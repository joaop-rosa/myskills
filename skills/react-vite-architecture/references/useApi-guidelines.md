# Guia de Integração com useApi

## Visão Geral

O `useApi` é um conjunto de hooks customizados construído sobre o React Query (@tanstack/react-query) que padroniza a integração com APIs na aplicação. Fornece dois hooks principais:

- **`useQueryApi`**: Para requisições GET (leitura de dados)
- **`useMutationApi`**: Para requisições POST, PUT, DELETE (modificação de dados)

## ⚠️ Regra Essencial: Sempre Use useApi

**Toda e qualquer integração com APIs deve ser feita através dos hooks `useApi`**. Não use `fetch`, `axios` ou qualquer outra biblioteca diretamente em componentes.

### Por que?

1. **Padronização**: Garante um padrão único e consistente em toda a aplicação
2. **Tratamento de Erros**: Erros são capturados de forma centralizada
3. **Cache Automático**: React Query gerencia cache, evitando requisições duplicadas
4. **Logging**: Todos os erros são automaticamente logados através do `logCustomError`
5. **Tipagem**: Tipos específicos garantem segurança e autocomplete
6. **Maintainabilidade**: Centralizando a integração, mudanças na API ou tratamento de erros afetam toda a aplicação

### Exceções (Casos Muito Raros)

Praticamente **não há exceções**. Até mesmo requisições de terceiros devem passar por um wrapper se usarem a aplicação de forma direta.

## Regras Fundamentais

### 1. **Sempre Definir Mensagens de Erro Customizadas**

Toda integração com `useApi` deve incluir um objeto `error` com mensagens específicas do contexto:

```typescript
error: {
  logName: 'NomeDaOperacao',  // Identificador único para logs
  messages: {
    default: 'Mensagem padrão quando há erro',
    '400': 'Erro específico para código 400',
    '404': 'Recurso não encontrado',
    '500': 'Erro interno do servidor',
  },
}
```

### 2. **Usar Chaves de Query Tipadas**

As chaves de cache devem ser do tipo `Keys` (enum definido em `useApi.ts`):

```typescript
export type Keys = 'duel-cards'  // Adicionar novas chaves conforme necessário
```

Ao integrar uma nova entidade, adicione a chave correspondente:

```typescript
export type Keys = 'duel-cards' | 'users' | 'posts'  // Exemplo expandido
```

### 3. **Tipagem Genérica de Dados**

Sempre defina tipos específicos para os dados retornados:

```typescript
// ✅ Bom - tipo específico
const { data } = useQueryApi<Card[]>({ ... })

// ❌ Ruim - tipo genérico/any
const { data } = useQueryApi({ ... })
```

### 4. **Configuração de Cache**

Use `cacheTime` para controlar quanto tempo os dados permanecem em cache:

```typescript
// Sem cache (padrão)
useQueryApi({ cacheTime: 0 })

// Cache de 5 minutos
useQueryApi({ cacheTime: 5 * 60 * 1000 })

// Cache de 1 hora
useQueryApi({ cacheTime: 60 * 60 * 1000 })
```

### 5. **Execução Condicional**

Use `execute` para controlar quando a requisição é disparada:

```typescript
const [shouldFetch, setShouldFetch] = useState(false)

useQueryApi({
  execute: shouldFetch,  // Requisição só é feita quando true
  ...config
})
```

## Como Usar: useQueryApi

### Configuração Básica

```typescript
import { useQueryApi } from '../hooks/useApi'

function MyComponent() {
  const { data, error, status, refetch } = useQueryApi<UserResponse>({
    key: 'users',  // Usar chave apropriada após adicionar ao tipo Keys
    url: '/api/users',
    error: {
      logName: 'FetchUsers',
      messages: {
        default: 'Não foi possível carregar os usuários',
        '404': 'Usuários não encontrados',
        '401': 'Você não tem permissão para acessar',
      },
    },
  })

  if (status === 'pending') return <div>Carregando...</div>
  if (error) return <div>{error.firstErrorMessage}</div>
  if (!data) return <div>Sem dados</div>

  return <div>{/* Renderizar dados */}</div>
}
```

### Com Requisição Condicional

```typescript
function SearchUsers({ searchTerm }: { searchTerm: string }) {
  const { data, error, status } = useQueryApi<User[]>({
    key: 'users',
    url: `/api/users?search=${searchTerm}`,
    execute: !!searchTerm,  // Só busca se houver termo
    error: {
      logName: 'SearchUsers',
      messages: {
        default: 'Erro ao buscar usuários',
      },
    },
  })

  if (!searchTerm) return null
  if (status === 'pending') return <div>Buscando...</div>
  if (error) return <div>{error.firstErrorMessage}</div>

  return <div>{/* Renderizar resultados */}</div>
}
```

### Com Cache

```typescript
const { data } = useQueryApi<PostsResponse>({
  key: 'posts',
  url: '/api/posts',
  cacheTime: 10 * 60 * 1000,  // Cache 10 minutos
  error: {
    logName: 'FetchPosts',
    messages: {
      default: 'Erro ao carregar posts',
    },
  },
})
```

## Como Usar: useMutationApi

### Configuração Básica

```typescript
import { useMutationApi } from '../hooks/useApi'

function CreateUserForm() {
  const { mutate, status, error } = useMutationApi<UserResponse, CreateUserPayload>({
    url: '/api/users',
    method: 'POST',
    error: {
      logName: 'CreateUser',
      messages: {
        default: 'Não foi possível criar o usuário',
        '400': 'Dados inválidos',
        '409': 'Usuário já existe',
      },
    },
  })

  const handleSubmit = async (formData: CreateUserPayload) => {
    mutate(formData)
  }

  if (status === 'pending') return <button disabled>Criando...</button>

  return (
    <button onClick={() => handleSubmit({ name: 'John' })}>
      Criar Usuário
    </button>
  )
}
```

### Com Callbacks

```typescript
const { mutate, status } = useMutationApi<UserResponse, CreateUserPayload>({
  url: '/api/users',
  method: 'POST',
  error: {
    logName: 'CreateUser',
    messages: {
      default: 'Erro ao criar usuário',
    },
  },
  onSuccess: async (data, body) => {
    // Dados foram salvos com sucesso
    console.log('Usuário criado:', data)
    // Aqui você pode redirecionar, mostrar notificação, etc.
  },
  onError: async (error, body) => {
    // Erro ao salvar
    console.log('Erro:', error.firstErrorMessage)
  },
  onSettled: async (data, error, body) => {
    // Sempre executado, sucesso ou erro
    console.log('Operação finalizada')
  },
})
```

### Com Invalidação de Cache

```typescript
const { mutate } = useMutationApi<UserResponse, CreateUserPayload>({
  url: '/api/users',
  method: 'POST',
  error: {
    logName: 'CreateUser',
    messages: {
      default: 'Erro ao criar usuário',
    },
  },
  // Refazer requisição de users após criar
  refetchQueries: ['users'],  // Usar chave apropriada
  // Ou remover dados em cache
  removeQueries: ['users'],
})
```

### DELETE com Body

```typescript
const { mutate } = useMutationApi<void, DeletePayload>({
  url: '/api/users/123',
  method: 'DELETE',
  error: {
    logName: 'DeleteUser',
    messages: {
      default: 'Erro ao deletar usuário',
    },
  },
})

mutate({ reason: 'User requested deletion' })
```

## Tratamento de Erros

### Estrutura do Objeto ErrorState

```typescript
interface ErrorState {
  firstErrorMessage: string  // Primeira mensagem de erro (priorizado)
  errorMessages: Record<string | number, string>  // Todas as mensagens mapeadas
}
```

### Exemplo de Tratamento

```typescript
const { error } = useQueryApi<Data>({
  key: 'todo',
  url: '/api/data',
  error: {
    logName: 'FetchData',
    messages: {
      default: 'Erro padrão',
      '400': 'Requisição inválida',
      '401': 'Não autenticado',
      '403': 'Sem permissão',
      '500': 'Erro do servidor',
    },
  },
})

if (error) {
  // Use firstErrorMessage para exibir ao usuário
  console.log(error.firstErrorMessage)  // Ex: "Sem permissão"

  // Use errorMessages para lógica customizada
  if (error.errorMessages['401']) {
    // Redirecionar para login
  }
}
```

## Boas Práticas

### ✅ Fazer

1. **Definir tipos específicos** para dados e payloads:
   ```typescript
   useQueryApi<BlogPost>({ ... })
   useMutationApi<BlogPost, CreateBlogPostPayload>({ ... })
   ```

2. **Usar nomes descritivos** para `logName`:
   ```typescript
   logName: 'FetchUserProfile'  // ✅
   logName: 'api'               // ❌
   ```

3. **Validar dados** antes de enviar:
   ```typescript
   const validated = validateUserInput(formData)
   mutate(validated)
   ```

4. **Usar `onSettled`** para lógica que deve rodar em qualquer caso:
   ```typescript
   onSettled: (data, error, body) => {
     // Fechar modal, resetar formulário, etc.
   }
   ```

### ❌ Evitar

1. **Usar types genéricos**:
   ```typescript
   useQueryApi({ ... })           // ❌ sem tipo
   useQueryApi<any>({ ... })      // ❌ tipo genérico
   ```

2. **Não tratar status "pending"**:
   ```typescript
   if (status === 'pending') {
     return <Skeleton />  // ✅ sempre mostrar loading
   }
   ```

3. **Fazer lógica pesada em `onSuccess`**:
   ```typescript
   // ❌ Evitar operações síncronas pesadas
   onSuccess: (data) => {
     const result = processHugeArray(data)
   }
   ```

4. **Misturar requisições sem sincronização**:
   ```typescript
   // ❌ Evitar múltiplas chamadas sem refetchQueries
   mutate(data1)
   mutate(data2)
   ```

5. **Usar fetch ou axios diretamente**:
   ```typescript
   // ❌ NUNCA faça isso
   fetch('/api/data').then(res => res.json())
   axios.get('/api/data')
   new XMLHttpRequest()

   // ✅ Sempre use useQueryApi ou useMutationApi
   useQueryApi<Data>({ url: '/api/data', ... })
   ```

## Exemplo Completo

```typescript
import { useState } from 'react'
import { useQueryApi, useMutationApi } from '../hooks/useApi'

type Post = {
  id: string
  title: string
  content: string
}

type CreatePostPayload = {
  title: string
  content: string
}

export function PostManager() {
  const [shouldFetch, setShouldFetch] = useState(true)

  // Buscar posts
  const { data: posts, error: fetchError, status: fetchStatus } = useQueryApi<Post[]>({
    key: 'todo',
    url: '/api/posts',
    execute: shouldFetch,
    cacheTime: 5 * 60 * 1000,  // 5 minutos
    error: {
      logName: 'FetchPosts',
      messages: {
        default: 'Não foi possível carregar os posts',
        '401': 'Você não está autenticado',
      },
    },
  })

  // Criar novo post
  const { mutate: createPost, status: createStatus } = useMutationApi<Post, CreatePostPayload>({
    url: '/api/posts',
    method: 'POST',
    error: {
      logName: 'CreatePost',
      messages: {
        default: 'Erro ao criar post',
        '400': 'Dados inválidos',
      },
    },
    onSuccess: (data) => {
      console.log('Post criado:', data)
    },
    refetchQueries: ['todo'],  // Recarregar lista após criar
  })

  const handleCreatePost = () => {
    createPost({
      title: 'Novo Post',
      content: 'Conteúdo do post',
    })
  }

  if (fetchStatus === 'pending') return <div>Carregando posts...</div>
  if (fetchError) return <div>{fetchError.firstErrorMessage}</div>
  if (!posts) return <div>Sem posts</div>

  return (
    <div>
      <button onClick={handleCreatePost} disabled={createStatus === 'pending'}>
        {createStatus === 'pending' ? 'Criando...' : 'Criar Post'}
      </button>

      <ul>
        {posts.map((post) => (
          <li key={post.id}>{post.title}</li>
        ))}
      </ul>
    </div>
  )
}
```

## Adicionando Novas Integrações

Quando integrar uma nova entidade/recurso:

1. **Adicione a chave em `useApi.ts`**:
   ```typescript
   export type Keys = 'todo' | 'newResource'
   ```

2. **Crie tipos para requisição/resposta**:
   ```typescript
   type NewResourceResponse = { id: string; name: string }
   type CreateNewResourcePayload = { name: string }
   ```

3. **Use em componentes com o padrão estabelecido**:
   ```typescript
   const { data } = useQueryApi<NewResourceResponse[]>({
     key: 'newResource',
     url: '/api/new-resources',
     error: {
       logName: 'FetchNewResources',
       messages: {
         default: 'Erro ao carregar recursos',
       },
     },
   })
   ```

4. **Sempre forneça mensagens de erro customizadas**

## Checklist Rápido para Novas Integrações

Antes de fazer commit de qualquer integração, verifique:

- [ ] Está usando `useQueryApi` ou `useMutationApi`? (nunca fetch/axios direto)
- [ ] Adicionou a chave em `export type Keys`?
- [ ] Definiu tipos específicos para dados retornados?
- [ ] `logName` é descritivo?
- [ ] Tratou o estado `pending`?
- [ ] Tratou o caso de `error`?
- [ ] Se for mutação, definiu `onSuccess`/`onError` se necessário?
- [ ] Se for mutação, configurou `refetchQueries` ou `removeQueries`?
- [ ] Configurou `cacheTime` apropriadamente?

## Referências

- [React Query Documentation](https://tanstack.com/query/latest)
- [useApi.ts](/src/hooks/useApi.ts)
- [api.ts](/src/infra/api.ts)
- [error.ts](/src/infra/error.ts)
