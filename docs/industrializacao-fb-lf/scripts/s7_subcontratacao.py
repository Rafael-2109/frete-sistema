#!/usr/bin/env python3
"""S7 SUBCONTRATACAO + FLUXO DE ENTRADA (READ-only) — o ciclo remessa+retorno+escrituracao
pode ser orquestrado por 1 PO de subcontratacao (nativo Odoo), com rastreabilidade nativa?

Investiga:
  1. BoM 14794 (subcontract) do azeite: subcontractor_ids, em uso?
  2. a PO que originou a ENTSI 506211 (origin=C2615462): e' de subcontratacao? liga PA<->componentes?
     linhas, partner, pickings (resupply + recebimento PA), invoices.
  3. picking_types de subcontratacao (resupply/production) p/ a LF.
  4. como a NF de entrada (ENTSI) e' criada (via PO? via DFe? create_uid).

NAO escreve nada.
"""
import sys
import argparse
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5]}


def m2o(v):
    return f"{v[0]}|{v[1]}" if isinstance(v, list) and v else ('-' if not v else str(v))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--po-name', default='C2615462', help='origin da ENTSI (PO)')
    ap.add_argument('--entsi', type=int, default=506211)
    ap.add_argument('--bom-sub', type=int, default=14794)
    args = ap.parse_args()

    o = get_odoo_connection()
    assert o.authenticate(), "FALHA AUTH"
    print(f"UID {o._uid}")

    def rr(model, domain, fields, **kw):
        return o.execute_kw(model, 'search_read', [domain], {'fields': fields, 'context': CTX, **kw})

    def rd(model, ids, fields):
        return o.execute_kw(model, 'read', [list(ids)], {'fields': fields, 'context': CTX}) if ids else []

    def has_fields(model, *names):
        fg = o.execute_kw(model, 'fields_get', [], {'attributes': [], 'context': CTX})
        return [n for n in names if n in fg]

    # 1) BoM subcontract
    print("\n" + "=" * 88)
    print("1) BoM 14794 (subcontract) — subcontratante + uso")
    print("=" * 88)
    b = rd('mrp.bom', [args.bom_sub], ['id', 'type', 'product_tmpl_id', 'product_id', 'subcontractor_ids', 'product_qty'])
    if b:
        b = b[0]
        print(f"  BoM {b['id']} type={b.get('type')} tmpl={m2o(b.get('product_tmpl_id'))} subcontractor_ids={b.get('subcontractor_ids')}")
        subs = rd('res.partner', b.get('subcontractor_ids') or [], ['id', 'name', 'l10n_br_cnpj'])
        for s in subs:
            print(f"     subcontratante: {s['id']}|{s.get('name')} cnpj={s.get('l10n_br_cnpj')}")

    # 2) a PO que originou a ENTSI
    print("\n" + "=" * 88)
    print(f"2) PO origin da ENTSI (name={args.po_name!r})")
    print("=" * 88)
    poflds = ['id', 'name', 'partner_id', 'origin', 'state', 'date_order', 'picking_ids', 'invoice_ids',
              'order_line', 'l10n_br_tipo_pedido', 'company_id']
    poflds = ['id', 'name', 'partner_id', 'origin', 'state', 'picking_ids', 'invoice_ids', 'order_line',
              'company_id'] + has_fields('purchase.order', 'l10n_br_tipo_pedido', 'subcontract', 'is_subcontract')
    po = rr('purchase.order', [('name', '=', args.po_name)], list(dict.fromkeys(poflds)), limit=3)
    for p in po:
        print(f"  PO {p['id']} {p['name']} partner={m2o(p.get('partner_id'))} state={p.get('state')} "
              f"company={m2o(p.get('company_id'))}")
        print(f"     origin={p.get('origin')} pickings={p.get('picking_ids')} invoices={p.get('invoice_ids')}")
        for k in p:
            if 'subcontract' in k.lower() or 'tipo_pedido' in k.lower():
                print(f"     {k} = {p.get(k)}")
        pol = rd('purchase.order.line', p.get('order_line') or [],
                 ['product_id', 'product_qty', 'price_unit'])
        print(f"     order_line: {len(pol)}")
        for l in pol[:12]:
            print(f"        {m2o(l.get('product_id'))[:34]:34} qty={l.get('product_qty')} pu={l.get('price_unit')}")
        # pickings da PO (resupply + recebimento?)
        pks = rd('stock.picking', p.get('picking_ids') or [],
                 ['id', 'name', 'picking_type_id', 'location_id', 'location_dest_id', 'state'])
        for pk in pks:
            print(f"     picking {pk['id']} {pk['name']} pt={m2o(pk.get('picking_type_id'))} "
                  f"{m2o(pk.get('location_id'))}->{m2o(pk.get('location_dest_id'))} {pk.get('state')}")

    # 3) a ENTSI: como nasce
    print("\n" + "=" * 88)
    print(f"3) ENTSI {args.entsi} — create_uid + vinculo PO/DFe")
    print("=" * 88)
    extra = has_fields('account.move', 'l10n_br_tipo_pedido_entrada', 'dfe_id', 'l10n_br_dfe_id', 'purchase_id')
    mv = rd('account.move', [args.entsi],
            ['id', 'name', 'create_uid', 'invoice_origin', 'ref', 'journal_id', 'move_type'] + extra)
    if mv:
        for k, v in mv[0].items():
            if k != 'id' and v not in (False, None, ''):
                print(f"  {k:30} = {m2o(v) if isinstance(v, list) else v}")

    # 4) picking_types de subcontratacao na LF/FB
    print("\n" + "=" * 88)
    print("4) picking_types de subcontratacao (resupply/production) — existem?")
    print("=" * 88)
    pts = rr('stock.picking.type', ['|', ('name', 'ilike', 'subcontrat'), ('name', 'ilike', 'terceir')],
             ['id', 'name', 'code', 'company_id', 'default_location_src_id', 'default_location_dest_id'], limit=30)
    for t in pts:
        print(f"   pt{t['id']:5} {t['name'][:40]:40} code={t.get('code'):10} company={m2o(t.get('company_id'))[:18]}")
    # locations de subcontratacao
    locs = rr('stock.location', [('usage', '=', 'production'), ('name', 'ilike', 'subcontr')],
              ['id', 'name', 'company_id'], limit=20)
    print(f"\n  locations production/subcontract: {len(locs)}")
    for l in locs[:10]:
        print(f"   loc {l['id']} {l['name']} company={m2o(l.get('company_id'))}")

    print("\n[FIM s7_subcontratacao — READ-only]")


if __name__ == '__main__':
    main()
