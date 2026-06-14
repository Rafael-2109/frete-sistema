#!/usr/bin/env python3
"""S34 — READ-only: casar os 16 insumos de terceiros (fonte da NF-2) com o PRICE da
REMESSA do piloto (RPI/2026/00245 = move 735679, CFOP 5901). Invariante 5902=5901:
o price_unit do retorno = o price_unit da remessa. Substitui o standard_price de teste.

Mostra, p/ cada um dos 16:
  - qty da BoM explodida (1 PA) | price remessa | price standard | subtotal remessa
  - quais batem entre BoM e remessa; faltantes/sobrantes
  - total da remessa (deve ~= 279,23 = D 5101010001 da Etapa 1)

READ-ONLY.
"""
import sys
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5], 'company_id': 5, 'lang': 'pt_BR'}
COD_PA = '4870112'
REMESSA = 735679   # RPI/2026/00245 (Etapa 1, FB->LF)


def explode_bom(rr, tmpl_id, fator, folhas):
    boms = rr('mrp.bom', ['|', ('product_tmpl_id', '=', tmpl_id), ('product_id', '=', tmpl_id)],
              ['id', 'product_qty'], limit=1)
    if not boms:
        return
    rende = boms[0].get('product_qty') or 1.0
    lines = rr('mrp.bom.line', [('bom_id', '=', boms[0]['id'])], ['product_id', 'product_qty'], order='id')
    for ln in lines:
        cid = ln['product_id'][0]
        ctmpl = rr('product.product', [('id', '=', cid)], ['product_tmpl_id'])[0]['product_tmpl_id'][0]
        q = fator * (ln['product_qty'] / rende)
        sub = rr('mrp.bom', ['|', ('product_tmpl_id', '=', ctmpl), ('product_id', '=', cid)], ['id'], limit=1)
        if sub:
            explode_bom(rr, ctmpl, q, folhas)
        else:
            folhas[cid] = folhas.get(cid, 0.0) + q


def main():
    o = get_odoo_connection(); assert o.authenticate(), "FALHA AUTH"

    def rr(model, dom, fields, **kw):
        kw2 = {'fields': fields, 'context': CTX}; kw2.update(kw)
        return o.execute_kw(model, 'search_read', [dom], kw2)

    # remessa
    rem = rr('account.move', [('id', '=', REMESSA)], ['name', 'state', 'amount_untaxed', 'amount_total'])
    print("=" * 96)
    print(f"### REMESSA {REMESSA} = {rem[0]['name'] if rem else '?'} "
          f"state={rem[0]['state'] if rem else '?'} untax={rem[0].get('amount_untaxed') if rem else '?'}")
    rlines = rr('account.move.line', [('move_id', '=', REMESSA), ('display_type', '=', 'product')],
                ['product_id', 'l10n_br_cfop_codigo', 'quantity', 'price_unit', 'price_subtotal'], order='id')
    rem_by_prod = {l['product_id'][0]: l for l in rlines}
    print(f"   {len(rlines)} linhas na remessa (cfops={sorted(set(str(l.get('l10n_br_cfop_codigo')) for l in rlines))})")

    # fonte (16 terceiros)
    prod = rr('product.product', [('default_code', '=', COD_PA)], ['id', 'product_tmpl_id'], limit=1)
    folhas = {}
    explode_bom(rr, prod[0]['product_tmpl_id'][0], 1.0, folhas)
    pinfo = {p['id']: p for p in rr('product.product', [('id', 'in', list(folhas))],
             ['id', 'default_code', 'name', 'type', 'standard_price'])}
    terceiros = {pid: q for pid, q in folhas.items() if pinfo.get(pid, {}).get('type') == 'product'}

    print(f"\n### CASAMENTO 16 insumos (BoM) × remessa (price_unit invariante 5902=5901)")
    print(f"   {'cod':>10} {'nome':32} {'qty_bom':>10} {'price_rem':>11} {'price_std':>11} {'sub_rem':>10}")
    tot_rem_match = 0.0
    sem_remessa = []
    for pid, q in sorted(terceiros.items(), key=lambda x: pinfo.get(x[0], {}).get('default_code') or ''):
        p = pinfo.get(pid, {})
        rl = rem_by_prod.get(pid)
        price_rem = rl['price_unit'] if rl else None
        sub = round((price_rem or 0) * q, 2)
        if rl:
            tot_rem_match += sub
        else:
            sem_remessa.append(p.get('default_code'))
        print(f"   {str(p.get('default_code')):>10} {str(p.get('name'))[:32]:32} {round(q,5):>10} "
              f"{('-' if price_rem is None else round(price_rem,6)):>11} {round(p.get('standard_price') or 0,4):>11} "
              f"{('-' if rl is None else sub):>10}")

    bom_ids = set(terceiros)
    rem_ids = set(rem_by_prod)
    print(f"\n   insumos da BoM SEM linha na remessa: {sem_remessa or 'nenhum'}")
    print(f"   produtos na remessa que NAO sao insumos-terceiros da BoM: "
          f"{sorted(pinfo.get(i,{}).get('default_code') or i for i in (rem_ids - bom_ids)) or 'nenhum'}")
    print(f"   total NF-2 c/ price=remessa (so casados) ~= R$ {round(tot_rem_match,2)} "
          f"(remessa untax={rem[0].get('amount_untaxed') if rem else '?'})")


if __name__ == '__main__':
    main()
