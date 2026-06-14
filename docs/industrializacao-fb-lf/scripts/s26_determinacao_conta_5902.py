#!/usr/bin/env python3
"""S26 — de onde vem a conta 1150100012 (transitoria) na linha 5902 da NF real,
e por que a minha (RETIND 1083, fp 111) caiu em 3101020002/3 (receita)? READ-ONLY.

A conta da linha = income do produto REMAPEADA por account.fiscal.position.account
(mapeamento conta_origem -> conta_destino). Compara o mapeamento das fps usadas:
  - fp 111 (SAIDA SERVICO IND) — a que usei
  - fp 89  (SAIDA RETRABALHO)  — a da SARET separada (deu 1150100012)
Mostra se 3101020002/3 -> 1150100012 esta mapeado em alguma delas.
"""
import sys
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5], 'company_id': 5, 'lang': 'pt_BR'}
FPS = {111: 'SAIDA SERVICO IND (usei)', 89: 'SAIDA RETRABALHO (SARET)'}
CONTAS_RECEITA = ['3101020002', '3101020003']
CONTA_ALVO = '1150100012'


def m2o(v):
    return f"{v[0]}|{str(v[1])[:30]}" if isinstance(v, list) and v else ('-' if not v else str(v))


def main():
    o = get_odoo_connection(); assert o.authenticate(), "FALHA AUTH"

    def rr(model, dom, fields, **kw):
        kw2 = {'fields': fields, 'context': CTX}; kw2.update(kw)
        return o.execute_kw(model, 'search_read', [dom], kw2)

    for fp_id, label in FPS.items():
        print("=" * 84)
        print(f"### fiscal.position {fp_id} — {label}")
        maps = rr('account.fiscal.position.account', [('position_id', '=', fp_id)],
                  ['account_src_id', 'account_dest_id'], limit=200)
        print(f"   {len(maps)} mapeamentos de conta (account_src -> account_dest)")
        # destinos == 1150100012 ?
        alvo = [mp for mp in maps if CONTA_ALVO in m2o(mp.get('account_dest_id'))]
        print(f"   -> mapeam p/ {CONTA_ALVO}: {len(alvo)}")
        for mp in alvo[:12]:
            print(f"        {m2o(mp.get('account_src_id'))[:40]:40} -> {m2o(mp.get('account_dest_id'))[:30]}")
        # mapeiam as contas de receita das embalagens/MP?
        for c in CONTAS_RECEITA:
            hit = [mp for mp in maps if c in m2o(mp.get('account_src_id'))]
            for mp in hit:
                print(f"   src {c}: {m2o(mp.get('account_src_id'))[:34]} -> {m2o(mp.get('account_dest_id'))}")

    # confirmar a conta de receita "natural" dos produtos de terceiros
    print("\n" + "=" * 84)
    print("### income account dos produtos de terceiros (categoria) — amostra")
    prods = rr('product.product', [('default_code', 'in', ['210030010', '104000002', '105000022'])],
               ['id', 'default_code', 'categ_id', 'property_account_income_id'])
    for p in prods:
        inc = p.get('property_account_income_id')
        cat = rr('product.category', [('id', '=', p['categ_id'][0])],
                 ['property_account_income_categ_id']) if p.get('categ_id') else []
        cinc = cat[0].get('property_account_income_categ_id') if cat else False
        print(f"   [{p['default_code']}] categ={m2o(p.get('categ_id'))[:24]} "
              f"income_prod={m2o(inc)} income_categ={m2o(cinc)}")


if __name__ == '__main__':
    main()
