"""
Exemplos de Uso do Sistema Unificado de Permissões
==================================================

Este arquivo demonstra como usar o novo sistema de decoradores unificados
em diferentes cenários.
"""

from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user

from app.permissions.decorators_unified import (
    check_permission,
    require_permission,
    require_admin,
    can_access,
    invalidate_user_cache
)

# Criar blueprint de exemplo
example_bp = Blueprint('permission_examples', __name__, url_prefix='/examples')


# =============================================================================
# EXEMPLOS BÁSICOS
# =============================================================================

@example_bp.route('/basic')
@login_required
@check_permission(module='faturamento')
def basic_permission():
    """Exemplo básico - apenas verificar módulo"""
    return "Você tem acesso ao módulo de faturamento!"


@example_bp.route('/basic-edit')
@login_required
@check_permission(module='faturamento', action='edit')
def basic_edit_permission():
    """Exemplo com ação de edição"""
    return "Você pode editar no módulo de faturamento!"


# =============================================================================
# EXEMPLOS HIERÁRQUICOS
# =============================================================================

@example_bp.route('/hierarchical')
@login_required
@check_permission(
    category='financeiro',
    module='faturamento',
    submodule='faturas',
    function='aprovar'
)
def hierarchical_permission():
    """Exemplo com hierarquia completa"""
    return "Você pode aprovar faturas!"


@example_bp.route('/hierarchical-partial')
@login_required
@check_permission(
    module='carteira',
    submodule='separacao',
    action='view'
)
def hierarchical_partial():
    """Exemplo com hierarquia parcial"""
    return render_template('carteira/separacao.html')


# =============================================================================
# EXEMPLOS COM PERMISSÕES ALTERNATIVAS
# =============================================================================

@example_bp.route('/alternative-permissions')
@login_required
@check_permission(
    module='relatorios',
    allow_if_any=['administrador', 'gerente', 'financeiro']
)
def alternative_permissions():
    """Permite acesso se tiver qualquer um dos perfis listados"""
    return "Relatório disponível para admin, gerente ou financeiro"


@example_bp.route('/multiple-roles')
@login_required
@check_permission(
    module='dashboard',
    function='vendas',
    allow_if_any=['vendedor', 'gerente_vendas', 'diretor_comercial']
)
def sales_dashboard():
    """Dashboard de vendas com múltiplos perfis permitidos"""
    return render_template('dashboard/vendas.html')


# =============================================================================
# EXEMPLOS COM VALIDADORES CUSTOMIZADOS
# =============================================================================

def is_owner_validator(user):
    """Validador customizado - verifica se é proprietário"""
    # Exemplo: verificar se o usuário é dono do recurso
    resource_id = request.view_args.get('id')
    if resource_id:
        # Verificar no banco se o usuário é dono
        from app.models import Resource
        resource = Resource.query.get(resource_id)
        return resource and resource.owner_id == user.id
    return False


@example_bp.route('/resource/<int:id>/edit')
@login_required
@check_permission(
    module='recursos',
    action='edit',
    custom_validator=is_owner_validator,
    message="Apenas o proprietário pode editar este recurso"
)
def edit_resource(id):
    """Editar recurso - apenas proprietário"""
    return f"Editando recurso {id}"


def vendedor_ativo_validator(user):
    """Verifica se é vendedor com status ativo"""
    return (
        hasattr(user, 'perfil') and 
        user.perfil == 'vendedor' and 
        hasattr(user, 'ativo') and 
        user.ativo
    )


@example_bp.route('/vendas/criar')
@login_required
@check_permission(
    module='vendas',
    function='criar',
    custom_validator=vendedor_ativo_validator,
    message="Apenas vendedores ativos podem criar vendas"
)
def criar_venda():
    """Criar venda - apenas vendedores ativos"""
    return render_template('vendas/criar.html')


# =============================================================================
# EXEMPLOS COM RESPOSTAS JSON
# =============================================================================

