"""
Decoradores de Permissões Avançados
===================================

Sistema baseado no novo modelo de permissões granulares.
Substitui os decorators antigos (@require_admin) por sistema flexível.
"""

from functools import wraps
from flask import flash, redirect, url_for, request, abort, jsonify
from flask_login import current_user
import logging

logger = logging.getLogger(__name__)

def require_permission(modulo_nome: str, funcao_nome: str, nivel_acesso: str = 'visualizar'):
    """
    Decorator moderno para verificar permissões granulares
    
    Args:
        modulo_nome (str): Nome do módulo (ex: 'faturamento', 'carteira')
        funcao_nome (str): Nome da função (ex: 'listar', 'editar', 'exportar') 
        nivel_acesso (str): 'visualizar' ou 'editar'
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Você precisa fazer login para acessar esta página.', 'warning')
                return redirect(url_for('auth.login'))
            
            # Verificar permissão usando o novo sistema
            if not _verificar_permissao_usuario(current_user.id, modulo_nome, funcao_nome, nivel_acesso):
                error_msg = f'Acesso negado. Você não tem permissão para "{funcao_nome}" no módulo "{modulo_nome}".'
                
                # Se for requisição AJAX, retornar JSON
                if request.headers.get('Content-Type') == 'application/json' or request.headers.get('Accept') == 'application/json':
                    return jsonify({'error': error_msg, 'code': 'PERMISSION_DENIED'}), 403
                
                flash(error_msg, 'danger')
                flash(f'Entre em contato com o administrador para solicitar acesso.', 'info')
                return redirect(url_for('main.dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_profile_level(nivel_minimo: int):
    """
    Decorator baseado em nível hierárquico do perfil
    
    Args:
        nivel_minimo (int): Nível mínimo necessário (0-10)
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Você precisa fazer login para acessar esta página.', 'warning')
                return redirect(url_for('auth.login'))
            
            # Verificar nível hierárquico
            nivel_usuario = _obter_nivel_usuario(current_user.id)
            if nivel_usuario < nivel_minimo:
                error_msg = f'Acesso negado. Nível de permissão insuficiente (necessário: {nivel_minimo}, atual: {nivel_usuario}).'
                flash(error_msg, 'danger')
                return redirect(url_for('main.dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_any_vendor_access():
    """
    Decorator para funções que vendedores podem acessar (seus próprios dados)
    Administradores e gerentes têm acesso total
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Você precisa fazer login para acessar esta página.', 'warning')
                return redirect(url_for('auth.login'))
            
            # Verificar se tem acesso (admin, gerente ou vendedor)
            if not _verificar_acesso_vendedor(current_user.id):
                flash('Acesso negado. Você não tem permissão para acessar dados de vendas.', 'danger')
                return redirect(url_for('main.dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# ============================================================================
# DECORATORS DE COMPATIBILIDADE (para migração gradual)
# ============================================================================

def require_admin_new(f):
    """
    Substituto moderno para @require_admin
    Usa o sistema de permissões para verificar nível administrativo
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Você precisa fazer login para acessar esta página.', 'warning')
            return redirect(url_for('auth.login'))
        
        # Verificar se é administrador no novo sistema
        if not _verificar_admin_permissao(current_user.id):
            flash('Acesso negado. Apenas administradores podem acessar esta funcionalidade.', 'danger')
            return redirect(url_for('main.dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function

def require_module_access(modulo_nome: str):
    """
    Decorator simplificado para acesso a módulos
    Verifica se o usuário tem qualquer permissão no módulo
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Você precisa fazer login para acessar esta página.', 'warning')
                return redirect(url_for('auth.login'))
            
            if not _verificar_acesso_modulo(current_user.id, modulo_nome):
                flash(f'Acesso negado ao módulo "{modulo_nome}".', 'danger')
                return redirect(url_for('main.dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================

def _verificar_permissao_usuario(user_id: int, modulo_nome: str, funcao_nome: str, nivel_acesso: str) -> bool:
    """Verifica se usuário tem permissão específica"""
    try:
        from app.permissions.models import PermissaoUsuario, ModuloSistema, FuncaoModulo
        
        # Buscar módulo
        modulo = ModuloSistema.query.filter_by(nome=modulo_nome, ativo=True).first()
        if not modulo:
            logger.warning(f"Módulo '{modulo_nome}' não encontrado")
            return False
        
        # Buscar função
        funcao = FuncaoModulo.query.filter_by(
            modulo_id=modulo.id, 
            nome=funcao_nome,
            ativo=True
        ).first()
        if not funcao:
            logger.warning(f"Função '{funcao_nome}' não encontrada no módulo '{modulo_nome}'")
            return False
        
        # Verificar permissão
        permissao = PermissaoUsuario.query.filter_by(
            usuario_id=user_id,
            funcao_id=funcao.id,
            ativo=True
        ).first()
        
        if not permissao:
            return False
        
        # Verificar nível de acesso
        if nivel_acesso == 'visualizar':
            return permissao.pode_visualizar
        elif nivel_acesso == 'editar':
            return permissao.pode_editar
        
        return False
        
    except Exception as e:
        logger.error(f"Erro ao verificar permissão: {e}")
        return False

def _verificar_admin_permissao(user_id: int) -> bool:
    """Verifica se usuário é administrador no novo sistema"""
    try:
        from app.permissions.models import PerfilUsuario
        from app.auth.models import Usuario
        
        usuario = Usuario.query.get(user_id)
        if not usuario:
            return False
        
        # Buscar perfil detalhado
        if hasattr(usuario, 'perfil_detalhado') and usuario.perfil_detalhado:
            return usuario.perfil_detalhado.nivel_hierarquico >= 9  # Nível admin
        
        # Fallback para perfil antigo
        return usuario.perfil == 'administrador'
        
    except Exception as e:
        logger.error(f"Erro ao verificar admin: {e}")
        return False

def _obter_nivel_usuario(user_id: int) -> int:
    """Obtém nível hierárquico do usuário"""
    try:
        from app.auth.models import Usuario
        
        usuario = Usuario.query.get(user_id)
        if not usuario:
            return 0
        
        if hasattr(usuario, 'perfil_detalhado') and usuario.perfil_detalhado:
            return usuario.perfil_detalhado.nivel_hierarquico
        
        # Fallback para sistema antigo
        niveis_antigos = {
            'administrador': 10,
            'gerente_comercial': 8,
            'logistica': 7,
            'financeiro': 6,
            'vendedor': 3,
            'usuario_comum': 1
        }
        return niveis_antigos.get(usuario.perfil, 0)
        
    except Exception as e:
        logger.error(f"Erro ao obter nível: {e}")
        return 0

def _verificar_acesso_vendedor(user_id: int) -> bool:
    """Verifica se usuário pode acessar dados de vendas"""
    try:
        from app.auth.models import Usuario
        
        usuario = Usuario.query.get(user_id)
        if not usuario:
            return False
        
        # Administradores e gerentes têm acesso total
        if _obter_nivel_usuario(user_id) >= 6:  # Financeiro ou superior
            return True
        
        # Vendedores podem acessar seus dados
        if usuario.perfil == 'vendedor':
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"Erro ao verificar acesso vendedor: {e}")
        return False

def _verificar_acesso_modulo(user_id: int, modulo_nome: str) -> bool:
    """Verifica se usuário tem qualquer acesso ao módulo"""
    try:
        from app.permissions.models import PermissaoUsuario, ModuloSistema, FuncaoModulo
        
        # Buscar módulo
        modulo = ModuloSistema.query.filter_by(nome=modulo_nome, ativo=True).first()
        if not modulo:
            return False
        
        # Verificar se tem alguma permissão no módulo
        permissoes = PermissaoUsuario.query.join(FuncaoModulo).filter(
            PermissaoUsuario.usuario_id == user_id,
            FuncaoModulo.modulo_id == modulo.id,
            PermissaoUsuario.ativo == True,
            FuncaoModulo.ativo == True
        ).first()
        
        return permissoes is not None
        
    except Exception as e:
        logger.error(f"Erro ao verificar acesso módulo: {e}")
        return False

# ============================================================================
# HELPERS PARA TEMPLATES
# ============================================================================

def user_can_access(modulo_nome: str, funcao_nome: str, nivel_acesso: str = 'visualizar') -> bool:
    """
    Helper para usar em templates Jinja2
    
    Uso: {% if user_can_access('faturamento', 'editar', 'editar') %}
    """
    if not current_user.is_authenticated:
        return False
    
    return _verificar_permissao_usuario(current_user.id, modulo_nome, funcao_nome, nivel_acesso)

def user_is_admin() -> bool:
    """Helper para verificar se usuário é admin"""
    if not current_user.is_authenticated:
        return False
    
    return _verificar_admin_permissao(current_user.id)

def user_level() -> int:
    """Helper para obter nível do usuário"""
    if not current_user.is_authenticated:
        return 0
    
    return _obter_nivel_usuario(current_user.id)