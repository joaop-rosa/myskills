---
name: lingui-translate
description: "Identifica e preenche traduções faltantes (entradas com msgstr vazio) em arquivos de catálogo .po de projetos que utilizam LinguiJS, preservando placeholders (<0>, {name}, %s) e sincronizando locales. Ative quando o usuário pedir 'preencher traduções', 'traduzir .po', 'atualizar catálogo lingui', 'traduzir mensagens faltantes' ou 'translate'."
---

# Tradução e Sincronização de Catálogos LinguiJS (.po)

Esta skill define o fluxo padronizado para identificar e preencher traduções ausentes em projetos internacionalizados com **LinguiJS** que utilizam catálogos de mensagens em formato `.po`.

> [!IMPORTANT]
> **Diretrizes Estritas:**
> 1. **Idioma Fonte**: A fonte canônica das mensagens padrão é geralmente o inglês (`en`) ou o locale configurado como fonte no projeto.
> 2. **Preservação de Placeholders**: Mantenha **exatamente** todos os placeholders, interpolações e tags como aparecem no `msgid` (ex.: `<0>`, `</0>`, `{name}`, `%s`, `{count, plural, ...}`).
> 3. **Modificação Estrita de `msgstr`**: Edite **apenas** as linhas `msgstr ""` que estiverem vazias. **NUNCA** altere o `msgid`, `msgctxt`, cabeçalhos do arquivo ou a ordem das entradas.
> 4. **Sem Alteração Estrutural**: Não adicione, remova ou reordene entradas no arquivo `.po`. Preserve o encoding (UTF-8) e as quebras de linha existentes.

---

## Fluxo de Execução

### Etapa 1 — Localizar Configurações de Locale
1. Verifique a configuração do LinguiJS no projeto:
   - Inspecione `lingui.config.ts`, `lingui.config.js` ou `package.json` para identificar o diretório de catálogos e os locales suportados.
   - Verifique o arquivo de definição de locales (ex.: `src/locales/locales.ts`, `src/locales/` ou `locales/`).
2. Identifique os arquivos `.po` existentes (ex: `en.po`, `pt-BR.po`, `es.po`, etc.).

### Etapa 2 — Identificar Entradas Faltantes
1. Inspecione cada arquivo `.po` do idioma de destino comparando com o arquivo fonte (ex.: `en.po`).
2. Localize todas as ocorrências onde o valor de tradução está vazio:
   ```po
   msgid "Welcome back, {userName}!"
   msgstr ""
   ```

### Etapa 3 — Tradução Contextual
Para cada `msgstr ""` vazio:
1. Analise o contexto da mensagem a partir do `msgid` e de comentários (`#.`) presentes no catálogo.
2. Gere uma tradução natural, fluida e precisa no idioma de destino.
3. Garanta que todas as variáveis e marcações de formatação sejam mantidas intactas:
   ```po
   # Exemplo Correto:
   msgid "Hello <0>{name}</0>"
   msgstr "Olá <0>{name}</0>"
   ```

### Etapa 4 — Compilação e Validação
1. Após atualizar os arquivos `.po`, verifique se o projeto possui script de compilação do Lingui no `package.json`:
   - Se existir `npm run lingui:extract:compile` ou `npm run lingui:compile`, execute para compilar os catálogos `.js`.
2. Valide o build ou verificação de tipos (`npm run build` ou `npm run typecheck`) caso aplicável.

---

## Relatório de Conclusão

Apresente um resumo claro das alterações:
- **Arquivos atualizados**: lista dos arquivos `.po` modificados.
- **Quantidade de termos traduzidos** por idioma.
- **Status da compilação**: se os catálogos foram compilados com sucesso.
