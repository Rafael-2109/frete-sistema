#!/usr/bin/env python3
"""G9 VARRE (READ-ONLY) conciliacoes erradas pra LF na FB.

Universo: todos os debitos FORNECEDORES (2120100001 id=11038) com partner LA FAMIGLIA - LF
(35) na company FB (1), posted, 2026. Para cada move, le a origem (statement.line do extrato)
e classifica pelo MEMO:
  - memo confirma LF (CNPJ 18.467.441 ou FAMIGLIA) -> OK (pagamento FB->LF)
  - memo NAO confirma (agua/energia/tarifa/etc ou generico) + veio do extrato -> SUSPEITO
  - sem statement.line (veio de payment/invoice, nao de reconciliacao de extrato) -> OUTRO
NAO escreve nada. Lista os suspeitos com memo p/ decisao.
"""
import sys
from collections import defaultdict
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5]}
ACC_FORN_FB, P_LF, COMP_FB = 11038, 35, 1
DESDE = '--desde-2025' in sys.argv and '2025-01-01' or '2026-01-01'


def main():
    o = get_odoo_connection()
    assert o.authenticate(), "FALHA AUTH"
    print(f"UID {o._uid} | desde {DESDE}\n")

    def sr(m, d, f, **k):
        kw = {'fields': f, 'context': CTX}; kw.update(k)
        return o.execute_kw(m, 'search_read', [d], kw)

    # debitos FORNECEDORES partner LF na FB (cada linha = parte de um pagamento)
    deb = sr('account.move.line', [('account_id', '=', ACC_FORN_FB), ('partner_id', '=', P_LF),
             ('company_id', '=', COMP_FB), ('parent_state', '=', 'posted'),
             ('debit', '>', 0), ('date', '>=', DESDE)],
             ['debit', 'date', 'move_id'])
    # agrupa por move (transacao)
    trans = defaultdict(lambda: {'val': 0.0, 'date': None})
    for d in deb:
        t = trans[d['move_id'][0]]; t['val'] += d['debit']; t['date'] = d['date']
    mids = list(trans.keys())
    mv = {}
    for i in range(0, len(mids), 200):
        for m in o.execute_kw('account.move', 'read', [mids[i:i + 200]],
                              {'fields': ['name', 'journal_id', 'statement_line_id', 'ref', 'move_type'], 'context': CTX}):
            mv[m['id']] = m
    # memos das statement lines
    slids = [mv[m]['statement_line_id'][0] for m in mv if mv[m].get('statement_line_id')]
    memo = {}
    for i in range(0, len(slids), 200):
        for s in o.execute_kw('account.bank.statement.line', 'read', [slids[i:i + 200]],
                              {'fields': ['payment_ref'], 'context': CTX}):
            memo[s['id']] = (s['payment_ref'] or '')

    ok, suspeito, outro = [], [], []
    for mid, t in trans.items():
        m = mv.get(mid, {})
        sl = m.get('statement_line_id')
        if sl:
            txt = memo.get(sl[0], '')
            up = txt.upper()
            rec = {'name': m.get('name'), 'date': t['date'], 'val': t['val'],
                   'banco': (m.get('journal_id') or [0, ''])[1], 'memo': txt}
            if '18.467.441' in up or 'FAMIGLIA' in up:
                ok.append(rec)
            else:
                suspeito.append(rec)
        else:
            outro.append({'name': m.get('name'), 'date': t['date'], 'val': t['val'],
                          'banco': (m.get('journal_id') or [0, ''])[1],
                          'tipo': m.get('move_type'), 'ref': m.get('ref')})

    n = len(trans); v = sum(t['val'] for t in trans.values())
    print(f"UNIVERSO debitos FORNECEDORES/LF na FB (transacoes): {n} = R$ {v:,.2f}")
    print(f"  OK confirmam LF (extrato c/ CNPJ/FAMIGLIA): {len(ok):>3} = R$ {sum(r['val'] for r in ok):,.2f}")
    print(f"  SUSPEITOS (extrato memo NAO confirma LF):   {len(suspeito):>3} = R$ {sum(r['val'] for r in suspeito):,.2f}")
    print(f"  OUTROS (nao vieram de extrato):             {len(outro):>3} = R$ {sum(r['val'] for r in outro):,.2f}\n")

    print("=== SUSPEITOS (conciliacao de extrato com partner LF, memo nao-LF) ===")
    for r in sorted(suspeito, key=lambda x: x['date']):
        print(f"  {r['date']} R$ {r['val']:>11,.2f} {r['name']:<17} [{r['banco']}] {r['memo'][:55]}")

    if outro:
        print(f"\n=== OUTROS (origem != extrato — payment/invoice; conferir se sao FB->LF legitimos) ===")
        for r in sorted(outro, key=lambda x: x['date']):
            print(f"  {r['date']} R$ {r['val']:>11,.2f} {r['name']:<17} {r['tipo']:<12} [{r['banco']}] ref={str(r['ref'])[:30]}")


if __name__ == '__main__':
    main()
