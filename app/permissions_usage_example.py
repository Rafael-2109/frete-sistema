"""
Exemplos de Uso do Sistema de Permissões Simples
================================================

Mostra como aplicar as permissões nas rotas existentes.
"""

# =============================================================================
# EXEMPLO 1: Rota de Carteira (vendedor vê só seus clientes)
# =============================================================================

from flask import render_template
from flask_login import login_required
from app.permissions.permissions_simple import check_permission, filter_by_user_data
from app.carteira.models import CarteiraCliente

@carteira_bp.route('/clientes')
@login_required
@check_permission('carteira')  # Verifica se pode acessar carteira
def listar_clientes():
    # Aplica filtro automático baseado no perfil
    clientes = filter_by_user_data(CarteiraCliente.query, CarteiraCliente).all()
    
    # Vendedor verá apenas seus clientes
    # Admin/Gerente verão todos
    return render_template('carteira/clientes.html', clientes=clientes)


# =============================================================================
# EXEMPLO 2: API com permissão de edição
# =============================================================================

@carteira_bp.route('/api/cliente/<int:id>', methods=['PUT'])
@login_required
@check_permission('carteira', 'edit')  # Verifica se pode editar
def editar_cliente(id):
    # Aplica filtro para garantir que só edita seus próprios dados
    cliente = filter_by_user_data(
        CarteiraCliente.query, 
        CarteiraCliente
    ).filter_by(id=id).first_or_404()
    
    # ... lógica de edição ...
    return jsonify({'success': True})


# =============================================================================
# EXEMPLO 3: EntregaMonitorada com comentários (vendedor pode comentar)
# =============================================================================

from app.permissions_simple import can_user_comment_entrega
from app.monitoramento.models import EntregaMonitorada, ComentarioNF

@monitoramento_bp.route('/entrega/<int:id>')
@login_required
@check_permission('monitoramento')
def visualizar_entrega(id):
    # Aplica filtro - vendedor só vê entregas de seus clientes
    entrega = filter_by_user_data(
        EntregaMonitorada.query,
        EntregaMonitorada
    ).filter_by(id=id).first_or_404()
    
    # Verifica se pode comentar
    pode_comentar = can_user_comment_entrega(entrega)
    
    return render_template('monitoramento/entrega.html', 
                         entrega=entrega,
                         pode_comentar=pode_comentar)


@monitoramento_bp.route('/entrega/<int:id>/comentar', methods=['POST'])
@login_required
@check_permission('monitoramento')  # Primeiro verifica acesso ao módulo
def adicionar_comentario(id):
    # Busca entrega com filtro
    entrega = filter_by_user_data(
        EntregaMonitorada.query,
        EntregaMonitorada
    ).filter_by(id=id).first_or_404()
    
    # Verifica se pode comentar especificamente
    if not can_user_comment_entrega(entrega):
        abort(403)
    
    # ... adicionar comentário ...
    return jsonify({'success': True})


# =============================================================================
# EXEMPLO 4: Template com verificação condicional
# =============================================================================

# No template Jinja2:
"""
{% if has_permission('carteira', 'edit') %}
    <button class="btn btn-primary">Editar Cliente</button>
{% endif %}

{% if current_user.perfil == 'vendedor' %}
    <p>Você está vendo apenas seus clientes</p>
{% endif %}
"""


# =============================================================================
# EXEMPLO 5: Aplicar em rotas existentes (modificação mínima)
# =============================================================================

# ANTES (rota sem permissão):
@faturamento_bp.route('/relatorios')
@login_required
def relatorios():
    relatorios = RelatorioFaturamento.query.all()
    return render_template('faturamento/relatorios.html', relatorios=relatorios)

# DEPOIS (com permissão):
from app.permissions_simple import check_permission, filter_by_user_data

@faturamento_bp.route('/relatorios')
@login_required
@check_permission('faturamento')  # ← Adiciona isso
def relatorios():
    # ↓ Muda query para aplicar filtro
    relatorios = filter_by_user_data(
        RelatorioFaturamento.query,
        RelatorioFaturamento
    ).all()
    return render_template('faturamento/relatorios.html', relatorios=relatorios)


# =============================================================================
# EXEMPLO 6: Portaria (perfil específico)
# =============================================================================

@portaria_bp.route('/registros')
@login_required
@check_permission('portaria')
def listar_registros():
    # Portaria vê todos os registros (sem filtro own_data)
    registros = RegistroPortaria.query.all()
    return render_template('portaria/registros.html', registros=registros)


@portaria_bp.route('/registro/novo', methods=['POST'])
@login_required
@check_permission('portaria', 'edit')  # Portaria pode editar
def criar_registro():
    # ... criar registro ...
    return jsonify({'success': True})


# =============================================================================
# EXEMPLO 7: Admin/Permissions (restrito)
# =============================================================================

@permissions_bp.route('/usuarios')
@login_required
def gerenciar_usuarios():
    # Só admin e gerente_comercial acessam (já tem all: True)
    if current_user.perfil not in ['administrador', 'gerente_comercial']:
        abort(403)
    
    usuarios = Usuario.query.all()
    return render_template('permissions/usuarios.html', usuarios=usuarios)