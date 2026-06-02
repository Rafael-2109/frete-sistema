#!/usr/bin/env python3
"""S7 CICLO DE SUBCONTRATACAO (READ-only) — a subcontratacao nativa do Odoo esta ATIVA e
gera as NFs fiscais (5901/5902/5124)? (decide Forma 1 nativa x Forma 2 pipeline)

Verifica:
  1. UNIVERSO: quantas BoM subcontract; quantas POs serv-industrializacao (FB).
  2. USO do resupply: pickings pt75 'Reposicao para subcontratacao' (done, recentes) — existe fluxo?
  3. USO de MO subcontract: mrp.production com BoM subcontract (recentes).
  4. RASTREIO de 1 ciclo: pega o caso mais recente e segue PO -> resupply -> MO -> recebimento -> NFs.
     -> que NFs (CFOP/journal) o CIEL IT emite em cada etapa? sao automaticas?

NAO escreve nada.
"""
import sys
from collections import Counter
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5]}


def m2o(v):
    return f"{v[0]}|{v[1]}" if isinstance(v, list) and v else ('-' if not v else str(v))


def main():
    o = get_odoo_connection()
    assert o.authenticate(), "FALHA AUTH"
    print(f"UID {o._uid}")

    def rr(model, domain, fields, **kw):
        return o.execute_kw(model, 'search_read', [domain], {'fields': fields, 'context': CTX, **kw})

    def cnt(model, domain):
        return o.execute_kw(model, 'search_count', [domain], {'context': CTX})

    # ----------------------------------------------------------------
    print("\n" + "=" * 88)
    print("1) UNIVERSO")
    print("=" * 88)
    n_bom_sub = cnt('mrp.bom', [('type', '=', 'subcontract')])
    n_bom_tot = cnt('mrp.bom', [])
    print(f"  BoM subcontract: {n_bom_sub} de {n_bom_tot} total")
    # subcontratantes distintos
    bsub = rr('mrp.bom', [('type', '=', 'subcontract')], ['id', 'subcontractor_ids', 'product_tmpl_id'], limit=2000)
    subs = Counter()
    for b in bsub:
        for s in (b.get('subcontractor_ids') or []):
            subs[s] += 1
    print(f"  subcontratantes (partner_id: nº de BoMs): {dict(subs.most_common(8))}")
    n_po_si = cnt('purchase.order', [('l10n_br_tipo_pedido', '=', 'serv-industrializacao')])
    print(f"  POs l10n_br_tipo_pedido=serv-industrializacao: {n_po_si}")

    # ----------------------------------------------------------------
    print("\n" + "=" * 88)
    print("2) USO do RESUPPLY (pt75 'Reposicao para subcontratacao')")
    print("=" * 88)
    for pt in (75, 74, 80, 95):
        tot = cnt('stock.picking', [('picking_type_id', '=', pt)])
        done = cnt('stock.picking', [('picking_type_id', '=', pt), ('state', '=', 'done')])
        recent = rr('stock.picking', [('picking_type_id', '=', pt)],
                    ['id', 'name', 'state', 'date_done', 'scheduled_date'], limit=3, order='id desc')
        amostra = '; '.join(f"{p['name']}({p.get('state')},{p.get('date_done') or p.get('scheduled_date')})" for p in recent)
        print(f"  pt{pt}: total={tot} done={done} | ultimos: {amostra}")

    # ----------------------------------------------------------------
    print("\n" + "=" * 88)
    print("3) USO de MO SUBCONTRACT (mrp.production com BoM subcontract)")
    print("=" * 88)
    try:
        n_mo_sub = cnt('mrp.production', [('bom_id.type', '=', 'subcontract')])
        mos = rr('mrp.production', [('bom_id.type', '=', 'subcontract')],
                 ['id', 'name', 'state', 'date_start', 'product_id', 'company_id', 'picking_ids'],
                 limit=5, order='id desc')
        print(f"  MOs subcontract: {n_mo_sub}")
        for mo in mos:
            print(f"   MO {mo['id']} {mo['name']} state={mo.get('state')} prod={m2o(mo.get('product_id'))[:26]} "
                  f"company={m2o(mo.get('company_id'))} date={mo.get('date_start')}")
    except Exception as e:
        print(f"  (erro bom_id.type: {e})")
        mos = []

    # ----------------------------------------------------------------
    print("\n" + "=" * 88)
    print("4) RASTREIO de 1 ciclo recente (resupply pt75 done -> origem -> NFs)")
    print("=" * 88)
    rec = rr('stock.picking', [('picking_type_id', '=', 75), ('state', '=', 'done')],
             ['id', 'name', 'origin', 'group_id', 'date_done', 'location_id', 'location_dest_id'],
             limit=3, order='id desc')
    if not rec:
        print("  >>> pt75 NAO tem picking done -> resupply nativo NAO esta em uso operacional.")
    for pk in rec:
        print(f"\n  RESUPPLY {pk['id']} {pk['name']} {m2o(pk.get('location_id'))}->{m2o(pk.get('location_dest_id'))} "
              f"origin={pk.get('origin')} group={m2o(pk.get('group_id'))} date={pk.get('date_done')}")
        # NF gerada por esse resupply? (account.move com invoice_origin/ref = picking)
        for campo in ('invoice_origin', 'ref'):
            mvs = rr('account.move', [(campo, '=', pk['name'])], ['id', 'name', 'journal_id', 'move_type'], limit=4)
            for mv in mvs:
                print(f"     NF [{campo}={pk['name']}]: {mv['name']} j={m2o(mv.get('journal_id'))} type={mv.get('move_type')}")

    # tambem: a PO serv-industrializacao mais recente -> rastreio PO->pickings->NFs
    print("\n  --- PO serv-industrializacao mais recente (entrada FB) ---")
    po = rr('purchase.order', [('l10n_br_tipo_pedido', '=', 'serv-industrializacao')],
            ['id', 'name', 'partner_id', 'origin', 'state', 'picking_ids', 'invoice_ids', 'date_order'],
            limit=2, order='id desc')
    for p in po:
        print(f"  PO {p['id']} {p['name']} partner={m2o(p.get('partner_id'))} origin={p.get('origin')} "
              f"pickings={p.get('picking_ids')} invoices={p.get('invoice_ids')} date={p.get('date_order')}")

    print("\n[FIM s7_ciclo_subcontratacao — READ-only]")


if __name__ == '__main__':
    main()
