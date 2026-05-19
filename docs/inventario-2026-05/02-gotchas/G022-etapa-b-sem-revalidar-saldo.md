# G022 — ETAPA B não re-valida saldo entre action_assign e button_validate

**Status**: 🔴 ABERTO
**Severidade**: MEDIUM
**Sessão descoberto**: 2026-05-18 sessão 3 (tarde, batch 50 prods LF)

## Sintoma

ETAPA B faz:
1. `search_read stock.quant` para descobrir saldo livre por lote
2. Calcula `livre = quantity - reserved_quantity` por quant
3. Cria picking com qty alocada por lote (FIFO ordenado)
4. `action_confirm` + `action_assign`
5. `button_validate`

Entre passos 3 e 5, **outro processo Odoo** (ETAPA A in-flight, robô
CIEL IT, ou qualquer write externo) pode mudar o `stock.quant.quantity`.

`action_assign` é **permissivo** — aceita reservar acima do disponível
(soft reservation). `button_validate` é **estrito** — checa
`quantity >= reserved` por lote e rejeita com Fault 2.

## Evidência

Após F5b falhar no picking 317402, lote 2025,2527/24 tinha:
- `quantity=185.2375`
- `reserved_quantity=250.0` (do próprio picking 317402)
- `livre=-64.7625` ← inconsistência

O Odoo nunca rejeitou o `action_assign` mas rejeitou o `button_validate`.

## Refinamento (2026-05-18 sessão 3 batch 30) — Over-reservation pós-renomeação

Investigação adicional revelou mecanismo mais grave: quando ETAPA A
renomeia lote (action_apply_inventory), as **reservas no lote antigo
não são transferidas para o lote novo**. ETAPA B subsequente reserva
em AMBOS os lotes.

Caso real (picking 317417, produto 104000004):
```
move 1098904: demand=1563.97  →  reserved=3355.12 (215% overshoot!)
  ml1: 1563.97 do lote 0109 (só tinha 121.40 fisico!)
  ml2:  227.17 do lote 20250802
  ml3: 1563.97 do lote INV-104000004-20260518 (lote criado pela ETAPA A)
```

action_assign distribuiu a mesma demand entre o lote antigo (com saldo
remanescente) E o lote novo (que recebeu o saldo transferido), causando
2-3x overshoot consistente em pickings PERDA pós-RENOMEAR.

**NÃO é problema de location**: investigado 18/05; LF tem 683
sub-locations (LF/Estoque/MOLHO/R-1/N-1/P-01 etc.) mas saldo dos produtos
do batch fica direto em LF/Estoque(42). `child_of=42` retorna idêntico
a `=42`.

## Combinação com G021

Quando combinado com G021 (race A↔B), o sintoma se manifesta como
**TODOS os pickings PERDA falhando** porque o saldo pós-A ainda não
foi commitado quando B consultou.

No batch de hoje:
- 5/6 pickings F5c_FALHA (todos os PERDA)
- 1/6 OK (INDUSTR 317407, que veio de FB/Estoque — não impactado pela A
  na LF)

## Mitigação atual

`G019` (fix F5b) detecta o false-positive: após `button_validate`, verifica
`picking.state == 'done'`. Se não, marca `F5c_FALHA` e aborta. **Sem o
fix G019, o script teria seguido em frente com pickings em
state=assigned**, corrompendo a pipeline.

## Fix proposto

Adicionar re-validação em `StockPickingService.validar()`:

```python
# Antes de button_validate, re-consultar stock.quant e abortar
# se reserved > quantity em algum lote do picking.
moves = odoo.read('stock.move', move_ids, ['product_id', 'location_id'])
for m in moves:
    quants = odoo.search_read('stock.quant',
        [['product_id', '=', m['product_id'][0]],
         ['location_id', '=', m['location_id'][0]]],
        ['quantity', 'reserved_quantity', 'lot_id'])
    for q in quants:
        if float(q.get('reserved_quantity') or 0) > float(q['quantity']):
            raise RuntimeError(
                f'G022 abort: quant lot={q["lot_id"]} reserved > quantity '
                f'({q["reserved_quantity"]} > {q["quantity"]}). '
                f'Saldo desatualizado entre action_assign e button_validate.'
            )
```

Trade-off: +1 query por move antes de cada validar. Em batch de 6 pickings
e ~150 moves, ~150 queries extras (~2-3s).

## Ref

- `app/odoo/services/stock_picking_service.py:validar()` (alvo do fix)
- `docs/inventario-2026-05/02-gotchas/G021-etapa-a-reporta-prematuro.md` (causa correlacionada)
- `docs/inventario-2026-05/02-gotchas/G019-f5b-validar-engole-erro.md` (fix relacionado)
