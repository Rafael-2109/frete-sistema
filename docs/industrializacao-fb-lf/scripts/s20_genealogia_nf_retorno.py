#!/usr/bin/env python3
"""S20 — GENEALOGIA da NF de retorno real (16x5902): COMO ela foi gerada?
Hipotese Rafael: as 5902 abrem via MO ou lista de materiais (nao manual, nao remessa).

READ-ONLY. Pega a NF de retorno real do shoyu (709632 default) e rastreia:
  1. header non-falsy (invoice_origin, ref, referencia_ids, create_uid/date)
  2. CADA linha-produto: create_uid + create_date + write_date (1 transacao? quem?)
     -> distingue: tudo no mesmo timestamp+uid = acao em lote (SA/botao/import)
  3. a origem (invoice_origin) resolvida em stock.picking E mrp.production
  4. se ha MO no ciclo, lista os move_raw_ids (componentes consumidos) e compara
     com as 16 linhas 5902 (a hipotese "abre via MO")

MODOS:
  --nf NF        NF de retorno (default 709632); tambem 708286, 574827
"""
import sys
import argparse
from collections import Counter
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5], 'company_id': 5, 'lang': 'pt_BR'}
NF_DEFAULT = 709632


def m2o(v):
    return f"{v[0]}|{v[1]}" if isinstance(v, list) and v else ('-' if not v else str(v))


def nf(d):
    return {k: v for k, v in sorted(d.items()) if v not in (False, None, '', 0, 0.0, [], ())}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--nf', type=int, default=NF_DEFAULT)
    args = ap.parse_args()
    o = get_odoo_connection(); assert o.authenticate(), "FALHA AUTH"

    def rd(model, ids, fields):
        ids = [i for i in ids if i]
        return o.execute_kw(model, 'read', [list(ids)], {'fields': fields, 'context': CTX}) if ids else []

    def rr(model, dom, fields, **kw):
        kw2 = {'fields': fields, 'context': CTX}; kw2.update(kw)
        return o.execute_kw(model, 'search_read', [dom], kw2)

    # 1) header
    mf = o.execute_kw('account.move', 'fields_get', [], {'attributes': ['type'], 'context': CTX})
    hwant = ['name', 'invoice_origin', 'ref', 'create_uid', 'create_date', 'write_uid', 'write_date',
             'journal_id', 'l10n_br_operacao_id', 'l10n_br_tipo_pedido', 'partner_id', 'amount_total',
             'l10n_br_referencia_ids', 'invoice_user_id', 'l10n_br_chave_nfe', 'state']
    hf = [f for f in hwant if f in mf]
    h = rd('account.move', [args.nf], hf)
    assert h, f"NF {args.nf} nao existe"
    h = h[0]
    print("=" * 88)
    print(f"=== 1) HEADER NF {args.nf} ===")
    for k, v in nf(h).items():
        print(f"   {k} = {v}")

    # 2) linhas-produto: quem/quando criou cada uma
    lf = o.execute_kw('account.move.line', 'fields_get', [], {'attributes': ['type'], 'context': CTX})
    lwant = ['product_id', 'l10n_br_cfop_codigo', 'l10n_br_operacao_id', 'create_uid', 'create_date',
             'write_uid', 'write_date', 'quantity', 'price_unit']
    # campos de vinculo a origem, se existirem
    for cand in ['sale_line_ids', 'purchase_line_id', 'l10n_br_origem_id', 'move_id',
                 'stock_move_id', 'l10n_br_documento_referenciado_id']:
        if cand in lf:
            lwant.append(cand)
    lfields = [f for f in lwant if f in lf]
    lines = rr('account.move.line', [('move_id', '=', args.nf), ('display_type', '=', 'product')],
               lfields, order='id')
    print(f"\n=== 2) {len(lines)} linhas-produto (create_uid/create_date — 1 transacao?) ===")
    for ln in lines:
        print(f"   {m2o(ln['product_id'])[:40]:40} cfop={ln.get('l10n_br_cfop_codigo'):>5} "
              f"by={m2o(ln.get('create_uid'))[:24]:24} at={ln.get('create_date')} wr={ln.get('write_date')}")
    cd = Counter(str(l.get('create_date')) for l in lines)
    cu = Counter(m2o(l.get('create_uid')) for l in lines)
    print(f"\n   create_date distintos: {dict(cd)}")
    print(f"   create_uid distintos : {dict(cu)}")
    # vinculos de origem presentes?
    for cand in ['sale_line_ids', 'purchase_line_id', 'l10n_br_origem_id', 'stock_move_id',
                 'l10n_br_documento_referenciado_id']:
        if cand in lfields:
            vals = [l.get(cand) for l in lines if l.get(cand)]
            print(f"   vinculo {cand}: {len(vals)}/{len(lines)} preenchidos -> {vals[:3]}")

    # 3) resolver invoice_origin em picking e MO
    org = h.get('invoice_origin')
    print(f"\n=== 3) origem '{org}' resolvida ===")
    if org:
        for token in str(org).replace(',', ' ').split():
            pk = rr('stock.picking', [('name', '=', token)], ['id', 'origin', 'group_id', 'picking_type_id'], limit=3)
            for p in pk:
                print(f"   stock.picking {p['id']} name={token} origin={p.get('origin')} "
                      f"type={m2o(p.get('picking_type_id'))} group={m2o(p.get('group_id'))}")
            mo = rr('mrp.production', [('name', '=', token)], ['id', 'product_id', 'state'], limit=3)
            for m in mo:
                print(f"   mrp.production {m['id']} name={token} prod={m2o(m.get('product_id'))} state={m.get('state')}")
            so = rr('sale.order', [('name', '=', token)], ['id', 'state'], limit=3)
            for s in so:
                print(f"   sale.order {s['id']} name={token} state={s.get('state')}")
    else:
        print("   (invoice_origin VAZIO — NF nao tem origem documental)")

    # 4) MO do PA no ciclo: move_raw_ids (componentes consumidos) vs as 5902
    print(f"\n=== 4) MO do PA (shoyu 4870112) — move_raw_ids vs as linhas 5902 ===")
    prod = rr('product.product', [('default_code', '=', '4870112')], ['id'], limit=1)
    if prod:
        pid = prod[0]['id']
        mos = rr('mrp.production', [('product_id', '=', pid)], ['id', 'name', 'state', 'date_finished'],
                 order='id desc', limit=3)
        for mo in mos:
            raws = rr('stock.move', [('raw_material_production_id', '=', mo['id'])],
                      ['product_id', 'product_uom_qty'], limit=40)
            print(f"   MO {mo['id']} {mo['name']} state={mo['state']}: {len(raws)} componentes (move_raw_ids)")
            for r in raws[:20]:
                print(f"       - {m2o(r['product_id'])[:50]:50} qty={r.get('product_uom_qty')}")


if __name__ == '__main__':
    main()
