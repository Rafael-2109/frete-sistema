"""s78 — INVESTIGA (READ-only) S2: put-away rules + features de multi-location/storage (decide abordagem).

  - put-away rules existentes (LF / location 42 / warehouse 4)
  - feature group_stock_multi_locations ativa? storage categories?
  - location 42: campos de put-away/storage

Zero escrita. Uso: python .../s78_invest_putaway.py
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
    print('=' * 85); print('s78 — PUT-AWAY + features storage/multi-loc'); print('=' * 85)

    # 1. put-away rules
    print('\n### 1. stock.putaway.rule existentes')
    try:
        pa = sr('stock.putaway.rule', [],
                ['id', 'location_in_id', 'location_out_id', 'product_id', 'category_id', 'company_id'], limit=200)
        print(f"  total putaway rules: {len(pa)}")
        for r in pa:
            print(f"    [{r['id']}] in={m2(r['location_in_id'])} -> out={m2(r['location_out_id'])} "
                  f"prod={m2(r.get('product_id'))} categ={m2(r.get('category_id'))} co={r['company_id'][0] if r['company_id'] else '?'}")
        OUT['putaway'] = pa
    except Exception as e:
        print(f"  ERRO put-away: {e}")

    # 2. feature flags (res.groups / ir.config_parameter)
    print('\n### 2. Features de estoque (grupos)')
    for xmlid in ['stock.group_stock_multi_locations', 'stock.group_stock_storage_categories',
                  'stock.group_adv_location', 'stock.group_stock_multi_warehouses']:
        try:
            grp = o.execute_kw('ir.model.data', 'search_read',
                               [[['module', '=', xmlid.split('.')[0]], ['name', '=', xmlid.split('.')[1]]]],
                               {'fields': ['res_id'], 'context': CTX})
            if grp:
                g = o.execute_kw('res.groups', 'read', [[grp[0]['res_id']]], {'fields': ['name', 'users'], 'context': CTX})
                print(f"  {xmlid}: ativo p/ {len(g[0]['users'])} usuários")
                OUT[xmlid] = len(g[0]['users'])
            else:
                print(f"  {xmlid}: (não encontrado)")
        except Exception as e:
            print(f"  {xmlid}: ERRO {e}")

    # 3. location 42 storage fields
    print('\n### 3. location 42 — campos storage/putaway')
    f = o.execute_kw('stock.location', 'fields_get', [], {'attributes': ['string'], 'context': CTX})
    sf = [k for k in f if any(p in k.lower() for p in ['storage', 'putaway', 'removal', 'cyclic'])]
    l42 = o.execute_kw('stock.location', 'read', [[42, 31092, 31093]], {'fields': ['id', 'complete_name'] + sf, 'context': CTX})
    print(f"  campos: {sf}")
    for l in l42:
        print(f"    [{l['id']}] {l['complete_name']}: " + " ".join(f"{k}={l.get(k)}" for k in sf))

    # 4. warehouse 4 — campos de etapa que poderiam ancorar put-away
    wh = o.execute_kw('stock.warehouse', 'read', [[4]],
                      {'fields': ['id', 'name', 'lot_stock_id', 'reception_steps', 'delivery_steps',
                                  'manufacture_steps', 'manufacture_to_resupply'], 'context': CTX})
    print(f"\n### 4. warehouse LF: {wh}")
    OUT['wh'] = wh

    with open('/tmp/s2_s78.json', 'w') as fo:
        json.dump(OUT, fo, ensure_ascii=False, indent=2, default=str)
    print('\n[dump] /tmp/s2_s78.json')


if __name__ == '__main__':
    main()
