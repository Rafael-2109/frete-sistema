#!/usr/bin/env python3
"""S7 PICKING vs LINHAS DA NF (READ-only) — Frente 1: as linhas 5902 (insumos) da VND
mista tem stock.move proprio no picking, ou sao compostas pelo CIEL IT (sem move)?

Decide se "separar em 2 NF = 2 pickings" e' direto (cada linha = 1 move) ou se a NF de
insumos seria um documento SEM movimento fisico (= precisa veiculo/picking simbolico).

Compara, para a VND e a ENTSI: nº de linhas-produto por CFOP  x  nº de stock.moves do picking.
NAO escreve nada.
"""
import sys
import argparse
from collections import Counter
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5]}


def m2o(v):
    return f"{v[0]}|{v[1]}" if isinstance(v, list) and v else ('-' if not v else str(v))


def cf(v):
    return v[1].split(' - ')[0].strip() if isinstance(v, list) and v else '-'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--moves', nargs='*', type=int, default=[738097], help='account.move ids (VND/ENTSI)')
    args = ap.parse_args()

    o = get_odoo_connection()
    assert o.authenticate(), "FALHA AUTH"
    print(f"UID {o._uid}")

    def rr(model, domain, fields, **kw):
        return o.execute_kw(model, 'search_read', [domain], {'fields': fields, 'context': CTX, **kw})

    def rd(model, ids, fields):
        return o.execute_kw(model, 'read', [list(ids)], {'fields': fields, 'context': CTX}) if ids else []

    for mid in args.moves:
        print("\n" + "#" * 88)
        mv = rd('account.move', [mid], ['name', 'invoice_origin', 'ref', 'move_type', 'journal_id'])[0]
        print(f"# {mv['name']} (move {mid}) {mv.get('move_type')} j={m2o(mv.get('journal_id'))}")
        print(f"#   invoice_origin={mv.get('invoice_origin')} ref={mv.get('ref')}")
        print("#" * 88)

        # linhas-produto por CFOP
        lines = rr('account.move.line', [('move_id', '=', mid), ('product_id', '!=', False),
                                         ('display_type', '=', 'product')],
                   ['product_id', 'l10n_br_cfop_id', 'quantity'], limit=400)
        by_cfop = Counter(cf(l.get('l10n_br_cfop_id')) for l in lines)
        prods_nf = {l['product_id'][0] for l in lines if isinstance(l.get('product_id'), list)}
        print(f"\n  LINHAS-produto na NF: {len(lines)} | por CFOP: {dict(by_cfop)} | produtos distintos: {len(prods_nf)}")

        # picking de origem
        cand = []
        for src in (mv.get('invoice_origin'), mv.get('ref')):
            if src:
                cand += [x.strip() for x in str(src).split(',') if x.strip()]
        pk = None
        for nm in cand:
            r = rr('stock.picking', [('name', '=', nm)], ['id', 'name', 'sale_id', 'origin', 'group_id'], limit=1)
            if r:
                pk = r[0]; break
        if not pk:
            # talvez ref seja uma SO -> picking
            print(f"  (sem picking por name em {cand}; tentando sale.order)")
            for nm in cand:
                so = rr('sale.order', [('name', '=', nm)], ['id', 'name', 'picking_ids'], limit=1)
                if so and so[0].get('picking_ids'):
                    pkr = rd('stock.picking', so[0]['picking_ids'][:1], ['id', 'name', 'sale_id', 'origin'])
                    if pkr:
                        pk = pkr[0]; break
        if not pk:
            print("  >>> picking NAO localizado — linhas da NF provavelmente compostas pela SO/CIEL IT")
            # mostrar SO se invoice_origin for SO
            continue

        moves = rr('stock.move', [('picking_id', '=', pk['id'])],
                   ['product_id', 'quantity', 'state'], limit=400)
        prods_mv = {mm['product_id'][0] for mm in moves if isinstance(mm.get('product_id'), list)}
        print(f"\n  PICKING {pk['id']} {pk['name']} (sale_id={m2o(pk.get('sale_id'))} origin={pk.get('origin')})")
        print(f"  stock.moves: {len(moves)} | produtos distintos no picking: {len(prods_mv)}")
        # produtos na NF mas SEM move (=simbolicos/compostos)
        sem_move = prods_nf - prods_mv
        com_move = prods_nf & prods_mv
        print(f"  produtos da NF COM move fisico: {len(com_move)} | SEM move (simbolico/composto): {len(sem_move)}")
        if sem_move:
            amostra = rd('product.product', list(sem_move)[:10], ['default_code', 'name'])
            print("  amostra SEM move (linhas fiscais sem movimento fisico):")
            for p in amostra:
                print(f"     [{p.get('default_code')}] {p.get('name')[:40]}")
        if com_move:
            amostra = rd('product.product', list(com_move)[:10], ['default_code', 'name'])
            print("  COM move (movimento fisico real):")
            for p in amostra:
                print(f"     [{p.get('default_code')}] {p.get('name')[:40]}")

        # a SO tem as linhas 5902? (de onde vem a composicao)
        if pk.get('sale_id'):
            sol = rr('sale.order.line', [('order_id', '=', pk['sale_id'][0]), ('product_id', '!=', False)],
                     ['product_id', 'l10n_br_cfop_id', 'product_uom_qty'], limit=400)
            by = Counter(cf(s.get('l10n_br_cfop_id')) for s in sol)
            print(f"\n  SALE.ORDER {m2o(pk.get('sale_id'))}: {len(sol)} linhas | por CFOP: {dict(by)}")

    print("\n[FIM s7_vnd_picking_vs_nf — READ-only]")


if __name__ == '__main__':
    main()
