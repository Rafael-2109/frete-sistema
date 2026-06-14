#!/usr/bin/env python3
"""S23 — Ancora da SOLUCAO-alvo (nao do mecanismo manual): estrutura do ciclo de
industrializacao do shoyu 4870112, para projetar a SA que gera as 2 NFs.

READ-ONLY. Mapeia:
  1. MO do PA (mrp.production): bom_id + move_raw_ids (o que a MO REALMENTE consumiu)
  2. explosao RECURSIVA da BoM do PA ate as folhas (MP de terceiros) — deve dar 16
     (= o que a FB remeteu = o que deve voltar na NF 5902)
  3. quants de TERCEIROS: estoque de terceiros em poder da LF (Mat.Terceiros / PA
     Terceiros) — a base "por quant" sugerida pelo Rafael
  4. contas de compensacao 5101010001 (ATIVA, estoque em poder de terceiros - FB) e
     5101020001 (PASSIVA, estoque de terceiros em meu poder - LF)
"""
import sys
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5], 'company_id': 5, 'lang': 'pt_BR'}
COD_PA = '4870112'
LOCS_TERCEIROS = [31092, 31093, 30720]  # LF/Mat.Terceiros · LF/PA Terceiros · FB customer terceiros


def m2o(v):
    return f"{v[0]}|{v[1]}" if isinstance(v, list) and v else ('-' if not v else str(v))


def main():
    o = get_odoo_connection(); assert o.authenticate(), "FALHA AUTH"

    def rr(model, dom, fields, **kw):
        kw2 = {'fields': fields, 'context': CTX}; kw2.update(kw)
        return o.execute_kw(model, 'search_read', [dom], kw2)

    prod = rr('product.product', [('default_code', '=', COD_PA)], ['id', 'name', 'product_tmpl_id'], limit=1)
    pid, ptmpl = prod[0]['id'], prod[0]['product_tmpl_id'][0]
    print("=" * 88)
    print(f"=== PA {COD_PA} (product={pid} tmpl={ptmpl}) — {prod[0]['name'][:46]} ===")

    # 1) MO recente do PA
    print("\n--- 1) MO (mrp.production) recente do PA: bom + move_raw_ids consumidos ---")
    mos = rr('mrp.production', [('product_id', '=', pid)], ['id', 'name', 'state', 'bom_id', 'qty_produced'],
             order='id desc', limit=1)
    if mos:
        mo = mos[0]
        print(f"   MO {mo['id']} {mo['name']} state={mo['state']} bom={m2o(mo.get('bom_id'))} produced={mo.get('qty_produced')}")
        raws = rr('stock.move', [('raw_material_production_id', '=', mo['id'])],
                  ['product_id', 'product_uom_qty', 'quantity', 'location_id'], limit=40)
        for r in raws:
            print(f"      raw {m2o(r['product_id'])[:46]:46} consumido={r.get('quantity')} de {m2o(r.get('location_id'))[:20]}")

    # 2) explosao recursiva da BoM do PA ate folhas
    print("\n--- 2) BoM do PA EXPLODIDA recursivamente (folhas = MP de terceiros) ---")
    folhas = {}

    def explode(tmpl_id, fator, nivel):
        boms = rr('mrp.bom', ['|', ('product_tmpl_id', '=', tmpl_id), ('product_id', '=', tmpl_id)],
                  ['id', 'type', 'product_qty', 'bom_line_ids'], limit=1)
        if not boms:
            return False  # folha
        b = boms[0]
        rende = b.get('product_qty') or 1.0
        lines = rr('mrp.bom.line', [('bom_id', '=', b['id'])],
                   ['product_id', 'product_qty'], order='id')
        for ln in lines:
            cid = ln['product_id'][0]
            ctmpl = rr('product.product', [('id', '=', cid)], ['product_tmpl_id'])[0]['product_tmpl_id'][0]
            q = fator * (ln['product_qty'] / rende)
            sub = rr('mrp.bom', ['|', ('product_tmpl_id', '=', ctmpl), ('product_id', '=', cid)], ['id'], limit=1)
            if sub:
                explode(ctmpl, q, nivel + 1)
            else:
                key = m2o(ln['product_id'])
                folhas[key] = folhas.get(key, 0) + q
        return True

    explode(ptmpl, 1.0, 0)
    print(f"   {len(folhas)} folhas (MP de terceiros) — qty por 1 un de PA:")
    for k, v in sorted(folhas.items()):
        print(f"      {k[:52]:52} qty={round(v, 6)}")

    # 3) quants de terceiros (estoque de terceiros em poder da LF)
    print("\n--- 3) quants em locations de TERCEIROS (Mat.Terceiros/PA Terceiros/FB) ---")
    for loc in LOCS_TERCEIROS:
        li = rr('stock.location', [('id', '=', loc)], ['complete_name', 'usage', 'company_id'])
        if not li:
            print(f"   loc {loc}: nao existe"); continue
        qs = rr('stock.quant', [('location_id', '=', loc), ('quantity', '!=', 0)],
                ['product_id', 'quantity', 'lot_id', 'company_id'], limit=12)
        print(f"   loc {loc} {li[0]['complete_name']} usage={li[0]['usage']} company={m2o(li[0].get('company_id'))}: {len(qs)} quants nao-zero")
        for q in qs[:8]:
            print(f"      {m2o(q['product_id'])[:42]:42} qty={q['quantity']} lot={m2o(q.get('lot_id'))[:16]}")

    # 4) contas de compensacao
    print("\n--- 4) contas de compensacao (estoque em/de terceiros) ---")
    for code in ['5101010001', '5101020001']:
        accs = rr('account.account', [('code', '=', code)], ['id', 'name', 'account_type', 'company_id'])
        for a in accs:
            print(f"   {code} id={a['id']} {a['name'][:40]} type={a.get('account_type')} company={m2o(a.get('company_id'))}")


if __name__ == '__main__':
    main()
