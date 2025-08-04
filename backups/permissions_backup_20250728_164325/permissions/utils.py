"""
Utilitários para o Sistema de Permissões
=========================================

Funções auxiliares para facilitar o gerenciamento de permissões.
"""

from functools import wraps
from flask import abort, redirect, url_for, flash
from flask_login import current_user
from app.permissions.models import LogPermissao
import logging

logger = logging.getLogger(__name__)

# Decoradores para verificação de permissões
def requer_permissao(modulo, funcao=None, submodulo=None, redirecionar=True):
    """
    Decorador que verifica se o usuário tem permissão para acessar uma rota.
    
    Args:
        modulo: Nome do módulo (ex: 'faturamento')
        funcao: Nome da função específica (opcional)
        submodulo: Nome do submódulo (opcional)
        redirecionar: Se True, redireciona para login. Se False, retorna 403.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                if redirecionar:
                    flash('Por favor, faça login para acessar esta página.', 'warning')
                    return redirect(url_for('auth.login'))
                abort(401)
            
            # Verificar permissão
            if not current_user.tem_permissao(modulo, funcao, submodulo):
                # Registrar tentativa negada
                LogPermissao.registrar(
                    usuario_id=current_user.id,
                    acao='TENTATIVA_NEGADA',
                    funcao_id=None,  # TODO: buscar ID da função
                    detalhes=f'Módulo: {modulo}, Função: {funcao}, Submódulo: {submodulo}',
                    resultado='NEGADO'
                )
                
                if redirecionar:
                    flash('Você não tem permissão para acessar esta página.', 'danger')
                    return redirect(url_for('main.index'))
                abort(403)
            
            # Registrar uso bem-sucedido
            LogPermissao.registrar(
                usuario_id=current_user.id,
                acao='USADA',
                funcao_id=None,  # TODO: buscar ID da função
                detalhes=f'Módulo: {modulo}, Função: {funcao}, Submódulo: {submodulo}',
                resultado='SUCESSO'
            )
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def requer_edicao(modulo, funcao=None, submodulo=None, redirecionar=True):
    """
    Decorador que verifica se o usuário pode editar no módulo/função.
    
    Args:
        modulo: Nome do módulo (ex: 'faturamento')
        funcao: Nome da função específica (opcional)
        submodulo: Nome do submódulo (opcional)
        redirecionar: Se True, redireciona para login. Se False, retorna 403.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                if redirecionar:
                    flash('Por favor, faça login para acessar esta página.', 'warning')
                    return redirect(url_for('auth.login'))
                abort(401)
            
            # Verificar permissão de edição
            if not current_user.pode_editar(modulo, funcao, submodulo):
                # Registrar tentativa negada
                LogPermissao.registrar(
                    usuario_id=current_user.id,
                    acao='TENTATIVA_NEGADA',
                    funcao_id=None,  # TODO: buscar ID da função
                    detalhes=f'Edição - Módulo: {modulo}, Função: {funcao}, Submódulo: {submodulo}',
                    resultado='NEGADO'
                )
                
                if redirecionar:
                    flash('Você não tem permissão para editar nesta página.', 'danger')
                    return redirect(url_for('main.index'))
                abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def requer_perfil(perfis_permitidos, redirecionar=True):
    """
    Decorador que verifica se o usuário tem um dos perfis permitidos.
    Mantém compatibilidade com o sistema antigo.
    
    Args:
        perfis_permitidos: Lista de perfis permitidos ou string com perfil único
        redirecionar: Se True, redireciona para login. Se False, retorna 403.
    """
    if isinstance(perfis_permitidos, str):
        perfis_permitidos = [perfis_permitidos]
    
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                if redirecionar:
                    flash('Por favor, faça login para acessar esta página.', 'warning')
                    return redirect(url_for('auth.login'))
                abort(401)
            
            if current_user.perfil not in perfis_permitidos:
                if redirecionar:
                    flash('Você não tem o perfil necessário para acessar esta página.', 'danger')
                    return redirect(url_for('main.index'))
                abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Funções auxiliares para templates
def usuario_pode_ver(modulo, funcao=None, submodulo=None):
    """
    Função helper para usar em templates Jinja2.
    Verifica se o usuário atual pode visualizar.
    """
    if not current_user.is_authenticated:
        return False
    return current_user.tem_permissao(modulo, funcao, submodulo)

def usuario_pode_editar(modulo, funcao=None, submodulo=None):
    """
    Função helper para usar em templates Jinja2.
    Verifica se o usuário atual pode editar.
    """
    if not current_user.is_authenticated:
        return False
    return current_user.pode_editar(modulo, funcao, submodulo)

def get_modulos_menu():
    """
    Retorna os módulos que devem aparecer no menu para o usuário atual.
    """
    if not current_user.is_authenticated:
        return []
    
    modulos = current_user.get_modulos_permitidos()
    
    # Agrupar por categoria se disponível
    from app.permissions.models import PermissionCategory
    categorias = PermissionCategory.query.filter_by(ativo=True).order_by(PermissionCategory.ordem).all()
    
    menu_estruturado = []
    for categoria in categorias:
        modulos_categoria = [m for m in modulos if m.category_id == categoria.id]
        if modulos_categoria:
            menu_estruturado.append({
                'categoria': categoria,
                'modulos': modulos_categoria
            })
    
    # Adicionar módulos sem categoria
    modulos_sem_categoria = [m for m in modulos if not m.category_id]
    if modulos_sem_categoria:
        menu_estruturado.append({
            'categoria': None,
            'modulos': modulos_sem_categoria
        })
    
    return menu_estruturado

