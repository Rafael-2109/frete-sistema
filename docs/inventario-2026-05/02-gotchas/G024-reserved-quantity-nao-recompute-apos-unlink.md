# G024 — `stock.quant.reserved_quantity` NAO recompute apos `unlink` de move_line orfa

> **Renumerado 2026-05-18**: antes era G006. Renomeado para G024 porque o nome
> original G006 ja era ocupado por `G006-picking-inter-company-location-virtual.md`
> (descoberto antes, no sub-piloto da madrugada). Este gotcha foi descoberto
> mais tarde, durante a execucao da pre-etapa CD (D007).

**Data**: 2026-05-18
**Descoberto durante**: execucao pre-etapa CD (D007), Opcao B-minimo
**Impacto**: 121 ajustes ficaram em FALHA mesmo apos limpeza de orfaos

---

## Sintoma

Apos `DELETE` (unlink) de 526 `stock.move.line` orfaos no CD (pre-etapa D007),
o campo `reserved_quantity` dos `stock.quant` afetados **continuou inalterado**
no Odoo CIEL IT.

Esperado: `reserved_quantity` zerar (ou reduzir) automaticamente, porque
sem move_line apontando, nao ha mais "reserva".

Real: o campo permaneceu congelado mesmo sem nenhum move_line apontando
para o quant.

**Exemplo concreto**:
```
Quant 137630 (SAL SEM IODO MIGRACAO):
  quantity         = 85.913 un
  reserved_quantity = 4.200 un  ← antes do DELETE: move_line 217525603 reservava 4.200 un
                                ← apos DELETE: campo continuou 4.200 (deveria ser 0)
```

---

## Causa raiz

`stock.quant.reserved_quantity` no Odoo 17 e um campo **stored** (nao computed
dinamicamente). O recompute depende de **triggers** disparados quando o
`stock.move.line` muda:

```python
# odoo/addons/stock/models/stock_move_line.py (simplificado)
@api.depends('quantity', 'product_id', 'location_id', 'lot_id')
def _compute_reserved_quantity_on_quant(self):
    ...
```

**Problema**: as move_lines orfas tinham `move_id=False`, `picking_id=False`,
`state=False`. O trigger de recompute do quant **provavelmente busca via
`move_id`** para invalidar o cache da reserva, e como nao ha move_id,
**nao consegue identificar o quant a invalidar**.

Resultado: `unlink` apaga o registro mas o `reserved_quantity` do quant
continua com o valor stale.

---

## Solucao implementada

Script `/tmp/fix_reserved_quantity.py` que:

1. Para cada produto suspeito (Cat 2 do D007), busca quants com `reserved_quantity > 0`
2. Verifica se existe `stock.move.line` REAL apontando (com `move_id` ou `picking_id`)
3. Se nao tiver link real, calcula nova reserva = soma das move_lines reais (geralmente 0)
4. `odoo.write('stock.quant', [id], {'reserved_quantity': nova_qty})` — WRITE direto

**Resultado**: 47 quants atualizados em 1s, 0 falhas. 39 ajustes adicionais
destravados na re-execucao do 09b.

---

## Como detectar

Sintoma indicativo: ajuste falha com mensagem `Quant origem X tem Y un
reservadas em pickings ativos. Saldo apos transferencia ficaria < reserva`,
**mas** investigacao via Odoo nao revela picking ativo (apenas move_line
orfa com `move_id=False AND picking_id=False`).

Query Odoo para validar:
```python
domain = [
    ['product_id', '=', pid], ['company_id', '=', 4],
    ['location_id', '=', locid], ['lot_id', '=', lid],
    ['state', 'not in', ['done', 'cancel']],
]
mls = odoo.search_read('stock.move.line', domain,
    ['id', 'move_id', 'picking_id', 'state', 'quantity'])
# Se TODAS as move_lines tem move_id=False AND picking_id=False:
#   reserva e fantasma — fazer write direto para recompute
```

---

## Recomendacao

**Fluxo completo de limpeza apos detectar orfaos**:

1. Identificar orfaos via filtro estrito (`move_id=False AND picking_id=False AND state=False`)
2. Backup snapshot dos orfaos (JSON)
3. `odoo.execute_kw('stock.move.line', 'unlink', [ids])` em batches
4. **OBRIGATORIO**: para cada quant afetado, recalcular `reserved_quantity`:
   - somar `quantity` das move_lines REAIS ainda existentes
   - `odoo.write('stock.quant', [id], {'reserved_quantity': novo_valor})`
5. Validar: re-buscar quants e confirmar reserved_quantity correto

**Sem o passo 4, o DELETE e' apenas cosmetico** — os ajustes que dependem
dessas reservas continuam bloqueados.

---

## Risco residual da solucao

`write` direto em `reserved_quantity` **bypassa logica do Odoo**. Pode-se
argumentar que e' "destrutivo" — mas:
- Sem move_line apontando, o valor stale e' o problema (nao a solucao)
- Reversivel: write inverso restaura
- `quantity` (saldo real) NAO mexe

**Mitigacao**: aplicar apenas em quants onde `len(move_lines com link real) == 0`.

---

## Referencias

- Script: `/tmp/fix_reserved_quantity.py`
- D007: `00-decisoes/D007-pre-etapa-cd-fb-minimizar-nf.md`
- Relacionado: G025 (orfaos recorrentes no CD — antes era G007)
