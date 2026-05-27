# Odoo — Guia de Desenvolvimento

**63 arquivos** | **~28.8K LOC** | **Atualizado**: 25/05/2026

Integracao bidirecional com Odoo ERP via XML-RPC. API-only: sem models SQLAlchemy proprios — le/escreve models de outros modulos (8+). Modulo mais consumido do sistema (37+ arquivos externos importam).

> Subpacote `estoque/` (orquestrador WRITE + READ ao vivo): 13 arquivos / ~6.7K LOC. Guia completo: `app/odoo/estoque/CLAUDE.md`.

---

## Estrutura

```
app/odoo/
  ├── __init__.py              # Re-exporta connection, mappers, services principais
  ├── routes_circuit_breaker.py # Blueprint p/ status do circuit breaker
  ├── config/
  │   └── odoo_config.py       # 1 config (constantes Odoo: URL, DB, UID)
  ├── constants/               # 4 modulos de constantes-dado
  │   ├── locations.py             # COMPANY_LOCATIONS (FB=8, CD=32, LF=42)
  │   ├── operacoes_fiscais.py     # MATRIZ_INTERCOMPANY (D002 — operacoes NACOM)
  │   ├── picking_types.py         # IDs de picking_type por empresa/operacao
  │   └── ids_diversos.py          # IDs fixos auxiliares (categorias, tags)
  ├── models/                  # 2 models SQLAlchemy (excecao a regra "sem models proprios")
  │   ├── ajuste_estoque_inventario.py  # Ciclo de inventario (1 linha por divergencia)
  │   └── operacao_odoo_auditoria.py    # Auditoria polimorfica de operacoes Odoo
  ├── routes/
  │   └── sincronizacao_integrada.py  # 1 rota (sync manual + fallback + pedido individual)
  ├── services/                # 21 services
  │   ├── carteira_service.py              # Sync sale.order → CarteiraPrincipal/Separacao (~142K)
  │   ├── faturamento_service.py           # Sync account.move → FaturamentoProduto (~90K)
  │   ├── importacao_fallback_service.py   # Fallback quando sync principal falha (~69K)
  │   ├── pedido_compras_service.py        # Sync purchase.order → PedidoCompras (~46K)
  │   ├── ajuste_sincronizacao_service.py  # Ajustes pos-sync (saldos, alertas) (~44K)
  │   ├── cte_service.py                   # Sync l10n_br_fiscal.document CTe (~39K)
  │   ├── requisicao_compras_service.py    # Sync purchase.request → RequisicaoCompras (~32K)
  │   ├── requisicao_compras_service_otimizado.py  # Versao otimizada (~27K)
  │   ├── entrada_material_service.py      # Sync stock.picking → MovimentacaoEstoque (~27K)
  │   ├── alocacao_compras_service.py      # Sync purchase.request.allocation (~23K)
  │   ├── sincronizacao_integrada_service.py # Orquestra sync completa (fat→cart) (~19K)
  │   ├── pedido_sync_service.py           # Sync individual de pedido (~19K)
  │   ├── inventario_pipeline_service.py   # ⚠️ LEGADO MINERADO (1346 LOC) — fonte do orchestrator novo em `app/odoo/estoque/orchestrators/faturamento_pipeline.py` (Skill 8 v18). Manter por enquanto (callers legados). Arquivar v22+ pos-canary REAL PROD.
  │   ├── stock_picking_service.py         # SHIM 2026-05-24 — re-exporta de app/odoo/estoque/scripts/picking.py (Skill 5)
  │   ├── stock_lot_service.py             # Operacoes stock.lot (criar/buscar com fallback like)
  │   ├── stock_internal_transfer_service.py # SHIM 2026-05-24 — re-exporta de app/odoo/estoque/scripts/transfer.py (Skill 2)
  │   ├── stock_quant_adjustment_service.py # SHIM 2026-05-23 — re-exporta de app/odoo/estoque/scripts/quant.py (Skill 1)
  │   ├── stock_mo_service.py              # SHIM 2026-05-24 — re-exporta de app/odoo/estoque/scripts/mo.py (Skill 4 — cancelar MO)
  │   ├── transferencia_saldo_codigo_service.py # Transferencia entre codigos de produto (interna)
  │   ├── pre_etapa_estoque_service.py     # Pre-etapa CD/FB para minimizar NF (D007)
  │   └── indisponibilizacao_estoque_service.py # Bloqueio temporario de lotes em ajuste
  ├── utils/                   # 12 utils
  │   ├── cached_lookups.py        # Cache de lookups frequentes (metodos entrega, etc.) (~267 LOC)
  │   ├── carteira_mapper.py       # Mapeia sale.order → dict CarteiraPrincipal (~21K)
  │   ├── connection.py            # OdooConnection XML-RPC + timeout adaptativo (~16K)
  │   ├── cte_xml_parser.py        # Parser XML de CTe (~21K)
  │   ├── dfe_utils.py             # Helpers DFe (busca, validacao, tipos) (~15K)
  │   ├── faturamento_mapper.py    # Mapeia account.move → dict FaturamentoProduto (~15K)
  │   ├── safe_connection.py       # Conexao com retry/fallback (~15K)
  │   ├── circuit_breaker.py       # Circuit breaker para chamadas Odoo (~12K)
  │   ├── pedido_cliente_utils.py  # Busca pedido cliente no Odoo (~9K)
  │   ├── metodo_entrega_utils.py  # Busca metodo de entrega Odoo (~8K)
  │   ├── gtin_validator.py        # Valida GTIN (cEAN) p/ SEFAZ NF-e; barcode invalido → cstat=225 (G035) (~116 LOC)
  │   └── sanitizacao_faturamento.py # Sanitiza dados de faturamento (~4K)
  ├── jobs/                    # 0 jobs (vazio — jobs ficam no scheduler)
  ├── docs/                    # 3 docs internos
  │   ├── campos_minimos_sale_order.md
  │   ├── mapeamento_campos_odoo_carteira.md
  │   └── triggers_sale_order.md
  └── estoque/                 # Subpacote ORQUESTRADOR (skills WRITE + READ ao vivo, 2026-05-22+)
      │                        # 13 arquivos / ~6.7K LOC. Ver app/odoo/estoque/CLAUDE.md
      ├── __init__.py / _cli_utils.py / _utils.py
      ├── scripts/             # Atomos por skill (Skills 1, 2, 2.4, 5, 4, 6, 9)
      │   ├── quant.py             # Skill 1 — ajustar_quant (✅ MATURADA)
      │   ├── transfer.py          # Skill 2 — transferindo-interno-odoo
      │   ├── reserva.py           # Skill 2.4 — operando-reservas-odoo
      │   ├── picking.py           # Skill 5 — operando-picking-odoo
      │   ├── mo.py                # Skill 4 — operando-mo-odoo
      │   ├── pre_etapa.py         # Skill 6 — planejando-pre-etapa-odoo
      │   └── consulta_quant.py    # Skill 9 — consultando-quant-odoo (READ-only)
      ├── orchestrators/       # Macros C3 (compoem atomos em fluxos)
      │   └── pre_etapa_executor.py
      └── fluxos/              # Folhas de fluxo Markdown (2.1, 2.2, 2.4, 2.5, 2.6, 2.9, 3.1, 4.1)
```

