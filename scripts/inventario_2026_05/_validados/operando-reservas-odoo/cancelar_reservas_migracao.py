# etapa: validado
# doc-dono: scripts/inventario_2026_05/INDEX.md
"""Cancela reservas em lote MIGRACAO* nos quants listados em
/tmp/migracao_mover_pulados.csv (gerado pelo mover_migracao_para_indisponivel.py).

Para cada quant pulado por reserva:
  1. Identifica stock.move.line com qty_done=0 que reservam o quant
     (filtro: product_id + location_id + lot_id + state in [assigned,
     partially_available, confirmed, waiting] + company_id).
  2. Coleta picking_ids unicos.
  3. Chama stock.picking.do_unreserve nesses pickings (cancela apenas
     reservas pendentes — qty_done>0 nao e afetado).

Depois disso, o operador da MO precisara fazer 'Check Availability'
para reservar outros lotes no mesmo local. Ver discussao em sessao.

Uso:
    python scripts/inventario_2026_05/cancelar_reservas_migracao.py
    python scripts/inventario_2026_05/cancelar_reservas_migracao.py --confirmar
"""
import argparse
import csv
import logging
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Set

_THIS = Path(__file__).resolve()
# ARQUIVADO 2026-05-23 — movido para _validados/operando-reservas-odoo/ (2 niveis abaixo).
# parents[2] (era repo root) → parents[4] após o move. Skill substituta: operando-reservas-odoo.
# 'monitor' tambem precisa subir 2 niveis (ainda no inventario_2026_05/monitor/).
sys.path.insert(0, str(_THIS.parents[4]))
sys.path.insert(0, str(_THIS.parents[2] / 'monitor'))

from _comum import m2o_id, m2o_name  # type: ignore  # noqa: E402

from app import create_app  # noqa: E402  # type: ignore
from app.odoo.utils.connection import get_odoo_connection  # noqa: E402  # type: ignore

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-7s %(name)s | %(message)s',
)
logger = logging.getLogger('cancelar_reservas')

COMPANY_NAME = {1: 'FB', 4: 'CD', 5: 'LF'}
CSV_PULADOS_DEFAULT = '/tmp/migracao_mover_pulados.csv'
CSV_LOG_DEFAULT = '/tmp/cancelar_reservas_log.csv'


def banner(t, c='='):
    print()
    print(c * 90)
    print(f'  {t}')
    print(c * 90)


def ler_pulados(path: str) -> List[Dict[str, Any]]:
    out = []
    with open(path) as f:
        r = csv.DictReader(f)
        for row in r:
            try:
                row['product_id'] = int(row['product_id'])
                row['lot_id'] = int(row['lot_id'])
                row['location_id'] = int(row['location_id'])
                row['company_id'] = int(row['company_id'])
                row['qty'] = float(row['qty'])
                row['reservada'] = float(row['reservada'])
                row['quant_id'] = int(row['quant_id'])
                out.append(row)
            except (ValueError, KeyError) as e:
                logger.warning(f'pula linha invalida: {e} -> {row}')
    return out


