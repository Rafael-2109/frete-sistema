"""Rotas de gerenciamento de PessoalProvisao (forecast de entradas/saidas)."""
from datetime import datetime, date

from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user, login_required

from app.pessoal import pode_acessar_pessoal
from app.pessoal.models import (
    PessoalCategoria, PessoalConta, PessoalMembro,
)
from app.pessoal.services import provisao_service

provisao_bp = Blueprint('pessoal_provisao', __name__)


def _current_user_label():
    if hasattr(current_user, 'nome') and current_user.nome:
        return current_user.nome
    return str(getattr(current_user, 'id', '?'))


@provisao_bp.route('/provisoes')
@login_required
def index():
    """Tela de gerenciamento de provisoes (CRUD)."""
    if not pode_acessar_pessoal(current_user):
        return 'Acesso restrito.', 403

    hoje = date.today()
    ano = request.args.get('ano', hoje.year, type=int)
    mes = request.args.get('mes', hoje.month, type=int)

    categorias = PessoalCategoria.query.filter_by(ativa=True).order_by(
        PessoalCategoria.grupo, PessoalCategoria.nome,
    ).all()
    membros = PessoalMembro.query.filter_by(ativo=True).order_by(
        PessoalMembro.nome,
    ).all()
    contas = PessoalConta.query.filter_by(ativa=True).order_by(
        PessoalConta.nome,
    ).all()

    return render_template(
        'pessoal/provisoes.html',
        ano=ano,
        mes=mes,
        categorias=categorias,
        membros=membros,
        contas=contas,
    )


# =============================================================================
# APIs (CRUD)
# =============================================================================
@provisao_bp.route('/api/provisoes', methods=['GET'])
@login_required
def api_listar():
    """Lista provisoes com filtros."""
    if not pode_acessar_pessoal(current_user):
        return jsonify({'sucesso': False, 'mensagem': 'Acesso restrito.'}), 403

    def _parse_date(raw):
        if not raw:
            return None
        try:
            return datetime.strptime(raw, '%Y-%m-%d').date()
        except ValueError:
            return None

    data_inicio = _parse_date(request.args.get('data_inicio'))
    data_fim = _parse_date(request.args.get('data_fim'))
    tipo = request.args.get('tipo')
    status = request.args.get('status')
    categoria_id = request.args.get('categoria_id', type=int)
    membro_id = request.args.get('membro_id', type=int)
    conta_id = request.args.get('conta_id', type=int)
    incluir_canceladas = request.args.get('incluir_canceladas', '0') == '1'

    try:
        provisoes = provisao_service.listar_provisoes(
            data_inicio=data_inicio,
            data_fim=data_fim,
            tipo=tipo,
            status=status,
            categoria_id=categoria_id,
            membro_id=membro_id,
            conta_id=conta_id,
            incluir_canceladas=incluir_canceladas,
        )
        return jsonify({
            'sucesso': True,
            'provisoes': provisoes,
            'total': len(provisoes),
        })
    except Exception as e:
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 500


@provisao_bp.route('/api/provisoes', methods=['POST'])
@login_required
def api_criar():
    """Cria uma provisao (suporta recorrencia)."""
    if not pode_acessar_pessoal(current_user):
        return jsonify({'sucesso': False, 'mensagem': 'Acesso restrito.'}), 403

    dados = request.get_json() or {}

    try:
        data_prevista = datetime.strptime(
            dados['data_prevista'], '%Y-%m-%d',
        ).date()
    except (KeyError, ValueError, TypeError):
        return jsonify({
            'sucesso': False,
            'mensagem': 'data_prevista obrigatoria (YYYY-MM-DD)',
        }), 400

    recorrencia_ate = None
    if dados.get('recorrencia_ate'):
        try:
            recorrencia_ate = datetime.strptime(
                dados['recorrencia_ate'], '%Y-%m-%d',
            ).date()
        except ValueError:
            return jsonify({
                'sucesso': False,
                'mensagem': 'recorrencia_ate invalida (YYYY-MM-DD)',
            }), 400

    try:
        prov = provisao_service.criar_provisao(
            tipo=dados.get('tipo'),
            data_prevista=data_prevista,
            valor=float(dados.get('valor', 0)),
            descricao=dados.get('descricao', '').strip(),
            categoria_id=dados.get('categoria_id'),
            membro_id=dados.get('membro_id'),
            conta_id=dados.get('conta_id'),
            orcamento_id=dados.get('orcamento_id'),
            recorrente=bool(dados.get('recorrente', False)),
            recorrencia_tipo=dados.get('recorrencia_tipo'),
            recorrencia_ate=recorrencia_ate,
            observacao=dados.get('observacao'),
            criado_por=_current_user_label(),
        )
        return jsonify({'sucesso': True, 'provisao': prov.to_dict()})
    except ValueError as e:
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 400
    except Exception as e:
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 500


@provisao_bp.route('/api/provisoes/<int:provisao_id>', methods=['PATCH'])
@login_required
def api_atualizar(provisao_id: int):
    """Atualiza campos editaveis de uma provisao."""
    if not pode_acessar_pessoal(current_user):
        return jsonify({'sucesso': False, 'mensagem': 'Acesso restrito.'}), 403

    dados = request.get_json() or {}

    # Se data_prevista vier, converte
    if 'data_prevista' in dados and dados['data_prevista']:
        try:
            dados['data_prevista'] = datetime.strptime(
                dados['data_prevista'], '%Y-%m-%d',
            ).date()
        except ValueError:
            return jsonify({
                'sucesso': False,
                'mensagem': 'data_prevista invalida',
            }), 400

    try:
        prov = provisao_service.atualizar_provisao(provisao_id, **dados)
        return jsonify({'sucesso': True, 'provisao': prov.to_dict()})
    except ValueError as e:
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 400
    except Exception as e:
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 500


