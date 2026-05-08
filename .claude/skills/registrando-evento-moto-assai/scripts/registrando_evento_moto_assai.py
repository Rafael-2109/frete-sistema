#!/usr/bin/env python3
"""
Script: registrando_evento_moto_assai.py

Skill WRITE — transicao de estados de chassis no pipeline Motos Assai.

8 sub-comandos cobrindo o pipeline:
    --montar                          ESTOQUE -> MONTADA
    --montar-pendente                 ESTOQUE -> PENDENTE (+ descricao obrig.)
    --resolver-pendencia              PENDENTE -> MONTADA (via PENDENCIA_RESOLVIDA)
    --disponibilizar                  MONTADA/REVERTIDA_PARA_MONTADA -> DISPONIVEL
    --reverter-disponibilizacao       DISPONIVEL -> REVERTIDA_PARA_MONTADA
    --separar                         DISPONIVEL -> SEPARADA (em pedido/loja)
    --desfazer-separacao              SEPARADA -> DISPONIVEL
    --cancelar-separacao              cancela separacao + devolve chassis

Args obrigatorios sempre: --user-id <id>
Sem --confirmar: preview dry-run (exit 4).
Com --confirmar: efetiva via service.

Exit codes:
    0 - sucesso (efetivado)
    1 - validacao (ValidationError)
    2 - infra (DB / app boot)
    3 - sem autorizacao (pode_acessar_motos_assai=False)
    4 - dry-run preview
    5 - conflito (UNIQUE race)
"""
import sys
import os
import json
import argparse
import contextlib
import io
from datetime import datetime
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

# Suprimir logs barulhentos durante create_app() para nao poluir stdout
with contextlib.redirect_stdout(io.StringIO()):
    from app import create_app, db  # noqa: E402, F401


