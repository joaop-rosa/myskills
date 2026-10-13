# Diretrizes para Arquitetura

## Princípio Transversal
- Sempre considere escopo local primeiro.
- Promova para escopo global apenas quando houver necessidade real de compartilhamento entre múltiplas rotas/features.
- Em caso de dúvida, mantenha local.

## Estrutura orientada a rotas e features
- O projeto usa Vite + React com roteamento por arquivos via **TanStack Router** em `src/routes/`.
- Cada rota deve ser tratada como uma feature.
- Organize o código por página primeiro e, dentro da página, por responsabilidade.

### Regras para `routes/`
- Arquivo da rota: mantenha no nível de `routes/` quando a tela for simples.
- Pasta da rota: crie somente quando houver código específico da página além do arquivo principal.
- Ao criar pasta da rota, declare a rota em `routes/nome-da-rota/route.tsx` e mantenha o conteúdo em `index.tsx`.
- Pastas e arquivos que **não** são rotas devem usar o prefixo `-` (ex.: `-components/`, `-hooks/`, `-modals/`): o `@tanstack/router-plugin` ignora esse prefixo. O prefixo `_` é reservado para rotas pathless e não deve ser usado em pastas comuns.
- Em arquivos de rota, exporte a rota com `export const Route = createFileRoute('/caminho')({ component: ... })`; o componente da tela fica em uma função nomeada no mesmo arquivo.

### Convenção recomendada
- `routes/nome-da-rota.tsx`:
  - Use para páginas simples, sem componentes/hooks/contexts exclusivos.
- `routes/nome-da-rota/`:
  - Use quando a rota tiver estrutura própria.
  - Estrutura interna sugerida:
    - `route.tsx` (layout/entrada da rota)
    - `index.tsx` (rota index do diretório)
    - `-components/` (se necessário)
    - `-hooks/` (se necessário)
    - `-contexts/` (se necessário)
    - `-modals/` (se necessário)
    - `-services/` (se necessário)

### Convenção para Modais
- Use `src/modals/` para modais reutilizáveis entre múltiplas páginas.
- Em features de página, use `routes/nome-da-rota/-modals/` para modais exclusivos daquela rota.
- Modais locais devem ser registrados em um `DialogProvider` no `route.tsx` da própria rota/feature.
- Ao usar `-modals/`, declare a rota em `routes/nome-da-rota/route.tsx` para encapsular o provider e manter o escopo local.
- Promova um modal de `-modals/` para `src/modals/` apenas quando houver reuso real em mais de uma página.

## Boas Práticas de Arquitetura
- Separe lógica de apresentação e lógica de negócios.
- Utilize `contexts/` globais para estado realmente compartilhado entre múltiplas rotas, priorizando `zustand`.
- Prefira hooks para encapsular lógica reutilizável.
- Mantenha o que é específico da rota dentro da própria pasta da rota.
- Promova para `components/`, `hooks/` ou `contexts/` globais apenas o que for reutilizado por mais de uma página.

## Organização por escopo
- `routes/`: definição de rotas e features por tela.
- `components/`: componentes reutilizáveis entre páginas.
- `modals/`: modais reutilizáveis entre páginas.
- `hooks/`: hooks reutilizáveis entre páginas.
- `contexts/`: arquivos globais de estado e providers de integração.
- `infra/`: API, clientes HTTP, cookies, tratamento de erro e integrações externas.

### Convenção para `contexts/` globais
- Para estado global de cliente, use `zustand`.
- Mantenha no mesmo arquivo a definição da store e das actions.
- Separe store de actions: actions devem ser funções separadas responsáveis por atualizar a store.
- Consuma estado e actions diretamente pelo hook da store (ex.: `useAuthStore(selector)`).
- `Provider` é opcional para stores Zustand e só deve ser criado quando precisar encapsular lógica global da aplicação.
- Use React Context apenas quando uma biblioteca exigir provider/context obrigatoriamente.

## Diretrizes de roteamento
- Mantenha a criação e a configuração do router (opções globais, `routeTree`) no nível de `router.tsx`.
- Evite concentrar regra de negócio em `router.tsx`; a regra deve ficar na feature da rota.
- Composição/layout de uma rota fica no `route.tsx` do diretório da rota.
- Para rotas com modais, estados locais e fluxos próprios, prefira pasta dedicada em `routes/`.

### Navegação interna
- **Sempre** utilize `Link` ou `useNavigate` do TanStack Router para navegação interna.
- **Nunca** use `<a href="...">` para links internos; isso causa reload completo da página.
- Importe `Link` e `useNavigate` de `@tanstack/react-router`.

#### Exceções (quando `<a href>` é permitido)
- Links para **domínios externos** (ex: `https://example.com`).
- Links para **downloads de arquivos** (ex: PDFs, imagens).
- Links que precisam abrir em **nova aba** (`target="_blank"`) com `rel="noopener noreferrer"`.
- Arquivos estáticos servidos pelo servidor (raro em SPA com Vite).

#### Exemplos

```tsx
// ✅ Correto - navegação interna com Link
import { Link } from '@tanstack/react-router'

<Link to="/dashboard">Dashboard</Link>

// ✅ Correto - navegação programática com useNavigate
import { useNavigate } from '@tanstack/react-router'

const navigate = useNavigate()
navigate({ to: '/settings' })

// ❌ Incorreto - navegação interna com <a href>
<a href="/dashboard">Dashboard</a>

// ✅ Correto - link externo
<a href="https://google.com" target="_blank" rel="noopener noreferrer">Google</a>
```

### Sobre routeTree.gen.ts e tipos de rota
- O arquivo `src/routeTree.gen.ts` é automaticamente gerado pelo `@tanstack/router-plugin` com base nos arquivos em `src/routes/`.
- Não edite `routeTree.gen.ts` manualmente; ele é sobrescrito a cada `npm run dev`/build.
- A tipagem das rotas (`to` do `Link`, params e search params) vem do `Register` declarado em `src/router.tsx`.
- Após adicionar uma nova rota em `src/routes/`, aguarde a regeneração da árvore de rotas (ou reinicie o dev server) para que `Link` e `useNavigate` reconheçam a nova rota.

## Exemplo de Estrutura
```
src/
  routes/
    __root.tsx
    index.tsx
    duel.tsx
    about/
      route.tsx           # layout/entrada da rota (ex.: DialogProvider)
      index.tsx
      -components/
        AboutCard.tsx
      -hooks/
        useAboutData.ts
      -contexts/
        AboutContext.tsx
      -modals/
        AboutInfoModal.tsx
      -services/
        aboutApi.ts
  modals/
    WelcomeModal.tsx
  components/
    Header.tsx
    Footer.tsx
  hooks/
    useApi.ts
  contexts/
    GlobalProviders.tsx
  infra/
    api.ts
  routeTree.gen.ts         # gerado pelo @tanstack/router-plugin
  router.tsx               # criação do router
```

## Resumo de decisão
- Comece simples com arquivo único de rota.
- Evolua para pasta de feature quando a página crescer.
- Evite criar pasta por padrão sem necessidade real.