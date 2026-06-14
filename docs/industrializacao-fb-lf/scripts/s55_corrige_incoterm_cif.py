#!/usr/bin/env python3
"""S55 — CORRECAO FISCAL (Rafael, 2026-06-14): o incoterm correto do retorno de
industrializacao LF->FB e' CIF (frete por conta do EMITENTE=LF) com transportadora LF —
NAO FOB. FOB implicaria transportadora FB (destinatario arca). O s51 setou FOB(4) espelhando
as NFs reais, mas as reais estao INCONSISTENTES (709632: FOB + carrier LF — a combinacao que
o Rafael apontou como errada; as operadoras erram na duplicacao do modelo).

Corrige invoice_incoterm_id = [6] CIF nas 2 NFs. Carrier LF (999) ja' aplicado no s53 (mantem).

REVERSIVEL: incoterm e' campo nao-contabil. check_move_validity=False.

MODOS:
  (sem flag)   READ: incoterm + carrier atuais
  --executar   seta invoice_incoterm_id=CIF(6) nas 2
"""
import sys
import argparse
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5], 'company_id': 5, 'lang': 'pt_BR'}
INCOTERM_CIF = 6   # [CIF] CIF — frete por conta do emitente (LF). Regra fiscal Rafael.


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--executar', action='store_true')
    ap.add_argument('--nf1', type=int, default=791437)
    ap.add_argument('--nf2', type=int, default=791441)
    args = ap.parse_args()
    nfs = [args.nf1, args.nf2]
    o = get_odoo_connection(); assert o.authenticate(), "FALHA AUTH"

    def rd(ids, fields):
        return o.execute_kw('account.move', 'read', [list(ids)], {'fields': fields, 'context': CTX})

    F = ['name', 'invoice_incoterm_id', 'l10n_br_carrier_id']
    print("=" * 80)
    print(f"S55 — incoterm CIF({INCOTERM_CIF}) + carrier LF (retorno LF->FB = frete do emitente)")
    print("=" * 80)
    for r in rd(nfs, F):
        print(f"  NF {r['id']} {r['name']}: incoterm={r.get('invoice_incoterm_id')} carrier={r.get('l10n_br_carrier_id')}")

    if not args.executar:
        print(f"\n  [DRY-RUN] alvo: invoice_incoterm_id={INCOTERM_CIF} (CIF) nas 2. carrier LF mantido. --executar")
        return

    for nf in nfs:
        o.execute_kw('account.move', 'write', [[nf], {'invoice_incoterm_id': INCOTERM_CIF}],
                     {'context': dict(CTX, check_move_validity=False)})
    print(f"\n  [escrita] invoice_incoterm_id={INCOTERM_CIF} (CIF) aplicado. DEPOIS:")
    for r in rd(nfs, F):
        print(f"  NF {r['id']} {r['name']}: incoterm={r.get('invoice_incoterm_id')} carrier={r.get('l10n_br_carrier_id')}")
    print(f"\n  >>> re-testar preview via SA: s49 --executar")


if __name__ == '__main__':
    main()
