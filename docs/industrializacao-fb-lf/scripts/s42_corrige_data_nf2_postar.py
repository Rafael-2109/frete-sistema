#!/usr/bin/env python3
"""S42 — completa a FASE A: corrige o invoice_date da NF-2 (789485) que ficou 14/06 (UTC,
gotcha TZ da SA — datetime.date.today() no servidor da UTC) e posta a NF-2, medindo a baixa
da PASSIVA 5101020001. A NF-1 (789484) ja' esta posted (VND/2026/00384).

Alinha invoice_date da NF-2 = invoice_date da NF-1 (data BRT correta, 13/06). NAO transmite.

MODOS:
  (sem flag)   READ: datas + estado das 2 + saldo PASSIVA
  --executar   corrige data NF-2 + action_post NF-2 + mede baixa
"""
import sys
import argparse
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5], 'company_id': 5, 'lang': 'pt_BR'}
NF1, NF2 = 789484, 789485
ACC_PASSIVA = 26667
POST_CTX = dict(CTX, allowed_company_ids=[5])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--executar', action='store_true')
    args = ap.parse_args()
    o = get_odoo_connection(); assert o.authenticate(), "FALHA AUTH"

    def rr(model, dom, fields, **kw):
        kw2 = {'fields': fields, 'context': CTX}; kw2.update(kw)
        return o.execute_kw(model, 'search_read', [dom], kw2)
    def rd(model, ids, fields):
        return o.execute_kw(model, 'read', [list(ids)], {'fields': fields, 'context': CTX})

    def saldo_passiva():
        lns = rr('account.move.line', [('account_id', '=', ACC_PASSIVA),
                                       ('parent_state', '=', 'posted'), ('company_id', '=', 5)], ['balance'])
        return round(sum(l.get('balance') or 0 for l in lns), 2)

    r = rd('account.move', [NF1, NF2], ['name', 'state', 'invoice_date', 'date'])
    by = {x['id']: x for x in r}
    print("=" * 84)
    for nf in [NF1, NF2]:
        x = by[nf]
        print(f"  NF {nf} {x['name']}: state={x['state']} invoice_date={x['invoice_date']} date={x['date']}")
    print(f"  saldo PASSIVA atual = {saldo_passiva()}")
    data_nf1 = by[NF1]['invoice_date']

    if not args.executar:
        print(f"\n  [DRY-RUN] correcao: NF-2.invoice_date {by[NF2]['invoice_date']} -> {data_nf1} + postar. --executar")
        return

    print(f"\n  [1] corrige NF-2.invoice_date -> {data_nf1} (= NF-1)")
    o.execute_kw('account.move', 'write', [[NF2], {'invoice_date': data_nf1, 'date': data_nf1}],
                 {'context': dict(CTX, check_move_validity=False)})
    saldo0 = saldo_passiva()
    print(f"  [2] action_post NF-2 {NF2}...")
    try:
        o.execute_kw('account.move', 'action_post', [[NF2]], {'context': POST_CTX})
    except Exception as e:
        print(f"      ❌ post NF-2 FALHOU: {str(e)[:240]}"); return
    saldo1 = saldo_passiva()
    nfl = rr('account.move.line', [('move_id', '=', NF2), ('account_id', '=', ACC_PASSIVA)], ['debit', 'credit'])
    debito = round(sum(l.get('debit') or 0 for l in nfl), 2)
    h2 = rd('account.move', [NF2], ['name', 'state', 'l10n_br_cstat_nf'])[0]
    print(f"      NF-2 posted: {h2['name']} state={h2['state']} cstat={h2.get('l10n_br_cstat_nf') or 'VAZIO (nao transmitido) ✅'}")
    print(f"      baixa PASSIVA: {saldo0} -> {saldo1} | Δ={round(saldo1-saldo0,2)} | D conta 26667 = {debito} "
          f"{'✅' if abs((saldo1-saldo0)-debito) < 0.01 and debito > 0 else '⚠️'}")

    print(f"\n  === FASE A COMPLETA ===")
    f = rd('account.move', [NF1, NF2], ['name', 'state', 'l10n_br_cstat_nf', 'amount_total', 'l10n_br_total_nfe'])
    for x in f:
        print(f"    {x['name']}: state={x['state']} cstat={x.get('l10n_br_cstat_nf') or 'VAZIO ✅'} "
              f"total={x['amount_total']} vNF={x['l10n_br_total_nfe']}")
    print(f"\n  >>> PAROU NA BEIRA. Ambas POSTED, NAO transmitidas. Transmissao (PRODUCAO, irreversivel) = go duplo.")
    print(f"  >>> reverter: s37 --cleanup 325344 {NF1} {NF2}")


if __name__ == '__main__':
    main()
