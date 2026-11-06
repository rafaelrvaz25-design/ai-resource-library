# Arquitetura

## Princípios

Git-native, sem servidores nem bases de dados: tudo é JSON, JSON Schema, Markdown e Python da biblioteca padrão.
O histórico Git é o registo de alterações; as GitHub Actions validam cada push.

```
catalog/_registry.json ──► define tipos (→ ficheiro) e categorias permitidas
catalog/<tipo>.json    ──► FONTE DE VERDADE: cada recurso existe uma só vez
collections/*.json     ──► referências por ID + papel + justificação + recomendações por cenário
environments/*.json    ──► observações datadas: instalado / executável / autorização (por ambiente)
resources/**/<id>.md   ──► documentação própria opcional (campo "doc")
schemas/*.schema.json  ──► contrato dos três tipos de ficheiro
scripts/               ──► search · validate · check_links · new_resource (+ library.py partilhado)
tests/                 ──► testes obrigatórios (unittest)
skills/                ──► skill portável (formato Agent Skills)
```

## Alterações face à estrutura de referência (e porquê)

| Alteração | Motivo |
|---|---|
| **`catalog/_registry.json`** | Novos tipos e categorias sem alterar esquemas nem scripts (requisito §4). O `type` no esquema é validado contra o registo pelo `validate.py`. |
| **Tipo `standard` + `catalog/standards.json`** | MCP, AGENTS.md, Agent Skills, WCAG e DTCG não são ferramentas nem APIs. Serve também de prova de que a extensão funciona. |
| **`environments/` + `environment.schema.json`** | O catálogo descreve recursos *conhecidos/verificados*; "instalado", "disponível" e "autorizado" dependem do ambiente e não podem viver no catálogo sem mentir noutro ambiente. O esquema de recurso **proíbe** esses campos (`additionalProperties: false`). |
| **`resources/` só com ficheiros necessários** | Pastas vazias por tipo seriam duplicação sem valor. Os registos apontam para docs próprias via `doc`. |
| **Sem índice gerado** | Com < 500 registos, o `search.py` lê os JSON diretamente em milissegundos; um índice gerado seria mais um artefacto a sincronizar. Reavaliar acima de alguns milhares de registos. |
| **`scripts/new_resource.py` e `scripts/library.py`** | Adicionar recursos com deteção de duplicados; código de leitura partilhado. |
| **`tests/` e `requirements.txt`** | Os 6 testes obrigatórios correm em CI. Única dependência: `jsonschema` (só para validar). |
| **`skills/ai-resource-library/`** | Skill de consulta portável (§11), com `scripts/locate_library.py` (descoberta validada e clone temporário) e `scripts/project_context.py` (contexto do projeto, só leitura). Os scripts vivem com a skill para poderem ser usados antes de a biblioteca estar localizada. |
| **Sem `.cursor/` nem outros adaptadores** | Codex lê `AGENTS.md` nativamente e o `CLAUDE.md` importa-o. Ver `integrations.md` para os restantes. |

## Modelo de dados (resumo)

Recurso (`schemas/resource.schema.json`):

- Identidade: `id` (kebab-case, estável), `name`, `type`, `origin` (`external`/`internal`)
- Descrição: `summary` (≤200), `description`, `features`, `use_cases`
- Classificação: `categories` (do registo), `tags`, `technologies`, `platforms`
- Ligações: `urls.{official,docs,github,package}`, `related[]` (relações tipadas validadas)
- Uso: `requirements`, `dependencies`, `install.{method,instructions,commands}`, `configuration`
- Negócio: `license.{spdx,name,url}`, `pricing.{model,notes}`
- Estados separados:
  - `maintenance.{status,last_activity,checked_on}` — atividade do projeto
  - `verification.{status,verified_on,method,sources,confirmed_fields,unconfirmed_fields}` — confiança nos metadados
  - `risk.{level,executes_code,requires_credentials,data_access,notes}` — base para pedir autorização
- `limitations`, `notes`, `doc`, `ext` (reservado para extensões)

Valores desconhecidos são `null` ou listas vazias, e aparecem em `unconfirmed_fields`.

## Pesquisa

`scripts/search.py`: normaliza (minúsculas, sem acentos), remove stopwords PT/EN, expande sinónimos PT→EN,
e pontua cada termo por campo (nome/id 6, tags 4, tipo/categorias/tecnologias 3, plataformas 2.5, resumo e casos
de uso 2, funcionalidades 1.5, descrição 1, coleções 1). O total é ponderado pela cobertura dos termos; resultados
com cobertura < 50% são descartados (`--min-coverage`). `unverified` ×0.85, `deprecated` ×0.2 e ocultos por omissão.

É deliberadamente **não semântica**: a interpretação de linguagem natural é feita pelo agente (ver `AGENTS.md` §2).
Não há embeddings nem serviços externos.

## Validação

`scripts/validate.py` verifica JSON, esquemas, tipo ↔ ficheiro, IDs únicos, duplicados (nome normalizado e URL
oficial), categorias, relações, referências das coleções e ambientes, coerência (deprecated não pode ser `core`),
docs existentes, segredos (padrões de tokens/chaves), e avisa sobre verificações antigas (>180 dias) e inatividade
(>365 dias). `scripts/check_links.py` classifica links em ok / partidos / inconclusivos e nunca altera ficheiros.

## Preparado para o futuro (sem implementar já)

| Funcionalidade | Onde encaixa |
|---|---|
| Relações e dependências entre recursos | `related[]` já existe e é validado |
| Favoritos, avaliações, histórico de uso | `ext` nos registos, ou ficheiros novos `ratings/`, `usage/` que referenciam IDs |
| Coleções personalizadas | basta um novo ficheiro em `collections/` |
| Recomendações por contexto | `recommendations[]` por cenário nas coleções |
| Interface visual | página estática (GitHub Pages) que lê os JSON |
| Pesquisa avançada | índice gerado em CI ou embeddings locais, só com necessidade demonstrada |
| Servidor MCP próprio | envolver `search.py` como tool MCP (ver `skill-mcp-builder`) |
| Novos agentes | novo adaptador fino que aponta para `AGENTS.md` |
