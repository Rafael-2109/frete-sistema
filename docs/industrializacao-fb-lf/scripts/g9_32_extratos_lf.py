#!/usr/bin/env python3
"""G9 EXTRATOS LF (READ-ONLY) — os recebimentos da FB estao importados/conciliados na LF?

Mede statement lines (extrato) da LF (company 5) por ano nos journals de banco, e quanto
esta conciliado. Confirma se os R$ ~11,45M de 2026 (pgto FB) tem extrato. NAO escreve nada.
"""
import sys
from collections import defaultdict
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5]}


def main():
    o = get_odoo_connection()
    assert o.authenticate(), "FALHA AUTH"
    print(f"UID {o._uid}\n")

    # journals de banco da LF
    jb = o.execute_kw('account.journal', 'search_read', [[('type', '=', 'bank'), ('company_id', '=', 5)]],
                      {'fields': ['name', 'code'], 'context': CTX})
    jids = [j['id'] for j in jb]
    print("Journals de banco LF:", [f"{j['code']}" for j in jb])

    P = lambda x: f"{x:>14,.2f}"
    print("\n" + "=" * 72)
    print("1) EXTRATO (account.bank.statement.line) da LF por ano")
    sl = o.execute_kw('account.bank.statement.line', 'search_read',
                      [[('journal_id', 'in', jids), ('company_id', '=', 5)]],
                      {'fields': ['date', 'amount', 'is_reconciled'], 'context': CTX})
    by = defaultdict(lambda: {'n': 0, 'v': 0.0, 'nc': 0, 'vc': 0.0})
    for l in sl:
        y = (l['date'] or '----')[:4]
        b = by[y]; b['n'] += 1; b['v'] += l['amount'] or 0
        if not l['is_reconciled']:
            b['nc'] += 1; b['vc'] += l['amount'] or 0
    print(f"   {'Ano':6s} {'linhas':>8s} {'valor':>16s} {'nao-concil':>10s} {'valor nao-conc':>16s}")
    for y in sorted(by):
        b = by[y]
        print(f"   {y:6s} {b['n']:>8d} {P(b['v'])} {b['nc']:>10d} {P(b['vc'])}")

    print("\n" + "=" * 72)
    print("2) RECEBIMENTOS da FB na conta CLIENTES (26085) da LF por ano (credito, exceto G9)")
    g = o.execute_kw('account.move.line', 'read_group',
                     [[('account_id', '=', 26085), ('partner_id', '=', 1), ('parent_state', '=', 'posted'),
                       ('credit', '>', 0), ('journal_id', '!=', 894)], ['credit:sum'], ['date:year']],
                     {'context': CTX, 'lazy': False})
    for r in g:
        print(f"   {str(r.get('date:year')):6s} R$ {r.get('credit', 0) or 0:,.2f} ({r['__count']})")

    print("\n" + "=" * 72)
    print("3) PAGAMENTOS da FB -> LF por ano (debito FORNECEDORES FB) — o que DEVERIA ter extrato na LF")
    g2 = o.execute_kw('account.move.line', 'read_group',
                      [[('account_id', '=', 11038), ('partner_id', '=', 35), ('parent_state', '=', 'posted'), ('debit', '>', 0)],
                       ['debit:sum'], ['date:year']], {'context': CTX, 'lazy': False})
    for r in g2:
        print(f"   {str(r.get('date:year')):6s} R$ {r.get('debit', 0) or 0:,.2f} ({r['__count']})")


if __name__ == '__main__':
    main()
