"""Inspeciona invoices antes do SEFAZ. Uso: python fat_lf_inspect_invoice.py 678566 678567 678569"""
import os
import sys
import warnings
warnings.simplefilter('ignore')
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from app import create_app  # noqa: E402
from app.odoo.utils.connection import get_odoo_connection  # noqa: E402

ESPERADO = {  # por l10n_br_tipo_pedido
    'industrializacao': {'cfop': '5901', 'fp': 25},
    'perda': {'cfop': '5903', 'fp': 91},
    'dev-industrializacao': {'cfop': '5949', 'fp': 89},
}


def main():
    ids = [int(x) for x in sys.argv[1:]]
    app = create_app()
    with app.app_context():
        odoo = get_odoo_connection()
        moves = odoo.read('account.move', ids,
                          ['name', 'state', 'move_type', 'ref', 'invoice_origin',
                           'fiscal_position_id', 'l10n_br_tipo_pedido', 'company_id',
                           'amount_total', 'amount_untaxed', 'invoice_line_ids', 'partner_id'])
        for m in moves:
            print('=' * 70)
            tp = m.get('l10n_br_tipo_pedido')
            fp = m['fiscal_position_id'][1] if m.get('fiscal_position_id') else None
            fpid = m['fiscal_position_id'][0] if m.get('fiscal_position_id') else None
            print(f"  account.move id={m['id']} name={m.get('name')} state={m['state']} type={m['move_type']}")
            print(f"  company={m['company_id'][1] if m.get('company_id') else '?'} partner={m['partner_id'][1] if m.get('partner_id') else '?'}")
            print(f"  ref={m.get('ref')} origin={m.get('invoice_origin')}")
            print(f"  l10n_br_tipo_pedido={tp!r}  fiscal_position={fp!r} (id={fpid})")
            print(f"  amount_untaxed={m.get('amount_untaxed')}  amount_total={m.get('amount_total')}")
            exp = ESPERADO.get(tp)
            if exp:
                print(f"  ESPERADO p/ {tp}: CFOP {exp['cfop']}, fiscal_position_id {exp['fp']} -> "
                      f"FP {'OK' if fpid == exp['fp'] else 'DIVERGENTE!!'}")
            # linhas
            lines = odoo.read('account.move.line', m['invoice_line_ids'],
                              ['product_id', 'quantity', 'price_unit', 'price_subtotal',
                               'l10n_br_cfop_id', 'name'])
            for ln in lines:
                cfop = ln['l10n_br_cfop_id'][1] if ln.get('l10n_br_cfop_id') else None
                prod = ln['product_id'][1] if ln.get('product_id') else '?'
                print(f"    LINHA: {prod[:45]:45} qty={ln.get('quantity')} "
                      f"pu={ln.get('price_unit')} subtotal={ln.get('price_subtotal')} CFOP={cfop}")


if __name__ == '__main__':
    main()
