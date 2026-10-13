# Diretrizes para Criação de Estados Globais

## Alinhamento com Arquitetura
- Este documento não define organização de pastas ou local de criação.
- Para decisões de estrutura e escopo por rota/feature, siga exclusivamente `docs/architecture-guidelines.md`.

## Stack Padrão para Estado Global
- Para estado global de cliente, prefira `zustand` como padrão do projeto.
- Evite criar novos estados globais com React Context para dados mutáveis de domínio.
- React Context deve ficar restrito a integrações específicas de bibliotecas (ex.: i18n, tema de lib) quando a API exigir provider.

## Quando Criar um Estado Global
- Crie um estado global apenas quando a informação precisar ser compartilhada por múltiplas áreas da aplicação.
- Prefira estado local quando o dado for usado por um único componente ou por uma árvore pequena.
- Prefira hooks especializados quando a lógica for reutilizável, mas o estado não precisar ser global.
- Não use store global para dados de servidor, cache ou controle de requisições. Para esses casos, mantenha a responsabilidade em soluções como `react-query`.

## Casos Indicados
- Idioma selecionado pelo usuário.
- Dados de autenticação ou sessão.
- Preferências globais de interface.
- Sinalizadores de fluxo compartilhados entre páginas ou layouts.

## Casos que Devem Ser Evitados
- Estado temporário de formulário.
- Controle visual isolado, como abrir e fechar um modal local.
- Dados usados em apenas uma página.
- Valores derivados que podem ser calculados localmente.

## Estrutura Esperada
- Crie o arquivo dentro de `src/contexts/` com sufixo `Provider`, como `ThemeProvider.tsx` ou `AuthProvider.tsx`.
- Mantenha store e actions no mesmo arquivo.
- Separe claramente a definição do store da definição das actions.
- O consumo deve ser feito diretamente pelo hook da store do Zustand (ex.: `useThemeStore(selector)`).
- O `Provider` é opcional com Zustand e deve existir apenas quando for necessário encapsular lógica global para toda a aplicação.

## Padrão de Implementação
- Defina um tipo explícito para o estado do domínio.
- Defina tipos explícitos para as funções de action separadas.
- Crie a store com `create` do Zustand contendo apenas o estado.
- Implemente actions como funções separadas (fora da store), exportando essas funções para uso na aplicação.
- Use seletores no hook da store para consumir apenas a API necessária.
- Evite criar `Provider` apenas para expor store; use `Provider` somente quando houver necessidade real de efeitos/composição global.
- Mantenha a regra de negócio fora dos componentes consumidores.
- Evite stores muito amplas com responsabilidades distintas. Se necessário, divida em múltiplos providers.

## Boas Práticas
- Inicialize a store com uma estrutura tipada e previsível.
- Evite armazenar valores derivados na store quando eles puderem ser calculados a partir do estado base.
- Reduza re-renderizações desnecessárias selecionando apenas fatias necessárias do estado (`useStore(selector)`).
- Quando houver efeitos colaterais, como persistência em `localStorage` ou sincronização com API, encapsule essa lógica em actions ou hooks auxiliares.
- Evite expor o objeto completo da store para componentes consumidores.

## Exemplo de Estrutura
```tsx
import { type PropsWithChildren } from 'react'
import { create } from 'zustand'

type Theme = 'light' | 'dark'

type ThemeState = {
  theme: Theme
}

type SetTheme = (theme: Theme) => void

export const useThemeStore = create<ThemeState>(() => ({
  theme: 'light',
}))

export const setTheme: SetTheme = (theme) => {
  useThemeStore.setState({ theme })
}

// opcional: use apenas se precisar encapsular logica global da aplicacao
export function ThemeProvider({ children }: PropsWithChildren) {
  return <>{children}</>
}

// consumo em componentes:
// const theme = useThemeStore((state) => state.theme)
// setTheme('dark')
```

## Integração com o Projeto
- Antes de criar uma nova store, verifique se o domínio já possui um provider/store existente que pode ser estendido sem misturar responsabilidades.