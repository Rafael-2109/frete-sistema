# Atualizacao Sentry — 2026-06-01-1

**Data**: 2026-06-01
**Org / Projeto**: `nacom` / `python-flask` (regionUrl `https://us.sentry.io`)
**Issues avaliadas**: 23 (todas `is:unresolved environment:production`)
**Issues resolvidas**: 3 (WB, WD ja-corrigidas em commit anterior; W4 corrigida nesta execucao)
**Issues fora de escopo / ignoradas**: 20

## Resumo

Triagem das 23 issues nao resolvidas em producao, ordenadas por frequencia. Tres
issues caem no escopo de correcao tecnica e foram marcadas `resolved`:
- **WB** e **WD** ja estavam corrigidas no `main` HEAD pelo commit `4477faa4d`
  (2026-05-27 20:41); os eventos rodaram em release anterior ao fix.
- **W4** foi corrigida nesta execucao: caminho de import errado num script de skill
  (1 arquivo modificado).

As 20 restantes sao instabilidade XML-RPC do Odoo (infra externa CIEL IT), scripts
ad-hoc de Render Shell / Python interativo (`__main__` / `<stdin>`,
`mechanism=excepthook`), config de ambiente (tessdata OCR) ou logs de condicao de
negocio — todas fora do escopo de correcao do cron.

## Issues Resolvidas

### PYTHON-FLASK-W4 — ModuleNotFoundError: No module named 'app.carvia.services.cotacao_service'
- **Frequencia**: 1 evento, 0 usuarios (last seen 6 dias)
- **Culprit**: `__main__ in cotar_transportadora` →
  `.claude/skills/gerindo-carvia/scripts/cotando_subcontrato_carvia.py`
- **Causa raiz**: o script importava `from app.carvia.services.cotacao_service import
  CotacaoService`, mas o modulo real esta em
  `app.carvia.services.pricing.cotacao_service` (`class CotacaoService` linha 29). O
  segmento `.pricing.` estava ausente no path.
- **Fix (categoria: missing/corrected import)**: corrigido o caminho de import nas 3
  ocorrencias (linhas 24, 52, 108) para `app.carvia.services.pricing.cotacao_service`.
  - **stacktrace → arquivo:linha**: `cotando_subcontrato_carvia.py:52` (culprit
    `cotar_transportadora`); demais ocorrencias 24 e 108.
- **Verificacao**: `ast.parse` OK; confirmado que o destino tem `class CotacaoService`
  e o metodo `cotar_subcontrato` (usado pelo culprit `cotar_transportadora`).
- **Nota (latente, fora de escopo)**: as funcoes `--listar-opcoes`/`--todas` chamam
  `service.listar_opcoes_transportadora(...)`, que **nao existe** na classe atual (so
  ha `cotar_subcontrato` e `cotar_todas_opcoes`). Isso e um bug de interface separado,
  NAO reportado no Sentry (o evento W4 e do culprit `cotar_transportadora`, que so usa
  `cotar_subcontrato`). Corrigi-lo exigiria refactor de interface — fora do escopo de
  "missing import". Documentado aqui para tratamento futuro.
- **Acao**: marcado `resolved` com comentario rastreavel.

### PYTHON-FLASK-WB — AttributeError: 'OdooConnection' object has no attribute 'search_count'
- **Frequencia**: 12 eventos, 1 usuario
- **Culprit**: `inventario.movimentacoes_api` →
  `app/inventario/services/movimentacoes_odoo_service.py` (`buscar_paginado`)
- **Causa raiz**: chamada a `OdooConnection.search_count(...)` num release onde o metodo
  ainda nao existia / o service usava a API antiga.
- **Fix (pre-existente)**: `OdooConnection.search_count` existe em
  `app/odoo/utils/connection.py:318`; o service ja chama `odoo.search_count('stock.move.line', domain)`
  corretamente (`movimentacoes_odoo_service.py:86`). Consolidado no commit `4477faa4d`
  (2026-05-27 20:41 — "fix(inventario): tela Confronto"). Todos os 12 eventos sao de
  2026-05-27 14:xx, **anteriores** ao fix.
- **Acao**: marcado `resolved` (ja-resolved; comentario rastreavel postado). Nenhum
  arquivo modificado para esta issue.

### PYTHON-FLASK-WD — TypeError: OdooConnection.search() got an unexpected keyword argument 'offset'
- **Frequencia**: 5 eventos (issue) / 6 em 14d, 1 usuario
- **Culprit**: `inventario.movimentacoes_api` →
  `app/inventario/services/movimentacoes_odoo_service.py` (`buscar_paginado`)
- **Causa raiz**: `odoo.search('stock.move.line', domain, offset=..., order=...)` — o
  metodo `OdooConnection.search()` so aceita `limit` (`connection.py:310`); paginacao +
  ordenacao sao de `search_read` (`connection.py:296`).
