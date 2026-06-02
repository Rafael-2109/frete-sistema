# etapa: orquestrador
# doc-dono: scripts/inventario_2026_05/INDEX.md
"""FLUXO B (inventario 2026-05) — 7 out_invoice FB->LF NAO transmitidas (rascunho), com
picking FB/SAI/IND done (estoque parado em Em Transito Industrializacao). Objetivo:
desfazer a saida abortada e isolar o estoque em FB/Indisponivel/MIGRAÇÃO.

3 passos por NF (dry-run obrigatorio; --confirmar para real):
  1. Cancelar a out_invoice (button_draft se posted -> button_cancel). Seguro: nenhuma
     foi autorizada na SEFAZ (verificado: XML_aut=0, sem chave, sem DFe na LF).
  2. Devolver o picking (stock.return.picking -> create_returns -> button_validate):
     Em Transito (26489) -> FB/Estoque (8).
  3. Transferir cada (lote, qty) de FB/Estoque -> FB/Indisponivel(31088)/MIGRAÇÃO via
     inventory adjustment 2 passos (action_apply_inventory) — tecnica do
     ajuste_fb_cd_indisponivel.py (reduz origem respeitando reserva + aumenta destino).

NAO inclui 682965/682828 (Fluxo C): sao o MESMO estoque destas 7 vivas (consolidada
cancelada+devolvida e re-emitida aqui). Tratar ambos tiraria 2x de FB/Estoque.

Uso:
  python scripts/inventario_2026_05/executar_fluxo_b_vivas.py            # DRY-RUN
  python scripts/inventario_2026_05/executar_fluxo_b_vivas.py --confirmar
  python scripts/inventario_2026_05/executar_fluxo_b_vivas.py --so-passo 1   # so cancelar (dry)
"""
import argparse
import os
import sys
import time
import warnings
from datetime import datetime

warnings.simplefilter('ignore')
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app  # noqa: E402
from app.odoo.services.stock_lot_service import StockLotService  # noqa: E402
from app.odoo.utils.connection import get_odoo_connection  # noqa: E402

# (invoice_id, picking_id FB/SAI/IND, NF)
VIVAS = [
    (684872, 320136, 'RPI/2026/00217'),
    (684874, 320134, 'RPI/2026/00218'),
    (684881, 320132, 'RPI/2026/00219'),
    (684885, 320142, 'RPI/2026/00220'),
    (684887, 320140, 'RPI/2026/00221'),
    (684890, 320138, 'RPI/2026/00222'),
    (684879, 320144, '(draft)'),
]

from app.odoo.constants.locations import get_local_indisponivel, get_location_id  # noqa: E402

COMPANY_FB = 1
LOC_FB_ESTOQUE = get_location_id(1)
LOC_FB_INDISP = get_local_indisponivel(1)
LOTE_MIGRACAO = 'MIGRAÇÃO'
LOTE_VAZIO = 'P-15/05'  # proxy de "sem lote" no inventario FB
CASAS = 6
TOL = 0.001


def m2o_id(x):
    return x[0] if isinstance(x, list) and x else None


def m2o_name(x):
    return x[1] if isinstance(x, list) and len(x) >= 2 else ''


def cancelar_invoice(odoo, inv_id, dry):
    mv = odoo.read('account.move', [inv_id], ['state', 'name', 'l10n_br_situacao_nf'])
    if not mv:
        return f'invoice {inv_id} nao existe'
    st, sit = mv[0]['state'], mv[0].get('l10n_br_situacao_nf')
    if st == 'cancel':
        return f'invoice {inv_id} ({mv[0]["name"]}) JA cancelada'
    if dry:
        return f'invoice {inv_id} ({mv[0]["name"]}) state={st} situacao={sit!r}: [DRY] button_draft+button_cancel'
    if st == 'posted':
        odoo.execute_kw('account.move', 'button_draft', [[inv_id]])
    odoo.execute_kw('account.move', 'button_cancel', [[inv_id]])
    return f'invoice {inv_id}: CANCELADA'


