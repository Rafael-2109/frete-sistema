#!/usr/bin/env python3
"""E2E (READ-ONLY): dimensionar batch minimo do 4870112 + componentes/qtd + categorias (escopo L1)."""
import sys
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

BOM_PA = 3695   # 4870112 (LF)
BOM_BAT = 3646  # BATELADA DE SHOYU (semi 3800018)


def bom_info(o, bom_id, lbl):
    b = o.read('mrp.bom', [bom_id], ['display_name', 'product_qty', 'product_uom_id'])[0]
    print(f"\n{lbl} (bom {bom_id}): {b['display_name']} | rende {b['product_qty']} {b['product_uom_id'][1] if b['product_uom_id'] else ''}")
    lines = o.search_read('mrp.bom.line', [('bom_id', '=', bom_id)], ['product_id', 'product_qty', 'product_uom_id'], limit=50)
    comps = []
    for l in lines:
        p = o.read('product.product', [l['product_id'][0]], ['default_code', 'name', 'categ_id', 'type'])[0]
        comps.append({'pid': p['id'], 'cod': p['default_code'], 'nome': p['name'][:28],
                      'qtd': l['product_qty'], 'categ_id': p['categ_id'][0] if p['categ_id'] else None,
                      'categ': p['categ_id'][1] if p['categ_id'] else '-', 'type': p['type']})
        print(f"   {p['default_code']:>12} x{l['product_qty']:<10} [{p['type']:7}] {p['name'][:30]} | categ {p['categ_id'][0] if p['categ_id'] else '?'} {p['categ_id'][1].split('/')[-1].strip() if p['categ_id'] else ''}")
    return b, comps


def main():
    o = get_odoo_connection(); o.authenticate()
    print("=" * 92)
    print("BATCH MINIMO + ESCOPO L1 — produto 4870112")
    print("=" * 92)
    bpa, cpa = bom_info(o, BOM_PA, "BoM PA")
    bbat, cbat = bom_info(o, BOM_BAT, "BoM BATELADA (semi)")
    # categorias unicas (escopo L1) - PA + todos componentes
    pa = o.read('product.product', [27834], ['categ_id'])[0]
    cats = {pa['categ_id'][0]: pa['categ_id'][1]} if pa['categ_id'] else {}
    for c in cpa + cbat:
        if c['categ_id'] and c['type'] == 'product':
            cats[c['categ_id']] = c['categ']
    print("\n" + "=" * 92)
    print(f"ESCOPO L1 — categorias (real_time) a repointar na LF p/ o piloto: {len(cats)}")
    print("=" * 92)
    for cid, nm in sorted(cats.items()):
        print(f"   categ {cid:<5} {nm}")
    print("\n  (PA categ 193; BATELADA é semi; ÁGUA é consu = própria LF, não entra no L1)")


if __name__ == '__main__':
    main()
