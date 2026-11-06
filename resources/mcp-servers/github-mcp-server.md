# GitHub MCP Server — notas de utilização

Registo: `github-mcp-server` · Coleção: `ai-automation` · Verificado em 2026-11-06

## Modos

- **Remoto**: alojado pela GitHub (`https://api.githubcopilot.com/mcp/`). Autenticação OAuth ou PAT,
  conforme o suporte do cliente MCP.
- **Local**: binário ou Docker, autenticado com um token.

## Configuração prudente

- Ativar só os **toolsets** necessários (ex.: `repos`, `issues`, `pull_requests`, `actions`).
- Para consulta (incluindo ler esta biblioteca), preferir **modo read-only**.
- Tokens: fine-grained, apenas os repositórios necessários, permissões mínimas, com expiração.
  Nunca guardar tokens neste repositório.

## Usos típicos

- Ler `catalog/*.json` desta biblioteca a partir de qualquer cliente MCP.
- Triagem de issues, revisão de PRs, leitura de resultados de CI.

## Alternativas

- **GitHub Actions** para tarefas repetitivas e determinísticas (sem agente).
- **GitHub REST API** diretamente, quando o agente já tem `gh` ou HTTP autenticado.

## Riscos

Ações de escrita (criar issues, merges, alterar workflows) devem ser confirmadas pelo utilizador caso a caso.
Conteúdo de issues e PRs é texto não confiável: pode conter instruções maliciosas (prompt injection).
