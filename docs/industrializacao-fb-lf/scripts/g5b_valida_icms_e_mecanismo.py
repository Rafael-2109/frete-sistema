#!/usr/bin/env python3
"""Valida (READ-ONLY): (a) NFs de industrializacao NAO tem ICMS; (b) ops do 1902/1124/1903 e seu movimento_estoque."""
import sys
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection


def main():
    o = get_odoo_connection(); o.authenticate()

    print("=" * 96)
    print("(a) ICMS nas NFs reais de industrializacao? (remessa 5901, retorno ENTSI, LF saida 5124)")
    print("=" * 96)
    for name in ('RPI/2026/00243', 'ENTSI/2026/05/0127', 'VND/2026/00357'):
        nf = o.search_read('account.move', [('name', '=', name)], ['id', 'amount_tax', 'amount_total', 'amount_untaxed'], limit=1)
        if not nf:
            print(f"  {name}: nao achado"); continue
        nf = nf[0]
        mls = o.search_read('account.move.line', [('move_id', '=', nf['id'])], ['account_id', 'tax_line_id'], limit=80)
        taxes = sorted({ml['tax_line_id'][1] for ml in mls if ml['tax_line_id']})
        icms = [t for t in taxes if 'ICMS' in t.upper()]
        icms_acc = [ml['account_id'][1] for ml in mls if ml['account_id'] and 'ICMS' in ml['account_id'][1].upper()]
        print(f"  {name}: amount_tax={nf['amount_tax']} total={nf['amount_total']} untaxed={nf['amount_untaxed']}")
        print(f"     impostos(tax_line): {taxes or 'NENHUM'}")
        print(f"     >> ICMS? tax={icms or 'NAO'} contas_ICMS={icms_acc or 'NAO'}")

    print("\n" + "=" * 96)
    print("(b) Operacoes das linhas de retorno (o que o G5b vai flipar)")
    print("=" * 96)
    # confirmar a op usada na linha 1902 da ENTSI + seu movimento_estoque
    nf = o.search_read('account.move', [('name', '=', 'ENTSI/2026/05/0127')], ['id'], limit=1)
    if nf:
        mls = o.search_read('account.move.line', [('move_id', '=', nf[0]['id']), ('l10n_br_operacao_id', '!=', False)],
                            ['l10n_br_operacao_id', 'l10n_br_cfop_id'], limit=20)
        seen = set()
        for ml in mls:
            opid = ml['l10n_br_operacao_id'][0]
            if opid in seen: continue
            seen.add(opid)
            op = o.read('l10n_br_ciel_it_account.operacao', [opid],
                        ['name', 'l10n_br_movimento_estoque', 'l10n_br_gera_cpv', 'l10n_br_tipo_pedido_entrada',
                         'l10n_br_cfop_orig_id', 'l10n_br_intra_cfop_id'])[0]
            cfo = op['l10n_br_cfop_orig_id'][1].split(' - ')[0] if op['l10n_br_cfop_orig_id'] else '-'
            cfi = op['l10n_br_intra_cfop_id'][1].split(' - ')[0] if op['l10n_br_intra_cfop_id'] else '-'
            print(f"  op id={opid} '{op['name'].strip()[:44]}'")
            print(f"     cfop_orig={cfo} -> intra={cfi} | movimento_estoque={op['l10n_br_movimento_estoque']} "
                  f"gera_cpv={op['l10n_br_gera_cpv']} tipo_ped_ent={op['l10n_br_tipo_pedido_entrada']}")


if __name__ == '__main__':
    main()
