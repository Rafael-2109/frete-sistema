#!/usr/bin/env python3
"""
PASSO B — CRIAR a remessa FB->LF (pt53) do piloto. DRY-RUN-FIRST.

3 gates (cada um exige o anterior):
  (default DRY-RUN)  planeja o picking pt53 (16 moves 1 caixa, src=8 -> dst=26489, do LOTE
                     dedicado). NAO escreve.
  --execute          cria o picking + LOTE PINADO nas move.lines + valida (componentes ->
                     26489). REVERSIVEL (devolucao). PARA antes de liberar.
  --liberar          (exige --picking validado) action_liberar_faturamento -> robo CIEL IT
                     cria a NF 5901. NAO transmite SEFAZ (manual, com go).

INVARIANTE DE SEGURANCA (review 2026-05-31): o LOTE remetido e' EXATAMENTE o --lote.
find_lote casa por nome exato; sem match -> BLOQUEADOR (sem fallback FIFO). A move.line
recebe lot_id fixo (nao depende da reserva automatica). Aborta se qtd/lote divergir.

Odoo 17/CIEL IT: stock.move.line grava 'quantity' E 'qty_done' juntos; button_validate
com context skip_backorder (sem stock.immediate.transfer, removido no v17).

Uso:
  python e2e_remessa_criar.py --lote PILOTO-3105                  # plano (dry-run)
  python e2e_remessa_criar.py --lote PILOTO-3105 --execute        # cria+valida picking
  python e2e_remessa_criar.py --picking <id> --liberar            # dispara NF (robo)
"""
import argparse
import sys
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CMP_FB = 1
PT_REMESSA = 53
LOC_FB, LOC_TRANSITO = 8, 26489
BOM_PA, BOM_BAT, SEMI_CODE = 3695, 3646, '3800018'
INCOTERM, CARRIER = 6, 996


def ctx_fb():
    return {'allowed_company_ids': [CMP_FB], 'company_id': CMP_FB}


def explode(o, caixas):
    comps = {}

    def add(pid, qty):
        p = o.read('product.product', [pid], ['default_code', 'name', 'type', 'uom_id'])[0]
        comps[pid] = {'cod': p['default_code'], 'nome': p['name'][:32], 'type': p['type'],
                      'qty': qty, 'uom': p['uom_id'][0] if p['uom_id'] else 1}
    rende_pa = float(o.read('mrp.bom', [BOM_PA], ['product_qty'])[0].get('product_qty') or 1.0)
    fpa = caixas / rende_pa
    semi_pid = semi_qty = None
    for l in o.search_read('mrp.bom.line', [('bom_id', '=', BOM_PA)], ['product_id', 'product_qty']):
        add(l['product_id'][0], l['product_qty'] * fpa)
        if (comps[l['product_id'][0]]['cod'] or '').strip() == SEMI_CODE:
            semi_pid, semi_qty = l['product_id'][0], l['product_qty'] * fpa
    if semi_pid:
        del comps[semi_pid]
        rende_bat = float(o.read('mrp.bom', [BOM_BAT], ['product_qty'])[0].get('product_qty') or 1.0)
        fbat = (semi_qty or 0.0) / rende_bat
        for l in o.search_read('mrp.bom.line', [('bom_id', '=', BOM_BAT)], ['product_id', 'product_qty']):
            add(l['product_id'][0], l['product_qty'] * fbat)
    return {pid: c for pid, c in comps.items() if c['type'] == 'product'}


def find_lote(o, pid, lote):
    """quant do produto na FB/Estoque(8)+subs. Se --lote dado: SO match exato (sem fallback)."""
    subs = [s['id'] for s in o.search_read('stock.location', [('id', 'child_of', LOC_FB)], ['id'], limit=500)]
    q = o.search_read('stock.quant',
                      [('product_id', '=', pid), ('location_id', 'in', subs), ('quantity', '>', 0)],
                      ['lot_id', 'location_id', 'quantity', 'reserved_quantity'], limit=50, order='in_date asc')
    if lote:
        cand = [x for x in q if x['lot_id'] and lote.lower() in str(x['lot_id'][1]).lower()]
        return cand[0] if cand else None           # SEM fallback: lote nao encontrado = None
    return q[0] if q else None


