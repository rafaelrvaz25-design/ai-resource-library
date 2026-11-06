# AI Resource Library

Biblioteca universal e privada de recursos técnicos — ferramentas, plugins, repositórios, servidores MCP, skills,
frameworks, APIs e standards — para ser consultada por agentes de IA (Claude primeiro, mas também Codex, Cursor,
ChatGPT e outros) e por mim, ao escolher recursos para novos projetos.

Não é uma lista de links: cada recurso tem metadados verificados, estado de confiança, risco, limitações e
relações; as coleções dão recomendações por cenário; há pesquisa local, validação automática e regras claras
para agentes. **A biblioteca informa — não instala, não executa e não autoriza nada.**

## Objetivos

1. Centralizar recursos relevantes num único sítio versionado.
2. Pesquisar por nome, tipo, categoria, tag, tecnologia, plataforma ou caso de uso.
3. Escolher o recurso certo para cada projeto, comparando alternativas e limitações.
4. Reutilizar entre projetos e entre agentes, sem copiar metadados.
5. Manter tudo atualizável e rastreável pelo Git.

## Estrutura

```
ai-resource-library/
├── AGENTS.md                 Regras universais para agentes (referência principal)
├── CLAUDE.md                 Notas para Claude (importa AGENTS.md)
├── catalog/
│   ├── _registry.json        Tipos de recurso e categorias permitidas
│   ├── tools.json  plugins.json  repositories.json  mcp-servers.json
│   ├── skills.json  frameworks.json  apis.json  standards.json
├── collections/              web-development · ui-ux-design · ai-automation · research-documentation
├── environments/             Observações datadas do que está instalado/disponível num ambiente
├── resources/                Documentação própria opcional (ex.: wordpress.md, github-mcp-server.md)
├── schemas/                  resource · collection · environment (JSON Schema 2020-12)
├── scripts/                  search.py · validate.py · check_links.py · new_resource.py · library.py
├── skills/ai-resource-library/  Skill de consulta: SKILL.md + scripts/locate_library.py e project_context.py
├── tests/                    Testes do catálogo (test_library.py) e da integração (test_integration.py)
├── docs/                     architecture.md · contributing.md · integrations.md · test-report.md
└── .github/workflows/validate.yml
```

Decisões e diferenças face à estrutura inicial: [docs/architecture.md](docs/architecture.md).

## Conteúdo (2026-11-06)

**79 recursos** · 42 `verified` · 34 `partially_verified` · 2 `unverified` · 1 `deprecated` · 5 internos

| Tipo | N.º | Exemplos |
|---|---|---|
| Tools | 24 | Figma, WordPress, Playwright, Lighthouse, axe-core, Supabase, deploy oficial do GitHub Pages |
| Frameworks | 13 | Next.js, React, GSAP, Motion, Tailwind CSS, shadcn/ui, Style Dictionary |
| MCP Servers | 13 | GitHub, Figma, Playwright, Chrome DevTools, Supabase, WordPress MCP Adapter |
| Skills | 7 | frontend-design, webapp-testing, mcp-builder, ai-resource-library |
| Plugins | 6 | Tokens Studio, Stark, Create Block Theme, Query Monitor |
| Repositories | 6 | anthropics/skills, modelcontextprotocol/servers, 3 projetos próprios |
| APIs | 5 | GitHub REST, Figma REST, WordPress REST, Claude API, Brevo |
| Standards | 5 | MCP, AGENTS.md, Agent Skills, WCAG 2.2, Design Tokens (DTCG) |

### Coleções

| Coleção | Recursos | Foco |
|---|---|---|
| `web-development` | 29 | WordPress, React/Next.js, performance, acessibilidade, testes, deployment |
| `ui-ux-design` | 14 | Figma, design systems, tokens, handoff, acessibilidade no design |
| `ai-automation` | 27 | Servidores MCP, skills, agentes, automação GitHub |
| `research-documentation` | 13 | Fontes, documentação técnica, conversão, links |

