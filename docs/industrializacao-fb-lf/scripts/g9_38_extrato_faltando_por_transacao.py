#!/usr/bin/env python3
"""G9 INVESTIGA (READ-ONLY) — extrato faltando, cruzando por TRANSACAO (nao por fatura).

Agrupa os debitos FORNECEDORES FB 2026 por move (= 1 transacao bancaria) e cruza com as
entradas NACOM do extrato LF. Transacao FB sem entrada LF = extrato faltando (ou transito).
Distingue pelo TIMING (recente=transito; espalhado=faltando). NAO escreve nada.
"""
import sys
from collections import defaultdict, Counter
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5]}


def main():
    o = get_odoo_connection()
    assert o.authenticate(), "FALHA AUTH"
    print(f"UID {o._uid}\n")

    def sr(m, d, f, **k):
        kw = {'fields': f, 'context': CTX}; kw.update(k)
        return o.execute_kw(m, 'search_read', [d], kw)

    pag = sr('account.move.line', [('account_id', '=', 11038), ('partner_id', '=', 35),
             ('parent_state', '=', 'posted'), ('debit', '>', 0), ('date', '>=', '2026-01-01')],
             ['date', 'debit', 'move_id'])
    # agrupar por move = transacao
    trans = defaultdict(lambda: {'val': 0.0, 'date': None})
    for p in pag:
        t = trans[p['move_id'][0]]; t['val'] += p['debit']; t['date'] = p['date']
    jb = [j['id'] for j in sr('account.journal', [('type', '=', 'bank'), ('company_id', '=', 5)], ['id'])]
    ent = sr('account.bank.statement.line', [('journal_id', 'in', jb), ('company_id', '=', 5),
             ('date', '>=', '2026-01-01'), ('amount', '>', 0), ('payment_ref', 'ilike', 'NACOM')], ['amount'])
    print(f"transacoes FB->LF 2026 (moves de pagamento): {len(trans)} = R$ {sum(t['val'] for t in trans.values()):,.2f}")
    print(f"entradas NACOM no extrato LF 2026:           {len(ent)} = R$ {sum(e['amount'] for e in ent):,.2f}")

    B = Counter(round(e['amount'], 2) for e in ent)
    falt = []
    for mid, t in trans.items():
        k = round(t['val'], 2)
        if B.get(k, 0) > 0:
            B[k] -= 1
        else:
            falt.append((mid, t))
    nm = {}
    mids = [mid for mid, _ in falt]
    for i in range(0, len(mids), 300):
        for m in o.execute_kw('account.move', 'read', [mids[i:i + 300]], {'fields': ['name', 'ref'], 'context': CTX}):
            nm[m['id']] = m

    print(f"\nTRANSACOES FB SEM entrada NACOM no extrato LF: {len(falt)} = R$ {sum(t['val'] for _, t in falt):,.2f}")
    pormes = defaultdict(lambda: [0, 0.0])
    for _, t in falt:
        pormes[t['date'][:7]][0] += 1; pormes[t['date'][:7]][1] += t['val']
    print("  por mês (data do pagamento FB):")
    for mes in sorted(pormes):
        print(f"    {mes}: {pormes[mes][0]:3d} | R$ {pormes[mes][1]:,.2f}")
    print("  detalhe (maiores):")
    for mid, t in sorted(falt, key=lambda x: -x[1]['val'])[:15]:
        info = nm.get(mid, {})
        print(f"    {t['date']} R$ {t['val']:>12,.2f}  {info.get('name','')} | {str(info.get('ref') or '')[:40]}")


if __name__ == '__main__':
    main()