@example_bp.route('/api/data')
@login_required
@check_permission(
    module='api',
    function='consultar',
    json_response=True,
    redirect_on_fail=False
)
def api_data():
    """API endpoint com resposta JSON"""
    return jsonify({
        'success': True,
        'data': {
            'user': current_user.username,
            'module': 'api',
            'timestamp': datetime.now().isoformat()
        }
    })


@example_bp.route('/api/protected')
@login_required
@check_permission(
    module='api',
    function='admin_only',
    json_response=True,
    message="Este endpoint requer privilégios administrativos"
)
def api_protected():
    """API endpoint protegido"""
    return jsonify({
        'success': True,
        'message': 'Acesso concedido ao endpoint protegido'
    })


# =============================================================================
# EXEMPLOS COM CACHE
# =============================================================================

@example_bp.route('/cached')
@login_required
@check_permission(
    module='relatorios',
    function='pesados',
    use_cache=True,
    cache_ttl=600  # Cache por 10 minutos
)
def cached_permission():
    """Permissão com cache customizado"""
    # Esta verificação será cacheada por 10 minutos
    return "Relatório pesado com permissão cacheada"


@example_bp.route('/no-cache')
@login_required
@check_permission(
    module='seguranca',
    function='auditoria',
    use_cache=False  # Sempre verificar em tempo real
)
def no_cache_permission():
    """Permissão sem cache - sempre verifica"""
    return "Área de segurança - permissão sempre verificada"


# =============================================================================
# EXEMPLOS COM AUDITORIA DETALHADA
# =============================================================================

@example_bp.route('/audit-detailed')
@login_required
@check_permission(
    module='financeiro',
    function='transferencia',
    action='edit',
    audit_level='detailed'  # Log completo com todos os detalhes
)
def financial_transfer():
    """Operação crítica com auditoria detalhada"""
    return "Transferência financeira - todos os detalhes logados"


@example_bp.route('/audit-minimal')
@login_required
@check_permission(
    module='publico',
    function='consulta',
    audit_level='minimal'  # Log mínimo, apenas falhas
)
def public_query():
    """Consulta pública com log mínimo"""
    return "Consulta pública - log mínimo"


# =============================================================================
# EXEMPLOS DE ADMIN
# =============================================================================

@example_bp.route('/admin-only')
@login_required
@require_admin()
def admin_only():
    """Área exclusiva para administradores"""
    return "Área administrativa"


@example_bp.route('/admin-panel')
@login_required
@require_admin(
    message="Acesso ao painel administrativo restrito",
    json_response=False
)
def admin_panel():
    """Painel administrativo"""
    return render_template('admin/panel.html')


# =============================================================================
# EXEMPLOS EM TEMPLATES
# =============================================================================

@example_bp.route('/template-example')
@login_required
def template_permission_example():
    """Exemplo mostrando uso em templates"""
    return render_template('examples/permissions.html')


