"""s79 — INVESTIGA (READ-only) S2/D2: viabilidade de lot_stock_id=41 (view).

  - lot_stock_id de TODOS os warehouses (algum usa location view?)
  - usage de 41 + filhas internal de 41
  - domain/help do campo lot_stock_id
  - categoria PRODUTO ACABADO (id) p/ put-away

Zero escrita. Uso: python .../s79_invest_lotstock_view.py
"""
import sys, json
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema_wire_r2')
from dotenv import load_dotenv
load_dotenv('/home/rafaelnascimento/projetos/frete_sistema/.env')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5], 'company_id': 5, 'lang': 'pt_BR'}
OUT = {}


def main():
    o = get_odoo_connection()
    assert o.authenticate(), 'falha auth'

    def sr(model, dom, fields, **kw):
        kw.setdefault('context', CTX)
        return o.execute_kw(model, 'search_read', [dom], {'fields': fields, **kw})

    def m2(v):
        return f"{v[0]}:{v[1]}" if v else "—"
    print('=' * 85); print('s79 — lot_stock view + categoria PA'); print('=' * 85)

    # 1. lot_stock de todos os WH + usage da location
    print('\n### 1. lot_stock_id de todos os warehouses (usa view?)')
    whs = sr('stock.warehouse', [], ['id', 'name', 'code', 'lot_stock_id', 'view_location_id', 'company_id'])
    locids = list({w['lot_stock_id'][0] for w in whs if w.get('lot_stock_id')} |
                  {w['view_location_id'][0] for w in whs if w.get('view_location_id')})
    usages = {l['id']: l['usage'] for l in o.execute_kw('stock.location', 'read', [locids], {'fields': ['usage'], 'context': CTX})}
    for w in sorted(whs, key=lambda x: x['id']):
        ls = w.get('lot_stock_id'); vl = w.get('view_location_id')
        print(f"    WH[{w['id']}] {w['name']:24s} co={w['company_id'][0] if w['company_id'] else '?'} "
              f"lot_stock={m2(ls)} (usage={usages.get(ls[0]) if ls else '?'}) "
              f"view_loc={m2(vl)} (usage={usages.get(vl[0]) if vl else '?'})")
    OUT['whs'] = [{'id': w['id'], 'lot_stock': m2(w.get('lot_stock_id')),
                   'lot_usage': usages.get(w['lot_stock_id'][0]) if w.get('lot_stock_id') else None,
                   'view_loc': m2(w.get('view_location_id'))} for w in whs]

    # 2. campo lot_stock_id (help/domain)
    print('\n### 2. campo stock.warehouse.lot_stock_id')
    f = o.execute_kw('stock.warehouse', 'fields_get', [['lot_stock_id', 'view_location_id']],
                     {'attributes': ['string', 'help', 'domain', 'relation', 'required'], 'context': CTX})
    for k, v in f.items():
        print(f"    {k}: domain={v.get('domain')} required={v.get('required')} help={(v.get('help') or '')[:90]}")
    OUT['lot_stock_field'] = f

    # 3. filhas de 41 (o que entraria no on-hand com lot_stock=41)
    print('\n### 3. Filhas internal de 41 (impacto no on-hand se lot_stock=41)')
    filhas41 = sr('stock.location', [['id', 'child_of', 41], ['usage', '=', 'internal']],
                  ['id', 'complete_name', 'usage'])
    for l in sorted(filhas41, key=lambda x: x['id']):
        print(f"    [{l['id']}] {l['complete_name']}")
    OUT['filhas41_internal'] = [l['id'] for l in filhas41]

    # 4. categoria PRODUTO ACABADO p/ put-away
    print('\n### 4. Categoria(s) PRODUTO ACABADO (raiz p/ put-away PA->31093)')
    cats = sr('product.category', [['complete_name', 'ilike', 'PRODUTO ACABADO']],
              ['id', 'complete_name', 'parent_id'])
    for c in sorted(cats, key=lambda x: len(x['complete_name'])):
        print(f"    [{c['id']}] parent={m2(c.get('parent_id'))} | {c['complete_name']}")
    # raiz "TODOS"
    raiz = sr('product.category', [['name', '=', 'TODOS']], ['id', 'complete_name'])
    print(f"  raiz: {raiz}")
    OUT['cat_pa'] = cats; OUT['cat_raiz'] = raiz

    with open('/tmp/s2_s79.json', 'w') as fo:
        json.dump(OUT, fo, ensure_ascii=False, indent=2, default=str)
    print('\n[dump] /tmp/s2_s79.json')


if __name__ == '__main__':
    main()
