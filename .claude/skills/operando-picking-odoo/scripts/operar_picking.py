"""operar_picking.py — skill `operando-picking-odoo`: cancelar, validar ou devolver.

Expõe StockPickingService via CLI:
- cancelar (single ou batch JSON; cascade automático moves+MLs+quants),
- validar (button_validate com invariante G019/G020; opcional G023 via --linhas-esperadas),
- devolver (cria stock.return.picking + valida; idempotente).
`--dry-run` é o DEFAULT.

Modos (--modo é OBRIGATÓRIO):
  cancelar:  --picking-id <id> [--motivo "..."]
             --json <path> [--limite N] [--idade-min DIAS]
  validar:   --picking-id <id> [--linhas-esperadas JSON_STR]
  devolver:  --picking-id <id>

Exemplos:
  python operar_picking.py --modo cancelar --picking-id 316701
  python operar_picking.py --modo cancelar --picking-id 316701 --motivo "fantasma" --confirmar
  python operar_picking.py --modo cancelar --json /tmp/pickings.json --idade-min 7 --confirmar
  python operar_picking.py --modo validar --picking-id 317342 --confirmar
  python operar_picking.py --modo validar --picking-id 317306 \\
      --linhas-esperadas '[{"product_id":205460830,"quantity":35,"lot_name":"MI 027-098/26"}]' \\
      --confirmar
  python operar_picking.py --modo devolver --picking-id 320063 --confirmar

Exit: 0 efetivado · 4 dry-run OK · 1 falha · 2 uso.
"""
import argparse
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parents[4]))

from app import create_app  # noqa: E402
from app.odoo.estoque.scripts.picking import StockPickingService  # noqa: E402
from app.odoo.utils.connection import get_odoo_connection  # noqa: E402
from app.utils.timezone import agora_brasil_naive  # noqa: E402  # CR1#4 timezone

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-7s %(name)s | %(message)s',
)
logger = logging.getLogger('operar_picking')

_FALHAS = {
    'FALHA_PICKING_NAO_EXISTE', 'FALHA_STATE_DONE',
    'FALHA_STATE_INVALIDO', 'FALHA_STATE_NAO_DONE',
    'FALHA_CREATE_RETURNS', 'FALHA_ODOO', 'FALSE_POSITIVE_G019',
}
_OKS = {'CANCELADO', 'VALIDADO', 'DEVOLUCAO_CRIADA', 'DEVOLUCAO_REUTILIZADA', 'NOOP'}


def _emitir(out: Dict[str, Any], dry_run: bool) -> int:
    """Imprime JSON e retorna exit code conforme status."""
    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
    status = out.get('status', '')
    if status in _FALHAS:
        return 1
    if dry_run:
        return 4 if status == 'DRY_RUN_OK' else 1
    return 0 if status in _OKS else 1


