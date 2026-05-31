#!/usr/bin/env python3
"""Grounding (READ-ONLY) p/ a proposta de operacoes+journals de retorno (G5a+G5b).
1) operacoes candidatas p/ CFOP entrada 1124/1902/1903 (config completa).
2) journals FB purchase + default/no_payment account.
3) como o DFe atribui operacao por linha (cfop_orig De-Para)."""
import sys
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

OP = 'l10n_br_ciel_it_account.operacao'
F = ['id', 'name', 'l10n_br_movimento_estoque', 'l10n_br_gera_cpv', 'l10n_br_tipo_operacao',
     'l10n_br_tipo_pedido', 'l10n_br_tipo_pedido_entrada', 'l10n_br_intra_cfop_id', 'l10n_br_cfop_orig_id']


def cf(v): return v[1].split(' - ')[0] if isinstance(v, list) and v else '-'
def nm(v): return v[1] if isinstance(v, list) and v else '-'


def main():
    o = get_odoo_connection(); o.authenticate()

    print("=" * 100)
    print("1 — Operacoes de ENTRADA cujo CFOP intra ∈ {1124,1902,1903} (candidatas p/ o retorno na FB)")
    print("=" * 100)
    allops = o.search_read(OP, [('l10n_br_intra_cfop_id', '!=', False), ('l10n_br_tipo_operacao', '=', 'entrada')], F, limit=2000)
    ops = [op for op in allops if cf(op['l10n_br_intra_cfop_id']) in ('1124', '1902', '1903')]
    for op in sorted(ops, key=lambda x: cf(x['l10n_br_intra_cfop_id'])):
        print(f"  id={op['id']:<5} cfop={cf(op['l10n_br_intra_cfop_id']):5} estoque={str(op['l10n_br_movimento_estoque']):5} "
              f"cpv={str(op['l10n_br_gera_cpv']):5} tipo_ped_ent={str(op['l10n_br_tipo_pedido_entrada']):22} | {op['name'].strip()[:46]}")

    print("\n" + "=" * 100)
    print("2 — Journals FB (purchase) + contas (default / account_no_payment_id) — onde rotear p/ 5101010001")
    print("=" * 100)
    for code in ('5101010001', '5101020001', '5101020002', '5101010002'):
        a = o.search_read('account.account', [('code', '=', code), ('company_id', '=', 1)], ['id', 'name'], limit=1)
        print(f"  conta {code} (FB) id={a[0]['id'] if a else '?'} {a[0]['name'] if a else ''}")
    fg = o.execute_kw('account.journal', 'fields_get', [], {'attributes': ['type']})
    npf = 'account_no_payment_id' if 'account_no_payment_id' in fg else None
    flds = ['id', 'name', 'type', 'default_account_id'] + ([npf] if npf else [])
    js = o.search_read('account.journal', [('company_id', '=', 1), ('type', '=', 'purchase')], flds, limit=200)
    print(f"\n  {len(js)} journals purchase FB (mostrando os de industrializacao/remessa/retorno/servico):")
    for j in sorted(js, key=lambda x: x['name']):
        if any(k in j['name'].upper() for k in ('INDUSTRIALIZ', 'REMESSA', 'RETORNO', 'SERVIÇO', 'SERVICO', 'TERCEIR')):
            da = cf(j.get('default_account_id')); np = cf(j.get(npf)) if npf else '-'
            print(f"    j{j['id']:<5} default={da:12} no_payment={np:12} | {j['name']}")

    print("\n" + "=" * 100)
    print("3 — Atribuicao de operacao por linha: cfop_orig_id (De-Para DFe CFOP->operacao)")
    print("=" * 100)
    # operacoes com cfop_orig setado (entrada) - como o DFe mapeia
    with_orig = o.search_read(OP, [('l10n_br_cfop_orig_id', '!=', False), ('l10n_br_tipo_operacao', '=', 'entrada')],
                              ['id', 'name', 'l10n_br_cfop_orig_id', 'l10n_br_intra_cfop_id', 'l10n_br_movimento_estoque'], limit=15)
    print(f"  operacoes entrada com cfop_orig setado: {o.search_count(OP, [('l10n_br_cfop_orig_id','!=',False),('l10n_br_tipo_operacao','=','entrada')])} (amostra):")
    for op in with_orig[:12]:
        print(f"    id={op['id']:<5} cfop_orig={cf(op['l10n_br_cfop_orig_id']):5} -> intra={cf(op['l10n_br_intra_cfop_id']):5} estoque={op['l10n_br_movimento_estoque']} | {op['name'].strip()[:40]}")
    # existe modelo de De-Para dedicado?
    print("\n  modelos De-Para candidatos:")
    for m in ('l10n_br_ciel_it_account.cfop.operacao', 'l10n_br_ciel_it_account.operacao.cfop',
              'l10n_br_ciel_it_account.de.para.operacao', 'l10n_br_ciel_it_account.dfe.operacao'):
        try:
            n = o.search_count(m, [])
            print(f"    {m}: EXISTE ({n} registros)")
        except Exception:
            pass


if __name__ == '__main__':
    main()
