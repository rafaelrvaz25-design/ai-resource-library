# Teste de descoberta: portfolio-v2 (2026-11-06)

## Objetivo e âmbito

Avaliar a capacidade de descoberta de recursos da AI Resource Library a partir de pedidos de Product Design, UI/UX e desenvolvimento web, usando o projeto real `rafaelrvaz25-design/portfolio-v2` como contexto. **O portfólio não foi alterado.**

## Contexto confirmado no GitHub

- Repositório: https://github.com/rafaelrvaz25-design/portfolio-v2
- `package.json`: Next.js 13.4.10, React 18.2, GSAP, Framer Motion, Locomotive Scroll, Sass e Three.js.
- `next.config.js`: `output: 'export'`, `trailingSlash: true`, `basePath` dependente do ambiente; `eslint.ignoreDuringBuilds: true`.
- `README.md`: publicação no GitHub Pages, conteúdo dos case studies em Markdown.

## Metodologia

Foram consultados os 84 registos dos ficheiros `catalog/*.json` e a implementação de `scripts/search.py` em `main`. As seis pesquisas foram **simuladas em JavaScript com os mesmos pesos, normalização básica, limiar de cobertura (0,5) e critérios de ordenação do motor Python**. Não se executou o CLI Python nem a skill instalada; os resultados são **indicativos**, não uma execução end-to-end. Não houve execução de código dos recursos externos.

## Resultados indicativos

| Pesquisa | Top resultados | Observação |
|---|---|---|
| `melhorar design visual portfolio nextjs` | webflow (12.16) | **Falha**: não recupera oil-ui, skill-frontend-design ou design-how; os termos genéricos e `nextjs` dificultam cobertura |
| `direcao visual interface website` | oil-ui (11), skill-frontend-design (7.22), webflow (6.65) | **Passa**: oil-ui é o primeiro |
| `documentar componentes handoff figma` | figma-mcp-server (33.5), figma (28), figma-rest-api (24.22), storybook (21.68), tokens-studio (15.05), dimensional-drawing (14.88) | **Parcial**: encontra dimensional-drawing em 6.º; ranking não reflete intenção de documentação dimensional |
| `investigacao referencias visuais websites` | awwwards-mcp (11.05), mcp-server-fetch (10.5), zotero (6.3) | **Passa**: awwwards-mcp é o primeiro |
| `design system react componentes` | shadcn-ui (24.5), storybook (23.5), radix-ui-primitives (21.5), react (18), design-how (15) | **Parcial**: design-how surge em 5.º; resultados podem ser complementares, não necessariamente errados |
| `identidade visual marca logotipo` | brand-identity-skill (24.5), skill-frontend-design (4.2) | **Passa**: brand-identity-skill é o primeiro |

## Diagnóstico

1. O motor de pesquisa é lexical e não interpreta intenções. Uma frase com várias restrições pode ocultar o recurso correto devido ao `--min-coverage 0.5`.
2. O dicionário `SYNONYMS` é limitado para português de Product Design: `melhorar`, `portfólio`, `direção`, `identidade`, `handoff` e variantes nem sempre convergem para termos indexados.
3. Os pesos de nome/tags favorecem correspondências lexicais fortes, mas não distinguem **função principal**, **alternativa** e **complemento**.
4. A skill já documenta que pedidos complexos devem ser decompostos em pesquisas específicas. Este teste demonstra a importância de verificar se os agentes seguem esse passo.
5. A catalogação não implica instalação, disponibilidade ou autorização. Nenhuma ferramenta externa foi instalada.

## Recomendações (não implementadas)

- Criar testes de regressão com intenções em PT-PT, consultas compostas e expectativas mínimas de recuperação, evitando impor uma ordem artificial a recursos complementares.
- Acrescentar um passo de decomposição de pedidos complexos na skill e procurar por intenções separadas: `direcao visual interface`, `design system react`, `acessibilidade`, `performance`.
- Reforçar sinónimos de UX/UI e normalização linguística; testar o impacto em falsos positivos.
- Distinguir no relatório de recomendação recursos `core`, `recommended`, `optional`, alternativas e ferramentas já usadas pelo projeto.
- Testar explicitamente as regras de autorização e ausência de instalação.

## Critérios para próxima iteração

1. O pedido composto sobre melhorar o portfólio deve recuperar `oil-ui` e `skill-frontend-design` entre as opções a considerar, sem perder as ferramentas de performance e acessibilidade.
2. `dimensional-drawing`, `awwwards-mcp`, `design-how` e `brand-identity-skill` devem ser recuperáveis por intenções PT-PT próprias.
3. As recomendações devem explicar **porquê**, **quando não usar**, **riscos** e **estado de instalação**.
4. Os testes unitários, validação de esquemas e CI existentes devem continuar a passar.

## Estado

Diagnóstico concluído e documentado; melhorias ao motor de pesquisa ainda não implementadas. O projeto `portfolio-v2` permanece intacto.
