# Skill 9 `consultando-quant-odoo` — Validacao

**Status:** 🟡 mín viável (READ ancillary). Estendida em v7 com 2 átomos cross-ref reverso.

## Smoke PROD (2026-05-23 — atomos `listar_quants` + `auditar_pares`)

**Caso:** Dogfood pos-WRITE Skill 1 (104 ajustes negativos).

| Cenario | Comando | Resultado |
|---|---|---|
| Auditoria 104 pares pos-WRITE | `consultar_quants.py --modo quants --pares ...` (via Python direto) | 17 totalmente_zerados + 46 so_indisp + 39 com_saldo_nao_indisp + 2 sem_produto = 104 ✓ |
| Investigacao 4856125 | `consultar_quants.py --cods 4856125 --empresas FB --formato json` | Identificou quants em loc !=Indisp para validar reducoes |

## Smoke PROD v7 (2026-05-24 — atomos NOVOS `listar_move_lines_por_quant` + `listar_pickings_por_quant`)

**Caso:** Caso 71 cods Indisponivel (fluxo 2.6).

| Cenario | Comando | Resultado |
|---|---|---|
| Pickings reservando lote 13206 (3 quants em FB) | `--modo pickings --quant-ids 261590,261594,261598` | 1 picking FB/INT/08022 (Transferencia Interna FB), 3 MLs, 1035.083 un, lote=['13206'], state=assigned. Bate 100% com probe Fase A. |
| Pickings reservando MIGRAÇÃO em FB/Estoque (10 quants) | `--modo pickings --quant-ids 254523,254534,254903,...` | 3 pickings: FB/FB/EMB/11673+11674 (Separação Embalagem, origem MO=FB/OP/MANUAL/01763+01764, 3 MLs centavos) + FB/OUT/01046 (Expedição, DEVOLUcaO LA FAMIGLIA, 3 MLs 890.46 un). Bate 100% com Fase A. |
| Pos-cancel FB/INT/08022 | `--modo pickings --quant-ids 261590,261594,261598` | 0 pickings, reserved=0 nos 3 quants. Confirma fluxo 2.6 caminho A. |

## Cobertura pytest

**19 testes** em `tests/odoo/services/test_stock_quant_query_service.py` (mock-based):
- `listar_move_lines_por_quant`: quant_ids vazio, default states, custom states, sem filtro, domain compound OR para N quants, resolve quant_id via tupla, picking_state batch unico, ML sem picking_id, incluir_move adiciona campos, incluir_picking=False skip read, quantity None defensive, lot_id=False (11 testes).
- `listar_pickings_por_quant`: quant_ids vazio, agrupa 3 MLs em 1 picking (caso 13206), separa mls_sem_picking, ordem assigned-antes-done, enriquece partner/origin/picking_type (caso FB/OUT/01046), zero MLs (8 testes).

**229 verdes totais** (rodado 2026-05-24).

## Gotchas codificados

- **G030** (DESCOBERTO v7): `stock.move.line.quant_id` e' computed `store: False` em Odoo CIEL IT. Cross-ref ML→quant via TUPLA (product_id, lot_id, location_id, company_id). Doc: `docs/inventario-2026-05/02-gotchas/G030-quant-id-em-stock-move-line-eh-computed.md`.
- **G024** (herdado): usar `quantity`, nao `reserved_uom_qty` (Odoo 16/17).

## Scripts SUPERADOS (movidos para `_validados/consultando-quant-odoo/`)

Nenhum por enquanto — Skill 9 e' READ ancillary que cobre subconjunto dos ~33 READ scripts (monitor/, auditoria/, comparar_sot_*, diff_*, relatorio_*, investiga_*). Esses permanecem VIVOS como ad-hoc até pattern individual madurar.

## Limitacoes documentadas

- Atomos previstos sem implementacao (sem demanda atual):
  - `listar_pickings(states, picking_type_ids, partner_ids)` — query INDEPENDENTE de quant_ids.
  - `snapshot_estoque_por_lote(empresa)` — agregado por lote.
  - `saldo_fora_principal(empresa)` — classifica INTERNAL_FORA vs ESTOQUE_RAIZ.
