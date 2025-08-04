"""
Utilitários para o Sistema Unificado de Permissões
==================================================

Funções auxiliares, contexto e auditoria.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from flask import request
from flask_login import current_user
from app import db
from app.permissions.models_unified import (
    UserPermission, PermissionCategory, PermissionModule, 
    PermissionSubModule, PermissionLog, UserVendedor, 
    UserEquipe, VendedorPermission, EquipePermission
)

logger = logging.getLogger(__name__)


def get_user_permission_context(user_id: int) -> Dict[str, Any]:
    """
    Retorna contexto completo de permissões do usuário.
    Útil para renderizar interfaces e fazer verificações em lote.
    """
    context = {
        'user_id': user_id,
        'categories': [],
        'vendors': [],
        'teams': [],
        'profile': None
    }
    
    try:
        # Buscar perfil do usuário
        from app.auth.models import Usuario
        user = Usuario.query.get(user_id)
        if user:
            context['profile'] = user.perfil
        
        # Buscar vendedores
        vendors = UserVendedor.query.filter_by(
            user_id=user_id,
            ativo=True
        ).all()
        context['vendors'] = [
            {'id': v.vendedor_id, 'name': v.vendedor_rel.nome}
            for v in vendors
        ]
        
        # Buscar equipes
        teams = UserEquipe.query.filter_by(
            user_id=user_id,
            ativo=True
        ).all()
        context['teams'] = [
            {'id': t.equipe_id, 'name': t.equipe_rel.nome}
            for t in teams
        ]
        
        # Buscar hierarquia completa com permissões
        categories = PermissionCategory.query.filter_by(
            ativo=True
        ).order_by(PermissionCategory.ordem).all()
        
        for category in categories:
            cat_data = {
                'id': category.id,
                'name': category.nome,
                'display_name': category.nome_exibicao,
                'permissions': _get_user_permissions(user_id, 'CATEGORY', category.id),
                'modules': []
            }
            
            # Buscar módulos
            modules = category.modules.filter_by(ativo=True).order_by(PermissionModule.ordem)
            
            for module in modules:
                mod_data = {
                    'id': module.id,
                    'name': module.nome,
                    'display_name': module.nome_exibicao,
                    'permissions': _get_user_permissions(user_id, 'MODULE', module.id),
                    'submodules': []
                }
                
                # Buscar submódulos
                submodules = module.submodules.filter_by(ativo=True).order_by(PermissionSubModule.ordem)
                
                for submodule in submodules:
                    sub_data = {
                        'id': submodule.id,
                        'name': submodule.nome,
                        'display_name': submodule.nome_exibicao,
                        'route': submodule.route_pattern,
                        'critical': submodule.critical_level,
                        'permissions': _get_user_permissions(user_id, 'SUBMODULE', submodule.id)
                    }
                    mod_data['submodules'].append(sub_data)
                
                cat_data['modules'].append(mod_data)
            
            context['categories'].append(cat_data)
        
        return context
        
    except Exception as e:
        logger.error(f"Erro ao buscar contexto de permissões: {e}")
        return context


def _get_user_permissions(user_id: int, entity_type: str, entity_id: int) -> Dict[str, bool]:
    """
    Busca permissões efetivas do usuário para uma entidade.
    Considera herança de vendedor/equipe.
    """
    permissions = {
        'can_view': False,
        'can_edit': False,
        'can_delete': False,
        'can_export': False,
        'source': 'none'  # none, direct, vendor, team, inherited
    }
    
    # 1. Verificar permissão direta
    user_perm = UserPermission.query.filter_by(
        user_id=user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        ativo=True
    ).first()
    
    if user_perm and not user_perm.is_expired:
        permissions.update({
            'can_view': user_perm.can_view,
            'can_edit': user_perm.can_edit,
            'can_delete': user_perm.can_delete,
            'can_export': user_perm.can_export,
            'source': 'direct'
        })
        
        # Se tem override customizado, não verificar herança
        if user_perm.custom_override:
            return permissions
    
    # 2. Verificar herança de vendedor
    vendor_ids = db.session.query(UserVendedor.vendedor_id).filter_by(
        user_id=user_id,
        ativo=True
    ).subquery()
    
    vendor_perms = VendedorPermission.query.filter(
        VendedorPermission.vendedor_id.in_(vendor_ids),
        VendedorPermission.entity_type == entity_type,
        VendedorPermission.entity_id == entity_id,
        VendedorPermission.ativo == True
    ).all()
    
    for vp in vendor_perms:
        if vp.can_view:
            permissions['can_view'] = True
            permissions['source'] = 'vendor'
        if vp.can_edit:
            permissions['can_edit'] = True
            permissions['source'] = 'vendor'
    
    # 3. Verificar herança de equipe
    team_ids = db.session.query(UserEquipe.equipe_id).filter_by(
        user_id=user_id,
        ativo=True
    ).subquery()
    
    team_perms = EquipePermission.query.filter(
        EquipePermission.equipe_id.in_(team_ids),
        EquipePermission.entity_type == entity_type,
        EquipePermission.entity_id == entity_id,
        EquipePermission.ativo == True
    ).all()
    
    for tp in team_perms:
        if tp.can_view:
            permissions['can_view'] = True
            if permissions['source'] == 'none':
                permissions['source'] = 'team'
        if tp.can_edit:
            permissions['can_edit'] = True
            if permissions['source'] == 'none':
                permissions['source'] = 'team'
    
    return permissions


def check_entity_permission(
    user_id: int,
    entity_type: str,
    entity_id: int,
    action: str = 'view'
) -> bool:
    """
    Verifica se usuário tem permissão específica em uma entidade.
    """
    permissions = _get_user_permissions(user_id, entity_type, entity_id)
    
    action_map = {
        'view': 'can_view',
        'edit': 'can_edit',
        'delete': 'can_delete',
        'export': 'can_export'
    }
    
    permission_key = action_map.get(action, 'can_view')
    return permissions.get(permission_key, False)


def check_inherited_permissions(
    user_id: int,
    entity_type: str,
    entity_id: int,
    action: str = 'view'
) -> bool:
    """
    Verifica permissões herdadas da hierarquia.
    Categoria -> Módulo -> Submódulo
    """
    # Se já é categoria (topo), não há herança
    if entity_type == 'CATEGORY':
        return False
    
    parents = []
    
    # Buscar hierarquia
    if entity_type == 'SUBMODULE':
        submodule = PermissionSubModule.query.get(entity_id)
        if submodule:
            # Adicionar módulo pai
            parents.append(('MODULE', submodule.module_id))
            # Adicionar categoria avô
            if submodule.module.category_id:
                parents.append(('CATEGORY', submodule.module.category_id))
    
    elif entity_type == 'MODULE':
        module = PermissionModule.query.get(entity_id)
        if module and module.category_id:
            # Adicionar categoria pai
            parents.append(('CATEGORY', module.category_id))
    
    # Verificar permissões nos pais
    for parent_type, parent_id in parents:
        if check_entity_permission(user_id, parent_type, parent_id, action):
            return True
    
    return False


def audit_permission_check(
    user,
    module: Optional[str] = None,
    submodule: Optional[str] = None,
    action: str = 'view',
    result: str = 'SUCCESS',
    reason: Optional[str] = None
):
    """
    Registra verificação de permissão no log de auditoria.
    """
    try:
        details = {
            'module': module,
            'submodule': submodule,
            'action': action,
            'reason': reason,
            'route': request.endpoint if request else None,
            'method': request.method if request else None
        }
        
        # Limpar valores None
        details = {k: v for k, v in details.items() if v is not None}
        
        PermissionLog.log(
            user_id=user.id,
            action='PERMISSION_CHECK',
            details=details,
            result=result,
            ip_address=request.remote_addr if request else None,
            user_agent=request.headers.get('User-Agent') if request else None,
            session_id=request.headers.get('X-Session-ID') if request else None
        )
    except Exception as e:
        logger.error(f"Erro ao registrar auditoria: {e}")


def grant_permissions_batch(
    user_ids: List[int],
    permissions: List[Dict[str, Any]],
    granted_by: int,
    reason: Optional[str] = None
) -> Tuple[int, int]:
    """
    Concede permissões em lote para múltiplos usuários.
    
    Args:
        user_ids: Lista de IDs de usuários
        permissions: Lista de dicts com entity_type, entity_id, can_view, can_edit, etc
        granted_by: ID do usuário que está concedendo
        reason: Motivo da concessão
    
    Returns:
        Tuple (sucessos, erros)
    """
    success_count = 0
    error_count = 0
    
    try:
        for user_id in user_ids:
            for perm_data in permissions:
                try:
                    # Buscar ou criar permissão
                    perm = UserPermission.query.filter_by(
                        user_id=user_id,
                        entity_type=perm_data['entity_type'],
                        entity_id=perm_data['entity_id']
                    ).first()
                    
                    if not perm:
                        perm = UserPermission(
                            user_id=user_id,
                            entity_type=perm_data['entity_type'],
                            entity_id=perm_data['entity_id'],
                            granted_by=granted_by
                        )
                        db.session.add(perm)
                    
                    # Atualizar permissões
                    perm.can_view = perm_data.get('can_view', False)
                    perm.can_edit = perm_data.get('can_edit', False)
                    perm.can_delete = perm_data.get('can_delete', False)
                    perm.can_export = perm_data.get('can_export', False)
                    perm.ativo = True
                    perm.reason = reason
                    
                    success_count += 1
                    
                except Exception as e:
                    logger.error(f"Erro ao conceder permissão: {e}")
                    error_count += 1
        
        db.session.commit()
        
        # Invalidar cache dos usuários
        from app.permissions.cache_unified import invalidate_user_permissions
        for user_id in user_ids:
            invalidate_user_permissions(user_id)
        
    except Exception as e:
        logger.error(f"Erro no batch de permissões: {e}")
        db.session.rollback()
        error_count = len(user_ids) * len(permissions)
    
    return success_count, error_count


def copy_permissions(
    from_user_id: int,
    to_user_ids: List[int],
    copied_by: int,
    include_vendors: bool = False,
    include_teams: bool = False
) -> Tuple[int, int]:
    """
    Copia permissões de um usuário para outros.
    """
    success_count = 0
    error_count = 0
    
    try:
        # Buscar permissões origem
        source_perms = UserPermission.query.filter_by(
            user_id=from_user_id,
            ativo=True
        ).all()
        
        for to_user_id in to_user_ids:
            try:
                # Copiar permissões diretas
                for source in source_perms:
                    # Verificar se já existe
                    existing = UserPermission.query.filter_by(
                        user_id=to_user_id,
                        entity_type=source.entity_type,
                        entity_id=source.entity_id
                    ).first()
                    
                    if not existing:
                        existing = UserPermission(
                            user_id=to_user_id,
                            entity_type=source.entity_type,
                            entity_id=source.entity_id,
                            granted_by=copied_by
                        )
                        db.session.add(existing)
                    
                    # Copiar permissões
                    existing.can_view = source.can_view
                    existing.can_edit = source.can_edit
                    existing.can_delete = source.can_delete
                    existing.can_export = source.can_export
                    existing.ativo = True
                    existing.reason = f"Copiado de usuário {from_user_id}"
                
                # Copiar vendedores se solicitado
                if include_vendors:
                    source_vendors = UserVendedor.query.filter_by(
                        user_id=from_user_id,
                        ativo=True
                    ).all()
                    
                    for sv in source_vendors:
                        if not UserVendedor.query.filter_by(
                            user_id=to_user_id,
                            vendedor_id=sv.vendedor_id
                        ).first():
                            new_vendor = UserVendedor(
                                user_id=to_user_id,
                                vendedor_id=sv.vendedor_id,
                                tipo_acesso=sv.tipo_acesso,
                                adicionado_por=copied_by
                            )
                            db.session.add(new_vendor)
                
                # Copiar equipes se solicitado
                if include_teams:
                    source_teams = UserEquipe.query.filter_by(
                        user_id=from_user_id,
                        ativo=True
                    ).all()
                    
                    for st in source_teams:
                        if not UserEquipe.query.filter_by(
                            user_id=to_user_id,
                            equipe_id=st.equipe_id
                        ).first():
                            new_team = UserEquipe(
                                user_id=to_user_id,
                                equipe_id=st.equipe_id,
                                tipo_acesso=st.tipo_acesso,
                                cargo_equipe=st.cargo_equipe,
                                adicionado_por=copied_by
                            )
                            db.session.add(new_team)
                
                success_count += 1
                
            except Exception as e:
                logger.error(f"Erro ao copiar para usuário {to_user_id}: {e}")
                error_count += 1
        
        db.session.commit()
        
        # Invalidar cache
        from app.permissions.cache_unified import invalidate_user_permissions
        for user_id in to_user_ids:
            invalidate_user_permissions(user_id)
        
    except Exception as e:
        logger.error(f"Erro na cópia de permissões: {e}")
        db.session.rollback()
        error_count = len(to_user_ids)
    
    return success_count, error_count