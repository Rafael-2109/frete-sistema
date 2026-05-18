# D004 — Renomear lote + transferir apenas a diferença líquida

**Data**: 2026-05-17
**Status**: parcialmente superseded por D006 (2026-05-18) — item "Renomear lote" reinterpretado como TRANSFERIR quantidade entre lotes via inventory adjustment (sem renomeio). Demais conceitos (consolidacao + diferenca liquida + custo medio) seguem validos.
**Fonte**: instrucao usuario apos analise caso 210030325 LF

> **VEJA TAMBEM**: `D006-transferir-quantidade-entre-lotes-nao-renomear.md` — substitui o item 1 desta decisao (renomeio → transferencia).

---

## Contexto

Versao anterior do F7.3 gerava 1 diff por quant Odoo. Caso real:

**Cod 210030325 LF (Embalagem, tipo=2)**
- Odoo: 4 lotes (vazio, 24715, 3009/24, MIGRACAO) totalizando 114.332 un
- Inv: 1 lote (26014) totalizando 82.300 un — lote nao existe no Odoo

**Versao anterior gerava 5 ajustes**:
- 4 PERDA_LF_FB (uma por lote Odoo, todas com qty=0 no inv) totalizando -114.332 un
- 1 INDUSTRIALIZACAO_FB_LF (lote 26014 sem contraparte Odoo) +82.300 un
- Net: -32.032 un, mas via 5 NFs separadas (4 perdas + 1 remessa)

Errado fiscalmente: implica devolver 114k e mandar 82k de volta. Realidade: 82.300 un EXISTEM fisicamente, so estao em "lote errado" no Odoo.

---

## Decisao

Para LF (e generalizavel para FB/CD), quando ha saldo nos DOIS lados (Odoo e inventario) com lotes diferentes:

1. **Renomear lotes Odoo ate cobrir saldo inv** (FIFO por quant_id ou prioridade MIGRACAO primeiro). Resultado: lotes Odoo passam a usar o nome do lote inventariado.
2. **Diferenca liquida apenas** (`|odoo_total - inv_total|`):
   - Se Odoo > Inv (sobra fantasma): UMA NF de saida (PERDA_LF_FB ou similar) so com a diferenca, lote_destino na FB = `MIGRACAO`
   - Se Inv > Odoo (falta): UMA NF de entrada (INDUSTRIALIZACAO_FB_LF) so com a diferenca, lote_destino na LF = lote inv

3. **Custo unitario do RENOMEAR e da diferenca**:
   - Quando o lote alvo (lote inv) nao tem custo no Odoo (lote novo), usar **custo medio dos outros lotes do mesmo cod_produto** (media ponderada por quantity de `stock.quant.value/quantity`).

---

## Exemplo aplicado: 210030325 LF

| Operacao | qty | lote_origem | lote_destino | custo unit | valor R$ |
|---|---|---|---|---|---|
| RENOMEAR_LOTE (parcial MIGRACAO) | 35.188 | MIGRACAO | 26014 (LF) | 0,6434 | 22.638,01 |
| RENOMEAR_LOTE (vazio) | 39.216 | (vazio) | 26014 (LF) | 0,6434 | 25.231,57 |
| RENOMEAR_LOTE (24715) | 5.604 | 24715 | 26014 (LF) | 0,6434 | 3.605,61 |
| RENOMEAR_LOTE (3009/24) | 2.292 | 3009/24 | 26014 (LF) | 0,6434 | 1.474,67 |
| PERDA_LF_FB | -32.032 | MIGRACAO (residuo) | MIGRACAO (FB) | 0,6434 | 20.605,38 |

Total RENAME: 82.300 (= saldo inv). Diferenca: 32.032 = `114.332 - 82.300`. 1 NF de saida fiscal (PERDA) em vez de 4.

---

## Generalizacao (a aplicar progressivamente)

Mesma logica para:
- **FB tipo[4] vs CD tipo[4]**: rename interno + transferencia da diferenca
- **CD tipo[1,2,3] vs FB tipo[1,2,3]**: idem
- Quando lote alvo nao existe no destino, usar lote MIGRACAO (ver D005)

---

## Impacto no codigo

- `scripts/inventario_2026_05/03_confrontar_inv_vs_odoo.py:confrontar_company()` — refatorar logica de agregacao para LF (cid=5) inicialmente; depois generalizar
- `app/odoo/models/ajuste_estoque_inventario.py` — adicionar coluna `lote_destino`
- `scripts/inventario_2026_05/04_propor_ajustes.py:cmd_propor()` — preencher `lote_destino` no insert
- Migration: `scripts/migrations/2026_05_17_add_lote_destino_ajuste.{py,sql}`
