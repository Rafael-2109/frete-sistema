#!/usr/bin/env python3
"""G5b dive (READ-ONLY): config das operacoes-chave de industrializacao + journal/conta + a operacao da ENTSI quebrada."""
import sys
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

OP = 'l10n_br_ciel_it_account.operacao'
KEY_OPS = [2686, 850, 2711, 849, 2930, 3110, 2552]  # remessa, retorno, retorno-nao-aplicado, 5124, entrada-FB, dev-industr, dev-compra
FIELDS = ['name', 'l10n_br_movimento_estoque', 'l10n_br_gera_cpv', 'l10n_br_tipo_operacao',
          'l10n_br_tipo_pedido', 'l10n_br_tipo_pedido_entrada', 'l10n_br_intra_cfop_id', 'l10n_br_cfop_orig_id']


def cfop(v):
    return v[1] if isinstance(v, list) and v else '-'


def main():
    o = get_odoo_connection(); o.authenticate()

    print("=" * 100)
    print("A — Config das operacoes-chave (movimento_estoque é O LEVER do L5b)")
    print("=" * 100)
    ops = o.read(OP, KEY_OPS, FIELDS)
    for op in sorted(ops, key=lambda x: KEY_OPS.index(x['id']) if x['id'] in KEY_OPS else 99):
        print(f"\n  id={op['id']} | {op['name'].strip()}")
        print(f"     movimenta_estoque={op['l10n_br_movimento_estoque']}  gera_cpv={op['l10n_br_gera_cpv']}  tipo_op={op['l10n_br_tipo_operacao']}")
        print(f"     tipo_pedido(saida)={op['l10n_br_tipo_pedido']}  tipo_pedido_entrada={op['l10n_br_tipo_pedido_entrada']}")
        print(f"     CFOP intra={cfop(op['l10n_br_intra_cfop_id'])}  CFOP orig(DFe)={cfop(op['l10n_br_cfop_orig_id'])}")

    print("\n" + "=" * 100)
    print("B — Operacao usada HOJE na ENTSI (retorno quebrado) — partir de uma NF de entrada LF na FB")
    print("=" * 100)
    nf = o.search_read('account.move', [('company_id', '=', 1), ('partner_id', '=', 35),
                                        ('move_type', '=', 'in_invoice'), ('state', '=', 'posted')],
                       ['id', 'name', 'l10n_br_operacao_id'], limit=3, order='invoice_date desc')
    for n in nf:
        print(f"\n  NF {n['name']} operacao_cabecalho={cfop(n['l10n_br_operacao_id'])}")
        mls = o.search_read('account.move.line', [('move_id', '=', n['id']), ('display_type', '=', 'product')],
                            ['name', 'l10n_br_operacao_id', 'l10n_br_cfop_id', 'account_id'], limit=20)
        if not mls:
            mls = o.search_read('account.move.line', [('move_id', '=', n['id'])],
                                ['name', 'l10n_br_operacao_id', 'l10n_br_cfop_id', 'account_id'], limit=20)
        seen = set()
        for ml in mls:
            opn = cfop(ml.get('l10n_br_operacao_id')); cf = cfop(ml.get('l10n_br_cfop_id'))
            acc = cfop(ml.get('account_id'))
            key = (opn, cf, acc.split(' ')[0] if acc != '-' else acc)
            if key in seen: continue
            seen.add(key)
            print(f"     linha op='{opn}' cfop='{cf}' conta={acc[:34]}")

    print("\n" + "=" * 100)
    print("C — Journals que carregam conta 5101010001 (p/ creditar no retorno = L5a)")
    print("=" * 100)
    acc = o.search_read('account.account', [('code', '=', '5101010001'), ('company_id', '=', 1)], ['id'], limit=1)[0]['id']
    js = o.search_read('account.journal', [('company_id', '=', 1)], ['id', 'name', 'type', 'default_account_id'], limit=200)
    for j in js:
        da = j.get('default_account_id')
        if da and da[0] == acc:
            print(f"  journal id={j['id']} '{j['name']}' type={j['type']} default_account=5101010001")
    # tipo.pedido.diario: mapeia tipo_pedido -> journal
    print("\n  tipo.pedido.diario (tipo_pedido -> journal) p/ FB:")
    try:
        tpd = o.search_read('l10n_br_ciel_it_account.tipo.pedido.diario',
                            [('company_id', '=', 1)], ['l10n_br_tipo_pedido', 'journal_id'], limit=80)
        for t in tpd:
            j = t.get('journal_id')
            if j and ('INDUSTRIALIZ' in j[1].upper() or 'REMESSA' in j[1].upper() or 'RETORNO' in j[1].upper()):
                print(f"     tipo_pedido={t.get('l10n_br_tipo_pedido')} -> journal {j[1]}")
    except Exception as e:
        print(f"     (modelo tipo.pedido.diario: {e})")


if __name__ == '__main__':
    main()
