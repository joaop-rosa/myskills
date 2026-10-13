---
name: playwright-test
description: Runbook e procedimentos para teste E2E do Praetor CRM utilizando Playwright e o servidor Playwright MCP.
---

# Guia de Testes E2E com Playwright & MCP — Praetor CRM

Use este skill ao realizar testes de ponta a ponta (E2E), testes de interface e validações de fluxo na aplicação Praetor CRM.

---

## 1. Contexto do Ambiente Local

- **URL Base:** `http://localhost:3000`
- **Credenciais de Teste (Admin):**
  - Usuário: `admin`
  - Senha: `senha123`
- **Cookies & Sessão:** Autenticação via cookie HTTP-only `token` gerado em `/api/auth/login`.

---

## 2. Fluxos Principais de Teste

### 2.1 Autenticação (`/login`)
1. Navegue para `http://localhost:3000/login`.
2. Preencha o input `#username` com `admin` e `#password` com `senha123`.
3. Clique no botão de submissão do formulário.
4. Verifique o redirecionamento automático para `/leads` ou `/dashboard`.

### 2.2 Gestão de Leads (`/leads`)
1. Navegue para `http://localhost:3000/leads`.
2. Verifique se as colunas do Kanban carregam (`Novo`, `Primeiro Contato`, `Reunião Agendada`, `Contrato Ganho`, etc.).
3. Clique em um card para abrir o `LeadDetailsSheet`.
4. Teste a alteração de status condicional:
   - `MEETING_SCHEDULED`: requer data e hora da reunião.
   - `WON`: exibe campos de honorários, parcelas e vencimento.
   - `LOST`: exibe motivos rápidos de perda.

### 2.3 Módulo Financeiro (`/financial`)
1. Navegue para `http://localhost:3000/financial`.
2. Verifique o carregamento dos KPI cards superiores (Receitas, Despesas, Saldo Líquido).
3. Teste a navegação pelas abas:
   - **Recebíveis:** Tabela e cards expansíveis, botão de novo contrato.
   - **Custos:** Tabela de custos fixos/variáveis, botão de custos em atraso anterior.
   - **Inadimplência:** Visão agregada por cliente/contrato com alerta de contratos encerrados.
4. Teste o acionamento dos modais:
   - Modal de pagamento (`PaymentModal`): opções FIFO e histórico.
   - Modal de custos anteriores (`PriorOverdueExpensesModal`).

---

## 3. Boas Práticas durante a Execução
- Capture screenshots após passos críticos para validação visual.
- Verifique o console do navegador em busca de erros 500 ou runtime uncaught exceptions.
- Limpe dados criados durante os testes quando aplicável ou utilize identificadores com prefixo `[TESTE]`.
