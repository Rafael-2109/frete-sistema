#!/usr/bin/env python3
"""S7 FONTE DOS INSUMOS 5902 (READ-only) — de onde o CIEL IT expande as linhas de insumos
ao faturar o picking do PA? (BoM do PA × remessa 5901 vinculada × vínculo do stock.move)

Cruza, para a VND/2026/00359 (PA 4739099, move PA 1176773, picking 322836):
  1. os 9 insumos 5902 da NF  vs  a BoM do PA (mrp.bom) — batem? (=> fonte BoM)
  2. vínculos do stock.move do PA (move_orig/dest, origin, production, bom_line) — aponta remessa/MO?
  3. campos do wizard stock.invoice.onshipping (industri/remessa/origem)
  4. existe remessa de entrada (1901) na LF p/ o PA? (=> fonte remessa)

NAO escreve nada. Uso: python s7_fonte_insumos.py [--pa-prod 27753] [--move-nf 738097] [--move-pa 1176773]
"""
import sys
import argparse
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5]}


def m2o(v):
    return f"{v[0]}|{v[1]}" if isinstance(v, list) and v else ('-' if not v else str(v))


def cf(v):
    return v[1].split(' - ')[0].strip() if isinstance(v, list) and v else '-'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pa-prod', type=int, default=27753, help='product.product do PA (4739099=27753)')
    ap.add_argument('--move-nf', type=int, default=738097, help='account.move da VND')
    ap.add_argument('--move-pa', type=int, default=1176773, help='stock.move do PA no picking')
    args = ap.parse_args()

    o = get_odoo_connection()
    assert o.authenticate(), "FALHA AUTH"
    print(f"UID {o._uid}")

    def rr(model, domain, fields, **kw):
        return o.execute_kw(model, 'search_read', [domain], {'fields': fields, 'context': CTX, **kw})

    def rd(model, ids, fields):
        return o.execute_kw(model, 'read', [list(ids)], {'fields': fields, 'context': CTX}) if ids else []

    def fields_like(model, *needles):
        fg = o.execute_kw(model, 'fields_get', [], {'attributes': ['string', 'type', 'relation'], 'context': CTX})
        return {k: v for k, v in fg.items() if any(n in k.lower() for n in needles)}

    # produto PA + template
    pa = rd('product.product', [args.pa_prod], ['id', 'default_code', 'name', 'product_tmpl_id'])
    tmpl_id = pa[0]['product_tmpl_id'][0] if pa and isinstance(pa[0].get('product_tmpl_id'), list) else None
    print(f"\nPA = {pa[0].get('default_code')} {pa[0].get('name')[:40]} (product {args.pa_prod}, tmpl {tmpl_id})")

    # ----------------------------------------------------------------
    # 1) os insumos 5902 da NF
    # ----------------------------------------------------------------
    print("\n" + "=" * 88)
    print("1) INSUMOS 5902 na NF  vs  BoM do PA")
    print("=" * 88)
    ln = rr('account.move.line', [('move_id', '=', args.move_nf), ('product_id', '!=', False)],
            ['product_id', 'l10n_br_cfop_id', 'quantity', 'price_unit'], limit=300)
    insumos_nf = {l['product_id'][0]: l for l in ln if cf(l.get('l10n_br_cfop_id')) == '5902'}
    pa_lines = [l for l in ln if cf(l.get('l10n_br_cfop_id')) == '5124']
    print(f"  linhas 5124 (PA): {[m2o(l['product_id']) for l in pa_lines]}")
    print(f"  linhas 5902 (insumos): {len(insumos_nf)} produtos")

    # BoM do PA (por product_id OU template)
    boms = rr('mrp.bom', ['|', ('product_id', '=', args.pa_prod), ('product_tmpl_id', '=', tmpl_id)],
              ['id', 'code', 'type', 'product_id', 'product_tmpl_id', 'product_qty', 'bom_line_ids'], limit=10)
    print(f"\n  BoMs do PA: {len(boms)}")
    bom_prods = set()
    for b in boms:
        print(f"   BoM {b['id']} code={b.get('code')} type={b.get('type')} qty={b.get('product_qty')} "
              f"linhas={len(b.get('bom_line_ids') or [])}")
        bls = rd('mrp.bom.line', b.get('bom_line_ids') or [], ['product_id', 'product_qty'])
        for bl in bls:
            if isinstance(bl.get('product_id'), list):
                bom_prods.add(bl['product_id'][0])
    # cruzamento
    nf_prods = set(insumos_nf.keys())
    print(f"\n  produtos na BoM: {len(bom_prods)} | insumos 5902 na NF: {len(nf_prods)}")
    inter = nf_prods & bom_prods
    print(f"  >>> 5902 que ESTAO na BoM: {len(inter)}/{len(nf_prods)}  "
          f"({'FONTE = BoM (batem)' if inter and len(inter) >= len(nf_prods) * 0.6 else 'NAO batem com BoM'})")
    so_nf = nf_prods - bom_prods
    if so_nf:
        amostra_fora = rd('product.product', list(so_nf)[:10], ['default_code', 'name'])
        print(f"  5902 que NAO estao na BoM ({len(so_nf)}):")
        for p in amostra_fora:
            print(f"     [{p.get('default_code')}] {p.get('name')[:38]}")

    # ----------------------------------------------------------------
    # 2) vínculos do stock.move do PA
    # ----------------------------------------------------------------
    print("\n" + "=" * 88)
    print("2) VINCULOS do stock.move do PA (move {})".format(args.move_pa))
    print("=" * 88)
    mv_fields = fields_like('stock.move', 'bom', 'production', 'origin', 'industri', 'remessa',
                            'raw', 'dfe', 'invoice', 'purchase', 'sale')
    flds = ['id', 'product_id', 'origin', 'move_orig_ids', 'move_dest_ids'] + list(mv_fields.keys())
    flds = list(dict.fromkeys(flds))  # dedup
    try:
        mv = rd('stock.move', [args.move_pa], flds)
    except Exception as e:
        print(f"  (alguns campos falharam: {e}); tentando minimo")
        mv = rd('stock.move', [args.move_pa], ['id', 'product_id', 'origin', 'move_orig_ids', 'move_dest_ids'])
    if mv:
        for k, v in mv[0].items():
            if k == 'id':
                continue
            if v not in (False, [], None):
                print(f"  {k:34} = {m2o(v) if isinstance(v, list) and len(v)==2 and isinstance(v[1],str) else v}")

    # ----------------------------------------------------------------
    # 3) wizard stock.invoice.onshipping — campos de industrializacao/origem
    # ----------------------------------------------------------------
    print("\n" + "=" * 88)
    print("3) stock.invoice.onshipping — campos (industri/remessa/origem/bom/component)")
    print("=" * 88)
    wf = fields_like('stock.invoice.onshipping', 'industri', 'remessa', 'origin', 'bom',
                     'component', 'insumo', 'retorno', 'devol', 'simbol')
    for k, v in wf.items():
        print(f"   {k:34} {v.get('type'):10} {v.get('string')}  rel={v.get('relation')}")
    if not wf:
        print("   (nenhum campo com essas palavras — expansao provavelmente no metodo create_invoice)")

    # ----------------------------------------------------------------
    # 4) campos l10n_br no picking que apontem origem/remessa
    # ----------------------------------------------------------------
    print("\n" + "=" * 88)
    print("4) stock.picking — campos l10n_br/origem/industrializacao (no picking 322836)")
    print("=" * 88)
    pf = fields_like('stock.picking', 'industri', 'remessa', 'l10n_br', 'origin', 'devol', 'retorno', 'nota', 'dfe')
    chave = list(pf.keys())
    pkv = rd('stock.picking', [322836], ['id'] + chave) if chave else []
    if pkv:
        for k in chave:
            v = pkv[0].get(k)
            if v not in (False, [], None, ''):
                print(f"  {k:36} = {m2o(v) if isinstance(v, list) else v}")

    print("\n[FIM s7_fonte_insumos — READ-only]")


if __name__ == '__main__':
    main()