@provisao_bp.route('/api/provisoes/<int:provisao_id>/cancelar', methods=['POST'])
@login_required
def api_cancelar(provisao_id: int):
    """Cancela uma provisao (status=CANCELADA)."""
    if not pode_acessar_pessoal(current_user):
        return jsonify({'sucesso': False, 'mensagem': 'Acesso restrito.'}), 403

    try:
        prov = provisao_service.cancelar_provisao(provisao_id)
        return jsonify({'sucesso': True, 'provisao': prov.to_dict()})
    except ValueError as e:
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 400
    except Exception as e:
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 500


@provisao_bp.route('/api/provisoes/<int:provisao_id>/realizar', methods=['POST'])
@login_required
def api_realizar(provisao_id: int):
    """Marca provisao como REALIZADA, vinculando a transacao (opcional)."""
    if not pode_acessar_pessoal(current_user):
        return jsonify({'sucesso': False, 'mensagem': 'Acesso restrito.'}), 403

    dados = request.get_json() or {}
    transacao_id = dados.get('transacao_id')

    try:
        prov = provisao_service.realizar_provisao(
            provisao_id,
            transacao_id=transacao_id,
        )
        return jsonify({'sucesso': True, 'provisao': prov.to_dict()})
    except ValueError as e:
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 400
    except Exception as e:
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 500


@provisao_bp.route(
    '/api/provisoes/<int:provisao_id>/reverter-realizacao',
    methods=['POST'],
)
@login_required
def api_reverter_realizacao(provisao_id: int):
    """Volta status REALIZADA para PROVISIONADA."""
    if not pode_acessar_pessoal(current_user):
        return jsonify({'sucesso': False, 'mensagem': 'Acesso restrito.'}), 403

    try:
        prov = provisao_service.reverter_realizacao(provisao_id)
        return jsonify({'sucesso': True, 'provisao': prov.to_dict()})
    except ValueError as e:
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 400
    except Exception as e:
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 500


@provisao_bp.route('/api/provisoes/<int:provisao_id>', methods=['DELETE'])
@login_required
def api_excluir(provisao_id: int):
    """Delete fisico (use com cuidado)."""
    if not pode_acessar_pessoal(current_user):
        return jsonify({'sucesso': False, 'mensagem': 'Acesso restrito.'}), 403

    try:
        provisao_service.excluir_provisao(provisao_id)
        return jsonify({'sucesso': True})
    except ValueError as e:
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 400
    except Exception as e:
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 500


# =============================================================================
# Materializar orcamento -> provisoes
# =============================================================================
@provisao_bp.route('/api/provisoes/materializar-orcamento', methods=['POST'])
@login_required
def api_materializar_orcamento():
    """Cria provisoes de saida a partir de orcamentos datados.

    Payload:
      - ano (int)
      - mes (int)
      - dia_vencimento_default (int, opcional, default=10)
      - mapa_vencimento (dict, opcional): {"<categoria_id>": dia}
    """
    if not pode_acessar_pessoal(current_user):
        return jsonify({'sucesso': False, 'mensagem': 'Acesso restrito.'}), 403

    dados = request.get_json() or {}
    ano = dados.get('ano')
    mes = dados.get('mes')
    if not ano or not mes:
        return jsonify({
            'sucesso': False, 'mensagem': 'ano e mes obrigatorios',
        }), 400

    mapa_raw = dados.get('mapa_vencimento') or {}
    # Normaliza chaves para int
    try:
        mapa = {int(k): int(v) for k, v in mapa_raw.items()}
    except (ValueError, TypeError):
        return jsonify({
            'sucesso': False,
            'mensagem': 'mapa_vencimento invalido ({categoria_id: dia})',
        }), 400

    try:
        res = provisao_service.materializar_orcamento(
            ano=int(ano),
            mes=int(mes),
            dia_vencimento_default=int(dados.get('dia_vencimento_default', 10)),
            mapa_vencimento_por_categoria=mapa,
            criado_por=_current_user_label(),
        )
        return jsonify({'sucesso': True, **res})
    except Exception as e:
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 500


@provisao_bp.route(
    '/api/provisoes/desmaterializar-orcamento',
    methods=['POST'],
)
@login_required
def api_desmaterializar_orcamento():
    """Cancela provisoes vindas de orcamento em um mes."""
    if not pode_acessar_pessoal(current_user):
        return jsonify({'sucesso': False, 'mensagem': 'Acesso restrito.'}), 403

    dados = request.get_json() or {}
    ano = dados.get('ano')
    mes = dados.get('mes')
    if not ano or not mes:
        return jsonify({
            'sucesso': False, 'mensagem': 'ano e mes obrigatorios',
        }), 400

    try:
        n = provisao_service.desmaterializar_orcamento(int(ano), int(mes))
        return jsonify({'sucesso': True, 'canceladas': n})
    except Exception as e:
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 500
