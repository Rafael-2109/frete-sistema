# Atualizacao Sentry — 2026-06-15-1

**Data**: 2026-06-15
**Org / Projeto**: `nacom` / `python-flask` (regionUrl `https://us.sentry.io`)
**Issues avaliadas**: 50 (top por frequencia, `is:unresolved environment:production`)
**Issues resolvidas/fechadas nesta execucao**: 1 (XZ — fix ja em `main`; marcada `resolved` + comentario de rastreio)
**Issues fora de escopo / ignoradas**: 49
**Arquivos de codigo modificados por esta triagem**: 0

## Resumo

Padrao identico as triagens anteriores: 46 das 50 issues abertas em producao sao
falhas de infraestrutura externa do Odoo (CIEL IT) — `ProtocolError 502 Bad
Gateway` em `odoo.nacomgoya.com.br/xmlrpc/2/common` e "Falha na autenticacao com
Odoo" disparadas pelos crons/jobs de sync. Nao sao bugs de codigo (infra
externa). Apenas **1 bug tecnico real** estava no escopo (PYTHON-FLASK-XZ —
`TypeError: float - Decimal` no template de fatura CarVia) e **ja estava
corrigido em `main`** antes desta execucao (commit `68d1e43b4`). Os 4 outros
candidatos nao-Odoo (XA, HW, E7, J1) sao `logger.error` nao-crash, transientes
de conexao, comportamento da memoria do agente ou perf (N+1) — todos fora do
escopo de correcao tecnica simples. **Nenhuma alteracao de codigo foi feita.**

## Issues Avaliadas — Escopo de Correcao

### PYTHON-FLASK-XZ: TypeError: unsupported operand type(s) for -: 'float' and 'decimal.Decimal'
- **Frequencia**: 9 eventos, 2 usuarios (first/last seen 2026-06-08).
- **Culprit**: `carvia.detalhe_fatura_cliente` →
  `app/templates/carvia/faturas_cliente/detalhe.html:278`.
- **Causa raiz**: o alerta de divergencia I2 fazia
  `(fatura.valor_total|float - (_soma_ops + _soma_comp))|abs > 1.0`, onde
  `_soma_ops`/`_soma_comp` somavam `cte_valor` (coluna `Numeric` →
  `decimal.Decimal`). Subtrair `float - Decimal` levanta `TypeError`.
- **Status**: **JA CORRIGIDO EM `main`** — commit `68d1e43b4`
  (`fix(carvia): corrige float-Decimal no detalhe de fatura-cliente`,
  2026-06-08 **13:45 BRT**) adicionou `|float` aos dois somatorios (linhas
  276-277), normalizando ambos os operandos para `float` antes da subtracao.
- **Por que os eventos apareceram**: os 9 eventos rodaram sobre o release
  `fd2f61479` (commit **11:18 BRT**), ANTERIOR ao fix das 13:45 BRT.
  `git merge-base --is-ancestor 68d1e43b4 fd2f61479` retorna falso → o fix NAO
  estava no release dos eventos → ruido pre-deploy; nao recorre apos o deploy.
- **Acao**: marcada `resolved` no Sentry com comentario de rastreio (commit +
  release + analise de timeline). **Sem alteracao de codigo** (working tree
  limpo; fix ja commitado em `main`).

### PYTHON-FLASK-XA: Can't reconnect until invalid transaction is rolled back
- **Frequencia**: 18 eventos, 7 usuarios. Substatus `regressed`.
- **Culprit**: `teams.bot_message` →
  `app/agente/tools/ontology_query_tool.py` (`[ONTOLOGY_QUERY]`).
- **Natureza**: `logger.error()` com HTTP 200 (`trace.status: ok`), nao crash.
  A sessao SQLAlchemy chega ao tool ja em transacao invalida (envenenada por
  statement anterior no mesmo request). Rollback best-effort **ja presente** no
  handler (`ontology_query_tool.py:196-204`, referenciando `PYTHON-FLASK-XA`).
- **Status**: fora de escopo — concern estrutural de sessao; fix defensivo ja
  presente; ja documentado na triagem 2026-06-08.

