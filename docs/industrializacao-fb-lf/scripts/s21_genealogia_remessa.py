#!/usr/bin/env python3
"""S21 — A explosao da BoM e' AUTOMATICA na REMESSA (FB->LF)? READ-ONLY.
Reconciliacao: o retorno (5902) NAO tem server action; a operadora replica. A
explosao automatica da lista de materiais acontece na REMESSA — esta e' a etapa
"o sistema abre os componentes". Prova: em remessas REAIS de industrializacao,
quem criou as linhas (robo/picking que explode a BoM) e de qual picking nasceram.

Pega N remessas reais (journal 17 REMESSA P/ INDUSTRIALIZACAO, op 80) e mostra:
  - header: create_uid, invoice_origin
  - linhas: create_uid (robo? humano?) + create_date (1 transacao?)
  - o stock.picking de origem (pt que explode a BoM no envio)
"""
import sys
from collections import Counter
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5], 'company_id': 5, 'lang': 'pt_BR'}
J_REMESSA = 17


def m2o(v):
    return f"{v[0]}|{v[1]}" if isinstance(v, list) and v else ('-' if not v else str(v))


def main():
    o = get_odoo_connection(); assert o.authenticate(), "FALHA AUTH"

    def rr(model, dom, fields, **kw):
        kw2 = {'fields': fields, 'context': CTX}; kw2.update(kw)
        return o.execute_kw(model, 'search_read', [dom], kw2)

    rems = rr('account.move', [('journal_id', '=', J_REMESSA), ('state', '=', 'posted'),
                               ('move_type', '=', 'out_invoice')],
              ['id', 'name', 'create_uid', 'invoice_origin', 'ref', 'partner_id', 'amount_total'],
              order='id desc', limit=4)
    print("=" * 88)
    print("=== Remessas REAIS de industrializacao (journal 17) — genealogia das linhas ===")
    for r in rems:
        print(f"\n### {r['name']} (move {r['id']}) header by={m2o(r['create_uid'])} "
              f"origin={r.get('invoice_origin')} ref={r.get('ref')} partner={m2o(r.get('partner_id'))[:20]}")
        lines = rr('account.move.line', [('move_id', '=', r['id']), ('display_type', '=', 'product')],
                   ['l10n_br_cfop_codigo', 'create_uid', 'create_date'], order='id')
        cu = Counter(m2o(l.get('create_uid')) for l in lines)
        cd = Counter(str(l.get('create_date')) for l in lines)
        cf = Counter(str(l.get('l10n_br_cfop_codigo')) for l in lines)
        print(f"    {len(lines)} linhas | CFOPs={dict(cf)} | by={dict(cu)} | create_dates_distintos={len(cd)}")
        # picking de origem (que explode a BoM no envio)
        org = r.get('invoice_origin') or r.get('ref')
        if org:
            for tok in str(org).replace(',', ' ').split():
                pk = rr('stock.picking', [('name', '=', tok)],
                        ['id', 'picking_type_id', 'origin', 'create_uid'], limit=2)
                for p in pk:
                    print(f"    origem picking {p['id']} {tok} type={m2o(p.get('picking_type_id'))[:30]} "
                          f"by={m2o(p.get('create_uid'))[:18]}")


if __name__ == '__main__':
    main()
