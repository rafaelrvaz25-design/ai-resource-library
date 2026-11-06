# CLAUDE.md

As regras universais estão em AGENTS.md e aplicam-se integralmente:

@AGENTS.md

(O Claude Code importa o ficheiro acima automaticamente. Noutros produtos Claude, ler `AGENTS.md` antes de continuar.)

## Notas específicas para Claude

**Localizar o catálogo.** Se este repositório estiver aberto, a raiz é a pasta deste ficheiro. Noutros projetos,
usar `skills/ai-resource-library/scripts/locate_library.py`. A ordem é: `AI_RESOURCE_LIBRARY_ROOT` → `~/ai-resource-library`
e afins → caminhos conhecidos do ambiente (ex.: `/home/claude/ai-resource-library`, só se existir) → projeto atual e
antecessores → clone temporário com `--remote`. Cada diretório é validado antes de ser usado. Não assumir que o
acesso de uma sessão anterior continua ativo.

**Contexto do projeto.** `skills/ai-resource-library/scripts/project_context.py <projeto> --library <lib> --compact`
(só leitura) dá tecnologias, restrições, lacunas e pesquisas sugeridas antes de pesquisar.

**Pesquisar.** Executar `python scripts/search.py "<termos>" --json` e trabalhar sobre o JSON. Decompor a pergunta
do utilizador em 2–4 palavras-chave e filtros; se vier vazio, repetir com termos em inglês ou com menos filtros.
Para o registo completo de um candidato: `--show <id>`.

**Consultar coleções.** `--list-collections` para ver as quatro coleções; `--collection <id>` devolve os recursos
por papel e as `recommendations` por cenário — bom ponto de partida para a resposta.

**Interpretar e apresentar resultados.** Para cada recomendação indicar: porque se adequa, estado de verificação,
licença/custo, risco, limitações e link. Separar claramente:
- *Catalogado* (está na biblioteca),
- *Disponível nesta sessão* (verificar as ferramentas/conectores realmente presentes agora;
  `environments/claude-ai-rafael.json` é só uma observação datada),
- *Autorizado* (só com confirmação explícita do utilizador para a ação concreta).

**Skill.** A skill `skills/ai-resource-library/` empacota este processo; se estiver instalada, usá-la.

**Propor novos recursos.** Confirmar em fontes oficiais, usar `scripts/new_resource.py`, preencher, correr
`scripts/validate.py` e os testes. Apresentar o diff ao utilizador antes de fazer commit/push, a menos que
ele tenha pedido explicitamente para atualizar a biblioteca.

**Manter a biblioteca.** `python scripts/validate.py` (erros e avisos de manutenção) e, com rede,
`python scripts/check_links.py --report link-report.md`. Os resultados são propostas: rever antes de alterar.
