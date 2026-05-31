#!/usr/bin/env python3
"""
Passo 0 — LEVANTAMENTO de contas de categoria (READ-ONLY) — Industrializacao FB<->LF.

NAO escreve nada no Odoo. Para cada categoria usada na LF (quant cmp=5):
  - le os 4 campos de conta + valuation/cost_method em contexto LF(5) e FB(1)
  - resolve os ids de conta para codes
  - faz dump bruto de ir.property (fonte de verdade) das categorias
Saida: tabela no stdout + JSON em /tmp/passo0_contas_lf.json

Uso:
    source .venv/bin/activate
    python docs/industrializacao-fb-lf/scripts/passo0_levantar_contas.py
"""
import sys
import json
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')

from app.odoo.utils.connection import get_odoo_connection

CMP_FB = 1
CMP_LF = 5

PROP_ACC_FIELDS = [
    'property_stock_valuation_account_id',
    'property_stock_account_input_categ_id',
    'property_stock_account_output_categ_id',
    'property_stock_account_production_cost_id',
]
SEL_FIELDS = ['property_valuation', 'property_cost_method']


def read_ctx(odoo, model, ids, fields, cid):
    """read com contexto de empresa (resolve company_dependent / ir.property)."""
    return odoo.execute_kw(model, 'read', [ids, fields],
                           {'context': {'allowed_company_ids': [cid], 'company_id': cid}})


def main():
    odoo = get_odoo_connection()
    if not odoo.authenticate():
        raise SystemExit("Falha auth Odoo")

    # 1) universo de categorias com quant na LF
    quants = odoo.search_read('stock.quant', [('company_id', '=', CMP_LF)],
                              ['product_id'], limit=100000)
    prod_ids = sorted({q['product_id'][0] for q in quants if q['product_id']})
    cat_ids = set()
    for i in range(0, len(prod_ids), 300):
        prods = odoo.read('product.product', prod_ids[i:i + 300], ['categ_id'])
        for p in prods:
            if p['categ_id']:
                cat_ids.add(p['categ_id'][0])
    cat_ids = sorted(cat_ids)
    print(f"# categorias na LF: {len(cat_ids)}")

    # 2) ler contas + valuation em contexto LF e FB
    flds = PROP_ACC_FIELDS + SEL_FIELDS + ['complete_name']
    lf = {c['id']: c for c in read_ctx(odoo, 'product.category', cat_ids, flds, CMP_LF)}
    fb = {c['id']: c for c in read_ctx(odoo, 'product.category', cat_ids, flds, CMP_FB)}

    # 3) resolver ids de conta -> code/name (uniao de todos referenciados)
    acc_ids = set()
    for src in (lf, fb):
        for c in src.values():
            for f in PROP_ACC_FIELDS:
                v = c.get(f)
                if v:
                    acc_ids.add(v[0])
    acc_map = {}
    if acc_ids:
        for a in odoo.read('account.account', sorted(acc_ids), ['code', 'name', 'company_id']):
            cmp = a['company_id'][1] if a['company_id'] else 'GLOBAL'
            acc_map[a['id']] = f"{a['code']} ({cmp.split(' - ')[-1] if ' - ' in cmp else cmp})"

    def acc(c, f):
        v = c.get(f)
        return acc_map.get(v[0], f"id={v[0]}") if v else '—'

    # 4) tabela: estado atual LF vs FB
    print()
    print("=" * 120)
    print("ESTADO ATUAL — contas de estoque por categoria (contexto LF vs FB)")
    print("VAL=valoracao  IN=entrada  OUT=saida  PROD=producao/elaboracao")
    print("=" * 120)
    out = []
    for cid in cat_ids:
        cl, cf = lf[cid], fb[cid]
        nome = cl.get('complete_name', '')
        row = {
            'categ_id': cid, 'nome': nome,
            'lf_valuation': cl.get('property_valuation'),
            'lf_cost_method': cl.get('property_cost_method'),
            'lf_val': acc(cl, 'property_stock_valuation_account_id'),
            'lf_in': acc(cl, 'property_stock_account_input_categ_id'),
            'lf_out': acc(cl, 'property_stock_account_output_categ_id'),
            'lf_prod': acc(cl, 'property_stock_account_production_cost_id'),
            'fb_val': acc(cf, 'property_stock_valuation_account_id'),
            'fb_in': acc(cf, 'property_stock_account_input_categ_id'),
            'fb_out': acc(cf, 'property_stock_account_output_categ_id'),
            'fb_prod': acc(cf, 'property_stock_account_production_cost_id'),
        }
        out.append(row)
        print(f"\ncateg {cid} | {nome}")
        print(f"  LF: valuation={row['lf_valuation']}/{row['lf_cost_method']} "
              f"VAL={row['lf_val']} IN={row['lf_in']} OUT={row['lf_out']} PROD={row['lf_prod']}")
        print(f"  FB: VAL={row['fb_val']} IN={row['fb_in']} OUT={row['fb_out']} PROD={row['fb_prod']}")

    # 5) resumo de padroes distintos na LF (quantos sao iguais)
    print()
    print("=" * 120)
    print("RESUMO — padroes distintos de contas na LF (VAL/IN/OUT/PROD)")
    print("=" * 120)
    from collections import Counter
    pat = Counter((r['lf_val'], r['lf_in'], r['lf_out'], r['lf_prod']) for r in out)
    for (v, i, o, p), n in pat.most_common():
        print(f"  [{n:>2} cats] VAL={v} | IN={i} | OUT={o} | PROD={p}")
    valn = Counter((r['lf_valuation'], r['lf_cost_method']) for r in out)
    print("  valuation/cost_method na LF:", dict(valn))

    # 6) dump ir.property bruto (fonte de verdade)
    print()
    print("=" * 120)
    print("ir.property — linhas existentes para estas categorias (fonte de verdade)")
    print("=" * 120)
    res_refs = [f"product.category,{cid}" for cid in cat_ids]
    props = odoo.search_read('ir.property',
                             [('res_id', 'in', res_refs),
                              ('name', 'in', PROP_ACC_FIELDS + SEL_FIELDS)],
                             ['name', 'res_id', 'company_id', 'value_reference', 'type'],
                             limit=100000)
    print(f"  total ir.property rows: {len(props)}")
    by_cmp = Counter((p['company_id'][1] if p['company_id'] else 'GLOBAL') for p in props)
    print("  por empresa:", dict(by_cmp))
    by_field_cmp = Counter(
        (p['name'], (p['company_id'][1].split(' - ')[-1] if p['company_id'] else 'GLOBAL'))
        for p in props)
    for (fname, cmp), n in sorted(by_field_cmp.items()):
        print(f"    {fname:48s} {cmp:8s} -> {n} rows")

    with open('/tmp/passo0_contas_lf.json', 'w') as f:
        json.dump({'cat_ids': cat_ids, 'rows': out,
                   'ir_property_count': len(props)}, f, ensure_ascii=False, indent=2)
    print("\nJSON salvo em /tmp/passo0_contas_lf.json")


if __name__ == '__main__':
    main()
