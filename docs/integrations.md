# Integrações com agentes e projetos

Resumo: a biblioteca é um repositório Git **privado**. Qualquer agente que consiga ler o repositório consegue
usá-la; a forma de acesso depende do produto. **O acesso de uma sessão não passa automaticamente para outras.**

## Métodos de acesso

| Método | Como | Limitações reais |
|---|---|---|
| **Git clone** | `git clone https://github.com/rafaelrvaz25-design/ai-resource-library ~/ai-resource-library` | Requer credenciais com acesso ao repositório privado. Atualizar com `git pull`. |
| **Scripts locais** | `python scripts/search.py ...` na cópia local | Requer Python 3.9+ e shell. Sem dependências para pesquisar. |
| **Integração GitHub nativa do agente** | Indicar o repositório ao agente (ex.: anexar o repositório na sessão Claude) | Depende do produto e de autorização por sessão/organização. Algumas integrações só leem ficheiros (sem executar scripts). |
| **GitHub REST API** | `GET /repos/rafaelrvaz25-design/ai-resource-library/contents/catalog/mcp-servers.json` | Token com permissão de leitura; rate limits; devolve conteúdo em base64. |
| **GitHub MCP Server** | Ferramentas de leitura de ficheiros do servidor oficial (`github-mcp-server` no catálogo) | Requer o servidor configurado no cliente; preferir modo read-only. |
| **MCP Filesystem** | Apontar `mcp-server-filesystem` (read-only) para a cópia local | Útil em clientes MCP sem shell (ex.: apps desktop). |
| **Skill** | `skills/ai-resource-library/` | Ver abaixo. Requer que a biblioteca esteja acessível por um dos métodos anteriores. |
| **Servidor MCP próprio** | Não implementado (v2) | Exigiria um processo a correr; desnecessário enquanto `search.py` + leitura de ficheiros chegar. |

## Claude

### Claude (claude.ai / apps)
1. Instalar a skill: comprimir a pasta `skills/ai-resource-library` em ZIP e carregá-la nas definições de
   skills do Claude (o nome exato do menu pode mudar entre versões), ou guardar a proposta de skill que o Claude ofereceu na sessão de criação.
2. Em cada sessão nova, dar acesso ao repositório (integração GitHub da sessão) e pedir, por exemplo:
   *"Consulta a minha ai-resource-library: que recursos tenho para uma landing page em WordPress?"*
3. Sem acesso ao repositório na sessão, a skill avisa e não inventa resultados.

### Claude Code
- Dentro do repositório: o `CLAUDE.md` é lido automaticamente e importa o `AGENTS.md`.
- Noutros projetos, acrescentar ao `CLAUDE.md` do projeto:
  ```markdown
  ## Recursos
  Antes de escolher ferramentas, consultar a AI Resource Library em ~/ai-resource-library
  (python ~/ai-resource-library/scripts/search.py "<termos>" --json). Regras: ~/ai-resource-library/AGENTS.md
  ```
- Skill pessoal: copiar `skills/ai-resource-library/` para `~/.claude/skills/ai-resource-library/`.

## Codex (OpenAI)
Lê `AGENTS.md` nativamente quando trabalha dentro do repositório. Noutros projetos, acrescentar ao `AGENTS.md`
desse projeto o mesmo parágrafo de "Recursos" acima. Não é necessário adaptador.

## Cursor
Versões recentes leem `AGENTS.md`. Se a versão em uso não o fizer, criar `.cursor/rules/ai-resource-library.mdc`
no projeto consumidor com um parágrafo a apontar para `AGENTS.md` e para `scripts/search.py`
(confirmar o formato atual na documentação de regras do Cursor). Não foi criado adaptador porque duplicaria `AGENTS.md`.

## ChatGPT
Não lê ficheiros de instruções do repositório automaticamente. Opções: ligar o GitHub através dos conectores
disponíveis na conta (se existirem no plano) e pedir para ler `AGENTS.md` e a coleção relevante; ou anexar
`AGENTS.md` + `collections/<id>.json` + o `catalog/<tipo>.json` necessário à conversa. Sem execução de scripts,
a pesquisa é feita pelo próprio modelo sobre os JSON — menos determinística.

## Outros agentes
Qualquer agente com leitura do repositório: começar por `AGENTS.md`. Para adicionar um adaptador, criar um
ficheiro fino no formato que o agente lê, que **aponta** para `AGENTS.md` em vez de o copiar.

## Usar a biblioteca a partir de outro projeto (sem copiar recursos)

1. Ter uma cópia local partilhada (`~/ai-resource-library`) ou acesso GitHub.
2. Referir a biblioteca no ficheiro de instruções do projeto (parágrafo acima).
3. No projeto, registar apenas as **decisões** (que recursos foram escolhidos e porquê), não os metadados.
