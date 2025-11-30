"""
CRUD de Liberação Antecipação (LiberacaoAntecipacao)
Configuração de prazos de liberação para antecipação de recebíveis
"""

from flask import render_template, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime

from app import db
from app.financeiro.routes import financeiro_bp


# ========================================
# CRUD: LIBERAÇÃO ANTECIPAÇÃO
# ========================================

@financeiro_bp.route('/contas-receber/liberacao-antecipacao')
@login_required
def listar_liberacao_antecipacao():
    """
    Listagem de configurações de Liberação Antecipação
    """
    from app.financeiro.models import LiberacaoAntecipacao

    # Filtros
    criterio = request.args.get('criterio', '')
    ativo = request.args.get('ativo', '')

    query = LiberacaoAntecipacao.query

    if criterio:
        query = query.filter(LiberacaoAntecipacao.criterio_identificacao == criterio)
    if ativo:
        query = query.filter(LiberacaoAntecipacao.ativo == (ativo == 'true'))

    query = query.order_by(LiberacaoAntecipacao.criterio_identificacao, LiberacaoAntecipacao.identificador)
    configs = query.all()

    return render_template(
        'financeiro/crud_liberacao_antecipacao.html',
        configs=configs
    )


@financeiro_bp.route('/contas-receber/liberacao-antecipacao/api', methods=['GET'])
@login_required
def api_liberacao_list():
    """API para listar configurações"""
    try:
        from app.financeiro.models import LiberacaoAntecipacao

        criterio = request.args.get('criterio', '')
        ativo = request.args.get('ativo', '')

        query = LiberacaoAntecipacao.query

        if criterio:
            query = query.filter(LiberacaoAntecipacao.criterio_identificacao == criterio)
        if ativo:
            query = query.filter(LiberacaoAntecipacao.ativo == (ativo == 'true'))

        configs = query.order_by(LiberacaoAntecipacao.criterio_identificacao, LiberacaoAntecipacao.identificador).all()

        return jsonify({
            'success': True,
            'configs': [c.to_dict() for c in configs]
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@financeiro_bp.route('/contas-receber/liberacao-antecipacao/api/<int:config_id>', methods=['GET'])
@login_required
def api_liberacao_detalhe(config_id):
    """API para obter detalhes de uma configuração"""
    try:
        from app.financeiro.models import LiberacaoAntecipacao

        config = LiberacaoAntecipacao.query.get_or_404(config_id)
        return jsonify({'success': True, 'config': config.to_dict()})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@financeiro_bp.route('/contas-receber/liberacao-antecipacao/api', methods=['POST'])
@login_required
def api_criar_liberacao():
    """API para criar nova configuração"""
    try:
        from app.financeiro.models import LiberacaoAntecipacao

        data = request.get_json()

        # Validações
        if not data.get('criterio_identificacao'):
            return jsonify({'success': False, 'error': 'Critério de identificação é obrigatório'}), 400
        if not data.get('identificador'):
            return jsonify({'success': False, 'error': 'Identificador é obrigatório'}), 400
        if not data.get('dias_uteis_previsto'):
            return jsonify({'success': False, 'error': 'Dias úteis é obrigatório'}), 400

        config = LiberacaoAntecipacao(
            criterio_identificacao=data['criterio_identificacao'],
            identificador=data['identificador'],
            uf=data.get('uf', 'TODOS'),
            dias_uteis_previsto=int(data['dias_uteis_previsto']),
            ativo=data.get('ativo', True),
            criado_por=current_user.nome
        )

        db.session.add(config)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Configuração criada com sucesso!',
            'config': config.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@financeiro_bp.route('/contas-receber/liberacao-antecipacao/api/<int:config_id>', methods=['PUT'])
@login_required
def api_atualizar_liberacao(config_id):
    """API para atualizar configuração"""
    try:
        from app.financeiro.models import LiberacaoAntecipacao

        config = LiberacaoAntecipacao.query.get_or_404(config_id)
        data = request.get_json()

        config.criterio_identificacao = data.get('criterio_identificacao', config.criterio_identificacao)
        config.identificador = data.get('identificador', config.identificador)
        config.uf = data.get('uf', config.uf)
        config.dias_uteis_previsto = int(data.get('dias_uteis_previsto', config.dias_uteis_previsto))
        config.ativo = data.get('ativo', config.ativo)
        config.atualizado_por = current_user.nome
        config.atualizado_em = datetime.utcnow()

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Configuração atualizada com sucesso!',
            'config': config.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@financeiro_bp.route('/contas-receber/liberacao-antecipacao/api/<int:config_id>', methods=['DELETE'])
@login_required
def api_excluir_liberacao(config_id):
    """API para excluir configuração (soft delete)"""
    try:
        from app.financeiro.models import LiberacaoAntecipacao

        config = LiberacaoAntecipacao.query.get_or_404(config_id)

        # Soft delete
        config.ativo = False
        config.atualizado_por = current_user.nome
        config.atualizado_em = datetime.utcnow()

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Configuração desativada com sucesso!'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
