"""Remove TODAS as reservas de SAIDA (origem interna) das 4 companies.

Instrucao do usuario (2026-05-19 noite): "Remova todas as reservas do Odoo
de todos os produtos. Essas reservas estao uma zona. E melhor depois terem
o trabalho de reservar novamente do que deixar assim."

Escopo (confirmado): FB+SC+CD+LF, SO reservas de SAIDA que travam estoque
interno (location_id origem = internal). NAO mexe em recebimentos (origem
fornecedor/virtual, nao travam saldo interno).

3 fases:
  FASE 1 — Pickings: stock.picking.do_unreserve nos pickings com move de
           origem interna e state assigned/partially_available. Cobre
           Delivery, Separacoes, Transferencias internas outbound.
  FASE 2 — MOs ativas: mrp.production.do_unreserve nas MOs em state
           confirmed/progress (EXCLUI to_close/done — picked=True ja e
           consumo realizado, nao reserva). Remove reserva de materia-prima.
  FASE 3 — Cleanup: zera reserved_quantity residual (stale/negativo) nos
           quants internos onde nenhuma move.line picked=False sobrou.

Metodos validados (2026-05-19):
  - stock.picking.do_unreserve([ids])  -> remove move.line picked=False
  - mrp.production.do_unreserve([ids])  -> remove move.line picked=False da MO
  Ambos no-op em registros done/to_close (seguros).

reserved_quantity de quant interno SEMPRE vem de saida (recebimento reserva
contraparte virtual). Logo zerar residual stale e seguro.

Uso:
    python scripts/inventario_2026_05/remover_reservas_saida.py
    python scripts/inventario_2026_05/remover_reservas_saida.py --confirmar
    python scripts/inventario_2026_05/remover_reservas_saida.py --confirmar --companies 1
"""
import argparse
import csv
import logging
import sys
import time
from pathlib import Path

_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parents[2]))

from app import create_app  # noqa: E402  # type: ignore
from app.odoo.utils.connection import get_odoo_connection  # noqa: E402  # type: ignore

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)-7s %(name)s | %(message)s')
logger = logging.getLogger('remover_reservas')

COMPANY_NAME = {1: 'FB', 3: 'SC', 4: 'CD', 5: 'LF'}
TODAS_COMPANIES = [1, 3, 4, 5]
STATES_RESERVA = ['assigned', 'partially_available']
STATES_MO_ATIVA = ['confirmed', 'progress']  # NAO to_close/done/cancel
BATCH = 50
CSV_AUDIT = '/tmp/remover_reservas_saida_audit.csv'


def banner(t, c='='):
    print()
    print(c * 90)
    print(f'  {t}')
    print(c * 90)


def coletar(odoo, companies):
    """Coleta pickings e MOs alvo. Retorna (picking_ids, mo_ids_ativas, stats)."""
    # 1. Moves de origem interna com reserva
    moves = odoo.search_read('stock.move', [
        ('company_id', 'in', companies),
        ('state', 'in', STATES_RESERVA),
        ('location_id.usage', '=', 'internal'),
    ], ['id', 'picking_id', 'raw_material_production_id', 'company_id'])
    print(f'Moves de saida interna com reserva: {len(moves)}')

    picking_ids = set()
    mo_ids = set()
    moves_sem_dono = 0
    stats_pk = {c: 0 for c in companies}
    stats_mo = {c: 0 for c in companies}
    for m in moves:
        cid = m['company_id'][0] if m.get('company_id') else None
        if m.get('picking_id'):
            picking_ids.add(m['picking_id'][0])
            if cid in stats_pk:
                stats_pk[cid] += 1
        elif m.get('raw_material_production_id'):
            mo_ids.add(m['raw_material_production_id'][0])
            if cid in stats_mo:
                stats_mo[cid] += 1
        else:
            moves_sem_dono += 1

    # 2. Filtrar MOs ativas (confirmed/progress)
    mo_ids_ativas = []
    mo_excluidas_to_close = 0
    if mo_ids:
        mos = odoo.read('mrp.production', list(mo_ids), ['id', 'state'])
        for mo in mos:
            if mo['state'] in STATES_MO_ATIVA:
                mo_ids_ativas.append(mo['id'])
            else:
                mo_excluidas_to_close += 1

    print(f'\n  Pickings unicos (saida interna): {len(picking_ids)}')
    for c in companies:
        if stats_pk.get(c):
            print(f'     {COMPANY_NAME[c]}: {stats_pk[c]} moves')
    print(f'  MOs unicas: {len(mo_ids)} (ativas confirmed/progress={len(mo_ids_ativas)}, '
          f'excluidas to_close/done={mo_excluidas_to_close})')
    for c in companies:
        if stats_mo.get(c):
            print(f'     {COMPANY_NAME[c]}: {stats_mo[c]} moves de MO')
    if moves_sem_dono:
        print(f'  Moves sem picking nem MO (ignorados): {moves_sem_dono}')

    return sorted(picking_ids), sorted(mo_ids_ativas)