### PYTHON-FLASK-WK / WJ: Fault XML-RPC (script ad-hoc)
- **Frequencia**: 24 + 22 eventos, 0 usuarios.
- **Culprit aparente**: `app.odoo.utils.connection in _do_execute`, mas o top
  frame real e `<string>` + `python -c` (Render Shell). Script ad-hoc
  consultando `account.journal` (mismatch de schema/versao Odoo). Nao e codigo
  versionado. Fora de escopo (consistente com triagens anteriores).

## Issues Fora de Escopo / Ignoradas (49)

### Infra externa Odoo — XML-RPC 502 / auth (46 issues)

`502 Bad Gateway` / `ProtocolError` em `odoo.nacomgoya.com.br/xmlrpc/2/common`
e "Falha na autenticacao com Odoo" disparadas por dezenas de crons/jobs de sync.
Mesma causa raiz (Odoo CIEL IT intermitentemente down / auth falhando); cada
modulo emite sua propria issue. Recorrente em TODAS as triagens anteriores. Por
frequencia: V5 (226), V6 (179), V7 (58), 5C (54), 4 (51), 3 (42), TY (40),
TW (39), TJ (31), TQ (31), 6J (30), 5Y (26), 5X (26), V8 (20), GQ (20),
BZ (20), C4 (19), 5Z (19), CD (19), GS (18), C8 (18), GN (18), CC (21),
C3 (17), GT (17), H0 (15), GV (14), GR (14), 58 (12), 56 (12), 5N (11),
V9 (10), C0 (10), BX (10), 5M (10), 5K (10), C5 (9), 5P (9), 5J (9), 5H (9),
5W (8), GP (7). Varias marcadas `super_low`/`medium` actionability pelo Seer,
consistente com infra externa.

### Scripts ad-hoc Render Shell (2 issues)

WK (24ev) e WJ (22ev) — vide secao acima. `python -c` no Render Shell, schema
Odoo, nao codigo versionado.

### logger.error nao-crash / transiente / comportamento de agente / perf (1+4 = 5, contadas acima ou aqui)

- **XA** (18ev, 7us) — `logger.error` HTTP 200, rollback defensivo ja presente
  (vide secao Escopo). Fora de escopo.
- **HW** (10ev, 6us) — `[MEMORY_MCP]` `psycopg2.OperationalError: SSL connection
  has been closed unexpectedly` em `teams.bot_message`. Drop transiente de
  conexao Postgres mid-query, logado via `logger.error` (transacao `mcp.server`,
  nao crash). 10 eventos em ~2 meses (15/04→11/06) = taxa baixa, intermitente.
  Infra/transiente — nao corrigivel por guard None/KeyError. Fora de escopo.
- **E7** (10ev, 8us) — `[MEMORY_MCP] update_memory: Texto nao encontrado`. O tool
  de find-and-replace da memoria do agente recebeu `old_str` desatualizado (a
  LLM passou um trecho que nao bate com o conteudo atual do arquivo). Modo de
  falha esperado das semanticas de edit (handler ja devolve "Conteudo atual"
  para retry). Comportamento do agente, nao crash tecnico. Fora de escopo.
- **J1** (9ev, 4us) — `N+1 Query` (categoria `db_query`) em `portaria.dashboard`.
  Issue de performance; exige refactor (eager loading). Consistente com triagens
  anteriores que classificam N+1 como fora de escopo (refactor). Fora de escopo.

## Metricas

- Issues abertas (unresolved/production) avaliadas: 50
- Bugs tecnicos de aplicacao acionaveis e em aberto: **0** (o unico real, XZ, ja
  estava corrigido em `main` antes desta execucao)
- Issues corrigidas com codigo nesta execucao: 0
- Issues marcadas `resolved` nesta execucao: 1 (XZ — fix ja em `main`;
  comentario de rastreio adicionado)
- Fora de escopo: 49 (46 infra Odoo externa + 2 scripts ad-hoc + 1 N+1 +
  contabilizando XA/HW/E7 como logger/transiente/agente)
- **Arquivos de codigo modificados por esta triagem: 0**

> Nota para o orquestrador D4: nenhum arquivo de codigo foi modificado por esta
> triagem. O working tree contem apenas 2 scripts `docs/industrializacao-fb-lf/`
> nao rastreados, pre-existentes e NAO relacionados a esta execucao.
