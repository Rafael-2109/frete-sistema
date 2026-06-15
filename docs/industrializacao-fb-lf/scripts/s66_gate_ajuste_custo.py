#!/usr/bin/env python3
"""S66 — GATE-ajuste (R2.3b): postar as 2 NFs + revalorar o PA + medir + reverter.

Prova REVERSIVEL o fluxo contabil completo da entrada FB antes do POST real:
  1. alinhar preco da NF-2 a remessa (Δ0,07 -> baixa exata 279,23)
  2. postar NF-2 (j1084 -> baixa ATIVA 5101010001) + NF-1 (j1001 -> servico)
  3. revalorar o PA: wizard stock.valuation.layer.revaluation
        added_value=+Ic / account_id=CMV(3202010001) -> D 1150100007 PA / C CMV
  4. medir gate: PA=Ic+S, CMV=0, ATIVA baixada, CPV, FORNECEDORES, transit 1150100011
  5. reverter tudo (revaloracao inversa + button_draft das 2)

Modos: --plan (READ) | --alinhar | --postar | --revalorar | --medir | --reverter
PRODUCAO. j1084/j1001 hash=False (reversiveis).
"""
import sys
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1], 'company_id': 1, 'lang': 'pt_BR'}
NF2 = 791950          # insumos (j1084)
NF1 = 792219          # servico (j1001)
REMESSA = 735679      # RPI/2026/00245 (fonte canonica dos precos)
PA = 27834
ACC = {'ATIVA': 22800, 'CMV': 22611, 'CPV': 22527, 'TRANSIT': 26842,
       'PA': 22294, 'FORN': None}  # FORN resolvido on the fly
SEP = '=' * 96


