#!/usr/bin/env python3
"""S46 — READ-only: VALIDA a abordagem A/B/C do Rafael p/ a fonte dos componentes da NF-2:
  A. todas as MOs do LOTE do PA + todos os componentes consumidos (recursivo nos semis)
  B. rateio = (qtd faturada na NF-1) / (total produzido do lote) x cada componente
  C. -> componentes por unidade de PA, robusto a multiplas MOs (piloto tem 3 p/ o mesmo lote)

Genealogia recursiva (propaga o rateio tambem pelos semis):
  explode(lote, fator): MOs que produziram o lote -> total T; cada componente consumido Q ->
    folha de 31092: acc += Q*fator/T ; semi: explode(lote_semi, Q*fator/T)
  inicial: explode(lote_PA, qtd_faturada)

Valor unitario = quant de 31092 (decisao Rafael: materiais de terceiros valorados pela remessa).
Compara qtd+valor com a remessa 735679 (s34: 16 itens, 279,23).
READ-ONLY. Piloto: NF-1 789484 -> PA 4870112 lote 60542.
"""
import sys
from collections import defaultdict
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5], 'company_id': 5, 'lang': 'pt_BR'}
NF1 = 789484
LOC_TERCEIROS = 31092
REMESSA = 735679


def m2o(v):
    return f"{v[0]}|{str(v[1])[:26]}" if isinstance(v, list) and v else ('-' if not v else str(v))


def main():
    o = get_odoo_connection(); assert o.authenticate(), "FALHA AUTH"

    def rr(model, dom, fields, **kw):
        kw2 = {'fields': fields, 'context': CTX}; kw2.update(kw)
        return o.execute_kw(model, 'search_read', [dom], kw2)

    acc = defaultdict(float)
    log = []

    def explode(lot_id, fator, depth=0):
        """Acumula materiais de terceiros (31092) consumidos p/ produzir `fator` un do lote."""
        mos = rr('mrp.production', [('lot_producing_id', '=', lot_id), ('state', '=', 'done')],
                 ['id', 'name', 'product_qty', 'qty_producing'])
        if not mos:
            return False   # folha (nao produzido aqui)
        total = sum((m.get('qty_producing') or m.get('product_qty') or 0) for m in mos) or 1.0
        log.append(f"{'  '*depth}lote {lot_id}: {len(mos)} MO(s) total_prod={total} fator={round(fator,5)}")
        for mo in mos:
            raws = rr('stock.move', [('raw_material_production_id', '=', mo['id']),
                                     ('state', '=', 'done')],
                     ['product_id', 'product_qty', 'location_id'])
            for r in raws:
                pid = r['product_id'][0]; q = r.get('product_qty') or 0
                # lote consumido (p/ descer no semi)
                mls = rr('stock.move.line', [('move_id', 'in',
                         [x['id'] for x in rr('stock.move', [('raw_material_production_id', '=', mo['id']),
                          ('product_id', '=', pid)], ['id'])])], ['lot_id'], limit=1)
                comp_lot = mls[0]['lot_id'][0] if (mls and mls[0].get('lot_id')) else None
                share = q * fator / total
                # e' semi? (o lote consumido foi produzido por uma MO)
                is_semi = False
                if comp_lot:
                    is_semi = explode(comp_lot, share, depth + 1)
                if not is_semi and r.get('location_id') and r['location_id'][0] == LOC_TERCEIROS:
                    acc[pid] += share
        return True

    # NF-1 -> PA + lote + qtd faturada
    pal = rr('account.move.line', [('move_id', '=', NF1), ('l10n_br_cfop_codigo', '=', '5124')],
             ['product_id', 'quantity'], limit=1)
    pa_pid = pal[0]['product_id'][0]; pa_qty = pal[0]['quantity']
    pk = rr('stock.picking', ['|', ('invoice_id', '=', NF1), ('invoice_ids', 'in', [NF1])], ['id'], limit=1)
    ml = rr('stock.move.line', [('picking_id', '=', pk[0]['id']), ('product_id', '=', pa_pid)], ['lot_id'], limit=1)
    lot_pa = ml[0]['lot_id'][0]
    print("=" * 92)
    print(f"### A/B/C: NF-1 {NF1} fatura {pa_qty} un do PA {m2o(pal[0]['product_id'])} lote {lot_pa}")
    print("=" * 92)
    explode(lot_pa, pa_qty)
    for l in log:
        print("   " + l)

    # info + valor (quant 31092)
    pinfo = {p['id']: p for p in rr('product.product', [('id', 'in', list(acc))],
             ['id', 'default_code', 'name', 'standard_price'])}
    quants = rr('stock.quant', [('location_id', '=', LOC_TERCEIROS), ('product_id', 'in', list(acc))],
                ['product_id', 'quantity', 'value'])
    qval = {}
    for qd in quants:
        pid = qd['product_id'][0]
        if qd.get('quantity'):
            qval[pid] = qd['value'] / qd['quantity']

    print(f"\n### Componentes rateados (qtd p/ {pa_qty} un) + valor unit (quant 31092)")
    total_nf2 = 0.0
    for pid, q in sorted(acc.items(), key=lambda x: pinfo.get(x[0], {}).get('default_code') or ''):
        p = pinfo.get(pid, {})
        vu = qval.get(pid, p.get('standard_price') or 0)
        sub = q * vu
        total_nf2 += sub
        print(f"   [{p.get('default_code')}] {str(p.get('name'))[:28]:28} qty={round(q,5):>9} "
              f"vu_quant={round(vu,5):>9} sub={round(sub,2)}")

    # comparar com remessa
    rl = rr('account.move.line', [('move_id', '=', REMESSA), ('display_type', '=', 'product')],
            ['product_id', 'price_subtotal'])
    rem_ids = {l['product_id'][0] for l in rl}
    rem_total = round(sum(l.get('price_subtotal') or 0 for l in rl), 2)
    der_ids = set(acc)
    print(f"\n### vs remessa {REMESSA}: itens remessa={len(rem_ids)} derivado={len(der_ids)}")
    print(f"   falta: {[pinfo.get(i,{}).get('default_code') or i for i in (rem_ids-der_ids)] or 'nenhum'}")
    print(f"   sobra: {[pinfo.get(i,{}).get('default_code') or i for i in (der_ids-rem_ids)] or 'nenhum'}")
    print(f"   {'✅ MATCH de itens' if rem_ids==der_ids else '⚠️ DIVERGE itens'} | "
          f"total derivado=R$ {round(total_nf2,2)} vs remessa=R$ {rem_total}")


if __name__ == '__main__':
    main()
