#!/usr/bin/env python3
"""Lado LF do ciclo (READ-ONLY): como a LF contabiliza hoje a ENTRADA (recebe remessa FB)
e a SAIDA/RETORNO (5124 PA + 5902 consumidos + 5903 sobras). Aterra o SOT do lado LF."""
import sys
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CMP_LF = 5
PARTNER_FB = 1   # NACOM GOYA - FB (fornecedor da LF na entrada)


def agg_move(o, move_id):
    agg = {}
    for ml in o.search_read('account.move.line', [('move_id', '=', move_id)], ['account_id', 'debit', 'credit'], limit=80):
        a = ml['account_id']; k = a[1] if a else '?'
        d, c = agg.get(k, (0, 0)); agg[k] = (d + ml['debit'], c + ml['credit'])
    return agg


def show_agg(agg, indent='       '):
    for nm, (d, c) in sorted(agg.items(), key=lambda x: -(x[1][0] + x[1][1])):
        code = nm.split(' ')[0]
        flag = '  <== TERCEIROS/COMPENS' if code.startswith(('11502', '510101', '510102')) else ''
        print(f"{indent}{code:12} D={d:>12,.2f} C={c:>12,.2f}  {nm[:38]}{flag}")


def trace_pickings(o, label, domain):
    print(f"\n{'='*92}\n{label}\n{'='*92}")
    picks = o.search_read('stock.picking', domain, ['id', 'name', 'date_done', 'picking_type_id', 'origin', 'partner_id'],
                          limit=6, order='date_done desc')
    print(f"  {len(picks)} pickings; types: {set(p['picking_type_id'][1] for p in picks if p['picking_type_id'])}")
    if not picks:
        return
    r = picks[0]
    print(f"\n  >>> TRACE {r['name']} (pt {r['picking_type_id'][1]}, origin {r.get('origin')}, partner {r['partner_id'][1] if r['partner_id'] else '-'})")
    moves = o.search_read('stock.move', [('picking_id', '=', r['id'])], ['product_id', 'location_dest_id'], limit=50)
    mv_ids = [m['id'] for m in moves]
    svls = o.search_read('stock.valuation.layer', [('stock_move_id', 'in', mv_ids)], ['value', 'account_move_id'], limit=200) if mv_ids else []
    ams = {s['account_move_id'][0] for s in svls if s['account_move_id']}
    print(f"      {len(moves)} moves, SVLs={len(svls)} valor={sum(s['value'] for s in svls):,.2f}")
    agg = {}
    for amid in list(ams)[:60]:
        for nm, (d, c) in agg_move(o, amid).items():
            dd, cc = agg.get(nm, (0, 0)); agg[nm] = (dd + d, cc + c)
    print("      >> SVL (valoracao) agregado:")
    show_agg(agg)


def main():
    o = get_odoo_connection(); o.authenticate()

    # 1) LF ENTRADA: recebe remessa da FB (pt19 ou pt64), incoming, partner FB
    trace_pickings(o, "LF ENTRADA (recebe remessa FB) — incoming, partner=FB(1)",
                   [('company_id', '=', CMP_LF), ('partner_id', '=', PARTNER_FB),
                    ('picking_type_id.code', '=', 'incoming'), ('state', '=', 'done')])

    # 2) LF SAIDA/RETORNO: outgoing para FB (pt98 ou outros), partner FB
    trace_pickings(o, "LF SAIDA/RETORNO (devolve p/ FB) — outgoing, partner=FB(1)",
                   [('company_id', '=', CMP_LF), ('partner_id', '=', PARTNER_FB),
                    ('picking_type_id.code', '=', 'outgoing'), ('state', '=', 'done')])

    # 3) NF de SAIDA da LF p/ FB (out_invoice) - a NF de retorno (5124/5902/5903)
    print(f"\n{'='*92}\nLF — NFs de SAIDA p/ FB (out_invoice) recentes — retorno industrializacao\n{'='*92}")
    nfs = o.search_read('account.move', [('company_id', '=', CMP_LF), ('partner_id', '=', PARTNER_FB),
                                         ('move_type', '=', 'out_invoice'), ('state', '=', 'posted')],
                        ['id', 'name', 'invoice_date', 'amount_untaxed', 'journal_id'], limit=5, order='invoice_date desc')
    for nf in nfs[:3]:
        print(f"\n  {nf['name']} data={nf['invoice_date']} untaxed={nf['amount_untaxed']} journal={nf['journal_id'][1] if nf['journal_id'] else '-'}")
        show_agg(agg_move(o, nf['id']), indent='     ')

    # 4) LF ENTRADA NF (in_invoice) da FB - a DFe 1901
    print(f"\n{'='*92}\nLF — NFs de ENTRADA da FB (in_invoice) recentes — remessa recebida (1901)\n{'='*92}")
    nfs2 = o.search_read('account.move', [('company_id', '=', CMP_LF), ('partner_id', '=', PARTNER_FB),
                                          ('move_type', '=', 'in_invoice'), ('state', '=', 'posted')],
                         ['id', 'name', 'invoice_date', 'amount_untaxed', 'journal_id'], limit=5, order='invoice_date desc')
    for nf in nfs2[:3]:
        print(f"\n  {nf['name']} data={nf['invoice_date']} untaxed={nf['amount_untaxed']} journal={nf['journal_id'][1] if nf['journal_id'] else '-'}")
        show_agg(agg_move(o, nf['id']), indent='     ')


if __name__ == '__main__':
    main()
