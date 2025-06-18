"""
Decoradores de autenticação e autorização
Sistema de controle de permissões baseado nos perfis de usuário
"""

from functools import wraps
from flask import flash, redirect, url_for, request, abort
from flask_login import current_user

def require_permission(permission_method):
    """
    Decorador genérico para verificar permissões
    
    Args:
        permission_method (str): Nome do método de permissão no modelo Usuario
                                Ex: 'pode_acessar_financeiro', 'pode_aprovar_usuarios'
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Você precisa fazer login para acessar esta página.', 'warning')
                return redirect(url_for('auth.login'))
            
            # Verifica se o método de permissão existe no usuário
            if not hasattr(current_user, permission_method):
                flash('Erro interno: método de permissão não encontrado.', 'error')
                return abort(500)
            
            # Chama o método de permissão
            permission_check = getattr(current_user, permission_method)
            if not permission_check():
                flash(f'Acesso negado. Seu perfil ({current_user.perfil_nome}) não tem permissão para esta funcionalidade.', 'danger')
                return redirect(url_for('main.dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_profiles(*allowed_profiles):
    """
    Decorador para verificar perfis específicos
    
    Args:
        allowed_profiles: Lista de perfis permitidos
                         Ex: 'administrador', 'financeiro', 'logistica'
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Você precisa fazer login para acessar esta página.', 'warning')
                return redirect(url_for('auth.login'))
            
            if current_user.perfil not in allowed_profiles:
                flash(f'Acesso negado. Seu perfil ({current_user.perfil_nome}) não tem permissão para esta funcionalidade.', 'danger')
                flash(f'Perfis permitidos: {", ".join(allowed_profiles)}', 'info')
                return redirect(url_for('main.dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_admin():
    """Decorador específico para administradores"""
    return require_profiles('administrador')

def require_financeiro():
    """Decorador para acesso ao financeiro"""
    return require_permission('pode_acessar_financeiro')

def require_embarques():
    """Decorador para acesso aos embarques"""
    return require_permission('pode_acessar_embarques')

def require_portaria():
    """Decorador para acesso à portaria"""
    return require_permission('pode_acessar_portaria')

def require_monitoramento_geral():
    """Decorador para acesso ao monitoramento geral"""
    return require_permission('pode_acessar_monitoramento_geral')

def require_editar_cadastros():
    """Decorador para edição de cadastros"""
    return require_permission('pode_editar_cadastros')

def allow_vendedor_own_data():
    """
    Decorador especial para vendedores acessarem apenas seus próprios dados
    Deve ser usado em conjunto com lógica específica na rota
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Você precisa fazer login para acessar esta página.', 'warning')
                return redirect(url_for('auth.login'))
            
            # Administradores e perfis elevados têm acesso total
            if current_user.perfil in ['administrador', 'gerente_comercial', 'logistica', 'financeiro']:
                return f(*args, **kwargs)
            
            # Vendedores precisam de validação especial na rota
            if current_user.perfil == 'vendedor':
                # A rota deve implementar a lógica de verificação
                return f(*args, **kwargs)
            
            # Outros perfis não têm acesso
            flash(f'Acesso negado. Seu perfil ({current_user.perfil_nome}) não tem permissão para esta funcionalidade.', 'danger')
            return redirect(url_for('main.dashboard'))
        
        return decorated_function
    return decorator

# ================ FUNÇÕES AUXILIARES ================

def check_vendedor_permission(vendedor_nome=None, numero_nf=None):
    """
    Verifica se vendedor tem permissão para acessar dados específicos
    
    Args:
        vendedor_nome: Nome do vendedor no registro
        numero_nf: Número da NF para verificar no faturamento
    
    Returns:
        bool: True se tem permissão, False caso contrário
    """
    if not current_user.is_authenticated:
        return False
    
    # Administradores e perfis elevados têm acesso total
    if current_user.perfil in ['administrador', 'gerente_comercial', 'logistica', 'financeiro']:
        return True
    
    # Vendedores só podem ver seus próprios dados
    if current_user.perfil == 'vendedor':
        if current_user.vendedor_vinculado:
            # Verifica por nome do vendedor
            if vendedor_nome and vendedor_nome.upper() == current_user.vendedor_vinculado.upper():
                return True
            
            # Verifica por NF no faturamento (implementar se necessário)
            if numero_nf:
                from app.faturamento.models import RelatorioFaturamentoImportado
                nf_faturamento = RelatorioFaturamentoImportado.query.filter_by(numero_nf=numero_nf).first()
                if nf_faturamento and nf_faturamento.vendedor and \
                   nf_faturamento.vendedor.upper() == current_user.vendedor_vinculado.upper():
                    return True
        
        return False
    
    # Outros perfis não têm acesso
    return False

def get_vendedor_filter_query():
    """
    Retorna filtro de query para vendedores acessarem apenas seus dados
    
    Returns:
        Condição de filtro SQL ou None para acesso total
    """
    if not current_user.is_authenticated:
        return None
    
    # Administradores e perfis elevados têm acesso total
    if current_user.perfil in ['administrador', 'gerente_comercial', 'logistica', 'financeiro']:
        return None  # Sem filtro = acesso total
    
    # Vendedores só veem seus dados
    if current_user.perfil == 'vendedor' and current_user.vendedor_vinculado:
        # Retorna condição para filtrar por vendedor
        return current_user.vendedor_vinculado
    
    # Outros perfis sem acesso (retorna filtro impossível)
    return "ACESSO_NEGADO" 