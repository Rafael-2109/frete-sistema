#!/usr/bin/env python3
"""S33 — READ-only: separar o TOTAL CONTABIL (amount_total, zerado pela baixa no_payment)
do TOTAL FISCAL/SEFAZ (l10n_br_total_nfe = vNF do XML). A SARET real mostrou
amount_total=0 mas l10n_br_total_nfe=105 (autorizada). Confere o par nas nossas NFs.

Util tambem nos GATE 2/3 (SEFAZ/post). READ-ONLY.
Uso: python s33_total_nfe_vs_contabil.py [nf_id ...]   (default: 788504 725475 709632)
"""
import sys
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5], 'company_id': 5, 'lang': 'pt_BR'}
NFS = [int(x) for x in sys.argv[1:]] or [788504, 725475, 709632]


def main():
    o = get_odoo_connection(); assert o.authenticate(), "FALHA AUTH"
    rows = o.execute_kw('account.move', 'read', [NFS],
                        {'fields': ['name', 'state', 'amount_untaxed', 'amount_tax', 'amount_total',
                                    'l10n_br_total_nfe', 'l10n_br_cstat_nf', 'l10n_br_situacao_nf',
                                    'l10n_br_calcular_imposto'], 'context': CTX})
    print(f"{'NF':>8} {'name':18} {'state':8} {'untax':>9} {'tax':>9} {'amt_total':>9} "
          f"{'total_nfe':>9} {'cstat':>6} situacao")
    for r in rows:
        print(f"{r['id']:>8} {str(r.get('name'))[:18]:18} {str(r.get('state')):8} "
              f"{r.get('amount_untaxed'):>9} {r.get('amount_tax'):>9} {r.get('amount_total'):>9} "
              f"{str(r.get('l10n_br_total_nfe')):>9} {str(r.get('l10n_br_cstat_nf') or '-'):>6} "
              f"{r.get('l10n_br_situacao_nf') or '-'}")


if __name__ == '__main__':
    main()
