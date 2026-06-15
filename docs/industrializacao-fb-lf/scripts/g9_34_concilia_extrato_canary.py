#!/usr/bin/env python3
"""G9 CONCILIA extrato LF 2026 (entradas FB) contra NFs VND por FIFO.

Mecanica: a statement line tem C TRANSITORIA (suspense). Conciliar = reapontar essa linha
para CLIENTES (26085, partner FB) e reconciliar com o debito da(s) NF(s) VND mais antiga(s).
DRY-RUN default. --canary processa SO a entrada mais antiga (1). --confirmar processa TODAS.
Exclui o PSIC (nao e NF). NAO efetivar sem autorizacao.
"""
import sys
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5]}
ACC_LF, P_FB = 26085, 1
ACC_TRANS = 1110100003
CANARY = '--canary' in sys.argv
CONFIRMAR = '--confirmar' in sys.argv


def main():
    o = get_odoo_connection()
    assert o.authenticate(), "FALHA AUTH"
    modo = 'CANARY (1)' if CANARY else ('CONFIRMAR (TODAS)' if CONFIRMAR else 'DRY-RUN')
    print(f"UID {o._uid} | {modo}\n")

    def sr(m, d, f, **k):
        kw = {'fields': f, 'context': CTX}; kw.update(k)
        return o.execute_kw(m, 'search_read', [d], kw)

    jb = [j['id'] for j in sr('account.journal', [('type', '=', 'bank'), ('company_id', '=', 5)], ['id'])]
    ent = sr('account.bank.statement.line',
             [('journal_id', 'in', jb), ('company_id', '=', 5), ('date', '>=', '2026-01-01'),
              ('amount', '>', 0), ('payment_ref', 'ilike', 'NACOM'), ('is_reconciled', '=', False)],
             ['date', 'amount', 'move_id'], order='date, id')
    if CANARY:
        ent = ent[:1]
    print(f"entradas a conciliar: {len(ent)} = R$ {sum(e['amount'] for e in ent):,.2f}")

    # pilha de NFs VND a receber (FIFO), excluindo PSIC/VAS
    fat = sr('account.move.line',
             [('account_id', '=', ACC_LF), ('partner_id', '=', P_FB), ('parent_state', '=', 'posted'),
              ('debit', '>', 0), ('amount_residual', '>', 0)],
             ['move_id', 'amount_residual', 'date'], order='date, id')
    mids = list({f['move_id'][0] for f in fat})
    names = {}
    for i in range(0, len(mids), 300):
        for m in o.execute_kw('account.move', 'read', [mids[i:i + 300]], {'fields': ['name'], 'context': CTX}):
            names[m['id']] = m['name']
    pilha = [{'id': f['id'], 'nf': names.get(f['move_id'][0], ''), 'r': f['amount_residual']}
             for f in fat if names.get(f['move_id'][0], '').startswith('VND')]
    print(f"NFs VND a receber (FIFO): {len(pilha)} = R$ {sum(p['r'] for p in pilha):,.2f}\n")

    if not (CANARY or CONFIRMAR):
        for e in ent[:3]:
            falta = e['amount']; usa = []
            for p in pilha:
                if p['r'] <= 0.005:
                    continue
                u = min(falta, p['r']); usa.append(f"{p['nf']}({u:,.2f})"); falta -= u
                if falta <= 0.005:
                    break
            print(f"  {e['date']} R$ {e['amount']:>11,.2f} -> {', '.join(usa[:3])}")
        print("\n[DRY-RUN] --canary processa 1; --confirmar processa todas.")
        return

    ok = fail = 0
    for e in ent:
        # re-ler a linha suspense (a contrapartida = unica linha de credito do move)
        mls = sr('account.move.line', [('move_id', '=', e['move_id'][0]), ('credit', '>', 0)], ['credit', 'account_id', 'reconciled'])
        if len(mls) != 1 or mls[0]['reconciled']:
            print(f"  SKIP {e['date']}: contrapartida inesperada ({len(mls)} linhas credito / ja reconciliada)"); continue
        trans_id = mls[0]['id']
        amt = e['amount']
        # selecionar NFs VND FIFO ate cobrir amt
        alvo = []; falta = amt
        for p in pilha:
            if p['r'] <= 0.005:
                continue
            u = min(falta, p['r']); p['r'] -= u; falta -= u; alvo.append(p['id'])
            if falta <= 0.005:
                break
        try:
            # 1) reapontar a linha suspense para CLIENTES / partner FB
            o.execute_kw('account.move.line', 'write', [[trans_id], {'account_id': ACC_LF, 'partner_id': P_FB}], {'context': CTX})
            # 2) reconciliar com os debitos das NFs VND
            o.execute_kw('account.move.line', 'reconcile', [[trans_id] + alvo], {'context': CTX})
            # 3) verificar
            chk = o.execute_kw('account.bank.statement.line', 'read', [[e['id']], ['is_reconciled']], {'context': CTX})
            ok += 1
            print(f"  OK {e['date']} R$ {amt:,.2f} -> {len(alvo)} NF(s) | is_reconciled={chk[0]['is_reconciled']}")
        except Exception as ex:
            fail += 1
            print(f"  FALHA {e['date']} R$ {amt:,.2f}: {str(ex)[:120]}")
            if CANARY:
                break
    print(f"\n[FIM] ok={ok} fail={fail}")


if __name__ == '__main__':
    main()
