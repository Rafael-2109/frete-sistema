"""operar_mo.py — skill `operando-mo-odoo`: cancelar MO (single ou batch).

Expoe StockMOService.cancelar_mo via CLI. Default seguro:
- `--dry-run` (sem `--confirmar`) so calcula o plano (exit 4).
- consumo > 0 BLOQUEIA cancelamento (G-MO-01 furo contabil); para reverter
  consumo, usar mrp.unbuild via fluxo cross-skill (ver memoria
  [[reaproveitar-semiacabado-orfao-mo-cancelada]]).

Modos (--modo eh OBRIGATORIO; V1 so cobre cancelar):
  cancelar:  --mo-id <id> [--motivo "..."]                    (single)
             [--create-de Y-M-D] [--create-ate Y-M-D]         (batch — filtros)
             [--states draft,confirmed,progress,to_close]
             [--empresas 1,4,5]
             [--consumo zero|qualquer]   (default zero)
             [--limite N]

Exemplos:
  python operar_mo.py --modo cancelar --mo-id 19713
  python operar_mo.py --modo cancelar --mo-id 19713 --motivo "zumbi" --confirmar
  python operar_mo.py --modo cancelar --create-ate 2025-06-01 --empresas 1 --consumo zero
  python operar_mo.py --modo cancelar --create-ate 2025-06-01 --empresas 1 --consumo zero --limite 1 --confirmar
  python operar_mo.py --modo cancelar --create-ate 2025-06-01 --empresas 1,4 --consumo zero --confirmar

Exit: 0 efetivado · 4 dry-run OK · 1 falha · 2 uso.
"""
import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parents[4]))

from app.odoo.estoque._cli_utils import (  # noqa: E402
    adicionar_args_padrao, setup_cli_completo,
)
from app.odoo.estoque.scripts.mo import StockMOService  # noqa: E402
from app.utils.timezone import agora_brasil_naive  # noqa: E402  # timezone

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-7s %(name)s | %(message)s',
)
logger = logging.getLogger('operar_mo')


_FALHAS = {
    'FALHA',
    'FALHA_FURO_CONTABIL',
    'FALHA_STATE_NAO_CANCELAVEL',
    'FALHA_STATE_INESPERADO',
}
_OKS = {'EXECUTADO', 'NOOP'}
_DRY_OKS = {
    'DRY_RUN_OK', 'DRY_RUN_NOOP',
    # Dry-runs que ja preveem falha sao SUCESSO da CLI (plano valido), mas
    # retornamos exit 4 (operacao nao efetivada) e o usuario sabe que real
    # bloqueara.
    'DRY_RUN_FALHA_FURO_CONTABIL',
    'DRY_RUN_FALHA_STATE_NAO_CANCELAVEL',
}


def _emitir(out: Dict[str, Any], dry_run: bool) -> int:
    """Imprime JSON e retorna exit code conforme status."""
    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))

    # Batch
    if 'contagem_status' in out:
        contagem = out['contagem_status']
        if dry_run:
            # Em dry-run, sucesso = sem FALHAs nao previstas (FALHA generica)
            if 'FALHA' in contagem:
                return 1
            return 4
        # Real: 0 se nenhum FALHA*; 1 se houver falhas
        for st in contagem:
            if st.startswith('FALHA'):
                return 1
        return 0

    # Single
    status = out.get('status', '')
    if status in _FALHAS:
        return 1
    if dry_run:
        if status in _DRY_OKS:
            return 4
        return 1
    return 0 if status in _OKS else 1


def cancelar_single(svc: StockMOService, mo_id: int,
                    motivo: str, dry_run: bool) -> Dict[str, Any]:
    """Cancela 1 MO via service (delega tudo — guards no service)."""
    out: Dict[str, Any] = {
        'modo': 'cancelar',
        'tipo': 'single',
        'ts_inicio': agora_brasil_naive().isoformat(timespec='seconds'),
        'dry_run': dry_run,
    }
    r = svc.cancelar_mo(mo_id, motivo=motivo, dry_run=dry_run)
    out.update(r)
    return out


def cancelar_batch(
    svc: StockMOService,
    *,
    create_de: Optional[str],
    create_ate: Optional[str],
    states: List[str],
    empresas: List[int],
    consumo: str,
    limite: int,
    motivo: str,
    dry_run: bool,
) -> Dict[str, Any]:
    """Cancela MOs em massa por criterio (delega ao service)."""
    t0 = time.time()
    out: Dict[str, Any] = {
        'modo': 'cancelar',
        'tipo': 'batch',
        'ts_inicio': agora_brasil_naive().isoformat(timespec='seconds'),
        'dry_run': dry_run,
    }
    res = svc.cancelar_mos_em_massa(
        create_de=create_de, create_ate=create_ate,
        states=states, empresas=empresas, consumo=consumo,
        max_n=limite, motivo=motivo, dry_run=dry_run,
    )
    out.update(res)
    out['tempo_total_ms'] = int((time.time() - t0) * 1000)
    return out


