"""14 - Cancelar MOs antigas state=confirmed que reservam MIGRACAO em Pre-Prod FB.

Cancela mrp.production em state=confirmed criadas ate 6 meses atras que
reservam lote MIGRACAO em sub-locations de Pre-Producao (Linha Balde/Vidro/
Manual/Salmoura). Libera move_lines reservadas.

NAO cancela:
- MOs em state=progress (produzindo agora)
- MOs em state=to_close (finalizando)
- MOs confirmed criadas nos ultimos 6 meses (planejadas para produzir em breve)

Backup informacional: o JSON de auditoria contem nome/state/data de criacao
de cada MO antes do cancel — permite reverter manualmente se necessario.

Reversao: MOs canceladas podem ser duplicadas via UI Odoo (botao "Duplicar")
para recriar caso especifico, ou criar nova MO com mesmo BoM/qty.

Flags:
    --dry-run             (default) so lista, nao cancela
    --confirmar           executa real
    --dias-corte N        idade minima em dias (default 180)
    --limite N            limite N MOs canceladas (canary)
    --log-json PATH       caminho do log JSON
"""
import argparse
import json
import logging
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parents[2]))

from app import create_app  # noqa: E402
from app.odoo.utils.connection import get_odoo_connection  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-7s %(name)s | %(message)s',
)
logger = logging.getLogger('14_cancelar_mos')

COMPANY_ID = 1  # FB
PRE_PROD_LOCS = [4066, 4067, 4068, 27458]
LOG_DRY_RUN_PATH = (
    '/home/rafaelnascimento/projetos/frete_sistema/scripts/'
    'inventario_2026_05/auditoria/log_13_transf_migr_fb_20260518_224352.json'
)


def banner(t: str, c: str = '=') -> None:
    print()
    print(c * 78)
    print(f'  {t}')
    print(c * 78)