---

## Patterns de Desenvolvimento

### P1: Anti-Detach — Extrair Dados ORM Antes de Operacoes Longas

**Problema**: Operacoes Odoo demoram 60-180s. SQLAlchemy expira a sessao → `"Instance <X> is not bound to a Session"`.

**Solucao**: Extrair valores simples (int, str) de objetos ORM ANTES da operacao longa. No final, re-buscar com `db.session.get()`.

```python
# ANTES da operacao longa (CORRETO)
frete_fatura_id = frete.fatura_frete_id
frete_numero_fatura = frete.fatura_frete.numero_fatura if frete.fatura_frete else None

# ... operacao Odoo de 180s ...

# DEPOIS: re-buscar com sessao nova
frete = db.session.get(Frete, frete_id)
frete.odoo_invoice_id = invoice_id
```

**Fonte**: `app/fretes/services/lancamento_odoo_service.py:728-736`, `app/fretes/services/lancamento_despesa_odoo_service.py`

### P2: Fire-and-Polling para Operacoes > 30s

**Problema**: HTTP timeout (~30s) < duracao real (5-10 min).

**Solucao**: Enqueue RQ → Worker processa → Redis armazena progresso → Frontend polls.

1. `enqueue_job(func, *args, queue_name='recebimento', timeout='15m', retry=Retry(max=3, interval=[30,120,480]))`
2. Worker executa N passos, atualiza Redis: `redis.setex(f'progresso:{id}', TTL, json.dumps({etapa, total, percentual}))`
3. Frontend polls: `GET /status/<id>` a cada 2-5s
4. Lock Redis (`SET nx, ex=1800`) evita duplicacao

