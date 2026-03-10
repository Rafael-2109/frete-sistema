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
    OcorrenciaAutorizadoPor, PermissaoCadastroDevolucao
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


def _verificar_permissao_cadastro(tipo_cadastro, acao):
    """
    Verifica se o usuario pode executar a acao no tipo de cadastro.
    Administradores e gerentes comerciais tem acesso total automaticamente.
    """
    if current_user.perfil in ('administrador', 'gerente_comercial'):
        return True
    perm = PermissaoCadastroDevolucao.query.filter_by(
        usuario_id=current_user.id,
        tipo_cadastro=tipo_cadastro,
        ativo=True
    ).first()
    if not perm:
        return False
    if acao == 'criar':
        return perm.pode_criar
    if acao == 'editar':
        return perm.pode_editar
    if acao == 'excluir':
        return perm.pode_excluir
    return False


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

    query = Model.query.filter_by(ativo=True)

    # Filtro por categoria_ids (subcategorias e responsaveis)
    categoria_ids_param = request.args.get('categoria_ids', '')
    if categoria_ids_param and tipo in ('subcategorias', 'responsaveis'):
        try:
            cat_ids = [int(x) for x in categoria_ids_param.split(',') if x.strip()]
        except ValueError:
            cat_ids = []
        if cat_ids:
            query = query.filter(Model.categoria_id.in_(cat_ids))

    itens = query.order_by(Model.descricao).all()

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

    if not _verificar_permissao_cadastro(tipo, 'criar'):
        return jsonify({'sucesso': False, 'erro': 'Sem permissao para criar neste cadastro'}), 403

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

    kwargs = dict(
        codigo=codigo,
        descricao=descricao,
        criado_por=_get_usuario(),
        criado_em=agora_utc_naive(),
    )

    # categoria_id obrigatorio para subcategorias e responsaveis
    if tipo in ('subcategorias', 'responsaveis'):
        cat_id = data.get('categoria_id')
        if not cat_id:
            return jsonify({'sucesso': False, 'erro': 'Categoria e obrigatoria'}), 400
        try:
            kwargs['categoria_id'] = int(cat_id)
        except (ValueError, TypeError):
            return jsonify({'sucesso': False, 'erro': 'Categoria invalida'}), 400

    item = Model(**kwargs)

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

    if not _verificar_permissao_cadastro(tipo, 'editar'):
        return jsonify({'sucesso': False, 'erro': 'Sem permissao para editar neste cadastro'}), 403

    item = db.session.get(Model, item_id)
    if not item:
        return jsonify({'sucesso': False, 'erro': 'Item nao encontrado'}), 404

    data = request.get_json()

    if 'descricao' in data:
        descricao = (data['descricao'] or '').strip()
        if descricao:
            item.descricao = descricao

    # Atualizar categoria_id se fornecido (subcategorias e responsaveis)
    if tipo in ('subcategorias', 'responsaveis') and 'categoria_id' in data:
        cat_id = data['categoria_id']
        if cat_id:
            try:
                item.categoria_id = int(cat_id)
            except (ValueError, TypeError):
                return jsonify({'sucesso': False, 'erro': 'Categoria invalida'}), 400
        else:
            return jsonify({'sucesso': False, 'erro': 'Categoria e obrigatoria'}), 400

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

    if not _verificar_permissao_cadastro(tipo, 'excluir'):
        return jsonify({'sucesso': False, 'erro': 'Sem permissao para ativar/desativar neste cadastro'}), 403

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


# =============================================================================
# Gerenciamento de Permissoes de Cadastro
# =============================================================================

@cadastro_bp.route('/api/permissoes', methods=['GET'])
@login_required
def listar_permissoes():
    """Lista permissoes de cadastro (admin/gerente_comercial only)"""
    if current_user.perfil not in ('administrador', 'gerente_comercial'):
        return jsonify({'sucesso': False, 'erro': 'Acesso restrito'}), 403

    permissoes = PermissaoCadastroDevolucao.query.filter_by(
        ativo=True
    ).order_by(PermissaoCadastroDevolucao.tipo_cadastro).all()

    # Listar usuarios disponiveis (excluindo admin/gerente)
    from app.auth.models import Usuario
    usuarios = Usuario.query.filter(
        Usuario.ativo == True,
        ~Usuario.perfil.in_(['administrador', 'gerente_comercial'])
    ).order_by(Usuario.nome).all()

    return jsonify({
        'sucesso': True,
        'permissoes': [p.to_dict() for p in permissoes],
        'usuarios': [{'id': u.id, 'nome': u.nome, 'perfil': u.perfil} for u in usuarios]
    })


