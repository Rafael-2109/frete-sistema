#!/usr/bin/env python3
"""S22 — De onde o PICKING de remessa (pt53) tira os componentes? READ-ONLY.
Hipotese Rafael: "o sistema abre os componentes via MO ou lista de materiais".
Procura pickings pt53 (FB Exp.Industrializacao) de CICLO COMPLETO (muitas move
lines) e rastreia a origem: group_id -> procurement -> MO (mrp.production) /
rota de subcontratacao / BoM. Se as move lines = BoM explodida e vieram de uma
MO/regra, ENTAO a explosao e' automatica na REMESSA (e o que o Rafael lembra).

Tambem casa: para o produto shoyu (4870112), acha pickings de remessa reais que
contenham os componentes da BoM e mostra a cadeia origin.
"""
import sys
from collections import Counter
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5], 'company_id': 5, 'lang': 'pt_BR'}
PT53 = 53  # FB: Expedicao Industrializacao


def m2o(v):
    return f"{v[0]}|{v[1]}" if isinstance(v, list) and v else ('-' if not v else str(v))


def main():
    o = get_odoo_connection(); assert o.authenticate(), "FALHA AUTH"

    def rr(model, dom, fields, **kw):
        kw2 = {'fields': fields, 'context': CTX}; kw2.update(kw)
        return o.execute_kw(model, 'search_read', [dom], kw2)

    # pickings pt53 recentes done com contagem de move lines
    picks = rr('stock.picking', [('picking_type_id', '=', PT53), ('state', '=', 'done')],
               ['id', 'name', 'origin', 'group_id', 'create_uid', 'move_ids'],
               order='id desc', limit=40)
    # ordenar por nº de moves desc
    picks.sort(key=lambda p: -len(p.get('move_ids') or []))
    print("=" * 88)
    print("=== Pickings pt53 (FB Exp.Industrializacao) done — por nº de componentes (top 6) ===")
    for p in picks[:6]:
        nmv = len(p.get('move_ids') or [])
        print(f"\n### {p['name']} (id {p['id']}) moves={nmv} origin={p.get('origin')} "
              f"group={m2o(p.get('group_id'))} by={m2o(p.get('create_uid'))[:18]}")
        moves = rr('stock.move', [('picking_id', '=', p['id'])],
                   ['product_id', 'product_uom_qty', 'bom_line_id', 'created_production_id',
                    'production_id', 'raw_material_production_id', 'group_id', 'origin'], limit=30)
        # quantos vieram de uma BoM line / MO?
        from_bom = sum(1 for m in moves if m.get('bom_line_id'))
        from_mo = sum(1 for m in moves if m.get('raw_material_production_id') or m.get('production_id'))
        print(f"    {len(moves)} stock.move | from_bom_line={from_bom} | from_MO={from_mo}")
        for m in moves[:8]:
            print(f"      - {m2o(m['product_id'])[:42]:42} qty={m.get('product_uom_qty')} "
                  f"bom_line={m2o(m.get('bom_line_id'))[:8]} MO_raw={m2o(m.get('raw_material_production_id'))[:14]} "
                  f"orig={m.get('origin')}")


if __name__ == '__main__':
    main()
