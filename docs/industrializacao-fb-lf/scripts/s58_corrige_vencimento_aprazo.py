#!/usr/bin/env python3
"""S58 — CORRECAO do gap que rejeitou a NF-1: vencimento da duplicata = data de emissao
=> o CIEL IT marca "pagamento a vista" e rejeita os dados de cobranca. A NF real autorizada
709632 usa vencimento = emissao + 1 dia (a-prazo) => duplicata permitida.

Ajusta a date_maturity da linha payment_term (duplicata) para invoice_date + 1 dia (a-prazo,
espelha a real). A NF de servico tem recebivel real (FB paga o servico), entao manter a
duplicata e' correto — so torna-la a-prazo. Aplica so na NF-1 (a NF-2 nao tem duplicata).

REVERSIVEL: muda so a data de vencimento (nao o valor/conta). check_move_validity=False.

MODOS:
  (sem flag)   READ: linha payment_term atual + data alvo
  --executar   seta date_maturity = invoice_date + 1 dia
"""
import sys
import argparse
import datetime
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5], 'company_id': 5, 'lang': 'pt_BR'}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--executar', action='store_true')
    ap.add_argument('--nf1', type=int, default=791437)
    args = ap.parse_args()
    nf = args.nf1
    o = get_odoo_connection(); assert o.authenticate(), "FALHA AUTH"

    def rr(model, dom, fields, **kw):
        kw2 = {'fields': fields, 'context': CTX}; kw2.update(kw)
        return o.execute_kw(model, 'search_read', [dom], kw2)

    def rd(model, ids, fields):
        return o.execute_kw(model, 'read', [list(ids)], {'fields': fields, 'context': CTX})

    h = rd('account.move', [nf], ['name', 'invoice_date', 'invoice_date_due', 'l10n_br_situacao_nf'])[0]
    inv_date = h['invoice_date']
    alvo = (datetime.date.fromisoformat(inv_date) + datetime.timedelta(days=1)).isoformat()
    lns = rr('account.move.line', [('move_id', '=', nf), ('display_type', '=', 'payment_term')],
             ['name', 'date_maturity', 'debit', 'credit'])

    print("=" * 84)
    print(f"S58 — vencimento a-prazo na NF-1 {nf} {h['name']} (situacao={h.get('l10n_br_situacao_nf')})")
    print("=" * 84)
    print(f"  invoice_date={inv_date} | invoice_date_due={h.get('invoice_date_due')}")
    for l in lns:
        print(f"  linha payment_term: venc={l.get('date_maturity')} D={l.get('debit')} C={l.get('credit')}")
    print(f"  ALVO: date_maturity = {alvo} (emissao + 1 dia = a-prazo, como a NF real)")

    if not args.executar:
        print(f"\n  [DRY-RUN] --executar para aplicar")
        return

    for l in lns:
        o.execute_kw('account.move.line', 'write', [[l['id']], {'date_maturity': alvo}],
                     {'context': dict(CTX, check_move_validity=False)})
    # tambem alinhar o header (related/stored)
    try:
        o.execute_kw('account.move', 'write', [[nf], {'invoice_date_due': alvo}],
                     {'context': dict(CTX, check_move_validity=False)})
    except Exception as e:
        print(f"  (aviso: invoice_date_due header: {str(e)[:80]})")
    h2 = rd('account.move', [nf], ['invoice_date_due'])[0]
    lns2 = rr('account.move.line', [('move_id', '=', nf), ('display_type', '=', 'payment_term')], ['date_maturity'])
    print(f"\n  [escrita] DEPOIS: invoice_date_due={h2.get('invoice_date_due')} | "
          f"linhas venc={[l.get('date_maturity') for l in lns2]}")
    print(f"  >>> re-validar preview via SA: s49 --executar")


if __name__ == '__main__':
    main()
