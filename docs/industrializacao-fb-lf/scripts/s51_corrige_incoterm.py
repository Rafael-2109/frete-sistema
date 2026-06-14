#!/usr/bin/env python3
"""S51 — CORRECAO DE CADASTRO pre-transmissao: seta invoice_incoterm_id = [4] FOB nas 2 NFs
do piloto. O preview do XML abortou ("Modalidade de frete nao configurada") porque a NF-1
saiu SEM incoterm (create_invoice do picking nao seta) e a NF-2 pegou CIF (id 6) por default.

As 3 NFs REAIS de retorno de industrializacao (709632/708286/574827) + as VND recentes do
j847 usam TODAS [4] FOB (s50). Espelhar a referencia (regra: NF sai igual a' autorizada).

REVERSIVEL: incoterm e' campo nao-contabil (nao afeta linhas/baixa). write check_move_validity=False.

MODOS:
  (sem flag)   READ: incoterm atual das 2 + alvo
  --executar   seta invoice_incoterm_id=FOB(4) nas 2 NFs
"""
import sys
import argparse
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5], 'company_id': 5, 'lang': 'pt_BR'}
INCOTERM_FOB = 4   # [FOB] FOB — igual as NFs reais de retorno (s50)


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

    F = ['name', 'state', 'invoice_incoterm_id']
    print("=" * 80)
    print(f"S51 — incoterm FOB({INCOTERM_FOB}) nas 2 NFs (espelha NFs reais de retorno)")
    print("=" * 80)
    for r in rd(nfs, F):
        print(f"  NF {r['id']} {r['name']}: state={r['state']} incoterm={r.get('invoice_incoterm_id') or 'VAZIO ❌'}")

    if not args.executar:
        print(f"\n  [DRY-RUN] alvo: invoice_incoterm_id={INCOTERM_FOB} (FOB) nas 2. --executar")
        return

    for nf in nfs:
        o.execute_kw('account.move', 'write', [[nf], {'invoice_incoterm_id': INCOTERM_FOB}],
                     {'context': dict(CTX, check_move_validity=False)})
    print(f"\n  [escrita] invoice_incoterm_id={INCOTERM_FOB} aplicado nas 2 NFs. DEPOIS:")
    for r in rd(nfs, F):
        print(f"  NF {r['id']} {r['name']}: incoterm={r.get('invoice_incoterm_id')}")
    print(f"\n  >>> re-testar preview via SA: python docs/industrializacao-fb-lf/scripts/s49_preview_xml_via_sa.py --executar")


if __name__ == '__main__':
    main()
