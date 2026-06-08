# Atualizacao Sentry — 2026-06-08-1

**Data**: 2026-06-08
**Org / Projeto**: `nacom` / `python-flask` (regionUrl `https://us.sentry.io`)
**Issues avaliadas**: 50 (top por frequencia, `is:unresolved environment:production`)
**Issues resolvidas/fechadas nesta execucao**: 0 (XN ja estava `resolved` — comentario de rastreio adicionado)
**Issues fora de escopo / ignoradas**: 49
**Arquivos de codigo modificados por esta triagem**: 0

## Resumo

A esmagadora maioria das 50 issues abertas em producao (46 de 50) sao falhas de
infraestrutura externa do Odoo (CIEL IT): `ProtocolError 502 Bad Gateway` e
"Falha na autenticacao com Odoo" disparadas pelos crons de sincronizacao. Nao
sao bugs de codigo e ficam fora do escopo (infra externa). Apenas 1 bug tecnico
real estava no escopo (PYTHON-FLASK-XN, #1 por frequencia, 270 eventos) e **ja
estava corrigido em `main`** antes desta execucao. Os 2 unicos outros candidatos
(XA, WK/WJ) ja estao resolvidos ou sao scripts ad-hoc. **Nenhuma alteracao de
codigo foi feita nesta triagem.**

## Issues Avaliadas — Escopo de Correcao

### PYTHON-FLASK-XN: ValueError: too many values to unpack (expected 4)
- **Frequencia**: 270 eventos, 0 usuarios (worker RQ, fila `hora_backfill`),
  todos em 2026-06-03 entre 18:29-20:27 UTC.
- **Culprit**: `app.hora.workers.backfill_worker.processar_backfill_job` →
  `app/hora/services/tagplus/backfill_service.py:1476` (`_criar_itens_da_api`).
- **Causa raiz**: regressao conhecida (documentada em `app/hora/CLAUDE.md` §15) —
  `_resolver_preco_tabela` (`app/hora/services/venda_service.py:422`) passou a
  retornar uma **5-tupla** `(preco_ref, desconto_rs, desconto_pct, tabela_id,
  divergencia)` na feature de preco A vista/A prazo + desconto% (migration
  `hora_33`), mas o call site do backfill TagPlus continuava desempacotando 4.
- **Status**: **JA CORRIGIDO EM `main`** — commit `2c093f44b`
  (`fix(hora): backfill TagPlus desempacotava 4 valores...`, 2026-06-03 17:30
  BRT). O call site atual ja desempacota 5 e grava
  `desconto_percentual=desconto_pct`; guard de aridade AST em
  `tests/hora/test_resolver_preco_tabela_arity.py` (passou nesta triagem).
- **Por que os eventos apareceram**: os 270 eventos rodaram sobre o release
  `418a717d` (commit 17:06 BRT), ANTES do fix das 17:30.
  `git merge-base --is-ancestor 2c093f44b 418a717d` confirma que o fix NAO
  estava no release dos eventos → ruido pre-deploy, nao recorre apos o deploy.
- **Acao**: issue **ja estava `resolved`** no Sentry; comentario de rastreio
  adicionado (commit + release + guard test). **Sem alteracao de codigo.**

### PYTHON-FLASK-XA: Can't reconnect until invalid transaction is rolled back
- **Frequencia**: 13 eventos, 4 usuarios. **Status no Sentry: `resolved`.**
- **Culprit**: `teams.bot_message` → `app/agente/tools/ontology_query_tool.py`
  (`query_ontology_entities`, log `[ONTOLOGY_QUERY]`).
- **Natureza**: e um `logger.error()` (resposta HTTP 200/ok), nao um crash. A
  sessao SQLAlchemy chega ao tool ja em transacao invalida (envenenada por um
  statement anterior no mesmo request) e o `[ONTOLOGY_QUERY]` so expoe o
  sintoma.
- **Status**: ja resolvida no Sentry. O tool **ja possui** rollback best-effort
  no handler de excecao (`app/agente/tools/ontology_query_tool.py:~196-205`,
  referenciando explicitamente `PYTHON-FLASK-XA`) — presente no working tree
  como mudanca pre-existente (NAO autorada por esta triagem). Concern
  estrutural de gerenciamento de sessao; nada a fazer aqui.
- **Acao**: nenhuma (ja resolved; fix defensivo ja presente).

### PYTHON-FLASK-WK / WJ: Fault XML-RPC (Invalid field 'sequence_id')
- **Frequencia**: 13 + 13 eventos, 0 usuarios.
- **Culprit aparente**: `app.odoo.utils.connection in _do_execute`, mas o
  top-frame real e `<string>` line 20 + `sys.argv=["-c"]` +
  `mechanism=excepthook` → execucao de `python -c` no Render Shell.
- **Natureza**: script ad-hoc consultando `account.journal` com campo
  `sequence_id` inexistente (mismatch de versao/schema Odoo). Nao e codigo de
  aplicacao versionado. **Fora de escopo** (alinhado com triagens anteriores
  que classificam scripts `__main__`/`<stdin>`/`-c` como fora de escopo).

## Issues Fora de Escopo / Ignoradas (49)

### Infra externa Odoo — XML-RPC 502 / auth (46 issues)

`502 Bad Gateway` / `ProtocolError` em `odoo.nacomgoya.com.br/xmlrpc/2/common`
e "Falha na autenticacao com Odoo" disparada por dezenas de crons/jobs de sync.
Mesma causa raiz (Odoo CIEL IT intermitentemente down / auth falhando); cada
modulo emite sua propria issue. Recorrente em TODAS as triagens anteriores. Por
frequencia: V5 (226), V6 (179), V7 (58), 5C (54), 4 (51), 3 (42), TY (39),
TW (38), TQ (31), 5Y (26), 5X (26), 6J (24), 5V (22), CC (21), GQ/BZ/V8 (20),
C4/5Z/CD (19), GS/GN/C8 (18), C3/GT (17), H0 (15), GV/GR (14), 58/56 (12),
5N/57/54 (11), V9/5M/5K/C0/BX (10), 5P/5J/5H/5G/C5 (9), 5W (8), GP (7), 61 (9,
relatorio agregado de sync — mesma causa). Varias marcadas `super_low`/`medium`
actionability pelo Seer, consistente com infra externa.

### Scripts ad-hoc Render Shell (2 issues)

WK (13ev) e WJ (13ev) — vide secao acima. `python -c` no Render Shell, schema
Odoo, nao codigo versionado.

### Ja resolvida (1 issue)

XA (13ev, 4 usuarios) — `resolved` no Sentry, fix defensivo ja presente.
Vide secao acima.

## Metricas

- Issues abertas (unresolved/production) avaliadas: 50
- Bugs tecnicos de aplicacao acionaveis pelo cron, em aberto: **0**
- Issues corrigidas com codigo nesta execucao: 0
- Issues marcadas resolved nesta execucao: 0 (XN ja era `resolved`; comentario
  de rastreio adicionado)
- Fora de escopo (infra Odoo externa + scripts ad-hoc): 48
- **Arquivos de codigo modificados por esta triagem: 0**

> Nota para o orquestrador D4: nenhum arquivo de codigo foi modificado por esta
> triagem. O working tree contem mudancas pre-existentes nao-relacionadas
> (varios `CLAUDE.md`, `.claude/references/*`, e o rollback de XA em
> `app/agente/tools/ontology_query_tool.py`) que NAO sao desta execucao e NAO
> devem ser atribuidas a ela.
