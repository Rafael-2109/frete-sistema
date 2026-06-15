#!/usr/bin/env python3
"""G9 CONCILIA extrato LF 2026 — ROBUSTO (re-le NFs frescas por entrada, padrao g9_15).

Conclui as entradas FB ainda nao-conciliadas. Para CADA entrada: re-le os debitos VND
com residual fresco e reconcilia FIFO. Imune a divergencia de casamento do Odoo.
DRY-RUN default. --confirmar efetiva. Idempotente (so toca o que esta aberto).
"""
import sys
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5]}
ACC_LF, P_FB = 26085, 1
CONFIRMAR = '--confirmar' in sys.argv


def main():
    o = get_odoo_connection()
    assert o.authenticate(), "FALHA AUTH"
    print(f"UID {o._uid} | {'CONFIRMAR' if CONFIRMAR else 'DRY-RUN'}\n")

    def sr(m, d, f, **k):
        kw = {'fields': f, 'context': CTX}; kw.update(k)
        return o.execute_kw(m, 'search_read', [d], kw)

    jb = [j['id'] for j in sr('account.journal', [('type', '=', 'bank'), ('company_id', '=', 5)], ['id'])]
    ent = sr('account.bank.statement.line',
             [('journal_id', 'in', jb), ('company_id', '=', 5), ('date', '>=', '2026-01-01'),
              ('amount', '>', 0), ('payment_ref', 'ilike', 'NACOM'), ('is_reconciled', '=', False)],
             ['date', 'amount', 'move_id'], order='date, id')
    print(f"entradas FB ainda nao-conciliadas: {len(ent)} = R$ {sum(e['amount'] for e in ent):,.2f}")
    if not CONFIRMAR:
        print("\n[DRY-RUN] --confirmar efetiva.")
        return

    def vnd_frescas(limit=300):
        fat = sr('account.move.line', [('account_id', '=', ACC_LF), ('partner_id', '=', P_FB),
                 ('parent_state', '=', 'posted'), ('debit', '>', 0), ('amount_residual', '>', 0)],
                 ['move_id', 'amount_residual'], order='date, id', limit=limit)
        mids = list({f['move_id'][0] for f in fat})
        nm = {}
        for i in range(0, len(mids), 300):
            for m in o.execute_kw('account.move', 'read', [mids[i:i + 300]], {'fields': ['name'], 'context': CTX}):
                nm[m['id']] = m['name']
        return [(f['id'], f['amount_residual']) for f in fat if nm.get(f['move_id'][0], '').startswith('VND')]

    ok = fail = 0
    for e in ent:
        mls = sr('account.move.line', [('move_id', '=', e['move_id'][0]), ('credit', '>', 0)], ['reconciled'])
        if len(mls) != 1 or mls[0]['reconciled']:
            continue
        trans_id = mls[0]['id']; amt = e['amount']
        fat = vnd_frescas()
        alvo = []; falta = amt
        for fid, fr in fat:
            u = min(falta, fr); falta -= u; alvo.append(fid)
            if falta <= 0.005:
                break
        try:
            o.execute_kw('account.move.line', 'write', [[trans_id], {'account_id': ACC_LF, 'partner_id': P_FB}], {'context': CTX})
            o.execute_kw('account.move.line', 'reconcile', [[trans_id] + alvo], {'context': CTX})
            ok += 1
            print(f"  OK {e['date']} R$ {amt:,.2f} -> {len(alvo)} NF(s)")
        except Exception as ex:
            fail += 1
            print(f"  FALHA {e['date']} R$ {amt:,.2f}: {str(ex)[:110]}")
    print(f"\n[FIM] ok={ok} fail={fail}")


if __name__ == '__main__':
    main()
