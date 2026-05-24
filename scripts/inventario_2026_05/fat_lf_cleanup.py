"""fat_lf_cleanup.py — Fluxo de erro: devolve picking + cancela invoice + reseta ajuste.

Para NFs com quantidade errada (ou erro SEFAZ) ainda NAO transmitidas: reverte o
estoque (stock.return.picking), cancela a invoice (draft->cancel) e limpa a fase
do ajuste no ciclo FATURAMENTO_LF_2026_05_20 para reprocessamento limpo.

Uso:
  python scripts/inventario_2026_05/fat_lf_cleanup.py --pickings 320063,320065
  python scripts/inventario_2026_05/fat_lf_cleanup.py --pickings 320063,320065 --confirmar
"""
import argparse
import os
import sys
import warnings
warnings.simplefilter('ignore')
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from app import create_app, db  # noqa: E402
from app.odoo.utils.connection import get_odoo_connection  # noqa: E402

CICLO = 'FATURAMENTO_LF_2026_05_20'


def reverter_picking(odoo, pid, dry):
    """Cria devolucao (stock.return.picking) e valida, restaurando o estoque."""
    pk = odoo.read('stock.picking', [pid], ['name', 'state'])
    if not pk:
        return f'picking {pid} nao existe'
    if pk[0]['state'] != 'done':
        return f'picking {pid} state={pk[0]["state"]} (nao done — nada a reverter)'
    # ja existe devolucao?
    ja = odoo.search_read('stock.picking', [['origin', 'ilike', f'Devolução de {pk[0]["name"]}']], ['id'], limit=1)
    if ja:
        return f'picking {pid}: devolucao ja existe ({ja[0]["id"]})'
    if dry:
        return f'picking {pid} ({pk[0]["name"]}): [DRY] criaria devolucao'
    ctx = {'active_id': pid, 'active_model': 'stock.picking', 'active_ids': [pid]}
    wid = odoo.execute_kw('stock.return.picking', 'create', [{'picking_id': pid}], {'context': ctx})
    # popular product_return_moves (default_get com contexto)
    odoo.execute_kw('stock.return.picking', 'write', [[wid], {}], {'context': ctx})
    res = odoo.execute_kw('stock.return.picking', 'create_returns', [[wid]], {'context': ctx})
    # CR3#7 (2026-05-24 v4): create_returns pode retornar dict {'res_id': N},
    # int N direto, ou [N] (lista 1-id em algumas versoes Odoo CIEL IT).
    # Sincronizado com app/odoo/estoque/scripts/picking.py:devolver (v3 fix).
    if isinstance(res, dict):
        new_pid = res.get('res_id')
    elif isinstance(res, list) and len(res) == 1 and isinstance(res[0], int):
        new_pid = res[0]
    elif isinstance(res, bool):
        new_pid = None
    else:
        new_pid = res
    if not isinstance(new_pid, int) or isinstance(new_pid, bool) or new_pid <= 0:
        return (
            f'picking {pid}: create_returns retornou inesperado: res={res!r} '
            f'(esperava int > 0, dict com res_id, ou [int] de 1 elemento). '
            'Abortando antes de prosseguir.'
        )
    # validar a devolucao: setar qty_done = reserved e button_validate
    mls = odoo.search_read('stock.move.line', [['picking_id', '=', new_pid]], ['id', 'quantity', 'qty_done'])
    for ml in mls:
        q = float(ml.get('quantity') or 0)
        if q > 0 and float(ml.get('qty_done') or 0) != q:
            odoo.write('stock.move.line', [ml['id']], {'qty_done': q})
    odoo.execute_kw('stock.picking', 'button_validate', [[new_pid]],
                    {'context': {'skip_backorder': True, 'picking_ids_not_to_backorder': [new_pid]}})
    st = odoo.read('stock.picking', [new_pid], ['state'])[0]['state']
    return f'picking {pid}: devolucao {new_pid} state={st}'


def cancelar_invoice(odoo, inv_id, dry):
    mv = odoo.read('account.move', [inv_id], ['state', 'name'])
    if not mv:
        return f'invoice {inv_id} nao existe'
    st = mv[0]['state']
    if st == 'cancel':
        return f'invoice {inv_id} ja cancelada'
    if dry:
        return f'invoice {inv_id} ({mv[0]["name"]}) state={st}: [DRY] cancelaria'
    if st == 'posted':
        odoo.execute_kw('account.move', 'button_draft', [[inv_id]])
    odoo.execute_kw('account.move', 'button_cancel', [[inv_id]])
    return f'invoice {inv_id}: cancelada'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pickings', required=True, help='CSV de picking_ids a reverter')
    ap.add_argument('--confirmar', action='store_true')
    args = ap.parse_args()
    dry = not args.confirmar
    pids = [int(x) for x in args.pickings.split(',') if x.strip()]

    app = create_app()
    with app.app_context():
        from app.odoo.models.ajuste_estoque_inventario import AjusteEstoqueInventario
        odoo = get_odoo_connection()
        for pid in pids:
            print('=' * 60)
            ajs = AjusteEstoqueInventario.query.filter_by(ciclo=CICLO, picking_id_odoo=pid).all()
            inv_ids = sorted({a.invoice_id_odoo for a in ajs if a.invoice_id_odoo})
            print(f'  picking {pid}: {len(ajs)} ajustes, invoices={inv_ids}')
            # 1. reverter picking (estoque)
            print('   ', reverter_picking(odoo, pid, dry))
            # 2. cancelar invoices
            for iv in inv_ids:
                print('   ', cancelar_invoice(odoo, iv, dry))
            # 3. resetar ajustes
            if not dry:
                for a in ajs:
                    a.picking_id_odoo = None
                    a.invoice_id_odoo = None
                    a.chave_nfe = None
                    a.fase_pipeline = None
                    a.status = 'APROVADO'
                    a.erro_msg = None
                db.session.commit()
            print(f'    ajustes resetados: {len(ajs)} (status->APROVADO, fase->None)' if not dry else f'    [DRY] resetaria {len(ajs)} ajustes')


if __name__ == '__main__':
    main()
