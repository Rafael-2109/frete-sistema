"""operar_reserva.py — skill `operando-reservas-odoo`: 5 modos (cirurgia, cancel, unreserve, find_orphan, zerar_residual).

Expõe StockReservaService via CLI:
- cirurgia (cancela 1+ moves órfãos preservando picking),
- cancelamento inteiro (action_cancel),
- unreserve_picking (libera reservas SEM cancelar — NOVO v7),
- find_orphan_mls (lista MLs apontando para quants zerados — NOVO v7),
- zerar_reserved_residual (cleanup pós-unlink — quants com reserved!=0 stale).
`--dry-run` é o DEFAULT (modos write).

Modos (mutuamente exclusivos):
  cirurgia:           --picking-id <id> --moves-writes "m1:q1,m2:q2" --ml-ids ml1,ml2,...
  cancela_picking:    --cancelar-picking --picking-id <id>
  unreserve_picking:  --unreserve-picking --picking-id <id>     (NOVO v7)
  find_orphan_mls:    --find-orphan --quant-ids q1,q2,q3,...    (NOVO v7, READ-only)
  zerar_residual:     --zerar-residual --quant-ids q1,q2,q3,...

Exemplos:
  # cirurgia dry-run (preview)
  python operar_reserva.py --picking-id 316701 --moves-writes "1075205:0.1986" --ml-ids 217654353
  # cirurgia efetivar
  python operar_reserva.py --picking-id 316701 --moves-writes "1075205:0.1986" --ml-ids 217654353 --confirmar
  # cancelar picking inteiro
  python operar_reserva.py --cancelar-picking --picking-id 320076 --confirmar
  # NOVO v7: unreserve_picking (libera reservas mantendo picking)
  python operar_reserva.py --unreserve-picking --picking-id 320753 --confirmar
  # NOVO v7: find_orphan_mls (READ-only, sempre exec)
  python operar_reserva.py --find-orphan --quant-ids 229937,258975
  # zerar reserved residual (OBRIGATÓRIO após cirurgia em quants já com reserved=0)
  python operar_reserva.py --zerar-residual --quant-ids 258975,258988,258958 --confirmar

Exit: 0 efetivado · 4 dry-run OK · 1 falha · 2 uso.
"""
import argparse
import json
import sys
from pathlib import Path

_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parents[4]))

from app import create_app  # noqa: E402
from app.odoo.estoque.scripts.reserva import StockReservaService  # noqa: E402
from app.odoo.utils.connection import get_odoo_connection  # noqa: E402

_FALHAS = {
    'FALHA_PICKING_NAO_EXISTE', 'FALHA_PICKING_STATE_INVALIDO', 'FALHA_ODOO',
}
_OK_STATUSES = {
    'CIRURGIA_OK', 'PICKING_CANCELADO', 'PICKING_UNRESERVED',
    'NOOP', 'ORPHAN_MLS_LISTED',
}


def _ids(csv: str):
    return [int(s) for s in csv.split(',') if s.strip()]


def _moves_writes(csv: str) -> dict:
    """Parse 'm1:q1,m2:q2,...' em {move_id: product_uom_qty}.
    Para zerar use ':0'. Para ajustar use ':<valor>'."""
    out = {}
    for token in csv.split(','):
        if not token.strip():
            continue
        mid, qty = token.split(':')
        out[int(mid)] = float(qty)
    return out


def _emitir(out: dict, dry_run: bool, read_only: bool = False) -> int:
    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
    status = out.get('status', '')
    if status in _FALHAS:
        return 1
    if read_only:
        # READ-only modes: ORPHAN_MLS_LISTED = sucesso
        return 0 if status in _OK_STATUSES else 1
    if dry_run:
        return 4 if status == 'DRY_RUN_OK' else (0 if status == 'NOOP' else 1)
    return 0 if status in _OK_STATUSES else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or '').split('\n')[0])
    ap.add_argument('--picking-id', type=int,
                    help='ID do picking (cirurgia/--cancelar-picking/--unreserve-picking)')
    ap.add_argument('--moves-writes',
                    help='Cirurgia: "m1:qty1,m2:qty2,..." (ex.: "1075205:0.1986,1075207:0")')
    ap.add_argument('--ml-ids', help='Cirurgia: IDs das stock.move.line a unlink')
    ap.add_argument('--cancelar-picking', action='store_true',
                    help='Cancela picking inteiro via action_cancel')
    ap.add_argument('--unreserve-picking', action='store_true',
                    help='[NOVO v7] Libera reservas mantendo picking (do_unreserve)')
    ap.add_argument('--find-orphan', action='store_true',
                    help='[NOVO v7] READ-only: lista MLs orfas (quants zerados c/ ML)')
    ap.add_argument('--zerar-residual', action='store_true',
                    help='Modo cleanup: zera reserved_quantity de N quants (use APÓS cirurgia)')
    ap.add_argument('--quant-ids',
                    help='[--zerar-residual / --find-orphan] IDs dos quants')
    ap.add_argument('--states',
                    help='[--find-orphan] States das MLs (csv). '
                         'Default=assigned,partially_available')
    ap.add_argument('--confirmar', action='store_true')
    args = ap.parse_args()

    # Validar modo
    modos_ativos = sum([
        bool(args.zerar_residual),
        bool(args.cancelar_picking),
        bool(args.unreserve_picking),
        bool(args.find_orphan),
        bool(args.moves_writes or args.ml_ids),  # cirurgia
    ])
    if modos_ativos == 0:
        ap.error(
            'escolha um modo: --find-orphan | --zerar-residual | '
            '--cancelar-picking | --unreserve-picking | '
            'cirurgia (--moves-writes/--ml-ids)'
        )
    if modos_ativos > 1:
        ap.error('modos mutuamente exclusivos')

    dry_run = not args.confirmar
    read_only = args.find_orphan
    app = create_app()
    with app.app_context():
        odoo = get_odoo_connection()
        svc = StockReservaService(odoo=odoo)

        if args.find_orphan:
            if not args.quant_ids:
                ap.error('--find-orphan exige --quant-ids')
            quant_ids = _ids(args.quant_ids)
            states = (
                [s.strip() for s in args.states.split(',') if s.strip()]
                if args.states else None
            )
            res = svc.find_orphan_mls(quant_ids, states=states)
        elif args.zerar_residual:
            if not args.quant_ids:
                ap.error('--zerar-residual exige --quant-ids')
            quant_ids = _ids(args.quant_ids)
            res = svc.zerar_reserved_residual(quant_ids, dry_run=dry_run)
        elif args.unreserve_picking:
            if not args.picking_id:
                ap.error('--unreserve-picking exige --picking-id')
            res = svc.unreserve_picking(args.picking_id, dry_run=dry_run)
        elif args.cancelar_picking:
            if not args.picking_id:
                ap.error('--cancelar-picking exige --picking-id')
            res = svc.cancelar_picking_inteiro(args.picking_id, dry_run=dry_run)
        else:
            if not args.picking_id:
                ap.error('cirurgia exige --picking-id')
            moves_writes = _moves_writes(args.moves_writes) if args.moves_writes else {}
            ml_ids = _ids(args.ml_ids) if args.ml_ids else []
            res = svc.cancelar_moves_orfaos(
                picking_id=args.picking_id,
                ml_ids=ml_ids,
                moves_writes=moves_writes,
                dry_run=dry_run,
            )
        return _emitir(res, dry_run, read_only=read_only)


if __name__ == '__main__':
    sys.exit(main())
