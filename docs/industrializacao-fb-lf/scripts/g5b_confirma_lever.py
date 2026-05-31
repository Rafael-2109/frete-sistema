#!/usr/bin/env python3
"""G5b confirma (READ-ONLY): (a) operacoes movimento_estoque=False existem? (b) conta 5101010001 nos journals; (c) op entrada 1902 full."""
import sys
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

OP = 'l10n_br_ciel_it_account.operacao'


def main():
    o = get_odoo_connection(); o.authenticate()

    print("=" * 100)
    print("A — Operacoes com movimento_estoque=False (prova que o flag é usado p/ simbolicas)")
    print("=" * 100)
    n_false = o.search_count(OP, [('l10n_br_movimento_estoque', '=', False)])
    n_true = o.search_count(OP, [('l10n_br_movimento_estoque', '=', True)])
    print(f"  movimento_estoque=False: {n_false} operacoes  |  =True: {n_true}")
    sample = o.search_read(OP, [('l10n_br_movimento_estoque', '=', False)],
                           ['id', 'name', 'l10n_br_tipo_operacao', 'l10n_br_intra_cfop_id'], limit=20)
    print("  amostra (False):")
    for s in sample:
        cf = s['l10n_br_intra_cfop_id'][1].split(' - ')[0] if s['l10n_br_intra_cfop_id'] else '-'
        print(f"    id={s['id']:<5} estoque=NAO tipo={s['l10n_br_tipo_operacao']:8} cfop={cf:6} {s['name'].strip()[:50]}")

    print("\n" + "=" * 100)
    print("B — Onde a conta 5101010001 (FB) mora nos journals de industrializacao")
    print("=" * 100)
    acc5101 = o.search_read('account.account', [('code', '=', '5101010001'), ('company_id', '=', 1)], ['id'], limit=1)[0]['id']
    jnames = ['REMESSA PARA INDUSTRIALIZAÇÃO', 'ENTRADA - RETORNO NAO APLICADO',
              'ENTRADA - SERVIÇO DE INDUSTRIALIZAÇÃO', 'SAÍDA - PERDAS', 'SAÍDA - PRODUTO INDUSTRIALIZADO',
              'ENTRADA - REMESSA PARA INDUSTRIALIZAÇÃO']
    for jn in jnames:
        j = o.search_read('account.journal', [('company_id', '=', 1), ('name', '=', jn)],
                          ['id', 'type', 'default_account_id'], limit=1)
        if not j:
            print(f"  '{jn}': nao encontrado"); continue
        j = j[0]
        extra_fields = []
        fg = o.execute_kw('account.journal', 'fields_get', [], {'attributes': ['type']})
        for cand in ('account_no_payment_id', 'l10n_br_account_no_payment_id', 'l10n_br_account_id'):
            if cand in fg:
                extra_fields.append(cand)
        vals = o.read('account.journal', [j['id']], ['default_account_id'] + extra_fields)[0]
        da = vals.get('default_account_id')
        line = f"  j{j['id']:<4} {jn[:42]:42s} type={j['type']:8} default={da[1].split(' ')[0] if da else '-'}"
        for ef in extra_fields:
            v = vals.get(ef)
            mark = ' <==5101010001' if v and v[0] == acc5101 else ''
            line += f"  {ef}={v[1].split(' ')[0] if v else '-'}{mark}"
        if da and da[0] == acc5101:
            line += '  <== default=5101010001'
        print(line)

    print("\n" + "=" * 100)
    print("C — Operacao de ENTRADA 1902 (a usada na ENTSI) — config completa relevante")
    print("=" * 100)
    op1902 = o.search_read(OP, [('name', 'ilike', 'Retorno de mercadoria remetida')],
                           ['id', 'name', 'l10n_br_movimento_estoque', 'l10n_br_gera_cpv',
                            'l10n_br_tipo_operacao', 'l10n_br_tipo_pedido_entrada', 'l10n_br_intra_cfop_id'], limit=5)
    for op in op1902:
        cf = op['l10n_br_intra_cfop_id'][1].split(' - ')[0] if op['l10n_br_intra_cfop_id'] else '-'
        print(f"  id={op['id']} {op['name'].strip()}")
        print(f"     movimenta_estoque={op['l10n_br_movimento_estoque']} cfop={cf} tipo_op={op['l10n_br_tipo_operacao']} tipo_ped_entrada={op['l10n_br_tipo_pedido_entrada']}")


if __name__ == '__main__':
    main()