def devolver_picking(odoo, pid, dry):
    pk = odoo.read('stock.picking', [pid], ['name', 'state'])
    if not pk:
        return None, f'picking {pid} nao existe'
    if pk[0]['state'] != 'done':
        return None, f'picking {pid} state={pk[0]["state"]} (nao done)'
    ja = odoo.search_read('stock.picking',
                          [['origin', 'ilike', f'Devolução de {pk[0]["name"]}']], ['id', 'name'], limit=1)
    if ja:
        return ja[0]['id'], f'picking {pid}: devolucao JA existe ({ja[0]["name"]})'
    if dry:
        return None, f'picking {pid} ({pk[0]["name"]}): [DRY] criaria stock.return.picking -> FB/Estoque'
    ctx = {'active_id': pid, 'active_model': 'stock.picking', 'active_ids': [pid]}
    wid = odoo.execute_kw('stock.return.picking', 'create', [{'picking_id': pid}], {'context': ctx})
    odoo.execute_kw('stock.return.picking', 'write', [[wid], {}], {'context': ctx})
    res = odoo.execute_kw('stock.return.picking', 'create_returns', [[wid]], {'context': ctx})
    new_pid = res.get('res_id') if isinstance(res, dict) else res
    mls = odoo.search_read('stock.move.line', [['picking_id', '=', new_pid]], ['id', 'quantity', 'qty_done'])
    for ml in mls:
        q = float(ml.get('quantity') or 0)
        if q > 0 and float(ml.get('qty_done') or 0) != q:
            odoo.write('stock.move.line', [ml['id']], {'qty_done': q})
    try:
        odoo.execute_kw('stock.picking', 'button_validate', [[new_pid]],
                        {'context': {'skip_backorder': True, 'picking_ids_not_to_backorder': [new_pid]}})
    except Exception as e:
        if 'cannot marshal None' not in str(e):
            raise
    st = odoo.read('stock.picking', [new_pid], ['state'])[0]['state']
    return new_pid, f'picking {pid}: devolucao {new_pid} state={st}'


def itens_do_picking(odoo, pid):
    """move_lines (cod, lote_id, lote_nome, qty) que o picking moveu = o que voltara p/ FB/Estoque."""
    out = []
    mls = odoo.search_read('stock.move.line', [['picking_id', '=', pid]],
                           ['product_id', 'qty_done', 'lot_id'])
    for ml in mls:
        pidp = m2o_id(ml.get('product_id'))
        cod = ''
        if pidp:
            p = odoo.read('product.product', [pidp], ['default_code'])
            cod = p[0].get('default_code') if p else ''
        out.append({'product_id': pidp, 'cod': cod, 'qty': float(ml.get('qty_done') or 0),
                    'lot_id': m2o_id(ml.get('lot_id')), 'lote': m2o_name(ml.get('lot_id')) or LOTE_VAZIO})
    return out


