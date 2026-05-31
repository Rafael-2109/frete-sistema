#!/usr/bin/env python3
"""
Passo 0 — PROBE estrutural (READ-ONLY) — Industrializacao FB<->LF.

NAO escreve nada no Odoo. Apenas leituras para:
  1. Confirmar nomes/tipos dos campos de conta de estoque em product.category.
  2. Resolver os IDs das contas-alvo (1150200001/1150200002/1150100004) por empresa.
  3. Descobrir o marcador de "produto industrializado pela LF" (linha_producao?).
  4. Dimensionar o universo de categorias usadas na LF (via stock.quant cmp=5).

Uso:
    source .venv/bin/activate
    python docs/industrializacao-fb-lf/scripts/passo0_probe.py
"""
import sys
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')

from app.odoo.utils.connection import get_odoo_connection

CMP_FB = 1
CMP_LF = 5
CONTAS_ALVO = ['1150200001', '1150200002', '1150100004',
               '1150100001', '1150100002', '1150100007',
               '1150100011', '1150100012', '3201000002', '3201000003']

PROP_FIELDS = [
    'property_stock_valuation_account_id',
    'property_stock_account_input_categ_id',
    'property_stock_account_output_categ_id',
    'property_stock_account_production_cost_id',
]


def main():
    odoo = get_odoo_connection()
    if not odoo.authenticate():
        raise SystemExit("Falha auth Odoo")

    print("=" * 78)
    print("1) CAMPOS de product.category (property_stock* + valuation/cost_method)")
    print("=" * 78)
    fg = odoo.execute_kw('product.category', 'fields_get', [],
                         {'attributes': ['string', 'type', 'relation', 'company_dependent']})
    for fname in sorted(fg.keys()):
        if 'stock' in fname or 'valuation' in fname or 'cost_method' in fname or fname.startswith('property_'):
            meta = fg[fname]
            print(f"  {fname:48s} type={meta.get('type'):10s} "
                  f"cdep={meta.get('company_dependent')} rel={meta.get('relation')}")

    print()
    print("=" * 78)
    print("2) CONTAS-ALVO (account.account) por empresa")
    print("=" * 78)
    accs = odoo.search_read('account.account',
                            [('code', 'in', CONTAS_ALVO)],
                            ['code', 'name', 'company_id'], limit=200)
    for a in sorted(accs, key=lambda x: (x['code'], (x['company_id'] or [0])[0])):
        cid = a['company_id'][1] if a['company_id'] else 'GLOBAL'
        print(f"  id={a['id']:<7} code={a['code']:<12} cmp={cid:<22} {a['name']}")
    # destaque: existe par terceiros na LF?
    for code in ('1150200001', '1150200002', '1150100004'):
        lf = [a for a in accs if a['code'] == code and a['company_id'] and a['company_id'][0] == CMP_LF]
        print(f"  -> {code} existe na LF(5)? {'SIM id='+str(lf[0]['id']) if lf else 'NAO!!!'}")

    print()
    print("=" * 78)
    print("3) Marcador de produto industrializado LF (descobrir campo)")
    print("=" * 78)
    fgt = odoo.execute_kw('product.template', 'fields_get', [],
                          {'attributes': ['string', 'type', 'relation']})
    cand = [f for f in fgt if any(k in f.lower() for k in
            ('linha_producao', 'linha', 'producao', 'industri', 'subcontr', 'fabric'))]
    for f in sorted(cand):
        print(f"  {f:42s} {fgt[f].get('type'):10s} {fgt[f].get('string')}")

    print()
    print("=" * 78)
    print("4) UNIVERSO: categorias distintas com stock.quant na LF (cmp=5)")
    print("=" * 78)
    # quants da LF: company_id=5. read_group por categoria via product.
    quants = odoo.search_read('stock.quant',
                              [('company_id', '=', CMP_LF)],
                              ['product_id', 'quantity', 'location_id'], limit=100000)
    print(f"  total quants cmp=5: {len(quants)}")
    prod_ids = sorted({q['product_id'][0] for q in quants if q['product_id']})
    print(f"  produtos distintos com quant na LF: {len(prod_ids)}")
    # mapear produto -> categ + type
    cats = {}
    for i in range(0, len(prod_ids), 200):
        chunk = prod_ids[i:i + 200]
        prods = odoo.read('product.product', chunk, ['categ_id', 'type', 'default_code', 'name'])
        for p in prods:
            if p['categ_id']:
                cats.setdefault(p['categ_id'][0], {'name': p['categ_id'][1], 'n_prod': 0, 'types': set()})
                cats[p['categ_id'][0]]['n_prod'] += 1
                cats[p['categ_id'][0]]['types'].add(p['type'])
    print(f"  categorias distintas usadas na LF: {len(cats)}")
    for cid, info in sorted(cats.items(), key=lambda x: -x[1]['n_prod']):
        print(f"    categ id={cid:<6} n_prod={info['n_prod']:<4} types={sorted(info['types'])} {info['name']}")


if __name__ == '__main__':
    main()
