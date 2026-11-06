# Guia de contribuição

Aplica-se a pessoas e agentes. As regras de comportamento dos agentes estão em `../AGENTS.md`.

## Preparar

```bash
git clone https://github.com/rafaelrvaz25-design/ai-resource-library
cd ai-resource-library
pip install -r requirements.txt     # só jsonschema
python scripts/validate.py
python -m unittest discover -s tests
```

## Adicionar um recurso

1. Confirmar que não existe: `python scripts/search.py "<nome>" --include-deprecated`.
2. Criar o esqueleto:
   ```bash
   python scripts/new_resource.py --type plugin --id meu-plugin --name "Meu Plugin" \
       --url https://exemplo.org --summary "O que faz, numa frase." --write
   ```
3. Editar o registo em `catalog/<tipo>.json`:
   - `categories` (obrigatório ter pelo menos uma das de `_registry.json` para ser útil), `tags`, `use_cases`.
   - Fontes **oficiais** em `verification.sources`; o que confirmou em `confirmed_fields`; o resto em `unconfirmed_fields`.
   - `verification.status`: `verified` só com origem, URLs, licença e descrição confirmados.
   - `risk`: `executes_code`, `requires_credentials`, nível e notas.
   - `limitations`: pelo menos uma limitação real, se conhecida.
4. (Opcional) Adicionar a coleções: `{ "id": "...", "role": "optional", "rationale": "porquê aqui" }`.
5. `python scripts/validate.py && python -m unittest discover -s tests`.
6. Commit: `catalog: add meu-plugin`.

## Atualizar um recurso

- Alterar só o que foi verificado; atualizar `verification.verified_on` e `maintenance.checked_on`.
- Nunca mudar o `id`. Para substituir: `deprecated` + `related: replaced_by`.
- Commit: `catalog: update <id> (<campo>)`.

## Adicionar uma coleção

Copiar uma coleção existente para `collections/<novo-id>.json` (nome do ficheiro = `id`), preencher e validar.
Só referências por ID; nunca copiar metadados de recursos.

## Adicionar um tipo de recurso

Entrada nova em `catalog/_registry.json` → `types`, e ficheiro `catalog/<ficheiro>.json` com `[]`.

## Registar um ambiente

Ficheiro em `environments/` com o que foi **observado** (data e evidência). Autorização por omissão:
`ask-every-time`. Não registar segredos, nomes de contas privadas nem dados pessoais.

## Regras de conteúdo

- Português de Portugal; nomes técnicos, comandos e identificadores em inglês.
- Não inventar: desconhecido = `null` + `unconfirmed_fields`.
- Não copiar documentação de terceiros; resumir por palavras próprias e ligar à fonte.
- Não incluir credenciais, tokens ou informação privada (o validador procura padrões comuns).
- Projetos próprios: `origin: "internal"` e tag `internal`.

## Convenções de commit

`catalog:`, `collections:`, `scripts:`, `docs:`, `schemas:`, `ci:`, `env:` + descrição curta.
