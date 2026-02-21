"""
Rotas CRUD para Cadastros de Ocorrencias
=========================================

CRUD generico para as 5 tabelas lookup da area Comercial:
- Categorias, Subcategorias, Responsaveis, Origens, Autorizados Por

Criado em: 21/02/2026
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.devolucao.models import (
    OcorrenciaCategoria, OcorrenciaSubcategoria,
    OcorrenciaResponsavel, OcorrenciaOrigem,
    OcorrenciaAutorizadoPor
)
from app.utils.timezone import agora_utc_naive

# Blueprint
cadastro_bp = Blueprint('devolucao_cadastro', __name__, url_prefix='/cadastros')

# Mapa tipo -> model
TIPO_MODEL_MAP = {
    'categorias': OcorrenciaCategoria,
    'subcategorias': OcorrenciaSubcategoria,
    'responsaveis': OcorrenciaResponsavel,
    'origens': OcorrenciaOrigem,
    'autorizados': OcorrenciaAutorizadoPor,
}


def _get_model(tipo):
    """Retorna model para o tipo ou None"""
    return TIPO_MODEL_MAP.get(tipo)


def _get_usuario():
    """Retorna nome do usuario atual"""
    return current_user.nome if hasattr(current_user, 'nome') else current_user.username


# =============================================================================
# Listar ativos (para selects da pagina)
# =============================================================================

@cadastro_bp.route('/api/<tipo>', methods=['GET'])
@login_required
def listar_ativos(tipo):
    """Lista itens ativos, ordenados por descricao"""
    Model = _get_model(tipo)
    if not Model:
        return jsonify({'sucesso': False, 'erro': f'Tipo invalido: {tipo}'}), 400

    itens = Model.query.filter_by(ativo=True).order_by(Model.descricao).all()

    return jsonify({
        'sucesso': True,
        'itens': [item.to_dict() for item in itens]
    })


# =============================================================================
# Listar todos (para CRUD modal, inclui inativos)
# =============================================================================

@cadastro_bp.route('/api/<tipo>/todos', methods=['GET'])
@login_required
def listar_todos(tipo):
    """Lista todos os itens (ativos e inativos) para CRUD"""
    Model = _get_model(tipo)
    if not Model:
        return jsonify({'sucesso': False, 'erro': f'Tipo invalido: {tipo}'}), 400

    itens = Model.query.order_by(Model.descricao).all()

    return jsonify({
        'sucesso': True,
        'itens': [item.to_dict() for item in itens]
    })


# =============================================================================
# Criar novo item
# =============================================================================

@cadastro_bp.route('/api/<tipo>', methods=['POST'])
@login_required
def criar(tipo):
    """Cria novo item de cadastro"""
    Model = _get_model(tipo)
    if not Model:
        return jsonify({'sucesso': False, 'erro': f'Tipo invalido: {tipo}'}), 400

    data = request.get_json()

    descricao = (data.get('descricao') or '').strip()
    if not descricao:
        return jsonify({'sucesso': False, 'erro': 'Descricao e obrigatoria'}), 400

    # Gerar codigo a partir da descricao (uppercase, underscores)
    codigo = (data.get('codigo') or '').strip()
    if not codigo:
        codigo = descricao.upper().replace(' ', '_')
        # Remover caracteres especiais
        import re
        codigo = re.sub(r'[^A-Z0-9_]', '', codigo)

    # Verificar duplicidade
    existente = Model.query.filter_by(codigo=codigo).first()
    if existente:
        return jsonify({'sucesso': False, 'erro': f'Codigo "{codigo}" ja existe'}), 409

    item = Model(
        codigo=codigo,
        descricao=descricao,
        criado_por=_get_usuario(),
        criado_em=agora_utc_naive(),
    )

    db.session.add(item)
    db.session.commit()

    return jsonify({
        'sucesso': True,
        'mensagem': f'{descricao} adicionado com sucesso!',
        'item': item.to_dict()
    }), 201


# =============================================================================
# Editar item existente
# =============================================================================

@cadastro_bp.route('/api/<tipo>/<int:item_id>', methods=['PUT'])
@login_required
def editar(tipo, item_id):
    """Edita descricao de um item"""
    Model = _get_model(tipo)
    if not Model:
        return jsonify({'sucesso': False, 'erro': f'Tipo invalido: {tipo}'}), 400

    item = db.session.get(Model, item_id)
    if not item:
        return jsonify({'sucesso': False, 'erro': 'Item nao encontrado'}), 404

    data = request.get_json()

    if 'descricao' in data:
        descricao = (data['descricao'] or '').strip()
        if descricao:
            item.descricao = descricao

    item.atualizado_por = _get_usuario()
    item.atualizado_em = agora_utc_naive()

    db.session.commit()

    return jsonify({
        'sucesso': True,
        'mensagem': 'Item atualizado!',
        'item': item.to_dict()
    })


# =============================================================================
# Toggle ativo/inativo
# =============================================================================

@cadastro_bp.route('/api/<tipo>/<int:item_id>/toggle', methods=['PATCH'])
@login_required
def toggle_ativo(tipo, item_id):
    """Ativa ou desativa um item"""
    Model = _get_model(tipo)
    if not Model:
        return jsonify({'sucesso': False, 'erro': f'Tipo invalido: {tipo}'}), 400

    item = db.session.get(Model, item_id)
    if not item:
        return jsonify({'sucesso': False, 'erro': 'Item nao encontrado'}), 404

    item.ativo = not item.ativo
    item.atualizado_por = _get_usuario()
    item.atualizado_em = agora_utc_naive()

    db.session.commit()

    status = 'ativado' if item.ativo else 'desativado'
    return jsonify({
        'sucesso': True,
        'mensagem': f'{item.descricao} {status}!',
        'item': item.to_dict()
    })
