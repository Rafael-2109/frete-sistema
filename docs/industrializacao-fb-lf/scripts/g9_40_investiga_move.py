#!/usr/bin/env python3
"""G9 INVESTIGA (READ-ONLY) a natureza real de moves de pagamento FB->LF.

Recebe nomes de account.move (argv) e detalha: company, journal, tipo, estado,
partner, ref, payment_state + TODAS as linhas contabeis (conta code/nome, D/C,
company da linha, reconciliada). Tambem cruza com account.bank.statement.line (extrato)
e account.payment. Serve p/ checar qualquer um dos 26 faltantes. NAO escreve nada.

Uso: python g9_40_investiga_move.py "BRAD/2026/00802" "BRAD/2026/00803"
     (sem args = os 2 BRAD do gap 18/03)
"""
import sys
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5]}
NOMES = [a for a in sys.argv[1:] if not a.startswith('-')] or ['BRAD/2026/00802', 'BRAD/2026/00803']


def main():
    o = get_odoo_connection()
    assert o.authenticate(), "FALHA AUTH"
    print(f"UID {o._uid}\n")

    def sr(m, d, f, **k):
        kw = {'fields': f, 'context': CTX}; kw.update(k)
        return o.execute_kw(m, 'search_read', [d], kw)

    comp = {c['id']: c['name'] for c in sr('res.company', [], ['name'])}

    for nome in NOMES:
        mv = sr('account.move', [('name', '=', nome)],
                ['name', 'date', 'journal_id', 'company_id', 'state', 'move_type',
                 'ref', 'payment_reference', 'amount_total', 'payment_state',
                 'statement_line_id', 'partner_id', 'invoice_origin'])
        if not mv:
            print(f"=== {nome}: NAO ENCONTRADO no account.move ===\n")
            continue
        for m in mv:
            print(f"=== {nome} (move id {m['id']}) ===")
            print(f"  company     : {m['company_id'][1] if m['company_id'] else '-'}")
            print(f"  journal     : {m['journal_id'][1] if m['journal_id'] else '-'}")
            print(f"  date        : {m['date']}   state: {m['state']}   move_type: {m['move_type']}")
            print(f"  partner     : {m['partner_id'][1] if m['partner_id'] else '-'}")
            print(f"  ref         : {m.get('ref')}   payment_reference: {m.get('payment_reference')}")
            print(f"  amount_total: {m['amount_total']:,.2f}   payment_state: {m.get('payment_state')}")
            print(f"  invoice_orig: {m.get('invoice_origin')}")
            print(f"  statement_line_id (extrato): {m.get('statement_line_id')}")
            lines = sr('account.move.line', [('move_id', '=', m['id'])],
                       ['account_id', 'partner_id', 'debit', 'credit', 'reconciled', 'company_id', 'name'])
            print(f"  --- {len(lines)} linha(s) contabil(eis) ---")
            for ln in lines:
                acc = ln['account_id'][1] if ln['account_id'] else '-'
                par = ln['partner_id'][1] if ln['partner_id'] else '-'
                cmp = comp.get(ln['company_id'][0], '?') if ln['company_id'] else '?'
                print(f"    [{cmp[:10]:<10}] {acc[:45]:<45} | D {ln['debit']:>11,.2f} | C {ln['credit']:>11,.2f} "
                      f"| recon={str(ln['reconciled'])[:1]} | partner={par[:18]}")
            # statement line do extrato com o mesmo valor/ref?
            if m.get('statement_line_id'):
                sl = sr('account.bank.statement.line', [('id', '=', m['statement_line_id'][0])],
                        ['date', 'amount', 'payment_ref', 'journal_id', 'company_id', 'is_reconciled'])
                for s in sl:
                    print(f"  >> EXTRATO statement.line {s['id']}: {s['date']} R$ {s['amount']:,.2f} "
                          f"| {s['journal_id'][1] if s['journal_id'] else '-'} | comp={comp.get(s['company_id'][0],'?') if s['company_id'] else '?'} "
                          f"| ref={s['payment_ref']} | is_reconciled={s['is_reconciled']}")
            print()


if __name__ == '__main__':
    main()
