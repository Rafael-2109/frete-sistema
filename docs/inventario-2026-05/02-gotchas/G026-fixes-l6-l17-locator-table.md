<!-- doc:meta
tipo: reference
camada: L3
sot_de: —
hub: docs/inventario-2026-05/02-gotchas/INDEX.md
superseded_by: —
atualizado: 2026-06-03
-->
# G026 — Tabela de fixes L6-L17 (sub-piloto bulk 10 produtos)

> **Papel:** G026 — Tabela de fixes L6-L17 (sub-piloto bulk 10 produtos).

**Data**: 2026-05-18 madrugada
**Origem**: extraído de `99-historia/CHECKPOINT_2026_05_18_SUBPILOTO_FINAL.md` antes do arquivamento
**Status**: TODOS FIXADOS (commit `a8e0d0bb` + commits subsequentes)

---

## Propósito

Tabela de referência rápida para localizar os 12 fixes feitos durante o sub-piloto bulk de 10 produtos (LF, 2026-05-18 madrugada). Cada fix ganhou descrição narrativa em outro gotcha (G001-G023) **mas os ponteiros file:line exatos só estavam neste checkpoint** que foi arquivado.

Use esta tabela quando precisar **navegar rapidamente do sintoma ao código** ou rastrear o histórico de uma decisão arquitetural.

---

## Tabela de fixes

| # | Tema | Sintoma | Fix | Arquivo | Linhas | Gotcha narrativo |
|---|---|---|---|---|---|---|
| L6 | Picking outgoing inter-company | `Empresas incompativeis: 'LF/Estoque' pertence a outra empresa` ao `action_confirm` | `resolver_location_destino(tipo_op, company_destino, company_origem)` mapeia `(origem, tipo_op) → location virtual com company_id=False` | `app/odoo/services/inventario_pipeline_service.py` | 74-148 | [`G006-picking-inter-company-location-virtual.md`](G006-picking-inter-company-location-virtual.md) |
| L7 | Backorder em assigned | `button_validate` valida picking MAS state continua `assigned` (Odoo abre wizard de backorder sem context) | `StockPickingService.validar()` passa `context={'skip_backorder': True, 'picking_ids_not_to_backorder': [picking_id]}` | `app/odoo/services/stock_picking_service.py` | 182-211 | — (decisão D006 §L7) |
| L8 | f5b/f5c/f5d marcavam só 1 ajuste por picking | Picking com 10 ajustes → só 1 ajuste marcava F5b/F5c/F5d, outros 9 ficavam em fase anterior | Helper `_agrupar_por_picking(ajustes) -> Dict[int, List]` + iterar TODOS ajustes do mesmo picking ao marcar fase | `app/odoo/services/inventario_pipeline_service.py` | 500-540 | — (decisão D006 §L8) |
| L9 | f5e re-transmitia mesma NF | Picking com 10 ajustes → Playwright tenta transmitir SEFAZ 10 vezes (mesma invoice). Pode causar rate limit ou double-charge SEFAZ | `invoices_processadas: Dict[int, str]` dentro de `f5e_transmitir_sefaz`. Após transmitir, marca outras linhas da mesma invoice como `SKIP_INV_PROC` sem chamar Playwright | `app/odoo/services/inventario_pipeline_service.py` | 778-870 | — (decisão D006 §L9) |
| L10 | status auditoria excedia VARCHAR(20) | `psycopg2.errors.StringDataRightTruncation: value too long for type character varying(20)` ao gravar status `'SKIPPED_INVOICE_JA_PROCESSADA'` (30 chars) | Status reduzido para `'SKIP_INV_PROC'` (13 chars) | `app/odoo/services/inventario_pipeline_service.py` | (busca por `SKIP_INV_PROC`) | — (caso similar em `EXECUCAO_PRE_ETAPA_CD_2026_05_18.md` Bug 2 — `acao` VARCHAR(20) no `operacao_odoo_auditoria`) |
| L11 | `forcar_qty_done` gerava saldo negativo | tentativa de "forçar qty_done = product_uom_qty" gerava saldo negativo no Odoo (lote tinha menos que demand) | Novo método `ajustar_qty_done_pelo_disponivel` NUNCA infla qty_done além do reservado. Reduz `product_uom_qty` da move para igualar reservado. Pendências retornadas para gerar ajustes complementares | `app/odoo/services/stock_picking_service.py` | 213-280 | — |
| L12 | 1 ajuste agregado vs N quants reais | `ajuste com lote_origem=MIGRAÇÃO qtd_ajuste=-672` falhava porque lote MIGRAÇÃO no Odoo só tinha 52 un. Robô CIEL IT gerava NF com qty parcial | `etapa_b_pickings` consulta `stock.quant` real e distribui demanda total entre lotes disponíveis (FIFO por create_date). Se sobrar `qty_restante > 0`, cria automaticamente ajuste compensatório `INDUSTRIALIZACAO_FB_LF` | `scripts/inventario_2026_05/09_executar_onda1_bulk.py` | 435-540 | [`G009-multi-lote-distribuir-fifo.md`](G009-multi-lote-distribuir-fifo.md) |
| L13 | custo_medio=0 → price_unit=0 → SEFAZ rejeita XML | NF 13150 com `price_unit=0` em 2 linhas. SEFAZ rejeitou: "Falha no Schema XML do lote de NFe" (vUnCom=0 viola schema NFe) | `etapa_b_pickings` busca `product.standard_price` no Odoo antes de criar pickings. Se `custo_medio <= 0`, atualiza com `abs(standard_price)` (negativos viram positivos — erro cadastro Odoo). Default 0.01 se ambos zero | `scripts/inventario_2026_05/09_executar_onda1_bulk.py` | 400-432 | [`G007-custo-zero-rejeita-sefaz.md`](G007-custo-zero-rejeita-sefaz.md), [`G015-protecao-price-zero-automatica.md`](G015-protecao-price-zero-automatica.md) |
| L14 | Conexão Odoo XML-RPC não thread-safe | `http.client.CannotSendRequest: Request-sent` ao usar `ThreadPoolExecutor` em ETAPA A | ETAPA A convertida para sequencial (1 thread). Performance: 5 transferências em ~5s. | `scripts/inventario_2026_05/09_executar_onda1_bulk.py` | 255-330 | — |
| L15 | carregar_ajustes excluía EXECUTADO | Após ETAPA D marcar ajustes como EXECUTADO, ETAPA E não encontrava nenhum SEFAZ-autorizado | `status_filtro=('APROVADO', 'PROPOSTO', 'EXECUTADO')` por default | `scripts/inventario_2026_05/09_executar_onda1_bulk.py` | 122-150 | — |
| L17 | etapa E não filtrava INDUSTRIALIZACAO_FB_LF (sentido invertido) | etapa_e tentava criar entrada FB para NFs FB→LF (sentido oposto) | Filtrar `acao_decidida` no `etapa_e_entrada_fb`: pular `INDUSTRIALIZACAO_FB_LF`, `DEV_FB_LF`, `DEV_CD_LF` | `scripts/inventario_2026_05/09_executar_onda1_bulk.py` | 1194, 1548 | — (referenciado como "G006/L17" nos comentários) |

