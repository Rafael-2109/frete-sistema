#!/usr/bin/env python3
"""G9 CONTRAPARTIDA (READ-ONLY) — saldos das transitorias + composicao da ATIVA + double-count fisico.

Para desenhar a contrapartida da baixa de regularizacao. Mede:
  1) saldo das transitorias 1150100012 (LF acc 26855) e 1150100011 (FB acc 26842) por empresa;
  2) composicao da ATIVA 5101010001 FB (acc 22800): debitos/creditos por OPERACAO (o que infla);
  3) double-count fisico do caso 564486 (ENTSI/2026/04/0025): stock.move + SVL gerados.
NAO escreve nada.
"""
import sys
from collections import defaultdict
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5]}


def m2o(v):
    if isinstance(v, list) and v:
        return f"{v[0]}|{v[1]}"
    return '-' if v in (False, None) else str(v)


def main():
    o = get_odoo_connection()
    assert o.authenticate(), "FALHA AUTH"
    print(f"UID {o._uid}\n")

    def rr(model, domain, fields, **kw):
        kwargs = {'fields': fields, 'context': CTX}
        kwargs.update(kw)
        return o.execute_kw(model, 'search_read', [domain], kwargs)

    def rg(model, domain, fields, groupby, **kw):
        kwargs = {'context': CTX}
        kwargs.update(kw)
        return o.execute_kw(model, 'read_group', [domain, fields, groupby], kwargs)

    # ===== 1) transitorias =====
    for label, acc in [("1150100012 FATUR.FISICO (LF, acc 26855)", 26855),
                       ("1150100011 RECEB.FISICO (FB, acc 26842)", 26842)]:
        print("=" * 70)
        print(f"TRANSITORIA — {label}")
        print("=" * 70)
        g = rg('account.move.line', [('account_id', '=', acc), ('parent_state', '=', 'posted')],
               ['debit:sum', 'credit:sum'], ['company_id'], lazy=False)
        for row in g:
            d = row.get('debit', 0) or 0
            c = row.get('credit', 0) or 0
            print(f"    company={m2o(row.get('company_id'))[:30]:30} D R$ {d:>16,.2f}  C R$ {c:>16,.2f}  saldo R$ {d-c:>16,.2f}  ({row.get('__count')} ln)")

    # ===== 2) composicao da ATIVA FB 22800 por operacao =====
    print("\n" + "=" * 70)
    print("COMPOSICAO ATIVA 5101010001 FB (acc 22800) por OPERACAO")
    print("=" * 70)
    lines = rr('account.move.line', [('account_id', '=', 22800), ('parent_state', '=', 'posted')],
               ['l10n_br_operacao_id', 'l10n_br_cfop_id', 'debit', 'credit', 'journal_id'], limit=5000)
    by_op = defaultdict(lambda: [0.0, 0.0, 0])
    for ln in lines:
        key = (m2o(ln.get('l10n_br_operacao_id')), m2o(ln.get('l10n_br_cfop_id')), m2o(ln.get('journal_id'))[:18])
        by_op[key][0] += ln.get('debit') or 0
        by_op[key][1] += ln.get('credit') or 0
        by_op[key][2] += 1
    for key, (d, c, n) in sorted(by_op.items(), key=lambda kv: -(kv[1][0] + kv[1][1])):
        op, cfop, jr = key
        print(f"    op={op[:14]:14} cfop={cfop[:9]:9} j={jr:18} D {d:>14,.2f} C {c:>14,.2f} ({n})")

    # ===== 3) double-count fisico do caso 564486 =====
    print("\n" + "=" * 70)
    print("DOUBLE-COUNT FISICO — entrada FB ENTSI/2026/04/0025 (move 564486)")
    print("=" * 70)
    # tentar achar picking e stock.move
    for dom_label, dom in [
        ("stock.picking origin~VND/2026/00234", [('company_id', '=', 1), ('origin', 'ilike', 'VND/2026/00234')]),
        ("stock.picking origin~ENTSI/2026/04/0025", [('company_id', '=', 1), ('origin', 'ilike', 'ENTSI/2026/04/0025')]),
    ]:
        pks = rr('stock.picking', dom, ['id', 'name', 'origin', 'state', 'picking_type_id'], limit=10)
        print(f"  [{dom_label}] -> {len(pks)} pickings")
        for p in pks:
            print(f"     pick {p['id']} {p['name']} origin={p.get('origin')} {p['state']} pt={m2o(p.get('picking_type_id'))[:30]}")
            mvs = rr('stock.move', [('picking_id', '=', p['id'])],
                     ['product_id', 'product_uom_qty', 'location_id', 'location_dest_id', 'state'], limit=50)
            for s in mvs[:6]:
                print(f"        mv {m2o(s['product_id'])[:28]:28} qty={s['product_uom_qty']:>7} {m2o(s['location_id'])[:14]}->{m2o(s['location_dest_id'])[:14]} {s['state']}")

    # SVL: valuation layers da company 1 que entraram via essa NF
    svls = rr('stock.valuation.layer',
              [('company_id', '=', 1), ('description', 'ilike', 'VND/2026/00234')],
              ['product_id', 'quantity', 'value', 'description'], limit=30)
    print(f"\n  SVL (stock.valuation.layer) description~VND/2026/00234 -> {len(svls)}")
    tot_svl = 0.0
    for s in svls[:20]:
        tot_svl += s.get('value') or 0
        print(f"     {m2o(s['product_id'])[:30]:30} qty={s['quantity']:>7} value R$ {s.get('value'):>10,.2f}")
    if svls:
        print(f"     => SVL total (entrada estoque FB pelo retorno): R$ {tot_svl:,.2f}  [=double-count se >0]")

    print("\n[FIM G9 CONTRAPARTIDA — nada foi escrito]")


if __name__ == '__main__':
    main()
