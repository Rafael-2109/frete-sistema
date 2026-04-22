"""Rotas da tela de matches empresa pendentes (2+ pontas — vinculacao manual)."""
from datetime import datetime

from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user, login_required

from app.pessoal import pode_acessar_pessoal
from app.pessoal.services import matches_empresa_service
from app.pessoal.services.compensacao_service import (
    aplicar_compensacao, reverter_compensacao, listar_compensacoes,
)

matches_empresa_bp = Blueprint('pessoal_matches_empresa', __name__)


def _user_label():
    if hasattr(current_user, 'nome') and current_user.nome:
        return current_user.nome
    return str(getattr(current_user, 'id', '?'))


@matches_empresa_bp.route('/matches-empresa')
@login_required
def index():
    if not pode_acessar_pessoal(current_user):
        return 'Acesso restrito.', 403
    return render_template('pessoal/matches_empresa.html')


@matches_empresa_bp.route('/api/matches-empresa/pendentes', methods=['GET'])
@login_required
def api_pendentes():
    """Lista dias com 2+ pontas empresa pendentes de match manual."""
    if not pode_acessar_pessoal(current_user):
        return jsonify({'sucesso': False, 'mensagem': 'Acesso restrito.'}), 403

    def _pd(raw):
        if not raw:
            return None
        try:
            return datetime.strptime(raw, '%Y-%m-%d').date()
        except ValueError:
            return None

    data_inicio = _pd(request.args.get('data_inicio'))
    data_fim = _pd(request.args.get('data_fim'))
    apenas_ambiguos = request.args.get('apenas_ambiguos', '1') == '1'

    try:
        dias = matches_empresa_service.listar_dias_pendentes(
            data_inicio=data_inicio,
            data_fim=data_fim,
            apenas_ambiguos=apenas_ambiguos,
        )
        return jsonify({'sucesso': True, 'dias': dias, 'total': len(dias)})
    except Exception as e:
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 500


@matches_empresa_bp.route('/api/matches-empresa/vincular', methods=['POST'])
@login_required
def api_vincular():
    """Aplica vinculacao manual (saida_id <-> entrada_id) com valor informado.

    Payload:
      - saida_id (int)
      - entrada_id (int)
      - valor (float): valor a compensar (min entre os residuos)
      - observacao (str, opcional)
    """
    if not pode_acessar_pessoal(current_user):
        return jsonify({'sucesso': False, 'mensagem': 'Acesso restrito.'}), 403

    dados = request.get_json() or {}
    try:
        saida_id = int(dados['saida_id'])
        entrada_id = int(dados['entrada_id'])
        valor = float(dados['valor'])
    except (KeyError, ValueError, TypeError):
        return jsonify({
            'sucesso': False,
            'mensagem': 'saida_id, entrada_id e valor obrigatorios (numericos)',
        }), 400

    if valor <= 0:
        return jsonify({'sucesso': False, 'mensagem': 'valor deve ser > 0'}), 400

    try:
        comp = aplicar_compensacao(
            saida_id=saida_id,
            entrada_id=entrada_id,
            valor=valor,
            origem='manual',
            criado_por=_user_label(),
            observacao=dados.get('observacao') or 'Match manual empresa',
        )
        return jsonify({'sucesso': True, 'compensacao': comp.to_dict()})
    except ValueError as e:
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 400
    except Exception as e:
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 500


@matches_empresa_bp.route(
    '/api/matches-empresa/reverter/<int:comp_id>',
    methods=['POST'],
)
@login_required
def api_reverter(comp_id: int):
    """Reverte uma compensacao (volta as pontas ao residuo anterior)."""
    if not pode_acessar_pessoal(current_user):
        return jsonify({'sucesso': False, 'mensagem': 'Acesso restrito.'}), 403

    try:
        comp = reverter_compensacao(comp_id, revertido_por=_user_label())
        return jsonify({'sucesso': True, 'compensacao': comp.to_dict()})
    except ValueError as e:
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 400
    except Exception as e:
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 500


@matches_empresa_bp.route('/api/matches-empresa/historico', methods=['GET'])
@login_required
def api_historico():
    """Lista compensacoes ativas + revertidas (historico de matches)."""
    if not pode_acessar_pessoal(current_user):
        return jsonify({'sucesso': False, 'mensagem': 'Acesso restrito.'}), 403

    status = request.args.get('status')  # ATIVA | REVERTIDA | None
    limit = request.args.get('limit', 200, type=int)

    try:
        comps = listar_compensacoes(status=status, limit=limit)
        return jsonify({'sucesso': True, 'compensacoes': comps, 'total': len(comps)})
    except Exception as e:
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 500
