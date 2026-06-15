#!/usr/bin/env python3
"""G9 INVESTIGA (READ-ONLY) — anatomia da conta corrente FB<->LF.

Responde: os creditos conciliados no FIFO sao PAGAMENTO (dinheiro) ou AJUSTE (insumos)?
A FB pagou de verdade? Contra qual conta?
NAO escreve nada no Odoo.
"""
import sys
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5]}


def main():
    o = get_odoo_connection()
    assert o.authenticate(), "FALHA AUTH"
    print(f"UID {o._uid}\n")

    def rg(m, d, f, g):
        return o.execute_kw(m, 'read_group', [d, f, g], {'context': CTX, 'lazy': False})

    def jname(jids):
        if not jids:
            return {}
        js = o.execute_kw('account.journal', 'read', [list(set(jids)), ['name', 'code', 'type']], {'context': CTX})
        return {j['id']: f"{j['code']}/{j['type']}" for j in js}

    def anat(label, acc, partner):
        print("=" * 78)
        print(f"{label} — conta {acc} partner {partner} (D=gera saldo, C=baixa) por journal")
        g = rg('account.move.line',
               [('account_id', '=', acc), ('partner_id', '=', partner), ('parent_state', '=', 'posted')],
               ['debit:sum', 'credit:sum'], ['journal_id'])
        jn = jname([row['journal_id'][0] for row in g if row.get('journal_id')])
        td = tc = 0.0
        for row in sorted(g, key=lambda r: -((r.get('credit') or 0) + (r.get('debit') or 0))):
            j = row.get('journal_id')
            jl = jn.get(j[0], str(j)) if j else 'SEM_JOURNAL'
            d, c = row.get('debit') or 0, row.get('credit') or 0
            td += d; tc += c
            print(f"  {jl:28s} D {d:>16,.2f}  C {c:>16,.2f}  ({row['__count']})")
        print(f"  {'TOTAL':28s} D {td:>16,.2f}  C {tc:>16,.2f}  | saldo D-C = {td - tc:,.2f}")

    # 1) Conta corrente vista pela LF (a receber da FB)
    anat("CLIENTES LF (a receber da FB)", 26085, 1)
    # 2) Conta corrente vista pela FB (a pagar a LF)
    anat("FORNECEDORES FB (a pagar a LF)", 11038, 35)

    # 3) Pagamentos efetivos via account.payment
    for lbl, comp, part in [("FB(1) paga -> LF(35)", 1, 35), ("LF(5) recebe <- FB(1)", 5, 1)]:
        print("=" * 78)
        print(f"account.payment {lbl}")
        try:
            g = rg('account.payment', [('company_id', '=', comp), ('partner_id', '=', part), ('state', '!=', 'draft')],
                   ['amount:sum'], ['payment_type'])
            if not g:
                print("  (nenhum)")
            for row in g:
                print(f"  {row.get('payment_type')}: R$ {row.get('amount') or 0:,.2f} ({row['__count']})")
        except Exception as e:
            print("  falhou:", str(e)[:140])


if __name__ == '__main__':
    main()