def buscar_move_lines_reservando(odoo, pulados: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Para cada quant pulado, busca stock.move.line com qty_done=0 que reservam.

    Retorna lista de dicts {move_line_id, picking_id, picking_name, move_id,
    product_id, default_code, lot_id, lot_name, location_id, location_name,
    qty_reservada, state, picking_type_name, origin}.
    """
    log = []
    for q in pulados:
        ml_ids = odoo.search('stock.move.line', [
            ('product_id', '=', q['product_id']),
            ('location_id', '=', q['location_id']),
            ('lot_id', '=', q['lot_id']),
            ('qty_done', '=', 0),
            ('state', 'in', ['confirmed', 'waiting', 'partially_available', 'assigned']),
            ('company_id', '=', q['company_id']),
        ])
        if not ml_ids:
            continue
        lines = odoo.read('stock.move.line', ml_ids, [
            'id', 'picking_id', 'move_id', 'quantity',
            'qty_done', 'state', 'lot_id',
        ])
        for ln in lines:
            log.append({
                'quant_id': q['quant_id'],
                'filial': q['filial'],
                'product_id': q['product_id'],
                'default_code': q.get('default_code', ''),
                'product_name': q.get('product_name', ''),
                'lot_id': q['lot_id'],
                'lot_name': q.get('lot_name', ''),
                'location_id': q['location_id'],
                'location_name': q.get('location_name', ''),
                'qty_quant': q['qty'],
                'qty_reservada': q['reservada'],
                'move_line_id': ln['id'],
                'picking_id': m2o_id(ln.get('picking_id')) or '',
                'picking_name': m2o_name(ln.get('picking_id')),
                'move_id': m2o_id(ln.get('move_id')) or '',
                'quantity_ml': ln.get('quantity') or 0,
                'state': ln.get('state'),
            })
    # enriquece picking_type + origin
    picking_ids = list({l['picking_id'] for l in log if l['picking_id']})
    pmap: Dict[int, Dict[str, Any]] = {}
    if picking_ids:
        for i in range(0, len(picking_ids), 200):
            batch = picking_ids[i:i + 200]
            data = odoo.read('stock.picking', list(batch),
                             ['id', 'picking_type_id', 'origin', 'state'])
            for p in data:
                pmap[p['id']] = {
                    'picking_type_name': m2o_name(p.get('picking_type_id')),
                    'origin': p.get('origin') or '',
                    'picking_state': p.get('state'),
                }
    for ln in log:
        pid = ln['picking_id']
        meta = pmap.get(pid) if pid else None
        if meta:
            ln['picking_type_name'] = meta['picking_type_name']
            ln['origin'] = meta['origin']
            ln['picking_state'] = meta['picking_state']
        else:
            ln['picking_type_name'] = ''
            ln['origin'] = ''
            ln['picking_state'] = ''
    return log


def imprimir_resumo(log: List[Dict[str, Any]]):
    if not log:
        print('  Nenhuma stock.move.line de reserva encontrada para os quants pulados.')
        return
    pickings: Dict[int, Dict[str, Any]] = {}
    for ln in log:
        pid = ln['picking_id']
        if not pid:
            continue
        if pid not in pickings:
            pickings[pid] = {
                'name': ln['picking_name'],
                'type': ln['picking_type_name'],
                'origin': ln['origin'],
                'state': ln['picking_state'],
                'n_lines': 0,
                'qty_total': 0.0,
                'filiais': set(),
            }
        pickings[pid]['n_lines'] += 1
        pickings[pid]['qty_total'] += float(ln['quantity_ml'])
        pickings[pid]['filiais'].add(ln['filial'])

    print(f'\n  {len(log)} stock.move.line de reserva → {len(pickings)} pickings unicos')

    # Resumo por tipo
    by_type: Dict[str, Dict[str, Any]] = defaultdict(lambda: {'n_pickings': 0, 'n_lines': 0, 'qty': 0.0})
    for pid, p in pickings.items():
        t = p['type'] or '(sem tipo)'
        by_type[t]['n_pickings'] += 1
    for ln in log:
        t = ln['picking_type_name'] or '(sem tipo)'
        by_type[t]['n_lines'] += 1
        by_type[t]['qty'] += float(ln['quantity_ml'])
    print('\n  Por picking_type:')
    for t, d in sorted(by_type.items(), key=lambda x: -x[1]['qty']):
        print(f"    {t:<50} pickings={d['n_pickings']:>4} lines={d['n_lines']:>4}  qty={d['qty']:>14,.2f}")

    # Resumo por state
    by_state: Dict[str, int] = defaultdict(int)
    for p in pickings.values():
        by_state[p['state']] += 1
    print('\n  Por picking_state:')
    for s, n in sorted(by_state.items(), key=lambda x: -x[1]):
        print(f"    {s:<25} {n}")

    # Top 15 pickings por qty
    print('\n  Top 15 pickings por qtd reservada:')
    top = sorted(pickings.items(), key=lambda x: -x[1]['qty_total'])[:15]
    for pid, p in top:
        print(f"    {p['name']:<25} type={p['type']:<35} state={p['state']:<22} "
              f"lines={p['n_lines']:>3}  qty={p['qty_total']:>12,.2f}  "
              f"origin={p['origin'][:30]}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--csv-pulados', default=CSV_PULADOS_DEFAULT,
                    help='CSV de quants pulados (gerado por mover_migracao_para_indisponivel.py)')
    ap.add_argument('--csv-log', default=CSV_LOG_DEFAULT,
                    help='CSV de saida com as move_lines impactadas')
    ap.add_argument('--confirmar', action='store_true',
                    help='Executa cancelamento. Sem flag: dry-run.')
    args = ap.parse_args()
    dry_run = not args.confirmar

    pulados = ler_pulados(args.csv_pulados)
    if not pulados:
        print(f'CSV {args.csv_pulados} vazio. Nada a fazer.')
        return

    app = create_app()
    with app.app_context():
        odoo = get_odoo_connection()
        banner(f'CANCELAR RESERVAS MIGRACAO  (modo={"DRY-RUN" if dry_run else "EXECUCAO"})')
        print(f'  {len(pulados)} quants pulados de entrada')

        banner('1. Identificando stock.move.line de reserva', '-')
        log = buscar_move_lines_reservando(odoo, pulados)
        imprimir_resumo(log)

        # Salva CSV de log
        if log:
            cols = ['filial', 'quant_id', 'product_id', 'default_code', 'product_name',
                    'lot_id', 'lot_name', 'location_id', 'location_name',
                    'qty_quant', 'qty_reservada',
                    'picking_id', 'picking_name', 'picking_type_name',
                    'origin', 'picking_state',
                    'move_id', 'move_line_id', 'quantity_ml', 'state']
            with open(args.csv_log, 'w', newline='') as f:
                w = csv.DictWriter(f, fieldnames=cols)
                w.writeheader()
                w.writerows(log)
            print(f'\n  Detalhe completo em {args.csv_log}')

        if dry_run:
            print('\n  [DRY-RUN] nada cancelado. Use --confirmar para executar.')
            return

        # Cancelamento real
        banner('2. Executando cancelamento (do_unreserve + unlink)', '-')

        # 2a. Pickings com picking_id: do_unreserve oficial
        picking_ids: Set[int] = set()
        ml_sem_picking: List[int] = []
        for ln in log:
            if ln['picking_id']:
                picking_ids.add(int(ln['picking_id']))
            else:
                ml_sem_picking.append(int(ln['move_line_id']))

        print(f'  2a. Pickings com do_unreserve: {len(picking_ids)}')
        ok_pck, falhas_pck = 0, []
        for pid in sorted(picking_ids):
            try:
                odoo.execute_kw('stock.picking', 'do_unreserve', [[pid]])
                ok_pck += 1
            except Exception as e:
                falhas_pck.append((pid, str(e)))
                logger.error(f'FALHA picking pid={pid}: {e}')
        print(f'      OK: {ok_pck} | FALHAS: {len(falhas_pck)}')

        # 2b. MOs (sem picking_id): unlink direto da stock.move.line
        print(f'  2b. stock.move.line a unlink (MOs sem picking): {len(ml_sem_picking)}')
        ok_ml, falhas_ml = 0, []
        # batch de 50 para evitar timeout
        for i in range(0, len(ml_sem_picking), 50):
            batch = ml_sem_picking[i:i + 50]
            try:
                odoo.execute_kw('stock.move.line', 'unlink', [batch])
                ok_ml += len(batch)
            except Exception as e:
                # tentar individualmente para identificar quais falharam
                for ml_id in batch:
                    try:
                        odoo.execute_kw('stock.move.line', 'unlink', [[ml_id]])
                        ok_ml += 1
                    except Exception as e2:
                        falhas_ml.append((ml_id, str(e2)))
                logger.warning(f'batch unlink falhou ({i}-{i + len(batch)}): {e}; fallback individual')
        print(f'      OK: {ok_ml} | FALHAS: {len(falhas_ml)}')

        if falhas_pck or falhas_ml:
            print('\n  Primeiras falhas:')
            for pid, err in falhas_pck[:5]:
                print(f'    picking pid={pid} {err[:200]}')
            for ml_id, err in falhas_ml[:5]:
                print(f'    move_line id={ml_id} {err[:200]}')


if __name__ == '__main__':
    main()