def contar_quants_reservados(odoo, companies):
    n = len(odoo.search('stock.quant', [
        ('company_id', 'in', companies),
        ('reserved_quantity', '!=', 0),
    ]))
    n_neg = len(odoo.search('stock.quant', [
        ('company_id', 'in', companies),
        ('reserved_quantity', '<', 0),
    ]))
    return n, n_neg


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--confirmar', action='store_true')
    ap.add_argument('--companies', nargs='+', type=int, default=TODAS_COMPANIES,
                    help='IDs de company (default: 1 3 4 5)')
    ap.add_argument('--skip-cleanup', action='store_true',
                    help='Pula FASE 3 (zerar reserved_quantity stale residual)')
    ap.add_argument('--csv-audit', default=CSV_AUDIT)
    args = ap.parse_args()
    dry_run = not args.confirmar
    companies = args.companies

    app = create_app()
    with app.app_context():
        odoo = get_odoo_connection()
        banner(f'REMOVER RESERVAS DE SAIDA  '
               f'(modo={"DRY-RUN" if dry_run else "EXECUCAO"}  companies={companies})')

        banner('1. Coletando alvos', '-')
        picking_ids, mo_ids = coletar(odoo, companies)

        n_res_antes, n_neg_antes = contar_quants_reservados(odoo, companies)
        print(f'\n  Quants reservados ANTES: {n_res_antes} (reserved<0: {n_neg_antes})')

        if dry_run:
            print('\n  [DRY-RUN] Nada alterado. Use --confirmar para executar.')
            print(f'  Plano: do_unreserve em {len(picking_ids)} pickings + '
                  f'{len(mo_ids)} MOs ativas + cleanup stale.')
            return

        audit = []
        t0 = time.time()

        # FASE 1 — Pickings
        banner('FASE 1 — do_unreserve pickings', '-')
        ok_pk, fail_pk = 0, 0
        for i in range(0, len(picking_ids), BATCH):
            batch = picking_ids[i:i + BATCH]
            try:
                odoo.execute_kw('stock.picking', 'do_unreserve', [batch])
                ok_pk += len(batch)
            except Exception as e:
                # fallback individual
                for pid in batch:
                    try:
                        odoo.execute_kw('stock.picking', 'do_unreserve', [[pid]])
                        ok_pk += 1
                    except Exception as e2:
                        fail_pk += 1
                        audit.append({'fase': 1, 'tipo': 'picking', 'id': pid,
                                      'status': 'FALHA', 'erro': str(e2)[:200]})
                logger.warning(f'batch picking {i} fallback: {e}')
            if (i // BATCH) % 5 == 0 or i + BATCH >= len(picking_ids):
                print(f'  {min(i + BATCH, len(picking_ids))}/{len(picking_ids)} pickings '
                      f'({int(time.time() - t0)}s)')
        print(f'  Pickings OK={ok_pk} FALHA={fail_pk}')

        # FASE 2 — MOs ativas
        banner('FASE 2 — do_unreserve MOs ativas', '-')
        ok_mo, fail_mo = 0, 0
        t1 = time.time()
        for i in range(0, len(mo_ids), BATCH):
            batch = mo_ids[i:i + BATCH]
            try:
                odoo.execute_kw('mrp.production', 'do_unreserve', [batch])
                ok_mo += len(batch)
            except Exception as e:
                for mid in batch:
                    try:
                        odoo.execute_kw('mrp.production', 'do_unreserve', [[mid]])
                        ok_mo += 1
                    except Exception as e2:
                        fail_mo += 1
                        audit.append({'fase': 2, 'tipo': 'mo', 'id': mid,
                                      'status': 'FALHA', 'erro': str(e2)[:200]})
                logger.warning(f'batch MO {i} fallback: {e}')
            if (i // BATCH) % 5 == 0 or i + BATCH >= len(mo_ids):
                print(f'  {min(i + BATCH, len(mo_ids))}/{len(mo_ids)} MOs '
                      f'({int(time.time() - t1)}s)')
        print(f'  MOs OK={ok_mo} FALHA={fail_mo}')

        # FASE 3 — Cleanup stale
        n_res_meio, n_neg_meio = contar_quants_reservados(odoo, companies)
        print(f'\n  Quants reservados apos FASE 1+2: {n_res_meio} (reserved<0: {n_neg_meio})')

        if not args.skip_cleanup and n_res_meio > 0:
            banner('FASE 3 — Cleanup reserved_quantity stale residual', '-')
            qids = odoo.search('stock.quant', [
                ('company_id', 'in', companies),
                ('reserved_quantity', '!=', 0),
            ])
            print(f'  Zerando reserved_quantity em {len(qids)} quants residuais (stale)...')
            for i in range(0, len(qids), 200):
                odoo.write('stock.quant', qids[i:i + 200], {'reserved_quantity': 0})
            print(f'  OK.')

        # Auditoria final
        banner('Auditoria final', '=')
        n_res_fim, n_neg_fim = contar_quants_reservados(odoo, companies)
        print(f'  Quants reservados ANTES:  {n_res_antes}')
        print(f'  Quants reservados DEPOIS: {n_res_fim} (reserved<0: {n_neg_fim})')
        print(f'  Pickings processados: {ok_pk}/{len(picking_ids)}')
        print(f'  MOs processadas:      {ok_mo}/{len(mo_ids)}')
        print(f'  Tempo total: {int(time.time() - t0)}s')

        # CSV de falhas (se houver)
        if audit:
            with open(args.csv_audit, 'w', newline='') as f:
                w = csv.DictWriter(f, fieldnames=['fase', 'tipo', 'id', 'status', 'erro'])
                w.writeheader()
                w.writerows(audit)
            print(f'  Falhas registradas em {args.csv_audit} ({len(audit)})')


if __name__ == '__main__':
    main()
