# Integrações com agentes e projetos

A biblioteca é um repositório Git **privado**. Um agente só a consegue usar se tiver acesso a uma cópia local
ou ao repositório remoto **nessa sessão**. Nada a torna automaticamente disponível em todas as sessões:
o acesso dado numa conversa ou máquina não passa para outra.

## Como a skill encontra a biblioteca

`skills/ai-resource-library/scripts/locate_library.py` procura por esta ordem e usa a **primeira cópia válida**:

1. `$AI_RESOURCE_LIBRARY_ROOT`
2. Diretório pessoal: `~/ai-resource-library`, `~/.ai-resource-library`, `~/{src,projects,code,dev}/ai-resource-library`
3. Caminhos conhecidos de ambientes, só se existirem: `/home/claude/ai-resource-library` (sessões cloud do Claude),
   `/workspace(s)/ai-resource-library`, mais os de `$AI_RESOURCE_LIBRARY_EXTRA_PATHS` (separados por `:`)
4. O projeto atual e até 3 antecessores, incluindo `./ai-resource-library` e `./.ai-resource-library`
5. Com `--remote`: testa o acesso (`git ls-remote`) e faz um clone superficial para uma **pasta temporária**

"Válida" significa que o diretório tem `AGENTS.md`, o registo de tipos, os ficheiros de catálogo, os esquemas e o
`search.py`. Diretórios inválidos são reportados e ignorados. Se houver uma cópia válida, **não clona**.

## Verificar se a cópia local está atualizada

`python skills/ai-resource-library/scripts/locate_library.py --check-updates` compara o commit local
com `refs/heads/main` remota através de Git, sem fetch nem pull. A verificação é opcional,
precisa de rede e acesso Git, e devolve `current`, `different` ou `unknown`.
`different` não garante que a cópia esteja desatualizada: pode ter commits locais.
Se não houver rede, continuar sem bloquear a descoberta. A skill instalada no agente é
uma cópia separada e pode precisar de atualização manual.

## Cópia local vs repositório remoto

| | Cópia local | Remoto (clone temporário) |
|---|---|---|
| Velocidade | Imediata | Segundos (clone superficial) |
| Atualização | Só o que tiver sido puxado (`git pull`); pode estar desatualizada | Versão atual do branch principal |
| Requisitos | Existir no disco | Acesso autenticado nesta sessão + rede |
| Persistência | Permanente | Apagada no fim (`--cleanup`); não fica cópia |
| Escrita | Possível, se o utilizador pedir manutenção | Push desativado na cópia temporária |
| Falhas | Diretório inválido → passa ao seguinte | `auth_failed`, `repo_not_found`, `network_error`, com mensagem clara |

Credenciais: o script usa apenas a autenticação que o git já tem (credential helper, `gh`, SSH ou o proxy da
sessão). Nunca põe tokens no URL nem os imprime, e as mensagens de erro do git são filtradas.

## Contexto do projeto

`skills/ai-resource-library/scripts/project_context.py <projeto> --library <lib>` faz uma análise estática e
limitada: manifestos de JavaScript, Python, PHP, Go, Rust, Ruby e Java, configurações de frameworks, workflows,
documentação e lacunas. Devolve pesquisas sugeridas e os recursos do catálogo que o projeto já usa.
Não executa scripts do projeto e não lê `.env`.

---

## Claude Code

| Automatizável | Continua a exigir ação/autorização |
|---|---|
| Ler `CLAUDE.md` do projeto e seguir para a biblioteca | Ter uma cópia local **ou** acesso ao repositório na máquina/sessão |
| Skill pessoal disponível em todos os projetos | Instalar a skill uma vez |
| Encontrar a cópia local sem clonar | Atualizar a cópia (`git pull`) |
| Correr `search.py` e `project_context.py` (só leitura) | Instalar ou executar qualquer recurso recomendado |

