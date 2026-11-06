# WordPress — notas de utilização

Registo: `wordpress` · Coleção: `web-development` · Verificado em 2026-11-06

## Quando escolher WordPress

- A página tem de ser editada por quem não programa.
- Há necessidade de CMS (posts, páginas, media, formulários) e não apenas uma página estática.

Se o conteúdo só for editado por quem programa, uma página estática (ver `internal-portfolio-static`)
ou Next.js com exportação estática é mais simples, rápida e gratuita no GitHub Pages.

## Abordagem recomendada para uma landing page

1. **Prototipar sem servidor** com `wordpress-playground`.
2. **Tema de blocos** (Full Site Editing) em vez de page builders: menos dependências e melhor performance.
   O plugin `create-block-theme` permite desenhar no Site Editor e exportar o tema.
3. **Tokens de design → `theme.json`**: cores, tipografia e espaçamentos do design system.
4. **Validar** com `lighthouse` (performance e acessibilidade) e testar breakpoints com `playwright`.
5. **Diagnóstico** com `query-monitor` apenas em desenvolvimento.

## Integração com agentes

- `wordpress-mcp-adapter` é a integração MCP oficial (abilities privadas por omissão).
- `automattic-wordpress-mcp` está **descontinuado**: não usar.
- `wordpress-rest-api` serve para automação e cenários headless.

## Riscos

- Plugins e temas de terceiros são o principal vetor de ataque: verificar origem, manutenção e número de instalações.
- `wp-cli` tem acesso total ao site: comandos destrutivos exigem autorização explícita.
