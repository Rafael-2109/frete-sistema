#!/usr/bin/env python3
"""S29 — READ-only: entender o MECANISMO do 'amount_total=0' no retorno de insumos.

Contradicao do s28: a NF MISTA real (709632) tem as 5902 com subtotal=total (valor
cheio, amount_tax da NF e' so do servico 5124); a SARET separada real (725475) tem
amount_total=0 / amount_tax=-105. Qual e' o alvo da NF-2 isolada (que precisa BAIXAR
a PASSIVA 5101020001 com VALOR CHEIO)?

Para decidir, abre TODAS as linhas (inclusive display_type='tax'/'line_section') das 2
NFs reais + a SARET, mostrando como o total fecha:
  - 709632 (mista): linhas 5124 + 5902 + tax/contrapartida
  - 725475 (SARET separada op 2710 cfop 5949): de onde vem o -105 que zera
  - l10n_br_calcular_imposto no HEADER e na LINHA das 5902

READ-ONLY.
"""
import sys
from collections import Counter
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5], 'company_id': 5, 'lang': 'pt_BR'}
NFS = {'MISTA-709632 (op2864/cfop5902)': 709632, 'SARET-725475 (op2710/cfop5949)': 725475}


def m2o(v):
    return f"{v[0]}|{str(v[1])[:24]}" if isinstance(v, list) and v else ('-' if not v else str(v))


def main():
    o = get_odoo_connection(); assert o.authenticate(), "FALHA AUTH"

    def rr(model, dom, fields, **kw):
        kw2 = {'fields': fields, 'context': CTX}; kw2.update(kw)
        return o.execute_kw(model, 'search_read', [dom], kw2)

    for label, nf in NFS.items():
        print("=" * 96)
        print(f"### {label}")
        h = rr('account.move', [('id', '=', nf)],
               ['name', 'amount_untaxed', 'amount_tax', 'amount_total', 'l10n_br_calcular_imposto'])
        if not h:
            print("   NF inexistente"); continue
        h = h[0]
        print(f"   {h['name']}  untax={h['amount_untaxed']} tax={h['amount_tax']} total={h['amount_total']} "
              f"calcular_imposto(header)={h['l10n_br_calcular_imposto']}")
        # TODAS as linhas (sem filtro de display_type)
        lns = rr('account.move.line', [('move_id', '=', nf)],
                 ['display_type', 'name', 'product_id', 'l10n_br_cfop_codigo', 'l10n_br_icms_cst',
                  'account_id', 'debit', 'credit', 'balance', 'price_subtotal', 'price_total',
                  'tax_ids', 'tax_line_id', 'l10n_br_calcular_imposto'], order='id')
        dts = Counter(l.get('display_type') or 'NULL' for l in lns)
        print(f"   {len(lns)} linhas no total | display_types={dict(dts)}")
        for l in lns:
            dt = l.get('display_type') or 'lancto'
            prod = m2o(l.get('product_id'))[:30] if l.get('product_id') else (l.get('name') or '')[:30]
            taxln = m2o(l.get('tax_line_id'))[:20] if l.get('tax_line_id') else '-'
            print(f"     [{dt:8}] {prod:30} conta={m2o(l.get('account_id'))[:22]:22} "
                  f"D={l.get('debit')} C={l.get('credit')} "
                  f"cfop={l.get('l10n_br_cfop_codigo')} cst={l.get('l10n_br_icms_cst')} "
                  f"tax_ids={'X' if l.get('tax_ids') else '-'} tax_line={taxln} "
                  f"calc_imp={l.get('l10n_br_calcular_imposto')}")


if __name__ == '__main__':
    main()
