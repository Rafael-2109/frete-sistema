#!/usr/bin/env python3
"""
TESTE LEVER SAIDA FB — valida que setar valuation_in/out na location de transito
26489 (Em Transito Industrializacao) faz a remessa FB->26489 lancar em TERCEIROS:

    saida FB->26489 (forward):  D 1150200001 MATERIAL EM TERCEIROS / C 1150100002 (estoque)
    retorno 26489->FB (reverse): D 1150100002 (estoque) / C 1150200001  [restaura, net-zero]

So' a industrializacao passa por 26489 (pt52/53/64/98) -> nao afeta venda normal.
Movimento via picking INTERNO pt5 (sem NF). Cobaia: ROTULO 210030322 (piloto), 10 un.

SEGURANCA:
  - --dry-run DEFAULT: nao escreve nada.
  - --execute: try/finally SEMPRE reverte a config da location (valuation_in/out->False)
    e reporta o estado do estoque (reverso 26489->FB restaura o saldo).
  - Janela com a 26489 configurada com conta FB e' de segundos (risco: move LF
    concorrente pela 26489 -> conta cross-company; improvavel).

Uso:
    source .venv/bin/activate
    python docs/industrializacao-fb-lf/scripts/teste_lever_saida_fb.py            # dry-run
    python docs/industrializacao-fb-lf/scripts/teste_lever_saida_fb.py --execute  # real (com go)
"""
import argparse
import sys
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CMP_FB = 1
LOC_FB = 8
LOC_TRANSITO = 26489
PT_FB_INTERNO = 5
PROD = 28236            # ROTULO - MOLHO SHOYU PET 1,01 L (210030322)
ACC_TERC = 22296        # 1150200001 MATERIAL EM TERCEIROS (FB)
ACC_ESTOQUE = 22289     # 1150100002 MATERIAL DE EMBALAGEM (FB) — valoracao da categ 75
DRY = True


def ctx():
    return {'allowed_company_ids': [CMP_FB], 'company_id': CMP_FB}


def loc_accounts(o):
    return o.execute_kw('stock.location', 'read',
                        [[LOC_TRANSITO], ['valuation_in_account_id', 'valuation_out_account_id']], {})[0]


def set_loc_accounts(o, in_acc, out_acc):
    o.execute_kw('stock.location', 'write',
                 [[LOC_TRANSITO], {'valuation_in_account_id': in_acc,
                                   'valuation_out_account_id': out_acc}], {'context': ctx()})


def quant_fb(o):
    q = o.search_read('stock.quant', [('product_id', '=', PROD), ('location_id', '=', LOC_FB)],
                      ['quantity'], limit=1)
    return q[0]['quantity'] if q else 0.0


def do_transfer(o, src, dst, qty, uom=1):
    """Cria picking interno pt5 src->dst, valida (stock only), retorna picking_id."""
    pick = o.execute_kw('stock.picking', 'create',
                        [{'picking_type_id': PT_FB_INTERNO, 'location_id': src, 'location_dest_id': dst,
                          'company_id': CMP_FB,
                          'move_ids_without_package': [(0, 0, {
                              'name': 'TESTE-LEVER-FB', 'product_id': PROD, 'product_uom_qty': qty,
                              'product_uom': uom, 'location_id': src, 'location_dest_id': dst,
                              'company_id': CMP_FB})]}], {'context': ctx()})
    o.execute_kw('stock.picking', 'action_confirm', [[pick]], {'context': ctx()})
    o.execute_kw('stock.picking', 'action_assign', [[pick]], {'context': ctx()})
    # setar qty_done nas move lines (campo reservado nesta versao = 'quantity')
    mls = o.search_read('stock.move.line', [('picking_id', '=', pick)], ['id', 'quantity'], limit=20)
    if mls:
        for ml in mls:
            o.execute_kw('stock.move.line', 'write', [[ml['id']], {'qty_done': ml.get('quantity') or qty}], {'context': ctx()})
    else:
        mv = o.search_read('stock.move', [('picking_id', '=', pick)], ['id'], limit=5)
        o.execute_kw('stock.move.line', 'create',
                     [{'move_id': mv[0]['id'], 'picking_id': pick, 'product_id': PROD,
                       'product_uom_id': uom, 'location_id': src, 'location_dest_id': dst,
                       'qty_done': qty, 'company_id': CMP_FB}], {'context': ctx()})
    # validar
    try:
        res = o.execute_kw('stock.picking', 'button_validate', [[pick]], {'context': ctx()})
        if isinstance(res, dict) and res.get('res_model') == 'stock.immediate.transfer':
            wiz = o.execute_kw('stock.immediate.transfer', 'create',
                               [{'pick_ids': [(6, 0, [pick])]}], {'context': ctx()})
            o.execute_kw('stock.immediate.transfer', 'process', [[wiz]], {'context': ctx()})
    except Exception as e:
        if 'cannot marshal None' not in str(e):
            raise
    return pick


def acc_move_for_picking(o, pick):
    mv = o.search_read('stock.move', [('picking_id', '=', pick)], ['id'], limit=10)
    mv_ids = [m['id'] for m in mv]
    svl = o.search_read('stock.valuation.layer', [('stock_move_id', 'in', mv_ids)],
                        ['value', 'account_move_id'], limit=10) if mv_ids else []
    lines = []
    amname = None
    for s in svl:
        if s['account_move_id']:
            amname = s['account_move_id'][1]
            mls = o.search_read('account.move.line', [('move_id', '=', s['account_move_id'][0])],
                                ['account_id', 'debit', 'credit'], limit=20)
            for ml in mls:
                a = ml['account_id']
                lines.append((a[0] if a else None, a[1] if a else '?', ml['debit'], ml['credit']))
    return amname, lines, sum(s['value'] for s in svl)