**Quando usar**: Qualquer operacao Odoo com multiplos writes sequenciais (ex: criar PO + linhas + impostos + confirmar + criar invoice + confirmar).

**Fonte**: `app/recebimento/services/recebimento_fisico_service.py:482-497`, `app/recebimento/workers/recebimento_lf_jobs.py:28-53`

### P3: Timeout Adaptativo com Reconnect

**Problema**: `socket.setdefaulttimeout()` so afeta sockets NOVOS. Mudar timeout sem reconnect nao tem efeito.

**Solucao**: `timeout_override` em `execute_kw()` faz: `self._models = None` (forca reconnect) → `setdefaulttimeout(novo)` → executa → `finally: restaura timeout + self._models = None`.

- Default: 90s
- Override maximo: 180s (ETAPA 6 do lancamento de frete)
- NUNCA reduzir abaixo de 30s

**Fonte**: `app/odoo/utils/connection.py:156-236`

### P4: Batch Fan-Out (N Queries → Join em Memoria)

**Problema**: Odoo XML-RPC nao suporta JOINs complexos.

**Solucao**:
1. Coletar TODOS os IDs de uma colecao: `set()`
2. 1 batch read: `search_read([('id', 'in', list(ids))])`
3. Dict cache: `{f['id']: f for f in faturas}`
4. JOIN em memoria usando os dicts

```python
# Faturamento: 6 queries batch → 6 dicts → join em memoria
cache_faturas = {f['id']: f for f in faturas}
cache_clientes = {c['id']: c for c in clientes}
cache_produtos = {p['id']: p for p in produtos}
# ... processar usando caches
```

**Anti-pattern**: N+1 queries individuais (100 pedidos x 6 queries = 600 chamadas → 6 com batch).

**Fonte**: `app/odoo/services/faturamento_service.py:83-198`, `app/odoo/services/carteira_service.py` (batch de 100 pedidos)

### P5: Checkpointing — Commit entre Fases Independentes

**Problema**: Sync completa tem 3+ fases. Se fase posterior falha, fases anteriores devem persistir.

**Solucao**: `db.session.commit()` ENTRE fases. Exemplo: sync integrada commita faturamento + status ANTES de iniciar carteira.

**Regra**: SEMPRE faturamento primeiro, depois carteira. Inverter causa perda de saldos.

**Fonte**: `app/odoo/services/sincronizacao_integrada_service.py:70-117`

### P6: Retomada de Processo — Verificar Estado Antes de Recriar

**Problema**: Processo de 16 etapas falhou na etapa 11. Reexecutar nao deve recriar PO (etapa 6).

**Solucao**: `_verificar_lancamento_existente()` busca PO/Invoice existentes no Odoo ANTES de iniciar. Retorna `continuar_de_etapa` (0 = novo, 7+ = retomar).

**Campos persistidos entre etapas**: `dfe_id`, `purchase_order_id`, `invoice_id` — em variaveis locais (nao ORM, ver P1).

**Fonte**: `app/fretes/services/lancamento_odoo_service.py:326-357`

