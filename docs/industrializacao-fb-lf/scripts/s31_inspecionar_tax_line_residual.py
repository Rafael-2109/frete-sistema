#!/usr/bin/env python3
"""S31 — READ-only: inspecionar a tax line RESIDUAL de -278,17 da NF 788504 (s30).

O s30 limpou tax_ids das product lines (tax_ids_total=0) e removeu a tax line, mas ela
FOI RECRIADA (tax_lines=1, tax=-278,17, total=0). Logo a tax line de compensacao NAO
depende dos tax_ids — vem da logica fiscal CIEL IT (operacao/fp). Este script revela:
  - todas as linhas da 788504 (foco na tax line): name, conta, D/C, tax_line_id, base
  - o account.tax por tras (se houver): nome, amount, type, conta de reparticao
  - compara com a tax line da SARET 725475 (mesmo mecanismo de 'total 0')
para decidir COMO impedir/remover a compensacao de forma estavel.

READ-ONLY. Default NF=788504 (passar outro id como argv[1]).
"""
import sys
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5], 'company_id': 5, 'lang': 'pt_BR'}
NF = int(sys.argv[1]) if len(sys.argv) > 1 else 788504


def m2o(v):
    return f"{v[0]}|{str(v[1])[:30]}" if isinstance(v, list) and v else ('-' if not v else str(v))


def main():
    o = get_odoo_connection(); assert o.authenticate(), "FALHA AUTH"

    def rr(model, dom, fields, **kw):
        kw2 = {'fields': fields, 'context': CTX}; kw2.update(kw)
        return o.execute_kw(model, 'search_read', [dom], kw2)

    h = rr('account.move', [('id', '=', NF)],
           ['name', 'state', 'amount_untaxed', 'amount_tax', 'amount_total',
            'l10n_br_calcular_imposto', 'journal_id', 'l10n_br_operacao_id', 'fiscal_position_id'])
    if not h:
        print(f"NF {NF} nao existe."); return
    h = h[0]
    print("=" * 92)
    print(f"### NF {NF} = {h['name']} state={h['state']} | untax={h['amount_untaxed']} "
          f"tax={h['amount_tax']} total={h['amount_total']} calc_imp={h['l10n_br_calcular_imposto']}")
    print(f"    journal={m2o(h['journal_id'])} op={m2o(h['l10n_br_operacao_id'])} fp={m2o(h['fiscal_position_id'])}")

    print("\n### TAX LINES (display_type='tax')")
    tls = rr('account.move.line', [('move_id', '=', NF), ('display_type', '=', 'tax')],
             ['name', 'account_id', 'debit', 'credit', 'balance', 'tax_line_id', 'tax_base_amount',
              'tax_repartition_line_id', 'l10n_br_cfop_codigo'])
    if not tls:
        print("   (nenhuma)")
    tax_ids_back = set()
    for l in tls:
        print(f"   name={l.get('name')!r} conta={m2o(l.get('account_id'))} D={l.get('debit')} "
              f"C={l.get('credit')} base={l.get('tax_base_amount')}")
        print(f"      tax_line_id={m2o(l.get('tax_line_id'))} repart={m2o(l.get('tax_repartition_line_id'))}")
        if l.get('tax_line_id'):
            tax_ids_back.add(l['tax_line_id'][0])

    # o account.tax por tras
    if tax_ids_back:
        print("\n### account.tax por tras da tax line")
        taxes = rr('account.tax', [('id', 'in', list(tax_ids_back))],
                   ['id', 'name', 'amount', 'amount_type', 'price_include', 'l10n_br_cst',
                    'tax_group_id', 'l10n_br_domain'])
        for t in taxes:
            print(f"   {t['id']}: {t.get('name')!r} amount={t.get('amount')} type={t.get('amount_type')} "
                  f"price_include={t.get('price_include')} cst={t.get('l10n_br_cst')} "
                  f"group={m2o(t.get('tax_group_id'))} domain={t.get('l10n_br_domain')}")
            # repartition lines (p/ ver a conta de compensacao)
            reps = rr('account.tax.repartition.line', [('tax_id', '=', t['id'])],
                      ['repartition_type', 'factor_percent', 'account_id', 'document_type'])
            for r in reps:
                print(f"      repart {r.get('document_type')}/{r.get('repartition_type')} "
                      f"{r.get('factor_percent')}% -> conta={m2o(r.get('account_id'))}")

    # de onde a product line puxa esse imposto? checar tax_ids ANTES de limpar nao da' mais;
    # mas posso ver se a OPERACAO 2864 referencia algum imposto
    print("\n### a operacao 2864 referencia impostos? (campos *_tax*/imposto com valor)")
    ofg = o.execute_kw('l10n_br_ciel_it_account.operacao', 'fields_get', [],
                       {'attributes': ['type', 'relation'], 'context': CTX})
    tax_fields = [f for f, m in ofg.items()
                  if m.get('relation') == 'account.tax' or
                  (m.get('type') in ('many2one', 'many2many') and 'tax' in f.lower())]
    if tax_fields:
        op = rr('l10n_br_ciel_it_account.operacao', [('id', '=', 2864)], tax_fields)
        if op:
            for f in tax_fields:
                v = op[0].get(f)
                if v:
                    print(f"   {f} = {v}")
    else:
        print("   (operacao nao tem campo m2o/m2m p/ account.tax)")

    # comparar com a tax line da SARET 725475 (mesmo mecanismo total=0)
    print("\n### comparacao: tax line da SARET 725475 (op 2710, total=0)")
    s = rr('account.move.line', [('move_id', '=', 725475), ('display_type', '=', 'tax')],
           ['name', 'account_id', 'debit', 'credit', 'tax_line_id', 'tax_base_amount'])
    for l in s:
        print(f"   name={l.get('name')!r} conta={m2o(l.get('account_id'))} D={l.get('debit')} "
              f"C={l.get('credit')} tax_line_id={m2o(l.get('tax_line_id'))} base={l.get('tax_base_amount')}")


if __name__ == '__main__':
    main()
