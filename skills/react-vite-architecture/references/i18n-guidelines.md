# i18n Guidelines

## Objetivo

Estabelecer práticas recomendadas para internacionalização (i18n) no projeto, garantindo que a aplicação seja facilmente adaptável para múltiplos idiomas e culturas.

## 1. Organização dos Arquivos de Tradução
- Mantenha todos os arquivos de tradução em `src/locales/`.
- Use um arquivo `.po` para cada idioma (ex: `en.po`, `pt-BR.po`).
- Utilize arquivos `.js` para exportar os recursos de tradução processados.
- Centralize a configuração de idiomas em `src/locales/locales.ts`.

## 2. Uso de Framework
- Utilize a biblioteca [LinguiJS](https://lingui.dev/) para gerenciamento de traduções.
- Configure o provider de i18n em `src/contexts/I18NProvider.tsx`.
- **Sempre utilize a função `t` via hook `useLingui()` para marcar textos traduzíveis**.
- Neste projeto, a importação padrão é `useLingui` de `@lingui/react/macro`.
- ⚠️ **Evite usar o componente `<Trans>` - use a função `t` do macro ao invés disso**.

## 3. Boas Práticas de Tradução
- Nunca deixe textos estáticos hardcoded nos componentes. Sempre utilize as funções de tradução.
- Prefira chaves descritivas e contextuais para as mensagens.
- Evite interpolar HTML diretamente nas mensagens. Use placeholders e variáveis.
- Sempre forneça contexto para tradutores quando necessário.

## 4. ⚠️ Regra Essencial: Use useLingui (t) em vez de <Trans>

**Sempre utilize o hook `useLingui` importado de `@lingui/react/macro` e obtenha `t` com `const { t } = useLingui()`. Nunca use o componente `<Trans>`.**

### Por que?

1. **Consistência**: Manter um padrão único facilita manutenção e compreensão do código
2. **Performance**: Macros são compiladas em tempo de build, melhor performance que componentes wrapper
3. **Legibilidade**: Código mais limpo e intuitivo com template literals
4. **Type-Safety**: Melhor suporte a tipos e autocomplete
5. **Extração Automática**: Facilita a extração de strings para tradução

### Exemplos

#### ❌ Evite - Componente <Trans>
```typescript
import { Trans } from '@lingui/react'

function MyComponent() {
  return (
    <div>
      <Trans>Bem-vindo ao meu app</Trans>
    </div>
  )
}
```

#### ✅ Recomendado - Hook useLingui do @lingui/react/macro
```typescript
import { useLingui } from '@lingui/react/macro'

function MyComponent() {
  const { t } = useLingui()

  return (
    <div>
      {t`Bem-vindo ao meu app`}
    </div>
  )
}
```

### Com Variáveis

#### ❌ Evite
```typescript
<Trans>
  Olá, <strong>{userName}</strong>!
</Trans>
```

#### ✅ Recomendado
```typescript
import { useLingui } from '@lingui/react/macro'

const { t } = useLingui()

const mensagem = t`Olá, ${userName}!`
```

## 6. Adição de Novos Textos
- Para adicionar um novo texto:
  1. Importe `useLingui` de `@lingui/react/macro` no código.
  2. Obtenha `t` com `const { t } = useLingui()`.
  3. Rode o comando de extração do Lingui para atualizar os arquivos `.po`.
  4. Adicione as traduções nos arquivos `.po` correspondentes.

## 10. Fluxo Operacional do Projeto
- Após qualquer ajuste de mensagens, rode `npm run lingui:extract:compile`.
- Revise o `src/locales/[lang].po` após extração, pois mensagens podem ficar com `msgstr` vazio.
- Só finalize a tarefa após recompilar catálogos e validar o build de tipos.

## 7. Atualização e Sincronização
- Sempre rode o comando de extração após adicionar ou alterar textos traduzíveis.
- Mantenha os arquivos `.po` sincronizados e revisados.
- Remova mensagens obsoletas periodicamente.

## 8. Testes
- Teste a aplicação em todos os idiomas suportados.
- Verifique se não há textos faltando ou placeholders não substituídos.

## 9. Referências
- [Documentação LinguiJS](https://lingui.dev/)
- [Guia de internacionalização da W3C](https://www.w3.org/International/)

---
