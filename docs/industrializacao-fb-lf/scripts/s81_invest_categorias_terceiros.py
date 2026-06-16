"""s81 — INVESTIGA (READ-only) S2/A5: QUAIS categorias LF já valoram terceiros + cruza com o saldo a migrar.

Define o escopo real de A5 (repoint L1):
  - mapa categ_id -> conta de valoração (company 5): terceiros (1150200001) vs próprio
  - dos 311 produtos do saldo em 42: quantos já estão em categoria-terceiros vs próprio

Zero escrita. Uso: python .../s81_invest_categorias_terceiros.py
"""
import sys, json, collections
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema_wire_r2')
from dotenv import load_dotenv
load_dotenv('/home/rafaelnascimento/projetos/frete_sistema/.env')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5], 'company_id': 5, 'lang': 'pt_BR'}
OUT = {}
TERCEIROS_ACC_ID = 26140  # 1150200001 MATERIAL DE TERCEIROS A INDUSTRIALIZAR (LF)


def main():
    o = get_odoo_connection()
    assert o.authenticate(), 'falha auth'

    def sr(model, dom, fields, **kw):
        kw.setdefault('context', CTX)
        return o.execute_kw(model, 'search_read', [dom], {'fields': fields, **kw})

    def rd(model, ids, fields):
        return o.execute_kw(model, 'read', [ids], {'fields': fields, 'context': CTX}) if ids else []

    print('=' * 88); print('s81 — categorias terceiros vs próprio + cruzamento com saldo'); print('=' * 88)

    # 1. ir.property valuation company 5 -> categ_id -> conta
    props = sr('ir.property', [['name', '=', 'property_stock_valuation_account_id'], ['company_id', '=', 5]],
               ['id', 'res_id', 'value_reference'])
    # res_id = 'product.category,ID'
    cat2acc = {}
    for p in props:
        rid = p.get('res_id')
        if not rid or ',' not in str(rid):
            continue
        cat_id = int(str(rid).split(',')[1])
        vr = p.get('value_reference')
        acc_id = int(str(vr).split(',')[1]) if vr and ',' in str(vr) else None
        cat2acc[cat_id] = acc_id
    cat_ids = list(cat2acc)
    cats = {c['id']: c['complete_name'] for c in rd('product.category', cat_ids, ['complete_name'])}
    print(f"\n### 1. Categorias LF com property valuation (company 5): {len(cat2acc)}")
    terceiros_cats = sorted([cid for cid, a in cat2acc.items() if a == TERCEIROS_ACC_ID], key=lambda c: cats.get(c, ''))
    print(f"\n  --- {len(terceiros_cats)} categorias JÁ em TERCEIROS (1150200001) ---")
    for cid in terceiros_cats:
        print(f"    [{cid}] {cats.get(cid)}")
    OUT['terceiros_cats'] = {cid: cats.get(cid) for cid in terceiros_cats}
    proprio_cats = sorted([cid for cid, a in cat2acc.items() if a and a != TERCEIROS_ACC_ID], key=lambda c: cats.get(c, ''))
    print(f"\n  --- {len(proprio_cats)} categorias em PRÓPRIO (amostra) ---")
    for cid in proprio_cats[:25]:
        print(f"    [{cid}] -> acc {cat2acc[cid]} | {cats.get(cid)}")
    OUT['proprio_cats'] = {cid: cats.get(cid) for cid in proprio_cats}

    # 2. cruzar com o saldo em 42 (produtos)
    print('\n### 2. Saldo em 42 — produtos por classe contábil da categoria')
    sub42 = [f['id'] for f in sr('stock.location', [['id', 'child_of', 42]], ['id'])]
    quants = sr('stock.quant', [['location_id', 'in', sub42]],
                ['product_id', 'quantity'], limit=5000)
    qn = [q for q in quants if abs(q['quantity']) > 1e-6 and q.get('product_id')]
    prod_ids = list({q['product_id'][0] for q in qn})
    prods = rd('product.product', prod_ids, ['id', 'categ_id'])
    pcat = {p['id']: (p['categ_id'][0] if p.get('categ_id') else None) for p in prods}
    cls = collections.Counter()
    cat_sem_prop = collections.Counter()
    for q in qn:
        pid = q['product_id'][0]
        cat = pcat.get(pid)
        acc = cat2acc.get(cat)
        if acc == TERCEIROS_ACC_ID:
            cls['terceiros'] += 1
        elif acc:
            cls['proprio'] += 1
        else:
            cls['sem_property'] += 1
            cat_sem_prop[cats.get(cat, cat)] += 1
    print(f"  quants(qty!=0) no saldo: {len(qn)}")
    print(f"    em categoria TERCEIROS (já 1150200001): {cls['terceiros']}")
    print(f"    em categoria PRÓPRIO: {cls['proprio']}")
    print(f"    sem property explícita (herda pai): {cls['sem_property']}")
    if cat_sem_prop:
        print('    --- categorias sem property (top) ---')
        for c, n in cat_sem_prop.most_common(10):
            print(f"      {n:4d} | {c}")
    OUT['cruzamento'] = dict(cls)

    with open('/tmp/s2_s81.json', 'w') as f:
        json.dump(OUT, f, ensure_ascii=False, indent=2, default=str)
    print('\n[dump] /tmp/s2_s81.json')


if __name__ == '__main__':
    main()
