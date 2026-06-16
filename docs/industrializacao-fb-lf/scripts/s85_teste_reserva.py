"""s85 — TESTE EMPÍRICO da causa do A4 (action_assign não reserva em move 42->31092).

Cria pickings de teste pt23 com 1 move (qty 1) e roda action_confirm+action_assign,
lê o estado (move.state + nº move_lines reservadas) e CANCELA+APAGA no finally (zero rabo;
reserva NÃO move estoque). Contraste: dst=31092 (FILHA de 42) vs dst não-descendente de 42.

Conclusão esperada: se filha NÃO reserva e contraste reserva -> causa = move pai->filha.
Uso: python .../s85_teste_reserva.py   (escrita inócua + auto-limpeza)
"""
import sys
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema_wire_r2')
from dotenv import load_dotenv
load_dotenv('/home/rafaelnascimento/projetos/frete_sistema/.env')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5], 'company_id': 5, 'lang': 'pt_BR'}
PROD, LOT, QTY, SRC, PT = 27756, 4788, 1.0, 42, 23


def main():
    o = get_odoo_connection()
    assert o.authenticate(), 'falha auth'

    def ex(model, method, *args, **kw):
        kw.setdefault('context', CTX)
        return o.execute_kw(model, method, list(args), kw)

    uom = ex('product.product', 'read', [PROD], fields=['uom_id'])[0]['uom_id'][0]
    sub42 = set(l['id'] for l in ex('stock.location', 'search_read', [('id', 'child_of', 42)], fields=['id']))
    # contraste: location internal company5, NÃO descendente de 42 (preferir 53 Pré-Produção)
    cand = ex('stock.location', 'search_read',
              [('usage', '=', 'internal'), ('company_id', '=', 5), ('id', 'not in', list(sub42))],
              fields=['id', 'complete_name'])
    contraste = next((c for c in cand if c['id'] == 53), cand[0] if cand else None)
    print(f"contraste (não-filha de 42): {contraste}")

    def teste(dst, rotulo):
        pid = ex('stock.picking', 'create', {
            'picking_type_id': PT, 'location_id': SRC, 'location_dest_id': dst, 'company_id': 5})
        mid = ex('stock.move', 'create', {
            'name': 'S85-TESTE', 'product_id': PROD, 'product_uom_qty': QTY, 'product_uom': uom,
            'location_id': SRC, 'location_dest_id': dst, 'picking_id': pid, 'company_id': 5})
        try:
            ex('stock.picking', 'action_confirm', [pid])
            ex('stock.picking', 'action_assign', [pid])
            mv = ex('stock.move', 'read', [mid], fields=['state', 'quantity', 'picked'])[0]
            mls = ex('stock.move.line', 'search_read', [('move_id', '=', mid)],
                     fields=['quantity', 'location_id', 'location_dest_id'])
            print(f"  [{rotulo}] dst={dst} move.state={mv['state']} qty={mv.get('quantity')} "
                  f"move_lines={len(mls)} {[(m['quantity'], m['location_id'][1], m['location_dest_id'][1]) for m in mls]}")
        finally:
            ex('stock.picking', 'action_cancel', [pid])
            ex('stock.picking', 'unlink', [pid])
            print(f"  [{rotulo}] picking {pid} limpo")

    print('=' * 80)
    teste(31092, 'FILHA de 42 (caso real A4)')
    if contraste:
        teste(contraste['id'], 'CONTRASTE não-filha')


if __name__ == '__main__':
    main()
