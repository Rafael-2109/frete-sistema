#!/usr/bin/env python3
"""
ANALISE PROFUNDA do ciclo de industrializacao FB<->LF (READ-ONLY).

Mapeia o ciclo completo via contas de compensacao 51010xx (ATIVA) / 51020xx (PASSIVA):
  PARTE 1: anatomia do razao de 5101010001 (FB) - o que DEBITA e o que CREDITA (por journal/move_type)
  PARTE 2: o RETORNO LF->FB (Etapa 5) - pickings + DFe entrada, onde os componentes caem, se 5101010001 e baixado
  PARTE 3: familia PASSIVA 51020xx - saldos e uso
  PARTE 4: lado LF - 5101010001 (LF) razao + como LF contabiliza o ciclo
  PARTE 5: amostra de documentos de retorno reais (trace completo)

Saida estruturada no stdout + JSON em /tmp/ciclo_analise.json
"""
import sys, json
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CMP_FB = 1
CMP_LF = 5
ACC_REMESSA_IND = {'FB': 22800, 'LF': 26652}   # 5101010001 REMESSA INDUSTRIALIZACAO (ATIVA)
PARTNER_LF_EM_FB = 35
LOC_FB_ESTOQUE = 8
out = {}


def grp_ledger(o, acc_id, cmp_id, by):
    """read_group de account.move.line da conta, agrupado por campo `by`."""
    return o.execute_kw('account.move.line', 'read_group',
                        [[('account_id', '=', acc_id), ('company_id', '=', cmp_id),
                          ('parent_state', '=', 'posted')],
                         ['debit:sum', 'credit:sum', 'balance:sum'], [by]],
                        {'lazy': False})


def secao(t):
    print("\n" + "=" * 96 + f"\n{t}\n" + "=" * 96)