---

## Tabela de pickings do sub-piloto (referência forense)

| Picking | Name | State | Detalhe |
|---|---|---|---|
| 317294 | LF/LF/SAI/RNA/00003 | done | Saída LF perda (NF 13150) — estoque devolvido |
| 317295 | LF/LF/SAI/RNA/00004 | done | Saída LF perda (NF 608631) — NF ok |
| 317296 | FB/SAI/IND/01553 | cancel | 1ª tentativa FB→LF (empresas incompatíveis location, gotcha L6/G006) |
| 317297 | FB/SAI/IND/01554 | done | Saída FB industr (NF 608629) — estoque saiu corretamente |
| 317299 | FB/IN/13151 | cancel | Entrada FB errada (RecLf 6, sentido invertido) |
| 317303 | LF/RECEB/IND/01355 | done | Devolução do 317294 (estoque LF voltou) |
| 317304 | FB/DEV/00606 | done | DEVOLUÇÃO ERRADA (cancelei NF 608629 por engano) |
| 317305 | FB/DEV/00607 | done | CONTRA-DEVOLUÇÃO (corrigi erro — estoque FB voltou para Em Trânsito) |
| 317306 | LF/IN/01733 | done | ENTRADA MANUAL LF (Em Trânsito Industr → LF/Estoque, 103000037 10.389 kg lote MIGRAÇÃO) |

---

## Ref

- `99-historia/CHECKPOINT_2026_05_18_SUBPILOTO_FINAL.md` — checkpoint original (arquivado)
- `00-decisoes/D006-transferir-quantidade-entre-lotes-nao-renomear.md` — D006 §"Lições aprendidas piloto" tem narrativa de L1-L5 + L6-L8
- `app/odoo/services/inventario_pipeline_service.py` — service principal do pipeline
- `scripts/inventario_2026_05/09_executar_onda1_bulk.py` — bulk wrapper