def main():
    args = sys.argv[1:]
    o = get_odoo_connection(); assert o.authenticate(), 'FALHA AUTH'

    def rr(m, d, f, **kw):
        kw2 = {'fields': f, 'context': CTX}; kw2.update(kw)
        return o.execute_kw(m, 'search_read', [d], kw2)

    def rd(m, ids, f):
        return o.execute_kw(m, 'read', [list(ids)], {'fields': f, 'context': CTX})

    def saldo(conta_id):
        rg = o.execute_kw('account.move.line', 'read_group',
                          [[('account_id', '=', conta_id), ('company_id', '=', 1),
                            ('parent_state', '=', 'posted')], ['balance:sum'], []],
                          {'context': CTX})
        return round(rg[0].get('balance') or 0.0, 2) if rg else 0.0

    def pa_estado():
        p = rd('product.product', [PA], ['standard_price'])[0]
        q = rr('stock.quant', [('product_id', '=', PA), ('location_id', '=', 8)],
               ['quantity', 'value'])
        return p['standard_price'], q

    # precos da remessa (fonte canonica)
    rem = rr('account.move.line', [('move_id', '=', REMESSA), ('display_type', '=', 'product')],
             ['product_id', 'quantity', 'price_unit', 'price_subtotal'])
    rem_by_prod = {l['product_id'][0]: l for l in rem}
    ic_total = round(sum(l['price_subtotal'] for l in rem), 2)

    # ---------------- PLAN ----------------
    if not any(a in args for a in ('--alinhar', '--postar', '--revalorar', '--medir', '--reverter')):
        print(SEP); print('S66 — GATE-ajuste (plan)'); print(SEP)
        print(f"\n  Ic total (remessa, untax) = {ic_total}")
        nf2l = rr('account.move.line', [('move_id', '=', NF2), ('display_type', '=', 'product')],
                  ['product_id', 'price_unit', 'price_subtotal'])
        nf2_total = round(sum(l['price_subtotal'] for l in nf2l), 2)
        print(f"  NF-2 untax atual = {nf2_total}  (Δ vs remessa = {round(nf2_total-ic_total,2)})")
        diffs = 0
        for l in nf2l:
            pid = l['product_id'][0]; r = rem_by_prod.get(pid)
            if r and abs((l['price_unit'] or 0) - (r['price_unit'] or 0)) > 1e-9:
                diffs += 1
        print(f"  linhas NF-2 com price_unit != remessa: {diffs}/{len(nf2l)}")
        std, q = pa_estado()
        print(f"\n  PA std_price={std} quant={q}")
        print(f"  saldos: ATIVA(5101010001)={saldo(ACC['ATIVA'])} CMV(3202010001)={saldo(ACC['CMV'])} "
              f"CPV(3201000001)={saldo(ACC['CPV'])} TRANSIT(1150100011)={saldo(ACC['TRANSIT'])}")
        gj = rr('account.journal', [('company_id', '=', 1), ('type', '=', 'general')],
                ['id', 'name', 'code'], limit=10)
        print(f"\n  journals general FB (p/ revaloracao): {[(j['id'], j['code']) for j in gj]}")
        # wizard model existe + metodos
        try:
            wf = o.execute_kw('stock.valuation.layer.revaluation', 'fields_get', [],
                              {'attributes': ['string', 'required'], 'context': CTX})
            req = [k for k in wf if wf[k].get('required')]
            print(f"  wizard revaluation campos required: {req}")
        except Exception as e:
            print(f"  wizard: {str(e)[:120]}")
        print('\n  Proximo: --alinhar -> --postar -> --revalorar -> --medir -> --reverter')
        print(SEP); return

    # ---------------- ALINHAR preco NF-2 ----------------
    if '--alinhar' in args:
        nf2l = rr('account.move.line', [('move_id', '=', NF2), ('display_type', '=', 'product')],
                  ['id', 'product_id', 'price_unit'])
        st = rd('account.move', [NF2], ['state'])[0]['state']
        if st != 'draft':
            print(f'  NF-2 nao esta draft ({st}) — abort'); return
        n = 0
        for l in nf2l:
            r = rem_by_prod.get(l['product_id'][0])
            if r and abs((l['price_unit'] or 0) - r['price_unit']) > 1e-9:
                o.execute_kw('account.move.line', 'write', [[l['id']], {'price_unit': r['price_unit']}], {'context': CTX})
                n += 1
        nf2l2 = rr('account.move.line', [('move_id', '=', NF2), ('display_type', '=', 'product')],
                   ['price_subtotal'])
        print(f"  [ALINHAR] {n} linhas ajustadas. NF-2 untax agora = {round(sum(l['price_subtotal'] for l in nf2l2),2)} (alvo {ic_total})")
        return

    def move_lines(inv):
        mls = rr('account.move.line', [('move_id', '=', inv)],
                 ['account_id', 'debit', 'credit'])
        agg = {}
        for l in mls:
            a = l['account_id'][1] if l.get('account_id') else '(sem)'
            d, c = agg.get(a, (0, 0)); agg[a] = (round(d+l['debit'], 2), round(c+l['credit'], 2))
        return agg

    # ---------------- POSTAR as 2 ----------------
    if '--postar' in args:
        a0 = saldo(ACC['ATIVA'])
        print(f"  ATIVA antes = {a0}")
        for inv, tag in [(NF2, 'NF-2 insumos'), (NF1, 'NF-1 servico')]:
            st = rd('account.move', [inv], ['state'])[0]['state']
            if st == 'posted':
                print(f"  {tag} ({inv}) JA posted"); continue
            o.execute_kw('account.move', 'action_post', [[inv]], {'context': CTX})
            m = rd('account.move', [inv], ['name', 'state', 'amount_total', 'amount_untaxed'])[0]
            print(f"  {tag} ({inv}) POST: {m['name']} state={m['state']} untax={m['amount_untaxed']} total={m['amount_total']}")
            print(f"    lancamento: {move_lines(inv)}")
        a1 = saldo(ACC['ATIVA'])
        print(f"  ATIVA depois = {a1}  (Δ = {round(a1-a0,2)})  [esperado -279,23 = baixa]")
        return

    # ---------------- REVALORAR o PA (+Ic, contrapartida CMV) ----------------
    if '--revalorar' in args:
        comp = rd('res.company', [1], ['currency_id'])[0]
        cur = comp['currency_id'][0]
        c0 = saldo(ACC['CMV']); pstd0, pq0 = pa_estado()
        print(f"  antes: PA std={pstd0} quant={pq0} CMV={c0}")
        wid = o.execute_kw('stock.valuation.layer.revaluation', 'create',
                           [{'company_id': 1, 'currency_id': cur, 'product_id': PA,
                             'added_value': ic_total, 'account_id': ACC['CMV'],
                             'account_journal_id': 8,
                             'reason': 'Ic industrializacao retorno PILOTO 4870112 (GATE)'}],
                           {'context': CTX})
        print(f"  wizard revaluation criado id={wid}")
        o.execute_kw('stock.valuation.layer.revaluation', 'action_validate_revaluation', [[wid]], {'context': CTX})
        c1 = saldo(ACC['CMV']); pstd1, pq1 = pa_estado()
        print(f"  depois: PA std={pstd1} quant={pq1} CMV={c1} (Δ CMV={round(c1-c0,2)})")
        # SVL da revaloracao
        svl = rr('stock.valuation.layer', [('product_id', '=', PA)],
                 ['id', 'value', 'description'], limit=2, order='id desc')
        print(f"  SVLs recentes do PA: {svl}")
        return

    # ---------------- MEDIR gate ----------------
    if '--medir' in args:
        std, q = pa_estado()
        print(SEP); print('GATE — medicao'); print(SEP)
        print(f"  PA std_price={std} quant={q}  (alvo Ic+S ~305,46)")
        for k in ('ATIVA', 'CMV', 'CPV', 'TRANSIT'):
            print(f"  {k} ({ACC[k]}) saldo = {saldo(ACC[k])}")
        for inv, tag in [(NF2, 'NF-2'), (NF1, 'NF-1')]:
            print(f"  {tag} lancamento: {move_lines(inv)}")
        return

    # ---------------- REVERTER (revaloracao inversa + draft) ----------------
    if '--reverter' in args:
        comp = rd('res.company', [1], ['currency_id'])[0]; cur = comp['currency_id'][0]
        # revaloracao inversa -Ic
        wid = o.execute_kw('stock.valuation.layer.revaluation', 'create',
                           [{'company_id': 1, 'currency_id': cur, 'product_id': PA,
                             'added_value': -ic_total, 'account_id': ACC['CMV'],
                             'account_journal_id': 8, 'reason': 'REVERTE GATE Ic PILOTO'}],
                           {'context': CTX})
        o.execute_kw('stock.valuation.layer.revaluation', 'action_validate_revaluation', [[wid]], {'context': CTX})
        print(f"  revaloracao inversa aplicada (wizard {wid}, -{ic_total})")
        for inv, tag in [(NF1, 'NF-1'), (NF2, 'NF-2')]:
            st = rd('account.move', [inv], ['state'])[0]['state']
            if st == 'posted':
                o.execute_kw('account.move', 'button_draft', [[inv]], {'context': CTX})
                print(f"  {tag} ({inv}) -> draft")
        std, q = pa_estado()
        print(f"  PA restaurado: std={std} quant={q}")
        print(f"  ATIVA={saldo(ACC['ATIVA'])} CMV={saldo(ACC['CMV'])}")
        return


if __name__ == '__main__':
    main()
