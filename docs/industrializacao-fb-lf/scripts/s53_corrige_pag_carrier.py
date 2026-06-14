#!/usr/bin/env python3
"""S53 — CORRECAO DE CADASTRO pre-transmissao (2/2): seta os gaps achados no diff vs a NF
real autorizada 709632 (s52):
  - payment_provider_id = 31 (Transferencia Bancaria LF)  -> "meio de pagamento" (erro do preview)
  - l10n_br_carrier_id   = 999 (LA FAMIGLIA = a propria LF) -> transportador

REVERSIVEL: campos nao-contabeis. write check_move_validity=False. (incoterm ja feito no s51.)

MODOS:
  (sem flag)   READ: valores atuais vs alvo
  --executar   aplica nas 2 NFs
"""
import sys
import argparse
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5], 'company_id': 5, 'lang': 'pt_BR'}
PAYMENT_PROVIDER = 31    # Transferencia Bancaria LF (= NF real)
CARRIER = 999            # LA FAMIGLIA ALIM LTDA (a propria LF) (= NF real)
ALVO = {'payment_provider_id': PAYMENT_PROVIDER, 'l10n_br_carrier_id': CARRIER}


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

    F = ['name'] + list(ALVO.keys())
    print("=" * 80)
    print("S53 — payment_provider_id + l10n_br_carrier_id (espelha NF real 709632)")
    print("=" * 80)
    for r in rd(nfs, F):
        print(f"  NF {r['id']} {r['name']}: pag={r.get('payment_provider_id') or 'VAZIO'} "
              f"carrier={r.get('l10n_br_carrier_id') or 'VAZIO'}")
    print(f"  alvo: {ALVO}")

    if not args.executar:
        print(f"\n  [DRY-RUN] --executar para aplicar")
        return

    for nf in nfs:
        o.execute_kw('account.move', 'write', [[nf], dict(ALVO)],
                     {'context': dict(CTX, check_move_validity=False)})
    print(f"\n  [escrita] aplicado nas 2 NFs. DEPOIS:")
    for r in rd(nfs, F):
        print(f"  NF {r['id']} {r['name']}: pag={r.get('payment_provider_id')} carrier={r.get('l10n_br_carrier_id')}")
    print(f"\n  >>> re-testar preview via SA: s49 --executar")


if __name__ == '__main__':
    main()
