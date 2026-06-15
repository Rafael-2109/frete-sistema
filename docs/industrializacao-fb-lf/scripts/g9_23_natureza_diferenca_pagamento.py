#!/usr/bin/env python3
"""G9 INVESTIGA (READ-ONLY) — a diferenca de pagamento e: defasagem (ultimos), pago a maior, ou divergencia de NF?

(1) FB pagou x LF baixou por MES (acumulada) — defasagem aparece como salto recente.
(2) Adiantamentos FB (debito sem fatura = pago a maior) — contagem/valor/datas.
(3) Pagamentos FB reconciliados x em aberto — se reconciliados, foram aplicados a titulos (nao 'a maior').
NAO escreve nada.
"""
import sys
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5]}
ACC_LF, P_FB = 26085, 1
ACC_FB, P_LF = 11038, 35
J_DIV_LF = 894


def main():
    o = get_odoo_connection()
    assert o.authenticate(), "FALHA AUTH"
    print(f"UID {o._uid}\n")

    def rg(d, f, g):
        return o.execute_kw('account.move.line', 'read_group', [d, f, g], {'context': CTX, 'lazy': False})

    base_lf = [('account_id', '=', ACC_LF), ('partner_id', '=', P_FB), ('parent_state', '=', 'posted')]
    base_fb = [('account_id', '=', ACC_FB), ('partner_id', '=', P_LF), ('parent_state', '=', 'posted')]
    P = lambda x: f"{x:>14,.2f}"

    print("=" * 78)
    print("1) FB pagou x LF baixou por MES (acumulada revela onde o descasamento surge)")
    gm_fb = rg(base_fb + [('debit', '>', 0)], ['debit:sum'], ['date:month'])
    gm_lf = rg(base_lf + [('credit', '>', 0), ('journal_id', '!=', J_DIV_LF)], ['credit:sum'], ['date:month'])
    pf = {r['date:month']: r.get('debit', 0) or 0 for r in gm_fb}
    pl = {r['date:month']: r.get('credit', 0) or 0 for r in gm_lf}
    print(f"   {'Mes':12s} {'FB pagou':>14s} {'LF baixou':>14s} {'dif mes':>14s} {'dif acum':>14s}")
    ac = 0.0
    for mes in sorted(set(pf) | set(pl)):
        a, b = pf.get(mes, 0), pl.get(mes, 0); ac += a - b
        print(f"   {mes:12s} {P(a)} {P(b)} {P(a - b)} {P(ac)}")

    print("=" * 78)
    print("2) ADIANTAMENTOS FB = pagto sem fatura aplicada (debito FORNECEDORES em aberto, residual>0)")
    adi = o.execute_kw('account.move.line', 'search_read',
                       [base_fb + [('debit', '>', 0), ('reconciled', '=', False), ('amount_residual', '>', 0)]],
                       {'fields': ['date', 'amount_residual', 'move_id'], 'order': 'date', 'context': CTX})
    tot = sum(l['amount_residual'] for l in adi)
    print(f"   {len(adi)} linhas | total R$ {tot:,.2f} | datas {adi[0]['date'] if adi else '-'} a {adi[-1]['date'] if adi else '-'}")
    for l in adi[:12]:
        print(f"     {l['date']}  R$ {l['amount_residual']:>12,.2f}  {l['move_id'][1]}")
    if len(adi) > 12:
        print(f"     ... (+{len(adi) - 12})")

    print("=" * 78)
    print("3) PAGAMENTOS FB (debitos) reconciliados x em aberto — se reconciliado, foi aplicado a titulo")
    g_rec = rg(base_fb + [('debit', '>', 0), ('reconciled', '=', True)], ['debit:sum'], [])
    g_abe = rg(base_fb + [('debit', '>', 0), ('reconciled', '=', False)], ['debit:sum'], [])
    rec = g_rec[0].get('debit', 0) or 0 if g_rec else 0
    abe = g_abe[0].get('debit', 0) or 0 if g_abe else 0
    print(f"   reconciliado (aplicado a fatura): R$ {rec:,.2f}")
    print(f"   em aberto (adiantamento/parcial): R$ {abe:,.2f}")


if __name__ == '__main__':
    main()
