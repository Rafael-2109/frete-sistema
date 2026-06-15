#!/usr/bin/env python3
"""G9 RE-CRUZA (READ-ONLY) pagamentos FB->LF x TODAS as entradas bancarias da LF.

Corrige o furo do filtro 'payment_ref ilike NACOM': o extrato SANTANDER da LF registra os
PIX da FB com memo 'PIX RECEBIDO 61724241000178' (CNPJ da FB), sem a palavra NACOM. Aqui o
lado LF = TODAS as entradas (amount>0) dos journals bank da LF, qualquer memo. Cruza por
valor (multiset) com os pagamentos FB->LF (debito FORNECEDORES/LF) agrupados por transacao.
Classifica as entradas Santander por origem. NAO escreve nada.
"""
import sys
from collections import defaultdict, Counter
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5]}
ACC_FORN_FB, P_LF = 11038, 35
CNPJ_FB, CNPJ_LF = '61724241000178', '18467441000163'


def main():
    o = get_odoo_connection()
    assert o.authenticate(), "FALHA AUTH"
    print(f"UID {o._uid}\n")

    def sr(m, d, f, **k):
        kw = {'fields': f, 'context': CTX}; kw.update(k)
        return o.execute_kw(m, 'search_read', [d], kw)

    # A = pagamentos FB->LF 2026 por transacao (move)
    pag = sr('account.move.line', [('account_id', '=', ACC_FORN_FB), ('partner_id', '=', P_LF),
             ('parent_state', '=', 'posted'), ('debit', '>', 0), ('date', '>=', '2026-01-01')],
             ['date', 'debit', 'move_id'])
    trans = defaultdict(lambda: {'val': 0.0, 'date': None})
    for p in pag:
        t = trans[p['move_id'][0]]; t['val'] += p['debit']; t['date'] = p['date']

    # B = TODAS as entradas bank LF 2026 (sem filtro de memo)
    jb = [j['id'] for j in sr('account.journal', [('type', '=', 'bank'), ('company_id', '=', 5)], ['id'])]
    ent = sr('account.bank.statement.line', [('journal_id', 'in', jb), ('company_id', '=', 5),
             ('date', '>=', '2026-01-01'), ('amount', '>', 0)],
             ['date', 'amount', 'payment_ref', 'journal_id', 'is_reconciled'], order='date')

    print(f"A) transacoes pagto FB->LF 2026:        {len(trans):>3} = R$ {sum(t['val'] for t in trans.values()):,.2f}")
    print(f"B) entradas bancarias LF 2026 (TODAS):  {len(ent):>3} = R$ {sum(e['amount'] for e in ent):,.2f}\n")

    # cruzamento por valor (multiset)
    B = Counter(round(e['amount'], 2) for e in ent)
    falt = []
    for mid, t in trans.items():
        k = round(t['val'], 2)
        if B.get(k, 0) > 0:
            B[k] -= 1
        else:
            falt.append(t)
    print(f">> Pagamentos FB SEM entrada em NENHUM banco LF: {len(falt)} = R$ {sum(t['val'] for t in falt):,.2f}")
    if falt:
        for t in sorted(falt, key=lambda x: -x['val'])[:10]:
            print(f"     {t['date']} R$ {t['val']:,.2f}")

    # classificacao das entradas Santander por origem do memo
    print("\n=== SANTANDER LF — classificacao das 37 entradas ===")
    sant = [e for e in ent if e['journal_id'][1].strip().upper() == 'SANTANDER']
    cls = defaultdict(lambda: [0, 0.0])
    pag_vals = Counter(round(t['val'], 2) for t in trans.values())
    casa_fb = [0, 0.0]
    for e in sant:
        up = (e['payment_ref'] or '').upper()
        if 'RESGATE' in up or 'CONTAMAX' in up or 'APLICA' in up:
            cat = 'RESGATE/aplicacao (nao-terceiro)'
        elif CNPJ_FB in up:
            cat = 'PIX da FB (CNPJ 6172...0178)'
        elif CNPJ_LF in up or 'FAMIGLIA' in up:
            cat = 'PIX da propria LF (revisar)'
        else:
            cat = 'PIX RECEBIDO sem CNPJ (verificar)'
        cls[cat][0] += 1; cls[cat][1] += e['amount']
        if pag_vals.get(round(e['amount'], 2), 0) > 0:
            casa_fb[0] += 1; casa_fb[1] += e['amount']
    for cat, (n, v) in sorted(cls.items(), key=lambda x: -x[1][1]):
        print(f"  {cat:<36} {n:>3} = R$ {v:,.2f}")
    print(f"  -> dessas, casam por VALOR com um pagamento FB->LF: {casa_fb[0]} = R$ {casa_fb[1]:,.2f}")


if __name__ == '__main__':
    main()