### P7: Commit Antes de Operacao Longa ao Odoo

**Problema**: Manter conexao DB aberta durante 180s de chamada Odoo esgota o pool.

**Solucao**: `db.session.commit()` ANTES de `execute_kw()` com timeout longo. Libera a conexao para outros processos.

**Fonte**: `app/fretes/services/lancamento_odoo_service.py:1509-1512,1630-1633`

---

## Gotchas

| Gotcha | Detalhe | Fonte |
|--------|---------|-------|
| `False` do Odoo ≠ `None` Python | many2one retorna `[id, name]` ou `False`. Converter `False` → `None` | `dfe_utils.py:424-426` |
| CB so conta erros especificos | Keywords: `timeout`, `timed out`, `connection refused`, `connection reset`. Erros de negocio NAO abrem circuit | `circuit_breaker.py:161-170` |
| Incoterm RED muda endereco | Se incoterm = `[RED]` ou ID 16 → endereco vem de `carrier_id/l10n_br_partner_id`, NAO do `partner_shipping_id` | `carteira_mapper.py:321-406` |
| Prefixos Odoo hardcoded | `is_pedido_odoo()` verifica `VSC`, `VCD`, `VFB`. Nova empresa = atualizar `carteira_service.py:64` | `carteira_service.py:40-65` |
| Socket timeout e GLOBAL | `setdefaulttimeout()` afeta TODAS conexoes do processo (nao so Odoo) | `connection.py:60,78,191` |
| Quase sem models proprios | Modulo ESCREVE em 8+ models de outros modulos. Excecao em `models/`: `AjusteEstoqueInventario` e `OperacaoOdooAuditoria` (inventario 2026-05) | Todos os services |
| Imports LAZY obrigatorios | Models de outros modulos importados DENTRO dos metodos (evita circular import) | Todos os services |
| Ordem de sync | SEMPRE faturamento primeiro, carteira depois. Inverter perde saldos | `sincronizacao_integrada_service.py:70-106` |
| l10n_br _compute stale via XML-RPC | Campos `nfe_infnfe_*` NAO recomputados quando invoice criada via robo → SEFAZ 225. Somente UI (Playwright) forca recomputacao | `app/recebimento/services/playwright_nfe_transmissao.py`, GOTCHAS.md |
| Odoo SPA: NUNCA networkidle | Long-polling mantem conexao aberta. Usar `domcontentloaded` + `wait_for_selector` | `app/recebimento/services/playwright_nfe_transmissao.py:444` |
| IDs de UI frageis | `menu_id=124`, `action=243` mudam se Odoo reinstalar. Preferir URL minima sem eles | IDS_FIXOS.md secao "IDs de UI" |

---

## Interdependencias

| Importa de | O que | Cuidado |
|-----------|-------|---------|
| `app/carteira/models.py` | `CarteiraPrincipal`, `PreSeparacaoItem`, `SaldoStandby` | Lazy (dentro de metodos). 5+ services |
| `app/separacao/models.py` | `Separacao` | Lazy. Usado em carteira_service, ajuste_sync, routes |
| `app/faturamento/models.py` | `FaturamentoProduto`, `RelatorioFaturamentoImportado` | Lazy. 4 services |
| `app/faturamento/services/` | `ProcessadorFaturamento` | Lazy. Chamado apos sync faturamento |
| `app/manufatura/models.py` | `RequisicaoCompras`, `PedidoCompras`, `HistoricoRequisicaoCompras`, `HistoricoPedidoCompras` | Top-level import nos services de compras |
| `app/fretes/models.py` | `ConhecimentoTransporte`, `Frete` | Top-level import em cte_service |
| `app/estoque/models.py` | `MovimentacaoEstoque` | Top-level em entrada_material_service e faturamento_service |
| `app/embarques/models.py` | `EmbarqueItem` | Top-level em faturamento_service |
| `app/custeio/models.py` | `CustoConsiderado`, `CustoFrete`, `ParametroCusteio`, `RegraComissao` | carteira_service (custeio integrado) |
| `app/producao/models.py` | `CadastroPalletizacao` | Lazy. 3 services (palletizacao) |
| `app/recebimento/models.py` | `ValidacaoFiscalDfe`, `ValidacaoNfPoDfe` | Lazy em dfe_utils |
| `app/recebimento/services/` | `validacao_ibscbs_service` | Lazy em cte_service |
| `app/utils/timezone.py` | `agora_utc_naive`, `odoo_para_local`, `agora_utc` | Todos os services e utils |
| `app/utils/database_helpers.py` | `retry_on_ssl_error`, `ensure_connection` | carteira_service (resiliencia DB) |
| `app/utils/file_storage.py` | `get_file_storage` | cte_service, entrada_material_service (PDFs) |
| `app/utils/redis_cache.py` | `RedisCache` | metodo_entrega_utils (cache de metodos entrega) |