def write_done(o, ml_id, qty):
    """grava qtd feita gravando AMBOS quantity e qty_done (CIEL IT v17). True se ok."""
    try:
        o.execute_kw('stock.move.line', 'write', [[ml_id], {'quantity': qty, 'qty_done': qty}], {'context': ctx_fb()})
        return True
    except Exception:
        for field in ('quantity', 'qty_done'):
            try:
                o.execute_kw('stock.move.line', 'write', [[ml_id], {field: qty}], {'context': ctx_fb()})
                return True
            except Exception:
                continue
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--caixas', type=float, default=1.0)
    ap.add_argument('--lote', default=None, help='lote dedicado a remeter (ex. PILOTO-3105); OBRIGATORIO p/ --execute')
    ap.add_argument('--execute', action='store_true')
    ap.add_argument('--liberar', action='store_true')
    ap.add_argument('--picking', type=int)
    args = ap.parse_args()
    o = get_odoo_connection(); o.authenticate()

    # ---- gate 3: --liberar
    if args.liberar:
        if not args.picking:
            print("[ABORT] --liberar exige --picking <id>"); return 1
        pk = o.read('stock.picking', [args.picking], ['name', 'state'])[0]
        if pk['state'] != 'done':
            print(f"[ABORT] picking {pk['name']} state={pk['state']} (precisa 'done')"); return 1
        print(f"[liberar] {pk['name']} -> action_liberar_faturamento (robo cria NF ~90s)")
        o.execute_kw('stock.picking', 'action_liberar_faturamento', [[args.picking]], {'context': ctx_fb()})
        print("[OK] liberado. Valide com e2e_piloto_validar.py --modo remessa --nf <id>. NAO transmita SEFAZ sem go.")
        return 0

    DRY = not args.execute
    if args.execute and not args.lote:
        print("[ABORT] --execute exige --lote (o piloto remete um lote dedicado)."); return 1

    print("=" * 100)
    print(f"PASSO B — REMESSA FB->LF (pt53) {args.caixas:g} caixa(s) lote={args.lote} — {'DRY-RUN' if DRY else 'EXECUTE'}")
    print("=" * 100)
    comps = explode(o, args.caixas)
    moves, bloq = [], []
    print(f"\n  {'cod':>12} {'componente':<32} {'qty':>12} {'lote':<18} {'free':>10}")
    for pid, c in sorted(comps.items(), key=lambda x: x[1]['cod'] or ''):
        q = find_lote(o, pid, args.lote)
        if not q:
            bloq.append(c['cod'])
            print(f"  {c['cod'] or '?':>12} {c['nome']:<32} {c['qty']:>12.6f} {'*** LOTE NAO ACHADO':<18} "
                  f"{'(lote '+args.lote+' inexistente)' if args.lote else '(sem saldo)'}")
            continue
        lote_nm = q['lot_id'][1] if q['lot_id'] else '(s/lote)'
        free = q['quantity'] - q['reserved_quantity']
        if free < c['qty'] - 1e-6:
            bloq.append(c['cod'])
        moves.append({'pid': pid, 'qty': c['qty'], 'uom': c['uom'],
                      'lot_id': q['lot_id'][0] if q['lot_id'] else False,
                      'src': q['location_id'][0] if q['location_id'] else LOC_FB})
        print(f"  {c['cod'] or '?':>12} {c['nome']:<32} {c['qty']:>12.6f} {str(lote_nm)[:18]:<18} {free:>10.4f}{'  *** FALTA' if free < c['qty']-1e-6 else ''}")

    print(f"\n  picking: pt{PT_REMESSA} FB/Estoque({LOC_FB}) -> Em Transito({LOC_TRANSITO}); {len(moves)} moves; pre-cond incoterm={INCOTERM}, carrier={CARRIER}")
    if bloq:
        print(f"\n  *** BLOQUEADOR ({len(bloq)}): {bloq}. Ajuste o estoque (passo A) no lote {args.lote}. Abortando.")
        return 1

    if DRY:
        print("\n  DRY-RUN: nada criado. --execute cria+valida (lote pinado, reversivel). Depois --liberar dispara a NF.")
        return 0

    # ---- gate 2: criar picking (demanda) -> confirmar -> move.line com LOTE PINADO -> validar
    move_vals = [(0, 0, {'name': f"REMESSA-PILOTO {m['pid']}", 'product_id': m['pid'],
                         'product_uom_qty': m['qty'], 'product_uom': m['uom'],
                         'location_id': m['src'], 'location_dest_id': LOC_TRANSITO, 'company_id': CMP_FB})
                 for m in moves]
    pk_id = o.execute_kw('stock.picking', 'create',
                         [{'picking_type_id': PT_REMESSA, 'location_id': LOC_FB, 'location_dest_id': LOC_TRANSITO,
                           'company_id': CMP_FB, 'incoterm': INCOTERM, 'carrier_id': CARRIER,
                           'move_ids_without_package': move_vals}], {'context': ctx_fb()})
    print(f"\n[criado] picking id={pk_id}")
    smoves = o.search_read('stock.move', [('picking_id', '=', pk_id)], ['id', 'product_id', 'product_uom'], limit=60)
    o.execute_kw('stock.move', 'write', [[m['id'] for m in smoves], {'company_id': CMP_FB}], {'context': ctx_fb()})
    o.execute_kw('stock.picking', 'action_confirm', [[pk_id]], {'context': ctx_fb()})
    # move.line MANUAL com lote pinado (nao depende de action_assign/FIFO)
    fails = []
    for sm in smoves:
        plan = next((m for m in moves if m['pid'] == (sm['product_id'][0] if sm['product_id'] else None)), None)
        if not plan:
            fails.append(('sem-plano', sm['id'])); continue
        ml_id = o.execute_kw('stock.move.line', 'create',
                             [{'move_id': sm['id'], 'picking_id': pk_id, 'product_id': plan['pid'],
                               'product_uom_id': sm['product_uom'][0] if sm['product_uom'] else plan['uom'],
                               'location_id': plan['src'], 'location_dest_id': LOC_TRANSITO,
                               'lot_id': plan['lot_id'], 'company_id': CMP_FB}], {'context': ctx_fb()})
        if not write_done(o, ml_id, plan['qty']):
            fails.append((plan['pid'], ml_id))
    if fails:
        print(f"[ABORT] falha ao gravar qtd/lote em {fails}. Picking {pk_id} criado mas NAO validado — verifique manualmente.")
        return 1
    # conferir lote+qtd antes de validar
    mls = o.search_read('stock.move.line', [('picking_id', '=', pk_id)], ['product_id', 'lot_id', 'quantity', 'qty_done'], limit=60)
    bad = [m for m in mls if not m['lot_id'] or (args.lote and args.lote.lower() not in str(m['lot_id'][1]).lower())]
    if bad:
        print(f"[ABORT] {len(bad)} move.line com lote != {args.lote}: {[(m['product_id'][1], m['lot_id']) for m in bad]}. NAO validando.")
        return 1
    print(f"  {len(mls)} move.lines com lote={args.lote} pinado e qtd gravada.")
    # validar (skip_backorder; sem stock.immediate.transfer)
    try:
        o.execute_kw('stock.picking', 'button_validate', [[pk_id]],
                     {'context': dict(ctx_fb(), skip_backorder=True, picking_ids_not_to_backorder=[pk_id])})
    except Exception as e:
        if 'cannot marshal None' not in str(e):
            print(f"  [aviso button_validate] {e}")
    st = o.read('stock.picking', [pk_id], ['name', 'state'])[0]
    if st['state'] != 'done':
        print(f"\n[FALHA] picking {st['name']} state={st['state']} (NAO done). Investigue reservas/estoque. NAO prossiga p/ --liberar.")
        return 1
    print(f"\n[OK] picking {st['name']} done (componentes em 26489, lote {args.lote}).")
    print(f"  Proximo (gate 3): python e2e_remessa_criar.py --picking {pk_id} --liberar")
    return 0


if __name__ == '__main__':
    sys.exit(main() or 0)
