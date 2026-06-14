#!/usr/bin/env python3
"""S38 — READ-only: validar as 2 NFs geradas pela SA da Task #4 (s37) + o vinculo R3.
Default NF1=789484 (servico) NF2=789485 (insumos). Confere:
  - NF-1: 1x5124, journal VND/j847, op 2702/CST 51, invoice_origin, referencia_ids->chave remessa
  - NF-2: 16x5902, RETIND 1083, CST 50, conta 1150100012, tributo 0, vNF cheio, mesmo invoice_origin + refNFe
  - R3: invoice_origin IGUAL nas 2 + referencia_ids apontando a MESMA chave (a da remessa RPI)
  - vinculo picking->NF-1 (por que invoice_ids veio vazio? checa reversed/ref/origin)
Uso: python s38_validar_2nf_r3.py [NF1 NF2]
"""
import sys
from collections import Counter
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5], 'company_id': 5, 'lang': 'pt_BR'}
NF1 = int(sys.argv[1]) if len(sys.argv) > 1 else 789484
NF2 = int(sys.argv[2]) if len(sys.argv) > 2 else 789485
REMESSA = 735679
REF_MODEL = 'l10n_br_ciel_it_account.account.move.referencia'


def m2o(v):
    return f"{v[0]}|{str(v[1])[:28]}" if isinstance(v, list) and v else ('-' if not v else str(v))


def main():
    o = get_odoo_connection(); assert o.authenticate(), "FALHA AUTH"

    def rr(model, dom, fields, **kw):
        kw2 = {'fields': fields, 'context': CTX}; kw2.update(kw)
        return o.execute_kw(model, 'search_read', [dom], kw2)

    chave_rem = rr('account.move', [('id', '=', REMESSA)], ['l10n_br_chave_nf'])[0].get('l10n_br_chave_nf')
    origins = {}
    refs = {}
    for label, nf in [('NF-1 SERVICO', NF1), ('NF-2 INSUMOS', NF2)]:
        h = rr('account.move', [('id', '=', nf)],
               ['name', 'state', 'journal_id', 'move_type', 'partner_id', 'amount_untaxed',
                'amount_total', 'l10n_br_total_nfe', 'invoice_origin', 'referencia_ids',
                'l10n_br_tipo_pedido', 'l10n_br_operacao_id'])
        if not h:
            print(f"### {label} {nf}: INEXISTENTE"); continue
        h = h[0]
        print("=" * 92)
        print(f"### {label} = {h['name']} (id {nf}) state={h['state']} journal={m2o(h['journal_id'])}")
        print(f"    partner={m2o(h.get('partner_id'))} untax={h['amount_untaxed']} total_contabil={h['amount_total']} "
              f"vNF={h.get('l10n_br_total_nfe')}")
        print(f"    tipo_pedido={h.get('l10n_br_tipo_pedido')} op_header={m2o(h.get('l10n_br_operacao_id'))}")
        print(f"    invoice_origin={h.get('invoice_origin')!r}")
        origins[label] = h.get('invoice_origin')
        nl = rr('account.move.line', [('move_id', '=', nf), ('display_type', '=', 'product')],
                ['l10n_br_cfop_codigo', 'l10n_br_icms_cst', 'account_id'])
        print(f"    {len(nl)} linhas | CFOP={dict(Counter(str(x.get('l10n_br_cfop_codigo')) for x in nl))} "
              f"CST={dict(Counter(str(x.get('l10n_br_icms_cst')) for x in nl))} "
              f"contas={sorted(set(m2o(x.get('account_id')).split('|')[-1] for x in nl))}")
        # refNFe
        if h.get('referencia_ids'):
            rfs = rr(REF_MODEL, [('id', 'in', h['referencia_ids'])], ['l10n_br_chave_nf'])
            chs = [r.get('l10n_br_chave_nf') for r in rfs]
            refs[label] = chs
            print(f"    referencia_ids ({len(rfs)}): {chs}")
            print(f"      -> aponta a chave da remessa? {'✅' if chave_rem in chs else '❌'}")

    print("\n" + "=" * 92)
    print("### R3 — VINCULO entre as 2 NFs")
    o1, o2 = origins.get('NF-1 SERVICO'), origins.get('NF-2 INSUMOS')
    print(f"    invoice_origin igual: {'✅' if o1 and o1 == o2 else '❌'} ({o1!r} == {o2!r})")
    r1 = refs.get('NF-1 SERVICO', []); r2 = refs.get('NF-2 INSUMOS', [])
    print(f"    referencia_ids -> mesma chave (remessa): "
          f"{'✅' if chave_rem in r1 and chave_rem in r2 else '❌'} (chave_remessa={chave_rem})")

    # como o picking 325344 se relaciona com a NF-1
    print("\n### vinculo picking 325344 -> NF-1")
    pf = o.execute_kw('stock.picking', 'fields_get', [], {'attributes': [], 'context': CTX})
    fl = [x for x in ['invoice_ids', 'invoice_id', 'sale_id'] if x in pf]
    p = rr('stock.picking', [('id', '=', 325344)], ['name', 'origin'] + fl)
    if p:
        print(f"    picking {p[0]['name']} origin={p[0].get('origin')} " +
              " ".join(f"{x}={p[0].get(x)}" for x in fl))


if __name__ == '__main__':
    main()