# Funções para gerenciamento em massa
def conceder_permissoes_em_lote(usuario_ids, funcao_ids, pode_visualizar=True, pode_editar=False, concedente_id=None):
    """
    Concede permissões em lote para múltiplos usuários e funções.
    
    Returns:
        Tuple (sucesso_count, erro_count, detalhes)
    """
    from app import db
    from app.permissions.models import PermissaoUsuario, BatchPermissionOperation
    import json
    
    sucesso_count = 0
    erro_count = 0
    detalhes = []
    
    # Registrar operação em lote
    operacao = BatchPermissionOperation(
        tipo_operacao='GRANT',
        descricao=f'Concessão em lote: {len(usuario_ids)} usuários, {len(funcao_ids)} funções',
        executado_por=concedente_id or current_user.id
    )
    
    try:
        for usuario_id in usuario_ids:
            for funcao_id in funcao_ids:
                try:
                    # Verificar se já existe
                    permissao = PermissaoUsuario.query.filter_by(
                        usuario_id=usuario_id,
                        funcao_id=funcao_id
                    ).first()
                    
                    if not permissao:
                        permissao = PermissaoUsuario(
                            usuario_id=usuario_id,
                            funcao_id=funcao_id,
                            concedida_por=concedente_id or current_user.id
                        )
                    
                    permissao.pode_visualizar = pode_visualizar
                    permissao.pode_editar = pode_editar
                    permissao.ativo = True
                    
                    db.session.add(permissao)
                    sucesso_count += 1
                    
                except Exception as e:
                    erro_count += 1
                    detalhes.append(f'Erro ao conceder permissão U:{usuario_id} F:{funcao_id}: {str(e)}')
        
        # Atualizar operação
        operacao.usuarios_afetados = len(usuario_ids)
        operacao.permissoes_alteradas = sucesso_count
        operacao.detalhes = {
            'sucesso': sucesso_count,
            'erros': erro_count,
            'detalhes_erros': detalhes[:10]  # Limitar detalhes
        }
        operacao.status = 'CONCLUIDO' if erro_count == 0 else 'CONCLUIDO_COM_ERROS'
        
        db.session.add(operacao)
        db.session.commit()
        
        return sucesso_count, erro_count, detalhes
        
    except Exception as e:
        db.session.rollback()
        operacao.status = 'ERRO'
        operacao.erro_detalhes = str(e)
        db.session.add(operacao)
        db.session.commit()
        raise

def revogar_permissoes_em_lote(usuario_ids, funcao_ids=None, modulo_ids=None, revogador_id=None):
    """
    Revoga permissões em lote.
    Pode revogar por função específica ou todas de um módulo.
    
    Returns:
        Tuple (sucesso_count, erro_count, detalhes)
    """
    from app import db
    from app.permissions.models import PermissaoUsuario, FuncaoModulo, BatchPermissionOperation
    
    sucesso_count = 0
    erro_count = 0
    detalhes = []
    
    # Registrar operação em lote
    operacao = BatchPermissionOperation(
        tipo_operacao='REVOKE',
        descricao=f'Revogação em lote: {len(usuario_ids)} usuários',
        executado_por=revogador_id or current_user.id
    )
    
    try:
        # Se especificou módulos, buscar todas as funções deles
        if modulo_ids and not funcao_ids:
            funcao_ids = db.session.query(FuncaoModulo.id).filter(
                FuncaoModulo.modulo_id.in_(modulo_ids)
            ).all()
            funcao_ids = [f[0] for f in funcao_ids]
        
        for usuario_id in usuario_ids:
            query = PermissaoUsuario.query.filter_by(usuario_id=usuario_id)
            
            if funcao_ids:
                query = query.filter(PermissaoUsuario.funcao_id.in_(funcao_ids))
            
            permissoes = query.all()
            
            for permissao in permissoes:
                try:
                    permissao.ativo = False
                    db.session.add(permissao)
                    sucesso_count += 1
                except Exception as e:
                    erro_count += 1
                    detalhes.append(f'Erro ao revogar permissão ID:{permissao.id}: {str(e)}')
        
        # Atualizar operação
        operacao.usuarios_afetados = len(usuario_ids)
        operacao.permissoes_alteradas = sucesso_count
        operacao.detalhes = {
            'sucesso': sucesso_count,
            'erros': erro_count,
            'detalhes_erros': detalhes[:10]
        }
        operacao.status = 'CONCLUIDO' if erro_count == 0 else 'CONCLUIDO_COM_ERROS'
        
        db.session.add(operacao)
        db.session.commit()
        
        return sucesso_count, erro_count, detalhes
        
    except Exception as e:
        db.session.rollback()
        operacao.status = 'ERRO'
        operacao.erro_detalhes = str(e)
        db.session.add(operacao)
        db.session.commit()
        raise