def cancelar_single(svc: StockPickingService, picking_id: int,
                    motivo: str, dry_run: bool) -> Dict[str, Any]:
    """Cancela 1 picking com checagem de pré-cond (state)."""
    t0 = time.time()
    out: Dict[str, Any] = {
        'modo': 'cancelar',
        'picking_id': picking_id,
        'motivo': motivo,
        'dry_run': dry_run,
    }
    pk = svc.odoo.read('stock.picking', [picking_id],
                       ['name', 'state', 'origin', 'create_date'])
    if not pk:
        out['status'] = 'FALHA_PICKING_NAO_EXISTE'
        out['tempo_ms'] = int((time.time() - t0) * 1000)
        return out
    out['name'] = pk[0]['name']
    out['picking_state_antes'] = pk[0]['state']
    out['origin'] = pk[0].get('origin') or ''
    out['create_date'] = str(pk[0].get('create_date'))

    if pk[0]['state'] == 'done':
        out['status'] = 'FALHA_STATE_DONE'
        out['motivo_falha'] = ('Picking em state=done — usar --modo devolver '
                               'em vez de cancelar.')
        out['tempo_ms'] = int((time.time() - t0) * 1000)
        return out
    if pk[0]['state'] == 'cancel':
        out['status'] = 'NOOP'
        out['picking_state_depois'] = 'cancel'
        out['tempo_ms'] = int((time.time() - t0) * 1000)
        return out

    if dry_run:
        out['status'] = 'DRY_RUN_OK'
        out['picking_state_depois'] = 'cancel (planejado)'
        out['tempo_ms'] = int((time.time() - t0) * 1000)
        return out

    try:
        svc.cancelar(picking_id, motivo=motivo)
        pos = svc.odoo.read('stock.picking', [picking_id], ['state'])
        out['picking_state_depois'] = pos[0]['state'] if pos else 'unknown'
        out['status'] = 'CANCELADO' if out['picking_state_depois'] == 'cancel' else 'FALHA_ODOO'
    except Exception as exc:
        out['status'] = 'FALHA_ODOO'
        out['erro'] = str(exc)
        logger.exception(f'Falha cancelar {picking_id}: {exc}')
    out['tempo_ms'] = int((time.time() - t0) * 1000)
    return out


def cancelar_batch(svc: StockPickingService, pickings: List[Dict],
                   dry_run: bool, motivo: str) -> Dict[str, Any]:
    """Cancela N pickings (batch)."""
    t_global = time.time()
    resultados = []
    for p in pickings:
        pid = int(p['id'])
        r = cancelar_single(svc, pid, motivo or '', dry_run)
        resultados.append(r)

    from collections import Counter
    cont = Counter(r['status'] for r in resultados)
    return {
        'modo': 'cancelar (batch)',
        'total': len(resultados),
        'contagem_status': dict(cont),
        'resultados': resultados,
        'tempo_total_s': round(time.time() - t_global, 2),
        'dry_run': dry_run,
        'status': 'DRY_RUN_OK' if dry_run else (
            'CANCELADO' if all(r['status'] in _OKS for r in resultados)
            else 'FALHA_ODOO'
        ),
    }


def carregar_pickings_json(path: str, idade_min: int = 0,
                           limite: int = 0) -> List[Dict]:
    """Carrega pickings de JSON com filtro opcional de idade."""
    with open(path) as f:
        data = json.load(f)
    pickings = data.get('pickings') or data
    if not isinstance(pickings, list):
        raise SystemExit(
            f'JSON {path} deve conter chave "pickings" (lista) ou ser '
            'uma lista de dicts. Recebido: ' + type(pickings).__name__
        )

    if idade_min > 0:
        # CR1#4 (2026-05-24 v3): usar agora_brasil_naive em vez de
        # datetime.now() (regras REGRAS_TIMEZONE.md — Brasil naive).
        # Odoo retorna create_date em Brasil naive (config.py com
        # timezone=America/Sao_Paulo), entao a subtracao naive-naive
        # produz delta correto.
        hoje = agora_brasil_naive()
        filtrados = []
        for p in pickings:
            data_str = p.get('create_date') or p.get('scheduled_date')
            if not data_str:
                continue
            d = datetime.fromisoformat(str(data_str).replace('Z', ''))
            if (hoje - d).days >= idade_min:
                filtrados.append(p)
        pickings = filtrados

    if limite > 0:
        pickings = pickings[:limite]
    return pickings