def listar_mos_candidatas(
    odoo, dias_corte: int, ate_data: str = '', skip_qty_done: bool = True,
) -> List[Dict]:
    """Lista MOs (state=confirmed) que reservam MIGRACAO em Pre-Prod.

    Args:
        dias_corte: idade minima em dias (ignorado se ate_data definido)
        ate_data: 'YYYY-MM-DD' explicito (precedencia sobre dias_corte)
        skip_qty_done: se True, exclui MOs cujos moves tenham qty_done>0
            (consumo ja efetivado — cancelar criaria furo contabil)
    """
    # 1. Carregar lot_ids MIGRACAO do log do script 13 (lotes que falharam)
    with open(LOG_DRY_RUN_PATH) as f:
        d = json.load(f)
    lot_ids = list(set(
        r['lot_id_origem'] for r in d['resultados']
        if r['status'] == 'FALHA_SEM_SALDO' and r.get('lot_id_origem')
    ))
    logger.info(f'lot_ids MIGRACAO em escopo: {len(lot_ids)}')

    # 2. Move_lines ativas em Pre-Prod com lote MIGRACAO
    mls = odoo.search_read(
        'stock.move.line',
        [
            ['lot_id', 'in', lot_ids],
            ['state', 'in', ['waiting', 'confirmed', 'partially_available', 'assigned']],
            ['company_id', '=', COMPANY_ID],
            ['location_id', 'in', PRE_PROD_LOCS],
        ],
        ['id', 'move_id', 'qty_done', 'lot_id', 'product_id', 'location_id'],
        limit=2000,
    )
    move_ids = list(set(ml['move_id'][0] for ml in mls if ml.get('move_id')))
    logger.info(f'move_lines em Pre-Prod: {len(mls)}, moves distintos: {len(move_ids)}')

    # 3. Moves -> MO (com qty_done para detectar consumo efetivado)
    moves = odoo.search_read(
        'stock.move', [['id', 'in', move_ids]],
        ['raw_material_production_id', 'product_qty', 'product_id'],
    )
    # Verifica qty_done agregado por MO via move_line.qty_done
    mo_qty_done: Dict[int, float] = {}
    for m in moves:
        mo_id = m.get('raw_material_production_id')
        if not mo_id:
            continue
        mo_id = mo_id[0]
        mo_qty_done.setdefault(mo_id, 0.0)
    # Somar qty_done de TODAS move_lines (incluindo as nao em Pre-Prod) por MO
    if move_ids:
        all_mls = odoo.search_read(
            'stock.move.line', [['move_id', 'in', move_ids]],
            ['move_id', 'qty_done'],
        )
        move_id_to_mo = {m['id']: (m['raw_material_production_id'][0]
                                   if m.get('raw_material_production_id') else None)
                         for m in moves}
        for ml in all_mls:
            mo_id = move_id_to_mo.get(ml['move_id'][0])
            if mo_id is not None:
                mo_qty_done[mo_id] = mo_qty_done.get(mo_id, 0) + float(ml.get('qty_done', 0))

    mo_to_moves: Dict[int, List[Dict]] = {}
    for m in moves:
        if m.get('raw_material_production_id'):
            mo_id = m['raw_material_production_id'][0]
            mo_to_moves.setdefault(mo_id, []).append(m)
    mo_ids = list(mo_to_moves.keys())
    logger.info(f'MOs com matprima MIGRACAO: {len(mo_ids)}')

    # 4. MOs + filtro
    if ate_data:
        LIMITE = ate_data
        logger.info(f'Usando --ate-data: {LIMITE} (precedencia sobre --dias-corte)')
    else:
        LIMITE = (datetime.now() - timedelta(days=dias_corte)).strftime('%Y-%m-%d')
    mos = odoo.search_read(
        'mrp.production', [['id', 'in', mo_ids]],
        ['id', 'name', 'state', 'create_date', 'date_start', 'product_id'],
    )
    candidatas = [
        mo for mo in mos
        if mo['state'] == 'confirmed'
        and mo.get('create_date', '9999')[:10] <= LIMITE
    ]
    # Filtro adicional: excluir MOs com consumo efetivado
    excluidas_por_qty_done = []
    if skip_qty_done:
        antes = len(candidatas)
        kept = []
        for mo in candidatas:
            qd = mo_qty_done.get(mo['id'], 0)
            if qd > 0:
                excluidas_por_qty_done.append((mo['name'], qd))
            else:
                kept.append(mo)
        candidatas = kept
        if excluidas_por_qty_done:
            logger.info(
                f'Excluidas por consumo efetivado (qty_done>0): '
                f'{len(excluidas_por_qty_done)} de {antes}'
            )
            for nome, qd in excluidas_por_qty_done[:5]:
                logger.info(f'  PRESERVADA {nome}: qty_done={qd}')
    logger.info(
        f'CANDIDATAS (state=confirmed AND create<={LIMITE}'
        f'{" AND qty_done=0" if skip_qty_done else ""}): {len(candidatas)} '
        f'de {len(mos)} ativas'
    )

    # Enriquecer com qty/move_count
    for mo in candidatas:
        ms = mo_to_moves.get(mo['id'], [])
        mo['n_moves'] = len(ms)
        mo['qty_total_moves'] = sum(float(m.get('product_qty', 0)) for m in ms)
        # move_lines desse MO em pre-prod
        ml_count = 0
        for m in ms:
            ml_count += sum(1 for ml in mls if ml.get('move_id') and ml['move_id'][0] == m['id'])
        mo['n_move_lines_pre_prod'] = ml_count
    return candidatas


