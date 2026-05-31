#!/usr/bin/env python3
"""
Passo 0 — DIMENSIONAR (READ-ONLY) — Industrializacao FB<->LF.

NAO escreve nada. Quantifica:
  A) De onde vem o estoque da LF: pickings de ENTRADA por picking_type (compra
     direta pt19 vs recebimento industrializacao pt64) -> testa a premissa
     "a LF nao tem estoque proprio / tudo e terceiros".
  B) Saldo contabil ATUAL das contas de estoque-proprio da LF (1150100001/002/
     006/007/010) -> magnitude da reclassificacao no lado LF (espelho do R$785k FB).
  C) Saldo atual de 1150200001/1150200002 na LF (devem estar ~zero hoje).

Uso:
    source .venv/bin/activate
    python docs/industrializacao-fb-lf/scripts/passo0_dimensionar.py
"""
import sys
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CMP_LF = 5
CUTOFF = '2025-05-01'  # ~12 meses (sizing, nao critico p/ timezone)

VAL_OWN_CODES = ['1150100001', '1150100002', '1150100006', '1150100007', '1150100010']
TERC_CODES = ['1150200001', '1150200002', '1150200003']
PROD_CODE = ['1150100004']


def main():
    odoo = get_odoo_connection()
    if not odoo.authenticate():
        raise SystemExit("Falha auth Odoo")

    # ---------- A) entradas na LF por picking_type ----------
    print("=" * 90)
    print("A) ENTRADAS na LF por picking_type (state=done, desde", CUTOFF, ")")
    print("=" * 90)
    pts = odoo.search_read('stock.picking.type',
                           [('company_id', '=', CMP_LF), ('code', '=', 'incoming')],
                           ['id', 'name', 'sequence_code'], limit=50)
    pt_by_id = {p['id']: p for p in pts}
    print("  picking types incoming LF:", [(p['id'], p['sequence_code']) for p in pts])
    grp = odoo.execute_kw('stock.picking', 'read_group',
                          [[('company_id', '=', CMP_LF),
                            ('picking_type_id', 'in', list(pt_by_id)),
                            ('state', '=', 'done'),
                            ('date_done', '>=', CUTOFF)],
                           ['id'], ['picking_type_id']],
                          {'lazy': False})
    print(f"\n  {'picking_type':32s} {'#pickings done (12m)':>22s}")
    for g in sorted(grp, key=lambda x: -x['__count']):
        nm = g['picking_type_id'][1] if g['picking_type_id'] else '?'
        print(f"  {nm[:32]:32s} {g['__count']:>22}")

    # ---------- B) saldo contabil das contas de estoque-proprio LF ----------
    print()
    print("=" * 90)
    print("B) SALDO CONTABIL ATUAL — contas de estoque-proprio da LF (cmp=5, posted)")
    print("   (magnitude da reclassificacao no lado LF, espelho do R$785k da FB)")
    print("=" * 90)
    accs = odoo.search_read('account.account',
                            [('code', 'in', VAL_OWN_CODES + TERC_CODES + PROD_CODE),
                             ('company_id', '=', CMP_LF)],
                            ['id', 'code', 'name'], limit=50)
    acc_by_id = {a['id']: a for a in accs}
    grp2 = odoo.execute_kw('account.move.line', 'read_group',
                           [[('account_id', 'in', list(acc_by_id)),
                             ('company_id', '=', CMP_LF),
                             ('parent_state', '=', 'posted')],
                            ['balance:sum', 'debit:sum', 'credit:sum'],
                            ['account_id']],
                           {'lazy': False})
    grp2_by_acc = {g['account_id'][0]: g for g in grp2 if g['account_id']}
    tot_own = 0.0
    print(f"\n  {'code':12s} {'nome':34s} {'saldo (D-C)':>18s} {'#lancs':>8s}")
    for a in sorted(accs, key=lambda x: x['code']):
        g = grp2_by_acc.get(a['id'])
        bal = g['balance'] if g else 0.0
        n = g['__count'] if g else 0
        if a['code'] in VAL_OWN_CODES:
            tot_own += bal
        print(f"  {a['code']:12s} {a['name'][:34]:34s} {bal:>18,.2f} {n:>8}")
    print(f"\n  >> SALDO TOTAL estoque-proprio LF (1150100001/002/006/007/010): R$ {tot_own:,.2f}")
    print("     (este e o ativo que a premissa 'tudo e terceiros' quer levar p/ 1150200001)")


if __name__ == '__main__':
    main()
