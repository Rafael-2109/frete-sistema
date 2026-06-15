#!/usr/bin/env python3
"""G9 CASA creditos abertos CLIENTES (partner FB) contra NFs VND — FIFO robusto.

As 13 entradas auto-conciliadas pelo Odoo reduziram o a-receber mas ficaram como CREDITO
em aberto (recon=False) na conta CLIENTES. Aqui casa cada credito com debitos VND frescos.
Idempotente. DRY-RUN default. --confirmar efetiva.
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

    cred = sr('account.move.line', [('account_id', '=', ACC_LF), ('partner_id', '=', P_FB),
              ('parent_state', '=', 'posted'), ('reconciled', '=', False), ('amount_residual', '<', 0)],
              ['amount_residual', 'date'], order='date, id')
    print(f"creditos abertos a casar: {len(cred)} = R$ {-sum(c['amount_residual'] for c in cred):,.2f}")
    if not CONFIRMAR:
        print("\n[DRY-RUN] --confirmar efetiva.")
        return

    def vnd_frescas():
        fat = sr('account.move.line', [('account_id', '=', ACC_LF), ('partner_id', '=', P_FB),
                 ('parent_state', '=', 'posted'), ('debit', '>', 0), ('amount_residual', '>', 0)],
                 ['move_id', 'amount_residual'], order='date, id', limit=300)
        mids = list({f['move_id'][0] for f in fat})
        nm = {}
        for i in range(0, len(mids), 300):
            for m in o.execute_kw('account.move', 'read', [mids[i:i + 300]], {'fields': ['name'], 'context': CTX}):
                nm[m['id']] = m['name']
        return [(f['id'], f['amount_residual']) for f in fat if nm.get(f['move_id'][0], '').startswith('VND')]

    ok = fail = 0
    for c in cred:
        cf = o.execute_kw('account.move.line', 'read', [[c['id']], ['amount_residual', 'reconciled']], {'context': CTX})
        if not cf or cf[0]['reconciled'] or abs(cf[0]['amount_residual']) < 0.005:
            continue
        falta = -cf[0]['amount_residual']
        alvo = []
        for fid, fr in vnd_frescas():
            u = min(falta, fr); falta -= u; alvo.append(fid)
            if falta <= 0.005:
                break
        try:
            o.execute_kw('account.move.line', 'reconcile', [[c['id']] + alvo], {'context': CTX})
            ok += 1
            print(f"  OK {c['date']} R$ {-c['amount_residual']:,.2f} -> {len(alvo)} NF(s)")
        except Exception as ex:
            fail += 1
            print(f"  FALHA {c['date']}: {str(ex)[:110]}")
    print(f"\n[FIM] ok={ok} fail={fail}")


if __name__ == '__main__':
    main()
