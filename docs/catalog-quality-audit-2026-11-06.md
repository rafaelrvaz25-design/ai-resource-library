# Auditoria de qualidade do catálogo (2026-11-06)

## Âmbito
Revisão dos 84 recursos existentes após o teste de descoberta com Claude. Não foi executado código de terceiros, nem atualizada a skill instalada no Claude.

## Estados de verificação antes desta iteração
- 47 `verified`
- 34 `partially_verified`
- 2 `unverified`
- 1 `deprecated`

O estado de verificação refere-se aos **metadados**, não à segurança do código.

## Registos que exigem investigação
- `claude-design-plugin-skills` e `figma-agent-skills`: sem URLs oficiais ou GitHub; manter como `unverified` até identificar origem e licença. Não inventar fontes nem promover o estado.
- Recursos comerciais e parcialmente verificados (ex.: Cursor, Figma, Webflow): verificar condições, licenças, integrações e data de manutenção antes de promover a `verified`.
- A ausência de atualização automática da skill instalada é um problema operacional, não um erro do catálogo. A skill deve ser atualizada manualmente na plataforma onde é utilizada.

## Lacunas avaliadas
- **Imagens:** Sharp, repositório oficial `lovell/sharp`, licença Apache-2.0, não arquivado, atividade confirmada em 2026-11-05. Catalogado como `partially_verified` e opcional; não instalado.
- **CSS:** Lightning CSS, repositório oficial `parcel-bundler/lightningcss`, licença MPL-2.0, não arquivado, atividade confirmada em 2026-11-04. Catalogado como `partially_verified` e opcional; não instalado.
- **Fontes:** não acrescentar ferramenta sem confirmar a necessidade e a adequação ao projeto. Primeiro avaliar o carregamento atual e os resultados do Lighthouse.
- **CSS não utilizado:** minificação não equivale a auditoria de seletores mortos. Esta lacuna continua aberta.

## Execução isolada
O comando `python -I scripts/validate.py --json` pode não conseguir importar o módulo local `library` porque `-I` exclui a pasta do script de `sys.path`. A alteração adiciona apenas o diretório conhecido de `validate.py` ao caminho de importação, com teste de regressão no CI. O ambiente continua a precisar de `jsonschema`; se estiver ausente, o erro de dependência mantém-se esperado.

## Próxima revisão
1. Confirmar as fontes e licenças dos dois registos sem verificação.
2. Investigar ferramentas de análise de CSS não utilizado com provas de manutenção.
3. Reavaliar fontes e imagens com dados reais do projeto antes de recomendar dependências.
4. Confirmar que o agente usa a skill instalada mais recente.
