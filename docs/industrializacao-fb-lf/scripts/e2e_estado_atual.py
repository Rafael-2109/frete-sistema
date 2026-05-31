#!/usr/bin/env python3
"""E2E — aterrar estado atual (READ-ONLY): qual produto tem infra de industrializacao
montada e componentes posicionados na FB. Compara 4870112 (piloto doc) vs 4870110 (cobaia)."""
import sys
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CMP_FB = 1
CMP_LF = 5
LOC_FB_ESTOQUE = 8
LOC_TRANSITO_IND = 26489
CAND = {'4870112': None, '4870110': None}


def main():
    o = get_odoo_connection()
    o.authenticate()

    for code in list(CAND):
        pr = o.search_read('product.product', [('default_code', '=', code)],
                           ['id', 'name', 'categ_id', 'type', 'route_ids', 'standard_price'], limit=1)
        if not pr:
            print(f"\n### {code}: NAO ENCONTRADO"); continue
        pr = pr[0]
        pid = pr['id']
        print(f"\n{'='*90}\n### {code} | id={pid} | {pr['name']}\n    categ={pr['categ_id'][1]} type={pr['type']} custo={pr['standard_price']}")
        # BoMs (todas empresas)
        boms = o.execute_kw('mrp.bom', 'search_read',
                            [[('product_tmpl_id.default_code', '=', code)]],
                            {'fields': ['id', 'display_name', 'type', 'company_id', 'active', 'consumption'],
                             'context': {'active_test': False}})
        print(f"    BoMs:")
        for b in boms:
            cmp = b['company_id'][1] if b['company_id'] else 'GLOBAL'
            print(f"      bom {b['id']} [{cmp}] type={b['type']} active={b['active']} consumption={b['consumption']} | {b['display_name']}")
        # quant FB/Estoque + LF
        for loc, lab in [(LOC_FB_ESTOQUE, 'FB/Estoque'), (LOC_TRANSITO_IND, 'Em Transito Ind')]:
            q = o.search_read('stock.quant', [('product_id', '=', pid), ('location_id', '=', loc)],
                              ['quantity'], limit=5)
            tot = sum(x['quantity'] for x in q)
            print(f"    saldo {lab}: {tot}")

    # componentes do piloto 4870112: BoM 3695 -> linhas; checar saldo em FB/Estoque
    print(f"\n{'='*90}\n### Componentes da BoM 3695 (piloto) — saldo em FB/Estoque")
    lines = o.search_read('mrp.bom.line', [('bom_id', '=', 3695)],
                          ['product_id', 'product_qty'], limit=200)
    comp_ids = [l['product_id'][0] for l in lines if l['product_id']]
    if comp_ids:
        quants = o.search_read('stock.quant',
                               [('product_id', 'in', comp_ids), ('location_id', '=', LOC_FB_ESTOQUE)],
                               ['product_id', 'quantity'], limit=500)
        saldo_by = {}
        for q in quants:
            saldo_by[q['product_id'][0]] = saldo_by.get(q['product_id'][0], 0) + q['quantity']
        prods = o.read('product.product', comp_ids, ['default_code', 'name', 'categ_id', 'type'])
        n_ok = 0
        for p in prods:
            s = saldo_by.get(p['id'], 0)
            if s > 0:
                n_ok += 1
            print(f"      {p['default_code']:>12} saldoFB={s:>10,.2f} type={p['type']:8} {p['name'][:32]} | {p['categ_id'][1].split('/')[-1].strip()}")
        print(f"    -> {n_ok}/{len(prods)} componentes COM saldo em FB/Estoque")


if __name__ == '__main__':
    main()
