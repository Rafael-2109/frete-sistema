"""s74 — INVESTIGA (READ-only) S2: histórico stock.move em 42 + parents das locations + reserva açúcar + MOs ativas.

Cobre checklist S2:
  - parent (location_id) de 42/31092/31093/53/54/26489/30716 -> decisivo p/ lot_stock_id
  - histórico de stock.move (done, 365d) tocando 42: entradas/saídas/internos por picking_type
  - reserva ativa do açúcar (quant 261042) -> qual move/picking
  - MOs ativas (confirmed/progress) consumindo de 42/53/31092

Zero escrita. Uso: python .../s74_invest_moves_parents_mos.py
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

    print(SEP); print('s74 — MOVES + PARENTS + RESERVA AÇÚCAR + MOs (READ-only)'); print(SEP)

    # ---------- 1. PARENTS das locations-chave ----------
    print('\n### 1. Parent (location_id) das locations-chave')
    chave = [41, 42, 31092, 31093, 53, 54, 30710, 28835, 26489, 30716, 30713, 4021, 26483, 43, 45]
    locs = rd('stock.location', chave, ['id', 'complete_name', 'usage', 'location_id'])
    OUT['parents'] = locs
    for l in sorted(locs, key=lambda x: x['id']):
        print(f"  [{l['id']}] {l['usage']:10s} parent={m2(l['location_id']):20s} | {l['complete_name']}")

    # ---------- 2. HISTÓRICO stock.move tocando 42 (done, 365d) ----------
    print('\n### 2. stock.move done (365d) tocando subárvore de 42 — fluxos reais por picking_type')
    sub42 = [f['id'] for f in sr('stock.location', [['id', 'child_of', 42]], ['id'])]
    DATA = '2025-06-01'

    # ENTRADAS (dest in 42, src NOT in 42)
    dom_in = [['state', '=', 'done'], ['date', '>=', DATA],
              ['location_dest_id', 'in', sub42], ['location_id', 'not in', sub42]]
    g_in = rg('stock.move', dom_in, ['picking_type_id'], ['product_qty:sum'])
    print('\n  --- ENTRADAS em 42 (src externo -> 42) por picking_type ---')
    for g in sorted(g_in, key=lambda x: -x['__count']):
        print(f"    {g['__count']:6d} moves | qty={g.get('product_qty', 0):>14.1f} | pt={m2(g['picking_type_id'])}")
    OUT['entradas_42'] = [{'pt': m2(g['picking_type_id']), 'n': g['__count'], 'qty': g.get('product_qty', 0)} for g in g_in]

    # SAÍDAS (src in 42, dest NOT in 42)
    dom_out = [['state', '=', 'done'], ['date', '>=', DATA],
               ['location_id', 'in', sub42], ['location_dest_id', 'not in', sub42]]
    g_out = rg('stock.move', dom_out, ['picking_type_id'], ['product_qty:sum'])
    print('\n  --- SAÍDAS de 42 (42 -> dest externo) por picking_type ---')
    for g in sorted(g_out, key=lambda x: -x['__count']):
        print(f"    {g['__count']:6d} moves | qty={g.get('product_qty', 0):>14.1f} | pt={m2(g['picking_type_id'])}")
    OUT['saidas_42'] = [{'pt': m2(g['picking_type_id']), 'n': g['__count'], 'qty': g.get('product_qty', 0)} for g in g_out]

    # também quebrar saídas por location_dest (p/ ver destinos reais)
    g_out_dest = rg('stock.move', dom_out, ['location_dest_id'], ['product_qty:sum'])
    print('\n  --- SAÍDAS de 42 por DESTINO ---')
    for g in sorted(g_out_dest, key=lambda x: -x['__count']):
        print(f"    {g['__count']:6d} moves | qty={g.get('product_qty', 0):>14.1f} | dest={m2(g['location_dest_id'])}")

    # entradas por origem
    g_in_src = rg('stock.move', dom_in, ['location_id'], ['product_qty:sum'])
    print('\n  --- ENTRADAS em 42 por ORIGEM ---')
    for g in sorted(g_in_src, key=lambda x: -x['__count']):
        print(f"    {g['__count']:6d} moves | qty={g.get('product_qty', 0):>14.1f} | src={m2(g['location_id'])}")

    # ---------- 3. RESERVA do açúcar 261042 ----------
    print('\n### 3. Reserva ativa (quant 261042 açúcar) — quem reserva?')
    # move.lines não-done reservando em 42 do produto açúcar cristal 105000024
    mls = sr('stock.move.line',
             [['state', 'not in', ['done', 'cancel']], ['location_id', 'in', sub42],
              ['product_id.default_code', '=', '105000024']],
             ['id', 'move_id', 'picking_id', 'product_id', 'lot_id', 'quantity', 'reserved_uom_qty', 'state', 'location_id', 'location_dest_id'])
    OUT['reserva_acucar'] = mls
    if not mls:
        print("    (nenhuma move.line aberta p/ açúcar cristal 105000024 — re-checar)")
    for ml in mls:
        print(f"    ML {ml['id']} pick={m2(ml.get('picking_id'))} move={m2(ml.get('move_id'))} "
              f"lot={m2(ml.get('lot_id'))} qty={ml.get('quantity')} resv={ml.get('reserved_uom_qty')} "
              f"state={ml['state']} {m2(ml['location_id'])}->{m2(ml['location_dest_id'])}")

    # qualquer reserva aberta em 42 (genérico)
    mls_all = sr('stock.move.line',
                 [['state', 'not in', ['done', 'cancel']], ['location_id', 'in', sub42]],
                 ['id', 'product_id', 'picking_id', 'reserved_uom_qty', 'state'], limit=50)
    print(f"\n    total move.lines abertas saindo de 42 (qualquer produto): {len(mls_all)}")
    for ml in mls_all[:20]:
        print(f"      ML {ml['id']} {m2(ml.get('product_id'))} pick={m2(ml.get('picking_id'))} resv={ml.get('reserved_uom_qty')} state={ml['state']}")

    # ---------- 4. MOs ativas consumindo de 42/53/31092 ----------
    print('\n### 4. MOs ativas (confirmed/progress/to_close) — LF')
    mos = sr('mrp.production',
             [['company_id', 'in', [5]], ['state', 'in', ['confirmed', 'progress', 'to_close']]],
             ['id', 'name', 'state', 'product_id', 'location_src_id', 'location_dest_id', 'date_start'], limit=100)
    OUT['mos_ativas'] = mos
    print(f"  total MOs ativas LF: {len(mos)}")
    for mo in mos:
        print(f"    [{mo['id']}] {mo['name']} {mo['state']:10s} src={m2(mo.get('location_src_id'))} "
              f"dst={m2(mo.get('location_dest_id'))} prod={m2(mo.get('product_id'))}")

    # raws dessas MOs reservando em 42
    if mos:
        raw = sr('stock.move',
                 [['raw_material_production_id', 'in', [m['id'] for m in mos]], ['state', 'not in', ['done', 'cancel']]],
                 ['id', 'product_id', 'location_id', 'reserved_availability', 'product_uom_qty', 'state'], limit=200)
        in42 = [r for r in raw if r['location_id'] and r['location_id'][0] in sub42]
        print(f"\n  raws dessas MOs com origem em 42: {len(in42)}")
        for r in in42[:30]:
            print(f"    move {r['id']} {m2(r['product_id'])} src={m2(r['location_id'])} qty={r['product_uom_qty']} resv={r.get('reserved_availability')} {r['state']}")

    with open('/tmp/s2_s74.json', 'w') as f:
        json.dump(OUT, f, ensure_ascii=False, indent=2, default=str)
    print('\n[dump] /tmp/s2_s74.json')


if __name__ == '__main__':
    main()
