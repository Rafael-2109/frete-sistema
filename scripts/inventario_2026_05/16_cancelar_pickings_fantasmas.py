"""16 - Cancelar pickings fantasmas que reservam lotes da planilha
'transf para MIGRACAO.xlsx' (2026-05-18).

Pickings fantasmas = pickings em state=assigned/draft com >7 dias de idade
e origin antiga (C24xxxxx) ou SEM origin, criados ha meses mas nunca
executados. Reservam saldo de lotes que precisamos transferir para MIGRACAO.

Identificacao: feita pelo script 15 (FALHA_SEM_SALDO com reserved=quantity).
Apos investigacao manual em /tmp/pickings_reservadores_15.json:
- 854 pickings unicos
- 96.7% > 7 dias, 75% > 90 dias, max 677 dias
- 96% tipo 'FB: Transferencias Internas (FB)'

Decisao do usuario 2026-05-18: cancelar todos os 854.

Operacao: `action_cancel` no stock.picking. Libera reservas automaticamente
(quants voltam a livre). Reversivel: pickings cancelados podem ser
recriados manualmente se preciso.

Flags:
    --dry-run             (default) so lista, nao executa
    --confirmar           cancela de verdade
    --json PATH           arquivo de input (default /tmp/pickings_reservadores_15.json)
    --limite N            primeiros N (canary)
    --idade-min N         so cancela pickings com >= N dias (filtro adicional)
"""
import argparse
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List

_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parents[2]))

from app import create_app  # noqa: E402
from app.odoo.services.stock_picking_service import StockPickingService  # noqa: E402
from app.odoo.utils.connection import get_odoo_connection  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-7s %(name)s | %(message)s',
)
logger = logging.getLogger('16_cancelar_fantasmas')

DEFAULT_JSON = '/tmp/pickings_reservadores_15.json'


def banner(t: str, c: str = '=') -> None:
    print()
    print(c * 78)
    print(f'  {t}')
    print(c * 78)


def carregar_pickings(path: str, idade_min: int = 0) -> List[Dict]:
    with open(path) as f:
        data = json.load(f)
    pickings = data['pickings']

    if idade_min > 0:
        hoje = datetime.now()
        filtrados = []
        for p in pickings:
            data_str = p.get('create_date') or p.get('scheduled_date')
            if not data_str:
                continue
            d = datetime.fromisoformat(str(data_str).replace('Z', ''))
            if (hoje - d).days >= idade_min:
                filtrados.append(p)
        logger.info(
            f'Filtro idade_min={idade_min}: '
            f'{len(filtrados)}/{len(pickings)} pickings'
        )
        pickings = filtrados
    return pickings


def cancelar_picking(svc: StockPickingService, p: Dict) -> Dict:
    """Cancela 1 picking. Retorna status com timing."""
    r = {
        'picking_id': p['id'],
        'name': p['name'],
        'state_antes': p['state'],
        'origin': p.get('origin') or '',
        'create_date': str(p.get('create_date')),
        'inicio': datetime.now().isoformat(timespec='seconds'),
    }
    t0 = time.time()
    try:
        svc.cancelar(p['id'], motivo='transf MIGRACAO 2026-05-18')
        r['status'] = 'CANCELED'
        r['tempo_ms'] = int((time.time() - t0) * 1000)
    except Exception as exc:
        r['status'] = 'FALHA'
        r['erro'] = str(exc)
        r['tempo_ms'] = int((time.time() - t0) * 1000)
        logger.exception(
            f'Falha cancelar picking {p["id"]} ({p["name"]}): {exc}'
        )
    return r


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true', default=True)
    parser.add_argument('--confirmar', action='store_true', default=False)
    parser.add_argument('--json', type=str, default=DEFAULT_JSON)
    parser.add_argument('--limite', type=int, default=0)
    parser.add_argument('--idade-min', type=int, default=0)
    parser.add_argument('--log-json', type=str, default='')
    args = parser.parse_args()

    if args.confirmar:
        args.dry_run = False

    if not Path(args.json).exists():
        logger.error(f'JSON nao encontrado: {args.json}')
        return 2

    pickings = carregar_pickings(args.json, idade_min=args.idade_min)
    if args.limite > 0:
        pickings = pickings[: args.limite]

    banner(
        f'CANCELAR PICKINGS FANTASMAS — '
        f'{"DRY-RUN" if args.dry_run else "EXECUCAO REAL"} '
        f'({len(pickings)} pickings)'
    )

    if args.dry_run:
        # So lista
        print('\nPrimeiros 30 pickings (DRY-RUN):')
        for p in pickings[:30]:
            print(
                f'  id={p["id"]:6d} {p["name"]:30s} state={p["state"]:10s} '
                f'origin={(p.get("origin") or "")[:25]:25s} '
                f'create={str(p.get("create_date") or "")[:10]}'
            )
        if len(pickings) > 30:
            print(f'  ... ({len(pickings)-30} mais)')
        print('\n  --confirmar para executar.')
        return 0

    app = create_app()
    resultados = []
    t_global = time.time()
    with app.app_context():
        odoo = get_odoo_connection()
        svc = StockPickingService(odoo=odoo)

        for i, p in enumerate(pickings, 1):
            r = cancelar_picking(svc, p)
            resultados.append(r)
            if r['status'] == 'CANCELED':
                if i % 20 == 0 or i == len(pickings):
                    logger.info(
                        f'[{i:4}/{len(pickings)}] cancelados ate agora: '
                        f'{sum(1 for x in resultados if x["status"]=="CANCELED")} '
                        f'falhas: {sum(1 for x in resultados if x["status"]=="FALHA")}'
                    )
            else:
                logger.warning(
                    f'[{i:4}/{len(pickings)}] FALHA picking {r["picking_id"]} '
                    f'{r["name"]}: {r.get("erro")}'
                )

    banner('RESUMO')
    from collections import Counter
    cont = Counter(r['status'] for r in resultados)
    for status, n in cont.most_common():
        print(f'  {status:30s} {n:5d}  ({n*100/len(resultados):.1f}%)')
    print(f'  {"TOTAL":30s} {len(resultados):5d}')
    print(f'  Tempo total: {time.time() - t_global:.1f}s')

    log_path = args.log_json
    if not log_path:
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        modo = 'real' if not args.dry_run else 'dryrun'
        log_path = str(
            _THIS.parent / 'auditoria' /
            f'log_16_cancelar_fantasmas_{modo}_{ts}.json'
        )
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, 'w', encoding='utf-8') as f:
        json.dump({
            'args': vars(args),
            'total': len(resultados),
            'contagem_status': dict(cont),
            'resultados': resultados,
        }, f, indent=2, default=str)
    print(f'\n  Log JSON: {log_path}')

    falhas = sum(1 for r in resultados if r['status'] == 'FALHA')
    return 0 if falhas == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