def _json_default(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    return str(obj)


def _verificar_autorizacao(user_id):
    """Retorna (ok: bool, motivo: Optional[str])."""
    from app.auth.models import Usuario
    u = Usuario.query.get(user_id)
    if not u:
        return False, 'usuario_nao_encontrado'
    if not u.pode_acessar_motos_assai():
        return False, 'sem_permissao_motos_assai'
    return True, None


def _status_efetivo_safe(chassi: str):
    """Wrap status_efetivo com tratamento de erro."""
    try:
        from app.motos_assai.services.moto_evento_service import status_efetivo
        return status_efetivo(chassi)
    except Exception:
        return None


def _resp_dry_run(comando: str, chassi: str = None, **kwargs):
    out = {
        'dry_run': True,
        'comando': comando,
        'exit_code': 4,
    }
    if chassi is not None:
        out['chassi'] = chassi.strip().upper()
        out['status_efetivo_atual'] = _status_efetivo_safe(chassi)
    out.update(kwargs)
    return out


def _resp_validacao(erro: str, **kwargs):
    out = {
        'ok': False,
        'erro': erro,
        'tipo_erro': 'validacao',
        'exit_code': 1,
    }
    out.update(kwargs)
    return out


def _resp_conflito(erro: str, **kwargs):
    out = {
        'ok': False,
        'erro': erro,
        'tipo_erro': 'conflito',
        'retry': True,
        'exit_code': 5,
    }
    out.update(kwargs)
    return out


def _resp_autorizacao(motivo: str, user_id: int):
    return {
        'ok': False,
        'erro': motivo,
        'tipo_erro': 'autorizacao',
        'user_id': user_id,
        'exit_code': 3,
    }


def _resp_ok(comando: str, payload: dict):
    out = {'ok': True, 'comando': comando, 'exit_code': 0}
    out.update(payload or {})
    return out


# ----- Sub-comandos ----------------------------------------------------------

def _cmd_montar(args):
    from app.motos_assai.services.montagem_service import (
        registrar_montagem, MontagemValidationError,
    )
    if not args.confirmar:
        return _resp_dry_run(
            'montar', chassi=args.chassi,
            acao_pretendida='ESTOQUE -> MONTADA',
        )
    try:
        result = registrar_montagem(
            chassi=args.chassi,
            pendencia=False,
            descricao_pendencia=None,
            chassi_doador=None,
            operador_id=args.user_id,
        )
        return _resp_ok('montar', result)
    except MontagemValidationError as e:
        return _resp_validacao(str(e))


def _cmd_montar_pendente(args):
    from app.motos_assai.services.montagem_service import (
        registrar_montagem, MontagemValidationError,
    )
    if not args.descricao:
        return _resp_validacao('--descricao obrigatorio para --montar-pendente')
    if not args.confirmar:
        return _resp_dry_run(
            'montar-pendente', chassi=args.chassi,
            acao_pretendida='ESTOQUE -> PENDENTE',
            descricao=args.descricao,
            chassi_doador=args.chassi_doador,
        )
    try:
        result = registrar_montagem(
            chassi=args.chassi,
            pendencia=True,
            descricao_pendencia=args.descricao,
            chassi_doador=args.chassi_doador,
            operador_id=args.user_id,
        )
        return _resp_ok('montar-pendente', result)
    except MontagemValidationError as e:
        return _resp_validacao(str(e))


def _cmd_resolver_pendencia(args):
    from app.motos_assai.services.montagem_service import (
        resolver_pendencia, MontagemValidationError,
    )
    if not args.descricao:
        return _resp_validacao('--descricao obrigatorio para --resolver-pendencia')
    if not args.confirmar:
        return _resp_dry_run(
            'resolver-pendencia', chassi=args.chassi,
            acao_pretendida='PENDENTE -> MONTADA',
            descricao_resolucao=args.descricao,
        )
    try:
        result = resolver_pendencia(
            chassi=args.chassi,
            descricao_resolucao=args.descricao,
            operador_id=args.user_id,
        )
        return _resp_ok('resolver-pendencia', result)
    except MontagemValidationError as e:
        return _resp_validacao(str(e))


def _cmd_disponibilizar(args):
    from app.motos_assai.services.disponibilizar_service import (
        disponibilizar, DisponibilizarValidationError,
    )
    if not args.confirmar:
        return _resp_dry_run(
            'disponibilizar', chassi=args.chassi,
            acao_pretendida='MONTADA/REVERTIDA -> DISPONIVEL',
        )
    try:
        result = disponibilizar(chassi=args.chassi, operador_id=args.user_id)
        return _resp_ok('disponibilizar', result)
    except DisponibilizarValidationError as e:
        return _resp_validacao(str(e))


def _cmd_reverter_disponibilizacao(args):
    from app.motos_assai.services.disponibilizar_service import (
        reverter_para_montada, DisponibilizarValidationError,
    )
    if not args.motivo:
        return _resp_validacao('--motivo obrigatorio para --reverter-disponibilizacao')
    if not args.confirmar:
        return _resp_dry_run(
            'reverter-disponibilizacao', chassi=args.chassi,
            acao_pretendida='DISPONIVEL -> REVERTIDA_PARA_MONTADA',
            motivo=args.motivo,
        )
    try:
        result = reverter_para_montada(
            chassi=args.chassi, motivo=args.motivo, operador_id=args.user_id,
        )
        return _resp_ok('reverter-disponibilizacao', result)
    except DisponibilizarValidationError as e:
        return _resp_validacao(str(e))


def _cmd_separar(args):
    from app.motos_assai.services.separacao_service import (
        registrar_chassi, SeparacaoValidationError, SeparacaoConflictError,
    )
    if args.pedido_id is None or args.loja_id is None:
        return _resp_validacao(
            '--pedido-id e --loja-id obrigatorios para --separar'
        )
    if not args.confirmar:
        return _resp_dry_run(
            'separar', chassi=args.chassi,
            acao_pretendida='DISPONIVEL -> SEPARADA',
            pedido_id=args.pedido_id, loja_id=args.loja_id,
        )
    try:
        result = registrar_chassi(
            pedido_id=args.pedido_id,
            loja_id=args.loja_id,
            chassi=args.chassi,
            registrada_por_id=args.user_id,
        )
        return _resp_ok('separar', result)
    except SeparacaoConflictError as e:
        return _resp_conflito(str(e))
    except SeparacaoValidationError as e:
        return _resp_validacao(str(e))


def _cmd_desfazer_separacao(args):
    from app.motos_assai.services.separacao_service import (
        desfazer_chassi, SeparacaoValidationError, SeparacaoConflictError,
    )
    if args.item_id is None:
        return _resp_validacao('--item-id obrigatorio para --desfazer-separacao')
    if not args.confirmar:
        return _resp_dry_run(
            'desfazer-separacao',
            acao_pretendida='SEPARADA -> DISPONIVEL',
            item_id=args.item_id,
        )
    try:
        result = desfazer_chassi(
            separacao_item_id=args.item_id, operador_id=args.user_id,
        )
        return _resp_ok('desfazer-separacao', result)
    except SeparacaoConflictError as e:
        return _resp_conflito(str(e))
    except SeparacaoValidationError as e:
        return _resp_validacao(str(e))


def _cmd_cancelar_separacao(args):
    from app.motos_assai.services.separacao_service import (
        cancelar_separacao, SeparacaoValidationError, SeparacaoConflictError,
    )
    if args.separacao_id is None:
        return _resp_validacao('--separacao-id obrigatorio para --cancelar-separacao')
    if not args.motivo:
        return _resp_validacao('--motivo obrigatorio para --cancelar-separacao')
    if not args.confirmar:
        return _resp_dry_run(
            'cancelar-separacao',
            acao_pretendida='separacao -> CANCELADA (chassis voltam DISPONIVEL)',
            separacao_id=args.separacao_id,
            motivo=args.motivo,
        )
    try:
        sep = cancelar_separacao(
            separacao_id=args.separacao_id,
            motivo=args.motivo,
            operador_id=args.user_id,
        )
        return _resp_ok('cancelar-separacao', {
            'separacao_id': sep.id,
            'status': sep.status,
            'motivo_cancelamento': sep.motivo_cancelamento,
        })
    except SeparacaoConflictError as e:
        return _resp_conflito(str(e))
    except SeparacaoValidationError as e:
        return _resp_validacao(str(e))


# ----- Roteador -------------------------------------------------------------

COMANDOS = [
    ('montar', _cmd_montar),
    ('montar_pendente', _cmd_montar_pendente),
    ('resolver_pendencia', _cmd_resolver_pendencia),
    ('disponibilizar', _cmd_disponibilizar),
    ('reverter_disponibilizacao', _cmd_reverter_disponibilizacao),
    ('separar', _cmd_separar),
    ('desfazer_separacao', _cmd_desfazer_separacao),
    ('cancelar_separacao', _cmd_cancelar_separacao),
]


def _selecionar_comando(args):
    """Garante que exatamente 1 comando foi especificado."""
    selecionados = [(nome, fn) for nome, fn in COMANDOS if getattr(args, nome, False)]
    if len(selecionados) == 0:
        return None, 'Nenhum comando especificado. Use --help para ver opcoes.'
    if len(selecionados) > 1:
        nomes = ', '.join(n for n, _ in selecionados)
        return None, f'Apenas um comando por vez. Selecionados: {nomes}'
    return selecionados[0], None


def main():
    parser = argparse.ArgumentParser(
        prog='registrando_evento_moto_assai',
        description='Skill WRITE para transicoes de estado de chassis Motos Assai',
    )
    # 8 comandos exclusivos
    parser.add_argument('--montar', action='store_true', help='ESTOQUE -> MONTADA')
    parser.add_argument('--montar-pendente', action='store_true',
                        dest='montar_pendente', help='ESTOQUE -> PENDENTE')
    parser.add_argument('--resolver-pendencia', action='store_true',
                        dest='resolver_pendencia', help='PENDENTE -> MONTADA')
    parser.add_argument('--disponibilizar', action='store_true',
                        help='MONTADA -> DISPONIVEL')
    parser.add_argument('--reverter-disponibilizacao', action='store_true',
                        dest='reverter_disponibilizacao',
                        help='DISPONIVEL -> REVERTIDA_PARA_MONTADA')
    parser.add_argument('--separar', action='store_true',
                        help='DISPONIVEL -> SEPARADA')
    parser.add_argument('--desfazer-separacao', action='store_true',
                        dest='desfazer_separacao',
                        help='SEPARADA -> DISPONIVEL (item)')
    parser.add_argument('--cancelar-separacao', action='store_true',
                        dest='cancelar_separacao',
                        help='Cancela separacao (chassis voltam DISPONIVEL)')

    # Args dos comandos
    parser.add_argument('--chassi', help='Chassi da moto')
    parser.add_argument('--descricao', help='Descricao (pendencia ou resolucao)')
    parser.add_argument('--motivo', help='Motivo (reverter / cancelar)')
    parser.add_argument('--chassi-doador', dest='chassi_doador',
                        default=None, help='Chassi doador (montar-pendente)')
    parser.add_argument('--pedido-id', type=int, dest='pedido_id',
                        default=None, help='ID do pedido (separar)')
    parser.add_argument('--loja-id', type=int, dest='loja_id',
                        default=None, help='ID da loja (separar)')
    parser.add_argument('--item-id', type=int, dest='item_id',
                        default=None, help='ID do item de separacao (desfazer)')
    parser.add_argument('--separacao-id', type=int, dest='separacao_id',
                        default=None, help='ID da separacao (cancelar)')

    # Auth e confirmacao
    parser.add_argument('--user-id', type=int, required=True,
                        dest='user_id', help='ID do operador (OBRIGATORIO)')
    parser.add_argument('--confirmar', action='store_true',
                        help='Efetiva a operacao (sem isso = dry-run)')

    args = parser.parse_args()

    # Selecionar comando
    selecionado, erro_sel = _selecionar_comando(args)
    if erro_sel:
        out = {
            'ok': False, 'erro': erro_sel,
            'tipo_erro': 'comando_invalido', 'exit_code': 1,
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 1

    nome_cmd, fn_cmd = selecionado

    # Validar args minimos por comando que exigem chassi
    comandos_com_chassi = {
        'montar', 'montar_pendente', 'resolver_pendencia',
        'disponibilizar', 'reverter_disponibilizacao', 'separar',
    }
    if nome_cmd in comandos_com_chassi and not args.chassi:
        out = {
            'ok': False, 'erro': '--chassi obrigatorio para esse comando',
            'tipo_erro': 'validacao', 'exit_code': 1,
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 1

    try:
        with contextlib.redirect_stdout(io.StringIO()):
            app = create_app()
        with app.app_context():
            # Verificar autorizacao primeiro (custo baixo)
            ok_auth, motivo_auth = _verificar_autorizacao(args.user_id)
            if not ok_auth:
                result = _resp_autorizacao(motivo_auth, args.user_id)
            else:
                result = fn_cmd(args)

        print(json.dumps(result, default=_json_default, ensure_ascii=False, indent=2))
        return result.get('exit_code', 0)
    except Exception as e:
        err = {
            'ok': False, 'erro': str(e),
            'tipo_erro': 'infra', 'exit_code': 2,
        }
        print(json.dumps(err, ensure_ascii=False), file=sys.stderr)
        print(json.dumps(err, ensure_ascii=False, indent=2))
        return 2


if __name__ == '__main__':
    sys.exit(main())
