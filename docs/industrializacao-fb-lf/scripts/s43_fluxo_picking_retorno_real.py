#!/usr/bin/env python3
"""S43 — READ-only: COMO o picking de retorno de industrializacao e' criado HOJE (manual
pelo operador vs automatico pela MO de subcontratacao)? Responde a pergunta do Rafael:
"o operador precisa criar o picking do retorno / faturar, ou e' automatico?"

Investiga NFs REAIS de retorno (mistas 5124+5902): 709632, 708286, 574827.
  - acha o picking de origem (via stock.move da linha do PA / invoice_id reverso)
  - picking: create_uid (HUMANO=operador vs OdooBot/robo), origin, picking_type, group_id
  - ha MO de subcontratacao vinculada? o picking de retorno saiu da MO (automatico) ou foi
    criado a mao? (origin aponta p/ MO/SO? procurement group?)

READ-ONLY.
"""
import sys
from collections import Counter
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5], 'company_id': 5, 'lang': 'pt_BR'}
NFS = [709632, 708286, 574827]


def m2o(v):
    return f"{v[0]}|{str(v[1])[:34]}" if isinstance(v, list) and v else ('-' if not v else str(v))


def main():
    o = get_odoo_connection(); assert o.authenticate(), "FALHA AUTH"

    def rr(model, dom, fields, **kw):
        kw2 = {'fields': fields, 'context': CTX}; kw2.update(kw)
        return o.execute_kw(model, 'search_read', [dom], kw2)
    def rd(model, ids, fields):
        return o.execute_kw(model, 'read', [list(ids)], {'fields': fields, 'context': CTX})

    for nf in NFS:
        print("=" * 94)
        h = rd('account.move', [nf], ['name', 'invoice_origin', 'create_uid', 'create_date',
                                      'invoice_user_id', 'l10n_br_tipo_pedido'])
        if not h:
            print(f"NF {nf}: inexistente"); continue
        h = h[0]
        print(f"### NF {nf} {h['name']} | origin={h.get('invoice_origin')!r} | "
              f"create_uid={m2o(h.get('create_uid'))} create_date={h.get('create_date')}")
        # achar o picking: via stock.picking que aponta invoice_id/invoice_ids == nf (vinculo CIEL IT)
        pick_ids = set()
        for p in rr('stock.picking', ['|', ('invoice_id', '=', nf), ('invoice_ids', 'in', [nf])],
                    ['id'], limit=5):
            pick_ids.add(p['id'])
        # fallback: pickings cujo origin == invoice_origin da NF
        if not pick_ids and h.get('invoice_origin'):
            for p in rr('stock.picking', [('origin', '=', h.get('invoice_origin'))], ['id'], limit=5):
                pick_ids.add(p['id'])
        print(f"   pickings vinculados: {pick_ids or 'NAO ACHADO por invoice_id/origin'}")
        for pid in pick_ids:
            p = rd('stock.picking', [pid], ['name', 'origin', 'create_uid', 'create_date',
                                            'picking_type_id', 'group_id', 'location_id', 'location_dest_id'])[0]
            print(f"   PICKING {pid} {p['name']}: pt={m2o(p.get('picking_type_id'))}")
            print(f"      create_uid={m2o(p.get('create_uid'))} create_date={p.get('create_date')}")
            print(f"      origin={p.get('origin')!r} group={m2o(p.get('group_id'))} "
                  f"src={m2o(p.get('location_id'))} dst={m2o(p.get('location_dest_id'))}")
            # MO de subcontratacao vinculada? procurar mrp.production com esse group/origin
            if p.get('group_id'):
                mos = rr('mrp.production', [('procurement_group_id', '=', p['group_id'][0])],
                         ['name', 'state', 'create_uid'], limit=3)
                print(f"      MO via group: {[(m['name'], m['state']) for m in mos] or 'nenhuma'}")

    # quem cria pickings pt66 em geral (amostra) — robo vs humano
    print("\n" + "=" * 94)
    print("### Quem cria os pickings pt66 (Exp.Industrializacao) — amostra recente (robo vs humano)")
    sample = rr('stock.picking', [('picking_type_id', '=', 66)], ['create_uid', 'origin'],
                limit=40, order='id desc')
    by_uid = Counter(m2o(p.get('create_uid')) for p in sample)
    print(f"   create_uid (top): {dict(by_uid.most_common(6))}")
    origins = Counter((p.get('origin') or '')[:14] for p in sample)
    print(f"   origins (top): {dict(origins.most_common(8))}")


if __name__ == '__main__':
    main()
