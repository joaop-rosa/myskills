---
name: wordpress-update
description: Procedimento passo a passo para atualizar os arquivos do core do WordPress no repositório site-2021 a partir de uma pasta wordpress/ fornecida na raiz.
---

# Atualização do WordPress Core

Utilize esta skill sempre que for solicitada a atualização do core do WordPress a partir de uma pasta `wordpress/` disponibilizada na raiz do projeto site-2021.

## 1. Diretrizes de Preservação
Ao atualizar os arquivos em `public/`, os seguintes arquivos e pastas pertencem ao projeto e **NUNCA** devem ser modificados, excluídos ou sobrescritos:
- `public/wp-config/` e `public/wp-config.php`
- `public/robots.txt` e `public/manutencao/`
- `public/.gitignore`
- `public/wp-content/themes/cwi-theme` (não adicionar temas padrão `twenty*`)
- `public/wp-content/plugins/` (não adicionar plugins padrão `akismet` ou `hello.php`)
- `public/wp-content/uploads/` e `public/wp-content/object-cache.php`

## 2. Execução da Atualização

```bash
# 1. Substituir wp-admin completamente (evita arquivos órfãos)
rm -rf public/wp-admin && cp -r wordpress/wp-admin public/wp-admin

# 2. Substituir wp-includes completamente (evita arquivos órfãos)
rm -rf public/wp-includes && cp -r wordpress/wp-includes public/wp-includes

# 3. Atualizar arquivos raiz do WordPress
for f in index.php license.txt readme.html wp-activate.php wp-blog-header.php wp-comments-post.php wp-cron.php wp-links-opml.php wp-load.php wp-login.php wp-mail.php wp-settings.php wp-signup.php wp-trackback.php xmlrpc.php; do
  if [ -f "wordpress/$f" ]; then
    cp "wordpress/$f" "public/$f"
  fi
done

# 4. Atualizar traduções de idiomas
rm -rf public/wp-content/languages && cp -r wordpress/wp-content/languages public/wp-content/languages

# 5. Remover pasta temporária
rm -rf wordpress
```

## 3. Verificações Imediatas
1. Confirmar versão atualizada:
   ```bash
   grep "wp_version =" public/wp-includes/version.php
   ```
2. Garantir que temas e plugins proprietários não sofreram alterações indesejadas:
   ```bash
   git status -s
   ```