Configuração única:
```bash
git clone https://github.com/rafaelrvaz25-design/ai-resource-library ~/ai-resource-library
mkdir -p ~/.claude/skills && cp -r ~/ai-resource-library/skills/ai-resource-library ~/.claude/skills/
# opcional, num caminho diferente:  export AI_RESOURCE_LIBRARY_ROOT=/caminho/para/ai-resource-library
```
Em cada projeto, acrescentar ao `CLAUDE.md` (ou `AGENTS.md`):
```markdown
## Recursos
Antes de escolher ferramentas, usar a skill ai-resource-library (AI Resource Library pessoal).
```

## Claude na versão web (claude.ai e apps)

| Automatizável | Continua a exigir ação/autorização |
|---|---|
| A skill fica disponível em todas as conversas depois de instalada | Instalar/atualizar a skill nas definições (ou aceitar a proposta do Claude) |
| Em sessões com ambiente de código, a skill localiza `/home/claude/ai-resource-library` ou faz um clone temporário | **Dar acesso ao repositório em cada conversa** (anexar o repositório / integração GitHub) |
| Analisar um projeto anexado à sessão | Anexar o projeto a analisar |
| | Confirmar qualquer uso de conectores (Figma, Supabase...) |

Notas:
- A skill instalada pode conter só o `SKILL.md`. Nesse caso segue a procura manual descrita no próprio ficheiro e
  usa os scripts que estão dentro da biblioteca, depois de a encontrar.
- Para ter os scripts junto da skill, carregar a pasta `skills/ai-resource-library` completa (em ZIP), se o
  produto o permitir.
- Sem acesso ao repositório, a skill informa que a biblioteca não está acessível e não inventa resultados.

## Codex

| Automatizável | Continua a exigir ação/autorização |
|---|---|
| Lê `AGENTS.md` nativamente (dentro da biblioteca ou do projeto) | Cópia local ou acesso ao repositório no ambiente do Codex |
| Correr os scripts da biblioteca | Aprovação conforme o modo de sandbox do Codex |

No `AGENTS.md` de cada projeto:
```markdown
## Recursos
Antes de escolher ferramentas, consultar a AI Resource Library:
`python ~/ai-resource-library/skills/ai-resource-library/scripts/locate_library.py` e seguir
`<biblioteca>/skills/ai-resource-library/SKILL.md`. Regras: `<biblioteca>/AGENTS.md`.
```

## Cursor

| Automatizável | Continua a exigir ação/autorização |
|---|---|
| Versões recentes leem `AGENTS.md` do projeto | Cópia local da biblioteca na máquina |
| Regras de projeto (`.cursor/rules/`) | Confirmar comandos no terminal conforme as definições do Cursor |

Usar o mesmo parágrafo de "Recursos" no `AGENTS.md` do projeto. Se a versão em uso não ler `AGENTS.md`, criar uma
regra em `.cursor/rules/` com esse parágrafo. Confirmar o formato atual na documentação de regras do Cursor.

## ChatGPT e outros agentes

O ChatGPT não lê ficheiros de instruções do repositório automaticamente. Opções:
- ligar o GitHub (se o plano tiver esse conector);
- anexar `AGENTS.md`, a coleção relevante e o `catalog/<tipo>.json` necessário.

Sem execução de scripts, a pesquisa e o contexto são feitos pelo modelo e são menos determinísticos.
Outros agentes: começar por `AGENTS.md`. Um adaptador deve **apontar** para ele, não copiá-lo.

## Outros métodos de acesso

| Método | Uso | Limitações |
|---|---|---|
| GitHub REST API | `GET /repos/rafaelrvaz25-design/ai-resource-library/contents/<caminho>` | Token de leitura; rate limits; sem execução de scripts |
| GitHub MCP Server | Ler ficheiros a partir de clientes MCP | Configurar o servidor; preferir read-only |
| MCP Filesystem | Apontar (read-only) para a cópia local | Apps desktop sem shell |
| Servidor MCP próprio | Não implementado | Ver `architecture.md` |
