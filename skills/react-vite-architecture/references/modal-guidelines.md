# Diretrizes para Criação de Modais

## Alinhamento com Arquitetura
- Este documento define apenas regras para criação e uso de modais.
- Para decisões de estrutura por rota/feature, siga `docs/architecture-guidelines.md`.
- Para componentes em geral (nome, exportação e estilo), siga também `docs/component-guidelines.md`.

## Stack e Padrão do Projeto
- Utilize `react-dialogs` como base para modais.
- Registre cada modal no `DialogProvider` apropriado ao seu escopo (local ou global), conforme definido na arquitetura.
- Defina um ID estável para cada modal e exporte esse ID no próprio arquivo do modal.

## Regra de Escopo
- Se o modal é usado por apenas uma rota, mantenha no escopo local da feature.
- Se o modal é usado em mais de uma rota, promova para escopo global.
- Evite registrar modal local no provider global.

## Convenções de Implementação
- Defina e exporte uma constante de ID:
  - `export const USER_PROFILE_MODAL_ID = 'user-profile-modal'`
- Defina e exporte o tipo das props do modal quando houver payload:
  - `export type UserProfileModalProps = { userId: string }`
- Use `useDialog<T>()` com o mesmo tipo usado no `show(...)`.
- Sempre encapsule conteúdo no componente `Dialog` com o mesmo `id`.
- Siga o padrão de import de CSS Modules com alias `s`.

## Exemplo Recomendado
```tsx
import { Dialog, useDialog } from 'react-dialogs'

import s from './UserProfileModal.module.css'

export const USER_PROFILE_MODAL_ID = 'user-profile-modal'

export type UserProfileModalProps = {
  userId: string
}

export function UserProfileModal() {
  const { close, props } = useDialog<UserProfileModalProps>(USER_PROFILE_MODAL_ID)

  return (
    <Dialog id={USER_PROFILE_MODAL_ID}>
      <section className={s.container} aria-labelledby="user-profile-modal-title">
        <h2>Perfil do usuário</h2>
        <p>ID: {props?.userId}</p>

        <button onClick={() => close()} type="button">
          Fechar
        </button>
      </section>
    </Dialog>
  )
}
```

## Como Abrir e Fechar o Modal
- Em páginas/componentes consumidores, use `useDialog<ModalProps>(MODAL_ID)`.
- Chame `show(payload)` para abrir.
- Use `close()` dentro do modal para fechar.
- Evite acoplamento entre modal e página chamadora além do payload tipado.

## Estado e Responsabilidades
- Prefira estado local para abrir/fechar modal e para estados visuais internos.
- Não promova para estado global controles locais de modal.
- Se o modal depender de dados remotos:
  - Deixe carregamento/erro explícitos no próprio modal.
  - Use hooks já padronizados (`useApi` ou React Query) conforme o caso.

## Acessibilidade
- Todo modal deve ter título claro e descritivo.
- Garanta associação semântica com `aria-labelledby` quando aplicável.
- Botões de ação devem ter texto objetivo (ex.: `Cancelar`, `Confirmar`, `Fechar`).
- Evite conteúdo apenas visual sem alternativa textual.
- Verifique fluxo de teclado (foco inicial, navegação por Tab e fechamento).

## Estilos
- Use CSS Modules com escopo local por modal.
- Evite estilos globais para comportamento interno do modal.
- Mantenha dimensões e espaçamento responsivos (desktop e mobile).

## Checklist de PR para Modais
- [ ] Modal registrado no `DialogProvider` correto para o escopo (local ou global).
- [ ] ID constante, estável e sem colisão.
- [ ] Payload tipado com TypeScript (quando necessário).
- [ ] Abertura via `show(...)` e fechamento via `close()`.
- [ ] Estrutura acessível (título, labels, foco e teclado).
- [ ] Estilos isolados em `.module.css`.
- [ ] Fluxos de loading/erro tratados quando houver integração com API.
