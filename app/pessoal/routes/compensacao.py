"""Rotas da funcionalidade de Compensacao Saida <-> Entrada Empresa."""
from datetime import datetime

from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user, login_required

from app import db
from app.pessoal import pode_acessar_pessoal
from app.pessoal.models import PessoalCategoria
from app.pessoal.services.compensacao_service import (
    aplicar_compensacao, compensar_automatico, listar_compensacoes,
    recalcular_valor_compensado, reverter_compensacao, sugerir_pareamento,
)

compensacao_bp = Blueprint('pessoal_compensacao', __name__)


def _parse_date(s):
    if not s:
        return None
    try:
        return datetime.strptime(s, '%Y-%m-%d').date()
    except ValueError:
        return None


def _user_label():
    if hasattr(current_user, 'nome') and current_user.nome:
        return current_user.nome
    return str(getattr(current_user, 'id', '?'))


# =============================================================================
# UI
# =============================================================================
@compensacao_bp.route('/compensacoes')
@login_required
def index():
    """Pagina de compensacoes: sugestoes + ativas + revertidas."""
    if not pode_acessar_pessoal(current_user):
        return 'Acesso restrito.', 403

    # Categorias compensaveis para referencia visual
    cats_saida = PessoalCategoria.query.filter_by(
        compensavel_tipo='S', ativa=True,
    ).order_by(PessoalCategoria.grupo, PessoalCategoria.nome).all()
    cats_entrada = PessoalCategoria.query.filter_by(
        compensavel_tipo='E', ativa=True,
    ).order_by(PessoalCategoria.grupo, PessoalCategoria.nome).all()

    return render_template(
        'pessoal/compensacoes.html',
        cats_saida=cats_saida,
        cats_entrada=cats_entrada,
    )


# =============================================================================
# API: sugerir pareamento (dry-run)
# =============================================================================
@compensacao_bp.route('/api/compensacoes/sugerir', methods=['GET'])
@login_required
def api_sugerir():
    if not pode_acessar_pessoal(current_user):
        return jsonify({'sucesso': False, 'mensagem': 'Acesso restrito.'}), 403

    janela_dias = request.args.get('janela_dias', 7, type=int)
    data_inicio = _parse_date(request.args.get('data_inicio'))
    data_fim = _parse_date(request.args.get('data_fim'))

    try:
        sugestoes = sugerir_pareamento(
            janela_dias=janela_dias,
            data_inicio=data_inicio, data_fim=data_fim,
        )
        return jsonify({
            'sucesso': True,
            'janela_dias': janela_dias,
            'total': len(sugestoes),
            'sugestoes': [s.to_dict() for s in sugestoes],
        })
    except Exception as e:
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 500


# =============================================================================
# API: aplicar compensacao (uma ou varias)
# =============================================================================
@compensacao_bp.route('/api/compensacoes/aplicar', methods=['POST'])
@login_required
def api_aplicar():
    if not pode_acessar_pessoal(current_user):
        return jsonify({'sucesso': False, 'mensagem': 'Acesso restrito.'}), 403

    dados = request.get_json() or {}
    pares = dados.get('pares')
    if pares is None:
        # Single: {saida_id, entrada_id, valor, observacao?}
        pares = [{
            'saida_id': dados.get('saida_id'),
            'entrada_id': dados.get('entrada_id'),
            'valor': dados.get('valor'),
            'observacao': dados.get('observacao'),
        }]

    if not pares:
        return jsonify({'sucesso': False, 'mensagem': 'Nenhum par informado.'}), 400

    aplicadas = []
    erros = []
    user = _user_label()
    for par in pares:
        try:
            saida_id = int(par['saida_id'])
            entrada_id = int(par['entrada_id'])
            valor = float(par['valor'])
            obs = par.get('observacao')
            comp = aplicar_compensacao(
                saida_id=saida_id, entrada_id=entrada_id, valor=valor,
                origem=par.get('origem', 'manual'), criado_por=user,
                observacao=obs, commit=False,
            )
            aplicadas.append(comp.to_dict())
        except Exception as e:
            erros.append({'par': par, 'erro': str(e)})

    if aplicadas and not erros:
        db.session.commit()
    elif aplicadas and erros:
        # Tem erro no lote: rollback tudo para manter consistencia
        db.session.rollback()
        return jsonify({
            'sucesso': False,
            'mensagem': 'Erro em algum par — nenhum foi aplicado.',
            'erros': erros,
        }), 400
    elif erros:
        db.session.rollback()
        return jsonify({'sucesso': False, 'mensagem': 'Erro ao aplicar.', 'erros': erros}), 400

    return jsonify({
        'sucesso': True,
        'mensagem': f'{len(aplicadas)} compensacao(es) aplicada(s).',
        'aplicadas': aplicadas,
    })


