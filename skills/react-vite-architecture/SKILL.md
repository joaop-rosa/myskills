---
name: react-vite-architecture
description: "Aplica e orquestra as diretrizes canônicas de arquitetura para projetos React + Vite (TanStack Router, Zustand, CSS Modules sem className externa e variáveis de cor reais, react-dialogs, LinguiJS macro e useApi/React Query). Ative ao criar ou refatorar rotas, páginas, componentes, modais, integrações de API, stores de estado global, internacionalização ou quando o usuário pedir 'siga as regras de docs', 'siga as diretrizes de arquitetura' ou 'execute conforme a arquitetura'."
---

# Diretrizes de Arquitetura React + Vite

Esta skill define as regras arquiteturais, convenções de código e padrões de engenharia para projetos frontend baseados em **React + Vite** com **TanStack Router**, **Zustand**, **LinguiJS**, **CSS Modules** e **React Query / useApi**.

---

## 1. Princípios Transversais Fundamentais

1. **Escopo Local Primeiro**: Mantenha componentes, hooks, modais e serviços na pasta da própria rota/feature (`routes/nome-da-rota/`). Promova para pastas globais (`src/components/`, `src/modals/`, `src/hooks/`) apenas quando houver reuso comprovado entre múltiplas páginas.
2. **Navegação Interna**: Sempre utilize `Link` ou `useNavigate` de `@tanstack/react-router`. NUNCA use `<a href>` para rotas internas da aplicação (apenas para links externos ou downloads).
3. **Componentes sem Prop `className` Externa**: Componentes não devem aceitar `className` ou `style` de fora. Variações devem ser controladas internamente por props explícitas (`theme`, `size`).
4. **Cores Reais em Variáveis CSS**: Use sempre nomes de cores reais em variáveis globais (`--blue`, `--gray-100`, `--black-05`). Proibido usar nomes funcionais como `--primary`, `--secondary` ou `--text-primary`.
5. **Estado Global com Zustand**: Use Zustand para estado de cliente. Separe a store das actions (actions são funções externas no mesmo arquivo). Não use React Context para estados mutáveis.
6. **i18n com LinguiJS Macro**: Sempre use `useLingui()` de `@lingui/react/macro` obtendo `{ t }` e template literals (ex.: `{t\`Texto\`}`). NUNCA use o componente `<Trans>`.
7. **Modais Padronizados**: Use `react-dialogs` com `DialogProvider` escopado, exportando sempre uma constante `NOME_MODAL_ID` e o tipo `NomeModalProps`.
8. **Integração HTTP via `useApi`**: Todas as requisições GET/POST/PUT/DELETE devem usar `useQueryApi` ou `useMutationApi` com `logName` e mensagens de erro tipadas por código HTTP. Nunca use `fetch` ou `axios` diretamente.

---

## 2. Fontes de Referência das Diretrizes

Para aprofundar em cada tópico, consulte as referências:
- Se o repositório atual possuir a pasta `docs/` com diretrizes locais, priorize as regras específicas do projeto.
- Caso contrário, utilize a documentação canônica embutida nesta skill:
  - [Arquitetura de Rotas e Features](file:///Users/joaopaulodarosa/.gemini/config/skills/react-vite-architecture/references/architecture-guidelines.md)
  - [Criação de Componentes e CSS Modules](file:///Users/joaopaulodarosa/.gemini/config/skills/react-vite-architecture/references/component-guidelines.md)
  - [Estado Global com Zustand](file:///Users/joaopaulodarosa/.gemini/config/skills/react-vite-architecture/references/global-state-guidelines.md)
  - [Internacionalização com LinguiJS](file:///Users/joaopaulodarosa/.gemini/config/skills/react-vite-architecture/references/i18n-guidelines.md)
  - [Criação e Registro de Modais](file:///Users/joaopaulodarosa/.gemini/config/skills/react-vite-architecture/references/modal-guidelines.md)
  - [Integração de APIs com useApi](file:///Users/joaopaulodarosa/.gemini/config/skills/react-vite-architecture/references/useApi-guidelines.md)

---

## 3. Mapeamento Tema -> Diretriz

Ao receber uma demanda, classifique os temas envolvidos para aplicar as regras correspondentes:

- **Rotas, pastas, navegação, feature folders**:
  Consulte [architecture-guidelines.md](file:///Users/joaopaulodarosa/.gemini/config/skills/react-vite-architecture/references/architecture-guidelines.md).
- **Componentes, props, CSS Modules, cores, fontes, responsividade**:
  Consulte [component-guidelines.md](file:///Users/joaopaulodarosa/.gemini/config/skills/react-vite-architecture/references/component-guidelines.md).
- **Zustand, providers, stores, autenticação/tema**:
  Consulte [global-state-guidelines.md](file:///Users/joaopaulodarosa/.gemini/config/skills/react-vite-architecture/references/global-state-guidelines.md).
- **Traduções, textos em tela, mensagens**:
  Consulte [i18n-guidelines.md](file:///Users/joaopaulodarosa/.gemini/config/skills/react-vite-architecture/references/i18n-guidelines.md).
- **Modais, diálogos, confirmações, `react-dialogs`**:
  Consulte [modal-guidelines.md](file:///Users/joaopaulodarosa/.gemini/config/skills/react-vite-architecture/references/modal-guidelines.md).
- **Chamadas de backend, queries, mutations, cache**:
  Consulte [useApi-guidelines.md](file:///Users/joaopaulodarosa/.gemini/config/skills/react-vite-architecture/references/useApi-guidelines.md).

---

## 4. Regras de Precedência

1. `architecture-guidelines.md` é a **regra transversal** e aplica-se sempre.
2. Se a tarefa envolver UI reutilizável, aplique também `component-guidelines.md`.
3. Se envolver modal, aplique `modal-guidelines.md` e a regra de escopo de rotas da arquitetura.
4. Se envolver integração HTTP, aplique `useApi-guidelines.md`.
5. Se envolver estado compartilhado, aplique `global-state-guidelines.md`.
6. Se envolver textos na interface, aplique `i18n-guidelines.md`.

---

## 5. Modo de Execução (Obrigatório)

Após identificar os guias aplicáveis, **NÃO pare apenas em planejamento ou checklist**:

1. **Implementação**: Escreva/edite diretamente os arquivos necessários no projeto seguindo os padrões.
2. **Conformidade**: Garanta que as convenções (mobile-first, variáveis de cor, escopo local, sem `className`, imports de CSS via `s`) foram respeitadas.
3. **Extração de i18n**: Se a tarefa adicionou ou alterou textos traduzíveis e o script existir, execute:
   ```bash
   npm run lingui:extract:compile
   ```
4. **Validação**: Execute os comandos pertinentes no projeto (`npm run build`, `npm run lint` ou `npm run typecheck`). Corrija eventuais erros de tipagem ou formatação decorrentes da alteração.

---

## 6. Formato do Relatório de Conclusão

Após finalizar a implementação, forneça o resumo estruturado:

1. **Guias Aplicados**: Lista dos tópicos/guias consultados.
2. **Implementação Realizada**: Arquivos criados ou modificados e resumo das alterações.
3. **Validações Executadas**: Comandos executados e status de sucesso.
4. **Pendências / Próximos Passos (se houver)**: Itens que dependem de definições de produto ou backend.
