"""s73 — INVESTIGA (READ-only) S2: rules + routes + picking_types + warehouse + subcontratação.

Cobre checklist S2:
  - TODAS as stock.rule que tocam 42 (src ou dst, incl. child_of) + a rota de cada
  - picking_types relevantes (entrada/armazenar PA/ordens entrega/retorno) com src/dst default
  - stock.warehouse LF (lot_stock_id e locations de etapa)
  - Subcontratação (rota subcontract, locations 30713/30716)

Zero escrita. Uso: python .../s73_invest_rules_routes_pt.py
"""
import sys, json, collections
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema_wire_r2')
from dotenv import load_dotenv
load_dotenv('/home/rafaelnascimento/projetos/frete_sistema/.env')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5], 'company_id': 5, 'lang': 'pt_BR'}
SEP = '=' * 95
OUT = {}


def main():
    o = get_odoo_connection()
    assert o.authenticate(), 'falha auth'

    def sr(model, dom, fields, **kw):
        kw.setdefault('context', CTX)
        return o.execute_kw(model, 'search_read', [dom], {'fields': fields, **kw})

    def rd(model, ids, fields):
        if not ids:
            return []
        return o.execute_kw(model, 'read', [ids], {'fields': fields, 'context': CTX})

    def m2(v):
        return f"{v[0]}:{v[1]}" if v else "—"

    print(SEP); print('s73 — RULES + ROUTES + PICKING_TYPES + WAREHOUSE + SUBCONTRAT (READ-only)'); print(SEP)

    # subárvore de 42 p/ pegar rules que usam 42 ou filhas
    filhas = [f['id'] for f in sr('stock.location', [['id', 'child_of', 42]], ['id'])]
    alvo = [42, 31092, 31093, 53, 54, 30710, 28835] + filhas
    alvo = list(set(alvo))

    # ---------- 1. RULES tocando 42 (src ou dst) ----------
    print('\n### 1. stock.rule — src OU dst em 42/subárvore (+ 31092/31093/53/54)')
    rule_fields = ['id', 'name', 'active', 'action', 'location_src_id', 'location_dest_id',
                   'picking_type_id', 'route_id', 'procure_method', 'company_id',
                   'group_propagation_option', 'group_id', 'sequence']
    dom = ['|', ['location_src_id', 'in', alvo], ['location_dest_id', 'in', alvo]]
    rules = sr('stock.rule', dom, rule_fields, limit=500)
    # filtra: pelo menos uma ponta exatamente em 42/31092/31093/53/54 (evita ruído de sublocations distantes)
    foco = [42, 31092, 31093, 53, 54, 30710, 28835]
    src42 = [r for r in rules if r['location_src_id'] and r['location_src_id'][0] in foco]
    dst42 = [r for r in rules if r['location_dest_id'] and r['location_dest_id'][0] in foco]
    print(f"  total rules tocando subárvore: {len(rules)} | src∈foco={len(src42)} | dst∈foco={len(dst42)}")
    print('\n  --- RULES (todas tocando o foco), ordenadas por rota ---')
    rota_de = collections.defaultdict(list)
    for r in rules:
        if (r['location_src_id'] and r['location_src_id'][0] in foco) or \
           (r['location_dest_id'] and r['location_dest_id'][0] in foco):
            rname = r['route_id'][1] if r['route_id'] else '(sem rota)'
            rota_de[rname].append(r)
    for rname in sorted(rota_de):
        print(f"\n  ROTA: {rname}")
        for r in sorted(rota_de[rname], key=lambda x: x['id']):
            act = r['action']
            print(f"    [{r['id']}] {'ON ' if r['active'] else 'off'} {act:14s} "
                  f"src={m2(r['location_src_id']):28s} -> dst={m2(r['location_dest_id']):28s} "
                  f"pt={m2(r['picking_type_id'])} pm={r.get('procure_method')} co={r['company_id'][0] if r['company_id'] else '?'}")
    OUT['rules_foco'] = [r for rs in rota_de.values() for r in rs]

    # ---------- 2. ROTAS completas dos rules ----------
    print('\n### 2. stock.route — rotas envolvidas + TODAS as suas rules')
    route_ids = list({r['route_id'][0] for rs in rota_de.values() for r in rs if r['route_id']})
    routes = rd('stock.route', route_ids, ['id', 'name', 'active', 'product_selectable',
                                           'product_categ_selectable', 'warehouse_selectable',
                                           'rule_ids', 'warehouse_ids', 'company_id'])
    OUT['routes'] = routes
    for rt in sorted(routes, key=lambda x: x['id']):
        print(f"  [{rt['id']}] {rt['name']} (active={rt['active']}, "
              f"sel: prod={rt['product_selectable']}/categ={rt['product_categ_selectable']}/wh={rt['warehouse_selectable']}, "
              f"#rules={len(rt['rule_ids'])}, wh={rt.get('warehouse_ids')}, co={rt['company_id']})")

    # ---------- 3. PICKING TYPES relevantes ----------
    print('\n### 3. stock.picking.type — LF + os referenciados pelas rules do foco')
    pt_from_rules = list({r['picking_type_id'][0] for rs in rota_de.values() for r in rs if r['picking_type_id']})
    # + todos os pt da LF (warehouse company 5) p/ entrada/armazenar/entrega/retorno
    pt_lf = sr('stock.picking.type', [['company_id', 'in', [5]]], ['id'], limit=200)
    pt_ids = list(set(pt_from_rules + [p['id'] for p in pt_lf]))
    pt_fields = ['id', 'name', 'code', 'sequence_code', 'default_location_src_id', 'default_location_dest_id',
                 'warehouse_id', 'company_id', 'active']
    # tentar campo CIEL IT tipo_pedido
    extra = o.execute_kw('stock.picking.type', 'fields_get', [], {'attributes': ['string'], 'context': CTX})
    tp_field = [k for k in extra if 'tipo_pedido' in k.lower()]
    pt_fields += tp_field
    pts = rd('stock.picking.type', pt_ids, pt_fields)
    OUT['picking_types'] = pts
    print(f"  (campo tipo_pedido detectado: {tp_field})")
    for p in sorted(pts, key=lambda x: x['id']):
        tp = p.get(tp_field[0]) if tp_field else None
        print(f"    [{p['id']}] {'ON ' if p['active'] else 'off'} {p['code']:9s} "
              f"src={m2(p['default_location_src_id']):26s} -> dst={m2(p['default_location_dest_id']):26s} "
              f"| {p['name']}  tipo_pedido={m2(tp) if isinstance(tp, (list, tuple)) else tp}")

    # ---------- 4. WAREHOUSE LF ----------
    print('\n### 4. stock.warehouse LF (âncora física)')
    wh_fields = ['id', 'name', 'code', 'lot_stock_id', 'company_id',
                 'wh_input_stock_loc_id', 'wh_output_stock_loc_id', 'wh_pack_stock_loc_id',
                 'wh_qc_stock_loc_id', 'manufacture_to_resupply', 'manu_type_id',
                 'reception_steps', 'delivery_steps', 'buy_to_resupply']
    whs = sr('stock.warehouse', [['company_id', 'in', [5]]], wh_fields)
    OUT['warehouses_lf'] = whs
    for w in whs:
        print(f"  [{w['id']}] {w['name']} ({w['code']}) lot_stock={m2(w['lot_stock_id'])} "
              f"manu_type={m2(w.get('manu_type_id'))} recv={w.get('reception_steps')} deliv={w.get('delivery_steps')} buy={w.get('buy_to_resupply')}")
        print(f"        input={m2(w.get('wh_input_stock_loc_id'))} output={m2(w.get('wh_output_stock_loc_id'))} "
              f"pack={m2(w.get('wh_pack_stock_loc_id'))} qc={m2(w.get('wh_qc_stock_loc_id'))}")

    # ---------- 5. SUBCONTRATAÇÃO ----------
    print('\n### 5. Subcontratação — rota subcontract + rules + locations 30713/30716')
    sub_routes = sr('stock.route', ['|', ['name', 'ilike', 'subcontrat'], ['name', 'ilike', 'subcontract']],
                    ['id', 'name', 'rule_ids', 'company_id'])
    for rt in sub_routes:
        print(f"  ROTA SUB [{rt['id']}] {rt['name']} (#rules={len(rt['rule_ids'])}, co={rt['company_id']})")
        srules = rd('stock.rule', rt['rule_ids'], ['id', 'name', 'action', 'location_src_id', 'location_dest_id', 'picking_type_id', 'company_id'])
        for r in srules:
            print(f"      [{r['id']}] {r['action']:12s} src={m2(r['location_src_id']):26s} -> dst={m2(r['location_dest_id']):26s} pt={m2(r['picking_type_id'])} co={r['company_id'][0] if r['company_id'] else '?'}")
    OUT['sub_routes'] = sub_routes

    with open('/tmp/s2_s73.json', 'w') as f:
        json.dump(OUT, f, ensure_ascii=False, indent=2, default=str)
    print('\n[dump] /tmp/s2_s73.json')


if __name__ == '__main__':
    main()