def cancelar_mo(odoo, mo_id: int) -> Dict:
    """Tenta cancelar MO via action_cancel. Retorna dict com resultado."""
    t0 = time.time()
    try:
        # Em mrp.production a acao de cancelar e action_cancel
        odoo.execute_kw('mrp.production', 'action_cancel', [[mo_id]])
        # Reler estado pos-cancel
        mo_atualizada = odoo.search_read(
            'mrp.production', [['id', '=', mo_id]], ['state'],
        )
        state_apos = mo_atualizada[0]['state'] if mo_atualizada else '?'
        return {
            'status': 'CANCELADA',
            'state_apos': state_apos,
            'tempo_ms': int((time.time() - t0) * 1000),
        }
    except Exception as exc:
        return {
            'status': 'FALHA',
            'erro': str(exc),
            'tempo_ms': int((time.time() - t0) * 1000),
        }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true', default=True)
    parser.add_argument('--confirmar', action='store_true', default=False)
    parser.add_argument('--dias-corte', type=int, default=180)
    parser.add_argument('--ate-data', type=str, default='',
                        help='YYYY-MM-DD: cancelar so MOs criadas ate essa data')
    parser.add_argument('--incluir-qty-done', action='store_true', default=False,
                        help='NAO excluir MOs com qty_done>0 (PERIGOSO)')
    parser.add_argument('--limite', type=int, default=0)
    parser.add_argument('--log-json', type=str, default='')
    args = parser.parse_args()
    if args.confirmar:
        args.dry_run = False

    cutoff_desc = (f'ate-data={args.ate_data}' if args.ate_data
                   else f'idade>={args.dias_corte}d')
    banner(
        f'CANCELAR MOs ANTIGAS — '
        f'{"DRY-RUN" if args.dry_run else "EXECUCAO REAL"} ({cutoff_desc})'
    )

    app = create_app()
    resultados = []
    with app.app_context():
        odoo = get_odoo_connection()
        candidatas = listar_mos_candidatas(
            odoo, args.dias_corte,
            ate_data=args.ate_data,
            skip_qty_done=not args.incluir_qty_done,
        )
        if args.limite > 0:
            candidatas = candidatas[: args.limite]

        logger.info(f'Processando {len(candidatas)} MOs')
        print()

        for i, mo in enumerate(sorted(candidatas, key=lambda x: x.get('create_date', '')), 1):
            r = {
                'mo_id': mo['id'],
                'name': mo['name'],
                'state_antes': mo['state'],
                'create_date': mo.get('create_date'),
                'product': mo['product_id'][1] if mo.get('product_id') else None,
                'n_moves': mo.get('n_moves', 0),
                'n_move_lines_pre_prod': mo.get('n_move_lines_pre_prod', 0),
                'qty_total_moves': mo.get('qty_total_moves', 0.0),
                'inicio': datetime.now().isoformat(timespec='seconds'),
            }
            if args.dry_run:
                r['status'] = 'DRY_RUN_OK'
            else:
                res = cancelar_mo(odoo, mo['id'])
                r.update(res)
            resultados.append(r)
            tag = r['status']
            if i <= 5 or i > len(candidatas) - 3 or i % 20 == 0:
                logger.info(
                    f'[{i:3}/{len(candidatas)}] {tag} '
                    f'{r["name"]:<22} create={(r["create_date"] or "?")[:10]} '
                    f'mls={r["n_move_lines_pre_prod"]}'
                )

    # Resumo
    banner('RESUMO')
    from collections import Counter
    cont = Counter(r['status'] for r in resultados)
    for s, n in cont.most_common():
        print(f'  {s:30s} {n:5d}')
    print(f'  {"TOTAL":30s} {len(resultados):5d}')
    print()
    print(f'  Move_lines em Pre-Prod afetadas: '
          f'{sum(r.get("n_move_lines_pre_prod", 0) for r in resultados)}')

    log_path = args.log_json
    if not log_path:
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_path = str(
            _THIS.parent / 'auditoria' / f'log_14_cancelar_mos_{ts}.json'
        )
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, 'w', encoding='utf-8') as f:
        json.dump({
            'args': vars(args),
            'company_id': COMPANY_ID,
            'pre_prod_locs': PRE_PROD_LOCS,
            'dias_corte': args.dias_corte,
            'total': len(resultados),
            'contagem_status': dict(cont),
            'inicio_run': resultados[0]['inicio'] if resultados else None,
            'fim_run': datetime.now().isoformat(timespec='seconds'),
            'resultados': resultados,
        }, f, indent=2, default=str)
    print(f'\n  Log JSON: {log_path}')

    falhas = sum(1 for r in resultados if r['status'].startswith('FALHA'))
    return 0 if falhas == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
