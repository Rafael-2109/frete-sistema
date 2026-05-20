# G036 — Lote com vírgula é literal real + lotes duplicados quebram operador `=`

**Severidade**: HIGH
**Status**: ✅ IDENTIFICADO + FIX APLICADO (2026-05-20)
**Descoberto em**: Sessão de realocação de lote LF (Pasta17.xlsx — ajustes +/-)

## Sintoma

Dois sintomas correlatos ao buscar saldo de lote na LF:

1. **Lote com vírgula no nome** (ex `0108/24, ME303-211/25`, `224,276`,
   `10388, MIGRAÇÃO`) parece ser "2 lotes concatenados" — tentar fazer split por
   vírgula leva a buscar lotes que não existem → redução falha.

2. **Busca de `stock.quant` / `stock.lot` por nome com operador `=` retorna
   vazio**, mesmo havendo saldo. Ex:
   ```python
   odoo.search_read('stock.lot', [['name','=','216/25'],['product_id','=',pid]], ['id'])
   # -> []   (ERRADO — o lote existe e tem saldo)
   odoo.search_read('stock.lot', [['name','in',['216/25']],['product_id','=',pid]], ['id'])
   # -> [{'id':37437},{'id':37661}]   (2 lotes com o MESMO nome!)
   ```

Resultado prático: script de ajuste reporta `FALHA_NAO_COBRIU` / `neg_sem_saldo`
para lotes que na verdade têm saldo, e/ou bloqueia produtos indevidamente.

## Causa raiz

**(A) CIEL IT cria nomes de `stock.lot` com vírgula.** Quando um lote consolida
mais de uma origem, o CIEL IT grava o nome literalmente com vírgula
(`0108/24, ME303-211/25`). É **um único `stock.lot`** real, não dois. O saldo
físico fica nesse lote literal. Confirmado 2026-05-20: 7 de 13 "compostos" do
Pasta17 tinham o saldo físico exato no próprio lote literal.

**(B) Lotes DUPLICADOS** (mesmo `name`, mesmo `product_id`, múltiplos
`stock.lot.id`) — ex 2× `216/25`. Combinado com o bug histórico do operador `=`
em `stock.lot.name` (ver memória `stock_lot_search_bug` / G-relacionado), a busca
por `=` retorna vazio intermitentemente. O saldo está em um dos `lot_id`
duplicados que o `=` não encontra.

## Fix aplicado

1. **Não fazer split de lote por vírgula.** Tratar o valor da célula como **nome
   literal** de lote. Buscar pelo nome exato.

2. **Resolver lot_ids via operador `in` (não `=`)** e considerar TODOS os ids com
   aquele nome; depois buscar quant por `lot_id in [ids]`:
   ```python
   def resolver_lot_ids(odoo, pid, nome):
       res = odoo.search_read('stock.lot',
           [['product_id','=',pid],['name','in',[nome]]], ['id','name'])
       return [r['id'] for r in res if (r.get('name') or '').strip() == nome]

   ids = resolver_lot_ids(odoo, pid, nome)
   quants = odoo.search_read('stock.quant',
       [['product_id','=',pid],['company_id','=',5],['lot_id','in',ids],
        ['location_id','in',[42,53]]],
       ['id','location_id','lot_id','quantity','reserved_quantity'])
   ```

Implementado em `scripts/inventario_2026_05/ajuste_estoque_lf_pasta17.py`
(`resolver_lot_ids`, `buscar_quants_fresh`). Resultado: lotes `216/25` (saldo 300
no `lot_id` 37661) e os 7 compostos com saldo passaram a ser encontrados.

## Como aplicar profilaticamente

- **NUNCA** buscar `stock.lot`/`stock.quant` por `['name','=',valor]`. Sempre
  `['name','in',[valor]]` + filtro exato em memória.
- **NUNCA** fazer split de nome de lote por vírgula/hífen/barra — são caracteres
  válidos em nomes de lote do CIEL IT. Buscar o nome literal.
- Ao classificar "lote tem saldo?", somar quants de **todos** os `lot_id` com
  aquele nome (duplicados existem).

## Why

O CIEL IT permite nomes de lote arbitrários (incluindo vírgula) e não impede
duplicação de nome por produto. O operador `=` do XML-RPC sobre campos
relacionais (`lot_id.name`) tem comportamento intermitente documentado; `in`
é estável.

## Referências

- Script: `scripts/inventario_2026_05/ajuste_estoque_lf_pasta17.py`
- Memória dev: `stock_lot_search_bug` (operador `=` em stock.lot.name)
- Diagnóstico da sessão: comparação literal vs componentes (13 compostos do Pasta17)
