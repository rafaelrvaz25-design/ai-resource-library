# Relatório de testes — versão inicial (2026-11-06)

Ambiente: Python 3, `jsonschema` 4.26. Comando: `python -m unittest discover -s tests -v` → **18/18 OK**.
`python scripts/validate.py` → **0 erros, 1 aviso** (MkDocs sem commits há 382 dias — aviso legítimo de manutenção).

## Teste 1 — Web Development: landing page responsiva em WordPress

`python scripts/search.py "landing page responsiva wordpress"` → top 5:
WordPress Playground, WordPress, Create Block Theme, Tailwind CSS, Playwright.
A coleção `web-development` tem uma recomendação para este cenário (`wordpress`, `create-block-theme`,
`wordpress-playground`, `lighthouse`). **Passou.**
Limitação: o termo "responsiva" só coincide com recursos que têm a tag `responsive` (Tailwind, Playwright);
os recursos WordPress não a têm, porque a fonte não o afirma explicitamente.

## Teste 2 — UI/UX Design: design system em Figma

`"design system figma documentar"` → Figma MCP Server, Figma REST API, Figma, skills Figma (observadas),
Tokens Studio, Storybook. `"plugins figma design systems" --type plugin` → Tokens Studio em 1.º. **Passou.**
Limitação: o catálogo tem poucos plugins Figma (Tokens Studio, Stark) — prioridade de expansão.

## Teste 3 — AI & Automation: MCP para automatizar desenvolvimento

`"automatizar tarefas desenvolvimento github" --type mcp-server` → GitHub MCP Server em 1.º, todos os resultados
são `mcp-server`. O plugin descontinuado `automattic-wordpress-mcp` fica oculto por omissão e, com
`--include-deprecated`, aparece abaixo do substituto oficial. **Passou.**

## Teste 4 — Pesquisa transversal sem duplicação

10 recursos pertencem a mais de uma coleção (ex.: `storybook` em `ui-ux-design` e `research-documentation`;
`figma-mcp-server`, `context7`, `wcag-22`...). As coleções contêm apenas `id`, `role` e `rationale`
(verificado automaticamente); cada ID existe uma única vez no catálogo. **Passou.**

## Teste 5 — Segurança

- O esquema de recurso rejeita campos como `installed` (testado com um registo modificado).
- Nenhum registo contém campos de instalação/autorização; a pesquisa marca cada resultado como
  "catalogado: NÃO implica instalado, disponível nem autorizado".
- Existem recursos `verified` com `risk.level: high` (ex.: `supabase-mcp`), demonstrando que verificado ≠ seguro.
- Todos os servidores MCP declaram `executes_code: true`.
- `environments/claude-ai-rafael.json` regista o que foi observado (ex.: Supabase MCP instalado e disponível)
  mas com autorização `ask-every-time`; nenhum ambiente concede autorização genérica.
- O validador procura padrões de segredos (tokens GitHub, chaves sk-, AWS, JWT, chaves privadas). **Passou.**

## Teste 6 — Integridade

`validate.py` sem erros; um teste copia a biblioteca, injeta uma referência inexistente numa coleção e confirma
que o validador falha e identifica o ID. Todos os ficheiros do registo existem. **Passou.**

## Outras verificações

| Verificação | Resultado |
|---|---|
| `new_resource.py` com ID existente | Recusado (exit 1) |
| `new_resource.py` com URL oficial existente | Recusado (exit 1) |
| `new_resource.py` com nome semelhante | Aviso com o recurso parecido |
| Workflow YAML | Sintaxe válida; jobs `validate` e `links` |
| Pacotes npm (14) | Existem no registry; licenças coincidem com o catálogo |
| Repositórios GitHub (50) | Existem (`git ls-remote`); licenças lidas do ficheiro LICENSE |
| `check_links.py` | 163 URLs: 101 ok, 0 partidos, 62 inconclusivos |

Os 62 inconclusivos são páginas `github.com` que o ambiente desta sessão bloqueia (HTTP 403); os mesmos
repositórios foram confirmados por `git ls-remote`. No GitHub Actions o script usa a API do GitHub com o token
automático da execução. Primeira execução do workflow no GitHub Actions (push inicial, 2026-11-06): **success** (validação, 18 testes e pesquisa de fumo).

---

# Relatório de testes — v1.1: integração entre projetos (2026-11-06)

Comando: `python -m unittest discover -s tests -v` → **42/42 OK**
(18 do catálogo em `test_library.py`, sem alterações, e 24 novos em `test_integration.py`).
`python scripts/validate.py` → 0 erros, 1 aviso (MkDocs inativo, já conhecido).

## Cenários pedidos

| Cenário | Teste(s) | Resultado |
|---|---|---|
| Biblioteca por variável de ambiente | `test_found_by_environment_variable` (com prioridade sobre `~`) | OK |
| Caminho local convencional | `test_found_in_conventional_local_path` | OK |
| Caminho alternativo | `test_found_in_alternative_known_path`, `test_found_via_extra_paths_variable`, `test_found_in_project_directories` | OK |
| Diretório existente mas inválido | `test_existing_but_invalid_directory_is_skipped`, `test_invalid_env_path_falls_through`, `test_registry_listing_missing_catalog_file_is_invalid` | OK |
| Indisponível localmente | `test_unavailable_locally_without_remote` | OK |
| Fallback remoto | `test_remote_fallback_clones_to_temp_and_cleans_up` (repositório Git local via `file://`), `test_local_copy_prevents_clone` | OK |
| Falha de autenticação | `test_authentication_failure_is_reported_clearly` (git falso; confirma que o token não aparece na saída e que não tenta clonar), `test_terminal_prompt_disabled_counts_as_auth_failure` | OK |
| Contexto de projeto JavaScript | `test_javascript_project` (deteção de stack, restrições, lacunas, recursos já usados; não lê `.env` nem conteúdo de scripts) | OK |
| Projeto sem `package.json` | `test_project_without_package_json` (Python), `test_wordpress_theme_without_package_json` (não expõe `wp-config.php`), `test_static_site_only_html` | OK |

Extra:
- erros de rede;
- recusa de credenciais no URL;
- `cleanup` só apaga pastas temporárias próprias;
- push desativado na cópia temporária;
- o código do projeto nunca é executado;
- limite de profundidade.

## Verificação real (fora dos testes unitários)

| Verificação | Resultado |
|---|---|
| Skill a partir do `portfolio-v2` | Encontrou `/home/claude/ai-resource-library` (caminho conhecido) sem clonar |
| Sem caminhos conhecidos | Encontrou a biblioteca pelos antecessores do projeto |
| Fallback remoto real (GitHub, sessão autenticada) | Clone temporário do commit atual, validado e apagado; nada ficou em `/tmp` |
| Repositório inexistente | `auth_failed` com mensagem clara (o GitHub não distingue "não existe" de "sem acesso" em repositórios privados) |
| `project_context.py` no `portfolio-v2` | Stack completa, 4 restrições, 4 lacunas; 1.ª pesquisa sugerida "github pages nextjs deploy" |
| `project_context.py` no `vazbarber` (sem `package.json`) | Supabase, GitHub Actions, HTML/TypeScript/SQL |
| Novo recurso `github-pages-actions-deploy` | 1.º lugar em "github pages nextjs deploy", "github actions deploy" e "publicar next.js github pages" |
