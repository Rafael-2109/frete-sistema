"""operar_mo.py — skill `operando-mo-odoo`: listar/detalhar/cancelar MO.

Expoe StockMOService via CLI. 3 modos:
  - listar (READ): lista MOs com classificacao SEGURO/RESERVA_FANTASMA/FURO_REAL
  - detalhar (READ): detalhamento de 1 MO (raws+finished+MLs+consumo)
  - cancelar (WRITE): action_cancel com guard G-MO-01 v6

Default seguro (cancelar):
- `--dry-run` (sem `--confirmar`) so calcula o plano (exit 4).
- consumo DONE > 0 BLOQUEIA cancelamento (G-MO-01 v6 = furo contabil REAL);
  reserva fantasma (assigned/waiting/picked) PASSA com warning. Para reverter
  furo real, usar mrp.unbuild via fluxo cross-skill (ver memoria
  memoria local Claude Code [[reaproveitar-semiacabado-orfao-mo-cancelada]]).

Modos:
  listar:    [--create-de Y-M-D] [--create-ate Y-M-D]
             [--states draft,confirmed,progress,to_close]
             [--empresas 1,4,5] [--limite N]
             (READ — bloqueia --confirmar)
  detalhar:  --mo-id <id>
             (READ — bloqueia --confirmar)
  cancelar:  --mo-id <id> [--motivo "..."] [--with-audit]   (single, audit default ON)
             OU (batch — todos os filtros idem listar)
             [--consumo zero|qualquer] [--with-audit]

Exemplos:
  python operar_mo.py --modo listar --create-ate 2026-05-15 --empresas 1,4,5
  python operar_mo.py --modo detalhar --mo-id 19713
  python operar_mo.py --modo cancelar --mo-id 19713
  python operar_mo.py --modo cancelar --mo-id 19713 --motivo "zumbi" --confirmar
  python operar_mo.py --modo cancelar --create-ate 2025-06-01 --empresas 1 --consumo zero
  python operar_mo.py --modo cancelar --create-ate 2025-06-01 --empresas 1 --consumo zero --limite 1 --confirmar
  python operar_mo.py --modo cancelar --mo-ids 17449,18108 --confirmar --with-audit

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
    'FALHA_FURO_CONTABIL',        # V5 legacy (alias deprecated)
    'FALHA_FURO_CONTABIL_REAL',   # V6 (done > 0)
    'FALHA_STATE_NAO_CANCELAVEL',
    'FALHA_STATE_INESPERADO',
}
_OKS = {'EXECUTADO', 'NOOP', 'OK_RESERVA_FANTASMA'}  # V6: fantasma OK
_DRY_OKS = {
    'DRY_RUN_OK', 'DRY_RUN_NOOP',
    'DRY_RUN_OK_RESERVA_FANTASMA',  # V6: passa o guard
    # Dry-runs que ja preveem falha sao SUCESSO da CLI (plano valido), mas
    # retornamos exit 4 (operacao nao efetivada) e o usuario sabe que real
    # bloqueara.
    'DRY_RUN_FALHA_FURO_CONTABIL',        # V5 legacy
    'DRY_RUN_FALHA_FURO_CONTABIL_REAL',   # V6
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
                    motivo: str, dry_run: bool,
                    with_audit: bool = True) -> Dict[str, Any]:
    """Cancela 1 MO via service. Audit pre/pos default ON em single."""
    out: Dict[str, Any] = {
        'modo': 'cancelar',
        'tipo': 'single',
        'ts_inicio': agora_brasil_naive().isoformat(timespec='seconds'),
        'dry_run': dry_run,
        'with_audit': with_audit,
    }
    if with_audit:
        r = svc.cancelar_mo_com_audit(mo_id, motivo=motivo, dry_run=dry_run)
    else:
        r = svc.cancelar_mo(mo_id, motivo=motivo, dry_run=dry_run)
    out.update(r)
    return out


def listar(svc: StockMOService, *, create_de: Optional[str],
           create_ate: Optional[str], states: List[str],
           empresas: List[int], limite: int) -> Dict[str, Any]:
    """Lista MOs com classificacao (READ — sem WRITE)."""
    out: Dict[str, Any] = {
        'modo': 'listar',
        'ts_inicio': agora_brasil_naive().isoformat(timespec='seconds'),
    }
    res = svc.listar_mos(
        create_de=create_de, create_ate=create_ate,
        states=states, empresas=empresas, max_n=limite,
    )
    out.update(res)
    return out


def detalhar(svc: StockMOService, mo_id: int) -> Dict[str, Any]:
    """Detalha 1 MO (READ — sem WRITE)."""
    out: Dict[str, Any] = {
        'modo': 'detalhar',
        'ts_inicio': agora_brasil_naive().isoformat(timespec='seconds'),
    }
    out.update(svc.detalhar_mo(mo_id))
    return out


def cancelar_batch(
    svc: StockMOService,
    *,
    mo_ids: Optional[List[int]] = None,
    create_de: Optional[str] = None,
    create_ate: Optional[str] = None,
    states: Optional[List[str]] = None,
    empresas: Optional[List[int]] = None,
    consumo: str = 'zero',
    limite: int = 0,
    motivo: str = '',
    dry_run: bool = False,
    with_audit: bool = False,
) -> Dict[str, Any]:
    """Cancela MOs em massa. mo_ids explicito OU criterio.

    with_audit (default OFF em batch — custa +1-2s/MO; ON quando o usuario
    quer JSON de auditoria estruturado).
    """
    t0 = time.time()
    out: Dict[str, Any] = {
        'modo': 'cancelar',
        'tipo': 'batch',
        'ts_inicio': agora_brasil_naive().isoformat(timespec='seconds'),
        'dry_run': dry_run,
        'with_audit': with_audit,
    }

    # Lista explicita de IDs (sem search): delega individual sem filtro de criterio.
    if mo_ids:
        resultados: List[Dict[str, Any]] = []
        from collections import defaultdict as _dd
        contagem: Dict[str, int] = _dd(int)
        for mid in mo_ids:
            if with_audit:
                r = svc.cancelar_mo_com_audit(mid, motivo=motivo, dry_run=dry_run)
            else:
                r = svc.cancelar_mo(mid, motivo=motivo, dry_run=dry_run)
            resultados.append(r)
            contagem[r['status']] += 1
        out.update({
            'criterio': {'mo_ids': mo_ids, 'motivo': motivo, 'dry_run': dry_run},
            'total_pre_filtro': len(mo_ids),
            'total_candidatas': len(mo_ids),
            'total_filtradas_por_consumo': 0,
            'contagem_status': dict(contagem),
            'resultados': resultados,
        })
    else:
        res = svc.cancelar_mos_em_massa(
            create_de=create_de, create_ate=create_ate,
            states=states, empresas=empresas, consumo=consumo,
            max_n=limite, motivo=motivo, dry_run=dry_run,
        )
        # Se with_audit, re-processar cada resultado via cancelar_mo_com_audit
        # nao e' eficiente — em vez disso o caminho explicito --mo-ids cobre o caso.
        # Documentar: --with-audit em batch (sem --mo-ids) tem efeito limitado.
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
        description='operando-mo-odoo: listar/detalhar/cancelar Manufacturing Orders no Odoo',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument('--modo', required=True, choices=['listar', 'detalhar', 'cancelar'])
    ap.add_argument('--mo-id', type=int, default=0,
                    help='ID de MO (detalhar OU cancelar single)')
    ap.add_argument('--mo-ids', default='',
                    help='CSV de IDs (cancelar batch explicito; ex: 17449,18108)')
    ap.add_argument('--motivo', default='', help='Motivo do cancelamento (auditoria)')
    # Filtros (listar + cancelar batch)
    ap.add_argument('--create-de', default='',
                    help='YYYY-MM-DD inclusivo (filtro create_date >=)')
    ap.add_argument('--create-ate', default='',
                    help='YYYY-MM-DD exclusivo (filtro create_date <)')
    ap.add_argument('--states', default='draft,confirmed,progress,to_close',
                    help='states cancelaveis (CSV)')
    ap.add_argument('--empresas', default='1,4,5',
                    help='company_id (CSV: 1=FB, 4=CD, 5=LF)')
    ap.add_argument('--consumo', choices=['zero', 'qualquer'], default='zero',
                    help='cancelar: zero = filtra apenas FURO_REAL (default seguro v6); '
                         'qualquer = inclui MOs com consumo>0 (mas guard bloqueia '
                         'por MO individual)')
    ap.add_argument('--limite', type=int, default=0,
                    help='limite N MOs (canary/paginacao). 0 = sem limite')
    # Audit (cancelar)
    ap.add_argument('--with-audit', action='store_true', default=False,
                    help='cancelar: incluir snapshot pre/pos + diff no JSON (custo +1-2s/MO). '
                         'Default ON em single (--mo-id), OFF em batch.')
    # Execucao
    ap.add_argument('--dry-run', action='store_true', default=True,
                    help='nao chama action_cancel (default)')
    ap.add_argument('--confirmar', action='store_true', default=False,
                    help='cancelar: executa action_cancel real')
    adicionar_args_padrao(ap)
    args = ap.parse_args()

    if args.confirmar:
        args.dry_run = False

    # ============================================================
    # Bloqueio anti-WRITE em modos READ (CLAUDE.md §6.b)
    # ============================================================
    if args.modo in ('listar', 'detalhar') and args.confirmar:
        logger.error(
            f'Modo {args.modo!r} e READ-only — --confirmar nao aceito '
            '(ver app/odoo/estoque/CLAUDE.md §6.b).'
        )
        return 2

    # ============================================================
    # Validacao por modo
    # ============================================================
    if args.modo == 'detalhar':
        if not args.mo_id:
            logger.error('--modo detalhar exige --mo-id <id>')
            return 2

    if args.modo == 'cancelar':
        # Mutex: --mo-id (single) OU --mo-ids/filtros (batch) — nao ambos
        if args.mo_id and (args.create_de or args.create_ate or args.mo_ids):
            logger.error(
                'Use OU --mo-id (single) OU --mo-ids/filtros (batch). Nao ambos.'
            )
            return 2
        # Batch precisa de pelo menos 1 filtro restritivo
        if (not args.mo_id and not args.mo_ids
                and not (args.create_de or args.create_ate) and not args.limite):
            logger.error(
                'Batch sem filtros e perigoso (cancelaria milhares de MOs). '
                'Use --mo-ids, --create-de/--create-ate ou --limite N como minimo.'
            )
            return 2

    app = setup_cli_completo(__file__, args.quiet, args.forcar_concorrencia)
    with app.app_context():
        svc = StockMOService()

        states = [s.strip() for s in args.states.split(',') if s.strip()]
        empresas = [int(x) for x in args.empresas.split(',') if x.strip()]

        if args.modo == 'listar':
            out = listar(
                svc,
                create_de=(args.create_de or None),
                create_ate=(args.create_ate or None),
                states=states, empresas=empresas, limite=args.limite,
            )
        elif args.modo == 'detalhar':
            out = detalhar(svc, args.mo_id)
        else:  # cancelar
            if args.mo_id:
                # Single: audit default ON
                with_audit = args.with_audit if '--with-audit' in sys.argv else True
                out = cancelar_single(
                    svc, args.mo_id, args.motivo, args.dry_run, with_audit=with_audit,
                )
            else:
                # Batch: audit default OFF
                mo_ids = [int(x) for x in args.mo_ids.split(',') if x.strip()] if args.mo_ids else None
                out = cancelar_batch(
                    svc,
                    mo_ids=mo_ids,
                    create_de=(args.create_de or None),
                    create_ate=(args.create_ate or None),
                    states=states, empresas=empresas, consumo=args.consumo,
                    limite=args.limite, motivo=args.motivo, dry_run=args.dry_run,
                    with_audit=args.with_audit,
                )

        # Sempre salvar log (auditoria)
        log_path = _salvar_log(out, args.dry_run if args.modo == 'cancelar' else True)
        if log_path:
            out['log_path'] = log_path

        # Exit code
        if args.modo in ('listar', 'detalhar'):
            print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
            return 0
        return _emitir(out, args.dry_run)


if __name__ == '__main__':
    sys.exit(main())