def _salvar_log(out: Dict[str, Any], dry_run: bool) -> Optional[str]:
    """Salva log JSON em scripts/inventario_2026_05/auditoria/."""
    try:
        base = Path(__file__).resolve().parents[4] / 'scripts' / 'inventario_2026_05' / 'auditoria'
        base.mkdir(parents=True, exist_ok=True)
        ts = agora_brasil_naive().strftime('%Y%m%d_%H%M%S')
        sufixo = 'dryrun' if dry_run else 'real'
        nome = f'log_skill4_mo_{sufixo}_{ts}.json'
        path = base / nome
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(out, f, ensure_ascii=False, indent=2, default=str)
        logger.info(f'Log salvo: {path}')
        return str(path)
    except Exception as exc:
        logger.warning(f'Falha ao salvar log: {exc}')
        return None


def main() -> int:
    ap = argparse.ArgumentParser(
        description='operando-mo-odoo: cancelar Manufacturing Orders no Odoo',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument('--modo', required=True, choices=['cancelar'])
    ap.add_argument('--mo-id', type=int, default=0,
                    help='ID de MO especifica (single mode)')
    ap.add_argument('--motivo', default='', help='Motivo do cancelamento (auditoria)')
    # Filtros batch
    ap.add_argument('--create-de', default='',
                    help='YYYY-MM-DD inclusivo (batch — filtro create_date >=)')
    ap.add_argument('--create-ate', default='',
                    help='YYYY-MM-DD exclusivo (batch — filtro create_date <)')
    ap.add_argument('--states', default='draft,confirmed,progress,to_close',
                    help='states cancelaveis (CSV)')
    ap.add_argument('--empresas', default='1,4,5',
                    help='company_id (CSV: 1=FB, 4=CD, 5=LF)')
    ap.add_argument('--consumo', choices=['zero', 'qualquer'], default='zero',
                    help='zero = bloqueia G-MO-01 (default seguro); '
                         'qualquer = inclui MOs com consumo>0 (mas guard ainda '
                         'bloqueia por MO individual)')
    ap.add_argument('--limite', type=int, default=0,
                    help='limite N MOs (canary). 0 = sem limite')
    # Execucao
    ap.add_argument('--dry-run', action='store_true', default=True,
                    help='nao chama action_cancel (default)')
    ap.add_argument('--confirmar', action='store_true', default=False,
                    help='executa action_cancel real')
    adicionar_args_padrao(ap)  # --quiet + --forcar-concorrencia (v7)
    args = ap.parse_args()

    if args.confirmar:
        args.dry_run = False

    # Validacao single OR batch (mutex)
    if args.mo_id and (args.create_de or args.create_ate):
        logger.error(
            'Use OU --mo-id (single) OU filtros batch (--create-de/--create-ate). '
            'Nao ambos.'
        )
        return 2

    # Em batch, exigir pelo menos 1 filtro restritivo se nao for canary
    if not args.mo_id and not (args.create_de or args.create_ate) and not args.limite:
        logger.error(
            'Batch sem filtros e perigoso (cancelaria milhares de MOs). '
            'Use --create-de/--create-ate ou --limite N como minimo.'
        )
        return 2

    app = setup_cli_completo(__file__, args.quiet, args.forcar_concorrencia)
    with app.app_context():
        svc = StockMOService()

        if args.mo_id:
            out = cancelar_single(svc, args.mo_id, args.motivo, args.dry_run)
        else:
            states = [s.strip() for s in args.states.split(',') if s.strip()]
            empresas = [int(x) for x in args.empresas.split(',') if x.strip()]
            out = cancelar_batch(
                svc,
                create_de=(args.create_de or None),
                create_ate=(args.create_ate or None),
                states=states, empresas=empresas, consumo=args.consumo,
                limite=args.limite, motivo=args.motivo, dry_run=args.dry_run,
            )

        # Sempre salvar log (mesmo dry-run) — auditoria
        log_path = _salvar_log(out, args.dry_run)
        if log_path:
            out['log_path'] = log_path

        return _emitir(out, args.dry_run)


if __name__ == '__main__':
    sys.exit(main())
