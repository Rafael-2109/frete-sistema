#!/usr/bin/env python3
"""G5a R1 (READ-ONLY) — qual conta a linha 1902 com op 3252 (mov_estoque=False) DEBITA?

R1 decide se o ciclo fecha no Ativo: com mov_estoque=False NAO ha stock.move/SVL,
entao a conta da linha 1902 vem da operacao/posicao fiscal/categoria — NAO da
transitoria de estoque. Se NAO for 1150100007 PA, o "Ativo->Ativo" nao acontece
automaticamente (PA nao incorpora Ic; AVCO so com S = G8).

Tenta fechar SEM criar NF:
  1. fp 88 (ENTRADA - SERVIÇO INDUSTRIALIZAÇÃO) — mapeamentos account_src->account_dest.
  2. categoria 193 (produto 4870112) na FB: contas expense/input/valuation.
  3. precedente empirico: operacoes de ENTRADA com mov_estoque=False JA usadas
     em NFs — qual conta a linha de produto debitou.
NAO escreve nada.
"""
import sys
from collections import Counter
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5]}
OP = 'l10n_br_ciel_it_account.operacao'


def m2o(v):
    if isinstance(v, list) and v:
        return f"{v[0]}|{v[1]}"
    return '-' if v is False or v is None else str(v)


def cf(v):
    return v[1].split(' - ')[0] if isinstance(v, list) and v else '-'


def main():
    o = get_odoo_connection()
    assert o.authenticate(), "FALHA AUTH"
    print(f"UID {o._uid}")

    def rr(model, domain, fields, **kw):
        kwargs = {'fields': fields, 'context': CTX}
        kwargs.update(kw)
        return o.execute_kw(model, 'search_read', [domain], kwargs)

    def rd(model, ids, fields):
        return o.execute_kw(model, 'read', [ids], {'fields': fields, 'context': CTX})

    # ====================================================================
    print("\n" + "=" * 88)
    print("1 — op 3252: TODOS os campos que possam definir/forcar conta da linha")
    print("=" * 88)
    op = rd(OP, [3252], None)[0]
    interesse = {k: v for k, v in op.items()
                 if any(t in k.lower() for t in ('account', 'conta', 'fiscal', 'cfop', 'tipo', 'movimento', 'gera'))}
    for k in sorted(interesse):
        print(f"    {k} = {m2o(interesse[k]) if isinstance(interesse[k], list) else interesse[k]}")

    # ====================================================================
    print("\n" + "=" * 88)
    print("2 — posicoes fiscais candidatas (fp 88 ENTRADA-SERVIÇO IND) + mapeamentos de conta")
    print("=" * 88)
    for fpid in (88, 25, 97, 131):
        fp = rd('account.fiscal.position', [fpid], ['id', 'name', 'company_id'])
        if not fp:
            continue
        print(f"\n  fp {fpid} {fp[0]['name']} (comp={m2o(fp[0].get('company_id'))})")
        maps = rr('account.fiscal.position.account', [('position_id', '=', fpid)],
                  ['account_src_id', 'account_dest_id'], limit=80)
        if not maps:
            print("     (sem remapeamento de conta)")
        for mp in maps:
            print(f"     {m2o(mp.get('account_src_id'))[:46]:46} -> {m2o(mp.get('account_dest_id'))}")

    # ====================================================================
    print("\n" + "=" * 88)
    print("3 — produto 4870112 / categoria: contas contabeis (expense/input/valuation) na FB")
    print("=" * 88)
    prod = rr('product.product', [('id', '=', 27834)],
              ['id', 'default_code', 'name', 'categ_id',
               'property_account_expense_id', 'property_account_income_id'], limit=1)
    if prod:
        p = prod[0]
        print(f"  product {p['id']} [{p.get('default_code')}] categ={m2o(p.get('categ_id'))}")
        print(f"    property_account_expense_id (produto) = {m2o(p.get('property_account_expense_id'))}")
        print(f"    property_account_income_id  (produto) = {m2o(p.get('property_account_income_id'))}")
        categ_id = p['categ_id'][0] if isinstance(p.get('categ_id'), list) else None
        if categ_id:
            cat = rd('product.category', [categ_id],
                     ['id', 'name', 'property_account_expense_categ_id', 'property_account_income_categ_id',
                      'property_stock_account_input_categ_id', 'property_stock_valuation_account_id',
                      'property_stock_account_output_categ_id'])
            c = cat[0]
            print(f"  categoria {categ_id} {c.get('name')} (contas company-dependent no contexto FB):")
            for k in ('property_account_expense_categ_id', 'property_account_income_categ_id',
                      'property_stock_account_input_categ_id', 'property_stock_valuation_account_id',
                      'property_stock_account_output_categ_id'):
                print(f"    {k} = {m2o(c.get(k))}")

    # ====================================================================
    print("\n" + "=" * 88)
    print("4 — PRECEDENTE EMPIRICO: operacoes de ENTRADA com mov_estoque=False ja usadas")
    print("=" * 88)
    ops_false = rr(OP, [('l10n_br_tipo_operacao', '=', 'entrada'),
                        ('l10n_br_movimento_estoque', '=', False)],
                   ['id', 'name', 'l10n_br_intra_cfop_id', 'company_id'], limit=200)
    print(f"  {len(ops_false)} operacoes de entrada com mov_estoque=False. Buscando quais foram usadas em NFs...")
    usados = []
    for op_ in ops_false:
        n = o.search_count('account.move.line', [('l10n_br_operacao_id', '=', op_['id'])])
        if n:
            usados.append((op_, n))
    usados.sort(key=lambda x: -x[1])
    print(f"  {len(usados)} delas tem uso em account.move.line. Amostra das contas debitadas:")
    for op_, n in usados[:8]:
        # amostra de linhas dessa operacao: qual conta debita
        lines = rr('account.move.line', [('l10n_br_operacao_id', '=', op_['id']), ('debit', '>', 0)],
                   ['account_id', 'l10n_br_cfop_id', 'debit'], limit=3)
        contas = Counter(m2o(ln.get('account_id'))[:40] for ln in lines)
        cfops = Counter(cf(ln.get('l10n_br_cfop_id')) for ln in lines)
        print(f"    op {op_['id']:<5} cfop={cf(op_.get('l10n_br_intra_cfop_id')):6} usos={n:<5} "
              f"| contas debitadas (amostra): {dict(contas)} cfops={dict(cfops)} | {op_['name'].strip()[:30]}")

    print("\n[FIM R1 READ-ONLY — nada foi escrito]")


if __name__ == '__main__':
    main()
