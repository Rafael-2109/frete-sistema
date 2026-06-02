#!/usr/bin/env python3
"""S7 PERNA FISICA da SARET + picking_types do retorno (READ-only) — Frente 1.

A SARET (NF de retorno de insumos SEPARADA) nasce de um picking `LF/LF/SAI/RETIND/...`
(visto em account.move.ref; invoice_origin vem False). Este script:

  1. Acha o picking de origem da SARET (via ref) -> picking_type, locations, tipo_pedido,
     stock.moves, lote, SVL (= simbolica? valor 0?).
  2. Confirma a regra do robo (R2c): picking_type.l10n_br_tipo_pedido -> journal.
     -> PROVA "2 NF = 2 pickings com picking_type/tipo_pedido distintos".
  3. Mapeia os picking_types candidatos do retorno na LF (pt98 + tipo_pedido relevantes)
     para desenhar a separacao serviço (j847) x insumos (j1002-like).

READ-only. Uso: python s7_saret_fisico.py [--ref LF/LF/SAI/RETIND/00009 ...]
"""
import sys
import argparse
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5]}


def m2o(v):
    if isinstance(v, list) and v:
        return f"{v[0]}|{v[1]}"
    return '-' if v is False or v is None else str(v)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ref', nargs='*', default=['LF/LF/SAI/RETIND/00009', 'LF/LF/SAI/RETIND/00003'],
                    help='refs (name) dos pickings RETIND a dissecar')
    args = ap.parse_args()

    o = get_odoo_connection()
    assert o.authenticate(), "FALHA AUTH"
    print(f"UID {o._uid}  CTX={CTX}")

    def rr(model, domain, fields, **kw):
        kwargs = {'fields': fields, 'context': CTX}
        kwargs.update(kw)
        return o.execute_kw(model, 'search_read', [domain], kwargs)

    PT_FLD = ['id', 'name', 'code', 'l10n_br_tipo_pedido', 'warehouse_id', 'company_id',
              'default_location_src_id', 'default_location_dest_id', 'sequence_code']

    def dump_pt(pt_id):
        pt = rr('stock.picking.type', [('id', '=', pt_id)], PT_FLD)
        for t in pt:
            print(f"     picking_type {t['id']} {t['name']!r} code={t.get('code')} "
                  f"company={m2o(t.get('company_id'))} seq={t.get('sequence_code')}")
            print(f"        l10n_br_tipo_pedido={t.get('l10n_br_tipo_pedido')!r}  "
                  f"src={m2o(t.get('default_location_src_id'))} dst={m2o(t.get('default_location_dest_id'))}")

    # ------------------------------------------------------------------
    # 1) picking de origem de cada SARET (via ref/name)
    # ------------------------------------------------------------------
    for ref in args.ref:
        print("\n" + "#" * 92)
        print(f"# PICKING de origem: ref={ref!r}")
        print("#" * 92)
        pks = rr('stock.picking', [('name', '=', ref)],
                 ['id', 'name', 'state', 'picking_type_id', 'location_id', 'location_dest_id',
                  'origin', 'group_id', 'partner_id', 'company_id', 'scheduled_date'], limit=5)
        if not pks:
            # fallback: pela sequencia final
            seq = ref.split('/')[-1]
            pks = rr('stock.picking', [('name', 'like', f'%RETIND/{seq}')],
                     ['id', 'name', 'state', 'picking_type_id', 'location_id', 'location_dest_id',
                      'origin', 'group_id', 'partner_id', 'company_id', 'scheduled_date'], limit=5)
        if not pks:
            print(f"  (nenhum picking name={ref!r} nem %RETIND/{ref.split('/')[-1]})")
            continue
        for pk in pks:
            print(f"  picking {pk['id']} {pk['name']} state={pk.get('state')} "
                  f"company={m2o(pk.get('company_id'))} partner={m2o(pk.get('partner_id'))}")
            print(f"     {m2o(pk.get('location_id'))} -> {m2o(pk.get('location_dest_id'))}  "
                  f"origin={pk.get('origin')} group={m2o(pk.get('group_id'))}")
            if isinstance(pk.get('picking_type_id'), list):
                dump_pt(pk['picking_type_id'][0])
            sm = rr('stock.move', [('picking_id', '=', pk['id'])],
                    ['id', 'product_id', 'quantity', 'product_uom_qty', 'location_id',
                     'location_dest_id', 'state'], limit=80)
            print(f"     stock.moves: {len(sm)}")
            for s in sm[:12]:
                print(f"        move {s['id']} {m2o(s.get('product_id'))[:26]:26} qty={s.get('quantity')} "
                      f"{m2o(s.get('location_id'))[:16]:16}->{m2o(s.get('location_dest_id'))[:16]:16} {s.get('state')}")
            mids = [s['id'] for s in sm]
            if mids:
                svl = rr('stock.valuation.layer', [('stock_move_id', 'in', mids)],
                         ['id', 'value', 'quantity'], limit=120)
                tot = round(sum(s.get('value') or 0 for s in svl), 2)
                print(f"     SVL: {len(svl)} layers, valor total = {tot}  "
                      f"({'SIMBOLICA (0 valoracao)' if abs(tot) < 0.01 else 'TEM valoracao fisica'})")
            # move.lines com lote
            mls = rr('stock.move.line', [('picking_id', '=', pk['id'])],
                     ['id', 'product_id', 'lot_id', 'quantity'], limit=20)
            lotes = {m2o(x.get('lot_id')) for x in mls if x.get('lot_id')}
            print(f"     move.lines: {len(mls)}; lotes: {sorted(lotes)[:6]}")

    # ------------------------------------------------------------------
    # 2) picking_types do RETORNO na LF + suas rotas p/ journal
    # ------------------------------------------------------------------
    print("\n" + "=" * 92)
    print("PICKING_TYPES candidatos do retorno (LF=5) + tipo_pedido -> journal")
    print("=" * 92)
    # pt98 (citado) + todos os outgoing da LF com tipo_pedido relevante
    pts = rr('stock.picking.type', [('company_id', '=', 5), ('code', '=', 'outgoing')], PT_FLD, limit=60)
    print(f"  {len(pts)} picking_types outgoing na LF:")
    for t in pts:
        tp = t.get('l10n_br_tipo_pedido')
        flag = ''
        if tp in ('dev-industrializacao', 'venda-industrializacao', 'perda', 'retorno'):
            flag = '  <<< relevante p/ retorno'
        print(f"   pt{t['id']:<5} {t['name'][:36]:36} tipo_pedido={str(tp):24} "
              f"src={m2o(t.get('default_location_src_id'))[:18]:18} dst={m2o(t.get('default_location_dest_id'))[:18]:18}{flag}")

    # journals sale LF por tipo_pedido (a regra do robo)
    print("\n  --- journals sale LF e seu l10n_br_tipo_pedido + no_payment (regra do robo R2c) ---")
    js = rr('account.journal', [('company_id', '=', 5), ('type', '=', 'sale')],
            ['id', 'name', 'code', 'l10n_br_tipo_pedido', 'account_no_payment_id'], limit=40)
    for j in js:
        print(f"   j{j['id']:<5} {j['name'][:34]:34} code={str(j.get('code')):8} "
              f"tipo_pedido={str(j.get('l10n_br_tipo_pedido')):24} no_payment={m2o(j.get('account_no_payment_id'))}")

    print("\n[FIM s7_saret_fisico — READ-only, nada escrito]")


if __name__ == '__main__':
    main()
