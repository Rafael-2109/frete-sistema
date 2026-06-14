#!/usr/bin/env python3
"""S28 — diagnostico READ-only: confirmar a RECEITA p/ montar a NF-insumos SEM imposto.

Hipotese (do s27): a NF real de retorno tem HEADER l10n_br_calcular_imposto=False e
linhas com tax_ids=[]; cfop/CST/conta vem da OPERACAO da linha (2864), nao do calculo
de imposto. Logo, montar com calcular_imposto=False deriva a estrutura fiscal sem gerar
valores de tributo espurios.

Verifica:
  1. ir.model.fields dos campos fiscais da LINHA (cfop/cst/conta): compute? related? store?
     -> se sao compute(store) dependentes da operacao, vem SEM precisar do calculo de imposto.
  2. NF de retorno SEPARADA real (SARET) — o modelo mais fiel do nosso alvo (NF so-insumos):
     header calcular_imposto + amounts; linhas op/cfop/cst/tax_ids/valores.
     Descobre uma SARET real automaticamente (journal sale LF, so linhas 5902/dev-ind).
  3. A operacao 2864: tem o campo que controla calculo de imposto? (p/ entender o gatilho)

READ-ONLY. Zero escrita.
"""
import sys
from collections import Counter
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5], 'company_id': 5, 'lang': 'pt_BR'}
OP_5902 = 2864
SARET_CANDIDATA = 725475   # citada no s25 como SARET separada real


def m2o(v):
    return f"{v[0]}|{str(v[1])[:34]}" if isinstance(v, list) and v else ('-' if not v else str(v))


def main():
    o = get_odoo_connection(); assert o.authenticate(), "FALHA AUTH"

    def rr(model, dom, fields, **kw):
        kw2 = {'fields': fields, 'context': CTX}; kw2.update(kw)
        return o.execute_kw(model, 'search_read', [dom], kw2)

    # ---- 1. natureza dos campos fiscais da linha ----
    print("=" * 92)
    print("### 1. ir.model.fields — cfop/cst/conta da linha sao compute/store? (vem da operacao?)")
    alvo = ['l10n_br_cfop_id', 'l10n_br_cfop_codigo', 'l10n_br_icms_cst', 'l10n_br_pis_cst',
            'l10n_br_cofins_cst', 'account_id', 'l10n_br_operacao_id', 'l10n_br_operacao_manual']
    flds = rr('ir.model.fields', [('model', '=', 'account.move.line'), ('name', 'in', alvo)],
              ['name', 'compute', 'related', 'store', 'depends', 'readonly'])
    for f in sorted(flds, key=lambda x: x['name']):
        comp = 'COMPUTE' if f.get('compute') else ('RELATED' if f.get('related') else 'plain')
        print(f"   {f['name']:30} {comp:8} store={f.get('store')} ro={f.get('readonly')} "
              f"depends={(f.get('depends') or '')[:48]}")

    # ---- 2. achar e diagnosticar uma SARET separada real ----
    print("\n" + "=" * 92)
    print("### 2. NF de retorno SEPARADA real (so-insumos) — header + linhas")
    nf = SARET_CANDIDATA
    h = rr('account.move', [('id', '=', nf)],
           ['name', 'state', 'move_type', 'amount_untaxed', 'amount_tax', 'amount_total',
            'l10n_br_calcular_imposto', 'journal_id', 'l10n_br_tipo_pedido', 'l10n_br_operacao_id'])
    if not h:
        print(f"   {nf} nao existe; buscando uma VND LF so-5902/dev-industrializacao...")
        cand = rr('account.move', [('move_type', '=', 'out_invoice'), ('company_id', '=', 5),
                                   ('state', '=', 'posted'), ('l10n_br_tipo_pedido', '=', 'dev-industrializacao')],
                  ['id', 'name'], order='id desc', limit=1)
        if cand:
            nf = cand[0]['id']
            h = rr('account.move', [('id', '=', nf)],
                   ['name', 'state', 'move_type', 'amount_untaxed', 'amount_tax', 'amount_total',
                    'l10n_br_calcular_imposto', 'journal_id', 'l10n_br_tipo_pedido', 'l10n_br_operacao_id'])
    if h:
        print(f"   NF {nf} = {h[0].get('name')}")
        for k in ['state', 'move_type', 'amount_untaxed', 'amount_tax', 'amount_total',
                  'l10n_br_calcular_imposto', 'journal_id', 'l10n_br_tipo_pedido', 'l10n_br_operacao_id']:
            v = h[0].get(k)
            print(f"      {k:26} = {m2o(v) if isinstance(v, list) else v}")
        lns = rr('account.move.line', [('move_id', '=', nf), ('display_type', '=', 'product')],
                 ['product_id', 'l10n_br_operacao_id', 'l10n_br_cfop_codigo', 'l10n_br_icms_cst',
                  'tax_ids', 'price_subtotal', 'price_total', 'l10n_br_icms_valor', 'account_id'], order='id')
        print(f"      --- {len(lns)} linhas-produto ---")
        cfops = Counter(str(l.get('l10n_br_cfop_codigo')) for l in lns)
        ops = Counter(m2o(l.get('l10n_br_operacao_id')) for l in lns)
        taxn = Counter('vazio' if not l.get('tax_ids') else 'TEM' for l in lns)
        contas = Counter(m2o(l.get('account_id')) for l in lns)
        print(f"      cfops={dict(cfops)}  operacoes={dict(ops)}")
        print(f"      tax_ids={dict(taxn)}  contas={dict(contas)}")
        for l in lns[:2]:
            print(f"      ex: {m2o(l.get('product_id'))[:36]} subtotal={l.get('price_subtotal')} "
                  f"total={l.get('price_total')} icms_valor={l.get('l10n_br_icms_valor')} tax_ids={l.get('tax_ids')}")

    # ---- 3. operacao 2864: campo que controla calculo de imposto ----
    print("\n" + "=" * 92)
    print(f"### 3. operacao {OP_5902} — campos calcular/imposto (gatilho)")
    ofg = o.execute_kw('l10n_br_ciel_it_account.operacao', 'fields_get', [],
                       {'attributes': ['string', 'type'], 'context': CTX})
    ocalc = sorted([f for f in ofg if 'calcular' in f.lower() or 'imposto' in f.lower()])
    if ocalc:
        op = rr('l10n_br_ciel_it_account.operacao', [('id', '=', OP_5902)], ocalc)
        if op:
            for f in ocalc:
                print(f"   {f:34} = {op[0].get(f)}")
    else:
        print("   (operacao nao tem campo calcular/imposto)")


if __name__ == '__main__':
    main()