@cadastro_bp.route('/api/permissoes', methods=['POST'])
@login_required
def conceder_permissao():
    """Concede permissao de cadastro"""
    if current_user.perfil not in ('administrador', 'gerente_comercial'):
        return jsonify({'sucesso': False, 'erro': 'Acesso restrito'}), 403

    data = request.get_json()
    usuario_id = data.get('usuario_id')
    tipo_cadastro = data.get('tipo_cadastro')

    if not usuario_id or not tipo_cadastro:
        return jsonify({'sucesso': False, 'erro': 'usuario_id e tipo_cadastro obrigatorios'}), 400

    tipos_validos = ['categorias', 'subcategorias', 'responsaveis', 'origens']
    if tipo_cadastro not in tipos_validos:
        return jsonify({'sucesso': False, 'erro': f'Tipo invalido: {tipo_cadastro}'}), 400

    # Verificar se ja existe
    existente = PermissaoCadastroDevolucao.query.filter_by(
        usuario_id=usuario_id,
        tipo_cadastro=tipo_cadastro
    ).first()

    if existente:
        # Reativar e atualizar
        existente.ativo = True
        existente.pode_criar = data.get('pode_criar', False)
        existente.pode_editar = data.get('pode_editar', False)
        existente.pode_excluir = data.get('pode_excluir', False)
        existente.concedido_por = _get_usuario()
        existente.concedido_em = agora_utc_naive()
        db.session.commit()
        return jsonify({'sucesso': True, 'mensagem': 'Permissao atualizada!', 'permissao': existente.to_dict()})

    perm = PermissaoCadastroDevolucao(
        usuario_id=int(usuario_id),
        tipo_cadastro=tipo_cadastro,
        pode_criar=data.get('pode_criar', False),
        pode_editar=data.get('pode_editar', False),
        pode_excluir=data.get('pode_excluir', False),
        concedido_por=_get_usuario(),
        concedido_em=agora_utc_naive()
    )

    db.session.add(perm)
    db.session.commit()

    return jsonify({
        'sucesso': True,
        'mensagem': 'Permissao concedida!',
        'permissao': perm.to_dict()
    }), 201


@cadastro_bp.route('/api/permissoes/<int:perm_id>', methods=['PUT'])
@login_required
def atualizar_permissao(perm_id):
    """Atualiza permissao de cadastro"""
    if current_user.perfil not in ('administrador', 'gerente_comercial'):
        return jsonify({'sucesso': False, 'erro': 'Acesso restrito'}), 403

    perm = db.session.get(PermissaoCadastroDevolucao, perm_id)
    if not perm:
        return jsonify({'sucesso': False, 'erro': 'Permissao nao encontrada'}), 404

    data = request.get_json()
    if 'pode_criar' in data:
        perm.pode_criar = data['pode_criar']
    if 'pode_editar' in data:
        perm.pode_editar = data['pode_editar']
    if 'pode_excluir' in data:
        perm.pode_excluir = data['pode_excluir']

    perm.concedido_por = _get_usuario()
    perm.concedido_em = agora_utc_naive()
    db.session.commit()

    return jsonify({'sucesso': True, 'mensagem': 'Permissao atualizada!', 'permissao': perm.to_dict()})


@cadastro_bp.route('/api/permissoes/<int:perm_id>', methods=['DELETE'])
@login_required
def revogar_permissao(perm_id):
    """Revoga permissao (soft delete)"""
    if current_user.perfil not in ('administrador', 'gerente_comercial'):
        return jsonify({'sucesso': False, 'erro': 'Acesso restrito'}), 403

    perm = db.session.get(PermissaoCadastroDevolucao, perm_id)
    if not perm:
        return jsonify({'sucesso': False, 'erro': 'Permissao nao encontrada'}), 404

    perm.ativo = False
    db.session.commit()

    return jsonify({'sucesso': True, 'mensagem': 'Permissao revogada!'})