def main():
    o = get_odoo_connection(); o.authenticate()

    # ---------------- PARTE 1: razao 5101010001 FB ----------------
    secao("PARTE 1 — Razao de 5101010001 REMESSA INDUSTRIALIZACAO (ATIVA) — FB")
    acc_fb = ACC_REMESSA_IND['FB']
    tot = o.execute_kw('account.move.line', 'read_group',
                       [[('account_id', '=', acc_fb), ('company_id', '=', CMP_FB), ('parent_state', '=', 'posted')],
                        ['debit:sum', 'credit:sum', 'balance:sum'], []], {'lazy': False})[0]
    print(f"TOTAL: D={tot['debit']:,.2f}  C={tot['credit']:,.2f}  saldo={tot['balance']:,.2f}  #={tot['__count']}")
    print("\nPor JOURNAL (o que move a conta):")
    for g in sorted(grp_ledger(o, acc_fb, CMP_FB, 'journal_id'), key=lambda x: -(x['debit'] + x['credit'])):
        j = g['journal_id'][1] if g['journal_id'] else '?'
        print(f"  {j[:46]:46s} D={g['debit']:>15,.2f} C={g['credit']:>15,.2f} #={g['__count']}")
    # quem CREDITA (a baixa rara) - amostra de linhas credit>0
    cred = o.search_read('account.move.line',
                         [('account_id', '=', acc_fb), ('company_id', '=', CMP_FB),
                          ('parent_state', '=', 'posted'), ('credit', '>', 0)],
                         ['move_id', 'credit', 'journal_id', 'date', 'name'], limit=15, order='credit desc')
    print(f"\nAmostra de CREDITOS (baixas) — {len(cred)} (top por valor):")
    for c in cred:
        print(f"  {c['date']} {c['move_id'][1][:36]:36s} C={c['credit']:>12,.2f} journal={c['journal_id'][1] if c['journal_id'] else '?'}")
    out['p1_total_fb'] = tot

    # ---------------- PARTE 2: RETORNO LF->FB (Etapa 5) ----------------
    secao("PARTE 2 — RETORNO LF->FB (Etapa 5): pickings de entrada na FB vindos da LF")
    # pickings incoming FB com partner LF, recentes, done
    rets = o.search_read('stock.picking',
                         [('company_id', '=', CMP_FB), ('partner_id', '=', PARTNER_LF_EM_FB),
                          ('picking_type_id.code', '=', 'incoming'), ('state', '=', 'done')],
                         ['id', 'name', 'date_done', 'picking_type_id', 'origin'], limit=8, order='date_done desc')
    print(f"Ultimos retornos LF->FB (done): {len(rets)}")
    pt_count = {}
    for r in rets:
        pt = r['picking_type_id'][1] if r['picking_type_id'] else '?'
        pt_count[pt] = pt_count.get(pt, 0) + 1
    print("  por picking_type:", pt_count)
    # trace 1 retorno: SVL + DFe entrada
    if rets:
        r = rets[0]
        print(f"\n>>> TRACE retorno {r['name']} (id {r['id']}, pt {r['picking_type_id'][1]}, origin {r.get('origin')})")
        moves = o.search_read('stock.move', [('picking_id', '=', r['id'])], ['product_id', 'product_qty', 'location_dest_id'], limit=50)
        print(f"    {len(moves)} moves; dest ex: {moves[0]['location_dest_id'][1] if moves else '-'}")
        mv_ids = [m['id'] for m in moves]
        svls = o.search_read('stock.valuation.layer', [('stock_move_id', 'in', mv_ids)], ['value', 'account_move_id'], limit=200) if mv_ids else []
        ams = {}
        for s in svls:
            if s['account_move_id']:
                ams.setdefault(s['account_move_id'][0], s['account_move_id'][1])
        print(f"    SVLs={len(svls)} valor={sum(s['value'] for s in svls):,.2f}  account.moves valoracao={len(ams)}")
        agg = {}
        for amid in list(ams)[:50]:
            for ml in o.search_read('account.move.line', [('move_id', '=', amid)], ['account_id', 'debit', 'credit'], limit=50):
                a = ml['account_id']; k = a[1] if a else '?'
                d, c = agg.get(k, (0, 0)); agg[k] = (d + ml['debit'], c + ml['credit'])
        print("    >> SVL agregado por conta:")
        for nm, (d, c) in sorted(agg.items(), key=lambda x: -(x[1][0] + x[1][1])):
            print(f"       {nm[:44]:44s} D={d:>12,.2f} C={c:>12,.2f}")
        # DFe entrada / NF de entrada ligada ao retorno
        nfs = o.search_read('account.move', ['|', ('invoice_origin', '=', r['name']), ('ref', 'ilike', r.get('origin') or '___nope___')],
                            ['name', 'move_type', 'amount_untaxed', 'state', 'journal_id'], limit=10)
        print(f"    >> NFs de entrada ligadas: {[(n['name'], n['move_type'], n['amount_untaxed']) for n in nfs]}")

    # ---------------- PARTE 3: PASSIVA 51020xx ----------------
    secao("PARTE 3 — Familia PASSIVA 51020xx (FB) — saldos")
    pass_accs = o.search_read('account.account', [('code', '=like', '510102%'), ('company_id', '=', CMP_FB)], ['id', 'code', 'name'], limit=40)
    for a in sorted(pass_accs, key=lambda x: x['code'])[:12]:
        g = o.execute_kw('account.move.line', 'read_group',
                         [[('account_id', '=', a['id']), ('parent_state', '=', 'posted')], ['balance:sum', 'debit:sum', 'credit:sum'], []], {'lazy': False})
        b = g[0] if g else {'balance': 0, 'debit': 0, 'credit': 0, '__count': 0}
        if b['__count']:
            print(f"  {a['code']:12} D={b['debit']:>14,.2f} C={b['credit']:>14,.2f} saldo={b['balance']:>14,.2f} #={b['__count']}  {a['name'][:30]}")

    # ---------------- PARTE 4: lado LF ----------------
    secao("PARTE 4 — 5101010001 REMESSA INDUSTRIALIZACAO (ATIVA) — LF")
    acc_lf = ACC_REMESSA_IND['LF']
    tlf = o.execute_kw('account.move.line', 'read_group',
                       [[('account_id', '=', acc_lf), ('company_id', '=', CMP_LF), ('parent_state', '=', 'posted')],
                        ['debit:sum', 'credit:sum', 'balance:sum'], []], {'lazy': False})[0]
    print(f"TOTAL LF: D={tlf['debit']:,.2f}  C={tlf['credit']:,.2f}  saldo={tlf['balance']:,.2f}  #={tlf['__count']}")
    print("Por JOURNAL:")
    for g in sorted(grp_ledger(o, acc_lf, CMP_LF, 'journal_id'), key=lambda x: -(x['debit'] + x['credit'])):
        j = g['journal_id'][1] if g['journal_id'] else '?'
        print(f"  {j[:46]:46s} D={g['debit']:>15,.2f} C={g['credit']:>15,.2f} #={g['__count']}")
    # RETORNO INDUSTRIALIZACAO (ATIVA) 5101010002 FB e LF
    secao("PARTE 4b — 5101010002 RETORNO INDUSTRIALIZACAO (ATIVA) — FB e LF")
    for lbl, cmp in [('FB', CMP_FB), ('LF', CMP_LF)]:
        a = o.search_read('account.account', [('code', '=', '5101010002'), ('company_id', '=', cmp)], ['id'], limit=1)
        if a:
            g = o.execute_kw('account.move.line', 'read_group',
                             [[('account_id', '=', a[0]['id']), ('parent_state', '=', 'posted')], ['debit:sum', 'credit:sum', 'balance:sum'], []], {'lazy': False})[0]
            print(f"  {lbl}: D={g['debit']:>14,.2f} C={g['credit']:>14,.2f} saldo={g['balance']:>14,.2f} #={g['__count']}")

    json.dump({'p1_fb': tot, 'p4_lf': tlf}, open('/tmp/ciclo_analise.json', 'w'), default=str, indent=2)
    print("\nJSON em /tmp/ciclo_analise.json")


if __name__ == '__main__':
    main()
