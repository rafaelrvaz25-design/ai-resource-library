# resources/

Documentação **própria** e opcional sobre recursos do catálogo, para quando os metadados JSON não chegam
(guias de configuração, decisões, armadilhas, notas de utilização).

Convenções:

- Caminho: `resources/<pasta-do-tipo>/<id>.md` (ex.: `resources/mcp-servers/github-mcp-server.md`).
- O registo no catálogo aponta para o ficheiro através do campo `doc`. O `validate.py` confirma que existe.
- Escrever por palavras próprias e ligar à documentação oficial. **Não copiar** READMEs ou documentação de terceiros.
- Comandos aqui documentados são referência: nunca são autorização para os executar (ver `AGENTS.md` §5).
- Não criar ficheiros vazios só para "completar" a estrutura: a maioria dos recursos não precisa de doc própria.
