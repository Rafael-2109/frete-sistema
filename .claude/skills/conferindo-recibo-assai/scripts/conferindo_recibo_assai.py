#!/usr/bin/env python3
"""
Script: conferindo_recibo_assai.py

Skill READ + WRITE para operar conferencia de recibos Motochefe (Motos Assai
B2B Q.P.A.). Cobre:
  - READ: listar recibos pendentes / detalhe de recibo (conferidos, faltantes,
    divergencias).
  - WRITE: registrar conferencia de chassi e finalizar recibo (com dry-run
    obrigatorio antes de --confirmar).

Uso (READ):
    --listar-pendentes
    --recibo-id <id>

Uso (WRITE; sempre exige --user-id e --confirmar para executar de fato):
    --registrar-chassi --recibo-id <id> --chassi <X> --modelo-id <m> --cor <c> \\
        --user-id <u> [--confirmar] [--avaria-fisica]
    --finalizar-recibo --recibo-id <id> --user-id <u> [--confirmar] \\
        [--confirmar-faltantes]

Exit codes:
    0 - sucesso
    1 - validacao falhou (RecebimentoValidationError)
    2 - erro infra (DB / app boot)
    3 - usuario nao autorizado (sem flag sistema_motos_assai)
    4 - confirmacao faltando (dry-run default sem --confirmar)
    5 - conflito 409 (RecebimentoConflictError; pode retry)
"""
import sys
import os
import json
import argparse
import contextlib
import io
from datetime import datetime, date
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

# Suprimir logs barulhentos durante create_app() para nao poluir stdout
with contextlib.redirect_stdout(io.StringIO()):
    from app import create_app, db  # noqa: E402


