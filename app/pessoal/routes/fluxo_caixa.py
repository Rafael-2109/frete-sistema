"""Rotas da vertente FLUXO DE CAIXA (tela + APIs)."""
from datetime import date, datetime

from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user, login_required

from app.pessoal import pode_acessar_pessoal
from app.pessoal.services import fatura_service, fluxo_caixa_service

fluxo_caixa_bp = Blueprint('pessoal_fluxo_caixa', __name__)


@fluxo_caixa_bp.route('/fluxo-caixa')
@login_required
def index():
    """Tela principal de fluxo de caixa."""
    if not pode_acessar_pessoal(current_user):
        return 'Acesso restrito.', 403

    hoje = date.today()
    ano = request.args.get('ano', hoje.year, type=int)
    mes = request.args.get('mes', hoje.month, type=int)
    meses_ant = request.args.get('meses_anteriores', 6, type=int)
    meses_fut = request.args.get('meses_futuros', 6, type=int)
    saldo_inicial = request.args.get('saldo_inicial', 0.0, type=float)

    return render_template(
        'pessoal/fluxo_caixa.html',
        ano=ano,
        mes=mes,
        meses_anteriores=meses_ant,
        meses_futuros=meses_fut,
        saldo_inicial=saldo_inicial,
    )


# =============================================================================
# APIs
# =============================================================================
@fluxo_caixa_bp.route('/api/fluxo-caixa/serie', methods=['GET'])
@login_required
def api_serie():
    """Serie mensal: entradas/saidas realizadas + provisoes + saldo acumulado."""
    if not pode_acessar_pessoal(current_user):
        return jsonify({'sucesso': False, 'mensagem': 'Acesso restrito.'}), 403

    hoje = date.today()
    ano = request.args.get('ano', hoje.year, type=int)
    mes = request.args.get('mes', hoje.month, type=int)
    meses_ant = request.args.get('meses_anteriores', 6, type=int)
    meses_fut = request.args.get('meses_futuros', 6, type=int)
    saldo_inicial = request.args.get('saldo_inicial', 0.0, type=float)

    try:
        serie = fluxo_caixa_service.fluxo_por_mes(
            ano_ref=ano,
            mes_ref=mes,
            meses_anteriores=meses_ant,
            meses_futuros=meses_fut,
            saldo_inicial=saldo_inicial,
        )
        return jsonify({'sucesso': True, 'serie': serie})
    except Exception as e:
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 500


@fluxo_caixa_bp.route('/api/fluxo-caixa/detalhe', methods=['GET'])
@login_required
def api_detalhe():
    """Detalhe de um mes: entradas, saidas, pagamentos de cartao, provisoes."""
    if not pode_acessar_pessoal(current_user):
        return jsonify({'sucesso': False, 'mensagem': 'Acesso restrito.'}), 403

    hoje = date.today()
    ano = request.args.get('ano', hoje.year, type=int)
    mes = request.args.get('mes', hoje.month, type=int)

    try:
        detalhe = fluxo_caixa_service.detalhe_do_mes(ano, mes)
        return jsonify({'sucesso': True, 'detalhe': detalhe})
    except Exception as e:
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 500


@fluxo_caixa_bp.route(
    '/api/fluxo-caixa/drilldown-fatura/<int:transacao_id>',
    methods=['GET'],
)
@login_required
def api_drilldown_fatura(transacao_id: int):
    """Dado um pagamento de fatura (transacao id), retorna as compras originais."""
    if not pode_acessar_pessoal(current_user):
        return jsonify({'sucesso': False, 'mensagem': 'Acesso restrito.'}), 403

    try:
        dados = fluxo_caixa_service.drilldown_fatura(transacao_id)
        return jsonify({'sucesso': True, 'dados': dados})
    except Exception as e:
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 500


