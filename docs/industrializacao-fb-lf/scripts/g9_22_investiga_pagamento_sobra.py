#!/usr/bin/env python3
"""G9 INVESTIGA (READ-ONLY) — a divergencia de pagamento e "pagamento que sobrou"?

Testa a hipotese: as notas diminuiram (G9 tirou insumos) -> a FB pagou a mais -> sobrou.
Mede: excedentes (credito em aberto) na LF, adiantamentos (debito em aberto) na FB,
e o timing (por ano) da diferenca FB-pagou x LF-recebeu. NAO escreve nada.
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

    def s1(domain, field):
        g = o.execute_kw('account.move.line', 'read_group', [domain, [f'{field}:sum'], []], {'context': CTX, 'lazy': False})
        return (g[0].get(field, 0) or 0, g[0]['__count'])

    base_lf = [('account_id', '=', ACC_LF), ('partner_id', '=', P_FB), ('parent_state', '=', 'posted')]
    base_fb = [('account_id', '=', ACC_FB), ('partner_id', '=', P_LF), ('parent_state', '=', 'posted')]
    P = lambda x: f"{x:>16,.2f}"

    print("=" * 78)
    print("1) SOBROU PAGAMENTO? (saldo CREDOR em aberto = excedente a favor da FB)")
    cred_aberto, n1 = s1(base_lf + [('amount_residual', '<', 0), ('reconciled', '=', False)], 'amount_residual')
    receb_aberto, n2 = s1(base_lf + [('amount_residual', '>', 0), ('reconciled', '=', False)], 'amount_residual')
    print(f"   LF a-receber em aberto (devedor) : {P(receb_aberto)}  ({n2} linhas)")
    print(f"   LF excedente em aberto (credor)  : {P(cred_aberto)}  ({n1} linhas)  <- se ~0, NAO sobrou")
    adiant_fb, n3 = s1(base_fb + [('amount_residual', '>', 0), ('reconciled', '=', False)], 'amount_residual')
    apagar_aberto_fb, n4 = s1(base_fb + [('amount_residual', '<', 0), ('reconciled', '=', False)], 'amount_residual')
    print(f"   FB a-pagar em aberto (credor)    : {P(apagar_aberto_fb)}  ({n4} linhas)")
    print(f"   FB adiantamento em aberto (devedor): {P(adiant_fb)}  ({n3} linhas)  <- pagto sem fatura na FB")

    print("=" * 78)
    print("2) TIMING — FB pagou x LF recebeu, por ANO (debitos FB x creditos LF nao-G9)")
    gm_fb = o.execute_kw('account.move.line', 'read_group', [base_fb + [('debit', '>', 0)], ['debit:sum'], ['date:year']], {'context': CTX, 'lazy': False})
    gm_lf = o.execute_kw('account.move.line', 'read_group', [base_lf + [('credit', '>', 0), ('journal_id', '!=', J_DIV_LF)], ['credit:sum'], ['date:year']], {'context': CTX, 'lazy': False})
    pf = {r['date:year']: r.get('debit', 0) or 0 for r in gm_fb}
    pl = {r['date:year']: r.get('credit', 0) or 0 for r in gm_lf}
    print(f"   {'Ano':6s} {'FB pagou':>16s} {'LF recebeu':>16s} {'diferenca':>16s}")
    tot = 0.0
    for y in sorted(set(pf) | set(pl)):
        a, b = pf.get(y, 0), pl.get(y, 0); tot += a - b
        print(f"   {str(y):6s} {P(a)} {P(b)} {P(a - b)}")
    print(f"   {'TOTAL':6s} {P(sum(pf.values()))} {P(sum(pl.values()))} {P(tot)}")

    print("=" * 78)
    print("3) A FB pagou o SERVICO ou o valor CHEIO? (debitos FB partner 35 por journal)")
    g = o.execute_kw('account.move.line', 'read_group', [base_fb + [('debit', '>', 0)], ['debit:sum'], ['journal_id']], {'context': CTX, 'lazy': False})
    for r in sorted(g, key=lambda x: -(x.get('debit') or 0)):
        j = r.get('journal_id')
        print(f"   {str(j[1]) if j else '?':32s} {P(r.get('debit') or 0)}  ({r['__count']})")


if __name__ == '__main__':
    main()