# =============================================================================
# API: compensar automatico em lote
# =============================================================================
@compensacao_bp.route('/api/compensacoes/auto', methods=['POST'])
@login_required
def api_auto():
    if not pode_acessar_pessoal(current_user):
        return jsonify({'sucesso': False, 'mensagem': 'Acesso restrito.'}), 403

    dados = request.get_json() or {}
    janela_dias = int(dados.get('janela_dias', 7))
    dry_run = bool(dados.get('dry_run', True))
    data_inicio = _parse_date(dados.get('data_inicio'))
    data_fim = _parse_date(dados.get('data_fim'))

    try:
        resultado = compensar_automatico(
            janela_dias=janela_dias, data_inicio=data_inicio,
            data_fim=data_fim, dry_run=dry_run, criado_por=_user_label(),
        )
        return jsonify({'sucesso': True, **resultado})
    except Exception as e:
        db.session.rollback()
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 500


# =============================================================================
# API: reverter
# =============================================================================
@compensacao_bp.route('/api/compensacoes/<int:comp_id>/reverter', methods=['POST'])
@login_required
def api_reverter(comp_id):
    if not pode_acessar_pessoal(current_user):
        return jsonify({'sucesso': False, 'mensagem': 'Acesso restrito.'}), 403

    try:
        comp = reverter_compensacao(comp_id, revertido_por=_user_label())
        return jsonify({
            'sucesso': True,
            'mensagem': f'Compensacao #{comp.id} revertida.',
            'compensacao': comp.to_dict(),
        })
    except ValueError as e:
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 500


# =============================================================================
# API: listar
# =============================================================================
@compensacao_bp.route('/api/compensacoes', methods=['GET'])
@login_required
def api_listar():
    if not pode_acessar_pessoal(current_user):
        return jsonify({'sucesso': False, 'mensagem': 'Acesso restrito.'}), 403

    status = request.args.get('status') or None
    data_inicio = _parse_date(request.args.get('data_inicio'))
    data_fim = _parse_date(request.args.get('data_fim'))
    limit = min(request.args.get('limit', 500, type=int), 2000)

    try:
        lista = listar_compensacoes(
            status=status, data_inicio=data_inicio, data_fim=data_fim, limit=limit,
        )
        return jsonify({'sucesso': True, 'total': len(lista), 'compensacoes': lista})
    except Exception as e:
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 500


# =============================================================================
# API: recalcular cache de uma transacao (util para admin)
# =============================================================================
@compensacao_bp.route('/api/compensacoes/recalcular/<int:transacao_id>', methods=['POST'])
@login_required
def api_recalcular(transacao_id):
    if not pode_acessar_pessoal(current_user):
        return jsonify({'sucesso': False, 'mensagem': 'Acesso restrito.'}), 403
    try:
        compensado = recalcular_valor_compensado(transacao_id)
        db.session.commit()
        return jsonify({'sucesso': True, 'valor_compensado': float(compensado)})
    except Exception as e:
        db.session.rollback()
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 500


# =============================================================================
# API: marcar categoria como compensavel
# =============================================================================
@compensacao_bp.route('/api/categorias/<int:cat_id>/compensavel', methods=['PATCH'])
@login_required
def api_marcar_compensavel(cat_id):
    """Seta compensavel_tipo ('S'|'E'|null) em uma categoria."""
    if not pode_acessar_pessoal(current_user):
        return jsonify({'sucesso': False, 'mensagem': 'Acesso restrito.'}), 403

    dados = request.get_json() or {}
    tipo = dados.get('compensavel_tipo')
    if tipo not in (None, '', 'S', 'E'):
        return jsonify({'sucesso': False, 'mensagem': "compensavel_tipo deve ser 'S', 'E' ou null."}), 400
    if tipo == '':
        tipo = None

    cat = db.session.get(PessoalCategoria, cat_id)
    if not cat:
        return jsonify({'sucesso': False, 'mensagem': 'Categoria nao encontrada.'}), 404

    cat.compensavel_tipo = tipo
    db.session.commit()
    return jsonify({'sucesso': True, 'categoria': cat.to_dict()})
