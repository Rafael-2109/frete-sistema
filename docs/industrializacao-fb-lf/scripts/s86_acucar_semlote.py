"""s86 — fecha as exceções da S3: AÇÚCAR reservado + 3 quants SEM lote (42 -> 31092).

Reusa a mecânica provada do A4 (s82): action_confirm -> apagar move.lines auto (anti-dup
at_confirm) -> codificar move.line manual (quantity+lot+picked) -> finalizar_picking (s84,
trata wizard expiry). Migração interna = 0 SVL (neutra).

Modos (dry-run é DEFAULT; escrita só com --confirmar):
  --acucar    desreserva a saída FB 321794 -> migra o açúcar (lote 230326) 42->31092 ->
              re-reserva 321794 (agora de 31092, filha de 42).
  --semlote   PALLET/CORANTE (tracking=none) migram SEM lote; PIMENTAO (tracking=lot, resíduo)
              recebe lote A-16/06 (criado + atribuído ao quant) e migra.
Uso: python .../s86_acucar_semlote.py --acucar            # dry
     python .../s86_acucar_semlote.py --acucar --confirmar # go
"""
import sys, argparse, collections
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema_wire_r2')
from dotenv import load_dotenv
load_dotenv('/home/rafaelnascimento/projetos/frete_sistema/.env')
from app.odoo.utils.connection import get_odoo_connection
from app.odoo.estoque.scripts.picking import StockPickingService
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema_wire_r2/docs/industrializacao-fb-lf/scripts')
from s84_canary_recovery import finalizar_picking

CTX = {'allowed_company_ids': [1, 5], 'company_id': 5, 'lang': 'pt_BR'}
LOC_42, LOC_MP = 42, 31092
PT_INTERNO = 23
SAIDA_FB = 321794            # saída que reserva o açúcar
ACUCAR_CODE = '105000024'
SUGAR_LOT = '230326'
SEMLOTE = {'208000012': 'PALLET', '105000062': 'PIMENTAO', '104000046': 'CORANTE'}
LOTE_NOVO = 'A-16/06'


def _ex(o):
    def ex(m, meth, *a, **k):
        k.setdefault('context', CTX)
        return o.execute_kw(m, meth, list(a), k)
    return ex


