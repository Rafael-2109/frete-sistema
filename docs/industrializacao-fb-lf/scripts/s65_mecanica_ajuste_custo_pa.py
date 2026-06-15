#!/usr/bin/env python3
"""S65 — investiga (READ-only) a MECANICA do ajuste de custo do PA (resido G8).

Objetivo: como subir o custo do PA (4870112) de ~26,23 para Ic+S (~305,19) com
a contrapartida caindo em CPV(3201000001)+CMV(3202010001) p/ zera-las (Opcao A).
3 frentes:
  1. categoria do PA: cost_method (AVCO/standard) + contas de valoracao.
  2. landed cost: modelo disponivel? produtos is_landed_cost? exemplos recentes.
  3. SVL do PA + como a revaloracao (standard_price) lanca a contrapartida.
READ-ONLY. Producao (CIEL IT).
"""
import sys
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1], 'company_id': 1, 'lang': 'pt_BR'}
PA = 27834
PICKING_PA = 325347
SEP = '=' * 96


def main():
    o = get_odoo_connection(); assert o.authenticate(), 'FALHA AUTH'

    def rr(model, dom, fields, **kw):
        kw2 = {'fields': fields, 'context': CTX}; kw2.update(kw)
        return o.execute_kw(model, 'search_read', [dom], kw2)

    def rd(model, ids, fields):
        return o.execute_kw(model, 'read', [list(ids)], {'fields': fields, 'context': CTX})

    print(SEP); print('S65 — mecanica do ajuste de custo do PA'); print(SEP)

    # 1. produto + categoria
    pa = rd('product.product', [PA], ['name', 'standard_price', 'categ_id',
                                      'cost_method', 'product_tmpl_id'])[0]
    print(f"\n[1] PA {PA}: std_price={pa['standard_price']} cost_method={pa.get('cost_method')} categ={pa['categ_id']}")
    cat_id = pa['categ_id'][0]
    catf = o.execute_kw('product.category', 'fields_get', [], {'attributes': ['string'], 'context': CTX})
    cf = ['property_cost_method', 'property_valuation'] + \
         [f for f in catf if 'stock_account' in f or 'stock_valuation' in f or 'account_creditor' in f]
    cat = rd('product.category', [cat_id], list(dict.fromkeys(['name'] + cf)))[0]
    print(f"    categoria {cat_id}:")
    for k, v in cat.items():
        if k != 'id' and v not in (False, None, []):
            print(f"      {k:42} = {v}")

    # 2. landed cost disponivel?
    print('\n[2] Landed cost:')
    try:
        n_lc = o.execute_kw('stock.landed.cost', 'search_count', [[]], {'context': CTX})
        lc_recent = rr('stock.landed.cost', [], ['id', 'name', 'state', 'account_journal_id'],
                       limit=3, order='id desc')
        print(f"    stock.landed.cost: modelo EXISTE, total={n_lc}; recentes={lc_recent}")
        lc_prods = rr('product.product', [('landed_cost_ok', '=', True)],
                      ['id', 'name', 'property_account_expense_id'], limit=8)
        print(f"    produtos landed_cost_ok: {[(p['id'], p['name'][:30]) for p in lc_prods]}")
        for p in lc_prods[:5]:
            print(f"      prod {p['id']} expense_acc={p.get('property_account_expense_id')}")
    except Exception as e:
        print(f"    landed cost indisponivel/erro: {str(e)[:160]}")

    # 3. SVL do PA (historico) + valor atual
    print('\n[3] SVL do PA (historico recente):')
    svls = rr('stock.valuation.layer', [('product_id', '=', PA)],
              ['id', 'create_date', 'quantity', 'value', 'unit_cost', 'remaining_qty',
               'remaining_value', 'description', 'stock_move_id'], limit=8, order='id desc')
    for s in svls:
        print(f"    SVL {s['id']} qty={s['quantity']} value={s['value']} unit={s['unit_cost']} "
              f"rem_qty={s.get('remaining_qty')} rem_val={s.get('remaining_value')} '{(s.get('description') or '')[:30]}'")
    # quant atual
    q = rr('stock.quant', [('product_id', '=', PA), ('location_id', '=', 8)],
           ['lot_id', 'quantity', 'value', 'inventory_quantity_set'])
    print(f"    quant PA FB/Estoque: {q}")

    # 4. existe wizard de revaloracao? (stock.valuation.layer.revaluation)
    print('\n[4] Wizard de revaloracao:')
    for model in ('stock.valuation.layer.revaluation',):
        try:
            f = o.execute_kw(model, 'fields_get', [], {'attributes': ['string'], 'context': CTX})
            rel = {k: f[k]['string'] for k in f if any(t in k for t in
                   ('account', 'added_value', 'new_value', 'reason', 'product', 'cost'))}
            print(f"    {model} EXISTE. campos-chave: {rel}")
        except Exception as e:
            print(f"    {model}: {str(e)[:120]}")

    print('\n' + SEP); print('FIM S65'); print(SEP)


if __name__ == '__main__':
    main()
