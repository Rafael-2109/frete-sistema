"""FLUXO C (inventario 2026-05) — Transferir p/ FB/Indisponivel/MIGRAÇÃO os itens das 2 NFs
canceladas UNICAS do C (sem viva correspondente; ja devolvidas via FB/DEV):

  667237 (RPI/2026/00205) -> FB/DEV/00627 (5 itens: rotulos/frascos oleo misto/molho)
  678566 (RPI/2026/00212) -> FB/DEV/00628 (1 item: 104000045 AROMA-CRAVO 12.3)

NAO inclui 682965/682828 (sao o MESMO estoque das 7 vivas ja tratadas no Fluxo B).
Le os move_lines dos FB/DEV (o que voltou p/ FB/Estoque) e transfere cada (produto,lote,qty)
de FB/Estoque(8) -> FB/Indisponivel(31088)/MIGRAÇÃO via inventory adjustment 2 passos.
Clamp ao saldo livre; nao toca saldo legitimo (transfere so a qty devolvida).

Uso:
  .venv/bin/python scripts/inventario_2026_05/transferir_fluxo_c.py            # DRY
  .venv/bin/python scripts/inventario_2026_05/transferir_fluxo_c.py --confirmar
"""
import argparse
import os
import sys
import warnings

warnings.simplefilter('ignore')
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app  # noqa: E402
from app.odoo.constants.locations import get_local_indisponivel, get_location_id  # noqa: E402
from app.odoo.services.stock_lot_service import StockLotService  # noqa: E402
from app.odoo.utils.connection import get_odoo_connection  # noqa: E402

COMPANY_FB = 1
FB_ESTOQUE = get_location_id(1)
FB_INDISP = get_local_indisponivel(1)
LOTE_MIGRACAO = 'MIGRAÇÃO'
CASAS = 6
TOL = 0.001
DEVOLUCOES = ['FB/DEV/00627', 'FB/DEV/00628']  # 667237, 678566


def m2o_id(x):
    return x[0] if isinstance(x, list) and x else None


def m2o_name(x):
    return x[1] if isinstance(x, list) and len(x) >= 2 else ''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--confirmar', action='store_true')
    args = ap.parse_args()
    dry = not args.confirmar

    app = create_app()
    with app.app_context():
        o = get_odoo_connection()
        lot_svc = StockLotService(o)
        print(f"{'='*92}\n  FLUXO C — transferir 667237+678566 -> FB/Indisponivel/MIGRAÇÃO | {'DRY' if dry else 'REAL'}\n{'='*92}")
        total = 0
        for dev_name in DEVOLUCOES:
            pks = o.search_read('stock.picking', [['name', '=', dev_name]], ['id'])
            if not pks:
                print(f"  {dev_name}: nao encontrado"); continue
            mls = o.search_read('stock.move.line', [['picking_id', '=', pks[0]['id']]],
                                ['product_id', 'qty_done', 'lot_id'])
            print(f"\n  {dev_name}: {len(mls)} itens")
            for ml in mls:
                pid = m2o_id(ml.get('product_id'))
                lot_id = m2o_id(ml.get('lot_id'))
                lote_nome = m2o_name(ml.get('lot_id')) or '(sem)'
                qty = round(float(ml.get('qty_done') or 0), CASAS)
                cod = o.read('product.product', [pid], ['default_code'])[0].get('default_code') if pid else '?'
                if qty <= 0:
                    continue
                # saldo origem FB/Estoque/lote
                dom = [['product_id', '=', pid], ['location_id', '=', FB_ESTOQUE]]
                if lot_id:
                    dom.append(['lot_id', '=', lot_id])
                qs = o.search_read('stock.quant', dom, ['id', 'quantity', 'reserved_quantity'])
                livre = sum(float(q['quantity']) - float(q.get('reserved_quantity') or 0) for q in qs)
                mov = min(qty, livre)
                flag = '[OK]' if livre + TOL >= qty else f'[CLAMP livre={livre:.3f}]'
                print(f"      {cod:>10} lote={lote_nome:<16} qty={qty:>12,.3f} FB/Estoque_livre={livre:>12,.3f} {flag}")
                if dry or mov <= 0:
                    continue
                # reduzir origem (clamp)
                restante = mov
                for q in qs:
                    if restante <= 0:
                        break
                    ql = float(q['quantity']) - float(q.get('reserved_quantity') or 0)
                    consumir = min(restante, ql)
                    if consumir <= 0:
                        continue
                    o.write('stock.quant', [q['id']], {'inventory_quantity': float(q['quantity']) - consumir})
                    o.execute_kw('stock.quant', 'action_apply_inventory', [[q['id']]])
                    restante -= consumir
                movido = round(mov - restante, CASAS)
                # aumentar destino FB/Indisponivel/MIGRAÇÃO
                lot_dest = lot_svc.buscar_por_nome(LOTE_MIGRACAO, pid, COMPANY_FB) or \
                    lot_svc.criar_se_nao_existe(LOTE_MIGRACAO, pid, COMPANY_FB)
                dq = o.search_read('stock.quant', [['product_id', '=', pid], ['location_id', '=', FB_INDISP], ['lot_id', '=', lot_dest]],
                                   ['id', 'quantity'])
                if dq:
                    o.write('stock.quant', [dq[0]['id']], {'inventory_quantity': float(dq[0]['quantity']) + movido})
                    o.execute_kw('stock.quant', 'action_apply_inventory', [[dq[0]['id']]])
                else:
                    nq = o.create('stock.quant', {'product_id': pid, 'company_id': COMPANY_FB,
                                                  'location_id': FB_INDISP, 'lot_id': lot_dest, 'inventory_quantity': movido})
                    o.execute_kw('stock.quant', 'action_apply_inventory', [[nq]])
                total += movido
                print(f"          -> movido {movido:,.3f} p/ FB/Indisponivel/MIGRAÇÃO")
        print(f"\n  {'[DRY] nada alterado.' if dry else f'[REAL] total movido p/ Indisponivel: {total:,.3f}'}")


if __name__ == '__main__':
    main()
