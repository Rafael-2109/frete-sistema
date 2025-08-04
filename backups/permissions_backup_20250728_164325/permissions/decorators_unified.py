"""
Sistema Unificado de Decoradores de Permissão
=============================================

Decorador único e flexível para todas as verificações de permissão.
Suporta cache multi-nível, auditoria completa e compatibilidade com sistema legado.
"""

from functools import wraps
from flask import abort, redirect, url_for, flash, request, g, jsonify
from flask_login import current_user
from app.permissions.models_unified import PermissionLog, UserPermission
from app.permissions.cache_unified import PermissionCache
from app.permissions.utils_unified import (
    get_user_permission_context,
    check_entity_permission,
    check_inherited_permissions,
    audit_permission_check
)
import logging
from typing import Optional, Union, List, Dict, Any, Callable

logger = logging.getLogger(__name__)


def check_permission(
    # Parâmetros principais
    module: Optional[str] = None,
    submodule: Optional[str] = None,
    function: Optional[str] = None,
    category: Optional[str] = None,
    
    # Ação requerida
    action: str = 'view',  # view, edit, delete, export
    
    # Comportamento
    redirect_on_fail: bool = True,
    message: Optional[str] = None,
    json_response: bool = False,
    
    # Permissões alternativas
    allow_if_any: Optional[List[str]] = None,  # Lista de perfis alternativos
    
    # Cache
    use_cache: bool = True,
    cache_ttl: int = 300,  # 5 minutos
    
    # Validador customizado
    custom_validator: Optional[Callable] = None,
    
    # Compatibilidade
    legacy_mode: bool = False
):
    """
    Decorador unificado para verificação de permissões.
    
    Args:
        module: Nome do módulo (ex: 'faturamento')
        submodule: Nome do submódulo (ex: 'faturas')
        function: Nome da função específica (ex: 'aprovar')
        category: Nome da categoria (ex: 'financeiro')
        
        action: Ação requerida ('view', 'edit', 'delete', 'export')
        
        redirect_on_fail: Se deve redirecionar em caso de falha
        message: Mensagem customizada de erro
        json_response: Se deve retornar JSON ao invés de redirect/abort
        
        allow_if_any: Lista de perfis que têm acesso alternativo
        
        use_cache: Se deve usar cache de permissões
        cache_ttl: Tempo de vida do cache em segundos
        
        custom_validator: Função customizada de validação
        
        legacy_mode: Força uso do sistema legado
    
    Exemplos:
        # Simples
        @check_permission(module='faturamento')
        
        # Com ação específica
        @check_permission(module='usuarios', action='edit')
        
        # Hierárquico completo
        @check_permission(
            category='financeiro',
            module='faturamento',
            submodule='faturas',
            function='aprovar',
            action='edit'
        )
        
        # Com perfis alternativos
        @check_permission(
            module='relatorios',
            allow_if_any=['administrador', 'gerente_comercial', 'financeiro']
        )
        
        # Para API JSON
        @check_permission(
            module='api',
            json_response=True,
            redirect_on_fail=False
        )
        
        # Com validador customizado
        @check_permission(
            module='vendas',
            custom_validator=lambda user: user.vendedor_vinculado is not None
        )
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Verificar autenticação
            if not current_user.is_authenticated:
                if json_response:
                    return jsonify({
                        'success': False,
                        'message': 'Autenticação requerida',
                        'error': 'unauthorized'
                    }), 401
                    
                if redirect_on_fail:
                    flash('Por favor, faça login para acessar esta página.', 'warning')
                    return redirect(url_for('auth.login', next=request.url))
                abort(401)
            
            # Administrador sempre tem acesso
            if current_user.perfil == 'administrador':
                # Log acesso de admin
                audit_permission_check(
                    user=current_user,
                    module=module,
                    submodule=submodule,
                    action=action,
                    result='SUCCESS',
                    reason='Admin bypass'
                )
                return f(*args, **kwargs)
            
            # Verificar perfis alternativos
            if allow_if_any and current_user.perfil in allow_if_any:
                audit_permission_check(
                    user=current_user,
                    module=module,
                    submodule=submodule,
                    action=action,
                    result='SUCCESS',
                    reason=f'Allowed by profile: {current_user.perfil}'
                )
                return f(*args, **kwargs)
            
            # Validador customizado
            if custom_validator:
                try:
                    if custom_validator(current_user):
                        audit_permission_check(
                            user=current_user,
                            module=module,
                            submodule=submodule,
                            action=action,
                            result='SUCCESS',
                            reason='Custom validator passed'
                        )
                        return f(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Erro no validador customizado: {e}")
            
            # Modo legado (compatibilidade)
            if legacy_mode:
                has_permission = _check_legacy_permission(
                    current_user, module, action
                )
            else:
                # Verificação moderna
                has_permission = _check_hierarchical_permission(
                    user=current_user,
                    category=category,
                    module=module,
                    submodule=submodule,
                    function=function,
                    action=action,
                    use_cache=use_cache,
                    cache_ttl=cache_ttl
                )
            
            # Processar resultado
            if not has_permission:
                # Log acesso negado
                audit_permission_check(
                    user=current_user,
                    module=module,
                    submodule=submodule,
                    action=action,
                    result='DENIED',
                    reason='Permission check failed'
                )
                
                # Determinar mensagem
                if not message:
                    action_msgs = {
                        'view': 'visualizar',
                        'edit': 'editar',
                        'delete': 'excluir',
                        'export': 'exportar'
                    }
                    action_text = action_msgs.get(action, action)
                    message = f'Você não tem permissão para {action_text} este recurso.'
                
                # Responder adequadamente
                if json_response:
                    return jsonify({
                        'success': False,
                        'message': message,
                        'error': 'forbidden'
                    }), 403
                    
                if redirect_on_fail:
                    flash(message, 'danger')
                    return redirect(url_for('main.dashboard'))
                    
                abort(403)
            
            # Log acesso permitido
            audit_permission_check(
                user=current_user,
                module=module,
                submodule=submodule,
                action=action,
                result='SUCCESS'
            )
            
            # Adicionar contexto de permissões ao g
            if not hasattr(g, 'user_permissions'):
                g.user_permissions = {}
            
            permission_key = f"{module or ''}.{submodule or ''}.{action}"
            g.user_permissions[permission_key] = True
            
            return f(*args, **kwargs)
            
        return decorated_function
    return decorator


def _check_legacy_permission(user, module: str, action: str) -> bool:
    """
    Verifica permissão usando sistema legado (compatibilidade).
    """
    try:
        # Mapeamento de ações para métodos legados
        if action == 'edit':
            if hasattr(user, 'pode_editar'):
                return user.pode_editar(module)
        
        # Para view e outras ações
        if hasattr(user, 'tem_permissao'):
            return user.tem_permissao(module)
        
        # Fallback para métodos específicos
        legacy_methods = {
            'usuarios': 'pode_aprovar_usuarios',
            'financeiro': 'pode_acessar_financeiro',
            'embarques': 'pode_acessar_embarques',
            'portaria': 'pode_acessar_portaria',
            'monitoramento': 'pode_acessar_monitoramento_geral'
        }
        
        method_name = legacy_methods.get(module)
        if method_name and hasattr(user, method_name):
            return getattr(user, method_name)()
        
        return False
        
    except Exception as e:
        logger.error(f"Erro na verificação legada: {e}")
        return False


def _check_hierarchical_permission(
    user,
    category: Optional[str],
    module: Optional[str],
    submodule: Optional[str],
    function: Optional[str],
    action: str,
    use_cache: bool,
    cache_ttl: int
) -> bool:
    """
    Verifica permissão usando sistema hierárquico moderno.
    """
    # Instância do cache
    cache = PermissionCache()
    
    # Gerar chave de cache
    cache_key = cache.generate_key(
        user_id=user.id,
        category=category,
        module=module,
        submodule=submodule,
        function=function or submodule,  # function é sinônimo de submodule
        action=action
    )
    
    # Verificar cache se habilitado
    if use_cache:
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            logger.debug(f"Cache hit para permissão: {cache_key}")
            return cached_result
    
    # Determinar entidade mais específica
    entity_type, entity_id = _find_most_specific_entity(
        category, module, submodule or function
    )
    
    if not entity_id:
        return False
    
    # Verificar permissão direta
    has_permission = check_entity_permission(
        user_id=user.id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action
    )
    
    # Se não tem permissão direta, verificar herança
    if not has_permission:
        has_permission = check_inherited_permissions(
            user_id=user.id,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action
        )
    
    # Cachear resultado
    if use_cache:
        cache.set(cache_key, has_permission, ttl=cache_ttl)
    
    return has_permission


def _find_most_specific_entity(
    category: Optional[str],
    module: Optional[str],
    submodule: Optional[str]
) -> tuple[Optional[str], Optional[int]]:
    """
    Encontra a entidade mais específica na hierarquia.
    """
    from app.permissions.models_unified import (
        PermissionCategory, PermissionModule, PermissionSubModule
    )
    
    # Tentar submódulo primeiro (mais específico)
    if submodule and module:
        sub = PermissionSubModule.query.join(
            PermissionModule
        ).filter(
            PermissionModule.nome == module,
            PermissionSubModule.nome == submodule,
            PermissionSubModule.ativo == True
        ).first()
        if sub:
            return 'SUBMODULE', sub.id
    
    # Tentar módulo
    if module:
        # Se especificou categoria, buscar dentro dela
        if category:
            mod = PermissionModule.query.join(
                PermissionCategory
            ).filter(
                PermissionCategory.nome == category,
                PermissionModule.nome == module,
                PermissionModule.ativo == True
            ).first()
        else:
            mod = PermissionModule.query.filter_by(
                nome=module, ativo=True
            ).first()
        
        if mod:
            return 'MODULE', mod.id
    
    # Tentar categoria
    if category:
        cat = PermissionCategory.query.filter_by(
            nome=category, ativo=True
        ).first()
        if cat:
            return 'CATEGORY', cat.id
    
    return None, None


# ============================================================================
# FUNÇÕES AUXILIARES PARA TEMPLATES
# ============================================================================

def can_access(
    module: Optional[str] = None,
    submodule: Optional[str] = None,
    category: Optional[str] = None,
    action: str = 'view'
) -> bool:
    """
    Função helper para verificar permissões em templates.
    
    Uso em templates:
        {% if can_access('faturamento') %}
            <a href="/faturamento">Faturamento</a>
        {% endif %}
        
        {% if can_access('usuarios', action='edit') %}
            <button>Editar Usuário</button>
        {% endif %}
    """
    if not current_user.is_authenticated:
        return False
    
    # Admin sempre pode
    if current_user.perfil == 'administrador':
        return True
    
    # Usar verificação hierárquica
    return _check_hierarchical_permission(
        user=current_user,
        category=category,
        module=module,
        submodule=submodule,
        function=None,
        action=action,
        use_cache=True,
        cache_ttl=300
    )


def get_user_permissions() -> Dict[str, Any]:
    """
    Retorna todas as permissões do usuário atual em formato estruturado.
    Útil para passar para o frontend.
    """
    if not current_user.is_authenticated:
        return {}
    
    context = get_user_permission_context(current_user.id)
    return context


# ============================================================================
# ALIASES PARA COMPATIBILIDADE
# ============================================================================

# Manter nomes antigos para não quebrar código existente
requer_permissao = check_permission
require_permission = check_permission
requer_edicao = lambda module, **kwargs: check_permission(module, action='edit', **kwargs)