# G030 — `stock.move.line.quant_id` em Odoo CIEL IT é COMPUTED `store: False`

**Data:** 2026-05-24 v7 | **Skill afetada:** 9 `consultando-quant-odoo` (átomos novos `listar_move_lines_por_quant`/`listar_pickings_por_quant`)
**Versão Odoo:** 17 EE (`nacomgoya-prd`)
**Status:** ✅ IMPLEMENTADO (fix codificado em `app/odoo/estoque/scripts/consulta_quant.py`)

---

## Sintoma

```python
odoo.search_read('stock.move.line',
    [('quant_id', 'in', [261590, 261594, 261598])],
    ['id', 'quant_id', 'lot_id', 'quantity', 'state', 'picking_id'],
    limit=20)
```

Retorna **20 MLs aleatórias com `quant_id=False`** (None) — completamente não-relacionadas aos quants alvo. O filtro `quant_id in [...]` é **SILENCIOSAMENTE IGNORADO** pelo Odoo.

---

## Causa raiz

Inspecionando atributos do campo:

```python
fields = odoo.execute_kw('stock.move.line', 'fields_get', [['quant_id']],
    {'attributes': ['string', 'type', 'relation', 'store', 'compute', 'depends']})
# {'quant_id': {'depends': [], 'relation': 'stock.quant', 'required': False,
#               'store': False, 'string': 'Pick From', 'type': 'many2one'}}
```

`quant_id`:
- **`store: False`** → não persistido no banco
- **`depends: []`** → computed sem deps explícitas (computado on-fetch via context UI)
- **string "Pick From"** → campo UI-only (Odoo frontend usa para mostrar qual quant a ML pegou)

Como não é stored, o ORM Odoo:
- Aceita o filtro silenciosamente sem erro
- Mas não consegue traduzir para SQL WHERE
- Retorna registros aleatórios (limit padrão)

---

## Solução: cross-ref via TUPLA `(product_id, lot_id, location_id, company_id)`

Cada quant é unicamente determinado pela tupla `(product, lot, location, company)`. MLs apontam para quants implicitamente via essa tupla. Solução:

```python
# 1. Buscar quants alvo → extrair tuplas
quants = odoo.read('stock.quant', [261590, 261594, 261598],
    ['product_id', 'lot_id', 'location_id', 'company_id'])

# 2. Construir domain compound: OR de AND para cada tupla
domain = []
per_tupla = []
for q in quants:
    pid = q['product_id'][0]
    lid = q['lot_id'][0] if q['lot_id'] else False
    loc = q['location_id'][0]
    cid = q['company_id'][0]
    per_tupla.append(['&', '&', '&',
                       ('product_id', '=', pid),
                       ('lot_id', '=', lid),
                       ('location_id', '=', loc),
                       ('company_id', '=', cid)])
# Unir N tuplas com N-1 '|' prefixados
if len(per_tupla) == 1:
    domain.extend(per_tupla[0])
else:
    domain.extend(['|'] * (len(per_tupla) - 1))
    for t_dom in per_tupla:
        domain.extend(t_dom)

# 3. Adicionar filtro de state
domain = ['&', ('state', 'in', ['assigned', 'partially_available'])] + domain

# 4. Buscar
mls = odoo.search_read('stock.move.line', domain,
    ['id', 'product_id', 'lot_id', 'location_id', 'quantity', 'state', 'picking_id'])

# 5. Resolver quant_id reverso via tupla (caller)
tupla_para_quant = {(q['product_id'][0], q['lot_id'][0] if q['lot_id'] else False,
                     q['location_id'][0], q['company_id'][0]): q['id']
                    for q in quants}
for ml in mls:
    chave = (ml['product_id'][0],
             ml['lot_id'][0] if ml['lot_id'] else False,
             ml['location_id'][0], ml['company_id'][0])
    ml['quant_id_resolvido'] = tupla_para_quant.get(chave)
```

---

## Validação AO VIVO 2026-05-24 v7

**Antes do fix:**
```
$ python consultar_quants.py --modo pickings --quant-ids 261590,261594,261598
Total pickings: 30+  (LIXO — 20 MLs random com quant_id=False, lotes 0407/24, 2612/24...)
```

**Após fix:**
```
$ python consultar_quants.py --modo pickings --quant-ids 261590,261594,261598
Total pickings: 1 | Total MLs: 3
  pkg_id= 320753 FB/INT/08022  state=assigned emp=FB
    type=FB: Transferências Internas (FB)
    3 MLs, qty_total=1035.0830, lotes=['13206'], produtos=3
      ml_id=217657766 quant_id= 261590 lot=13206 qty=319.0830 [4890128] (state=assigned)
      ml_id=217657767 quant_id= 261594 lot=13206 qty=269.0000 [4899027] (state=assigned)
      ml_id=217657769 quant_id= 261598 lot=13206 qty=447.0000 [4902852] (state=assigned)
```

✅ Caso real lote 13206 identifica exatamente 1 picking (FB/INT/08022) com 3 MLs e quant_ids resolvidos.

**Smoke MIGRAÇÃO** (5 cods FB/Estoque, 10 quants):
```
Total pickings: 3 | Total MLs: 6
  - FB/FB/EMB/11673 (1 ML, 0.006, origem MO FB/OP/MANUAL/01763)
  - FB/FB/EMB/11674 (2 MLs, 0.30 total, origem MO FB/OP/MANUAL/01764)
  - FB/OUT/01046 (3 MLs, 890.46 total, DEVOLUÇÃO LF/LA FAMIGLIA)
```

---

## Impacto arquitetural

1. **Skill 9 `listar_move_lines_por_quant` e `listar_pickings_por_quant`** — DEVE usar cross-ref via tupla. Codificado em `app/odoo/estoque/scripts/consulta_quant.py`.
2. **Skill 2.4 `find_orphan_mls`** — quando implementada, MESMA abordagem: receber quant_ids → buscar tuplas → cross-ref via tupla.
3. **Qualquer query futura sobre stock.move.line baseada em quants** — INVARIANTE: NUNCA usar `('quant_id', '=', X)` ou `('quant_id', 'in', [...])`.

---

## Padrão reaproveitável: campos computed `store: False`

Antes de filtrar por qualquer campo many2one/many2many em search_read:

```python
fields_attrs = odoo.execute_kw('<model>', 'fields_get', [['<field>']],
    {'attributes': ['store', 'compute', 'depends']})
# Se store=False E depends=[] → NUNCA usar como filtro!
```

Outros campos suspeitos a verificar (Odoo CIEL IT):
- `stock.move.line.quant_id` ❌ (G030)
- `stock.move.product_qty_available` (provável computed)
- `stock.picking.products_availability_state` (provável computed)

---

## Relacionado

- [[gotcha_quant_id_store_false]] (memória dev — sessão v7)
- [[skill9_quant_query_pattern]] (memória — pattern de query versátil)
- `app/odoo/estoque/scripts/consulta_quant.py` — implementação fix
- `tests/odoo/services/test_stock_quant_query_service.py` — 19 testes pytest validando

## Investigação histórica

| Data | Quem | Achado |
|---|---|---|
| 2026-05-24 v7 (Fase A) | Claude Code | Probe AO VIVO identificou `quant_id` como many2one stock.quant — INFERÊNCIA INCORRETA: assumiu que era stored |
| 2026-05-24 v7 (smoke C6) | Claude Code | Smoke real falhou — Odoo retornou lixo. Re-investigação via `fields_get` revelou `store: False` |
| 2026-05-24 v7 (fix C2) | Claude Code | Refatorado para cross-ref via tupla. 19 pytest verdes + 2 smokes PROD ✅ |
