# GitHub Pages com GitHub Actions — notas de utilização

Registo: `github-pages-actions-deploy` · Coleção: `web-development` · Verificado parcialmente em 2026-11-06

## O que é

É o fluxo oficial da GitHub para publicar um site no Pages a partir de um workflow, em vez de enviar
ficheiros gerados para um branch `gh-pages`. Assenta em três actions mantidas pela GitHub:

| Action | Versão observada | Papel |
|---|---|---|
| `actions/configure-pages` | v6 | Ativa o Pages e devolve metadados (incl. `base_path`). Com `static_site_generator: next` ajusta a configuração do Next.js no build. |
| `actions/upload-pages-artifact` | v5 | Empacota a pasta gerada (ex.: `out/`) num artefacto. |
| `actions/deploy-pages` | v5 | Publica o artefacto no ambiente `github-pages`. |

Ponto de partida: `actions/starter-workflows` → `pages/nextjs.yml`, também disponível no GitHub em
*Actions → New workflow → Pages → Next.js*.

## Quando usar

- O site é gerado por um build (Next.js com `output: 'export'`, Astro, Vite, MkDocs...).
- Hoje o deploy é manual: build, preparar a pasta e publicar noutro branch.
- Quer correr lint, testes ou Lighthouse antes de publicar, no mesmo workflow.

Não é necessário para sites só com HTML/CSS (ex.: `internal-portfolio-static`): aí a publicação por branch chega.

## Estrutura do workflow (Next.js estático)

1. **Job `build`**:
   - checkout;
   - setup de Node;
   - `configure-pages`;
   - cache de `.next/cache` (opcional);
   - instalação de dependências (`npm ci`);
   - `next build`;
   - `upload-pages-artifact` com `path: ./out`.
2. **Job `deploy`**: depende de `build`, usa o ambiente `github-pages` e corre `deploy-pages`.
3. **Permissões:** `contents: read`, `pages: write` e `id-token: write`.
4. **Concorrência:** grupo `pages`, sem cancelar deploys em curso.
5. **No repositório:** em *Settings → Pages*, mudar a origem para **GitHub Actions**.

## Cuidados

- **Versões:** o starter observado usa `upload-pages-artifact@v3` e `configure-pages@v5`, mas existem v5 e v6.
  Rever as versões ao copiar e fixá-las.
- **basePath:** em projetos que já calculam o basePath, há duas opções. Uma é usar `static_site_generator: next`
  e retirar a lógica própria. A outra é não o usar e passar `steps.<id>.outputs.base_path` ao build
  (ex.: como `BASE_PATH`). Ter as duas ao mesmo tempo cria duas fontes de verdade.
  - No `portfolio-v2`, o `next.config.js` lê `BASE_PATH`: a segunda opção encaixa sem alterar o código.
- **`.nojekyll`:** o starter não o cria, e `upload-pages-artifact` exclui ficheiros ocultos por omissão.
  Ainda não está confirmado se este fluxo dispensa o `.nojekyll`: testar a pasta `_next` no primeiro deploy.
- **Limites:** suporte oficial até 1 GB por site e timeout de deploy de 10 minutos.
- **Visibilidade:** tudo o que é publicado fica público, mesmo vindo de um repositório privado (sujeito ao plano).

## Alternativas

- `netlify`: deploy previews por pull request, fora do GitHub.
- Publicação manual por branch: sem CI, mais simples para sites sem build.

## Fontes

- Documentação: https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages
- Starter: https://github.com/actions/starter-workflows/blob/main/pages/nextjs.yml
- Actions: https://github.com/actions/configure-pages · https://github.com/actions/upload-pages-artifact · https://github.com/actions/deploy-pages
