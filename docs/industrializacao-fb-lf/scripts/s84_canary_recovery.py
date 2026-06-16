"""s84 — RECOVERY do canary A4 que falhou no button_validate (sem reserva).

Modos:
  --diag      (default, READ) lista pickings origin S3-REESTRUT* + estado dos moves/move_lines
              (qty reservada vs qty_done) p/ entender por que action_assign não reservou.
  --limpar    cancela+apaga os pickings NÃO-done do origin (limpa o rabo do experimento).
              GATED por --confirmar. button_validate done NUNCA é tocado.

Uso: python .../s84_canary_recovery.py --diag
     python .../s84_canary_recovery.py --limpar --confirmar
"""
import sys, argparse
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema_wire_r2')
from dotenv import load_dotenv
load_dotenv('/home/rafaelnascimento/projetos/frete_sistema/.env')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5], 'company_id': 5, 'lang': 'pt_BR'}
ORIGIN_LIKE = 'S3-REESTRUT%'

# wizards que o button_validate pode disparar (Odoo) e o método que confirma cada um
WIZ_METHODS = {
    'expiry.picking.confirmation': 'process',        # lotes a vencer/vencidos (product_expiry)
    'stock.immediate.transfer': 'process',
    'stock.backorder.confirmation': 'process_cancel_backorder',
}


def finalizar_picking(o, pid, max_wiz=6):
    """button_validate tratando wizards ENCADEADOS (expiry/immediate/backorder)
    até o picking ficar 'done'. Retorna o state final. Reusado pelo s82 (A4)."""
    ctx = dict(CTX); ctx.update({'skip_backorder': True, 'picking_ids_not_to_backorder': [pid]})

    def state():
        return o.execute_kw('stock.picking', 'read', [[pid]], {'fields': ['state'], 'context': CTX})[0]['state']

    try:
        action = o.execute_kw('stock.picking', 'button_validate', [[pid]], {'context': ctx})
    except Exception as e:
        if 'cannot marshal None' in str(e):
            return state()
        raise
    for _ in range(max_wiz):
        if not (isinstance(action, dict) and action.get('res_model')):
            break
        rm = action['res_model']; rid = action.get('res_id'); ctxw = dict(action.get('context') or ctx)
        meth = WIZ_METHODS.get(rm, 'process')
        wid = rid or o.execute_kw(rm, 'create', [{}], {'context': ctxw})
        try:
            action = o.execute_kw(rm, meth, [[wid]], {'context': ctxw})
        except Exception as e:
            if 'cannot marshal None' in str(e):
                action = None
            else:
                raise
    return state()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--diag', action='store_true')
    ap.add_argument('--limpar', action='store_true')
    ap.add_argument('--quant', nargs='*', default=None, help='product_ids p/ inspecionar quants em child_of 42')
    ap.add_argument('--finalizar', type=int, default=0, help='button_validate tratando wizard, p/ PID')
    ap.add_argument('--confirmar', action='store_true')
    args = ap.parse_args()
    o = get_odoo_connection()
    assert o.authenticate(), 'falha auth'

    if args.finalizar:
        print('STATE FINAL:', finalizar_picking(o, args.finalizar))
        return

    if args.quant is not None:
        codes = args.quant or ['29']
        prods = o.execute_kw('product.product', 'search_read', [[('default_code', 'in', codes)]],
                             {'fields': ['id', 'default_code'], 'context': CTX})
        pids = [p['id'] for p in prods]
        print(f"  resolvido default_code {codes} -> product_ids {[(p['id'], p['default_code']) for p in prods]}")
        sub42 = [l['id'] for l in o.execute_kw('stock.location', 'search_read',
                 [[('id', 'child_of', 42)]], {'fields': ['id', 'complete_name'], 'context': CTX})]
        locname = {l['id']: l['complete_name'] for l in o.execute_kw('stock.location', 'read',
                   [sub42], {'fields': ['complete_name'], 'context': CTX})}
        qs = o.execute_kw('stock.quant', 'search_read',
                          [[('product_id', 'in', pids), ('quantity', '!=', 0),
                            ('location_id.usage', '=', 'internal'), ('company_id', 'in', [1, 5])]],
                          {'fields': ['product_id', 'location_id', 'lot_id', 'quantity',
                                      'reserved_quantity', 'available_quantity', 'company_id'], 'context': CTX})
        print('=' * 88)
        print(f"s84 --quant {pids}: quants internos company[1,5]={len(qs)} (child_of42 ids={len(sub42)})")
        for q in qs:
            loc = q['location_id'][0]
            print(f"  prod={q['product_id'][1][:30]:30s} loc=[{loc}]{locname.get(loc,'?')[:34]:34s} "
                  f"lot={q.get('lot_id') and q['lot_id'][1]} qty={q['quantity']} "
                  f"reserv={q['reserved_quantity']} avail={q.get('available_quantity')}")
        return

    picks = o.execute_kw('stock.picking', 'search_read',
                         [[('origin', 'like', ORIGIN_LIKE)]],
                         {'fields': ['id', 'name', 'state', 'origin', 'location_id', 'location_dest_id'],
                          'context': CTX, 'order': 'id desc'})
    print('=' * 88)
    print(f's84 — pickings origin {ORIGIN_LIKE}: {len(picks)}')
    for p in picks:
        print(f"\n  [{p['id']}] {p['name']} state={p['state']} "
              f"{p['location_id'][1]} -> {p['location_dest_id'][1]}")
        moves = o.execute_kw('stock.move', 'search_read', [[('picking_id', '=', p['id'])]],
                             {'fields': ['id', 'product_id', 'product_uom_qty', 'quantity',
                                         'picked', 'state'], 'context': CTX})
        for m in moves:
            print(f"     move {m['id']} {m['product_id'][1][:34]:34s} demand={m['product_uom_qty']} "
                  f"qty(done)={m.get('quantity')} picked={m.get('picked')} state={m['state']}")
        mls = o.execute_kw('stock.move.line', 'search_read', [[('picking_id', '=', p['id'])]],
                           {'fields': ['id', 'product_id', 'lot_id', 'quantity', 'picked'], 'context': CTX})
        print(f"     move_lines: {len(mls)}")
        for ml in mls[:8]:
            print(f"       ml {ml['id']} {ml['product_id'][1][:28]:28s} lot={ml.get('lot_id') and ml['lot_id'][1]} qty={ml.get('quantity')} picked={ml.get('picked')}")

    if args.limpar:
        alvos = [p['id'] for p in picks if p['state'] != 'done']
        print(f"\n### LIMPAR — pickings não-done: {alvos}")
        if not alvos:
            print('  nada a limpar.'); return
        if not args.confirmar:
            print('  [DRY] use --confirmar p/ cancelar+apagar'); return
        o.execute_kw('stock.picking', 'action_cancel', [alvos], {'context': CTX})
        o.execute_kw('stock.picking', 'unlink', [alvos], {'context': CTX})
        print(f'  ✅ cancelado+apagado: {alvos}')


if __name__ == '__main__':
    main()