def _migrar(o, ex, linhas, dst, origin):
    """linhas: [{product_id, lot_id|None, qty, src}]. Cria picking interno, codifica
    move.lines (anti-dup), valida tratando wizard. Retorna (pid, state)."""
    ps = StockPickingService(odoo=o)
    payload = [{'product_id': l['product_id'], 'quantity': l['qty'],
                'lot_id': l.get('lot_id'), 'name': f"Reestrut terceiros {l['product_id']}"} for l in linhas]
    pid = ps.criar_transferencia(5, 5, LOC_42, dst, payload, PT_INTERNO,
                                 partner_id=None, incoterm_id=None, carrier_id=None, origin=origin)
    ex('stock.picking', 'action_confirm', [pid])
    old = ex('stock.move.line', 'search', [('picking_id', '=', pid)])
    if old:
        ex('stock.move.line', 'unlink', old)
    moves = ex('stock.move', 'search_read', [('picking_id', '=', pid)],
               fields=['id', 'product_id', 'product_uom_qty'], order='id')
    mbp = collections.defaultdict(list)
    for mv in moves:
        mbp[mv['product_id'][0]].append(mv)
    lpp = collections.defaultdict(list)
    for l in linhas:
        lpp[l['product_id']].append(l)
    for prod, lns in lpp.items():
        mvs = mbp.get(prod, [])
        for i, l in enumerate(lns):
            mid = mvs[0]['id'] if len(mvs) == 1 else \
                next((m for m in mvs if abs(m['product_uom_qty'] - l['qty']) < 1e-9), mvs[min(i, len(mvs) - 1)])['id']
            ml = {'move_id': mid, 'picking_id': pid, 'product_id': prod, 'quantity': l['qty'],
                  'picked': True, 'location_id': l['src'], 'location_dest_id': dst, 'company_id': 5}
            if l.get('lot_id'):
                ml['lot_id'] = l['lot_id']
            ex('stock.move.line', 'create', [ml])
    return pid, finalizar_picking(o, pid)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--acucar', action='store_true')
    ap.add_argument('--semlote', action='store_true')
    ap.add_argument('--confirmar', action='store_true')
    args = ap.parse_args()
    o = get_odoo_connection(); assert o.authenticate(), 'falha auth'
    ex = _ex(o)
    print('=' * 80)

    if args.acucar:
        ac = ex('product.product', 'search_read', [('default_code', '=', ACUCAR_CODE)], fields=['id'])[0]['id']
        q = ex('stock.quant', 'search_read',
               [('product_id', '=', ac), ('location_id', '=', 42), ('quantity', '>', 0)],
               fields=['id', 'lot_id', 'quantity', 'reserved_quantity'])
        q = [x for x in q if x.get('lot_id') and SUGAR_LOT in str(x['lot_id'][1])]
        print(f"s86 AÇÚCAR — quant {q} | saída {SAIDA_FB}")
        if not q:
            print('  nada a migrar.'); return
        qd = q[0]
        print(f"  PLANO: do_unreserve({SAIDA_FB}) -> migrar {qd['quantity']} (lote {qd['lot_id'][1]}) 42->31092 -> action_assign({SAIDA_FB})")
        if not args.confirmar:
            print('  [DRY] use --confirmar'); return
        ex('stock.picking', 'do_unreserve', [SAIDA_FB])
        pid, st = _migrar(o, ex, [{'product_id': ac, 'lot_id': qd['lot_id'][0], 'qty': qd['quantity'], 'src': 42}],
                          LOC_MP, 'S3-ACUCAR-DE-TERCEIROS')
        ex('stock.picking', 'action_assign', [SAIDA_FB])
        saida = ex('stock.picking', 'read', [SAIDA_FB], fields=['state'])[0]
        print(f"  ✅ picking {pid} state={st} | saída {SAIDA_FB} re-reservada -> state={saida['state']}")
        return

    if args.semlote:
        prods = {p['default_code']: p for p in ex('product.product', 'search_read',
                 [('default_code', 'in', list(SEMLOTE))], fields=['id', 'default_code', 'tracking'])}
        linhas = []
        for code, p in prods.items():
            qs = ex('stock.quant', 'search_read',
                    [('product_id', '=', p['id']), ('location_id', '=', 42), ('lot_id', '=', False), ('quantity', '>', 0)],
                    fields=['id', 'quantity'])
            for qd in qs:
                lot_id = None
                if p['tracking'] != 'none':
                    if not args.confirmar:
                        lot_id = 'A-16/06(criar)'
                    else:
                        existe = ex('stock.lot', 'search', [('name', '=', LOTE_NOVO), ('product_id', '=', p['id'])])
                        if existe:
                            lot_id = existe[0]
                        else:
                            created = ex('stock.lot', 'create', [{'name': LOTE_NOVO, 'product_id': p['id'], 'company_id': 5}])
                            lot_id = created[0] if isinstance(created, list) else created
                        ex('stock.quant', 'write', [qd['id']], {'lot_id': lot_id})  # atribui lote ao quant (0 SVL, qty igual)
                linhas.append({'product_id': p['id'], 'lot_id': None if isinstance(lot_id, str) else lot_id,
                               'qty': qd['quantity'], 'src': 42, '_t': p['tracking'], '_c': code})
        print('s86 SEM-LOTE — plano:')
        for l in linhas:
            print(f"  [{l['_c']}] tracking={l['_t']} qty={l['qty']} lote={'A-16/06' if l['_t']!='none' else '(sem lote)'}")
        if not linhas:
            print('  nada a migrar.'); return
        if not args.confirmar:
            print('  [DRY] use --confirmar'); return
        pid, st = _migrar(o, ex, linhas, LOC_MP, 'S3-SEMLOTE-DE-TERCEIROS')
        print(f"  ✅ picking {pid} state={st}")
        return


if __name__ == '__main__':
    main()