# Template examples/permissions.html:
"""
{% extends "base.html" %}

{% block content %}
<h1>Exemplos de Permissões em Templates</h1>

<!-- Verificação simples -->
{% if can_access('faturamento') %}
    <a href="/faturamento" class="btn btn-primary">Acessar Faturamento</a>
{% endif %}

<!-- Verificação com ação -->
{% if can_access('usuarios', action='edit') %}
    <button class="btn btn-warning">Editar Usuários</button>
{% endif %}

<!-- Verificação hierárquica -->
{% if can_access(category='financeiro', module='relatorios', function='gerar') %}
    <a href="/relatorios/financeiro/gerar">Gerar Relatório Financeiro</a>
{% endif %}

<!-- Menu dinâmico baseado em permissões -->
<ul class="nav">
    {% if can_access('dashboard') %}
        <li><a href="/dashboard">Dashboard</a></li>
    {% endif %}
    
    {% if can_access('vendas') %}
        <li class="dropdown">
            <a href="#" class="dropdown-toggle">Vendas</a>
            <ul class="dropdown-menu">
                {% if can_access('vendas', function='listar') %}
                    <li><a href="/vendas">Listar</a></li>
                {% endif %}
                {% if can_access('vendas', function='criar', action='edit') %}
                    <li><a href="/vendas/nova">Nova Venda</a></li>
                {% endif %}
            </ul>
        </li>
    {% endif %}
</ul>

<!-- Botões condicionais -->
<div class="actions">
    {% if can_access('pedidos', submodule='aprovacao', action='edit') %}
        <button class="btn btn-success" onclick="aprovarPedido()">
            Aprovar Pedido
        </button>
    {% endif %}
    
    {% if can_access('pedidos', submodule='cancelamento', action='edit') %}
        <button class="btn btn-danger" onclick="cancelarPedido()">
            Cancelar Pedido
        </button>
    {% endif %}
</div>
{% endblock %}
"""


# =============================================================================
# EXEMPLOS DE GERENCIAMENTO DE CACHE
# =============================================================================

@example_bp.route('/invalidate-cache/<int:user_id>')
@login_required
@require_admin()
def invalidate_cache_example(user_id):
    """Exemplo de invalidação de cache"""
    # Invalida cache de permissões do usuário
    invalidate_user_cache(user_id)
    
    return jsonify({
        'success': True,
        'message': f'Cache de permissões do usuário {user_id} invalidado'
    })


# =============================================================================
# EXEMPLOS COM MÚLTIPLAS VERIFICAÇÕES
# =============================================================================

@example_bp.route('/complex-permission')
@login_required
@check_permission(module='vendas', function='listar')  # Primeira verificação
@check_permission(module='clientes', function='visualizar')  # Segunda verificação
def complex_permission_check():
    """Rota que requer múltiplas permissões"""
    return "Você tem permissão para vendas E clientes!"


# =============================================================================
# EXEMPLOS COM CONTEXTO DE PERMISSÃO
# =============================================================================

from flask import g

@example_bp.route('/permission-context')
@login_required
@check_permission(
    category='comercial',
    module='vendas',
    submodule='pedidos',
    function='processar',
    action='edit'
)
def permission_context_example():
    """Exemplo usando contexto de permissão"""
    # Acessar informações de permissão do contexto
    permissions = g.get('permissions', {})
    
    return jsonify({
        'message': 'Permissão concedida',
        'context': permissions,
        'user': current_user.username
    })


# =============================================================================
# EXEMPLO DE USO COMPLETO EM UMA VIEW REAL
# =============================================================================

@example_bp.route('/faturamento/aprovar/<int:fatura_id>', methods=['GET', 'POST'])
@login_required
@check_permission(
    category='financeiro',
    module='faturamento',
    submodule='aprovacao',
    function='aprovar_fatura',
    action='edit',
    audit_level='detailed',
    message='Você não tem permissão para aprovar faturas'
)
def aprovar_fatura_completo(fatura_id):
    """Exemplo completo de aprovação de fatura com todas as features"""
    from app.faturamento.models import Fatura
    from app import db
    
    fatura = Fatura.query.get_or_404(fatura_id)
    
    if request.method == 'POST':
        # Processar aprovação
        fatura.status = 'aprovada'
        fatura.aprovada_por = current_user.id
        fatura.data_aprovacao = datetime.now()
        
        try:
            db.session.commit()
            flash('Fatura aprovada com sucesso!', 'success')
            
            # Invalidar cache do usuário que criou a fatura
            if fatura.criada_por:
                invalidate_user_cache(fatura.criada_por)
            
            return redirect(url_for('faturamento.listar'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao aprovar fatura: {str(e)}', 'danger')
    
    return render_template(
        'faturamento/aprovar.html',
        fatura=fatura,
        can_edit=can_access('faturamento', action='edit')
    )