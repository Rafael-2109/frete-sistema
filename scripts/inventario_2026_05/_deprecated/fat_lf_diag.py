"""Diagnostico: por que invoice qty != Excel QTD. Estado real picking vs invoice vs quants."""
import os
import sys
import warnings
warnings.simplefilter('ignore')
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from app import create_app  # noqa: E402
from app.odoo.utils.connection import get_odoo_connection  # noqa: E402

CASOS = [
    # (picking_id, invoice_id, cod, company, principal_loc, excel_qtd)
    (320063, 678566, '104000045', 1, 8, 59.931),
    (320065, 678569, '208000021', 5, 42, 50.0),
    (320066, 678567, '4856125', 5, 42, 53.417),
]


def main():
    app = create_app()
    with app.app_context():
        odoo = get_odoo_connection()
        for pick_id, inv_id, cod, comp, ploc, exc in CASOS:
            print('=' * 70)
            print(f'  COD {cod} | picking {pick_id} | invoice {inv_id} | Excel QTD={exc}')
            prod = odoo.search_read('product.product', [['default_code', '=', cod]],
                                    ['id', 'uom_id'], limit=1)
            pid = prod[0]['id']
            uom = prod[0]['uom_id'][1] if prod[0].get('uom_id') else '?'
            print(f'  product_id={pid} uom={uom}')
            # picking moves
            mvs = odoo.search_read('stock.move', [['picking_id', '=', pick_id]],
                                   ['id', 'product_id', 'product_uom_qty', 'quantity', 'state', 'product_uom'])
            for mv in mvs:
                print(f"    MOVE {mv['id']}: demand={mv['product_uom_qty']} done={mv.get('quantity')} "
                      f"state={mv['state']} uom={mv['product_uom'][1] if mv.get('product_uom') else '?'}")
                mls = odoo.search_read('stock.move.line', [['move_id', '=', mv['id']]],
                                       ['lot_id', 'qty_done', 'quantity', 'location_id'])
                for ml in mls:
                    lot = ml['lot_id'][1] if ml.get('lot_id') else '(sem)'
                    loc = ml['location_id'][1] if ml.get('location_id') else '?'
                    print(f"        ML lot={lot} qty_done={ml.get('qty_done')} qty={ml.get('quantity')} loc={loc}")
            # invoice line
            inv = odoo.read('account.move', [inv_id], ['invoice_line_ids', 'state'])
            ils = odoo.read('account.move.line', inv[0]['invoice_line_ids'], ['quantity', 'product_id'])
            for il in ils:
                print(f"    INVOICE LINE: qty={il.get('quantity')}")
            # quants atuais na principal
            qs = odoo.search_read('stock.quant',
                                  [['product_id', '=', pid], ['company_id', '=', comp], ['location_id', '=', ploc]],
                                  ['lot_id', 'quantity', 'reserved_quantity'])
            tot = sum(float(q['quantity']) for q in qs)
            res = sum(float(q.get('reserved_quantity') or 0) for q in qs)
            print(f"    QUANT principal(loc{ploc}): total={tot:.2f} reservado={res:.2f} livre={tot-res:.2f} ({len(qs)} quants)")


if __name__ == '__main__':
    main()