def _json_default(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    return str(obj)


def _verificar_autorizacao(user_id):
    from app.auth.models import Usuario
    u = Usuario.query.get(user_id)
    if not u:
        return False, 'usuario_nao_encontrado'
    if not u.pode_acessar_motos_assai():
        return False, 'sem_permissao_motos_assai'
    return True, None


# ======================================================================
# READ
# ======================================================================

def _serializar_recibo_resumo(recibo):
    """Serializa recibo com totais agregados (sem itens individuais)."""
    from app.motos_assai.models import AssaiReciboItem

    total_itens = AssaiReciboItem.query.filter_by(recibo_id=recibo.id, ativo=True).count()
    total_conferidos = AssaiReciboItem.query.filter_by(
        recibo_id=recibo.id, conferido=True, ativo=True,
    ).count()
    total_divergencias = (
        AssaiReciboItem.query
        .filter(
            AssaiReciboItem.recibo_id == recibo.id,
            AssaiReciboItem.ativo.is_(True),
            AssaiReciboItem.tipo_divergencia.isnot(None),
        )
        .count()
    )

    return {
        'id': recibo.id,
        'numero_recibo': recibo.numero_recibo,
        'compra_id': recibo.compra_id,
        'status': recibo.status,
        'data_recibo': recibo.data_recibo,
        'equipe': recibo.equipe,
        'conferente_motochefe': recibo.conferente_motochefe,
        'total_motos_declarado': recibo.total_motos_declarado,
        'total_itens': total_itens,
        'total_conferidos': total_conferidos,
        'total_divergencias': total_divergencias,
        'criado_em': recibo.criado_em,
    }


def _serializar_item(item):
    return {
        'id': item.id,
        'chassi': item.chassi,
        'modelo_id': item.modelo_id,
        'modelo_texto_recibo': item.modelo_texto_recibo,
        'cor_texto': item.cor_texto,
        'motor': item.motor,
        'conferido': item.conferido,
        'qr_code_lido': item.qr_code_lido,
        'tipo_divergencia': item.tipo_divergencia,
        'foto_s3_key': item.foto_s3_key,
        'ativo': item.ativo,
    }


def _read_listar_pendentes():
    from app.motos_assai.models import (
        AssaiReciboMotochefe,
        RECIBO_STATUS_AGUARDANDO, RECIBO_STATUS_EM_CONFERENCIA,
    )

    recibos = (
        AssaiReciboMotochefe.query
        .filter(AssaiReciboMotochefe.status.in_([
            RECIBO_STATUS_AGUARDANDO, RECIBO_STATUS_EM_CONFERENCIA,
        ]))
        .order_by(AssaiReciboMotochefe.id.desc())
        .limit(50)
        .all()
    )

    out = [_serializar_recibo_resumo(r) for r in recibos]
    return {
        'modo': 'listar_pendentes',
        'recibos': out,
        'total': len(out),
        'exit_code': 0,
    }


def _read_detalhe_recibo(recibo_id):
    from app.motos_assai.models import (
        AssaiReciboMotochefe, AssaiReciboItem,
    )

    recibo = AssaiReciboMotochefe.query.get(recibo_id)
    if not recibo:
        return {
            'modo': 'detalhe_recibo',
            'encontrado': False,
            'recibo_id': recibo_id,
            'mensagem': f'Recibo {recibo_id} nao encontrado',
            'exit_code': 0,
        }

    itens_todos = (
        AssaiReciboItem.query
        .filter_by(recibo_id=recibo_id)
        .order_by(AssaiReciboItem.id.asc())
        .all()
    )
    itens = [i for i in itens_todos if i.ativo]
    inativos = [_serializar_item(i) for i in itens_todos if not i.ativo]
    conferidos = [_serializar_item(i) for i in itens if i.conferido]
    faltantes = [_serializar_item(i) for i in itens if not i.conferido]
    divergencias = [
        _serializar_item(i) for i in itens if i.tipo_divergencia is not None
    ]

    return {
        'modo': 'detalhe_recibo',
        'encontrado': True,
        'recibo': {
            'id': recibo.id,
            'numero_recibo': recibo.numero_recibo,
            'compra_id': recibo.compra_id,
            'status': recibo.status,
            'data_recibo': recibo.data_recibo,
            'equipe': recibo.equipe,
            'conferente_motochefe': recibo.conferente_motochefe,
            'total_motos_declarado': recibo.total_motos_declarado,
            'criado_em': recibo.criado_em,
        },
        'itens_conferidos': conferidos,
        'itens_faltantes': faltantes,
        'itens_inativos': inativos,
        'divergencias': divergencias,
        'totais': {
            'declarado': recibo.total_motos_declarado or 0,
            'no_recibo': len(itens),
            'conferidos': len(conferidos),
            'faltantes': len(faltantes),
            'inativos': len(inativos),
            'divergencias': len(divergencias),
        },
        'exit_code': 0,
    }


# ======================================================================
# WRITE
# ======================================================================

def _write_registrar_chassi(args):
    """Registra conferencia de 1 chassi.

    Dry-run default. Exige --confirmar para executar.
    """
    from app.motos_assai.services.recebimento_service import (
        registrar_conferencia,
        RecebimentoConflictError, RecebimentoValidationError,
    )

    # Autorizacao
    ok, motivo = _verificar_autorizacao(args.user_id)
    if not ok:
        return {
            'modo': 'registrar_chassi',
            'ok': False,
            'error': motivo,
            'exit_code': 3,
        }

    chassi_norm = (args.chassi or '').strip().upper()
    preview = {
        'recibo_id': args.recibo_id,
        'chassi': chassi_norm,
        'modelo_id': args.modelo_id,
        'cor': args.cor,
        'avaria_fisica': bool(args.avaria_fisica),
        'user_id': args.user_id,
    }

    if not args.confirmar:
        return {
            'modo': 'registrar_chassi',
            'dry_run': True,
            'preview': preview,
            'mensagem': 'Dry-run. Use --confirmar para executar de fato.',
            'exit_code': 4,
        }

    # Executa
    try:
        item = registrar_conferencia(
            recibo_id=args.recibo_id,
            chassi=chassi_norm,
            modelo_conferido_id=args.modelo_id,
            cor_conferida=args.cor,
            qr_code_lido=False,
            foto_s3_key=None,
            operador_id=args.user_id,
            avaria_fisica=bool(args.avaria_fisica),
        )
        return {
            'modo': 'registrar_chassi',
            'dry_run': False,
            'ok': True,
            'item_id': item.id,
            'chassi': item.chassi,
            'tipo_divergencia': item.tipo_divergencia,
            'exit_code': 0,
        }
    except RecebimentoConflictError as e:
        return {
            'modo': 'registrar_chassi',
            'dry_run': False,
            'ok': False,
            'error': str(e),
            'retry': True,
            'exit_code': 5,
        }
    except RecebimentoValidationError as e:
        return {
            'modo': 'registrar_chassi',
            'dry_run': False,
            'ok': False,
            'error': str(e),
            'exit_code': 1,
        }


def _write_finalizar_recibo(args):
    """Finaliza recibo. Marca todos faltantes como MOTO_FALTANDO se confirmado."""
    from app.motos_assai.services.recebimento_service import (
        finalizar_recebimento,
        RecebimentoConflictError, RecebimentoValidationError,
    )

    # Autorizacao
    ok, motivo = _verificar_autorizacao(args.user_id)
    if not ok:
        return {
            'modo': 'finalizar_recibo',
            'ok': False,
            'error': motivo,
            'exit_code': 3,
        }

    preview = {
        'recibo_id': args.recibo_id,
        'confirmar_faltantes': bool(args.confirmar_faltantes),
        'user_id': args.user_id,
    }

    if not args.confirmar:
        return {
            'modo': 'finalizar_recibo',
            'dry_run': True,
            'preview': preview,
            'mensagem': 'Dry-run. Use --confirmar para executar de fato.',
            'exit_code': 4,
        }

    try:
        recibo = finalizar_recebimento(
            recibo_id=args.recibo_id,
            operador_id=args.user_id,
            confirmar_faltantes=bool(args.confirmar_faltantes),
        )
        return {
            'modo': 'finalizar_recibo',
            'dry_run': False,
            'ok': True,
            'recibo_id': recibo.id,
            'status': recibo.status,
            'exit_code': 0,
        }
    except RecebimentoConflictError as e:
        return {
            'modo': 'finalizar_recibo',
            'dry_run': False,
            'ok': False,
            'error': str(e),
            'retry': True,
            'exit_code': 5,
        }
    except RecebimentoValidationError as e:
        return {
            'modo': 'finalizar_recibo',
            'dry_run': False,
            'ok': False,
            'error': str(e),
            'hint': 'Reexecute com --confirmar-faltantes',
            'exit_code': 1,
        }


# ======================================================================
# Dispatch
# ======================================================================

def _run(args):
    if args.listar_pendentes:
        return _read_listar_pendentes()
    if args.recibo_id and not (args.registrar_chassi or args.finalizar_recibo):
        return _read_detalhe_recibo(args.recibo_id)
    if args.registrar_chassi:
        return _write_registrar_chassi(args)
    if args.finalizar_recibo:
        return _write_finalizar_recibo(args)

    # Default: listar pendentes
    return _read_listar_pendentes()


def main():
    parser = argparse.ArgumentParser(prog='conferindo_recibo_assai')

    # READ
    parser.add_argument('--listar-pendentes', action='store_true',
                        help='Lista recibos com status AGUARDANDO/EM_CONFERENCIA')
    parser.add_argument('--recibo-id', type=int,
                        help='ID do recibo (detalhe READ ou alvo WRITE)')

    # WRITE — modos
    parser.add_argument('--registrar-chassi', action='store_true',
                        help='WRITE: registrar conferencia de chassi')
    parser.add_argument('--finalizar-recibo', action='store_true',
                        help='WRITE: finalizar recibo')

    # WRITE — registrar-chassi
    parser.add_argument('--chassi', help='Numero do chassi (registrar-chassi)')
    parser.add_argument('--modelo-id', type=int,
                        help='ID do modelo conferido (registrar-chassi)')
    parser.add_argument('--cor', help='Cor conferida (registrar-chassi)')
    parser.add_argument('--avaria-fisica', action='store_true',
                        help='Marca AVARIA_FISICA (registrar-chassi)')

    # WRITE — finalizar-recibo
    parser.add_argument('--confirmar-faltantes', action='store_true',
                        help='Confirma marcar faltantes como MOTO_FALTANDO')

    # WRITE — comum
    parser.add_argument('--user-id', type=int,
                        help='ID do usuario operador (obrigatorio em WRITE)')
    parser.add_argument('--confirmar', action='store_true',
                        help='Sai do dry-run e executa de fato')

    args = parser.parse_args()

    # Validacoes preliminares de WRITE
    if args.registrar_chassi:
        if not args.user_id:
            err = {'modo': 'registrar_chassi', 'ok': False,
                   'error': '--user-id obrigatorio em WRITE', 'exit_code': 1}
            print(json.dumps(err, ensure_ascii=False, indent=2))
            return 1
        if not args.recibo_id:
            err = {'modo': 'registrar_chassi', 'ok': False,
                   'error': '--recibo-id obrigatorio', 'exit_code': 1}
            print(json.dumps(err, ensure_ascii=False, indent=2))
            return 1
        if not args.chassi:
            err = {'modo': 'registrar_chassi', 'ok': False,
                   'error': '--chassi obrigatorio', 'exit_code': 1}
            print(json.dumps(err, ensure_ascii=False, indent=2))
            return 1
        if not args.modelo_id:
            err = {'modo': 'registrar_chassi', 'ok': False,
                   'error': '--modelo-id obrigatorio', 'exit_code': 1}
            print(json.dumps(err, ensure_ascii=False, indent=2))
            return 1

    if args.finalizar_recibo:
        if not args.user_id:
            err = {'modo': 'finalizar_recibo', 'ok': False,
                   'error': '--user-id obrigatorio em WRITE', 'exit_code': 1}
            print(json.dumps(err, ensure_ascii=False, indent=2))
            return 1
        if not args.recibo_id:
            err = {'modo': 'finalizar_recibo', 'ok': False,
                   'error': '--recibo-id obrigatorio', 'exit_code': 1}
            print(json.dumps(err, ensure_ascii=False, indent=2))
            return 1

    try:
        with contextlib.redirect_stdout(io.StringIO()):
            app = create_app()
        with app.app_context():
            result = _run(args)
        print(json.dumps(result, default=_json_default, ensure_ascii=False, indent=2))
        return result.get('exit_code', 0)
    except Exception as e:
        err = {'ok': False, 'error': str(e), 'exit_code': 2}
        print(json.dumps(err), file=sys.stderr)
        print(json.dumps(err))
        return 2


if __name__ == '__main__':
    sys.exit(main())
