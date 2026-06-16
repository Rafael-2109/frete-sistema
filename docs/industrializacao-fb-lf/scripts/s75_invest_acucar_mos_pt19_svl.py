"""s75 — INVESTIGA (READ-only) S2: reserva açúcar + MOs ativas + o que entra por pt19 (compras) + SVL interno.

Fecha o checklist S2:
  - reserva ativa do açúcar (lote 230326 / quant 261042)
  - MOs ativas LF + raws com origem em 42
  - o que ENTRA por pt19 (Recebimento LF / compras): categorias (terceiros vs próprio)
  - CONTÁBIL: valuation_in/out das locations 42/31092/31093/26489 + SVL de move interno (prova neutralidade)

Zero escrita. Uso: python .../s75_invest_acucar_mos_pt19_svl.py
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

    def rg(model, dom, gb, fields):
        return o.execute_kw(model, 'read_group', [dom, fields, gb], {'lazy': False, 'context': CTX})

    def m2(v):
        return f"{v[0]}:{v[1]}" if v else "—"

    print(SEP); print('s75 — AÇÚCAR + MOs + pt19 + SVL interno (READ-only)'); print(SEP)
    sub42 = [f['id'] for f in sr('stock.location', [['id', 'child_of', 42]], ['id'])]

    # ---------- 1. RESERVA do açúcar ----------
    print('\n### 1. Reserva ativa do açúcar (lote 230326 / produto 105000024)')
    mls = sr('stock.move.line',
             [['state', 'not in', ['done', 'cancel']], ['location_id', 'in', sub42],
              ['product_id.default_code', '=', '105000024']],
             ['id', 'move_id', 'picking_id', 'product_id', 'lot_id', 'quantity', 'state',
              'location_id', 'location_dest_id'])
    OUT['reserva_acucar'] = mls
    for ml in mls:
        print(f"    ML {ml['id']} pick={m2(ml.get('picking_id'))} move={m2(ml.get('move_id'))} "
              f"lot={m2(ml.get('lot_id'))} qty={ml.get('quantity')} state={ml['state']} "
              f"{m2(ml['location_id'])}->{m2(ml['location_dest_id'])}")
    if mls:
        mv_ids = [ml['move_id'][0] for ml in mls if ml.get('move_id')]
        mvs = rd('stock.move', mv_ids, ['id', 'name', 'state', 'picking_id', 'raw_material_production_id',
                                        'location_id', 'location_dest_id', 'origin', 'group_id'])
        for mv in mvs:
            print(f"      MOVE {mv['id']} {mv.get('name')} state={mv['state']} pick={m2(mv.get('picking_id'))} "
                  f"MO={m2(mv.get('raw_material_production_id'))} origin={mv.get('origin')} "
                  f"{m2(mv['location_id'])}->{m2(mv['location_dest_id'])}")

    # todas as reservas abertas saindo de 42 (panorama)
    mls_all = sr('stock.move.line',
                 [['state', 'not in', ['done', 'cancel']], ['location_id', 'in', sub42]],
                 ['id', 'product_id', 'picking_id', 'move_id', 'quantity', 'state', 'lot_id'], limit=80)
    print(f"\n    total move.lines abertas saindo de 42: {len(mls_all)}")
    by_pt = collections.Counter()
    for ml in mls_all:
        by_pt[m2(ml.get('picking_id'))] += 1
    for k, c in by_pt.most_common():
        print(f"      {c}x pick={k}")
    OUT['reservas_abertas_42'] = len(mls_all)

    # ---------- 2. MOs ativas + raws de 42 ----------
    print('\n### 2. MOs ativas LF (confirmed/progress/to_close)')
    mos = sr('mrp.production',
             [['company_id', 'in', [5]], ['state', 'in', ['confirmed', 'progress', 'to_close']]],
             ['id', 'name', 'state', 'product_id', 'location_src_id', 'location_dest_id'], limit=100)
    OUT['mos_ativas'] = mos
    print(f"  total MOs ativas LF: {len(mos)}")
    for mo in mos:
        print(f"    [{mo['id']}] {mo['name']} {mo['state']:10s} src={m2(mo.get('location_src_id'))} dst={m2(mo.get('location_dest_id'))} prod={m2(mo.get('product_id'))}")
    if mos:
        raw = sr('stock.move',
                 [['raw_material_production_id', 'in', [m['id'] for m in mos]], ['state', 'not in', ['done', 'cancel']]],
                 ['id', 'product_id', 'location_id', 'product_uom_qty', 'state'], limit=300)
        in42 = [r for r in raw if r['location_id'] and r['location_id'][0] in sub42]
        print(f"\n  raws de MOs ativas com origem em 42: {len(in42)} (de {len(raw)} raws totais)")
        for r in in42[:30]:
            print(f"    move {r['id']} {m2(r['product_id'])} src={m2(r['location_id'])} qty={r['product_uom_qty']} {r['state']}")

    # ---------- 3. O que ENTRA por pt19 (compras) — categorias (terceiros vs próprio) ----------
    print('\n### 3. ENTRADAS por pt19 (Recebimento LF / compras) — categorias dos produtos (365d)')
    mv_pt19 = sr('stock.move',
                 [['picking_type_id', '=', 19], ['state', '=', 'done'], ['date', '>=', '2025-06-01']],
                 ['id', 'product_id', 'product_qty', 'location_id', 'location_dest_id', 'origin'], limit=4000)
    print(f"  moves pt19 done (365d): {len(mv_pt19)}")
    prod_ids = list({m['product_id'][0] for m in mv_pt19 if m.get('product_id')})
    prods = rd('product.product', prod_ids, ['id', 'categ_id', 'default_code'])
    catof = {p['id']: (p['categ_id'][1] if p.get('categ_id') else '?') for p in prods}
    cat_cnt = collections.Counter()
    cat_top = collections.defaultdict(lambda: 'TODOS')
    for m in mv_pt19:
        pid = m['product_id'][0] if m.get('product_id') else None
        cat = catof.get(pid, '?')
        top = cat.split('/')[1].strip() if '/' in cat else cat  # nível 1: EMBALAGEM/MATERIA PRIMA/PA
        cat_cnt[top] += 1
    print('  --- moves pt19 por macro-categoria ---')
    for c, n in cat_cnt.most_common():
        print(f"    {n:5d} moves | {c}")
    OUT['pt19_categorias'] = dict(cat_cnt)
    # destinos do pt19 (confirma se sempre 42 ou já houve override p/ 31092)
    dst_cnt = collections.Counter(m2(m['location_dest_id']) for m in mv_pt19)
    print('  --- destinos reais do pt19 ---')
    for d, n in dst_cnt.most_common():
        print(f"    {n:5d} -> {d}")

    # ---------- 4. CONTÁBIL: valuation accounts das locations + SVL de move interno ----------
    print('\n### 4. CONTÁBIL — valuation_in/out das locations 42/31092/31093/26489/54/53')
    locs = rd('stock.location', [42, 31092, 31093, 26489, 54, 53, 30716],
              ['id', 'complete_name', 'usage', 'valuation_in_account_id', 'valuation_out_account_id'])
    OUT['loc_valuation'] = locs
    for l in locs:
        print(f"    [{l['id']}] {l['usage']:10s} in={m2(l.get('valuation_in_account_id'))} "
              f"out={m2(l.get('valuation_out_account_id'))} | {l['complete_name']}")

    # SVL: existe valuation layer para moves INTERNOS (pt23 Transferências Internas) ?
    print('\n  --- SVL de moves internos (pt23 Transferências Internas, 365d) — prova de neutralidade ---')
    mv_int = sr('stock.move',
                [['picking_type_id', '=', 23], ['state', '=', 'done'], ['date', '>=', '2025-06-01']],
                ['id', 'product_id', 'location_id', 'location_dest_id'], limit=50)
    print(f"  moves pt23 done (365d): {len(mv_int)}")
    if mv_int:
        ids = [m['id'] for m in mv_int]
        svl = sr('stock.valuation.layer', [['stock_move_id', 'in', ids]],
                 ['id', 'stock_move_id', 'value', 'quantity'], limit=200)
        print(f"  SVL ligadas a esses moves internos: {len(svl)} (esperado 0 se internal->internal é neutro)")
        for s in svl[:10]:
            print(f"    SVL {s['id']} move={m2(s.get('stock_move_id'))} value={s.get('value')} qty={s.get('quantity')}")
        OUT['svl_internos'] = len(svl)
        for m in mv_int[:6]:
            print(f"    ex move {m['id']} {m2(m['location_id'])}->{m2(m['location_dest_id'])} {m2(m.get('product_id'))}")

    with open('/tmp/s2_s75.json', 'w') as f:
        json.dump(OUT, f, ensure_ascii=False, indent=2, default=str)
    print('\n[dump] /tmp/s2_s75.json')


if __name__ == '__main__':
    main()