Um recurso pode estar em várias coleções (10 estão); as coleções guardam só IDs, papel e justificação.

## Pesquisar

```bash
python scripts/search.py "landing page wordpress"
python scripts/search.py "design system figma" --collection ui-ux-design
python scripts/search.py github automation --type mcp-server
python scripts/search.py acessibilidade --min-verification verified
python scripts/search.py --collection web-development        # papéis + recomendações por cenário
python scripts/search.py --show figma-mcp-server             # registo completo
python scripts/search.py --list-collections
python scripts/search.py --stats
python scripts/search.py "react componentes" --json          # para agentes
```

Cada resultado mostra: descrição, motivo da relevância (campos coincidentes), categorias, compatibilidade,
verificação/manutenção, licença/preço, risco, limitações, coleções, estado observado no ambiente e link.

A pesquisa é **textual** (com sinónimos PT→EN), não semântica: perguntas em linguagem natural são
decompostas em palavras-chave pelo agente. Não precisa de dependências.

## Adicionar e atualizar recursos

```bash
python scripts/new_resource.py --type tool --id exemplo --name "Exemplo" --url https://exemplo.org --write
# editar catalog/tools.json, depois:
python scripts/validate.py
```

Regras completas em [docs/contributing.md](docs/contributing.md) e [AGENTS.md](AGENTS.md) §7–9.

## Validar

```bash
pip install -r requirements.txt          # jsonschema
python scripts/validate.py               # esquemas, IDs, referências, duplicados, segredos, manutenção
python -m unittest discover -s tests -v  # testes do catálogo e da integração
python scripts/check_links.py --report link-report.md
```

O workflow `.github/workflows/validate.yml` corre validação e testes em cada push/PR e verifica links
semanalmente (relatório no resumo da execução, sem alterar ficheiros).

## Confiança, risco e permissões

- `verification.status` mede a confiança nos **metadados** (`verified` ≠ seguro).
- `maintenance.status` mede a atividade do projeto.
- `risk` indica se executa código e se precisa de credenciais.
- **Instalado / disponível / autorizado** nunca estão no catálogo: dependem do ambiente
  (`environments/` guarda observações datadas; autorização por omissão `ask-every-time`).

## Integrar com Claude

- **Claude Code**: abrir o repositório (lê `CLAUDE.md`), ou referenciar a cópia local no `CLAUDE.md` de outro projeto.
- **Claude (apps)**: instalar a skill `skills/ai-resource-library` e dar acesso ao repositório na sessão.
- A partir de qualquer projeto, a skill localiza a biblioteca (`locate_library.py`, sem clonar se já houver uma
  cópia válida) e lê o contexto do projeto (`project_context.py`) antes de pesquisar.

Detalhes e limitações por método: [docs/integrations.md](docs/integrations.md).

## Integrar com outros agentes

Codex lê `AGENTS.md` nativamente; Cursor nas versões recentes; ChatGPT por conector GitHub ou anexando ficheiros.
Ver [docs/integrations.md](docs/integrations.md).

## Limitações conhecidas

- Pesquisa por palavras-chave: sinónimos limitados; perguntas muito abstratas precisam do agente para decompor.
- 34 recursos `partially_verified`: preços, planos e algumas licenças por confirmar (ver `unconfirmed_fields`).
- Dados de manutenção são instantâneos (2026-11-06); o validador avisa quando ficam antigos.
- `check_links.py` pode dar "inconclusivo" em sites que bloqueiam pedidos automáticos.
- `environments/` reflete uma sessão concreta; não prova disponibilidade futura.
- O acesso ao repositório privado tem de ser concedido em cada produto/sessão.

## Melhorias futuras

Ver [docs/architecture.md](docs/architecture.md#preparado-para-o-futuro-sem-implementar-já): avaliações,
favoritos, histórico de uso, interface visual estática, servidor MCP próprio, pesquisa avançada.
