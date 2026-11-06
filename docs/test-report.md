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
