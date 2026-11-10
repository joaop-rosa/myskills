---
name: mr-template
description: >-
  Gera e preenche descrições de Merge Request (MR) e Pull Request (PR) no template padrão do projeto, escrevendo de forma humana, direta e focada em validação de QA em ambiente de testes. Ative sempre que o usuário pedir para 'criar um template', 'preencher o template', 'gerar descrição do MR', 'gerar descrição do PR', 'criar MR', 'criar PR', 'template de MR' ou 'template'.
---

# MR / PR Template — Gerador de Descrição de Merge Request

Esta skill padroniza a criação e o preenchimento de descrições de Merge Request (GitLab) e Pull Request (GitHub), garantindo texto direto, escrita humana (sem vícios de IA) e instruções de teste voltadas para QA em ambiente de testes.

---

## 1. Visão Geral e Casos de Uso

Use esta skill sempre que o usuário pedir para:
- Criar ou preencher o template de MR/PR da branch atual.
- Preencher um template colado no prompt com base nas alterações feitas.
- Gerar a descrição de um Merge Request ou Pull Request.

---

## 2. Regras Estritas e Proibições (Diretrizes Críticas)

1. **Escrita Humana e Direta (Regras do `humanizer`):**
   - Vá direto ao ponto, com tom natural de pessoa desenvolvedora explicando a mudança para o time.
   - **Proibido usar vícios de escrita de IA:**
     - Sem estruturas *"não apenas X, mas Y"* (*not X, but Y*).
     - Sem travessões (`—` ou `–`) como conectores de frases.
     - Sem adjetivos ou verbos inflados (*"crucial"*, *"robusto"*, *"fundamental"*, *"aprimora significativamente"*, *"garantindo uma experiência perfeita"*).
     - Sem rótulos em negrito decorativos no início de cada item da lista (prefira `- Migração das chamadas...` em vez de `- **Migração:** Realizada a migração...`).
     - Sem frases dramáticas de efeito no final das seções.

2. **Foco em QA em Ambiente de Testes (`## Como testar`):**
   - Considere sempre que **o QA irá testar em um ambiente de testes** (homologação/staging/test build) e **não irá rodar o projeto localmente**.
   - Descreva passos práticos na interface do sistema/aplicativo e o comportamento esperado (incluindo fluxo principal, cenários de erro e regressão).
   - **NUNCA** coloque comandos de terminal (`git checkout`, `npm run`, `expo start`) na seção `Como testar`, a menos que o usuário peça explicitamente um teste técnico local.

3. **Checklist Sempre Preenchido (`[x]`):**
   - Todos os itens da seção `## Checklist` devem ser entregues já marcados com `[x]`.

4. **Extração Automática do Ticket/Issue (`## Links relacionados`):**
   - Extraia o número da issue/task diretamente do nome da branch atual (ex: `feat/request-improvements#1330` → `- Closes #1330`). Caso a branch não possua número identificável, mantenha `- Closes #`.

---

## 3. Passo a Passo Procedural (Runbook)

### Passo 1 — Coletar contexto do Git
Execute no repositório do projeto atual:
```bash
git branch --show-current
git log -n 3 --oneline
git status -s
```
E inspecione as alterações da branch (no último commit ou no diff em relação à branch base) para entender exatamente o que foi modificado.

### Passo 2 — Selecionar a estrutura do Template
Se o usuário não colar um template específico na mensagem, utilize exatamente a estrutura padrão abaixo:

```markdown
## O que foi feito

<!-- Bullet points diretos explicando as mudanças realizadas -->

## Motivação

<!-- 1 parágrafo curto e direto explicando qual problema existia e por que a mudança foi feita -->

## Tipo de mudança

- [ ] Bug fix
- [ ] Nova funcionalidade
- [ ] Refatoração
- [ ] Melhoria de performance
- [ ] Atualização de dependência
- [ ] Outro: <!-- descrever -->

## Como testar

1.
2.
3.

## Checklist

- [x] Li toda a descrição da task
- [x] Validei regras de negócio
- [x] Testei o fluxo principal
- [x] Testei cenários de erro
- [x] Atualizei a task com toda as regras 

## Screenshots / evidências

<!-- Se aplicável, adicione prints ou logs relevantes -->

## Links relacionados

- Closes #<id-da-issue>
```

### Passo 3 — Redigir e Revisar contra Vícios de IA
1. Preencha `## O que foi feito` com bullets objetivos citando o que mudou (e os arquivos principais quando útil para os revisores).
2. Preencha `## Motivação` explicando de forma simples o problema real que acontecia e o motivo da alteração.
3. Marque `[x]` nos tipos de mudança aplicáveis em `## Tipo de mudança`.
4. Escreva o `## Como testar` passo a passo pensando no QA usando o app/sistema no ambiente de testes.
5. Marque todos os itens do `## Checklist` com `[x]`.
6. Retorne o resultado dentro de um bloco de código ```` ```markdown ```` pronto para copiar e colar.
