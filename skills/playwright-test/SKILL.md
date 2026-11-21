---
name: playwright-test
description: >-
  Runbook agnóstico para testes E2E, automação de navegador, inspeção visual e diagnóstico de performance/rede coordenando os servidores Playwright MCP e Chrome DevTools MCP. Ative ao testar fluxos de interface no navegador, auditar console/network, investigar bugs visuais ou medir performance web.
---

# Testes E2E e Diagnóstico Web com Browser MCP

Diretrizes universais para automação de navegador e debugging em qualquer aplicação web utilizando os servidores **Playwright MCP** (`playwright`) e **Chrome DevTools MCP** (`chrome-devtools`).

---

## 1. Roteamento entre Servidores MCP (Regra da Instância Única)

Os dois servidores iniciam e controlam **instâncias separadas de navegador**. Nunca misture ferramentas de `playwright` e `chrome-devtools` dentro do mesmo fluxo de navegação (isso abre duas janelas distintas e perde cookies, sessão autenticada e estado de página).

| Cenário da Tarefa | Servidor MCP Recomendado | Exemplos de Uso |
| :--- | :--- | :--- |
| **Testes E2E e Fluxos Funcionais** | **`playwright`** (`@playwright/mcp`) | Login, preenchimento de formulários, CRUD, fluxos multi-aba e isolamento de sessão (`isolatedContext`) |
| **Auditoria Técnica, Rede e Performance** | **`chrome-devtools`** (`chrome-devtools-mcp`) | Tracing de Core Web Vitals, `lighthouse_audit`, inspeção de CSS computado, heapsnapshot e debugging de rede/CORS |

- Escolha **um único servidor** para a tarefa atual.
- Se precisar rodar uma auditoria no `chrome-devtools` após um teste E2E no `playwright`, finalize e feche o fluxo anterior antes de iniciar a nova sessão.

---

## 2. Regras Estritas e Economia de Contexto

1. **Inspecione a Accessibility Tree antes de agir:**
   - Sempre execute `browser_snapshot` (Playwright) ou `take_snapshot` (Chrome DevTools) após navegar ou alterar o estado da tela para obter referências exatas (`target` / `uid`).
   - Nunca chute seletores CSS frágeis ou cegos quando o snapshot já fornece a referência estrutural do elemento.
2. **Snapshots estruturais acima de screenshots repetidos:**
   - Use snapshots de texto/acessibilidade como fonte primária de leitura e validação de DOM.
   - Reserve screenshots (`scale: "css"` no Playwright) apenas para conferir alinhamento visual, layout responsivo ou evidência final, evitando estourar tokens de imagem no contexto.
3. **Preenchimento em lote:**
   - Ao preencher múltiplos campos de um formulário, prefira `browser_fill_form` (Playwright) ou `fill_form` (Chrome DevTools) em vez de chamadas sequenciais campo a campo.

---

## 3. Checklist Universal de Validação E2E e Diagnóstico

1. **Pré-voo (Pre-flight):**
   - Antes de abrir o navegador, garanta que a URL alvo (ex: servidor de desenvolvimento local) está respondendo e acessível.
2. **Telemetria Pós-Ação Obrigatória:**
   - Após submeter formulários, trocar rotas ou disparar ações críticas, verifique sempre:
     - **Console do navegador** (`browser_console_messages` / `list_console_messages`): zero exceções uncaught ou erros de hidratação/runtime.
     - **Requisições de rede** (`browser_network_requests` / `list_network_requests`): ausência de respostas HTTP 4xx/5xx inesperadas, timeouts ou falhas de CORS.
3. **Isolamento de Sessões e Permissões:**
   - Para testar fluxos com múltiplos perfis ou usuários simultâneos no Playwright MCP, crie abas com `isolatedContext` em `browser_tabs` para evitar contaminação de cookies e `localStorage`.
4. **Higiene de Dados de Teste:**
   - Utilize prefixos identificáveis (ex: `[TESTE]`) para registros criados durante a verificação e remova ou reverta dados temporários ao concluir o fluxo sempre que aplicável.
