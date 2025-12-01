"""
Sistema de Permissões Simples e Funcional
==========================================

Implementação minimalista mas efetiva para controle de acesso.
"""

from functools import wraps
from flask import abort, jsonify, request
from flask_login import current_user
from sqlalchemy import or_
from app import db

# =============================================================================
# CONFIGURAÇÃO DE PERMISSÕES POR PERFIL
# =============================================================================

PERMISSIONS = {
    'administrador': {
        'all': True  # Acesso total
    },
    
    'gerente_comercial': {
        'all': True  # Acesso total também
    },
    
    'logistica': {
        # Tudo exceto auth/permissions
        'modules': [
            'cadastros_agendamento', 'carteira', 'agente', 'cotacao',
            'embarques', 'estoque', 'faturamento', 'financeiro', 'fretes',
            'localidades', 'main', 'manufatura', 'monitoramento', 'odoo',
            'pedidos', 'portaria', 'producao', 'separacao', 'tabelas',
            'transportadoras', 'veiculos', 'vinculos'
        ],
        'can_edit': True
    },
    
    'financeiro': {
        # Tudo exceto auth/permissions
        'modules': [
            'cadastros_agendamento', 'carteira', 'agente', 'cotacao',
            'embarques', 'estoque', 'faturamento', 'financeiro', 'fretes',
            'localidades', 'main', 'manufatura', 'monitoramento', 'odoo',
            'pedidos', 'portaria', 'producao', 'separacao', 'tabelas',
            'transportadoras', 'veiculos', 'vinculos'
        ],
        'can_edit': True
    },
    
    'portaria': {
        'modules': ['portaria', 'embarques', 'veiculos', 'transportadoras'],
        'can_edit': ['portaria']  # Edita só portaria
    },
    
    'vendedor': {
        'modules': [
            'carteira',  # Ver seus clientes
            'pedidos',   # Ver seus pedidos
            'faturamento',  # Ver faturamento seus clientes
            'monitoramento'  # EntregaMonitorada - ver e comentar
        ],
        'can_edit': ['monitoramento.comentar'],  # Pode adicionar comentários
        'own_data_only': True  # Só vê dados próprios
    }
}


# =============================================================================
# DECORADORES E FUNÇÕES DE PERMISSÃO
# =============================================================================

