# G009 — Script 03 emite 1 ajuste por produto, mas estoque esta em N lotes

**Descoberta**: 2026-05-18 sub-piloto bulk (NF 13150 RETNA/2026/00030)
**Severidade**: MED (gera NFs incompletas com qty menor que demand)
**Status**: corrigido em `09_executar_onda1_bulk.py:435-540`

---

## Sintoma

Ajuste 161385 (103000117 PIMENTA BIQ B PERDA_LF_FB):
- `lote_origem = MIGRAÇÃO`
- `qtd_ajuste = -672.32` kg

Apos criar picking + reservar:
- move `product_uom_qty = 672.32` (demand)
- soma move_lines `qty_done = 52` (so isso conseguiu reservar)
- **falta 620.32 kg**

NF saiu com `qty=52` em vez de `672.32`. Estoque restante "perdido".

## Causa raiz

Script 03 (`03_confrontar_inv_vs_odoo.py`) agrega `total_odoo` por
(cod_produto, company_id) somando TODOS os lotes do Odoo. Gera 1 ajuste
`PERDA_LF_FB` com `qtd_ajuste = total_odoo - qtd_inventario` apontando
para UM unico `lote_origem` (o maior).

Mas o estoque real esta distribuido entre N lotes:
```
LF/Estoque produto 103000117:
  lote MIGRAÇÃO: 52 kg
  lote 0326/25: 620 kg
  lote outros: 0
```

O ajuste 161385 aponta para MIGRAÇÃO (52 kg) mas a demanda e' 672 kg.

## Solucao

`etapa_b_pickings` NUNCA usa `lote_origem` do DB diretamente. Em vez disso:

1. Para cada cod_produto do chunk:
   - Soma `demand_total = sum(abs(qtd_ajuste))` de TODOS ajustes do produto
   - Consulta `stock.quant` real (`company_origem` + `location_origem`) com
     `quantity > 0`
   - **FIFO por `create_date`**: pega quants mais antigos primeiro
   - Para cada quant, `take = min(qty_livre, qty_restante)`. Adiciona linha.
   - Para quando `qty_restante <= 0` ou esgotar quants

2. Se sobrar `qty_restante > 0`:
   - Cria ajuste compensatorio `INDUSTRIALIZACAO_FB_LF` (FB → LF +delta)
     com `acao_decidida='INDUSTRIALIZACAO_FB_LF'`,
     `tipo_divergencia='COMPENSATORIO_FALTA_ESTOQUE'`,
     `status='PROPOSTO'`
   - Registra `erro_msg` no ajuste original explicando o delta

3. Resultado: picking tem N linhas (1 por lote real disponivel), demand
   cobrida ate o disponivel.

## Codigo

```python
quants = odoo.search_read(
    'stock.quant',
    [
        ['product_id', '=', pid],
        ['company_id', '=', company_origem],
        ['location_id', '=', location_origem],
        ['quantity', '>', 0],
    ],
    ['id', 'lot_id', 'quantity', 'reserved_quantity', 'create_date'],
    order='create_date asc',  # FIFO
)
qty_restante = demand_total
for q in quants:
    if qty_restante <= 0.001: break
    livre = float(q['quantity']) - float(q.get('reserved_quantity') or 0)
    if livre <= 0: continue
    take = min(livre, qty_restante)
    linhas.append({
        'product_id': pid,
        'quantity': take,
        'lot_name': q['lot_id'][1] if q.get('lot_id') else False,
    })
    qty_restante -= take

# Se sobrou, criar ajuste compensatorio
if qty_restante > 0.001 and tipo_op == 'perda' and company_origem == 5:
    ajustes_compensatorios_a_criar.append({
        'cod_produto': cod,
        'acao_decidida': 'INDUSTRIALIZACAO_FB_LF',
        'qtd_ajuste': qty_restante,
        ...
    })
```

## Concept: regra do usuario (2026-05-18)

> "se qty_restante>0 criar ajuste positivo na FB e transferir pra LF"

A FB devolve a quantidade restante para a LF via NF FB→LF industrializacao,
re-equilibrando o estoque.

## Refactoring recomendado para script 03

O ideal seria que script 03 emitisse N ajustes PERDA_LF_FB, 1 por lote
real (proporcional). Mas o estado atual do bulk lida com isso na ETAPA B
sem precisar regenerar diffs.

## Ref

- D004 (rename + diferenca liquida)
- D006 secao L12
- script 03 linha 384-408 (loop por quants)