def validar_single(svc: StockPickingService, picking_id: int,
                   linhas_esperadas: Optional[List[Dict]],
                   dry_run: bool) -> Dict[str, Any]:
    """Re-valida 1 picking com invariante G019/G020 + opcional G023."""
    t0 = time.time()
    out: Dict[str, Any] = {
        'modo': 'validar',
        'picking_id': picking_id,
        'dry_run': dry_run,
        'tem_linhas_esperadas': bool(linhas_esperadas),
    }
    pk = svc.odoo.read('stock.picking', [picking_id], ['name', 'state'])
    if not pk:
        out['status'] = 'FALHA_PICKING_NAO_EXISTE'
        out['tempo_ms'] = int((time.time() - t0) * 1000)
        return out
    out['name'] = pk[0]['name']
    out['state_antes'] = pk[0]['state']

    if pk[0]['state'] in ('done', 'cancel'):
        out['status'] = 'FALHA_STATE_INVALIDO'
        out['motivo_falha'] = (
            f'state={pk[0]["state"]} — nada a validar.'
        )
        out['tempo_ms'] = int((time.time() - t0) * 1000)
        return out

    if dry_run:
        out['status'] = 'DRY_RUN_OK'
        out['state_depois'] = 'done (planejado)'
        if linhas_esperadas:
            out['g023_planejado'] = (
                f'consolidar_move_lines com {len(linhas_esperadas)} '
                'linhas esperadas ANTES de button_validate'
            )
        out['tempo_ms'] = int((time.time() - t0) * 1000)
        return out

    try:
        svc.validar(picking_id, linhas_esperadas=linhas_esperadas)
        pos = svc.odoo.read('stock.picking', [picking_id], ['state'])
        out['state_depois'] = pos[0]['state'] if pos else 'unknown'
        out['status'] = 'VALIDADO'
    except RuntimeError as rex:
        # G019/G020 invariante levantou
        out['status'] = 'FALSE_POSITIVE_G019'
        out['erro'] = str(rex)
        # Re-le state final
        pos = svc.odoo.read('stock.picking', [picking_id], ['state'])
        out['state_depois'] = pos[0]['state'] if pos else 'unknown'
    except Exception as exc:
        out['status'] = 'FALHA_ODOO'
        out['erro'] = str(exc)
        logger.exception(f'Falha validar {picking_id}: {exc}')
    out['tempo_ms'] = int((time.time() - t0) * 1000)
    return out