def has(lines, acc_id, side):
    return any(aid == acc_id and (deb if side == 'D' else cre) > 0 for aid, _, deb, cre in lines)


def show(amname, lines, val):
    print(f"    move={amname} valorSVL={val:,.4f}")
    for aid, nm, d, c in lines:
        flag = '  <== TERCEIROS' if aid == ACC_TERC else ''
        print(f"      {str(aid):>6} {nm[:36]:36s} D={d:>10,.2f} C={c:>10,.2f}{flag}")


def main():
    global DRY
    ap = argparse.ArgumentParser()
    ap.add_argument('--execute', action='store_true')
    ap.add_argument('--qty', type=float, default=10.0)
    args = ap.parse_args()
    DRY = not args.execute
    qty = args.qty

    o = get_odoo_connection()
    if not o.authenticate():
        raise SystemExit("Falha auth Odoo")

    print("=" * 92)
    print(f"TESTE LEVER SAIDA FB — {'DRY-RUN' if DRY else 'EXECUTE (real)'} | cobaia ROTULO 210030322 qty={qty}")
    print("=" * 92)
    snap = loc_accounts(o)
    saldo0 = quant_fb(o)
    print(f"[1] SNAPSHOT location 26489: valuation_in={snap['valuation_in_account_id']} "
          f"valuation_out={snap['valuation_out_account_id']}")
    print(f"    saldo FB/Estoque do ROTULO: {saldo0}")
    print(f"[2] PLANO: set 26489.valuation_in/out = {ACC_TERC} (1150200001) "
          f"-> transfer FB->26489 {qty}un -> esperar D 1150200001 / C 1150100002 -> reverter")

    if DRY:
        print("\nDRY-RUN: nada escrito. --execute para validar (try/finally restaura config+estoque).")
        return

    resultado = {'forward_ok': None, 'reverse_ok': None, 'config_revertida': None, 'saldo_restaurado': None}
    fwd = rev = None
    try:
        print(f"\n[3] set 26489.valuation_in/out = {ACC_TERC}")
        set_loc_accounts(o, ACC_TERC, ACC_TERC)
        print(f"[4] FORWARD transfer FB({LOC_FB}) -> 26489 ({qty} un)...")
        fwd = do_transfer(o, LOC_FB, LOC_TRANSITO, qty)
        amn, lines, val = acc_move_for_picking(o, fwd)
        show(amn, lines, val)
        resultado['forward_ok'] = has(lines, ACC_TERC, 'D') and has(lines, ACC_ESTOQUE, 'C')

        print(f"\n[5] REVERSE transfer 26489 -> FB({LOC_FB}) ({qty} un, restaura)...")
        rev = do_transfer(o, LOC_TRANSITO, LOC_FB, qty)
        amn2, lines2, val2 = acc_move_for_picking(o, rev)
        show(amn2, lines2, val2)
        resultado['reverse_ok'] = has(lines2, ACC_ESTOQUE, 'D') and has(lines2, ACC_TERC, 'C')
    finally:
        print(f"\n[6] LIMPEZA (try/finally)")
        # cancelar pickings nao-done (orfaos de falha)
        for tag, pk in (('forward', fwd), ('reverse', rev)):
            if not pk:
                continue
            try:
                st = o.read('stock.picking', [pk], ['state'])[0]['state']
                if st != 'done':
                    o.execute_kw('stock.picking', 'action_cancel', [[pk]], {'context': ctx()})
                    print(f"    picking {tag}={pk} estava '{st}' -> cancelado")
            except Exception as e:
                if 'cannot marshal None' not in str(e):
                    print(f"    aviso cancelar {tag}={pk}: {e}")
        try:
            set_loc_accounts(o, False, False)
            back = loc_accounts(o)
            resultado['config_revertida'] = (not back['valuation_in_account_id'] and not back['valuation_out_account_id'])
            print(f"    location 26489 restaurada: in={back['valuation_in_account_id']} out={back['valuation_out_account_id']}")
        except Exception as e:
            print(f"    ERRO ao restaurar config: {e} — RESTAURAR MANUALMENTE 26489 valuation_in/out=False")
        saldo_fim = quant_fb(o)
        resultado['saldo_restaurado'] = (abs(saldo_fim - saldo0) < 0.001)
        print(f"    saldo FB: inicial={saldo0} final={saldo_fim} {'OK' if resultado['saldo_restaurado'] else 'CONFERIR (26489 pode ter saldo)'}")
        if fwd:
            print(f"    pickings teste: forward={fwd} reverse={rev}")

    print("\n" + "=" * 92)
    print("RESULTADO:", resultado)
    print("saida FB -> terceiros (D 1150200001 / C 1150100002):", '✅' if resultado['forward_ok'] else '❌/NA')
    print("reverso net-zero (D 1150100002 / C 1150200001)      :", '✅' if resultado['reverse_ok'] else '❌/NA')
    print("=" * 92)


if __name__ == '__main__':
    main()
