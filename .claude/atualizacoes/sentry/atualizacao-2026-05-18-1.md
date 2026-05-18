# Atualizacao Sentry — 2026-05-18-1

**Data**: 2026-05-18
**Org**: nacom | **Projeto**: python-flask
**Issues avaliadas**: 57 (unresolved, environment=production)
**Issues corrigidas**: 0
**Issues fora escopo**: 57 (49 infra Odoo + 1 script ad-hoc + 1 design FK + 1 performance N+1 + 6 cascata/server-side)
**Issues ignoradas**: 0

## Resumo

Triagem de 57 issues unresolved em producao. Resultado: **zero fixes aplicaveis nesta janela**.

A massa esmagadora (49 de 57, ~86%) sao falhas de autenticacao Odoo XML-RPC (`ProtocolError 500 Internal Server Error` em `odoo.nacomgoya.com.br/xmlrpc/2/common` ou mensagens `Falha na autenticacao com Odoo` em cascata). Sao **infra externa CIEL IT**, nao acionaveis em codigo local. Memoria `incident_ciel_it_dfe_nfd.md` confirma instabilidade do servidor Odoo desde upgrade v17.0.25.3.18 (30/04).

Os 8 nao-Odoo restantes sao: 1 script ad-hoc one-shot (PYTHON-FLASK-VC ja auto-corrigido por modificacao subsequente do script), 1 ForeignKeyViolation que exige decisao de design (CASCADE vs validacao pre-delete — fora escopo), 1 N+1 Query (performance, requer analise de templates — nao bug tecnico simples), 2 Faults server-side (`Fault 1` no proprio dist-packages do Odoo), 1 mensagem de cascata.

## Issues Corrigidas

Nenhuma.

## Issues Fora de Escopo

### Infraestrutura Externa Odoo CIEL IT (49 issues — ~1.300 eventos)

**Causa raiz unica**: Servidor `odoo.nacomgoya.com.br` retornando HTTP 500 em `/xmlrpc/2/common` ou `authenticate()` retornando UID=False. **Acionavel apenas pela CIEL IT** (provedor do Odoo).

Top 10 por frequencia:

| Issue | Eventos | Culprit / Job |
|-------|---------|---------------|
| PYTHON-FLASK-V5 | 216 | Odoo auth (novo, 1 dia) |
| PYTHON-FLASK-V6 | 172 | Odoo auth (novo, 1 dia) |
| PYTHON-FLASK-FP | 101 | Odoo auth (since 2026-04-14) |
| PYTHON-FLASK-V7 | 56 | Odoo auth |
| PYTHON-FLASK-5C | 48 | verificar lote 3 |
| PYTHON-FLASK-4 | 47 | Contas a Receber |
| PYTHON-FLASK-3 | 39 | sync write_date |
| PYTHON-FLASK-TW | 37 | `pedido_compras_service.backfill_cnpj_via_odoo` |
| PYTHON-FLASK-TY | 36 | Odoo auth |
| PYTHON-FLASK-TJ | 30 | auto-heal CNPJ |

Demais 39 (5B, 6J, GQ, 5V, GS, GN, 5Z, GT, C4, C8, C3, H0, CD, CC, BZ, H2, GV, GR, 5M, 5K, 58, 56, 5P, 5N, 5J, 5H, 5G, 5A, 57, 54, 53, BX, 5W, GP, C5, C0, SX, H7, H3) sao manifestacoes do mesmo problema em diferentes jobs/services (sync carteira, faturamento, pickings, NCs, devolucoes, CTes, contas a pagar/receber, validacao recebimento, etc.).

**Acao recomendada (fora desta triagem)**: criar inhibit rule no Sentry agrupando todas em uma unica alert chain, ou marcar grupo como `ignored untilEscalating` ate CIEL IT estabilizar o XML-RPC. Memoria existente: `memory/incident_ciel_it_dfe_nfd.md`.

### Faults Server-Side (2 issues)

