#!/usr/bin/env python3
"""E2E Etapa 1 — a SAIDA da FB ja esta correta? (READ-ONLY)

Olha remessas reais pt 53 (FB/SAI/IND, FB/Estoque -> Em Transito Ind) recentes e
mostra os account.move gerados (valoracao SVL + NF fiscal), com codes de conta.
Pergunta-alvo: os componentes caem em 1150200001 MATERIAL EM TERCEIROS, ou so saem
do estoque (3201000003 / 1150100012) sem parar em terceiros?
"""
import sys
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CMP_FB = 1
PT_FB_SAI_IND = 53
LOC_FB_ESTOQUE = 8
LOC_TRANSITO = 26489


def acc_codes(o, move_id):
    mls = o.search_read('account.move.line', [('move_id', '=', move_id)],
                        ['account_id', 'debit', 'credit'], limit=50)
    out = []
    for ml in mls:
        a = ml['account_id']
        code = a[1].split(' ')[0] if a else '?'
        out.append((code, a[1] if a else '?', ml['debit'], ml['credit']))
    return out


def main():
    o = get_odoo_connection(); o.authenticate()
    picks = o.search_read('stock.picking',
                          [('picking_type_id', '=', PT_FB_SAI_IND), ('state', '=', 'done')],
                          ['id', 'name', 'date_done', 'partner_id', 'origin'],
                          limit=5, order='date_done desc')
    print(f"Ultimas remessas pt53 done: {[(p['name'], p['date_done']) for p in picks]}")
    for pk in picks[:3]:
        print(f"\n{'='*92}\nPICKING {pk['name']} id={pk['id']} date={pk['date_done']} partner={pk['partner_id']}")
        moves = o.search_read('stock.move', [('picking_id', '=', pk['id'])],
                              ['product_id', 'product_qty', 'location_id', 'location_dest_id'], limit=50)
        print(f"  {len(moves)} stock.moves; ex: {moves[0]['location_id'][1]} -> {moves[0]['location_dest_id'][1]}" if moves else "  (sem moves)")
        # SVLs do picking -> account_move de valoracao
        mv_ids = [m['id'] for m in moves]
        svls = o.search_read('stock.valuation.layer', [('stock_move_id', 'in', mv_ids)],
                             ['value', 'account_move_id', 'product_id'], limit=200) if mv_ids else []
        print(f"  SVLs: {len(svls)} (valor total {sum(s['value'] for s in svls):,.2f})")
        amset = {}
        for s in svls:
            if s['account_move_id']:
                amset.setdefault(s['account_move_id'][0], s['account_move_id'][1])
        print(f"  >> account.moves de VALORACAO (SVL): {len(amset)}")
        for amid, amname in list(amset.items())[:2]:
            print(f"     {amname}:")
            for code, nm, d, c in acc_codes(o, amid):
                flag = '  <== TERCEIROS' if code.startswith('11502') else ''
                print(f"        {code:12} D={d:>12,.2f} C={c:>12,.2f}  {nm[:34]}{flag}")
        # NF fiscal ligada (account.move out_*) via origin/invoice_origin ou stock_move->...
        # tenta achar a NF pela origem do picking
        if pk.get('name'):
            nfs = o.search_read('account.move',
                                ['|', ('invoice_origin', '=', pk['name']), ('ref', '=', pk['name'])],
                                ['name', 'move_type', 'amount_total', 'amount_untaxed', 'state'], limit=5)
            print(f"  >> NF fiscal por origin={pk['name']}: {[(n['name'], n['move_type'], n['amount_untaxed']) for n in nfs]}")
    # saldo atual 1150200001 na FB
    acc = o.search_read('account.account', [('code', '=', '1150200001'), ('company_id', '=', CMP_FB)], ['id'], limit=1)
    if acc:
        g = o.execute_kw('account.move.line', 'read_group',
                         [[('account_id', '=', acc[0]['id']), ('parent_state', '=', 'posted')],
                          ['balance:sum'], []], {'lazy': False})
        print(f"\nSALDO 1150200001 MATERIAL EM TERCEIROS (FB, posted): {g[0]['balance'] if g else 0:,.2f}")


if __name__ == '__main__':
    main()