# =============================================================================
# Gerenciamento de fatura <-> pagamento
# =============================================================================
@fluxo_caixa_bp.route('/api/fluxo-caixa/faturas', methods=['GET'])
@login_required
def api_faturas_listar():
    """Lista faturas de cartao com status de vinculo."""
    if not pode_acessar_pessoal(current_user):
        return jsonify({'sucesso': False, 'mensagem': 'Acesso restrito.'}), 403

    conta_id = request.args.get('conta_id', type=int)
    apenas_sem_vinculo = request.args.get('apenas_sem_vinculo', '') == '1'
    limit = request.args.get('limit', 100, type=int)

    try:
        faturas = fatura_service.listar_faturas_com_status(
            conta_id=conta_id,
            apenas_sem_vinculo=apenas_sem_vinculo,
            limit=limit,
        )
        return jsonify({'sucesso': True, 'faturas': faturas})
    except Exception as e:
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 500


@fluxo_caixa_bp.route(
    '/api/fluxo-caixa/faturas/<int:fatura_id>/sugerir-matches',
    methods=['GET'],
)
@login_required
def api_sugerir_matches(fatura_id: int):
    """Sugere transacoes de pagamento candidatas para uma fatura."""
    if not pode_acessar_pessoal(current_user):
        return jsonify({'sucesso': False, 'mensagem': 'Acesso restrito.'}), 403

    tolerancia = request.args.get('tolerancia', 0.02, type=float)
    janela_dias_max = request.args.get('janela_dias_max', 40, type=int)

    try:
        sugestoes = fatura_service.sugerir_matches(
            fatura_id,
            tolerancia_pct=tolerancia,
            janela_dias_max=janela_dias_max,
        )
        return jsonify({'sucesso': True, 'sugestoes': sugestoes})
    except ValueError as e:
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 400
    except Exception as e:
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 500


@fluxo_caixa_bp.route('/api/fluxo-caixa/faturas/<int:fatura_id>/vincular',
                      methods=['POST'])
@login_required
def api_vincular(fatura_id: int):
    """Vincula fatura a uma transacao de pagamento."""
    if not pode_acessar_pessoal(current_user):
        return jsonify({'sucesso': False, 'mensagem': 'Acesso restrito.'}), 403

    dados = request.get_json() or {}
    transacao_id = dados.get('transacao_pagamento_id')
    data_pagamento = dados.get('data_pagamento')
    if data_pagamento:
        try:
            data_pagamento = datetime.strptime(data_pagamento, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            return jsonify({
                'sucesso': False,
                'mensagem': 'data_pagamento invalida (esperado YYYY-MM-DD)',
            }), 400

    if not transacao_id:
        return jsonify({
            'sucesso': False,
            'mensagem': 'transacao_pagamento_id obrigatorio',
        }), 400

    try:
        res = fatura_service.vincular(
            fatura_id=fatura_id,
            transacao_pagamento_id=int(transacao_id),
            data_pagamento=data_pagamento,
        )
        return jsonify({'sucesso': True, **res})
    except ValueError as e:
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 400
    except Exception as e:
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 500


@fluxo_caixa_bp.route(
    '/api/fluxo-caixa/faturas/<int:fatura_id>/desvincular',
    methods=['POST'],
)
@login_required
def api_desvincular(fatura_id: int):
    """Remove vinculo fatura -> transacao de pagamento."""
    if not pode_acessar_pessoal(current_user):
        return jsonify({'sucesso': False, 'mensagem': 'Acesso restrito.'}), 403

    try:
        res = fatura_service.desvincular(fatura_id=fatura_id)
        return jsonify({'sucesso': True, **res})
    except ValueError as e:
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 400
    except Exception as e:
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 500


@fluxo_caixa_bp.route('/api/fluxo-caixa/faturas/backfill', methods=['POST'])
@login_required
def api_backfill():
    """Roda backfill automatico (match exato, 1 candidata). Suporta dry_run."""
    if not pode_acessar_pessoal(current_user):
        return jsonify({'sucesso': False, 'mensagem': 'Acesso restrito.'}), 403

    dados = request.get_json() or {}
    dry_run = bool(dados.get('dry_run', True))

    try:
        res = fatura_service.backfill_historico(dry_run=dry_run)
        return jsonify({'sucesso': True, **res})
    except Exception as e:
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 500
