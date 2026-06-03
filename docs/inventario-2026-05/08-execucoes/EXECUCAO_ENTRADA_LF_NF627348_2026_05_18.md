<!-- doc:meta
tipo: scratch
camada: L3
sot_de: —
hub: docs/inventario-2026-05/08-execucoes/INDEX.md
superseded_by: —
atualizado: 2026-06-03
-->
# Execução: Entrada manual LF da NF 627348 (PEPINO industrializacao)

**Data**: 2026-05-18 08:39 UTC
**Executado por**: Claude Code sessao 2 manha + autorizacao Rafael
**Contexto**: NF 627348 RPI/2026/00202 FB→LF industrializacao SEFAZ OK
deixou 168.108 un PEPINO em "Em Trânsito (Industrialização)" sem entrada
fisica na LF. Padrao L17: sentido FB→X requer entrada manual no destino.
**Snapshot auditoria**: `/tmp/auditoria_entrada_lf_nf627348.json`

---

## 1. Picking criado

**id=317316 | name=LF/IN/01734 | state=done | date_done=2026-05-18 11:39:49**

| Campo | Valor |
|---|---|
| picking_type_id | 19 (`LF: Recebimento (LF)`) |
| location_id | 26489 (`Estoque Virtual/Em Transito (Industrialização)`) |
| location_dest_id | 42 (`LF/Estoque`) |
| origin | `INV-INVENTARIO_2026_05-ENTRADA-LF-NF627348` |
| company_id | 5 (LA FAMIGLIA - LF) |

Move:
- product: 103000011 PEPINO IND (id=27690)
- quantity: 168.108 un
- lot_name: `INV-103000011-20260518`
- from: Em Transito Industr → to: LF/Estoque

---

## 2. Gotcha aplicado — company_id no move

Ao usar `odoo.create('stock.picking', ...)` com `move_ids_without_package`,
**Odoo NAO herda company_id do picking para o move** (em algumas versoes).
Move foi criado com `company_id=1 (FB)` enquanto picking estava
`company_id=5 (LF)`.

**Erro**: `action_confirm` falhou com `"Empresas incompatíveis"`.

**Fix aplicado**:
```python
moves = odoo.search('stock.move', [['picking_id', '=', picking_id]])
odoo.write('stock.move', moves, {'company_id': 5})  # forcar LF
# depois: action_confirm OK
```

**Recomendacao para `StockPickingService`**: sempre forçar `company_id`
nos moves apos create do picking inter-company.

---

## 3. Padrao de validacao G011 + lot_name

Apos `action_assign`, as move_lines vem com `quantity=168.108`
(automatico) mas `lot_name=False` e `lot_id=False`. Precisa preencher:

```python
mls = odoo.search_read('stock.move.line', [['picking_id', '=', picking_id]],
    ['id', 'lot_name', 'lot_id'])
for ml in mls:
    updates = {'quantity': 168.108}
    if not ml['lot_id'] and not ml['lot_name']:
        updates['lot_name'] = 'INV-103000011-20260518'
    odoo.write('stock.move.line', [ml['id']], updates)
```

Padrao G011 (preencher_qty_done apos action_assign) tambem aplica aqui.

---

## 4. Balanço pos-execucao (verificado)

Soma dos quants do PEPINO (pid=27690) com mesmo lote `INV-103000011-20260518`:

| quant | qty | lote_id | location | company | role |
|---|---|---|---|---|---|
| q228547 | 0.000 | 57251 | FB/Estoque | FB | saiu (origem) |
| q228548 | -168.108 | 57251 | Ajuste de Inventario | FB | saiu para Em Transito |
| q228549 | +168.108 | 57251 | Em Transito Industr | None | entrou via picking 317313 |
| q228630 | -168.108 | 57252 | Em Transito Industr | None | saiu via picking 317316 |
| q228631 | +168.108 | 57252 | LF/Estoque | LF | **entrou na LF** ✓ |

**Saldos liquidos**:
- LF/Estoque: +168.108 ✓ (objetivo)
- Em Transito Industr: 168.108 - 168.108 = 0 ✓
- FB/Estoque: 0 ✓ (ja zerado pelo picking 317313)

---

## 5. Detalhe tecnico — 2 stock.lot com mesmo nome

Existem agora **2 registros stock.lot** com `name='INV-103000011-20260518'`:

| id | company | criado_em | role |
|---|---|---|---|
| 57251 | NACOM GOYA - FB | sub-piloto sessao 1 (madrugada) | usado na saida FB |
| 57252 | LA FAMIGLIA - LF | sub-piloto sessao 2 (manha) | usado na entrada LF |

Isso e' **comportamento padrao do Odoo** para inter-company com stock.lot
por empresa. O mesmo nome de lote pode existir em multiplas companies como
registros distintos.

**Implicacao para rastreabilidade**: ao buscar `stock.lot.search([['name', '=', 'INV-103000011-20260518']])`, vai retornar
ambos. Filtrar por `company_id` quando precisar de scope especifico.

---

## 6. Status dos 3 ajustes locais (no DB)

Os 3 ajustes do invoice 627348 ja estavam em `F5e_SEFAZ_OK + EXECUTADO`
desde a etapa D do sub-piloto sessao 2. **Nenhuma alteracao no DB local
necessaria** — a entrada LF e' operacao Odoo-only.

| ajuste_id | cod | lote_destino DB | qty_ajuste | observacao |
|---|---|---|---|---|
| 162425 | 103000011 | 032/24-25 | 131.844 | renomeacao futura (D004) |
| 170143 | 103000011 | MIGRAÇÃO | 18.132 | renomeacao futura |
| 170174 | 103000011 | MIGRAÇÃO | 18.132 | renomeacao futura |
| **Total** | | | **168.108** | bate com picking 317316 ✓ |

A renomeacao para lotes `032/24-25` / `MIGRAÇÃO` deve ser feita como
RENOMEAR_LOTE em onda posterior (parte do plano D004). Por agora, os
168.108 estao em LF/Estoque com lote `INV-103000011-20260518`.

---

## 7. Comparacao com sessao 1 (sub-piloto madrugada)

Sessao 1 fez o mesmo tipo de operacao para a NF 608629 (ALHO GRANULADO
industr):

| | Sessao 1 (NF 608629) | Sessao 2 (NF 627348) |
|---|---|---|
| Picking | 317306 LF/IN/01733 | **317316 LF/IN/01734** |
| Origin | `INV-INVENTARIO_2026_05-ENTRADA-LF-NF608629` | `INV-INVENTARIO_2026_05-ENTRADA-LF-NF627348` |
| Produto | 103000037 ALHO GRANULADO 10.389 kg | 103000011 PEPINO 168.108 un |
| Lote entrada | `MIGRAÇÃO` | `INV-103000011-20260518` |
| Companies move | OK (deve ter sido criado outro caminho) | precisou fix manual |

Diferenca: sessao 2 atingiu o gotcha de `company_id` nao herdada no move.
Pode ter sido contornado na sessao 1 por outro fluxo (ex: criacao via UI Odoo).

---

## 8. Ref

- `docs/inventario-2026-05/02-gotchas/G006-picking-inter-company-location-virtual.md`
- `docs/inventario-2026-05/CHECKPOINT_2026_05_18_NCM_PENDENTE.md`
- `/tmp/auditoria_entrada_lf_nf627348.json` (snapshot completo)