- **PYTHON-FLASK-P5** (5 eventos, since 24d) — `Fault 1` em `account.move.line.search_read` via `app.odoo.utils.connection._do_execute`. Traceback aponta `/usr/lib/python3/dist-packages/odoo/addons/base/controllers/rpc.py:151` — codigo do **servidor Odoo**, nao do nosso cliente XML-RPC. Fora escopo.
- **PYTHON-FLASK-P6** (6 eventos) — mesmo padrao, mesma raiz. Fora escopo.

### Script Ad-Hoc One-Shot (1 issue)

- **PYTHON-FLASK-VC** (2 eventos, 17-18/05) — `DataError StringDataRightTruncation` em `scripts/migrations/motos_assai_backfill_match_nfs_2026_05_17.py::parte2_delete_chassis_lixo`. Coluna `assai_recibo_item.tipo_divergencia` e `VARCHAR(30)`. Inspecao do codigo atual (linha 192) mostra `'LIMPO_BACKFILL_2026_05_17'` (25 chars) — **valor ja cabe**. Eventos sao das execucoes iniciais antes da correcao no proprio script. Backfill one-shot do dia 17/05 (releases `67327f0d` e `1b61fdad`), nao parte do runtime de producao. Fora escopo.

### Design / Regra de Negocio (1 issue)

- **PYTHON-FLASK-VD** (1 evento, 18/05 01:53) — `IntegrityError ForeignKeyViolation` ao tentar DELETE em `assai_pedido_venda` com `assai_separacao.pedido_id` referenciando. FK em `app/motos_assai/models/separacao.py:24` foi declarada **sem `ondelete='CASCADE'`** deliberadamente (separacao precisa ser cancelada antes do pedido ser deletado — audit trail). Corrigir exigiria: (a) migration para adicionar CASCADE (perde audit trail), OU (b) validacao pre-delete no servico que tentou apagar. Ambos sao **decisao de design**, fora escopo de bug-fix simples. Apenas 1 evento — registrar e aguardar reincidencia.

### Performance (1 issue)

- **PYTHON-FLASK-S9** (6 eventos, 2 usuarios) — N+1 Query em `tabelas.listar_todas_tabelas`. `event.type=transaction`, `level=info`, `http.status_code=200` — **nao e erro**, e alerta de performance. Causa provavel: template `tabelas/listar_todas_tabelas.html` itera sobre 20 tabelas/pagina acessando relationships lazy. Fix exige `selectinload(TabelaFrete.transportadora)` no `.paginate()` (linha 612) ou analise de qual relationship dispara. Performance tuning, nao bug tecnico simples — fora escopo.

### Cascata (1 issue)

- **PYTHON-FLASK-61** (8 eventos) — "Sincronização com falhas graves - apenas 11/20 módulos OK" — mensagem agregada quando >= N modulos falham por Odoo auth. Cascata downstream de PYTHON-FLASK-V5/V6/etc, nao causa propria.

## Metricas

- Issues abertas antes: 57 (production)
- Issues abertas depois: 57
- Reducao: 0% (nenhum fix aplicavel)
- Eventos cobertos por causa-raiz unica (Odoo auth + Faults server-side): ~1.310 / ~1.500 (~87%)

## Observacoes para proxima execucao

1. **Bloquear ruido Odoo**: Sentry deveria ter rule de agregacao para `ProtocolError 500 odoo.nacomgoya.com.br` — 49 issues distintas do mesmo root cause poluem a fila. Sugestao: marcar grupo como `ignored untilEscalating` em massa quando CIEL IT confirmar correcao.
2. **PYTHON-FLASK-VD**: Se reincidir, considerar adicionar pre-check em servico que deleta pedido (validar absencia de `assai_separacao` ativa) e/ou retornar 409 com mensagem clara em vez de propagar IntegrityError.
3. **PYTHON-FLASK-S9**: Quando houver janela para perf tuning, aplicar `selectinload(TabelaFrete.transportadora)` em `app/tabelas/routes.py:444` (`TabelaFrete.query.join(Transportadora)` faz join mas template pode estar acessando outra relationship lazy).
4. **Script `motos_assai_backfill_match_nfs_2026_05_17.py`**: One-shot ja executado — pode ser arquivado em `scripts/migrations/_archive/` quando convier.
