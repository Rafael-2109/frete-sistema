<!-- doc:meta
tipo: explanation
camada: L3
sot_de: —
hub: docs/inventario-2026-05/00-decisoes/INDEX.md
superseded_by: —
atualizado: 2026-06-03
-->
# D004 — Renomear lote + transferir apenas a diferença líquida

> **Papel:** D004 — Renomear lote + transferir apenas a diferença líquida.

## Indice

- [Contexto](#contexto)
- [Decisao](#decisao)
- [Exemplo aplicado: 210030325 LF](#exemplo-aplicado-210030325-lf)
- [Generalizacao 2026-05-18 (apos piloto OK)](#generalizacao-2026-05-18-apos-piloto-ok)
- [Impacto no codigo](#impacto-no-codigo)

**Data**: 2026-05-17
**Status**:
- Item 1 (renomeio): superseded por D006 (2026-05-18) — substituido por TRANSFERIR quantidade via inventory adjustment.
- Item 2 (diferenca liquida) + Item 3 (custo medio): validos.
- **2026-05-18 fim do dia: GENERALIZADO** — logica aplicada em TODAS as
  companies (LF cid=5, FB cid=1, CD cid=4). Antes restrito a LF.

**Fonte**: instrucao usuario apos analise caso 210030325 LF +
generalizacao apos piloto OK.

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

## Generalizacao 2026-05-18 (apos piloto OK)

**Aplicada para todas as 3 companies em escopo do INVENTARIO_2026_05**:
- **LF (cid=5)**: industrializacao (entrada FB→LF), perda (saida LF→FB),
  dev-industrializacao (FB↔LF)
- **FB (cid=1)**: transf-filial (FB↔CD), industrializacao saida (FB→LF),
  dev-industrializacao (FB↔LF)
- **CD (cid=4)**: transf-filial (CD↔FB), dev-industrializacao (CD↔LF)

**Regra de `lote_destino` por acao** (recalculada em `04_propor_ajustes.py:cmd_propor`
a partir da acao final, mais autoritativa que o default do script 03):

| Acao | lote_destino |
|---|---|
| `RENOMEAR_LOTE` (=TRANSFERIR D006) | `lote_inventariado` (lote alvo) |
| `PERDA_LF_FB` | `MIGRACAO` (D005, consolidador FB) |
| `TRANSFERIR_CD_FB` | `MIGRACAO` (D005, consolidador FB) |
| `TRANSFERIR_FB_CD` | `lote_inventariado` (lote inv na CD) |
| `INDUSTRIALIZACAO_FB_LF` | `lote_inventariado` (lote inv na LF) |
| `DEV_*` (qualquer direcao) | `lote_inventariado` (lote inv no destino) |
| `INDISPONIBILIZAR_*` | `lote_odoo` (informacional) |

---

## Impacto no codigo

- `scripts/inventario_2026_05/03_confrontar_inv_vs_odoo.py:confrontar_company()` — bloco D004 aplicado a TODAS as companies (removido `if cid == 5`)
- `scripts/inventario_2026_05/04_propor_ajustes.py:cmd_propor()` — `lote_destino` recalculado por acao (override do diff)
- `app/odoo/models/ajuste_estoque_inventario.py` — colunas `lote_origem` + `lote_destino` (ja existem)
- Migration: `scripts/migrations/2026_05_17_add_lote_destino_ajuste.{py,sql}` (ja em build.sh item 22, aplicada em prod)
