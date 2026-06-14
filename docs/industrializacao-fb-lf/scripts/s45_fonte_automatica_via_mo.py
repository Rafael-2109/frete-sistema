#!/usr/bin/env python3
"""S45 — READ-only: a NF-2 pode ser derivada AUTOMATICAMENTE a partir da NF-1 (sem
hardcode da remessa)? Caminho: NF-1 -> linha 5124 (PA + lote) -> MO que produziu o lote
-> componentes consumidos de 31092 (Materiais de Terceiros) + sub-MOs -> os 16 + valores.

Compara o resultado (componentes + qty + valor) com a remessa RPI/2026/00245 (s34: 16
itens, total 279,23) para ver se a derivacao via MO bate (entao o cron G1 dispensa a
remessa e e' 100% deterministico a partir da NF-1).

READ-ONLY. Usa o piloto: NF-1 789484 -> PA 4870112 lote PILOTO-3105.
"""
import sys
from collections import defaultdict
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5], 'company_id': 5, 'lang': 'pt_BR'}
NF1 = 789484
LOC_TERCEIROS = 31092   # LF/Materiais de Terceiros
REMESSA = 735679


def m2o(v):
    return f"{v[0]}|{str(v[1])[:30]}" if isinstance(v, list) and v else ('-' if not v else str(v))


def main():
    o = get_odoo_connection(); assert o.authenticate(), "FALHA AUTH"

    def rr(model, dom, fields, **kw):
        kw2 = {'fields': fields, 'context': CTX}; kw2.update(kw)
        return o.execute_kw(model, 'search_read', [dom], kw2)

    # 1. NF-1 -> linha 5124 -> PA + lote
    print("=" * 92)
    print("### 1. NF-1 -> PA + lote (via linha 5124 / stock.move)")
    pal = rr('account.move.line', [('move_id', '=', NF1), ('l10n_br_cfop_codigo', '=', '5124')],
             ['product_id', 'quantity'], limit=1)
    if not pal:
        print("   sem linha 5124"); return
    pa_pid = pal[0]['product_id'][0]; pa_qty = pal[0]['quantity']
    print(f"   PA = {m2o(pal[0]['product_id'])} qty={pa_qty}")
    # lote: via o picking vinculado a NF-1 -> move.line lot
    pk = rr('stock.picking', ['|', ('invoice_id', '=', NF1), ('invoice_ids', 'in', [NF1])], ['id'], limit=1)
    lot_id = None
    if pk:
        ml = rr('stock.move.line', [('picking_id', '=', pk[0]['id']), ('product_id', '=', pa_pid)],
                ['lot_id', 'quantity'], limit=1)
        if ml and ml[0].get('lot_id'):
            lot_id = ml[0]['lot_id'][0]
            print(f"   lote do PA = {m2o(ml[0]['lot_id'])} (picking {pk[0]['id']})")

    # 2. MO que produziu o lote
    print("\n### 2. MO que produziu o lote do PA")
    mos = []
    if lot_id:
        mos = rr('mrp.production', [('lot_producing_id', '=', lot_id)],
                 ['id', 'name', 'state', 'product_id', 'product_qty'], limit=5)
    if not mos:
        mos = rr('mrp.production', [('product_id', '=', pa_pid), ('state', '=', 'done')],
                 ['id', 'name', 'state', 'product_id', 'product_qty'], order='id desc', limit=3)
        print("   (por lote nao achou; usando MOs done do PA)")
    for m in mos:
        print(f"   MO {m['id']} {m['name']} state={m['state']} qty={m['product_qty']}")

    # 3. componentes consumidos de 31092 (recursivo nas sub-MOs)
    print(f"\n### 3. componentes consumidos de {LOC_TERCEIROS} (Materiais de Terceiros) pela(s) MO(s)")
    consumido = defaultdict(lambda: {'qty': 0.0, 'valor': 0.0})
    visit = list(mos)
    seen_mo = set()
    while visit:
        mo = visit.pop()
        if mo['id'] in seen_mo:
            continue
        seen_mo.add(mo['id'])
        raws = rr('stock.move', [('raw_material_production_id', '=', mo['id'])],
                  ['product_id', 'product_qty', 'location_id', 'state'])
        for r in raws:
            if r.get('location_id') and r['location_id'][0] == LOC_TERCEIROS:
                pid = r['product_id'][0]
                consumido[pid]['qty'] += r.get('product_qty') or 0
            # sub-MO? procurar MO cujo produto = este componente (semi produzido)
            sub = rr('mrp.production', [('product_id', '=', r['product_id'][0]), ('state', '=', 'done')],
                     ['id', 'name', 'state', 'product_qty'], limit=1)
            for s in sub:
                if s['id'] not in seen_mo:
                    visit.append(s)
    pinfo = {p['id']: p for p in rr('product.product', [('id', 'in', list(consumido))],
             ['id', 'default_code', 'name', 'type', 'standard_price'])}
    terceiros = {pid: v for pid, v in consumido.items() if pinfo.get(pid, {}).get('type') == 'product'}
    print(f"   {len(consumido)} produtos consumidos de 31092 | type=product (terceiros): {len(terceiros)}")
    for pid, v in sorted(terceiros.items(), key=lambda x: pinfo.get(x[0], {}).get('default_code') or ''):
        p = pinfo.get(pid, {})
        print(f"      [{p.get('default_code')}] {str(p.get('name'))[:30]:30} qty={round(v['qty'],5)} std={p.get('standard_price')}")

    # 4. comparar com a remessa
    print(f"\n### 4. COMPARACAO com a remessa {REMESSA} (a fonte que o s35 usa hoje)")
    rl = rr('account.move.line', [('move_id', '=', REMESSA), ('display_type', '=', 'product')], ['product_id'])
    rem_ids = {l['product_id'][0] for l in rl}
    der_ids = set(terceiros)
    print(f"   remessa={len(rem_ids)} | derivado-via-MO={len(der_ids)}")
    print(f"   na remessa mas NAO derivado: {[pinfo.get(i,{}).get('default_code') or i for i in (rem_ids-der_ids)] or 'nenhum'}")
    print(f"   derivado mas NAO na remessa: {[pinfo.get(i,{}).get('default_code') or i for i in (der_ids-rem_ids)] or 'nenhum'}")
    print(f"   {'✅ MATCH — derivacao via MO e viavel (dispensa remessa hardcoded)' if rem_ids==der_ids else '⚠️ DIVERGE — investigar'}")


if __name__ == '__main__':
    main()
