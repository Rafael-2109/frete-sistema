#!/usr/bin/env python3
"""G9 DESCONCILIA (WRITE) as statement lines SABESP/agua reconciliadas por engano c/ partner LF.

Alvo default: statement.line 42285 (BRAD/2026/00802) e 42286 (BRAD/2026/00803) — pagamento de
CONTA DE AGUA SABESP reconciliado contra FORNECEDORES/LF e usado p/ baixar a fatura de
industrializacao ENTSI/2025/05/0047. Desconciliar reabre R$ 327,92 nessa fatura (correto) e
devolve as statement lines ao suspense p/ reclassificacao posterior como despesa de agua.

Usa account.bank.statement.line.button_undo_reconciliation (cirurgico: nao toca os outros
pagamentos da mesma fatura). DRY-RUN default. --confirmar efetiva. Idempotente.
"""
import sys
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5]}
SL_IDS = [int(a) for a in sys.argv[1:] if a.isdigit()] or [42285, 42286]
CONFIRMAR = '--confirmar' in sys.argv


def main():
    o = get_odoo_connection()
    assert o.authenticate(), "FALHA AUTH"
    print(f"UID {o._uid} | {'CONFIRMAR' if CONFIRMAR else 'DRY-RUN'} | alvo statement.lines {SL_IDS}\n")

    def sr(m, d, f, **k):
        kw = {'fields': f, 'context': CTX}; kw.update(k)
        return o.execute_kw(m, 'search_read', [d], kw)

    # faturas impactadas (p/ medir residual antes/depois)
    inv_ids = set()
    alvo = []
    for slid in SL_IDS:
        sl = sr('account.bank.statement.line', [('id', '=', slid)],
                ['payment_ref', 'amount', 'date', 'is_reconciled', 'move_id'])
        if not sl:
            print(f"  SKIP {slid}: nao encontrado"); continue
        sl = sl[0]
        if not sl['is_reconciled']:
            print(f"  SKIP {slid}: ja NAO reconciliada (idempotente)"); continue
        # achar fatura(s) casada(s) via partials da linha FORNECEDORES do move
        forn = sr('account.move.line', [('move_id', '=', sl['move_id'][0]), ('account_id', '=', 11038)],
                  ['matched_credit_ids', 'matched_debit_ids'])
        for fl in forn:
            pids = (fl.get('matched_credit_ids') or []) + (fl.get('matched_debit_ids') or [])
            if pids:
                for p in o.execute_kw('account.partial.reconcile', 'read', [pids],
                                      {'fields': ['debit_move_id', 'credit_move_id'], 'context': CTX}):
                    for side in ('debit_move_id', 'credit_move_id'):
                        if p[side] and p[side][0]:
                            ll = sr('account.move.line', [('id', '=', p[side][0])], ['move_id', 'account_id'])
                            if ll and ll[0]['account_id'][0] == 11038 and ll[0]['move_id'][0] != sl['move_id'][0]:
                                inv_ids.add(ll[0]['move_id'][0])
        print(f"  {slid} {sl['date']} R$ {sl['amount']:,.2f} | {sl['payment_ref'][:45]} | is_reconciled={sl['is_reconciled']}")
        alvo.append(slid)

    if inv_ids:
        print("\n  faturas que serao reabertas:")
        for inv in o.execute_kw('account.move', 'read', [list(inv_ids)],
                                {'fields': ['name', 'amount_residual', 'payment_state'], 'context': CTX}):
            print(f"     {inv['name']:<22} residual_atual={inv['amount_residual']:,.2f} ({inv['payment_state']})")

    if not alvo:
        print("\n[nada a fazer]"); return
    if not CONFIRMAR:
        print("\n[DRY-RUN] --confirmar executa button_undo_reconciliation nas linhas acima.")
        return

    # metodo: remove_move_reconcile na linha FORNECEDORES (11038) do move da statement line.
    # Desfaz o partial com a fatura ENTSI (reabre o residual). button_undo_reconciliation NAO
    # existe nesta versao CIEL IT; remove_move_reconcile e o metodo classico (publico) do Odoo.
    ok = fail = 0
    for slid in alvo:
        sl = sr('account.bank.statement.line', [('id', '=', slid)], ['move_id'])[0]
        forn = sr('account.move.line', [('move_id', '=', sl['move_id'][0]), ('account_id', '=', 11038)],
                  ['id', 'reconciled'])
        ids = [l['id'] for l in forn]
        if not ids:
            print(f"  SKIP {slid}: sem linha FORNECEDORES"); continue
        try:
            o.execute_kw('account.move.line', 'remove_move_reconcile', [ids], {'context': CTX})
            chk = sr('account.move.line', [('id', 'in', ids)], ['reconciled', 'amount_residual'])
            ok += 1
            print(f"  OK desconciliado {slid} | linhas FORNECEDORES recon agora: "
                  f"{[(c['reconciled'], round(c['amount_residual'], 2)) for c in chk]}")
        except Exception as ex:
            fail += 1
            print(f"  FALHA {slid}: {str(ex)[:160]}")
    # medir faturas reabertas
    if inv_ids:
        print("\n  faturas apos desconciliacao:")
        for inv in o.execute_kw('account.move', 'read', [list(inv_ids)],
                                {'fields': ['name', 'amount_residual', 'payment_state'], 'context': CTX}):
            print(f"     {inv['name']:<22} residual={inv['amount_residual']:,.2f} ({inv['payment_state']})")
    print(f"\n[FIM] ok={ok} fail={fail}")


if __name__ == '__main__':
    main()