def check_permission(module_name, action='view'):
    """
    Decorador simples para verificar permissões.
    
    Uso:
        @check_permission('carteira')  # Verifica permissão de visualização
        @check_permission('carteira', 'edit')  # Verifica permissão de edição
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Não autenticado
            if not current_user.is_authenticated:
                if request.is_json:
                    return jsonify({'error': 'Não autenticado'}), 401
                abort(401)
            
            # Obter perfil do usuário
            user_profile = getattr(current_user, 'perfil', None)
            if not user_profile:
                abort(403)
            
            # Buscar permissões do perfil
            profile_perms = PERMISSIONS.get(user_profile, {})
            
            # Admin e gerente_comercial têm acesso total
            if profile_perms.get('all', False):
                return f(*args, **kwargs)
            
            # Verificar se tem acesso ao módulo
            allowed_modules = profile_perms.get('modules', [])
            if module_name not in allowed_modules:
                if request.is_json:
                    return jsonify({'error': 'Acesso negado'}), 403
                abort(403)
            
            # Verificar permissão de edição se necessário
            if action == 'edit':
                can_edit = profile_perms.get('can_edit', [])
                if can_edit is True:
                    # Pode editar todos os módulos permitidos
                    pass
                elif isinstance(can_edit, list):
                    # Pode editar apenas módulos específicos
                    full_permission = f"{module_name}.{action}" if '.' not in action else action
                    if module_name not in can_edit and full_permission not in can_edit:
                        if request.is_json:
                            return jsonify({'error': 'Sem permissão para editar'}), 403
                        abort(403)
                else:
                    # Não pode editar
                    if request.is_json:
                        return jsonify({'error': 'Sem permissão para editar'}), 403
                    abort(403)
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def filter_by_user_data(query, model):
    """
    Aplica filtros de dados baseado no usuário logado.
    Usado principalmente para vendedores verem apenas seus próprios dados.
    
    Uso:
        pedidos = filter_by_user_data(CarteiraCliente.query, CarteiraCliente).all()
    """
    if not current_user.is_authenticated:
        return query.filter(False)  # Retorna query vazia
    
    user_profile = getattr(current_user, 'perfil', None)
    profile_perms = PERMISSIONS.get(user_profile, {})
    
    # Admin e gerente veem tudo
    if profile_perms.get('all', False):
        return query
    
    # Se perfil tem restrição own_data_only
    if profile_perms.get('own_data_only', False):
        # Importar aqui para evitar import circular
        from app.permissions.models import UserVendedor, UserEquipe, EquipeVendas
        
        # Buscar vendedores do usuário (considerando IDs e nomes)
        user_vendors = UserVendedor.query.filter_by(
            user_id=current_user.id,
            ativo=True
        ).all()
        
        # Coletar IDs e nomes de vendedores
        vendedor_ids = []
        vendedor_nomes = []
        
        for uv in user_vendors:
            if uv.vendedor_id:
                vendedor_ids.append(uv.vendedor_id)
            if uv.observacoes:  # Nome salvo no campo observacoes
                vendedor_nomes.append(uv.observacoes)
        
        # Se tem IDs de vendedor, também buscar os nomes
        if vendedor_ids:
            from app.permissions.models import Vendedor
            vendedores = Vendedor.query.filter(Vendedor.id.in_(vendedor_ids)).all()
            for v in vendedores:
                vendedor_nomes.append(v.nome)
        
        # Aplicar filtro se o modelo tem vendedor_id ou vendedor
        if hasattr(model, 'vendedor_id') and vendedor_ids:
            query = query.filter(model.vendedor_id.in_(vendedor_ids))
        elif hasattr(model, 'vendedor') and vendedor_nomes:
            query = query.filter(model.vendedor.in_(vendedor_nomes))
        
        # Para EntregaMonitorada, filtrar por vendedor da NF
        if model.__name__ == 'EntregaMonitorada' and hasattr(model, 'vendedor'):
            # Buscar equipes do usuário também
            user_teams = UserEquipe.query.filter_by(
                user_id=current_user.id,
                ativo=True
            ).all()
            
            # Coletar nomes de equipes
            equipe_nomes = []
            for ut in user_teams:
                if ut.equipe_id:
                    equipe = EquipeVendas.query.get(ut.equipe_id)
                    if equipe:
                        equipe_nomes.append(equipe.nome)
                if ut.observacoes:  # Nome salvo no campo observacoes
                    equipe_nomes.append(ut.observacoes)
            
            # Se tem vendedores ou equipes, aplicar filtro
            if vendedor_nomes or equipe_nomes:
                from app.faturamento.models import RelatorioFaturamentoImportado
                
                conditions = []
                if vendedor_nomes:
                    conditions.append(model.vendedor.in_(vendedor_nomes))
                
                # Para equipes, precisamos buscar vendedores dessas equipes
                if equipe_nomes:
                    # Buscar vendedores das equipes
                    vendedores_das_equipes = db.session.query(
                        RelatorioFaturamentoImportado.vendedor
                    ).filter(
                        RelatorioFaturamentoImportado.equipe_vendas.in_(equipe_nomes)
                    ).distinct().subquery()
                    
                    conditions.append(model.vendedor.in_(vendedores_das_equipes))
                
                if conditions:
                    query = query.filter(or_(*conditions))
    
    return query


def can_user_comment_entrega(entrega):
    """
    Verifica se o usuário pode comentar em uma entrega monitorada.
    Vendedor só pode comentar em entregas de seus clientes.
    """
    if not current_user.is_authenticated:
        return False
    
    user_profile = getattr(current_user, 'perfil', None)
    profile_perms = PERMISSIONS.get(user_profile, {})
    
    # Admin e gerente podem comentar em qualquer entrega
    if profile_perms.get('all', False):
        return True
    
    # Vendedor precisa ser vinculado ao vendedor da entrega
    if user_profile == 'vendedor':
        from app.permissions.models import UserVendedor
        
        # Verificar se o vendedor da entrega está vinculado ao usuário
        if hasattr(entrega, 'vendedor_id') and entrega.vendedor_id:
            vinculo = UserVendedor.query.filter_by(
                user_id=current_user.id,
                vendedor_id=entrega.vendedor_id,
                ativo=True
            ).first()
            
            return vinculo is not None
    
    # Outros perfis seguem permissão de edição do módulo
    return has_permission('monitoramento', 'edit')


def has_permission(module_name, action='view'):
    """
    Função helper para verificar permissão sem decorador.
    Útil para verificações condicionais no código.
    
    Uso:
        if has_permission('carteira', 'edit'):
            # mostrar botão de editar
    """
    if not current_user.is_authenticated:
        return False
    
    user_profile = getattr(current_user, 'perfil', None)
    if not user_profile:
        return False
    
    profile_perms = PERMISSIONS.get(user_profile, {})
    
    # Admin e gerente têm tudo
    if profile_perms.get('all', False):
        return True
    
    # Verificar módulo
    allowed_modules = profile_perms.get('modules', [])
    if module_name not in allowed_modules:
        return False
    
    # Se só quer view, já está ok
    if action == 'view':
        return True
    
    # Verificar ação específica
    can_edit = profile_perms.get('can_edit', [])
    if can_edit is True:
        return True
    elif isinstance(can_edit, list):
        full_permission = f"{module_name}.{action}"
        return module_name in can_edit or full_permission in can_edit
    
    return False


def get_user_permissions():
    """
    Retorna dicionário com todas as permissões do usuário atual.
    Útil para passar para templates ou APIs.
    """
    if not current_user.is_authenticated:
        return {}
    
    user_profile = getattr(current_user, 'perfil', None)
    if not user_profile:
        return {}
    
    return PERMISSIONS.get(user_profile, {})