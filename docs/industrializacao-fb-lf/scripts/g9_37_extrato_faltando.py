#!/usr/bin/env python3
"""G9 INVESTIGA (READ-ONLY) — os ~2,4M de diferença sao extrato faltando na LF?

Cruza valor-a-valor: cada pagamento FB->LF 2026 (debito FORNECEDORES) deveria ter uma
entrada NACOM no extrato da LF. Os pagamentos sem par = extrato faltando (ou transito).
NAO escreve nada.
"""
import sys
from collections import Counter, defaultdict
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

    # A = pagamentos FB -> LF 2026 (debitos FORNECEDORES partner LF), por valor
    pag = sr('account.move.line', [('account_id', '=', 11038), ('partner_id', '=', 35),
             ('parent_state', '=', 'posted'), ('debit', '>', 0), ('date', '>=', '2026-01-01')],
             ['date', 'debit', 'move_id', 'journal_id'], order='date')
    # B = entradas NACOM no extrato da LF 2026
    jb = [j['id'] for j in sr('account.journal', [('type', '=', 'bank'), ('company_id', '=', 5)], ['id'])]
    ent = sr('account.bank.statement.line', [('journal_id', 'in', jb), ('company_id', '=', 5),
             ('date', '>=', '2026-01-01'), ('amount', '>', 0), ('payment_ref', 'ilike', 'NACOM')], ['amount'])
    print(f"pagamentos FB->LF 2026 (debito FORNECEDORES): {len(pag)} = R$ {sum(p['debit'] for p in pag):,.2f}")
    print(f"entradas NACOM no extrato LF 2026:           {len(ent)} = R$ {sum(e['amount'] for e in ent):,.2f}")

    # multiset match por valor (centavo)
    B = Counter(round(e['amount'], 2) for e in ent)
    falt = []
    for p in pag:
        k = round(p['debit'], 2)
        if B.get(k, 0) > 0:
            B[k] -= 1
        else:
            falt.append(p)
    # nomes dos moves faltantes
    mids = list({p['move_id'][0] for p in falt})
    nm = {}
    for i in range(0, len(mids), 300):
        for m in o.execute_kw('account.move', 'read', [mids[i:i + 300]], {'fields': ['name', 'ref'], 'context': CTX}):
            nm[m['id']] = m
    print(f"\nPAGAMENTOS FB SEM entrada NACOM no extrato LF: {len(falt)} = R$ {sum(p['debit'] for p in falt):,.2f}")
    pormes = defaultdict(lambda: [0, 0.0])
    for p in falt:
        pormes[p['date'][:7]][0] += 1; pormes[p['date'][:7]][1] += p['debit']
    print("  por mês (data do pagamento FB):")
    for mes in sorted(pormes):
        print(f"    {mes}: {pormes[mes][0]:3d} | R$ {pormes[mes][1]:,.2f}")
    print("  detalhe (até 20):")
    for p in sorted(falt, key=lambda x: -x['debit'])[:20]:
        info = nm.get(p['move_id'][0], {})
        print(f"    {p['date']} R$ {p['debit']:>12,.2f}  {info.get('name','')} | {str(info.get('ref') or '')[:50]}")


if __name__ == '__main__':
    main()