def devolver_single(svc: StockPickingService, picking_id: int,
                    dry_run: bool) -> Dict[str, Any]:
    """Cria devolução do picking (idempotente)."""
    t0 = time.time()
    out: Dict[str, Any] = {
        'modo': 'devolver',
        'picking_id_origem': picking_id,
        'dry_run': dry_run,
    }
    pk = svc.odoo.read('stock.picking', [picking_id], ['name', 'state'])
    if not pk:
        out['status'] = 'FALHA_PICKING_NAO_EXISTE'
        out['tempo_ms'] = int((time.time() - t0) * 1000)
        return out
    out['name'] = pk[0]['name']
    out['state_origem'] = pk[0]['state']

    if pk[0]['state'] != 'done':
        out['status'] = 'FALHA_STATE_NAO_DONE'
        out['motivo_falha'] = (
            f'Picking state={pk[0]["state"]} — só dá pra devolver picking done.'
        )
        out['tempo_ms'] = int((time.time() - t0) * 1000)
        return out

    # Idempotência: checar se já existe
    ja = svc.odoo.search_read(
        'stock.picking',
        [['origin', 'ilike', f'Devolução de {pk[0]["name"]}']],
        ['id'], limit=1,
    )
    if ja:
        out['picking_id_devolucao'] = ja[0]['id']
        out['reutilizado_idempotente'] = True
        if dry_run:
            out['status'] = 'DRY_RUN_OK'
            out['plano'] = 'Devolução já existe; idempotente — retornaria id existente.'
        else:
            out['status'] = 'DEVOLUCAO_REUTILIZADA'
        out['tempo_ms'] = int((time.time() - t0) * 1000)
        return out

    if dry_run:
        out['status'] = 'DRY_RUN_OK'
        out['plano'] = 'Criar stock.return.picking + create_returns + validar.'
        out['tempo_ms'] = int((time.time() - t0) * 1000)
        return out

    try:
        new_pid = svc.devolver(picking_id)
        # CR1#3 (2026-05-24 v3): svc.devolver() ja garantiu state=done
        # (raise RuntimeError caso contrario). Evitar double-read aqui;
        # buscar so name (que nao foi garantido pelo svc).
        nm = svc.odoo.read('stock.picking', [new_pid], ['name'])
        out['picking_id_devolucao'] = new_pid
        out['state_devolucao'] = 'done'  # garantido pelo invariante do svc
        out['name_devolucao'] = nm[0]['name'] if nm else ''
        out['reutilizado_idempotente'] = False
        out['status'] = 'DEVOLUCAO_CRIADA'
    except RuntimeError as rex:
        msg = str(rex).lower()
        if 'create_returns' in msg:
            out['status'] = 'FALHA_CREATE_RETURNS'
        elif 'apos button_validate' in msg:
            out['status'] = 'FALSE_POSITIVE_G019'
        else:
            out['status'] = 'FALHA_ODOO'
        out['erro'] = str(rex)
    except Exception as exc:
        out['status'] = 'FALHA_ODOO'
        out['erro'] = str(exc)
        logger.exception(f'Falha devolver {picking_id}: {exc}')
    out['tempo_ms'] = int((time.time() - t0) * 1000)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(
        description=(__doc__ or '').split('\n')[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument('--modo', required=True,
                    choices=['cancelar', 'validar', 'devolver'],
                    help='Operação a executar.')
    ap.add_argument('--picking-id', type=int,
                    help='ID do picking (cancelar/validar/devolver single).')
    ap.add_argument('--json', type=str,
                    help='cancelar batch: caminho do JSON com lista de pickings '
                         '(cada item deve ter id, name, state, origin, create_date).')
    ap.add_argument('--limite', type=int, default=0,
                    help='cancelar batch: primeiros N pickings (canary).')
    ap.add_argument('--idade-min', type=int, default=0,
                    help='cancelar batch: só pickings com create_date >= N dias atrás.')
    ap.add_argument('--motivo', type=str, default='',
                    help='cancelar: motivo (apenas log).')
    ap.add_argument('--linhas-esperadas', type=str, default='',
                    help='validar: JSON inline com [{product_id, quantity, '
                         'lot_id|lot_name}, ...]. Passa para G023 consolidar antes '
                         'de button_validate.')
    ap.add_argument('--confirmar', action='store_true',
                    help='Efetivar (default = --dry-run).')
    args = ap.parse_args()

    dry_run = not args.confirmar

    # Validação args por modo
    if args.modo == 'cancelar':
        if not (args.picking_id or args.json):
            ap.error('--modo cancelar exige --picking-id OU --json.')
    elif args.modo == 'validar':
        if not args.picking_id:
            ap.error('--modo validar exige --picking-id.')
    elif args.modo == 'devolver':
        if not args.picking_id:
            ap.error('--modo devolver exige --picking-id.')

    # Parse linhas_esperadas se passou
    linhas_esperadas: Optional[List[Dict]] = None
    if args.linhas_esperadas:
        try:
            linhas_esperadas = json.loads(args.linhas_esperadas)
            if not isinstance(linhas_esperadas, list):
                raise ValueError('deve ser uma lista de dicts')
        except Exception as exc:
            ap.error(f'--linhas-esperadas inválido: {exc}')

    app = create_app()
    with app.app_context():
        odoo = get_odoo_connection()
        svc = StockPickingService(odoo=odoo)

        if args.modo == 'cancelar':
            if args.json:
                pickings = carregar_pickings_json(
                    args.json, idade_min=args.idade_min, limite=args.limite,
                )
                out = cancelar_batch(svc, pickings, dry_run, args.motivo)
            else:
                out = cancelar_single(svc, args.picking_id, args.motivo, dry_run)
        elif args.modo == 'validar':
            out = validar_single(svc, args.picking_id, linhas_esperadas, dry_run)
        else:  # devolver
            out = devolver_single(svc, args.picking_id, dry_run)

        return _emitir(out, dry_run)


if __name__ == '__main__':
    sys.exit(main())
