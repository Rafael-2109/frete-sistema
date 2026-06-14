#!/usr/bin/env python3
"""S27 — diagnostico READ-only: por que o recompute (s24) gera imposto ESPURIO
nas 5902 (amount_tax=-278,17) se a NF de retorno REAL nao tem tributo?

Regra (Rafael 2026-06-13): o retorno 5902 NAO tem ICMS/PIS/COFINS -> tax_ids=[] /
amount_tax=0. A NF real (709632) sai assim; o nosso onchange_l10n_br_calcular_imposto
inventa tributo. Este script acha a FONTE do imposto e COMO a NF real evita:

  1. campos de imposto disponiveis na account.move.line (descoberta dinamica)
  2. HEADER da NF real 709632: amount_*, l10n_br_calcular_imposto
  3. linhas 5902 da NF real: tax_ids + campos de imposto + valores
  4. operacao 2864 (modelo via relation) — tem config de impostos? calcular_imposto?
  5. impostos DEFAULT de produtos de terceiros (taxes_id) — a fonte provavel do espurio

READ-ONLY. Zero escrita.
"""
import sys
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5], 'company_id': 5, 'lang': 'pt_BR'}
NF_REAL = 709632          # VND real do shoyu: 1x5124 + 16x5902, sem tributo
OP_5902 = 2864            # operacao da linha 5902
CODS_TERCEIROS = ['210030010', '104000002', '105000022']   # amostra (s26)


def m2o(v):
    return f"{v[0]}|{str(v[1])[:34]}" if isinstance(v, list) and v else ('-' if not v else str(v))