def transferir_indisponivel(odoo, lot_svc, item, dry):
    """Reduz FB/Estoque(lote do item) em qty e aumenta FB/Indisponivel/MIGRAÇÃO em qty."""
    pid, qty = item['product_id'], round(item['qty'], CASAS)
    if qty <= 0:
        return f"      {item['cod']} qty<=0: skip"
    # quant origem em FB/Estoque (lote especifico do item)
    dom = [['product_id', '=', pid], ['company_id', '=', COMPANY_FB],
           ['location_id', '=', LOC_FB_ESTOQUE]]
    if item['lot_id']:
        dom.append(['lot_id', '=', item['lot_id']])
    qs = odoo.search_read('stock.quant', dom, ['id', 'quantity', 'reserved_quantity', 'lot_id'])
    livre = sum(float(q['quantity']) - float(q.get('reserved_quantity') or 0) for q in qs)
    if dry:
        return (f"      {item['cod']:>10} lote={item['lote']:<18} qty={qty:>12,.3f} "
                f"FB/Estoque_livre={livre:>12,.3f} -> FB/Indisponivel/MIGRAÇÃO "
                f"{'[OK]' if livre + TOL >= qty else '[!! SALDO INSUF]'}")
    # reduzir origem
    restante = qty
    for q in qs:
        if restante <= 0:
            break
        ql = float(q['quantity']) - float(q.get('reserved_quantity') or 0)
        consumir = min(restante, ql)
        if consumir <= 0:
            continue
        odoo.write('stock.quant', [q['id']], {'inventory_quantity': float(q['quantity']) - consumir})
        odoo.execute_kw('stock.quant', 'action_apply_inventory', [[q['id']]])
        restante -= consumir
    movido = round(qty - restante, CASAS)
    # aumentar destino MIGRAÇÃO em FB/Indisponivel
    lot_dest = lot_svc.buscar_por_nome(LOTE_MIGRACAO, pid, COMPANY_FB) or \
        lot_svc.criar_se_nao_existe(LOTE_MIGRACAO, pid, COMPANY_FB)
    dq = odoo.search_read('stock.quant',
                          [['product_id', '=', pid], ['company_id', '=', COMPANY_FB],
                           ['location_id', '=', LOC_FB_INDISP], ['lot_id', '=', lot_dest]],
                          ['id', 'quantity'])
    if dq:
        odoo.write('stock.quant', [dq[0]['id']], {'inventory_quantity': float(dq[0]['quantity']) + movido})
        odoo.execute_kw('stock.quant', 'action_apply_inventory', [[dq[0]['id']]])
    else:
        nq = odoo.create('stock.quant', {'product_id': pid, 'company_id': COMPANY_FB,
                                         'location_id': LOC_FB_INDISP, 'lot_id': lot_dest,
                                         'inventory_quantity': movido})
        odoo.execute_kw('stock.quant', 'action_apply_inventory', [[nq]])
    return f"      {item['cod']:>10} lote={item['lote']:<18} movido={movido:>12,.3f} -> Indisponivel/MIGRAÇÃO"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--confirmar', action='store_true')
    ap.add_argument('--so-passo', type=int, choices=[1, 2, 3], default=None)
    ap.add_argument('--invoices', default=None, help='CSV de invoice_ids p/ limitar (canary)')
    args = ap.parse_args()
    dry = not args.confirmar
    passos = [args.so_passo] if args.so_passo else [1, 2, 3]
    alvo = {int(x) for x in args.invoices.split(',')} if args.invoices else None
    vivas = [v for v in VIVAS if (alvo is None or v[0] in alvo)]

    app = create_app()
    with app.app_context():
        odoo = get_odoo_connection()
        lot_svc = StockLotService(odoo)
        print('=' * 92)
        print(f"  FLUXO B — {len(vivas)} NF(s) | modo={'DRY-RUN' if dry else 'REAL'} | passos={passos} | {datetime.now():%H:%M:%S}")
        print('=' * 92)
        for inv_id, pid, nf in vivas:
            print(f"\n  NF {nf} (invoice {inv_id}, picking {pid})")
            itens = itens_do_picking(odoo, pid)
            if 1 in passos:
                print('   P1', cancelar_invoice(odoo, inv_id, dry))
            if 2 in passos:
                _, msg = devolver_picking(odoo, pid, dry)
                print('   P2', msg)
            if 3 in passos:
                print('   P3 transferir FB/Estoque -> FB/Indisponivel/MIGRAÇÃO:')
                for it in itens:
                    print(transferir_indisponivel(odoo, lot_svc, it, dry))
            if not dry:
                time.sleep(1)
        print('\n' + '=' * 92)
        print(f"  {'[DRY-RUN] nada alterado.' if dry else '[REAL] concluido.'} Valide no Odoo.")


if __name__ == '__main__':
    main()