| Exporta para | O que | Cuidado |
|-------------|-------|---------|
| `app/recebimento/` (33 imports) | `get_odoo_connection`, `dfe_utils`, `CTeXMLParser`, services de compras | Maior consumidor. Lazy em quase todos |
| `app/financeiro/` (25 imports) | `get_odoo_connection` | Todos lazy (dentro de metodos) |
| `app/scheduler/` (23 imports) | Todos os 7 services principais | Sync incremental definitiva (steps 1-8) |
| `app/pallet/` (5 imports) | `get_odoo_connection` | Lazy. 4 services |
| `app/manufatura/` (4 imports) | `PedidoComprasServiceOtimizado`, `AlocacaoComprasServiceOtimizado`, `RequisicaoComprasService` | Top-level em routes |
| `app/fretes/` (3 imports) | `get_odoo_connection`, `CteService` | lancamento_odoo_service + cte_routes |
| `app/pedidos/` (4 imports) | `get_odoo_connection`, `ODOO_CONFIG` | Lazy |
| `app/portal/` (3 imports) | `buscar_pedido_cliente_odoo` | pedido_cliente_utils |
| `app/comercial/` (2 imports) | `buscar_pedidos_cliente_lote`, `buscar_metodos_entrega_lote` | pedido_service |
| `app/devolucao/` (2 imports) | `get_odoo_connection` | reversao_service, nfd_service |
| `app/carvia/` (1 import) | `CTeXMLParser` | Classe pai de CTeXMLParserCarvia |
| `app/faturamento/` (1 import) | `importar_faturamento_odoo` | Lazy em routes.py |
| `app/integracoes/` (1 import) | `FaturamentoService` | tagplus importador_v2 |
| `app/custeio/` (1 import) | `CarteiraService` | custeio_routes |
| `app/__init__.py` | `sync_integrada_bp`, `circuit_breaker_bp` | Registro de blueprints |

---

## Subpacote `estoque/` — orquestrador Odoo (skills WRITE)

A partir de 2026-05-22, todas as operacoes de ESCRITA de estoque no Odoo (ajuste quant, transferencia interna, cancelar reservas, etc.) migraram para o subpacote `app/odoo/estoque/`. Os arquivos antigos em `services/stock_*_service.py` agora sao SHIMs que re-exportam. Detalhes completos: **`app/odoo/estoque/CLAUDE.md`** (constituicao do orquestrador).

### Skills L2 atômicas (1 objeto Odoo cada — catálogo principal)