def main():
    o = get_odoo_connection(); assert o.authenticate(), "FALHA AUTH"

    def rr(model, dom, fields, **kw):
        kw2 = {'fields': fields, 'context': CTX}; kw2.update(kw)
        return o.execute_kw(model, 'search_read', [dom], kw2)

    def fields_of(model, needles):
        fg = o.execute_kw(model, 'fields_get', [], {'attributes': ['string', 'type', 'relation'], 'context': CTX})
        hits = {f: meta for f, meta in fg.items()
                if any(n in f.lower() for n in needles)}
        return fg, hits

    # ---- 1. campos de imposto na linha ----
    print("=" * 92)
    print("### 1. CAMPOS de imposto em account.move.line (descoberta dinamica)")
    lfg, limp = fields_of('account.move.line', ['icms', 'pis', 'cofins', 'ipi', 'imposto', 'tax', 'calcular'])
    # so os relevantes p/ valor/cst/calcular (evita poluir)
    rel = {f: m for f, m in limp.items()
           if any(k in f.lower() for k in ['_cst', '_valor', '_aliquota', 'tax_ids', 'calcular_imposto', '_base'])}
    for f in sorted(rel):
        print(f"   {f:42} {rel[f].get('type'):10} {rel[f].get('string','')[:30]}")

    line_imp_fields = sorted([f for f in rel if rel[f].get('type') != 'one2many' or f == 'tax_ids'])
    # incluir tax_ids sempre
    if 'tax_ids' not in line_imp_fields:
        line_imp_fields.append('tax_ids')

    # ---- 2. HEADER da NF real ----
    print("\n" + "=" * 92)
    print(f"### 2. HEADER NF real {NF_REAL}")
    hfg, _ = fields_of('account.move', [])
    hwant = [f for f in ['name', 'state', 'amount_untaxed', 'amount_tax', 'amount_total',
                         'l10n_br_calcular_imposto', 'journal_id', 'l10n_br_tipo_pedido',
                         'l10n_br_operacao_id', 'fiscal_position_id'] if f in hfg]
    h = rr('account.move', [('id', '=', NF_REAL)], hwant)
    if not h:
        print(f"   NF {NF_REAL} nao existe.");
    else:
        for k in hwant:
            print(f"   {k:28} = {m2o(h[0].get(k)) if isinstance(h[0].get(k), list) else h[0].get(k)}")

    # ---- 3. linhas 5902 da NF real ----
    print("\n" + "=" * 92)
    print(f"### 3. LINHAS 5902 da NF real {NF_REAL} (tax_ids + impostos + valores)")
    base = ['product_id', 'l10n_br_cfop_codigo', 'l10n_br_icms_cst', 'quantity',
            'price_unit', 'price_subtotal', 'price_total', 'account_id', 'tax_ids']
    base = [f for f in base if f in lfg]
    extra = [f for f in line_imp_fields if f not in base and f in lfg]
    lwant = base + extra
    lns = rr('account.move.line', [('move_id', '=', NF_REAL), ('display_type', '=', 'product'),
                                   ('l10n_br_cfop_codigo', '=', '5902')], lwant, order='id', limit=3)
    print(f"   (amostra de {len(lns)} linhas; foco em tax_ids/valores)")
    for ln in lns:
        print(f"   --- {m2o(ln.get('product_id'))[:40]} ---")
        print(f"       qty={ln.get('quantity')} price_unit={ln.get('price_unit')} "
              f"subtotal={ln.get('price_subtotal')} total={ln.get('price_total')}")
        print(f"       tax_ids={ln.get('tax_ids')}  cfop={ln.get('l10n_br_cfop_codigo')} cst={ln.get('l10n_br_icms_cst')}")
        nz = {f: ln.get(f) for f in extra if ln.get(f) not in (False, None, 0, 0.0, [], '')}
        if nz:
            print(f"       imposto!=0: {nz}")
        else:
            print(f"       imposto: TODOS zerados/vazios")

    # ---- 4. operacao 2864 ----
    print("\n" + "=" * 92)
    print(f"### 4. OPERACAO {OP_5902} (config fiscal/impostos)")
    op_rel = lfg.get('l10n_br_operacao_id', {}).get('relation')
    print(f"   modelo da operacao = {op_rel}")
    if op_rel:
        ofg, oimp = fields_of(op_rel, ['icms', 'pis', 'cofins', 'ipi', 'imposto', 'tax', 'calcular', 'cst', 'cfop'])
        owant = [f for f in oimp if ofg[f].get('type') not in ('one2many',)] + \
                [f for f in oimp if ofg[f].get('type') == 'one2many']
        owant = ['name'] + sorted(set(owant))
        owant = [f for f in owant if f in ofg]
        op = rr(op_rel, [('id', '=', OP_5902)], owant)
        if op:
            for k in owant:
                v = op[0].get(k)
                if v not in (False, None, '', [], 0, 0.0):
                    print(f"   {k:34} = {m2o(v) if isinstance(v, list) else v}")
        else:
            print(f"   operacao {OP_5902} nao encontrada")

    # ---- 5. impostos default dos produtos de terceiros ----
    print("\n" + "=" * 92)
    print("### 5. IMPOSTOS DEFAULT dos produtos de terceiros (taxes_id) — fonte provavel do espurio")
    pfg, _ = fields_of('product.product', [])
    pwant = [f for f in ['default_code', 'name', 'taxes_id', 'supplier_taxes_id'] if f in pfg]
    prods = rr('product.product', [('default_code', 'in', CODS_TERCEIROS)], pwant)
    for p in prods:
        print(f"   [{p.get('default_code')}] taxes_id={p.get('taxes_id')} supplier_taxes_id={p.get('supplier_taxes_id')}")
    # nomes dos taxes
    all_tax = set()
    for p in prods:
        for t in (p.get('taxes_id') or []):
            all_tax.add(t)
    if all_tax:
        taxes = rr('account.tax', [('id', 'in', list(all_tax))], ['id', 'name', 'amount', 'amount_type'])
        print("   --- impostos referenciados ---")
        for t in taxes:
            print(f"      {t['id']}: {t['name'][:40]} amount={t.get('amount')} type={t.get('amount_type')}")


if __name__ == '__main__':
    main()