- **Fix (pre-existente)**: service reescrito para usar `odoo.search_read(..., fields=,
  offset=, limit=, order=)` (`movimentacoes_odoo_service.py:90-96`) no commit `4477faa4d`
  (mensagem: "OdooConnection.search() nao aceita offset/order. Fix: search()+read()
  unificados em search_read() unico"). Os eventos (20:15–23:05 de 27/05) precedem ou
  coincidem com o deploy do fix; codigo em `main` HEAD esta correto.
- **Acao**: marcado `resolved` (ja-resolved; comentario rastreavel postado). Nenhum
  arquivo modificado para esta issue.

## Issues Fora de Escopo / Ignoradas (20)

### Odoo XML-RPC / 502 Bad Gateway — infra externa CIEL IT (11)
Instabilidade do `odoo.nacomgoya.com.br/xmlrpc/2/common` (502 / Fault server-side).
Padrao recorrente (ja documentado em 2026-05-18). Fora de escopo: infra externa.
- **TY** (38 ev) — ProtocolError 502 Bad Gateway na autenticacao Odoo
- **TQ** (31 ev) — ProtocolError 502 Bad Gateway na autenticacao Odoo
- **P6** (28 ev) — Fault em `account.move.search_read`
- **P5** (22 ev) — Fault em `_do_execute`
- **WJ** (10 ev) — Fault em `app.odoo.utils.connection._do_execute`
- **WK** (7 ev) — Fault em `app.odoo.utils.connection._do_execute`
- **WP** (2 ev) — Fault em `_do_execute`
- **VF** (2 ev) — Fault 2 `l10n_br_fiscal.document.line nao existe` (modelo Odoo)
- **W8** (1 ev) — Fault 2 `l10n_br_fiscal.document.line nao existe`
- **WN** (1 ev) — Fault em `account.move.read` (`recebimento_views.nf_transferencia_refresh`)
- **WM** (1 ev) — Fault em `recebimento_views.nf_transferencia_refresh`

### Scripts ad-hoc Render Shell / Python interativo (`__main__` / `<stdin>`, mechanism=excepthook) (5)
Execucoes manuais/throwaway — nao sao caminhos da app deployada nem arquivos versionados.
- **W6** (1 ev) — `ImportError: cannot import name 'get_connection'` em `mo_comp.py`
  (script throwaway; nao existe no repo).
- **X2** (2 ev) — `ValueError: Excel file format cannot be determined` em `<stdin>`
  (Python interativo via pipe).
- **X3** (1 ev) — `BadZipFile: File is not a zip file` (`__main__ in <module>`).
- **WZ** (1 ev) — `InFailedSqlTransaction` (`__main__ in <module>`).
- **W9** (1 ev) — `TypeError: 'bool' object is not subscriptable` (`__main__ in <listcomp>`,
  `location=<string>` — codigo inline `exec`/`-c`).

### MEMORY_MCP — transacao SQLAlchemy abortada (1)
- **EG** (3 ev em 48 dias, 3 usuarios) — `Can't reconnect until invalid transaction is
  rolled back` no logger `app.agente.tools.memory_mcp_tool` (culprit `teams.bot_message`).
  **Ja mitigado em codigo**: `memory_mcp_tool.py` (≈linha 444-477) ja tem um helper de
  rollback defensivo ("Sessao abortada detectada — rollback defensivo + re-tenta UMA
  vez com a sessao limpa") que faz `db.session.rollback()` e re-executa. E um log de
  erro (event.type=default), nao crash nao-tratado; 3 eventos em 48 dias = transiente.
  Sem fix trivial adicional no escopo. Documentado, NAO resolvido.

### Ambiente / config de infra (1)
- **WA** (1 ev) — `Failed to init API, possibly an invalid tessdata path: ./` no upload
  de comprovante (OCR tesseract). Config de ambiente do container (tessdata path), nao
  bug de codigo no escopo permitido. Transiente.

### Log de condicao de negocio / dado (2)
- **W7** (1 ev) — ALERTA de sync: produto existe no Odoo mas nao veio na sincronizacao
  (possivel timeout). Log de alerta de negocio, nao crash de codigo.
- **W5** (2 ev) — "Erro ao buscar tabela 16793: 404 Not Found" em
  `tabelas.editar_tabela_frete`. Recurso upstream 404 (tabela inexistente), logado como
  erro. Condicao de dado, nao bug fixavel.

## Metricas

- Issues abertas (unresolved, production) antes: 23
- Issues marcadas resolved nesta execucao: 3 (WB, WD, W4)
- Issues abertas depois: 20
- Reducao: 13.0%
- Arquivos de codigo modificados: 1
  (`.claude/skills/gerindo-carvia/scripts/cotando_subcontrato_carvia.py`)

## Arquivos Modificados

- `.claude/skills/gerindo-carvia/scripts/cotando_subcontrato_carvia.py` — corrigido
  import-path `app.carvia.services.cotacao_service` →
  `app.carvia.services.pricing.cotacao_service` (linhas 24, 52, 108). Fix de W4.

## Verificacao

- `git log -- app/inventario/services/movimentacoes_odoo_service.py` confirmou commit
  `4477faa4d` (2026-05-27 20:41) com mensagem que descreve o fix de WB/WD; codigo em
  disco usa `search_count` + `search_read(offset=...)`.
- `OdooConnection` (`connection.py`): `search_read` aceita `offset` (linha 296),
  `search` so aceita `limit` (linha 310), `search_count` existe (linha 318) — consistente
  com o codigo do service.
- `ast.parse` OK no script editado (`cotando_subcontrato_carvia.py`); nenhuma ocorrencia
  remanescente de `from app.carvia.services.cotacao_service`.
- Confirmado que `pricing/cotacao_service.py` tem `class CotacaoService` (linha 29) e o
  metodo `cotar_subcontrato` (linha 65) usado pelo culprit do evento W4.