| Skill | Service (novo) | SHIM antigo | Status |
|-------|----------------|-------------|--------|
| `ajustando-quant-odoo` | `app/odoo/estoque/scripts/quant.py` | `services/stock_quant_adjustment_service.py` | ✅ MATURADA |
| `transferindo-interno-odoo` | `app/odoo/estoque/scripts/transfer.py` | `services/stock_internal_transfer_service.py` | 🟡 v10 (Modo C + distribuir_para_indisponivel helper validado 5 cods PROD; FIX D-OPS-5 v14b) |
| `operando-reservas-odoo` | `app/odoo/estoque/scripts/reserva.py` | — | 🟡 v7+ (5 átomos: cirurgia, cancelamento, unreserve, find_orphan_mls, zerar_residual) |
| `operando-picking-odoo` | `app/odoo/estoque/scripts/picking.py` | `services/stock_picking_service.py` | 🟡 v15a (6 átomos · 61 pytest · G019/G020 fechada · 3 átomos inter-company para ETAPA F) |
| `operando-mo-odoo` | `app/odoo/estoque/scripts/mo.py` | `services/stock_mo_service.py` (preventivo) | 🟡 v5 (guard G-MO-01 furo contábil; idempotência action_cancel validada) |
| `escriturando-odoo` ⚠️ V1 STRICT | `app/odoo/estoque/scripts/escrituracao.py` | — | 🟡 V1 LIVE v17.5 — **antipadrão AP1/AP4 documentado em `app/odoo/estoque/CLAUDE.md §6.5` para refator v19+** (Skill 7 ABRANGENTE) |
| `consultando-quant-odoo` (READ) | `app/odoo/estoque/scripts/consulta_quant.py` | — | 🟡 v7+ (3 modos: quants/move-lines/pickings — fluxo 2.6) |

### Orchestrators C3 macros (compõem skills L2 — NÃO são skills L2 atômicas, ver `estoque/CLAUDE.md §3.1`)

| Orchestrator | Service | SHIM antigo | Status |
|--------------|---------|-------------|--------|
| `faturando-odoo` (Skill 8) | `app/odoo/estoque/orchestrators/faturamento_pipeline.py` + SKILL.md fachada em `.claude/skills/faturando-odoo/SKILL.md` | `services/inventario_pipeline_service.py` (1346 LOC — fonte minerada, manter até v22+) | 🟡 PIPELINE A-F + RECOVERY LIVE v18 (72 pytest · smoke PROD dry-run OK) |
| `planejando-pre-etapa-odoo` (Skill 6) | `app/odoo/estoque/scripts/pre_etapa.py` + `orchestrators/pre_etapa_executor.py` | — | 🟡 v9 (5 modos CLI: planejar/propor/listar/aprovar/executar-onda) |

### Sub-skill PRE-FLIGHT

| Sub-skill | Service | Status |
|-----------|---------|--------|
| `auditando-cadastro-fiscal-odoo` | `app/odoo/estoque/scripts/cadastro_fiscal_audit.py` | 🟡 V1 'inventario' (cobre G017+G018+G035+G014 + D-OPS-2/3; 14 pytest; delegada pela Skill 8) |

Subagente orquestrador: `.claude/agents/gestor-estoque-odoo.md`. Folhas de fluxo: `app/odoo/estoque/fluxos/` (galho 2/3/4 escritos; galho 1 ⬜ pendente refator v19+).

> **⭐ ESCUDO contra desvios reincidentes**: `app/odoo/estoque/PROTECAO_PROXIMA_SESSAO.md` (LEITURA OBRIGATÓRIA antes de tocar skills/orchestrators do estoque).

---

## References

| Preciso de... | Documento |
|---------------|-----------|
| IDs fixos (companies, journals, pickings) | `.claude/references/odoo/IDS_FIXOS.md` |
| Gotchas operacionais (timeouts, campos) | `.claude/references/odoo/GOTCHAS.md` |
| Campos por modelo Odoo | `.claude/references/odoo/MODELOS_CAMPOS.md` |
| Padroes avancados (auditoria, batch, locks) | `.claude/references/odoo/PADROES_AVANCADOS.md` |
| Pipeline recebimento de compras (fases 1-4) | `.claude/references/odoo/PIPELINE_RECEBIMENTO.md` |
| Pipeline recebimento LF (37 etapas, Playwright) | `.claude/references/odoo/PIPELINE_RECEBIMENTO_LF.md` |
| Conversao UoM | `.claude/references/odoo/CONVERSAO_UOM.md` |
| Campos de tabelas locais | `.claude/skills/consultando-sql/schemas/tables/{tabela}.json` |
